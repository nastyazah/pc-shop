from functools import lru_cache

from .config import settings


@lru_cache
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


# Моделі e5 вимагають префікси: "passage: " для документів і "query: " для запитів.
def embed_passages(texts: list[str]) -> list[list[float]]:
    return _model().encode([f"passage: {t}" for t in texts], normalize_embeddings=True, batch_size=32).tolist()


def embed_query(text: str) -> list[float]:
    return _model().encode(f"query: {text}", normalize_embeddings=True).tolist()
