from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from app.core.balance import free_balance, month_result
from app.core.leftover import initial_decision
from app.core.models import (
    Breakdown,
    ClosedMonth,
    LeftoverDecision,
    MonthResult,
    NewMonthCopy,
    Notice,
    Template,
)
from app.core.notices import closing_notices
from app.core.template_sync import build_month_copies


@dataclass(frozen=True, slots=True)
class OpenMonth:
    id: int
    year: int
    month_number: int
    breakdown: Breakdown


@dataclass(frozen=True, slots=True)
class RoutineState:
    last_checked_date: date | None
    open_month: OpenMonth | None
    current_salary: float | None
    fixed_templates: Sequence[Template]
    quota_templates: Sequence[Template]
    active_card_ids: Sequence[int]

@dataclass(frozen=True, slots=True)
class MonthClosing:
    month_id: int
    final_balance: float
    result: MonthResult
    closed_at: date
    leftover_decision: LeftoverDecision | None

@dataclass(frozen=True, slots=True)
class NewMonth:
    year: int
    month_number: int
    salary: float
    fixed_expenses: list[NewMonthCopy]
    savings_quotas: list[NewMonthCopy]
    card_ids: list[int]

@dataclass(frozen=True, slots=True)
class RoutinePlan:
    today: date
    closing: MonthClosing | None
    new_month: NewMonth | None
    new_notices: list[Notice]
    last_checked_date: date


def effective_today(system_today: date, last_checked_date: date | None) -> date:
    if last_checked_date is not None and system_today < last_checked_date:
        return last_checked_date
    return system_today

def build_new_month(
    year: int,
    month_number: int,
    salary: float,
    fixed_templates: Sequence[Template],
    quota_templates: Sequence[Template],
    active_card_ids: Sequence[int],
) -> NewMonth:
    return NewMonth(
        year=year,
        month_number=month_number,
        salary=salary,
        fixed_expenses=build_month_copies(fixed_templates),
        savings_quotas=build_month_copies(quota_templates),
        card_ids=list(active_card_ids),
    )

def plan_month_routine(state: RoutineState, system_today: date) -> RoutinePlan:
    today = effective_today(system_today, state.last_checked_date)
    open_month = state.open_month

    closing: MonthClosing | None = None
    new_notices: list[Notice] = []

    if open_month is not None and (open_month.year, open_month.month_number) < (
        today.year,
        today.month,
    ):
        final_balance = free_balance(open_month.breakdown)
        decision = initial_decision(final_balance)
        closing = MonthClosing(
            month_id=open_month.id,
            final_balance=final_balance,
            result=month_result(final_balance),
            closed_at=today,
            leftover_decision=decision,
        )
        new_notices = closing_notices(
            ClosedMonth(open_month.year, open_month.month_number, final_balance, decision),
            today.year,
            today.month,
        )

    month_still_open = open_month is not None and closing is None
    new_month: NewMonth | None = None
    if not month_still_open and state.current_salary is not None:
        new_month = build_new_month(
            today.year,
            today.month,
            state.current_salary,
            state.fixed_templates,
            state.quota_templates,
            state.active_card_ids,
        )

    return RoutinePlan(
        today=today,
        closing=closing,
        new_month=new_month,
        new_notices=new_notices,
        last_checked_date=today,
    )
