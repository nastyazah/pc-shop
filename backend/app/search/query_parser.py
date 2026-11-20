"""Розуміння запиту: сирий текст -> {категорія, бренд, фільтри, ціна, залишок тексту}.

Правила + словники (а не ML): детерміновано, швидко, легко покращувати логами пошуку.
Стійкість до помилок складається з шарів:
  1. нормалізація (регістр, апострофи, ё/ы/э/ґ);
  2. виправлення розкладки ("vfnthbyrf" -> "материнка");
  3. зіставлення за основою слова (материнка -> материнки/материнку);
  4. нечіткий матчинг за відстанню Дамерау-Левенштейна (плта, відеокрта, процеср, asuss).
Жорсткі фільтри (категорія, бренд, сокет, тип RAM, виробник чипа, ціна) звужують видачу.
М'які (обсяг, потужність) застосовуються лише коли відома категорія.
"""
from __future__ import annotations

import re
from functools import lru_cache
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config import INFRA
from .normalize import LAYOUT_RE, UK_LAYOUT_RE, fix_layout, normalize, unfix_layout
from .phonetic import phonetic_key

_DICT = Path(__file__).parent / "dictionaries"
_cats = yaml.safe_load((_DICT / "categories.yml").read_text("utf-8"))
_brands = yaml.safe_load((_DICT / "brands.yml").read_text("utf-8"))
_STOP = {
    w.strip()
    for w in (INFRA / "opensearch/analysis/stopwords_uk.txt").read_text("utf-8").splitlines()
    if w.strip() and not w.startswith("#")
}

_not_sold = yaml.safe_load((_DICT / "not_sold.yml").read_text("utf-8"))
NOT_SOLD_ENTRIES = {noun: [normalize(t).split() for t in d["terms"]] for noun, d in _not_sold.items()}
NOT_SOLD_RELATED = {noun: d.get("related") or [] for noun, d in _not_sold.items()}
CAT_LABEL = {slug: d["label"] for slug, d in _cats.items()}
CAT_ENTRIES = {slug: [normalize(t).split() for t in d["terms"]] for slug, d in _cats.items()}
BRAND_ENTRIES = {name: [normalize(t).split() for t in terms] for name, terms in _brands.items()}
BRAND_IMPLIES_CATEGORY = {"ryzen": "cpu", "райзен": "cpu", "ризен": "cpu"}

# кирилічні написання назв чипів -> латиниця (щоб збігалось з назвами моделей)
_CHIP_WORDS = {"ртх": "rtx", "гтх": "gtx", "радеон": "radeon", "джифорс": "geforce", "джіфорс": "geforce",
               "нвідіа": "nvidia", "нвидиа": "nvidia", "нвідія": "nvidia"}
_NVIDIA = {"nvidia", "geforce", "rtx", "gtx"}
_RADEON = {"radeon", "rx"}


# ---------- зіставлення слів ----------
def _stem_match(tok: str, entry: str) -> bool:
    if entry.isascii():
        return tok == entry
    if len(entry) >= 5:  # кирилиця: порівнюємо за основою (без останньої літери)
        return tok.startswith(entry[:-1])
    if len(entry) == 4:  # короткі слова: допускаємо закінчення (блок -> блоки, блоків)
        return tok.startswith(entry) and len(tok) - 4 <= 2
    return tok == entry


def _typo_limit(n: int) -> int:
    return 0 if n <= 3 else (1 if n <= 7 else 2)


