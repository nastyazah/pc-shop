"""Розбір складних запитів за допомогою LLM (необов'язковий шар).

Принципи:
  * LLM лише ПРОПОНУЄ структуру. Усе проходить валідацію за білими списками (категорії, бренди, ключі характеристик).
  * Правила мають пріоритет: LLM заповнює тільки те, чого парсер не зміг визначити.
  * Викликається лише для "невпевнених" запитів (немає категорії/бренду/фільтрів), результат кешується.
  * Помилка, таймаут чи відсутність ключа = пошук працює як без LLM.
"""
from __future__ import annotations

import json
import logging
import re
import time

import httpx

from ..config import settings
from .builder import FACET_FIELDS
from .normalize import normalize
from .phonetic import phonetic_key
from .query_parser import _STOP as STOP_WORDS
from .query_parser import _dl
from .query_parser import BRAND_ENTRIES, CAT_LABEL, ParsedQuery, build_chips

log = logging.getLogger("llm")

SPEC_KEYS = sorted({k for keys in FACET_FIELDS.values() for k in keys})
ENUMS = {"ram_type": {"DDR3", "DDR4", "DDR5"}, "vendor": {"NVIDIA", "AMD"}}
NUMERIC = {"cores", "vram_gb", "capacity_gb", "speed_mhz", "rpm", "wattage", "radiator_mm", "size_mm", "quantity"}

_cache: dict[str, tuple[float, dict | None]] = {}
LAST: dict = {}  # остання спроба виклику (для /api/llm/check)
_TTL, _NEG_TTL = 24 * 3600, 60  # успіх зберігаємо добу, невдачу хвилину


def _system_prompt() -> str:
    cats = "; ".join(f"{slug} = {label}" for slug, label in CAT_LABEL.items())
    return f"""You convert a search query for a Ukrainian online shop of PC components into JSON.
Return ONLY one JSON object, no prose, with exactly these keys:
{{"category": string|null, "brand": string|null, "price_min": number|null, "price_max": number|null,
 "specs": object, "text": string, "not_sold_product": string|null}}
Extract ONLY what the query explicitly states. Do NOT guess, infer or add anything the user did not write.
- category must be one of these slugs ({cats}); otherwise null.
- brand must be one of: {", ".join(BRAND_ENTRIES)}; otherwise null.
- Prices are in UAH. "до 30 тисяч" means price_max=30000 and price_min=null. "від 5 тисяч" means price_min=5000 only.
- specs: only values the user wrote with a number or a name, e.g. "8 гб" -> {{"vram_gb":[8]}} for a graphics card, "1 тб" -> {{"capacity_gb":[1000]}}, "750 вт" -> {{"wattage":[750]}}. If no explicit value is written, specs must be {{}}.
- text: the remaining meaningful keywords (model names, traits like "тихий", use cases like "кіберпанк"), corrected for typos and wrong keyboard layout, at most 6 words, WITHOUT prices, numbers with units or filler words. Empty string if nothing remains.
- not_sold_product: if the query names a product type that is clearly NOT a PC component (e.g. speakers, mouse, keyboard, monitor, laptop, headphones, printer, phone), give its Ukrainian plural noun, otherwise null.
- Understand Ukrainian and Russian, slang, typos, glued words and wrong keyboard layout."""


