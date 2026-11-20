from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]  # корінь репозиторію
INFRA = ROOT / "infra"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    database_url: str = "postgresql://shop:shop@localhost:5432/shop"
    opensearch_url: str = "http://localhost:9200"
    index_name: str = "products_v1"   # фізичний індекс (версіонований)
    index_alias: str = "products"     # з аліасом працює весь код -> reindex без простою
    search_pipeline: str = "hybrid-pipeline"
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    knn_k: int = 50
    worker_batch: int = 100
    worker_poll_seconds: float = 1.0
    cors_origins: list[str] = ["http://localhost:3000"]

    # Розбір складних запитів через LLM (необов'язково). off | openai (будь-який OpenAI-сумісний API) | anthropic
    llm_provider: str = "off"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = "http://localhost:11434/v1"  # за замовчуванням локальна Ollama
    llm_timeout: float = 4.0


settings = Settings()
