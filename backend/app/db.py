import psycopg
from psycopg.rows import dict_row

from .config import settings


def connect() -> psycopg.Connection:
    return psycopg.connect(settings.database_url, row_factory=dict_row)
