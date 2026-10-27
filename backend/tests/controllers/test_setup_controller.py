from app.controllers.session import session
from app.controllers.setup_controller import ensure_database


def test_creates_the_database_when_missing(tmp_path, monkeypatch):
    path = tmp_path / "data" / "app.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    assert ensure_database() is True
    assert path.exists()
    with session() as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_does_nothing_when_the_database_already_exists(db_path):
    with session() as conn:
        conn.execute("UPDATE settings SET current_salary = 4200")
    assert ensure_database() is False
    with session() as conn:
        assert conn.execute("SELECT current_salary FROM settings").fetchone()[0] == 4200
