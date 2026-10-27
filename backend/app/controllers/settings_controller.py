import sqlite3
from datetime import date
from app.controllers import clock
from app.controllers.mappers import to_date_or_none, to_iso
from app.controllers.month_routine_controller import create_month, new_month_for
from app.controllers.session import session
from app.core.money import round_money
from app.core.month_routine import effective_today
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings
from app.errors import NoOpenMonthError


def _read(conn: sqlite3.Connection) -> dict:
    row = settings.get(conn)
    month = months.get_open_month(conn)
    return {
        "current_salary": row["current_salary"],
        "current_month_salary": None if month is None else month["salary"],
    }


def get_settings() -> dict:
    with session() as conn:
        return _read(conn)


def save_current_salary(current_salary: float, today: date | None = None) -> dict:
    salary = round_money(current_salary)
    if salary < 0:
        raise ValueError("O salario nao pode ser negativo.")
    system_today = today if today is not None else clock.today()

    with session(immediate=True) as conn:
        settings.set_current_salary(conn, salary)
        month = months.get_open_month(conn)
        if month is not None:
            months.update_salary(conn, month["id"], salary)
        else:
            checked = to_date_or_none(settings.get(conn)["last_checked_date"])
            first_day = effective_today(system_today, checked)
            create_month(conn, new_month_for(conn, first_day.year, first_day.month, salary))
            settings.set_last_checked_date(conn, to_iso(first_day))
        return _read(conn)


def update_current_month_salary(salary: float) -> dict:
    value = round_money(salary)
    if value < 0:
        raise ValueError("O salario nao pode ser negativo.")
    with session(immediate=True) as conn:
        month = months.get_open_month(conn)
        if month is None:
            raise NoOpenMonthError()
        months.update_salary(conn, month["id"], value)
        return _read(conn)
