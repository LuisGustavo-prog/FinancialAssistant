from datetime import date
import pytest
from app.core.leftover import (
    decide_leftover,
    initial_decision,
    leftover_description,
    oldest_pending_leftover,
    pending_leftovers,
)
from app.core.models import ClosedMonth, IncomeSource, LeftoverDecision
from app.errors import LeftoverNotPendingError

PENDING = LeftoverDecision.PENDING
CARRIED = LeftoverDecision.CARRIED
DECLINED = LeftoverDecision.DECLINED


def closed(year, month, balance=100.0, decision=PENDING):
    return ClosedMonth(year=year, month_number=month, final_balance=balance, leftover_decision=decision)


def test_month_with_leftover_closes_pending():
    assert initial_decision(120.50) == PENDING


@pytest.mark.parametrize("balance", [0.0, -0.01, -300.0, 5e-17, -5e-17])
def test_zero_negative_or_noise_balance_has_no_question(balance):
    assert initial_decision(balance) is None


def test_pending_leftovers_are_ordered_oldest_first():
    months = [closed(2026, 9), closed(2025, 12), closed(2026, 1)]
    assert [(m.year, m.month_number) for m in pending_leftovers(months)] == [
        (2025, 12),
        (2026, 1),
        (2026, 9),
    ]


def test_decided_months_and_months_without_leftover_are_not_pending():
    months = [
        closed(2026, 7, decision=CARRIED),
        closed(2026, 8, decision=DECLINED),
        closed(2026, 9, balance=-50.0, decision=None),
        closed(2026, 10),
    ]
    assert oldest_pending_leftover(months) == closed(2026, 10)


def test_oldest_pending_is_none_when_nothing_is_pending():
    assert oldest_pending_leftover([]) is None
    assert oldest_pending_leftover([closed(2026, 9, decision=DECLINED)]) is None


def test_carrying_creates_a_locked_extra_income_in_the_current_month():
    today = date(2026, 11, 2)
    outcome = decide_leftover(closed(2026, 10, balance=250.75), carry=True, today=today)

    assert outcome.decision == CARRIED
    income = outcome.extra_income
    assert income is not None
    assert income.amount == 250.75
    assert income.occurred_on == today
    assert income.description == "Sobra de outubro"
    assert income.source == IncomeSource.LEFTOVER


def test_late_answer_enters_the_month_of_the_answer_not_the_next_month_after_closing():
    today = date(2027, 1, 15)
    outcome = decide_leftover(closed(2026, 10), carry=True, today=today)
    assert outcome.extra_income.occurred_on == today
    assert outcome.extra_income.description == "Sobra de outubro"


def test_declining_changes_nothing_else():
    outcome = decide_leftover(closed(2026, 10), carry=False, today=date(2026, 11, 2))
    assert outcome.decision == DECLINED
    assert outcome.extra_income is None


def test_carried_amount_is_rounded():
    outcome = decide_leftover(closed(2026, 10, balance=12.340000000000001), carry=True, today=date(2026, 11, 2))
    assert outcome.extra_income.amount == 12.34


@pytest.mark.parametrize("decision", [CARRIED, DECLINED])
def test_deciding_twice_is_refused(decision):
    with pytest.raises(LeftoverNotPendingError) as info:
        decide_leftover(closed(2026, 10, decision=decision), carry=True, today=date(2026, 11, 2))
    assert info.value.code == "leftover_not_pending"
    assert info.value.params == {"decision": str(decision)}


def test_month_without_leftover_cannot_be_decided():
    with pytest.raises(LeftoverNotPendingError) as info:
        decide_leftover(closed(2026, 10, balance=-20.0, decision=None), carry=True, today=date(2026, 11, 2))
    assert info.value.params == {"decision": None}


def test_description_uses_the_portuguese_month_name():
    assert leftover_description(3) == "Sobra de março"
    assert leftover_description(12) == "Sobra de dezembro"
