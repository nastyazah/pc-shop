from __future__ import annotations

import time
from collections import Counter
from dataclasses import replace

from ..config import settings
from ..embeddings import embed_query
from ..opensearch_client import get_client
from . import llm
from .builder import FACET_FIELDS, FACET_LABELS, SearchParams, build_body, build_filters, lexical_query
from .query_parser import CAT_LABEL, ParsedQuery, nearest_terms, parse


def _merge(p: SearchParams, pq: ParsedQuery) -> SearchParams:
    """Фільтри з інтерфейсу (явний вибір) мають пріоритет над тим, що ми зрозуміли з тексту."""
    specs = {k: [str(v) for v in vals] for k, vals in pq.specs.items()}
    specs.update(p.specs)
    return SearchParams(
        q=p.q, page=p.page, size=p.size,
        sort=p.sort if p.sort != "relevance" else (pq.sort or "relevance"),  # явний вибір у списку сильніший
        category=p.category or pq.category,
        brands=p.brands or ([pq.brand] if pq.brand else []),
        price_min=p.price_min if p.price_min is not None else pq.price_min,
        price_max=p.price_max if p.price_max is not None else pq.price_max,
        in_stock=p.in_stock or pq.in_stock,
        specs=specs,
    )


def _buckets(agg: dict, labels: dict | None = None) -> list[dict]:
    out = []
    for b in agg.get("buckets", []):
        key = b["key"]
        out.append({"value": key, "label": (labels or {}).get(key), "count": b["doc_count"]})
    if out and all(isinstance(b["value"], (int, float)) for b in out):
        out.sort(key=lambda b: b["value"])  # числові фасети (обсяг, потужність) - за зростанням
    return out


RELATED_TITLE = "Інші товари, які можуть вас зацікавити"
_EMPTY_FACETS = {"categories": [], "brands": [], "price": {"min": None, "max": None}, "specs": {}}


def _no_ui_filters(p: SearchParams) -> bool:
    return not (p.category or p.brands or p.specs or p.price_min is not None or p.price_max is not None)


def _blank(pq: ParsedQuery, state: str, t0: float, **extra) -> dict:
    """Відповідь без товарів: "ми це не продаємо" або "не зрозуміли запит"."""
    out = {
        "state": state, "total": 0, "hybrid": False, "items": [], "took_ms": round((time.perf_counter() - t0) * 1000),
        "understood": {"chips": [], "corrected_from": pq.corrected_from, "typos": pq.typos, "splits": pq.splits,
                       "llm": pq.llm, "suggestion": None},
        "applied": {"category": None, "brands": []}, "facets": _EMPTY_FACETS,
        "not_sold": None, "variants": [], "related": None,
    }
    out.update(extra)
    return out


def _related_items(categories: list[str], per: int = 2) -> list[dict]:
    """Доречні товари з пов'язаних категорій (найпопулярніші, в наявності). Порожній список = нічого не показуємо."""
    items: list[dict] = []
    for cat in categories[:4]:
        try:
            resp = get_client().search(index=settings.index_alias, body={
                "size": per, "sort": [{"popularity": "desc"}],
                "query": {"bool": {"filter": [{"term": {"category": cat}}, {"term": {"in_stock": True}}]}},
                "_source": {"excludes": ["embedding", "specs_text"]},
            })
        except Exception:  # noqa: BLE001
            continue
        items += [h["_source"] for h in resp["hits"]["hits"]]
    return items


def _not_sold_response(pq: ParsedQuery, noun: str, certain: bool, related: list[str], t0: float) -> dict:
    items = _related_items(related) if related else []
    return _blank(pq, "not_sold", t0, not_sold={"product": noun, "certain": certain},
                  related={"title": RELATED_TITLE, "items": items} if items else None)


def _unknown_response(pq: ParsedQuery, params: SearchParams, result: dict, t0: float) -> dict:
    """Запит не зрозуміли: пропонуємо найімовірніші варіанти, а не випадкові картки."""
    variants = [{"label": t, "q": t} for t in nearest_terms(params.q)]  # можливо, ви мали на увазі
    for cat, n in Counter(it["category"] for it in result["items"][:10]).most_common(3):
        if n >= 2 and len(variants) < 4:  # категорії, до яких найближча семантична видача
            variants.append({"label": CAT_LABEL[cat], "q": params.q, "category": cat})
    return _blank(pq, "unknown", t0, variants=variants)


def search(params: SearchParams) -> dict:
    t0 = time.perf_counter()
    pq = parse(params.q) if params.q else ParsedQuery(raw="")
    if pq.not_sold and _no_ui_filters(params):  # однозначно не наш асортимент (словник): навіть не шукаємо
        return _not_sold_response(pq, pq.not_sold["noun"], True, pq.not_sold["related"], t0)
    if params.q and llm.should_ask(pq):
        llm.enhance(pq)  # лише для "невпевнених" запитів; помилки LLM ігноруються
    result = _run(params, pq)
    if result["total"] == 0 and pq.llm:  # LLM звузив надто сильно: повторюємо лише за правилами
        pq = parse(params.q)
        result = _run(params, pq)
    _verify_suggestion(result, pq.suggest_category)

    lexical_total = result.pop("lexical_total", None)
    if result["hybrid"] and lexical_total == 0 and not result["understood"]["suggestion"]:
        # жодного збігу за словами і семантика нічого не підтвердила: показувати "найближче" було б вгадуванням
        if pq.llm_not_sold:
            return _not_sold_response(pq, pq.llm_not_sold, False, [], t0)
        return _unknown_response(pq, params, result, t0)

    _finalize_items(result)
    result.update(state="ok", not_sold=None, variants=[], related=None)
    result["took_ms"] = round((time.perf_counter() - t0) * 1000)
    return result


