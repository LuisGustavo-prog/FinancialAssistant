from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.controllers import clock
from app.db.init_db import create_database
from app.main import create_app


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "app.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    monkeypatch.delenv("TIMEZONE", raising=False)
    create_database(path)
    return path


@pytest.fixture
def freeze(monkeypatch):
    """Troca o relogio do app. `freeze(2026, 10, 23)` vale 12h UTC (9h em Brasilia) desse dia."""

    def _freeze(year, month, day, hour=12):
        monkeypatch.setattr(clock, "_utc_now", lambda: datetime(year, month, day, hour, 0, tzinfo=timezone.utc))

    _freeze(2026, 10, 23)
    return _freeze


@pytest.fixture
def client(db_path, freeze, monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8080")
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def ready(client):
    """O cliente com o salario ja informado (primeiro mes aberto em 23/10/2026)."""
    response = client.put("/settings", json={"current_salary": 3000})
    assert response.status_code == 200
    return client
