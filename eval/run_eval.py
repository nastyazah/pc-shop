"""Оцінка якості пошуку на еталонному наборі запитів (без залежностей).

Запуск:  python eval/run_eval.py
Метрики: частка запитів без результатів, MRR (для expect_sku), частка товарів очікуваної категорії у топ-10.
Додавай сюди реальні формулювання з логів: це і є доказ покращення для резюме.
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

API = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
rows = [json.loads(l) for l in (Path(__file__).parent / "queries.jsonl").read_text("utf-8").splitlines() if l.strip()]

zero, rr, cat_scores = 0, [], []
for r in rows:
    url = f"{API}/api/search?{urllib.parse.urlencode({'q': r['q'], 'size': 10})}"
    items = json.load(urllib.request.urlopen(url))["items"]
    if not items:
        zero += 1
    if "expect_sku" in r:
        rank = next((i + 1 for i, it in enumerate(items) if it["sku"] == r["expect_sku"]), None)
        rr.append(1 / rank if rank else 0.0)
    if "expect_category" in r and items:
        cat_scores.append(sum(it["category"] == r["expect_category"] for it in items) / len(items))
    print(f"{'OK ' if items else 'ZERO'}  {r['q']}")

print(f"\nзапитів: {len(rows)}")
print(f"без результатів: {zero} ({zero / len(rows):.0%})")
if rr:
    print(f"MRR (за артикулом): {sum(rr) / len(rr):.2f}")
if cat_scores:
    print(f"точність категорії у топ-10: {sum(cat_scores) / len(cat_scores):.0%}")
