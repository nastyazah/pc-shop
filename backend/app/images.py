"""Фото товарів: завантаження за data/image_urls.csv і прив'язка до товарів.

1) Заповни колонку url у data/image_urls.csv (посилання на картинку: правою кнопкою на фото -> "Копіювати адресу зображення").
2) python -m app.images
Скрипт скачає фото, стисне до WEBP (до 900 px) у frontend/public/products/<SKU>.webp і пропише image_url у БД
(тригер Outbox сам оновить індекс). Файли, покладені в цю папку вручну, теж підхоплюються.
"""
import csv
import io
import urllib.request

from PIL import Image

from .config import ROOT
from .db import connect

OUT = ROOT / "frontend/public/products"


def download(url: str, dest) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=25).read()
    im = Image.open(io.BytesIO(data))
    if im.mode in ("RGBA", "LA", "P"):  # прозорий фон -> білий
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[-1])
        im = bg
    im = im.convert("RGB")
    im.thumbnail((900, 900))
    im.save(dest, "WEBP", quality=82)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    csv_path = ROOT / "data/image_urls.csv"
    with csv_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            url, dest = (row.get("url") or "").strip(), OUT / f"{row['sku']}.webp"
            if url and not dest.exists():
                try:
                    download(url, dest)
                    print("OK  ", row["sku"])
                except Exception as exc:  # noqa: BLE001
                    print("FAIL", row["sku"], exc)

    with connect() as conn:
        n = 0
        for file in OUT.glob("*.webp"):
            n += conn.execute(
                "UPDATE products SET image_url = %s WHERE sku = %s AND image_url IS DISTINCT FROM %s",
                (f"/products/{file.name}", file.stem, f"/products/{file.name}"),
            ).rowcount
    print(f"image_url оновлено для товарів: {n}")


if __name__ == "__main__":
    main()
