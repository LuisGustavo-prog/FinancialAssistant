from datetime import date
import pytest
from app.core.models import (
    Breakdown,
    LeftoverDecision,
    MonthResult,
    NewMonthCopy,
    Notice,
    NoticeCode,
    Template,
)
from app.core.month_routine import (
    NewMonth,
    OpenMonth,
    RoutineState,
    build_new_month,
    effective_today,
    plan_month_routine,
)

def breakdown(salary=3000.0, fixed=1200.0, quotas=300.0, debit=450.50, card=800.25, extra=0.0):
    return Breakdown(
        salary=salary,
        extra_incomes=extra,
        fixed_expenses=fixed,
        savings_quotas=quotas,
        debit_expenses=debit,
        credit_card_total=card,
    )

def open_month(id=1, year=2026, month=10, **breakdown_values):
    return OpenMonth(id=id, year=year, month_number=month, breakdown=breakdown(**breakdown_values))

FIXED = [
    Template(1, "Aluguel", 1200.0, True),
    Template(2, "Academia", 99.9, False),
    Template(3, "Internet", 100.0, True),
]
QUOTAS = [Template(10, "Reserva", 300.0, True)]

def make_state(open_month_=None, last_checked=None, salary=3500.0, cards=(7, 8)):
    return RoutineState(
        last_checked_date=last_checked,
        open_month=open_month_,
        current_salary=salary,
        fixed_templates=FIXED,
        quota_templates=QUOTAS,
        active_card_ids=list(cards),
    )

@pytest.mark.parametrize(
    ("system", "last_checked", "expected"),
    [
        (date(2026, 10, 23), None, date(2026, 10, 23)),
        (date(2026, 10, 23), date(2026, 10, 20), date(2026, 10, 23)),
        (date(2026, 10, 23), date(2026, 10, 23), date(2026, 10, 23)),
        (date(2026, 10, 15), date(2026, 10, 23), date(2026, 10, 23)),  
    ],
)
def test_effective_today(system, last_checked, expected):
    assert effective_today(system, last_checked) == expected

def test_open_month_that_is_the_current_month_changes_nothing_but_the_date():
    today = date(2026, 10, 23)
    plan = plan_month_routine(make_state(open_month()), today)
    assert plan.closing is None
    assert plan.new_month is None
    assert plan.new_notices == []
    assert plan.today == today
    assert plan.last_checked_date == today

def test_month_turn_closes_the_old_month_and_creates_the_new_one():
    today = date(2026, 11, 1)
    plan = plan_month_routine(make_state(open_month(id=5)), today)

    closing = plan.closing
    assert closing.month_id == 5
    assert closing.final_balance == 249.25
    assert closing.result == MonthResult.GREEN
    assert closing.leftover_decision == LeftoverDecision.PENDING
    assert closing.closed_at == today

    assert plan.new_month == NewMonth(
        year=2026,
        month_number=11,
        salary=3500.0,
        fixed_expenses=[
            NewMonthCopy(1, "Aluguel", 1200.0),
            NewMonthCopy(3, "Internet", 100.0),
        ],
        savings_quotas=[NewMonthCopy(10, "Reserva", 300.0)],
        card_ids=[7, 8],
    )
    assert plan.new_notices == []  
    assert plan.last_checked_date == today

def test_new_month_salary_comes_from_the_current_salary_not_the_old_month():
    plan = plan_month_routine(
        make_state(open_month(salary=3000.0), salary=4200.0), date(2026, 11, 1)
    )
    assert plan.new_month.salary == 4200.0

def test_new_month_has_no_copies_when_there_are_no_active_templates_or_cards():
    state = RoutineState(None, open_month(), 3000.0, [], [], [])
    plan = plan_month_routine(state, date(2026, 11, 1))
    assert plan.new_month.fixed_expenses == []
    assert plan.new_month.savings_quotas == []
    assert plan.new_month.card_ids == []

def test_negative_month_is_red_without_question_and_with_a_stored_notice():
    state = make_state(open_month(salary=1000.0, fixed=800.0, quotas=0.0, debit=300.0, card=0.0))
    plan = plan_month_routine(state, date(2026, 11, 1))
    assert plan.closing.final_balance == -100.0
    assert plan.closing.result == MonthResult.RED
    assert plan.closing.leftover_decision is None
    assert plan.new_notices == [
        Notice(
            id=None,
            code=NoticeCode.MONTH_CLOSED_NEGATIVE,
            params={"closed_month": "2026-10", "current_month": "2026-11", "final_balance": -100.0},
        )
    ]

