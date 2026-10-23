import pytest
from app.errors import (
    AppError,
    FutureDateError,
    LeftoverIncomeLockedError,
    MonthClosedError,
    PaymentExceedsReportedValueError,
    ValueDecreasedError,
)

@pytest.mark.parametrize(
    ("error", "code", "params"),
    [
        (
            MonthClosedError("2026-10", "2026-11"),
            "month_closed",
            {"closed_month": "2026-10", "current_month": "2026-11"},
        ),
        (FutureDateError(), "future_date", {}),
        (ValueDecreasedError(50.0), "value_decreased", {"difference": 50.0}),
        (
            PaymentExceedsReportedValueError(120.0, 100.0),
            "payment_exceeds_reported_value",
            {"amount": 120.0, "reported_value": 100.0},
        ),
        (LeftoverIncomeLockedError(), "leftover_income_locked", {}),
    ],
)
def test_each_error_has_its_code_and_params(error, code, params):
    assert isinstance(error, AppError)
    assert error.code == code
    assert error.params == params
