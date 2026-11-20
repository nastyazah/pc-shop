"""Побудова запитів OpenSearch: лексичний (BM25), векторний (kNN), гібрид, фасети."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..config import settings

# які фільтри показувати для якої категорії
FACET_FIELDS = {
    "motherboards": ["socket", "chipset", "ram_type", "form_factor", "wifi"],
    "cpu": ["socket", "cores"],
    "gpu": ["vendor", "chip", "vram_gb"],
    "ram": ["ram_type", "capacity_gb", "speed_mhz"],
    "ssd": ["capacity_gb", "interface", "form_factor"],
    "hdd": ["capacity_gb", "rpm", "form_factor"],
    "psu": ["wattage", "efficiency", "modularity"],
    "cases": ["form_factor", "color"],
    "coolers": ["type", "radiator_mm"],
    "fans": ["size_mm", "quantity"],
}
FACET_LABELS = {
    "socket": "Сокет", "chipset": "Чипсет", "ram_type": "Тип памʼяті", "form_factor": "Форм-фактор",
    "wifi": "Wi-Fi", "cores": "Кількість ядер", "vendor": "Виробник чипа", "chip": "Графічний чип",
    "vram_gb": "Відеопамʼять, ГБ", "capacity_gb": "Обсяг", "speed_mhz": "Частота, МГц",
    "interface": "Інтерфейс", "rpm": "Швидкість, об/хв", "wattage": "Потужність, Вт",
    "efficiency": "Сертифікат 80+", "modularity": "Модульність", "color": "Колір", "type": "Тип",
    "radiator_mm": "Радіатор, мм", "size_mm": "Розмір, мм", "quantity": "У комплекті, шт",
}
SORTS = {
    "price_asc": [{"price": "asc"}],
    "price_desc": [{"price": "desc"}],
    "popular": [{"popularity": "desc"}],
}


@dataclass
class SearchParams:
    q: str = ""
    page: int = 1
    size: int = 24
    sort: str = "relevance"
    category: str | None = None
    brands: list[str] = field(default_factory=list)
    price_min: float | None = None
    price_max: float | None = None
    in_stock: bool = False
    specs: dict[str, list[str]] = field(default_factory=dict)


def build_filters(p: SearchParams) -> list[dict]:
    f: list[dict] = []
    if p.category:
        f.append({"term": {"category_path": p.category}})
    if p.brands:
        f.append({"terms": {"brand": p.brands}})
    for name, values in p.specs.items():
        f.append({"terms": {f"specs.{name}": values}})
    if p.price_min is not None or p.price_max is not None:
        rng = {}
        if p.price_min is not None:
            rng["gte"] = p.price_min
        if p.price_max is not None:
            rng["lte"] = p.price_max
        f.append({"range": {"price": rng}})
    if p.in_stock:
        f.append({"term": {"in_stock": True}})
    return f


def lexical_query(text: str, filters: list[dict]) -> dict:
    """Точний збіг за артикулом/моделлю + морфологія + синоніми + опечатки в латиниці."""
    if not text:
        return {"bool": {"filter": filters, "must": [{"match_all": {}}]}}
    should = [
        {"term": {"sku": {"value": text.lower(), "boost": 100}}},
        {
            "multi_match": {
                "query": text,
                "type": "best_fields",
                "tie_breaker": 0.3,
                "minimum_should_match": "70%",
                "fields": [
                    "name^4", "name.morph^3", "name.code^5", "sku.code^5", "specs_text^2",
                    "brand.text^2", "category_name^1.5", "category_name.morph^1.5",
                    "description^0.5", "description.morph^0.5",
                ],
            }
        },
        {
            "multi_match": {  # опечатки, пропущені й зайві літери; поля без синонімів
                "query": text,
                "type": "best_fields",
                "fuzziness": "AUTO:4,8",
                "prefix_length": 1,
                "minimum_should_match": "75%",
                "boost": 0.4,
                "fields": ["name.code^3", "name.morph^3", "category_name.morph^2", "brand.text^1.5"],
            }
        },
    ]
    return {"bool": {"filter": filters, "must": [{"bool": {"should": should, "minimum_should_match": 1}}]}}


def knn_query(vector: list[float], filters: list[dict]) -> dict:
    inner: dict = {"vector": vector, "k": settings.knn_k}
    if filters:
        inner["filter"] = {"bool": {"filter": filters}}
    return {"knn": {"embedding": inner}}


def aggregations(category: str | None) -> dict:
    aggs: dict = {
        "categories": {"terms": {"field": "category", "size": 20}},
        "brands": {"terms": {"field": "brand", "size": 20}},
        "price": {"stats": {"field": "price"}},
    }
    for name in FACET_FIELDS.get(category or "", []):
        aggs[f"spec_{name}"] = {"terms": {"field": f"specs.{name}", "size": 20}}
    return aggs


def build_body(p: SearchParams, text: str, vector: list[float] | None) -> tuple[dict, bool]:
    """Повертає (тіло запиту, чи_гібрид). Гібрид лише для сортування за релевантністю."""
    filters = build_filters(p)
    lex = lexical_query(text, filters)
    hybrid = bool(text) and vector is not None and p.sort == "relevance"
    offset = (p.page - 1) * p.size

    body: dict = {
        "size": p.size,
        "from": offset,
        "track_total_hits": True,
        "_source": {"excludes": ["embedding", "specs_text"]},
        "aggs": aggregations(p.category),
    }
    if hybrid:
        body["query"] = {"hybrid": {
            "queries": [lex, knn_query(vector, filters)],
            "pagination_depth": max(50, offset + p.size),
        }}
    else:
        body["query"] = lex
        body["sort"] = SORTS.get(p.sort) or (
            [{"_score": "desc"}, {"popularity": "desc"}] if text else [{"popularity": "desc"}]
        )
    return body, hybrid
