"""Створює індекс, аліас і search pipeline. Безпечно запускати повторно."""
import json

from ..config import INFRA, settings
from ..opensearch_client import get_client


def main() -> None:
    client = get_client()
    body = json.loads((INFRA / "opensearch/index_products.json").read_text("utf-8"))
    body["mappings"]["properties"]["embedding"]["dimension"] = settings.embedding_dim

    if not client.indices.exists(index=settings.index_name):
        client.indices.create(index=settings.index_name, body=body)
        print(f"створено індекс {settings.index_name}")
    if not client.indices.exists_alias(name=settings.index_alias):
        client.indices.put_alias(index=settings.index_name, name=settings.index_alias)
        print(f"аліас {settings.index_alias} -> {settings.index_name}")

    pipeline = json.loads((INFRA / "opensearch/search_pipeline_hybrid.json").read_text("utf-8"))
    client.transport.perform_request("PUT", f"/_search/pipeline/{settings.search_pipeline}", body=pipeline)
    print(f"search pipeline {settings.search_pipeline} оновлено")


if __name__ == "__main__":
    main()
