from datetime import date
from app.controllers.current_day import resolve_today
from app.controllers.session import session
from app.db.repositories import settings_repository as settings


def test_without_a_stored_date_the_given_date_is_used(db_path):
    with session() as conn:
        assert resolve_today(conn, date(2026, 10, 23)) == date(2026, 10, 23)


def test_a_clock_that_went_back_uses_the_stored_date(db_path):
    with session() as conn:
        settings.set_last_checked_date(conn, "2026-11-05")
        assert resolve_today(conn, date(2026, 10, 20)) == date(2026, 11, 5)
        assert resolve_today(conn, date(2026, 11, 9)) == date(2026, 11, 9)
