from ..search.normalize import fix_apostrophes


def build_document(row: dict) -> tuple[dict, str]:
    """Рядок Postgres -> (документ для OpenSearch, текст для ембедінгу)."""
    specs = row["specs"] or {}
    specs_text = " ".join(str(v) for v in specs.values() if not isinstance(v, (dict, list)))
    name = fix_apostrophes(row["name"])
    description = fix_apostrophes(row["description"] or "")
    category_name = fix_apostrophes(row["category_name"])

    doc = {
        "id": row["id"],
        "sku": row["sku"],
        "name": name,
        "description": description,
        "brand": row["brand"],
        "category": row["category"],
        "category_path": row["category_path"],
        "category_name": category_name,
        "price": float(row["price"]),
        "old_price": float(row["old_price"]) if row["old_price"] is not None else None,
        "in_stock": row["in_stock"],
        "popularity": row["popularity"],
        "specs": specs,
        "specs_text": specs_text,
        "image_url": row["image_url"],
        "updated_at": row["updated_at"].isoformat(),
    }
    embed_text = ". ".join(x for x in [name, row["brand"], category_name, specs_text, description] if x)
    return doc, embed_text
