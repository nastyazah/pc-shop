"""Воркер Outbox: Postgres -> OpenSearch.

- FOR UPDATE SKIP LOCKED: можна запускати кілька воркерів паралельно.
- Кілька подій одного товару в пачці згортаються в одну (береться остання).
- Документ будується з ПОТОЧНОГО стану БД, тому порядок подій не ламає індекс.
- external version = id події: старіша версія ніколи не перезапише новішу.
- Помилка пачки -> rollback, attempts+1; після 10 спроб подія лишається в черзі для розбору.
"""
import logging
import signal
import time

from ..config import settings
from ..db import connect
from ..embeddings import embed_passages
from ..opensearch_client import get_client
from .document import build_document

log = logging.getLogger("outbox")
_stop = False

PRODUCT_SQL = """
SELECT p.id, p.sku, p.name, p.description, p.price, p.old_price, p.in_stock, p.specs,
       p.image_url, p.popularity, p.updated_at,
       b.name AS brand, c.slug AS category, c.name AS category_name, cp.path AS category_path
FROM products p
JOIN categories c ON c.id = p.category_id
JOIN category_paths cp ON cp.id = c.id
LEFT JOIN brands b ON b.id = p.brand_id
WHERE p.id = ANY(%s) AND p.is_active
"""


def process_once() -> int:
    client = get_client()
    claimed: list[int] = []
    try:
        with connect() as conn:  # одна транзакція: commit при успіху, rollback при помилці
            events = conn.execute(
                "SELECT id, aggregate_id FROM outbox_events "
                "WHERE processed_at IS NULL AND attempts < 10 "
                "ORDER BY id LIMIT %s FOR UPDATE SKIP LOCKED",
                (settings.worker_batch,),
            ).fetchall()
            if not events:
                return 0
            claimed = [e["id"] for e in events]

            latest: dict[int, int] = {}  # product_id -> id останньої події
            for e in events:
                latest[e["aggregate_id"]] = e["id"]
            rows = {r["id"]: r for r in conn.execute(PRODUCT_SQL, (list(latest),)).fetchall()}

            lines: list[dict] = []
            to_embed = []
            for pid, ev_id in latest.items():
                row = rows.get(pid)
                if row is None:  # видалено або деактивовано
                    lines.append({"delete": {"_index": settings.index_alias, "_id": pid,
                                             "version": ev_id, "version_type": "external"}})
                else:
                    doc, text = build_document(row)
                    to_embed.append((pid, ev_id, doc, text))

            vectors = embed_passages([t for *_, t in to_embed]) if to_embed else []
            for (pid, ev_id, doc, _), vec in zip(to_embed, vectors):
                doc["embedding"] = vec
                lines.append({"index": {"_index": settings.index_alias, "_id": pid,
                                        "version": ev_id, "version_type": "external"}})
                lines.append(doc)

            resp = client.bulk(body=lines)
            if resp.get("errors"):
                for item in resp["items"]:
                    result = next(iter(item.values()))
                    status = result.get("status", 200)
                    if status in (404, 409):  # 409: в індексі вже новіша версія; 404: видаляти нічого
                        continue
                    if status >= 300:
                        raise RuntimeError(str(result)[:500])

            conn.execute("UPDATE outbox_events SET processed_at = now() WHERE id = ANY(%s)", (claimed,))
            return len(events)
    except Exception as exc:  # noqa: BLE001
        log.exception("пачка не оброблена")
        if claimed:
            with connect() as conn:
                conn.execute(
                    "UPDATE outbox_events SET attempts = attempts + 1, last_error = %s WHERE id = ANY(%s)",
                    (str(exc)[:500], claimed),
                )
        time.sleep(2)
        return 0


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

    def _handle(*_):
        global _stop
        _stop = True

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)
    log.info("воркер запущено, індекс: %s", settings.index_alias)
    while not _stop:
        n = process_once()
        if n:
            log.info("індексовано подій: %d", n)
        else:
            time.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    main()
