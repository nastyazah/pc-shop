"""Завантаження каталогу з data/catalog.yml у Postgres.

Можна запускати повторно: товари оновлюються за SKU. Тригери самі кладуть зміни в outbox,
а воркер індексує їх в OpenSearch.   Запуск:  python -m app.seed
"""
import re

import yaml
from psycopg.types.json import Jsonb

from .config import ROOT
from .db import connect


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main() -> None:
    catalog = yaml.safe_load((ROOT / "data/catalog.yml").read_text("utf-8"))
    with connect() as conn:
        root_id = conn.execute(
            "INSERT INTO categories (slug, name, position) VALUES ('components', 'Комплектуючі', 0) "
            "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id"
        ).fetchone()["id"]

        cat_ids, singular = {}, {}
        for i, c in enumerate(catalog["categories"], start=1):
            cat_ids[c["slug"]] = conn.execute(
                "INSERT INTO categories (slug, name, parent_id, position) VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name, parent_id = EXCLUDED.parent_id, "
                "position = EXCLUDED.position RETURNING id",
                (c["slug"], c["name"], root_id, i),
            ).fetchone()["id"]
            singular[c["slug"]] = c["singular"]

        brand_ids = {}
        for b in catalog["brands"]:
            brand_ids[b] = conn.execute(
                "INSERT INTO brands (slug, name) VALUES (%s, %s) "
                "ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name RETURNING id",
                (slugify(b), b),
            ).fetchone()["id"]

        count = 0
        for cat, rows in catalog["products"].items():
            for sku, brand, model, price, old, pop, specs, desc, *rest in rows:
                in_stock = rest[0] if rest else True
                name = f"{singular[cat]} {brand} {model}"
                conn.execute(
                    "INSERT INTO products (sku, name, brand_id, category_id, description, price, old_price, "
                    "in_stock, specs, popularity) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
                    "ON CONFLICT (sku) DO UPDATE SET name = EXCLUDED.name, brand_id = EXCLUDED.brand_id, "
                    "category_id = EXCLUDED.category_id, description = EXCLUDED.description, "
                    "price = EXCLUDED.price, old_price = EXCLUDED.old_price, in_stock = EXCLUDED.in_stock, "
                    "specs = EXCLUDED.specs, popularity = EXCLUDED.popularity",
                    (sku, name, brand_ids[brand], cat_ids[cat], desc, price, old, in_stock, Jsonb(specs), pop),
                )
                count += 1
    print(f"завантажено товарів: {count}")


if __name__ == "__main__":
    main()
