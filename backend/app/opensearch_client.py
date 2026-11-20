from functools import lru_cache

from opensearchpy import OpenSearch

from .config import settings


@lru_cache
def get_client() -> OpenSearch:
    return OpenSearch(hosts=[settings.opensearch_url], timeout=30)