def test_zero_balance_is_green_without_question():
    state = make_state(open_month(salary=0.3, fixed=0.0, quotas=0.0, debit=0.1 + 0.2, card=0.0))
    plan = plan_month_routine(state, date(2026, 11, 1))
    assert plan.closing.final_balance == 0.0
    assert plan.closing.result == MonthResult.GREEN
    assert plan.closing.leftover_decision is None
    assert plan.new_notices == []

def test_year_boundary_december_to_january():
    plan = plan_month_routine(make_state(open_month(year=2026, month=12)), date(2027, 1, 1))
    assert plan.closing is not None
    assert (plan.new_month.year, plan.new_month.month_number) == (2027, 1)
    assert plan.new_notices == []

def test_months_without_use_are_not_created_and_generate_a_notice():
    today = date(2027, 1, 15)
    plan = plan_month_routine(make_state(open_month(year=2026, month=10)), today)

    assert plan.closing.closed_at == today
    assert (plan.new_month.year, plan.new_month.month_number) == (2027, 1)
    assert plan.new_notices == [
        Notice(id=None, code=NoticeCode.UNUSED_MONTHS, params={"months": ["2026-11", "2026-12"]})
    ]

def test_negative_month_after_a_long_absence_generates_both_notices():
    state = make_state(open_month(salary=1000.0, fixed=1500.0, quotas=0.0, debit=0.0, card=0.0))
    plan = plan_month_routine(state, date(2026, 12, 10))
    assert [n.code for n in plan.new_notices] == [
        NoticeCode.MONTH_CLOSED_NEGATIVE,
        NoticeCode.UNUSED_MONTHS,
    ]
    assert plan.new_notices[0].params["current_month"] == "2026-12"
    assert plan.new_notices[1].params == {"months": ["2026-11"]}

def test_clock_going_back_never_reopens_or_recreates_a_closed_month():
    state = make_state(open_month(id=2, year=2026, month=11), last_checked=date(2026, 11, 5))
    plan = plan_month_routine(state, date(2026, 10, 20))
    assert plan.today == date(2026, 11, 5)
    assert plan.closing is None
    assert plan.new_month is None
    assert plan.new_notices == []
    assert plan.last_checked_date == date(2026, 11, 5)

def test_clock_going_back_inside_the_month_keeps_the_stored_date():
    state = make_state(open_month(), last_checked=date(2026, 10, 31))
    plan = plan_month_routine(state, date(2026, 10, 15))
    assert plan.last_checked_date == date(2026, 10, 31)
    assert plan.closing is None

def test_the_stored_date_can_trigger_the_turn_when_the_clock_went_back_after_it():
    state = make_state(open_month(year=2026, month=9), last_checked=date(2026, 10, 31))
    plan = plan_month_routine(state, date(2026, 10, 15))
    assert plan.today == date(2026, 10, 31)
    assert plan.closing.closed_at == date(2026, 10, 31)
    assert (plan.new_month.year, plan.new_month.month_number) == (2026, 10)

def test_first_run_without_salary_does_not_create_a_month():
    plan = plan_month_routine(make_state(None, salary=None), date(2026, 10, 23))
    assert plan.closing is None
    assert plan.new_month is None
    assert plan.new_notices == []
    assert plan.last_checked_date == date(2026, 10, 23)

def test_no_open_month_but_salary_configured_creates_the_current_month():
    plan = plan_month_routine(make_state(None), date(2026, 10, 23))
    assert plan.closing is None
    assert (plan.new_month.year, plan.new_month.month_number) == (2026, 10)
    assert plan.new_notices == []

def test_open_month_with_salary_missing_is_closed_but_no_month_is_created():
    plan = plan_month_routine(make_state(open_month(), salary=None), date(2026, 11, 1))
    assert plan.closing is not None
    assert plan.new_month is None

def test_running_the_routine_twice_changes_nothing_the_second_time():
    today = date(2026, 11, 1)
    first = plan_month_routine(make_state(open_month(id=1)), today)

    after = RoutineState(
        last_checked_date=first.last_checked_date,
        open_month=OpenMonth(
            id=2,
            year=first.new_month.year,
            month_number=first.new_month.month_number,
            breakdown=breakdown(salary=first.new_month.salary, fixed=0.0, quotas=0.0, debit=0.0, card=0.0),
        ),
        current_salary=3500.0,
        fixed_templates=FIXED,
        quota_templates=QUOTAS,
        active_card_ids=[7, 8],
    )
    second = plan_month_routine(after, today)
    assert second.closing is None
    assert second.new_month is None
    assert second.new_notices == []

def test_build_new_month_is_reused_for_the_first_month():
    month = build_new_month(2026, 10, 3000.0, FIXED, QUOTAS, [7])
    assert month.salary == 3000.0
    assert [c.template_id for c in month.fixed_expenses] == [1, 3]
    assert month.card_ids == [7]
