import sqlite3
from datetime import date
from app.controllers.current_day import resolve_today
from app.controllers.items import expense_item
from app.controllers.mappers import to_date, to_iso
from app.controllers.session import session
from app.controllers.unset import UNSET, _Unset
from app.core.guards import check_entry_date, check_entry_edit
from app.core.money import round_money
from app.db.repositories import category_repository as categories
from app.db.repositories import expense_repository as expenses
from app.db.repositories import month_repository as months
from app.errors import CategoryInactiveError, NoOpenMonthError, NotFoundError

def _clean_description(description: str | None) -> str | None:
    if description is None:
        return None
    description = description.strip()
    return description or None

def _positive_amount(amount: float) -> float:
    value = round_money(amount)
    if value <= 0:
        raise ValueError("O valor do gasto precisa ser maior que zero.")
    return value

def _require_open_month(conn: sqlite3.Connection) -> dict:
    month = months.get_open_month(conn)
    if month is None:
        raise NoOpenMonthError()
    return month

def _chosen_category(conn: sqlite3.Connection, category_id: int | None, keep_id: int | None = None) -> int:
    if category_id is None:
        return categories.get_default_category(conn)["id"]
    category = categories.get_category(conn, category_id)
    if category is None:
        raise NotFoundError("category", category_id)
    if not category["is_active"] and category_id != keep_id:
        raise CategoryInactiveError(category_id)
    return category_id

def list_expenses() -> list[dict]:
    with session() as conn:
        month = months.get_open_month(conn)
        if month is None:
            return []
        return [expense_item(row) for row in expenses.list_expenses(conn, month["id"])]

def create_expense(
    amount: float,
    occurred_on: date | None = None,
    description: str | None = None,
    category_id: int | None = None,
    today: date | None = None,
) -> dict:
    value = _positive_amount(amount)
    with session(immediate=True) as conn:
        month = _require_open_month(conn)
        day = resolve_today(conn, today)
        entry_date = day if occurred_on is None else occurred_on
        check_entry_date(entry_date, day)
        chosen = _chosen_category(conn, category_id)
        expense_id = expenses.insert_expense(
            conn, month["id"], value, to_iso(entry_date), _clean_description(description), chosen
        )
        return expense_item(expenses.get_expense(conn, expense_id))

def update_expense(
    expense_id: int,
    amount: float | None = None,
    occurred_on: date | None = None,
    description: str | None | _Unset = UNSET,
    category_id: int | None = None,
    today: date | None = None,
) -> dict:
    with session(immediate=True) as conn:
        row = expenses.get_expense(conn, expense_id)
        if row is None:
            raise NotFoundError("expense", expense_id)
        day = resolve_today(conn, today)
        old_date = to_date(row["occurred_on"])
        new_date = old_date if occurred_on is None else occurred_on
        check_entry_edit(old_date, new_date, day)

        expenses.update_expense(
            conn,
            expense_id,
            row["amount"] if amount is None else _positive_amount(amount),
            to_iso(new_date),
            row["description"] if isinstance(description, _Unset) else _clean_description(description),
            row["category_id"]
            if category_id is None
            else _chosen_category(conn, category_id, keep_id=row["category_id"]),
        )
        return expense_item(expenses.get_expense(conn, expense_id))

def delete_expense(expense_id: int, today: date | None = None) -> None:
    with session(immediate=True) as conn:
        row = expenses.get_expense(conn, expense_id)
        if row is None:
            raise NotFoundError("expense", expense_id)
        check_entry_date(to_date(row["occurred_on"]), resolve_today(conn, today))
        expenses.delete_expense(conn, expense_id)
