import pytest
from app.errors import (
    AppError,
    DefaultCategoryLockedError,
    FutureDateError,
    LeftoverIncomeLockedError,
    LeftoverNotPendingError,
    MonthClosedError,
    NameAlreadyExistsError,
    NoOpenMonthError,
    NotFoundError,
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
        (LeftoverNotPendingError("carried"), "leftover_not_pending", {"decision": "carried"}),
        (NotFoundError("category", 7), "not_found", {"resource": "category", "id": 7}),
        (NoOpenMonthError(), "no_open_month", {}),
        (NameAlreadyExistsError("Mercado"), "name_already_exists", {"name": "Mercado"}),
        (DefaultCategoryLockedError(), "default_category_locked", {}),
    ],
)
def test_each_error_has_its_code_and_params(error, code, params):
    assert isinstance(error, AppError)
    assert error.code == code
    assert error.params == params
