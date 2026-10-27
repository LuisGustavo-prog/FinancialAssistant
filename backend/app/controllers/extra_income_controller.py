import sqlite3
from datetime import date
from app.controllers.current_day import resolve_today
from app.controllers.items import extra_income_item
from app.controllers.mappers import to_date, to_iso
from app.controllers.session import session
from app.controllers.unset import UNSET, _Unset
from app.core.guards import check_entry_date, check_entry_edit, ensure_income_editable
from app.core.models import IncomeSource
from app.core.money import round_money
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months
from app.errors import NoOpenMonthError, NotFoundError


def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    description = description.strip()
    return description or None


def _positive_amount(amount: float) -> float:
    value = round_money(amount)
    if value <= 0:
        raise ValueError("O valor da renda precisa ser maior que zero.")
    return value


def _get_or_raise(conn: sqlite3.Connection, income_id: int) -> dict:
    row = incomes.get_extra_income(conn, income_id)
    if row is None:
        raise NotFoundError("extra_income", income_id)
    return row


def list_extra_incomes() -> list[dict]:
    with session() as conn:
        month = months.get_open_month(conn)
        if month is None:
            return []
        return [extra_income_item(row) for row in incomes.list_extra_incomes(conn, month["id"])]


def create_extra_income(
    amount: float,
    occurred_on: date | None = None,
    description: str | None = None,
    today: date | None = None,
) -> dict:
    value = _positive_amount(amount)
    with session(immediate=True) as conn:
        month = months.get_open_month(conn)
        if month is None:
            raise NoOpenMonthError()
        day = resolve_today(conn, today)
        entry_date = day if occurred_on is None else occurred_on
        check_entry_date(entry_date, day)
        income_id = incomes.insert_extra_income(
            conn,
            month["id"],
            value,
            to_iso(entry_date),
            _clean_description(description),
            IncomeSource.MANUAL.value,
        )
        return extra_income_item(incomes.get_extra_income(conn, income_id))


def update_extra_income(
    income_id: int,
    amount: float | None = None,
    occurred_on: date | None = None,
    description: str | None | _Unset = UNSET,
    today: date | None = None,
) -> dict:
    with session(immediate=True) as conn:
        row = _get_or_raise(conn, income_id)
        ensure_income_editable(row["source"])
        day = resolve_today(conn, today)
        old_date = to_date(row["occurred_on"])
        new_date = old_date if occurred_on is None else occurred_on
        check_entry_edit(old_date, new_date, day)

        incomes.update_extra_income(
            conn,
            income_id,
            row["amount"] if amount is None else _positive_amount(amount),
            to_iso(new_date),
            row["description"] if isinstance(description, _Unset) else _clean_description(description),
        )
        return extra_income_item(incomes.get_extra_income(conn, income_id))


def delete_extra_income(income_id: int, today: date | None = None) -> None:
    with session(immediate=True) as conn:
        row = _get_or_raise(conn, income_id)
        ensure_income_editable(row["source"])
        check_entry_date(to_date(row["occurred_on"]), resolve_today(conn, today))
        incomes.delete_extra_income(conn, income_id)
