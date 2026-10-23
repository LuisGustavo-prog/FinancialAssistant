import math
import pytest
from app.core.money import money_equals, round_money, sum_money

def test_the_float_problem_exists_without_rounding():
    assert 0.1 + 0.2 != 0.3
    assert 0.1 + 0.2 == 0.30000000000000004

def test_round_money_fixes_zero_point_one_plus_zero_point_two():
    assert round_money(0.1 + 0.2) == 0.3

def test_cents_still_add_up_normally():
    assert round_money(10.90 + 10.90) == 21.80

@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (0.30000000000000004, 0.3),
        (19.999999999999996, 20.0),
        (1234.5600000001, 1234.56),
        (0.01, 0.01),
        (-5.499999999999999, -5.5),
        (0.0, 0.0),
    ],
)
def test_round_money_cleans_noise_after_the_second_decimal(raw, expected):
    assert round_money(raw) == expected

def test_round_money_always_returns_float():
    result = round_money(10)
    assert isinstance(result, float)
    assert result == 10.0

def test_round_money_turns_negative_zero_into_zero():
    result = round_money(-0.001)
    assert result == 0.0
    assert math.copysign(1.0, result) == 1.0
    assert str(result) == "0.0"

@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_round_money_refuses_non_finite_values(bad):
    with pytest.raises(ValueError):
        round_money(bad)

def test_sum_money_of_empty_list_is_zero():
    assert sum_money([]) == 0.0


def test_sum_money_fixes_zero_point_one_plus_zero_point_two():
    assert sum_money([0.1, 0.2]) == 0.3

def test_sum_money_of_a_hundred_cents_is_exactly_one_real():
    naive_total = 0.0
    for _ in range(100):
        naive_total += 0.01
    assert naive_total != 1.0
    assert sum_money(0.01 for _ in range(100)) == 1.0

def test_sum_money_accepts_negative_values():
    assert sum_money([100.10, -50.05, -50.05]) == 0.0

def test_money_equals_rounds_before_comparing():
    assert money_equals(0.1 + 0.2, 0.3)
    assert not money_equals(0.3, 0.31)
