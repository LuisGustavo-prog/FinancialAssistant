import sqlite3
import pytest
from app.controllers.session import open_connection, session

def count_months() -> int:
    with session() as conn:
        return conn.execute("SELECT COUNT(*) FROM month").fetchone()[0]

def test_missing_database_fails_with_a_clear_message_and_does_not_create_the_file(tmp_path, monkeypatch):
    path = tmp_path / "missing.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    with pytest.raises(FileNotFoundError, match="init_db"):
        open_connection()
    assert not path.exists()

def test_session_commits_when_the_block_succeeds(db_path):
    with session() as conn:
        conn.execute("INSERT INTO month (year, month_number, status, salary) VALUES (2026, 10, 'open', 3000)")
    assert count_months() == 1

def test_session_rolls_back_when_the_block_fails(db_path):
    with pytest.raises(RuntimeError):
        with session() as conn:
            conn.execute("INSERT INTO month (year, month_number, status, salary) VALUES (2026, 10, 'open', 3000)")
            raise RuntimeError("falha")
    assert count_months() == 0

def test_session_closes_the_connection(db_path):
    with session() as conn:
        pass
    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")

def test_session_closes_the_connection_even_after_an_error(db_path):
    holder = {}
    with pytest.raises(RuntimeError):
        with session() as conn:
            holder["conn"] = conn
            raise RuntimeError("falha")
    with pytest.raises(sqlite3.ProgrammingError):
        holder["conn"].execute("SELECT 1")

def test_session_uses_the_database_of_the_configuration(db_path):
    with session() as conn:
        path = conn.execute("PRAGMA database_list").fetchone()["file"]
    assert path.endswith("app.db")
