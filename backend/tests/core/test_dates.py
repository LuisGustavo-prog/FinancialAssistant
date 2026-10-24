from datetime import date
import pytest
from app.core.dates import (
    days_left_in_month,
    days_since,
    first_day_of_month,
    is_same_month,
    last_day_of_month,
    month_name_pt,
    next_month,
    year_month,
)

def test_first_day_of_month():
    assert first_day_of_month(date(2026, 10, 23)) == date(2026, 10, 1)
    assert first_day_of_month(date(2026, 10, 1)) == date(2026, 10, 1)

@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 10, 23), date(2026, 10, 31)),
        (date(2026, 4, 1), date(2026, 4, 30)),
        (date(2026, 12, 5), date(2026, 12, 31)),
        (date(2026, 2, 10), date(2026, 2, 28)),
        (date(2028, 2, 10), date(2028, 2, 29)),  
        (date(2100, 2, 1), date(2100, 2, 28)),  
    ],
)
def test_last_day_of_month(day, expected):
    assert last_day_of_month(day) == expected

@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 10, 23), 8),
        (date(2026, 10, 31), 0),  
        (date(2026, 10, 30), 1),
        (date(2026, 10, 29), 2),
        (date(2026, 10, 1), 30),
        (date(2026, 2, 28), 0),
        (date(2028, 2, 28), 1),
        (date(2028, 2, 29), 0),
    ],
)
def test_days_left_in_month(today, expected):
    assert days_left_in_month(today) == expected

def test_days_since_same_day_is_zero():
    assert days_since(date(2026, 10, 10), date(2026, 10, 10)) == 0

def test_days_since_counts_calendar_days():
    assert days_since(date(2026, 10, 10), date(2026, 10, 15)) == 5
    assert days_since(date(2026, 9, 28), date(2026, 10, 2)) == 4
    assert days_since(date(2026, 2, 27), date(2026, 3, 1)) == 2

def test_days_since_is_negative_when_the_date_is_in_the_future():
    assert days_since(date(2026, 10, 15), date(2026, 10, 12)) == -3

def test_is_same_month():
    assert is_same_month(date(2026, 10, 1), date(2026, 10, 31))
    assert not is_same_month(date(2026, 10, 31), date(2026, 11, 1))
    assert not is_same_month(date(2026, 10, 15), date(2025, 10, 15))

def test_next_month_within_the_year():
    assert next_month(2026, 10) == (2026, 11)

def test_next_month_wraps_december_to_january():
    assert next_month(2026, 12) == (2027, 1)

@pytest.mark.parametrize("bad_month", [0, 13, -1])
def test_next_month_refuses_invalid_month(bad_month):
    with pytest.raises(ValueError):
        next_month(2026, bad_month)

@pytest.mark.parametrize(
    ("number", "name"),
    [(1, "janeiro"), (3, "março"), (10, "outubro"), (12, "dezembro")],
)
def test_month_name_pt(number, name):
    assert month_name_pt(number) == name

@pytest.mark.parametrize("bad_month", [0, 13])
def test_month_name_pt_refuses_invalid_month(bad_month):
    with pytest.raises(ValueError):
        month_name_pt(bad_month)

def test_year_month_label_is_zero_padded():
    assert year_month(date(2026, 10, 23)) == "2026-10"
    assert year_month(date(2026, 3, 1)) == "2026-03"
