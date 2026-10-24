from datetime import date
import pytest
from app.core.guards import (
    check_entry_date,
    check_entry_edit,
    ensure_income_editable,
    is_income_editable,
)
from app.core.models import IncomeSource
from app.errors import FutureDateError, LeftoverIncomeLockedError, MonthClosedError

TODAY = date(2026, 11, 2)

@pytest.mark.parametrize(
    "entry_date",
    [date(2026, 11, 1), date(2026, 11, 2), date(2026, 11, 30)],
)
def test_any_day_of_the_current_month_is_accepted(entry_date):
    check_entry_date(entry_date, TODAY)

def test_plan_example_freelance_of_oct_28_remembered_on_nov_2_is_refused():
    with pytest.raises(MonthClosedError) as info:
        check_entry_date(date(2026, 10, 28), TODAY)
    assert info.value.code == "month_closed"
    assert info.value.params == {"closed_month": "2026-10", "current_month": "2026-11"}

def test_last_day_of_previous_month_is_closed():
    with pytest.raises(MonthClosedError):
        check_entry_date(date(2026, 10, 31), TODAY)

def test_same_month_of_previous_year_is_closed():
    with pytest.raises(MonthClosedError) as info:
        check_entry_date(date(2025, 11, 15), TODAY)
    assert info.value.params["closed_month"] == "2025-11"

def test_first_day_of_next_month_is_future():
    with pytest.raises(FutureDateError) as info:
        check_entry_date(date(2026, 12, 1), TODAY)
    assert info.value.code == "future_date"

def test_next_year_is_future():
    with pytest.raises(FutureDateError):
        check_entry_date(date(2027, 1, 5), TODAY)

def test_year_boundary_in_january():
    today = date(2027, 1, 3)
    check_entry_date(date(2027, 1, 20), today)
    with pytest.raises(MonthClosedError):
        check_entry_date(date(2026, 12, 31), today)

def test_edit_inside_the_current_month_is_accepted():
    check_entry_edit(date(2026, 11, 1), date(2026, 11, 2), TODAY)

def test_edit_of_an_entry_from_a_closed_month_is_refused():
    with pytest.raises(MonthClosedError) as info:
        check_entry_edit(date(2026, 10, 20), date(2026, 11, 2), TODAY)
    assert info.value.params["closed_month"] == "2026-10"

def test_changing_the_date_to_a_closed_month_is_refused():
    with pytest.raises(MonthClosedError):
        check_entry_edit(date(2026, 11, 1), date(2026, 10, 31), TODAY)

def test_changing_the_date_to_a_future_month_is_refused():
    with pytest.raises(FutureDateError):
        check_entry_edit(date(2026, 11, 1), date(2026, 12, 1), TODAY)

def test_manual_income_is_editable():
    assert is_income_editable(IncomeSource.MANUAL) is True
    ensure_income_editable(IncomeSource.MANUAL)

def test_leftover_income_is_locked():
    assert is_income_editable(IncomeSource.LEFTOVER) is False
    with pytest.raises(LeftoverIncomeLockedError) as info:
        ensure_income_editable(IncomeSource.LEFTOVER)
    assert info.value.code == "leftover_income_locked"

def test_income_source_also_works_with_the_database_strings():
    assert is_income_editable("manual") is True
    assert is_income_editable("leftover") is False
    with pytest.raises(LeftoverIncomeLockedError):
        ensure_income_editable("leftover")
