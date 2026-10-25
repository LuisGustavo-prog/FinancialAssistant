import sqlite3
from dataclasses import asdict
from datetime import date
from app.controllers.breakdown import build_breakdown
from app.controllers.current_day import resolve_today
from app.controllers.items import expense_item
from app.controllers.mappers import (
    notices_from_json,
    notices_to_json,
    to_closed_month,
    to_date_or_none,
)
from app.controllers.session import session
from app.core.balance import free_balance
from app.core.dates import days_left_in_month
from app.core.leftover import oldest_pending_leftover
from app.core.models import CardStatus, Notice
from app.core.money import round_money
from app.core.notices import active_notices, dismiss_stored_notice
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import expense_repository as expenses
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings

RECENT_EXPENSES_LIMIT = 5

def _notice_item(notice: Notice) -> dict:
    return {"id": notice.id, "code": notice.code.value, "params": notice.params}

def _pending_leftover(conn: sqlite3.Connection) -> dict | None:
    rows = months.list_closed_months(conn)
    oldest = oldest_pending_leftover([to_closed_month(row) for row in rows])
    if oldest is None:
        return None
    row = next(r for r in rows if (r["year"], r["month_number"]) == (oldest.year, oldest.month_number))
    return {
        "month_id": row["id"],
        "year": row["year"],
        "month_number": row["month_number"],
        "amount": round_money(oldest.final_balance),
    }

def get_home(today: date | None = None) -> dict:
    with session() as conn:
        day = resolve_today(conn, today)
        month = months.get_open_month(conn)
        if month is None:
            return {"status": "needs_setup"}

        breakdown = build_breakdown(conn, month)
        active_cards = [
            CardStatus(name=row["card_name"], updated_at=to_date_or_none(row["updated_at"]))
            for row in cards.list_card_months(conn, month["id"])
            if row["is_active"]
        ]
        stored = notices_from_json(settings.get(conn)["pending_notices"])

        return {
            "status": "ok",
            "month": {
                "id": month["id"],
                "year": month["year"],
                "month_number": month["month_number"],
                "status": month["status"],
                "days_left": days_left_in_month(day),
            },
            "free_balance": free_balance(breakdown),
            "breakdown": asdict(breakdown),
            "notices": [_notice_item(n) for n in active_notices(stored, day, active_cards)],
            "pending_leftover": _pending_leftover(conn),
            "recent_expenses": [
                expense_item(row)
                for row in expenses.list_recent_expenses(conn, month["id"], RECENT_EXPENSES_LIMIT)
            ],
        }

def dismiss_notice(notice_id: int) -> None:
    with session(immediate=True) as conn:
        stored = notices_from_json(settings.get(conn)["pending_notices"])
        remaining = dismiss_stored_notice(stored, notice_id)
        if len(remaining) != len(stored):
            settings.set_pending_notices(conn, notices_to_json(remaining))
