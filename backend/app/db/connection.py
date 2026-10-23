import sqlite3
from pathlib import Path

DEFAULT_TIMEOUT_SECONDS = 5.0

def connect(path: str | Path, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=timeout, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
