"""Повна переіндексація: кладемо всі товари в outbox, а воркер усе зробить сам."""
from ..db import connect


def main() -> None:
    with connect() as conn:
        n = conn.execute(
            "INSERT INTO outbox_events (aggregate_type, aggregate_id, event_type) "
            "SELECT 'product', id, 'upsert' FROM products"
        ).rowcount
    print(f"поставлено в чергу: {n}")


if __name__ == "__main__":
    main()
