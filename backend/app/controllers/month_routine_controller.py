import sqlite3
from dataclasses import dataclass
from datetime import date
from app.controllers import clock
from app.controllers.breakdown import build_breakdown
from app.controllers.mappers import (
    notices_from_json,
    notices_to_json,
    to_date_or_none,
    to_iso,
    to_template,
)
from app.controllers.session import session
from app.core.month_routine import (
    NewMonth,
    OpenMonth,
    RoutinePlan,
    RoutineState,
    build_new_month,
    plan_month_routine,
)
from app.core.notices import store_notices
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings
from app.db.repositories import template_repository as templates


@dataclass(frozen=True, slots=True)
class RoutineResult:
    today: date
    closed_month_id: int | None
    created_month_id: int | None


def run(today: date | None = None) -> RoutineResult:
    system_today = today if today is not None else clock.today()

    with session() as conn:
        last_checked = settings.get(conn)["last_checked_date"]
    if last_checked == to_iso(system_today):
        return RoutineResult(system_today, None, None)

    with session(immediate=True) as conn:
        state = _read_state(conn)
        plan = plan_month_routine(state, system_today)
        closed_id, created_id = _apply(conn, plan)
    return RoutineResult(plan.today, closed_id, created_id)


def _read_state(conn: sqlite3.Connection) -> RoutineState:
    settings_row = settings.get(conn)
    month_row = months.get_open_month(conn)
    open_month = None
    if month_row is not None:
        open_month = OpenMonth(
            id=month_row["id"],
            year=month_row["year"],
            month_number=month_row["month_number"],
            breakdown=build_breakdown(conn, month_row),
        )
    return RoutineState(
        last_checked_date=to_date_or_none(settings_row["last_checked_date"]),
        open_month=open_month,
        current_salary=settings_row["current_salary"],
        fixed_templates=[to_template(r) for r in templates.list_fixed_expense_templates(conn)],
        quota_templates=[to_template(r) for r in templates.list_savings_quota_templates(conn)],
        active_card_ids=cards.list_active_card_ids(conn),
    )


def _apply(conn: sqlite3.Connection, plan: RoutinePlan) -> tuple[int | None, int | None]:
    closed_id: int | None = None
    created_id: int | None = None

    if plan.closing is not None:
        closing = plan.closing
        closed = months.close_month(
            conn,
            closing.month_id,
            closing.final_balance,
            closing.result.value,
            to_iso(closing.closed_at),
            None if closing.leftover_decision is None else closing.leftover_decision.value,
        )
        if not closed:
            raise RuntimeError(f"O mes {closing.month_id} nao estava aberto ao fechar.")
        closed_id = closing.month_id

    if plan.new_month is not None:
        created_id = create_month(conn, plan.new_month)

    if plan.new_notices:
        existing = notices_from_json(settings.get(conn)["pending_notices"])
        stored = store_notices(existing, plan.new_notices)
        settings.set_pending_notices(conn, notices_to_json(stored))

    settings.set_last_checked_date(conn, to_iso(plan.last_checked_date))
    return closed_id, created_id


def create_month(conn: sqlite3.Connection, new_month: NewMonth) -> int:
    month_id = months.create_month(conn, new_month.year, new_month.month_number, new_month.salary)
    for copy in new_month.fixed_expenses:
        months.insert_fixed_expense(conn, month_id, copy.template_id, copy.name, copy.amount)
    for copy in new_month.savings_quotas:
        months.insert_savings_quota(conn, month_id, copy.template_id, copy.name, copy.amount)
    for card_id in new_month.card_ids:
        cards.insert_card_month(conn, card_id, month_id)
    return month_id


def new_month_for(conn: sqlite3.Connection, year: int, month_number: int, salary: float) -> NewMonth:
    return build_new_month(
        year,
        month_number,
        salary,
        [to_template(r) for r in templates.list_fixed_expense_templates(conn)],
        [to_template(r) for r in templates.list_savings_quota_templates(conn)],
        cards.list_active_card_ids(conn),
    )
