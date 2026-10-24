"""Abre conexoes SQLite e controla transacoes. E o unico arquivo que configura PRAGMAs."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 5.0


def connect(path: str | Path, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> sqlite3.Connection:
    """Abre uma conexao com chaves estrangeiras ligadas.

    isolation_level=None desliga as transacoes implicitas do Python: quem
    precisar de transacao usa o auxiliar `transaction`, que escreve BEGIN,
    COMMIT e ROLLBACK de forma explicita.
    """
    conn = sqlite3.connect(path, timeout=timeout, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection, immediate: bool = False) -> Iterator[sqlite3.Connection]:
    """Executa um bloco em uma transacao: COMMIT se terminar bem, ROLLBACK se der erro.

    - Comum (BEGIN): para casos de uso que so leem ou que escrevem sem disputa.
    - `immediate=True` (BEGIN IMMEDIATE): pega a trava de escrita logo no inicio.
      E o modo da rotina do mes, para que duas requisicoes ao mesmo tempo nao
      fechem o mes duas vezes: a segunda espera (ate o timeout) e depois ve o
      estado ja atualizado. Nao ha transacao dentro de transacao.
    """
    conn.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
    try:
        yield conn
        conn.execute("COMMIT")
    except BaseException:
        if conn.in_transaction:
            conn.execute("ROLLBACK")
        raise
