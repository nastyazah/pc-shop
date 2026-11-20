# Ядро — магазин комплектуючих з розумним пошуком

Postgres (джерело правди) → Outbox → воркер → OpenSearch (BM25 + kNN гібрид) → FastAPI → Next.js.

## Запуск

```bash
# 0. Лише Linux/WSL: OpenSearch потребує більшого ліміту mmap, інакше контейнер впаде
sudo sysctl -w vm.max_map_count=262144

# 1. Змінні середовища
cp .env.example .env

# 2. Postgres + OpenSearch (перший раз збирається образ із плагіном analysis-ukrainian)
docker compose up -d --build

# 3. Бекенд: віртуальне середовище та залежності
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # легкий PyTorch без CUDA
pip install -r requirements.txt

# 4. Створити індекс, аліас і search pipeline в OpenSearch
python -m app.indexing.setup_index

# 4b. Завантажити каталог (data/catalog.yml) у Postgres; безпечно запускати повторно
python -m app.seed

# 5. Воркер Outbox (окремий термінал): індексує товари з Postgres в OpenSearch
python -m app.indexing.outbox_worker

# 6. API (ще один термінал, теж з активованим .venv)
uvicorn app.main:app --reload --port 8000

# 7. Фронтенд (ще один термінал)
cd frontend
cp .env.local.example .env.local
npm install
npm run dev                        # http://localhost:3000
```

## Корисні команди

```bash
# перевірити, як аналізатор розбирає запит (синоніми, стоп-слова, нормалізація)
curl -s localhost:9200/products_v1/_analyze -H 'Content-Type: application/json' \
  -d '{"analyzer":"uk_search","text":"хочу материнку"}'

# переіндексувати все (кладе всі товари в outbox, воркер підхопить)
python -m app.indexing.reindex

# оцінка якості пошуку на еталонному наборі
python eval/run_eval.py
```

## Де що

- `infra/opensearch/index_products.json` — аналізатори (нормалізація апострофів, стоп-слова, синоніми), мапінг, вектори
- `infra/opensearch/analysis/` — `stopwords_uk.txt`, `synonyms_uk.txt`
- `infra/opensearch/search_pipeline_hybrid.json` — ваги BM25 / kNN
- `infra/postgres/init/` — схема, outbox і тригери
- `data/catalog.yml` — каталог товарів; `python -m app.seed` завантажує його в БД
- `data/image_urls.csv` + `python -m app.images` — фото товарів
- `backend/app/search/query_parser.py` — розуміння запиту (діалекти, розкладка, атрибути, ціна)
- `backend/app/search/builder.py` — гібридний запит і фасети
- `backend/app/indexing/outbox_worker.py` — синхронізація Postgres → OpenSearch
- `frontend/src/app/globals.css` — дизайн-токени палітри

## Як працює розуміння запиту

Шари від дешевих до дорогих (кожен наступний працює лише там, де попередні не впоралися):

1. нормалізація, виправлення розкладки (в обидва боки), розбиття злитих слів;
2. словники (категорії, бренди) за основою слова та нечіткі збіги: опечатки (відстань Дамерау-Левенштейна) і звукова форма («аператива»);
3. регулярні вирази: ціна, обсяг, сокет, DDR, «найдешевша», «в наявності»;
4. необов'язково: LLM для складних фраз (див. нижче);
5. гібридний пошук: BM25 (артикул, назва, морфологія, синоніми) + вектори.

### LLM-розбір запиту (необов'язково)

LLM лише пропонує структуру (категорія, бренд, фільтри, ціна, сортування, ключові слова), а код перевіряє її за білими списками.
Правила мають пріоритет, LLM заповнює тільки прогалини. Викликається лише для запитів, які правила не зрозуміли; результат кешується.
Без налаштувань усе працює без LLM.

```bash
# варіант 1: локально й безкоштовно через Ollama (https://ollama.com)
ollama pull qwen2.5:7b
# у .env:  LLM_PROVIDER=openai  LLM_MODEL=qwen2.5:7b  LLM_BASE_URL=http://localhost:11434/v1

# варіант 2: Claude API
# у .env:  LLM_PROVIDER=anthropic  LLM_MODEL=claude-haiku-5-5  LLM_API_KEY=<ваш ключ>

# після зміни .env перезапустити API
```

Приклад: «щоб тягнула кіберпанк до 30 тисяч» -> відеокарти, до 30 000 ₴, ключові слова «кіберпанк».

## Відомі обмеження (наступні кроки)

- Плагін `analysis-ukrainian` не дає доступу до окремих фільтрів, тому морфологія живе в підполі `*.morph`, а власні стоп-слова/синоніми/нормалізація — в основних полях.
- Фасети рахуються по всій видачі (без «виключення власного фільтра»).
- Немає сторінки товару, кошика, оформлення замовлення.