def _complete(system: str, user: str) -> str:
    if settings.llm_provider == "anthropic":
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": settings.llm_api_key, "anthropic-version": "2023-06-01"},
            json={"model": settings.llm_model, "max_tokens": 300, "system": system,
                  "messages": [{"role": "user", "content": user}]},
            timeout=settings.llm_timeout,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"])
    r = httpx.post(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {settings.llm_api_key or 'none'}"},
        json={"model": settings.llm_model, "temperature": 0, "max_tokens": 300,
              "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
        timeout=settings.llm_timeout,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _num(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if 0 < x < 10_000_000 else None


UNITS = {  # число характеристики має стояти поруч із такою одиницею в запиті
    "vram_gb": r"(?:гб|gb|гіг\w*|гиг\w*)", "capacity_gb": r"(?:гб|gb|тб|tb|гіг\w*|гиг\w*|тера\w*)",
    "wattage": r"(?:вт|w|ват\w*)", "speed_mhz": r"(?:мгц|mhz)", "cores": r"(?:ядер|ядра|ядро|core\w*)",
    "rpm": r"(?:об/хв|rpm)", "size_mm": r"(?:мм|mm)", "radiator_mm": r"(?:мм|mm)", "quantity": r"(?:шт\w*)",
}


def _grounded_number(key: str, value: float, query: str) -> bool:
    """Число з LLM приймаємо, лише якщо воно з одиницею є в самому запиті (8 гб, 750 вт, 2 терабайти)."""
    unit = UNITS.get(key)
    if not unit:
        return False
    for m in re.finditer(rf"(\d+(?:[.,]\d+)?)\s*({unit})(?!\w)", query):
        n = float(m.group(1).replace(",", "."))
        if m.group(2).startswith(("тб", "tb", "тера")):
            n *= 1000
        if abs(n - value) < 1e-6:
            return True
    return False


def _grounded_price(value: float, query: str) -> bool:
    """Ціна з LLM має збігатися з числом із запиту (також "30 тисяч", "30к")."""
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(тис\w*|[кk](?!\w))?", query):
        n = float(m.group(1).replace(",", "."))
        if m.group(2):
            n *= 1000
        if abs(n - value) < 1e-6:
            return True
    return False


_FILLER = {"тисяч", "тисячі", "тис", "грн", "гривень", "гривні", "₴", "uah"}


def _clean_text(text: str) -> str:
    out = []
    for t in re.sub(r"[^\w\s'.+-]", " ", text).lower().split():
        if t in _FILLER or t.isdigit() or t in STOP_WORDS:
            continue
        out.append(t)
    return " ".join(out[:6])[:80]


def validate(raw: str, query: str) -> dict | None:
    """Відповідь моделі -> безпечна структура (або None).
    Білі списки + "прив'язка до запиту": жорсткі умови (ціна, характеристики) беремо лише якщо вони справді в тексті."""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(d, dict):
        return None
    q = normalize(query)

    specs: dict[str, list] = {}
    raw_specs = d.get("specs") if isinstance(d.get("specs"), dict) else {}
    for key, vals in raw_specs.items():
        if key not in SPEC_KEYS:
            continue
        clean = []
        for v in (vals if isinstance(vals, list) else [vals])[:5]:
            if isinstance(v, bool):
                continue
            if key in NUMERIC:
                x = _num(v)
                if x is not None and _grounded_number(key, x, q):
                    clean.append(x)
            elif isinstance(v, str) and 0 < len(v) <= 30:
                v = v.strip().upper().replace(" ", "") if key in ("socket", "ram_type", "vendor") else v.strip()
                if (key not in ENUMS or v in ENUMS[key]) and v.lower().replace(" ", "") in q.replace(" ", ""):
                    clean.append(v)
        if clean:
            specs[key] = clean

    pmin, pmax = _num(d.get("price_min")), _num(d.get("price_max"))
    pmin = pmin if pmin is not None and _grounded_price(pmin, q) else None
    pmax = pmax if pmax is not None and _grounded_price(pmax, q) else None
    if pmin is not None and pmax is not None and pmin >= pmax:
        pmin = None
    brand = d.get("brand") if d.get("brand") in BRAND_ENTRIES else None
    if brand and brand.lower().replace(" ", "").replace("!", "") not in q.replace(" ", ""):
        brand = None  # бренд не названо в запиті: це вигадка моделі
    return {
        "category": d.get("category") if d.get("category") in CAT_LABEL else None,
        "brand": brand,
        "price_min": pmin,
        "price_max": pmax,
        "specs": specs,
        "text": _clean_text(str(d.get("text") or "")),
        "not_sold": re.sub(r"[^\w\s'-]", "", str(d.get("not_sold_product") or "")).strip().lower()[:40] or None,
    }


def _lookup(query: str) -> dict | None:
    key = normalize(query)
    hit = _cache.get(key)
    if hit and hit[0] > time.time():
        return hit[1]
    t0 = time.perf_counter()
    data, raw, error = None, "", None
    try:
        raw = _complete(_system_prompt(), query)
        data = validate(raw, query)
        if data is None:
            error = "відповідь моделі не схожа на JSON"
    except Exception as exc:  # noqa: BLE001 - LLM не має ламати пошук
        error = repr(exc)
    seconds = round(time.perf_counter() - t0, 1)
    LAST.update(query=query, seconds=seconds, error=error, raw=raw[:500])
    if error:
        log.warning("LLM не допоміг (%s с): %s", seconds, error)
    _cache[key] = (time.time() + (_TTL if data else _NEG_TTL), data)
    if len(_cache) > 1000:
        _cache.pop(next(iter(_cache)))
    return data


def debug(query: str) -> dict:
    """Повний прохід для діагностики: сира відповідь моделі, результат валідації, час."""
    t0 = time.perf_counter()
    out: dict = {"query": query, "timeout_s": settings.llm_timeout}
    try:
        raw = _complete(_system_prompt(), query)
        out["raw"] = raw
        out["validated"] = validate(raw, query)
    except Exception as exc:  # noqa: BLE001
        out["error"] = repr(exc)
    out["seconds"] = round(time.perf_counter() - t0, 1)
    return out


def enabled() -> bool:
    return settings.llm_provider in ("openai", "anthropic") and bool(settings.llm_model)


def should_ask(pq: ParsedQuery) -> bool:
    """Питаємо LLM лише коли правила нічого не зрозуміли і в запиті є слова, схожі на звичайну мову."""
    if not enabled() or pq.category or pq.brand or pq.specs:
        return False
    tokens = pq.text.split()
    return bool(tokens) and not all(t.isascii() or any(c.isdigit() for c in t) for t in tokens)


def _supported(tok: str, refs: list[str]) -> bool:
    """Слово з LLM має спиратись на слово із запиту (збіг, опечатка, звучання), інакше це вигадка."""
    for r in refs:
        if tok == r or (tok[:1] == r[:1] and _dl(tok, r, 2) <= 2):
            return True
        if not tok.isascii() and not r.isascii() and len(tok) >= 5 and phonetic_key(tok) == phonetic_key(r):
            return True
    return False


def enhance(pq: ParsedQuery) -> bool:
    """Доповнює ParsedQuery тим, чого не знайшли правила. Повертає True, якщо щось змінилось.
    Жорсткими фільтрами стають лише умови, підтверджені текстом запиту; "вгадана" категорія - лише підказка."""
    data = _lookup(pq.raw)
    if not data:
        return False
    changed = False
    if pq.brand is None and data["brand"]:
        pq.brand, changed = data["brand"], True
    if pq.category is None and data["category"]:
        pq.suggest_category, changed = data["category"], True  # не фільтр: показуємо як "Можливо, ви шукаєте"
    allowed = set(FACET_FIELDS.get(pq.category or "", SPEC_KEYS))
    for k, v in data["specs"].items():
        if k in allowed and k not in pq.specs:
            pq.specs[k], changed = v, True
    if pq.price_min is None and pq.price_max is None:  # ціну, знайдену правилами, LLM не чіпає
        if data["price_min"] is not None or data["price_max"] is not None:
            pq.price_min, pq.price_max, changed = data["price_min"], data["price_max"], True
    refs = [t for t in re.findall(r"[\w'+-]+", normalize(pq.raw)) if t not in STOP_WORDS] + pq.text.split()
    text = " ".join(t for t in data["text"].split() if _supported(t, refs))
    if text and text != pq.text:
        pq.text, changed = text, True  # LLM виправляє розкладку/опечатки; вигадані слова відкинуто
    if data["not_sold"] and _supported(data["not_sold"].split()[-1], refs):  # назва товару має спиратись на слово запиту
        pq.llm_not_sold, changed = data["not_sold"], True
    if changed:
        pq.llm = True
        pq.chips = build_chips(pq)
    return changed