def _dl(a: str, b: str, limit: int) -> int:
    """Відстань Дамерау-Левенштейна (вставка, видалення, заміна, перестановка сусідніх)."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2: list[int] | None = None
    prev = list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        cur = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if prev2 is not None and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        prev2, prev = prev, cur
    return prev[-1]


_ENDINGS = "аиуіюеєяої"


def _phonetic_cost(tok: str, entry: str) -> int | None:
    """Збіг за звуковою формою: тільки кирилиця й слова від 5 літер."""
    if entry.isascii() or tok.isascii() or len(tok) < 5 or len(entry) < 5:
        return None
    pt, pe = phonetic_key(tok), phonetic_key(entry)
    if pt == pe:
        return 1
    if len(pe) >= 7 and pt.startswith(pe[:-1]) and len(pt) - len(pe) <= 2:  # + закінчення (лише довгі слова)
        return 1
    return None


def _fuzzy_cost(tok: str, entry: str) -> int | None:
    """Скільки помилок у слові відносно еталона (None - не схоже).
    Правопис: відстань Дамерау-Левенштейна з тією ж першою літерою. Слух: звукова форма."""
    if any(ch.isdigit() for ch in tok) or tok in _STOP:
        return None
    phon = _phonetic_cost(tok, entry)
    k = _typo_limit(len(tok))
    if tok[:1] != entry[:1] or k == 0 or len(entry) < 4:
        return phon
    best: int | None = None

    def consider(a: str, b: str, limit: int) -> None:
        nonlocal best
        d = _dl(a, b, limit)
        if d <= limit and (best is None or d < best):
            best = d

    consider(tok, entry, k)
    if not entry.isascii():
        if len(entry) >= 5 and tok[-1] in _ENDINGS:  # "плти" ~ "плата": закінчення береться зі слова користувача
            consider(tok, entry[:-1] + tok[-1], k)
        if len(tok) - 1 >= 4:  # слово довше за еталон (множина): "бмоки" ~ "блок"
            consider(tok[:-1], entry, 1)
        if len(entry) >= 7:  # відмінювана форма довгого слова: порівнюємо основу
            consider(tok[: len(entry) - 1], entry[:-1], 1)
    return best if best is not None else phon


def _tok_cost(tok: str, entry: str, fuzzy: bool) -> int | None:
    if _stem_match(tok, entry):
        return 0
    return _fuzzy_cost(tok, entry) if fuzzy else None


_NEAR_VOCAB = sorted({t for ents in (*CAT_ENTRIES.values(), *BRAND_ENTRIES.values()) for ph in ents for t in ph if len(t) >= 5})
_SINGLE = [ph[0] for ents in (*CAT_ENTRIES.values(), *BRAND_ENTRIES.values()) for ph in ents if len(ph) == 1]


def _known(tok: str) -> bool:
    return any(_stem_match(tok, e) for e in _SINGLE)


def _known_fuzzy(tok: str) -> bool:
    return any(_fuzzy_cost(tok, e) is not None for e in _SINGLE)


# латинські слова, які можуть бути набрані українською розкладкою ("фігі" = asus, "кеч" = rtx)
_LATIN_VOCAB = {e for e in _SINGLE if e.isascii() and len(e) >= 3} | {
    "rtx", "gtx", "ddr", "radeon", "geforce", "nvidia", "ryzen", "core", "wifi", "argb", "rgb"}
_RE_MODEL = re.compile(r"(rtx|gtx|rx|ddr|am|lga)\d*")


def _fix_token_layout(t: str) -> str | None:
    """Слово, набране не тією розкладкою, -> правильне слово (або None). Також терпить помилки в слові."""
    if LAYOUT_RE.fullmatch(t) and len(re.findall(r"[a-z\[\];',./]", t)) >= 3 and not _known(t):
        c = fix_layout(t)
        if _known(c) or _known_fuzzy(c):
            return c
    elif UK_LAYOUT_RE.fullmatch(t) and len(re.findall(r"[а-яіїєґ]", t)) >= 3 and not _known(t) and not _known_fuzzy(t):
        c = unfix_layout(t)
        if c in _LATIN_VOCAB or _RE_MODEL.fullmatch(c):
            return c
    return None


def _find(tokens: list[str], entries: dict[str, list[list[str]]], fuzzy: bool):
    hits = []
    for key, phrases in entries.items():
        for ph in phrases:
            n = len(ph)
            for i in range(len(tokens) - n + 1):
                costs = [_tok_cost(tokens[i + j], ph[j], fuzzy) for j in range(n)]
                if None not in costs:
                    hits.append((n, key, i, i + n, " ".join(ph), sum(costs)))
    return hits


def _resolve_not_sold(tokens: list[str]) -> str | None:
    """Назва товару, якого немає в асортименті. Спершу точні збіги, потім з урахуванням помилок."""
    for fuzzy in (False, True):
        hits = sorted((-n, cost, s, noun) for n, noun, s, e, ph, cost in _find(tokens, NOT_SOLD_ENTRIES, fuzzy))
        if hits:
            return hits[0][3]
    return None


def nearest_terms(text: str, limit: int = 3) -> list[str]:
    """Найближчі до слів запиту слова зі словників (вільніший поріг, ніж у розпізнаванні): "можливо, ви мали на увазі"."""
    out: list[str] = []
    for tok in re.findall(r"\w[\w'-]*", normalize(text)):
        if len(tok) < 5 or tok in _STOP or any(ch.isdigit() for ch in tok):
            continue
        scored = []
        for term in _NEAR_VOCAB:
            d = _dl(tok, term, 3)
            if d <= 2 or (d == 3 and tok[:3] == term[:3]):
                scored.append((d, term))
        if scored:
            out.append(min(scored)[1])
    return list(dict.fromkeys(out))[:limit]


def _resolve(tokens: list[str]):
    """Жадібно призначає по одній категорії та одному бренду. Спершу точні збіги, потім нечіткі.
    Довші фрази мають пріоритет, далі - раніше згадані (cooler master psu -> бренд Cooler Master)."""
    used: set[int] = set()
    got: dict[str, tuple | None] = {"category": None, "brand": None}
    for fuzzy in (False, True):
        hits = []
        for kind, entries in (("category", CAT_ENTRIES), ("brand", BRAND_ENTRIES)):
            for n, key, s, e, ph, cost in _find(tokens, entries, fuzzy):
                hits.append((-n, cost, s, kind, key, e, ph))
        for _, _, s, kind, key, e, ph in sorted(hits):
            if got[kind] or used & set(range(s, e)):
                continue
            got[kind] = (key, s, e, ph, fuzzy)
            used |= set(range(s, e))
    return got, used


# ---------- злитне написання: "материнкаасус8000грн" -> "материнка асус 8000 грн" ----------
_VOCAB = sorted(
    {t for ents in (*CAT_ENTRIES.values(), *BRAND_ENTRIES.values()) for ph in ents for t in ph
     if len(t) >= 3 and t not in _STOP}
    | {"rtx", "gtx", "radeon", "geforce", "nvidia", "ryzen", "core"},
    key=len, reverse=True,
)
_GLUE = sorted({w for w in _STOP if 2 <= len(w) <= 4}
               | {"гб", "тб", "gb", "tb", "вт", "w", "грн", "uah", "mhz", "мгц", "ddr", "ддр", "am", "ам", "lga"},
               key=len, reverse=True)
_RUN_RE = re.compile(r"[а-яіїєґ']+|[a-z]+|\d+")


def _piece_ends(run: str, i: int):
    n = len(run)
    for w in _VOCAB:
        if run.startswith(w, i):
            yield i + len(w), "word"
        elif not w.isascii() and len(w) >= 5 and run.startswith(w[:-1], i):  # слово з закінченням
            for extra in (1, 2, 3):
                if i + len(w) - 1 + extra <= n:
                    yield i + len(w) - 1 + extra, "word"
    for g in _GLUE:
        if run.startswith(g, i):
            yield i + len(g), "glue"


def _segment_run(run: str, multi: bool) -> list[str] | None:
    """Розбиває послідовність літер на слова зі словника. multi=True: поруч є цифри/інше письмо."""
    n = len(run)

    @lru_cache(maxsize=None)
    def best(i: int):
        if i == n:
            return (0, 0, ())  # (кількість слів-з-словника, кількість "клею", шматки)
        res = None
        for end, kind in _piece_ends(run, i):
            sub = best(end)
            if sub is None:
                continue
            cand = (sub[0] + (kind == "word"), sub[1] + (kind == "glue"), (run[i:end],) + sub[2])
            if res is None or (len(cand[2]), cand[1]) < (len(res[2]), res[1]):
                res = cand
        return res

    r = best(0)
    if r:
        words, glue, parts = r
        if multi and (words >= 1 or glue >= 1):
            return list(parts)
        if not multi and words >= 2:
            return list(parts)
    if re.fullmatch(r"[a-z]+", run):  # латинська модель після бренду: "kingstonfury" -> kingston fury
        for w in _VOCAB:
            if w.isascii() and len(w) >= 4 and run.startswith(w) and len(run) - len(w) >= 3:
                return [w, run[len(w):]]
            if w.isascii() and len(w) >= 4 and run.endswith(w) and len(run) - len(w) >= 3:
                return [run[: -len(w)], w]
    return None


def _split_token(t: str) -> list[str] | None:
    if not re.fullmatch(r"[0-9a-zа-яіїєґ']+", t) or RE_DDR.fullmatch(t) or RE_SOCKET.fullmatch(t):
        return None
    runs = _RUN_RE.findall(t)
    if len(runs) == 1 and (runs[0].isdigit() or len(runs[0]) < 7):
        return None
    pieces: list[tuple[str, str]] = []  # (текст, known|digit|unknown)
    for r in runs:
        if r.isdigit():
            pieces.append((r, "digit"))
        elif seg := _segment_run(r, multi=len(runs) > 1):
            pieces.extend((x, "known") for x in seg)
        else:
            pieces.append((r, "unknown"))
    if not any(k == "known" for _, k in pieces):
        return None
    parts: list[str] = []
    buf: list[tuple[str, str]] = []

    def flush() -> None:
        if buf:  # невідоме слово + цифри лишаємо цілим кодом моделі: "x570", "4060ti"
            parts.append("".join(x for x, _ in buf)) if any(k == "unknown" for _, k in buf) else parts.extend(x for x, _ in buf)
            buf.clear()

    for text, kind in pieces:
        if kind == "known":
            flush()
            parts.append(text)
        else:
            buf.append((text, kind))
    flush()
    return parts if len(parts) > 1 else None


def _split_glued(q: str) -> tuple[str, list[dict]]:
    out, splits = [], []
    for t in q.split():
        parts = _split_token(t)
        if parts:
            out.extend(parts)
            if any(len(x) >= 4 and x.isalpha() for x in parts):
                splits.append({"from": t, "to": " ".join(parts)})
        else:
            out.append(t)
    return " ".join(out), splits


# ---------- регулярні вирази ----------
_NUM = r"(\d{1,3}(?:[ \u00a0]\d{3})+|\d{3,6})"
_CUR = r"(?:\s*(?:грн|₴|uah))?"
_NOT_UNIT = r"(?!\d)(?!\s*(?:гб|gb|тб|tb|вт|w\b|мгц|mhz))"
RE_RANGE = re.compile(rf"(?<![\w-]){_NUM}\s*[-–]\s*{_NUM}{_CUR}{_NOT_UNIT}")
RE_MAX = re.compile(rf"(?<!\w)(?:до|<=?|не дорожче(?: ніж)?|макс\w*)\s*{_NUM}{_CUR}{_NOT_UNIT}")
RE_MIN = re.compile(rf"(?<!\w)(?:від|>=?|не дешевше(?: ніж)?|мін\w*)\s*{_NUM}{_CUR}{_NOT_UNIT}")
RE_SOCKET = re.compile(r"(?<!\w)(?:(?:am|ам)\s?([345])|lga\s?(1700|1851|1200|1151|1150))(?!\w)")
RE_DDR = re.compile(r"(?<!\w)(?:ddr|ддр)\s?([345])(?!\w)")
RE_CAP = re.compile(r"(?<!\w)(\d+(?:[.,]\d+)?)\s*(тб|tb|тера\w*|гб|gb|гіг\w*|гиг\w*)(?!\w)")
RE_WATT = re.compile(r"(?<!\w)(\d{3,4})\s*(?:вт|w|ват\w*)(?!\w)")


# одиниці й слова ціни, набрані англійською розкладкою (лише поруч із числом): "8 u," = "8 гб"
_UNIT_FIXES = [
    (re.compile(r"(?<=\d)\s*u,(?!\w)"), " гб"),
    (re.compile(r"(?<=\d)\s*n,(?!\w)"), " тб"),
    (re.compile(r"(?<=\d)\s*dn(?!\w)"), " вт"),
    (re.compile(r"(?<=\d)\s*uhy(?!\w)"), " грн"),
    (re.compile(r"(?<!\w)lj(?=\s*\d)"), "до"),
    (re.compile(r"(?<!\w)dsl(?=\s*\d)"), "від"),
]


def _fix_units(q: str) -> str:
    for rx, repl in _UNIT_FIXES:
        q = rx.sub(repl, q)
    return q


RE_STOCK = re.compile(r"(?<!\w)(?:(?:є\s+)?в\s+наявності|наявні|наявність|на\s+складі)(?!\w)")
# слова-наміри: "найдешевша відеокарта" -> категорія + сортування за ціною
_SORT_PREFIXES = [
    ("price_asc", ("дешев", "недорог", "бюджетн", "найдешевш", "економн")),
    ("price_desc", ("дорог", "топов", "флагман", "найдорожч", "преміальн", "преміум")),
    ("popular", ("популярн", "бестселер", "найкращ")),
]
SORT_LABEL = {"price_asc": "Спочатку дешевші", "price_desc": "Спочатку дорожчі", "popular": "Найпопулярніші"}


# "30 тисяч", "30 тис", "до 30к" -> 30000 (к/k лише після до/від, щоб "4k" не став ціною)
RE_THOUSANDS = re.compile(r"(?<![\w.])(\d+(?:[.,]\d+)?)\s*тис(?:яч\w*|\.)?(?!\w)")
RE_THOUSANDS_K = re.compile(r"(?<!\w)((?:до|від|<=?|>=?)\s*)(\d+(?:[.,]\d+)?)\s*[кk](?!\w)")


RE_THOUSANDS_RANGE = re.compile(
    r"(?<!\w)(?:від\s+)?(\d+(?:[.,]\d+)?)\s*(?:-|–|до)\s*(\d+(?:[.,]\d+)?)\s*тис(?:яч\w*|\.)?(?!\w)")


def _thousands(q: str) -> str:
    def conv(x: str) -> str:
        return str(int(float(x.replace(",", ".")) * 1000))
    # "від 5 до 12 тисяч" / "5-12 тис" -> діапазон у гривнях
    q = RE_THOUSANDS_RANGE.sub(lambda m: f" {conv(m.group(1))}-{conv(m.group(2))} ", q)
    q = RE_THOUSANDS.sub(lambda m: conv(m.group(1)), q)
    return RE_THOUSANDS_K.sub(lambda m: m.group(1) + conv(m.group(2)), q)


def _n(s: str) -> float:
    return float(re.sub(r"\D", "", s))


def _cut(s: str, m: re.Match) -> str:
    return f"{s[:m.start()]} {s[m.end():]}"


def _money(v: float) -> str:
    return f"{int(v):,}".replace(",", " ") + " ₴"


@dataclass
class ParsedQuery:
    raw: str
    text: str = ""
    category: str | None = None
    brand: str | None = None
    specs: dict[str, list] = field(default_factory=dict)
    price_min: float | None = None
    price_max: float | None = None
    corrected_from: str | None = None
    typos: list[dict] = field(default_factory=list)
    splits: list[dict] = field(default_factory=list)
    sort: str | None = None
    in_stock: bool = False
    llm: bool = False
    suggest_category: str | None = None  # підказка від LLM (не фільтр)
    not_sold: dict | None = None  # {"noun": ..., "related": [...]}: у каталозі такого немає (за словником)
    llm_not_sold: str | None = None  # те саме, але за підказкою LLM (менш певно)
    chips: list[dict] = field(default_factory=list)


def build_chips(pq: ParsedQuery) -> list[dict]:
    """Що саме ми зрозуміли із запиту: для рядка "Ми зрозуміли" в інтерфейсі."""
    chips: list[dict] = []
    if pq.category:
        chips.append({"kind": "category", "label": CAT_LABEL[pq.category], "value": pq.category})
    if pq.brand:
        chips.append({"kind": "brand", "label": pq.brand, "value": pq.brand})
    names = {"socket": "Сокет", "ram_type": "Памʼять", "capacity_gb": "Обсяг", "vram_gb": "Відеопамʼять",
             "wattage": "Потужність", "vendor": "Чип"}
    units = {"capacity_gb": " ГБ", "vram_gb": " ГБ", "wattage": " Вт"}
    for k, vals in pq.specs.items():
        for v in vals:
            shown = int(v) if isinstance(v, float) and v == int(v) else v
            unit = units.get(k, "")
            if k == "capacity_gb" and isinstance(v, (int, float)) and v >= 1000:
                shown, unit = f"{v / 1000:g}", " ТБ"
            chips.append({"kind": "spec", "label": f"{names.get(k, k)} {shown}{unit}", "value": v, "field": k})
    if pq.price_min is not None or pq.price_max is not None:
        lo = f"від {_money(pq.price_min)}" if pq.price_min is not None else ""
        hi = f"до {_money(pq.price_max)}" if pq.price_max is not None else ""
        chips.append({"kind": "price", "label": " ".join(x for x in (lo, hi) if x)})
    if pq.sort:
        chips.append({"kind": "sort", "label": SORT_LABEL[pq.sort]})
    if pq.in_stock:
        chips.append({"kind": "stock", "label": "В наявності"})
    if pq.text:
        chips.append({"kind": "text", "label": pq.text})
    return chips


def parse(raw: str) -> ParsedQuery:
    pq = ParsedQuery(raw=raw)
    q = normalize(raw)

    # 1. розкладка
    toks, changed = q.split(), False
    for i, t in enumerate(toks):
        if (fixed := _fix_token_layout(t)) is not None:
            toks[i], changed = fixed, True
    if changed:
        pq.corrected_from, q = q, " ".join(toks)

    q, pq.splits = _split_glued(q)  # злите написання -> окремі слова
    q = _thousands(_fix_units(q))

    # 2. ціна
    if m := RE_RANGE.search(q):
        pq.price_min, pq.price_max, q = _n(m.group(1)), _n(m.group(2)), _cut(q, m)
    else:
        if m := RE_MAX.search(q):
            pq.price_max, q = _n(m.group(1)), _cut(q, m)
        if m := RE_MIN.search(q):
            pq.price_min, q = _n(m.group(1)), _cut(q, m)

    if RE_STOCK.search(q):
        pq.in_stock, q = True, RE_STOCK.sub(" ", q)

    # 3. сокет і тип памʼяті
    for m in RE_SOCKET.finditer(q):
        pq.specs.setdefault("socket", []).append(f"AM{m.group(1)}" if m.group(1) else f"LGA{m.group(2)}")
    q = RE_SOCKET.sub(" ", q)
    for m in RE_DDR.finditer(q):
        pq.specs.setdefault("ram_type", []).append(f"DDR{m.group(1)}")
    q = RE_DDR.sub(" ", q)

    # 4. категорія і бренд (точно, потім з урахуванням помилок)
    tokens = re.findall(r"\w[\w'.+-]*", q)
    got, used = _resolve(tokens)
    for kind in ("category", "brand"):
        if hit := got[kind]:
            key, s, e, phrase, fuzzy = hit
            setattr(pq, kind, key)
            if fuzzy:
                pq.typos.append({"from": " ".join(tokens[s:e]), "to": phrase})
            if kind == "brand" and not pq.category and phrase in BRAND_IMPLIES_CATEGORY:
                pq.category = BRAND_IMPLIES_CATEGORY[phrase]
    rest_tokens = [t for i, t in enumerate(tokens) if i not in used and t not in _STOP]
    if pq.category:  # "кулер для процесора": слово "процесор" лише уточнює, а не шукається окремо
        other = [ph[0] for slug, ents in CAT_ENTRIES.items() if slug != pq.category for ph in ents if len(ph) == 1]
        rest_tokens = [t for t in rest_tokens if not any(_stem_match(t, e) for e in other)]

    kept = []
    for t in rest_tokens:  # слова-наміри ("дешевий", "топовий") -> сортування
        sort = next((srt for srt, prefs in _SORT_PREFIXES if t.startswith(prefs)), None)
        if sort:
            pq.sort = pq.sort or sort
        else:
            kept.append(t)
    rest_tokens = kept

    # 5. чіпи відеокарт: "ртх 4060", "нвідіа", "radeon" -> виробник + категорія "відеокарти"
    rest_tokens = [_CHIP_WORDS.get(t, t) for t in rest_tokens]
    tokset = set(rest_tokens)
    vendor = "NVIDIA" if tokset & _NVIDIA else ("AMD" if tokset & _RADEON else None)
    if vendor and pq.category in (None, "gpu"):
        pq.specs["vendor"] = [vendor]
        pq.category = "gpu"
        rest_tokens = [t for t in rest_tokens if t != "nvidia"]
    rest = " ".join(rest_tokens)

    # 6. м'які фільтри: потребують відомої категорії
    if m := RE_CAP.search(rest):
        if pq.category in ("gpu", "ram", "ssd", "hdd"):
            v = float(m.group(1).replace(",", "."))
            if m.group(2)[0] in "тt":
                v *= 1000
            pq.specs["vram_gb" if pq.category == "gpu" else "capacity_gb"] = [v]
            rest = _cut(rest, m)
    if (m := RE_WATT.search(rest)) and pq.category == "psu":
        pq.specs["wattage"] = [float(m.group(1))]
        rest = _cut(rest, m)
    pq.text = re.sub(r"\s+", " ", rest).strip()

    if not pq.category:  # категорії немає: можливо, це товар, якого ми не продаємо (бренд тип товару не визначає)
        if noun := _resolve_not_sold(tokens):
            pq.not_sold = {"noun": noun, "related": NOT_SOLD_RELATED[noun]}

    pq.chips = build_chips(pq)
    return pq