def _finalize_items(result: dict) -> None:
    """Гібридна видача: товари підтвердженої категорії йдуть першими (порядок усередині груп збережено), далі сторінка."""
    page, size = result.pop("page_info")
    if not result["hybrid"]:
        return
    items = result["items"]
    sug = (result["understood"].get("suggestion") or {}).get("category")
    if sug:
        items = [i for i in items if i["category"] == sug] + [i for i in items if i["category"] != sug]
    result["items"] = items[(page - 1) * size : page * size]


def _verify_suggestion(result: dict, suggested: str | None) -> None:
    """Підказку категорії показуємо, лише якщо її підтверджує семантична видача (другий незалежний сигнал).
    Підказка LLM потребує 3+ товарів цієї категорії в топ-10. Без LLM підказкою стає категорія, що домінує (6+ з 10)."""
    ui = result["understood"]
    if not result["hybrid"] or result["applied"]["category"]:
        ui["suggestion"] = None
        return
    counts = Counter(it["category"] for it in result["items"][:10])
    sug = suggested if suggested and counts[suggested] >= 3 else None
    if sug is None and counts:
        top, n = counts.most_common(1)[0]
        if n >= 6:
            sug = top
    ui["suggestion"] = {"category": sug, "label": CAT_LABEL[sug]} if sug else None


def _run(params: SearchParams, pq: ParsedQuery) -> dict:
    merged = _merge(params, pq)

    vector = embed_query(pq.text) if pq.text else None
    # гібрид: беремо весь пул кандидатів, щоб перевпорядкувати за підтвердженою категорією; сторінку виріжемо потім
    pooled = bool(pq.text) and merged.sort == "relevance"
    run_params = replace(merged, page=1, size=max(merged.size, settings.knn_k)) if pooled else merged
    body, hybrid = build_body(run_params, pq.text, vector)
    resp = get_client().search(
        index=settings.index_alias, body=body,
        params={"search_pipeline": settings.search_pipeline} if hybrid else None,
    )

    lexical_total = None  # скільки товарів має збіг за словами (без векторів): ознака, що запит узагалі про щось у каталозі
    if pooled and not (merged.category or merged.brands or merged.specs):
        try:
            lexical_total = get_client().count(
                index=settings.index_alias, body={"query": lexical_query(pq.text, build_filters(merged))})["count"]
        except Exception:  # noqa: BLE001 - без цього сигналу просто показуємо видачу як є
            lexical_total = None

    aggs = resp.get("aggregations", {})
    price = aggs.get("price", {})
    specs = {
        name: {"label": FACET_LABELS[name], "buckets": _buckets(aggs.get(f"spec_{name}", {}))}
        for name in FACET_FIELDS.get(merged.category or "", [])
    }
    items = [{**h["_source"], "score": h.get("_score")} for h in resp["hits"]["hits"]]
    return {
        "total": resp["hits"]["total"]["value"],
        "took_ms": 0,
        "hybrid": hybrid,
        "items": items,
        "page_info": (merged.page, merged.size),
        "lexical_total": lexical_total,
        "understood": {"chips": pq.chips, "corrected_from": pq.corrected_from, "typos": pq.typos, "splits": pq.splits, "llm": pq.llm,
                       "suggestion": ({"category": pq.suggest_category, "label": CAT_LABEL[pq.suggest_category]} if pq.suggest_category else None)},
        "applied": {"category": merged.category, "brands": merged.brands},
        "facets": {
            "categories": _buckets(aggs.get("categories", {}), CAT_LABEL),
            "brands": _buckets(aggs.get("brands", {})),
            "price": {"min": price.get("min"), "max": price.get("max")},
            "specs": specs,
        },
    }


def suggest(q: str) -> dict:
    pq = parse(q)
    filters = [{"term": {"category_path": pq.category}}] if pq.category else []
    if pq.text:
        query = {"bool": {"filter": filters, "must": [{"bool": {"should": [
            {"match": {"name.suggest": {"query": pq.text, "operator": "and"}}},
            {"match": {"name.code": {"query": pq.text, "fuzziness": "AUTO:4,8", "prefix_length": 1}}},
            {"match": {"name.morph": {"query": pq.text, "fuzziness": "AUTO:4,8", "prefix_length": 1}}},
        ], "minimum_should_match": 1}}]}}
    else:
        query = {"bool": {"filter": filters, "must": [{"match_all": {}}]}}
    resp = get_client().search(index=settings.index_alias, body={
        "size": 6, "query": query, "sort": [{"_score": "desc"}, {"popularity": "desc"}],
        "_source": ["id", "name", "brand", "price", "category"],
    })
    return {"chips": pq.chips, "products": [h["_source"] for h in resp["hits"]["hits"]]}
