import sqlite3
import pytest
from app.db.connection import connect
from app.db.init_db import apply_schema

@pytest.fixture
def conn() -> sqlite3.Connection:
    connection = connect(":memory:")
    apply_schema(connection)
    yield connection
    connection.close()
