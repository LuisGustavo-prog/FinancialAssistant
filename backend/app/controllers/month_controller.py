import sqlite3
from dataclasses import asdict
from datetime import date
from app.controllers.breakdown import build_breakdown, month_card_totals
from app.controllers.current_day import resolve_today
from app.controllers.items import expense_item, extra_income_item
from app.controllers.mappers import to_closed_month, to_iso
from app.controllers.session import session
from app.core.leftover import decide_leftover as decide_leftover_rule
from app.core.models import LeftoverDecision
from app.db.repositories import expense_repository as expenses
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months
from app.errors import LeftoverNotPendingError, NoOpenMonthError, NotFoundError

def _month_item(row: dict) -> dict:
    return {
        "id": row["id"],
        "year": row["year"],
        "month_number": row["month_number"],
        "status": row["status"],
        "result": row["result"],
        "final_balance": row["final_balance"],
        "leftover_decision": row["leftover_decision"],
    }

def list_months() -> list[dict]:
    with session() as conn:
        return [_month_item(row) for row in reversed(months.list_closed_months(conn))]

def _closed_month_or_raise(conn: sqlite3.Connection, month_id: int) -> dict:
    row = months.get_month(conn, month_id)
    if row is None or row["status"] != "closed":
        raise NotFoundError("month", month_id)
    return row

def get_month(month_id: int) -> dict:
    with session() as conn:
        row = _closed_month_or_raise(conn, month_id)
        return {
            **_month_item(row),
            "breakdown": asdict(build_breakdown(conn, row)),
            "expenses": [expense_item(r) for r in expenses.list_expenses(conn, month_id)],
            "extra_incomes": [
                {**extra_income_item(r), "is_editable": False}
                for r in incomes.list_extra_incomes(conn, month_id)
            ],
            "fixed_expenses": [
                {"name": r["name"], "amount": r["amount"]} for r in months.list_fixed_expenses(conn, month_id)
            ],
            "savings_quotas": [
                {"name": r["name"], "amount": r["amount"]} for r in months.list_savings_quotas(conn, month_id)
            ],
            "credit_cards": [
                {"id": card_month["credit_card_id"], "name": card_month["card_name"], "total": total}
                for card_month, total in month_card_totals(conn, month_id)
            ],
        }

def decide_leftover(month_id: int, decision: str, today: date | None = None) -> dict:
    if decision not in (LeftoverDecision.CARRIED.value, LeftoverDecision.DECLINED.value):
        raise ValueError("A decisao deve ser 'carried' ou 'declined'.")

    with session(immediate=True) as conn:
        row = months.get_month(conn, month_id)
        if row is None:
            raise NotFoundError("month", month_id)
        if row["status"] != "closed":
            raise LeftoverNotPendingError(None) 
        
        day = resolve_today(conn, today)
        outcome = decide_leftover_rule(
            to_closed_month(row), carry=decision == LeftoverDecision.CARRIED.value, today=day
        )
        if not months.set_leftover_decision(conn, month_id, outcome.decision.value):
            raise LeftoverNotPendingError(row["leftover_decision"])

        income_item = None
        if outcome.extra_income is not None:
            open_month = months.get_open_month(conn)
            if open_month is None:
                raise NoOpenMonthError()
            income = outcome.extra_income
            income_id = incomes.insert_extra_income(
                conn,
                open_month["id"],
                income.amount,
                to_iso(income.occurred_on),
                income.description,
                income.source.value,
            )
            income_item = extra_income_item(incomes.get_extra_income(conn, income_id))

        return {**_month_item(months.get_month(conn, month_id)), "extra_income": income_item}
