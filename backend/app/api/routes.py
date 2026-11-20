import time

from fastapi import APIRouter, Query, Request

from ..config import settings
from ..search import llm, service
from ..search.builder import SearchParams

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/search")
def search(
    request: Request,
    q: str = "",
    page: int = Query(1, ge=1, le=100),
    size: int = Query(24, ge=1, le=60),
    sort: str = "relevance",
    category: str | None = None,
    brand: list[str] = Query(default=[]),
    price_min: float | None = None,
    price_max: float | None = None,
    in_stock: bool = False,
):
    # фасети характеристик приходять як spec.socket=AM5&spec.socket=AM4
    specs: dict[str, list[str]] = {}
    for key, value in request.query_params.multi_items():
        if key.startswith("spec."):
            specs.setdefault(key[5:], []).append(value)
    return service.search(SearchParams(
        q=q.strip()[:200], page=page, size=size, sort=sort, category=category, brands=brand,
        price_min=price_min, price_max=price_max, in_stock=in_stock, specs=specs,
    ))


@router.get("/suggest")
def suggest(q: str = Query("", max_length=100)):
    if len(q.strip()) < 2:
        return {"chips": [], "products": []}
    return service.suggest(q.strip())


@router.get("/llm/check")
def llm_check():
    """Діагностика LLM: чи ввімкнено, чи відповідає модель і за скільки секунд."""
    info = {"enabled": llm.enabled(), "provider": settings.llm_provider, "model": settings.llm_model,
            "base_url": settings.llm_base_url, "timeout_s": settings.llm_timeout}
    if not llm.enabled():
        return {**info, "ok": False,
                "error": "LLM вимкнено: перевірте LLM_PROVIDER і LLM_MODEL у pc-shop/.env та перезапустіть API"}
    t0 = time.perf_counter()
    try:
        reply = llm._complete("Reply with one word.", "Say hi")
    except Exception as exc:  # noqa: BLE001
        return {**info, "ok": False, "error": repr(exc), "seconds": round(time.perf_counter() - t0, 1)}
    return {**info, "ok": True, "seconds": round(time.perf_counter() - t0, 1), "reply": reply[:80], "last_search_attempt": llm.LAST}


@router.get("/llm/debug")
def llm_debug(q: str = Query(..., max_length=200)):
    """Що саме відповіла модель на запит, що з цього пройшло валідацію і скільки це зайняло."""
    if not llm.enabled():
        return {"ok": False, "error": "LLM вимкнено"}
    return llm.debug(q)
