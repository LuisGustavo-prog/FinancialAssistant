from collections.abc import Iterable
from datetime import date
from app.core.balance import has_leftover
from app.core.dates import month_name_pt
from app.core.models import (
    ClosedMonth,
    IncomeSource,
    LeftoverDecision,
    LeftoverOutcome,
    NewExtraIncome,
)
from app.core.money import round_money
from app.errors import LeftoverNotPendingError


def initial_decision(final_balance: float) -> LeftoverDecision | None:
    return LeftoverDecision.PENDING if has_leftover(final_balance) else None


def leftover_description(month_number: int) -> str:
    return f"Sobra de {month_name_pt(month_number)}"


def pending_leftovers(months: Iterable[ClosedMonth]) -> list[ClosedMonth]:
    pending = [m for m in months if m.leftover_decision == LeftoverDecision.PENDING]
    return sorted(pending, key=lambda m: (m.year, m.month_number))


def oldest_pending_leftover(months: Iterable[ClosedMonth]) -> ClosedMonth | None:
    pending = pending_leftovers(months)
    return pending[0] if pending else None


def decide_leftover(month: ClosedMonth, carry: bool, today: date) -> LeftoverOutcome:
    if month.leftover_decision != LeftoverDecision.PENDING:
        raise LeftoverNotPendingError(None if month.leftover_decision is None else str(month.leftover_decision))
    if not carry:
        return LeftoverOutcome(decision=LeftoverDecision.DECLINED, extra_income=None)

    income = NewExtraIncome(
        amount=round_money(month.final_balance),
        occurred_on=today,
        description=leftover_description(month.month_number),
        source=IncomeSource.LEFTOVER,
    )
    return LeftoverOutcome(decision=LeftoverDecision.CARRIED, extra_income=income)
