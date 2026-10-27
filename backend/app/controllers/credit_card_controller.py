import sqlite3
from collections import defaultdict
from datetime import date
from app.controllers.current_day import resolve_today
from app.controllers.mappers import to_card_entry, to_date, to_date_or_none, to_iso
from app.controllers.session import session
from app.core.credit_card import (
    card_total,
    days_since_update,
    is_outdated,
    payments_total,
    plan_payment,
    plan_reported_value_update,
)
from app.core.guards import check_entry_date, check_entry_edit
from app.core.models import CardEntryType
from app.core.money import round_money
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import month_repository as months
from app.errors import NoOpenMonthError, NotFoundError


def _entry_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "type": row["type"],
        "amount": row["amount"],
        "occurred_on": row["occurred_on"],
    }


def _item(card: dict, card_month: dict | None, entry_rows: list[dict], today: date) -> dict:
    base = {"id": card["id"], "name": card["name"], "is_active": bool(card["is_active"])}
    if card_month is None:
        return {
            **base,
            "in_current_month": False,
            "reported_value": None,
            "payments_total": None,
            "total": None,
            "updated_at": None,
            "days_since_update": None,
            "is_outdated": False,
            "entries": [],
        }

    entries = [to_card_entry(row) for row in entry_rows]
    updated_at = to_date_or_none(card_month["updated_at"])
    return {
        **base,
        "in_current_month": True,
        "reported_value": card_month["reported_value"],
        "payments_total": payments_total(entries),
        "total": card_total(card_month["reported_value"], entries),
        "updated_at": card_month["updated_at"],
        "days_since_update": days_since_update(updated_at, today),
        "is_outdated": is_outdated(updated_at, today),
        "entries": [_entry_item(row) for row in entry_rows],
    }


def _view(conn: sqlite3.Connection, card_id: int, today: date) -> dict:
    card = cards.get_card(conn, card_id)
    month = months.get_open_month(conn)
    card_month = cards.get_card_month(conn, card_id, month["id"]) if month else None
    entry_rows = cards.list_entries(conn, card_month["id"]) if card_month else []
    return _item(card, card_month, entry_rows, today)


def _month_data(conn: sqlite3.Connection, card_id: int) -> tuple[dict, dict]:
    if cards.get_card(conn, card_id) is None:
        raise NotFoundError("credit_card", card_id)
    month = months.get_open_month(conn)
    if month is None:
        raise NoOpenMonthError()
    card_month = cards.get_card_month(conn, card_id, month["id"])
    if card_month is None:
        raise NotFoundError("credit_card_month", card_id)
    return month, card_month


def list_cards(today: date | None = None) -> list[dict]:
    with session() as conn:
        day = resolve_today(conn, today)
        month = months.get_open_month(conn)
        card_months: dict[int, dict] = {}
        entries_by_card_month: dict[int, list[dict]] = defaultdict(list)
        if month is not None:
            card_months = {cm["credit_card_id"]: cm for cm in cards.list_card_months(conn, month["id"])}
            for row in cards.list_entries_by_month(conn, month["id"]):
                entries_by_card_month[row["credit_card_month_id"]].append(row)
        items = []
        for card in cards.list_cards(conn):
            card_month = card_months.get(card["id"])
            rows = entries_by_card_month[card_month["id"]] if card_month else []
            items.append(_item(card, card_month, rows, day))
        return items


def create_card(name: str, today: date | None = None) -> dict:
    with session(immediate=True) as conn:
        card_id = cards.insert_card(conn, name.strip())
        month = months.get_open_month(conn)
        if month is not None:
            cards.insert_card_month(conn, card_id, month["id"])
        return _view(conn, card_id, resolve_today(conn, today))


def update_card(
    card_id: int,
    name: str | None = None,
    is_active: bool | None = None,
    today: date | None = None,
) -> dict:
    with session(immediate=True) as conn:
        card = cards.get_card(conn, card_id)
        if card is None:
            raise NotFoundError("credit_card", card_id)
        new_active = bool(card["is_active"]) if is_active is None else is_active
        cards.update_card(conn, card_id, card["name"] if name is None else name.strip(), new_active)

        month = months.get_open_month(conn)
        if new_active and month is not None and cards.get_card_month(conn, card_id, month["id"]) is None:
            cards.insert_card_month(conn, card_id, month["id"])
        return _view(conn, card_id, resolve_today(conn, today))


def update_reported_value(
    card_id: int,
    reported_value: float,
    entry_type: str | None = None,
    today: date | None = None,
) -> dict:
    decrease_type = None if entry_type is None else CardEntryType(entry_type)
    with session(immediate=True) as conn:
        _, card_month = _month_data(conn, card_id)
        day = resolve_today(conn, today)

        new_value = round_money(reported_value)
        line = plan_reported_value_update(card_month["reported_value"], new_value, decrease_type)
        if line is not None:
            cards.insert_entry(conn, card_month["id"], line.type.value, line.amount, to_iso(day))
        cards.update_reported_value(conn, card_month["id"], new_value, to_iso(day))
        return _view(conn, card_id, day)


def register_payment(card_id: int, amount: float, today: date | None = None) -> dict:
    with session(immediate=True) as conn:
        _, card_month = _month_data(conn, card_id)
        day = resolve_today(conn, today)

        plan = plan_payment(card_month["reported_value"], amount)
        cards.insert_entry(conn, card_month["id"], plan.entry.type.value, plan.entry.amount, to_iso(day))
        cards.update_reported_value(conn, card_month["id"], plan.new_reported_value, to_iso(day))
        return _view(conn, card_id, day)


def update_entry(
    entry_id: int,
    entry_type: str | None = None,
    amount: float | None = None,
    occurred_on: date | None = None,
    today: date | None = None,
) -> dict:
    new_type = None if entry_type is None else CardEntryType(entry_type)
    with session(immediate=True) as conn:
        row = cards.get_entry(conn, entry_id)
        if row is None:
            raise NotFoundError("credit_card_entry", entry_id)
        day = resolve_today(conn, today)
        old_date = to_date(row["occurred_on"])
        new_date = old_date if occurred_on is None else occurred_on
        check_entry_edit(old_date, new_date, day)

        new_amount = row["amount"] if amount is None else round_money(amount)
        if new_amount <= 0:
            raise ValueError("O valor da linha precisa ser maior que zero.")
        cards.update_entry(
            conn,
            entry_id,
            row["type"] if new_type is None else new_type.value,
            new_amount,
            to_iso(new_date),
        )
        return _entry_item(
            next(e for e in cards.list_entries(conn, row["credit_card_month_id"]) if e["id"] == entry_id)
        )


def delete_entry(entry_id: int, today: date | None = None) -> None:
    with session(immediate=True) as conn:
        row = cards.get_entry(conn, entry_id)
        if row is None:
            raise NotFoundError("credit_card_entry", entry_id)
        check_entry_date(to_date(row["occurred_on"]), resolve_today(conn, today))
        cards.delete_entry(conn, entry_id)
