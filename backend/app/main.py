import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from .api.routes import router
from .config import settings

log = logging.getLogger("api")


def _warmup() -> None:
    """Завантажуємо модель ембедінгів і прогріваємо kNN, щоб перший запит користувача не чекав."""
    from .search import llm, service
    from .search.builder import SearchParams

    service.search(SearchParams(q="розігрів пошуку"))
    if llm.enabled():  # модель вантажиться у фоні, старт API не блокується
        def _llm() -> None:
            try:
                llm._complete("Reply with one word.", "hi")
                log.warning("LLM прогрітий")
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM не відповів під час прогріву: %s", exc)

        threading.Thread(target=_llm, daemon=True).start()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await run_in_threadpool(_warmup)
        log.warning("пошук прогрітий")
    except Exception:  # noqa: BLE001 - API має стартувати, навіть якщо OpenSearch ще піднімається
        log.exception("прогрів не вдався")
    yield


app = FastAPI(title="PC shop search API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET"], allow_headers=["*"]
)
app.include_router(router)
