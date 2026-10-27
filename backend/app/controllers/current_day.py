import sqlite3
from datetime import date
from app.controllers import clock
from app.controllers.mappers import to_date_or_none
from app.core.month_routine import effective_today
from app.db.repositories import settings_repository as settings


def resolve_today(conn: sqlite3.Connection, today: date | None = None) -> date:
    system_today = today if today is not None else clock.today()
    last_checked = to_date_or_none(settings.get(conn)["last_checked_date"])
    return effective_today(system_today, last_checked)
