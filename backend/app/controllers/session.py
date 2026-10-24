"""Abre a conexao com o banco da configuracao e envolve um caso de uso em uma transacao."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from app.config import load_config
from app.db.connection import connect, transaction

def open_connection() -> sqlite3.Connection:
    path = Path(load_config().database_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Banco de dados nao encontrado: {path}. Crie com: python -m app.db.init_db"
        )
    return connect(path)

@contextmanager
def session(immediate: bool = False) -> Iterator[sqlite3.Connection]:
    conn = open_connection()
    try:
        with transaction(conn, immediate=immediate):
            yield conn
    finally:
        conn.close()
