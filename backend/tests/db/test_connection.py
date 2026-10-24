import sqlite3
import pytest
from app.db.connection import connect, transaction
from app.db.init_db import apply_schema

@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "test.db"
    conn = connect(path)
    apply_schema(conn)
    conn.close()
    return path

def count_months(path) -> int:
    reader = connect(path)
    try:
        return reader.execute("SELECT COUNT(*) FROM month").fetchone()[0]
    finally:
        reader.close()

def insert_open_month(conn):
    conn.execute(
        "INSERT INTO month (year, month_number, status, salary) VALUES (2026, 10, 'open', 3000)"
    )

def test_commit_saves_the_changes(db_path):
    conn = connect(db_path)
    with transaction(conn):
        insert_open_month(conn)
    assert conn.in_transaction is False
    conn.close()
    assert count_months(db_path) == 1

def test_error_inside_the_block_rolls_everything_back(db_path):
    conn = connect(db_path)
    with pytest.raises(RuntimeError):
        with transaction(conn):
            insert_open_month(conn)
            raise RuntimeError("falha no meio do caso de uso")
    assert conn.in_transaction is False
    conn.close()
    assert count_months(db_path) == 0

def test_database_error_rolls_back_the_earlier_writes_of_the_same_block(db_path):
    conn = connect(db_path)
    with pytest.raises(sqlite3.IntegrityError):
        with transaction(conn):
            insert_open_month(conn)
            conn.execute(  # segundo mes aberto: o schema recusa
                "INSERT INTO month (year, month_number, status, salary) VALUES (2026, 11, 'open', 1)"
            )
    conn.close()
    assert count_months(db_path) == 0

def test_the_block_receives_the_same_connection(db_path):
    conn = connect(db_path)
    with transaction(conn) as inside:
        assert inside is conn
    conn.close()

def test_immediate_transaction_blocks_a_second_writer_until_it_finishes(db_path):
    first = connect(db_path)
    second = connect(db_path, timeout=0.1)
    with transaction(first, immediate=True):
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            second.execute("BEGIN IMMEDIATE")
    with transaction(second, immediate=True):
        insert_open_month(second)
    first.close()
    second.close()
    assert count_months(db_path) == 1

def test_a_reader_still_works_while_an_immediate_transaction_is_open(db_path):
    writer = connect(db_path)
    with transaction(writer, immediate=True):
        insert_open_month(writer)
        assert count_months(db_path) == 0  
    writer.close()
    assert count_months(db_path) == 1

def test_transactions_cannot_be_nested(db_path):
    conn = connect(db_path)
    with pytest.raises(sqlite3.OperationalError):
        with transaction(conn):
            with transaction(conn):
                pass
    assert conn.in_transaction is False
    conn.close()
