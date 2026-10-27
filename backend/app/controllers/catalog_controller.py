import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from app.controllers.mappers import to_month_copy, to_template
from app.controllers.session import session
from app.core.money import round_money
from app.core.template_sync import SyncAction, plan_template_sync
from app.db.repositories import category_repository as categories
from app.db.repositories import month_repository as months
from app.db.repositories import template_repository as templates
from app.errors import DefaultCategoryLockedError, NameAlreadyExistsError, NotFoundError


@dataclass(frozen=True, slots=True)
class _Kind:
    resource: str
    list_templates: Callable
    get_template: Callable
    insert_template: Callable
    update_template: Callable
    list_copies: Callable
    insert_copy: Callable
    update_copy: Callable
    delete_copy: Callable


_FIXED_EXPENSE = _Kind(
    resource="fixed_expense",
    list_templates=templates.list_fixed_expense_templates,
    get_template=templates.get_fixed_expense_template,
    insert_template=templates.insert_fixed_expense_template,
    update_template=templates.update_fixed_expense_template,
    list_copies=months.list_fixed_expenses,
    insert_copy=months.insert_fixed_expense,
    update_copy=months.update_fixed_expense,
    delete_copy=months.delete_fixed_expense,
)

_SAVINGS_QUOTA = _Kind(
    resource="savings_quota",
    list_templates=templates.list_savings_quota_templates,
    get_template=templates.get_savings_quota_template,
    insert_template=templates.insert_savings_quota_template,
    update_template=templates.update_savings_quota_template,
    list_copies=months.list_savings_quotas,
    insert_copy=months.insert_savings_quota,
    update_copy=months.update_savings_quota,
    delete_copy=months.delete_savings_quota,
)


def _template_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "amount": row["amount"],
        "is_active": bool(row["is_active"]),
    }


def _sync_open_month(conn: sqlite3.Connection, kind: _Kind, template_row: dict) -> None:
    month = months.get_open_month(conn)
    if month is None:
        return
    copies = [to_month_copy(row) for row in kind.list_copies(conn, month["id"])]
    plan = plan_template_sync(to_template(template_row), copies)
    if plan.action == SyncAction.CREATE:
        kind.insert_copy(conn, month["id"], template_row["id"], plan.name, plan.amount)
    elif plan.action == SyncAction.UPDATE:
        kind.update_copy(conn, plan.copy_id, plan.name, plan.amount)
    elif plan.action == SyncAction.DELETE:
        kind.delete_copy(conn, plan.copy_id)


def _list_templates(kind: _Kind) -> list[dict]:
    with session() as conn:
        return [_template_item(row) for row in kind.list_templates(conn)]


def _create_template(kind: _Kind, name: str, amount: float) -> dict:
    with session(immediate=True) as conn:
        template_id = kind.insert_template(conn, name.strip(), round_money(amount))
        row = kind.get_template(conn, template_id)
        _sync_open_month(conn, kind, row)
        return _template_item(row)


def _update_template(
    kind: _Kind,
    template_id: int,
    name: str | None,
    amount: float | None,
    is_active: bool | None,
) -> dict:
    with session(immediate=True) as conn:
        row = kind.get_template(conn, template_id)
        if row is None:
            raise NotFoundError(kind.resource, template_id)
        kind.update_template(
            conn,
            template_id,
            row["name"] if name is None else name.strip(),
            row["amount"] if amount is None else round_money(amount),
            bool(row["is_active"]) if is_active is None else is_active,
        )
        updated = kind.get_template(conn, template_id)
        _sync_open_month(conn, kind, updated)
        return _template_item(updated)


def list_fixed_expenses() -> list[dict]:
    return _list_templates(_FIXED_EXPENSE)


def create_fixed_expense(name: str, amount: float) -> dict:
    return _create_template(_FIXED_EXPENSE, name, amount)


def update_fixed_expense(
    template_id: int,
    name: str | None = None,
    amount: float | None = None,
    is_active: bool | None = None,
) -> dict:
    return _update_template(_FIXED_EXPENSE, template_id, name, amount, is_active)


def list_savings_quotas() -> list[dict]:
    return _list_templates(_SAVINGS_QUOTA)


def create_savings_quota(name: str, amount: float) -> dict:
    return _create_template(_SAVINGS_QUOTA, name, amount)


def update_savings_quota(
    template_id: int,
    name: str | None = None,
    amount: float | None = None,
    is_active: bool | None = None,
) -> dict:
    return _update_template(_SAVINGS_QUOTA, template_id, name, amount, is_active)


def _category_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "is_default": bool(row["is_default"]),
        "is_active": bool(row["is_active"]),
    }


def _ensure_name_is_free(conn: sqlite3.Connection, name: str, ignore_id: int | None = None) -> None:
    for row in categories.list_categories(conn):
        if row["id"] != ignore_id and row["name"].casefold() == name.casefold():
            raise NameAlreadyExistsError(name)


def list_categories() -> list[dict]:
    with session() as conn:
        return [_category_item(row) for row in categories.list_categories(conn)]


def create_category(name: str) -> dict:
    clean_name = name.strip()
    with session(immediate=True) as conn:
        _ensure_name_is_free(conn, clean_name)
        category_id = categories.insert_category(conn, clean_name)
        return _category_item(categories.get_category(conn, category_id))


def update_category(category_id: int, name: str | None = None, is_active: bool | None = None) -> dict:
    with session(immediate=True) as conn:
        row = categories.get_category(conn, category_id)
        if row is None:
            raise NotFoundError("category", category_id)

        new_name = row["name"] if name is None else name.strip()
        new_active = bool(row["is_active"]) if is_active is None else is_active
        if row["is_default"] and not new_active:
            raise DefaultCategoryLockedError()
        if new_name != row["name"]:
            _ensure_name_is_free(conn, new_name, ignore_id=category_id)

        categories.update_category(conn, category_id, new_name, new_active)
        return _category_item(categories.get_category(conn, category_id))
