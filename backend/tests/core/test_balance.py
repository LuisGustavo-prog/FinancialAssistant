import pytest
from app.core.balance import free_balance, has_leftover, month_result
from app.core.models import Breakdown, MonthResult
from app.core.money import sum_money

def make_breakdown(**overrides) -> Breakdown:
    values = {
        "salary": 0.0,
        "extra_incomes": 0.0,
        "fixed_expenses": 0.0,
        "savings_quotas": 0.0,
        "debit_expenses": 0.0,
        "credit_card_total": 0.0,
    }
    values.update(overrides)
    return Breakdown(**values)

def test_free_balance_formula():
    breakdown = make_breakdown(
        salary=3000.0,
        extra_incomes=200.0,
        fixed_expenses=1200.0,
        savings_quotas=300.0,
        debit_expenses=450.50,
        credit_card_total=800.25,
    )
    assert free_balance(breakdown) == 449.25

def test_free_balance_with_only_salary():
    assert free_balance(make_breakdown(salary=2500.0)) == 2500.0

def test_free_balance_can_be_negative():
    breakdown = make_breakdown(salary=1000.0, credit_card_total=1050.10)
    assert free_balance(breakdown) == -50.10

def test_plan_example_thirty_cents_minus_ten_and_twenty_is_exactly_zero():
    naive = 0.30 - 0.1 - 0.2
    assert naive != 0.0  

    breakdown = make_breakdown(salary=0.30, debit_expenses=sum_money([0.1, 0.2]))
    balance = free_balance(breakdown)
    assert balance == 0.0
    assert month_result(balance) == MonthResult.GREEN
    assert has_leftover(balance) is False

@pytest.mark.parametrize("noise", [5e-17, -5e-17, 1e-12, -1e-12])
def test_float_noise_is_not_a_leftover_and_not_a_deficit(noise):
    assert has_leftover(noise) is False
    assert month_result(noise) == MonthResult.GREEN

def test_positive_balance_is_green_with_leftover():
    assert month_result(0.01) == MonthResult.GREEN
    assert has_leftover(0.01) is True

def test_negative_balance_is_red_without_leftover():
    assert month_result(-0.01) == MonthResult.RED
    assert has_leftover(-0.01) is False

def test_exactly_zero_is_green_without_leftover():
    assert month_result(0.0) == MonthResult.GREEN
    assert has_leftover(0.0) is False

def test_result_values_match_the_database_strings():
    assert month_result(10.0) == "green"
    assert month_result(-10.0) == "red"
