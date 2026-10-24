class AppError(Exception):
    code = "app_error"

    def __init__(self, **params: object) -> None:
        super().__init__(self.code)
        self.params = params

class MonthClosedError(AppError):
    code = "month_closed"

    def __init__(self, closed_month: str, current_month: str) -> None:
        super().__init__(closed_month=closed_month, current_month=current_month)

class FutureDateError(AppError):
    code = "future_date"

class ValueDecreasedError(AppError):
    code = "value_decreased"

    def __init__(self, difference: float) -> None:
        super().__init__(difference=difference)

class PaymentExceedsReportedValueError(AppError):
    code = "payment_exceeds_reported_value"

    def __init__(self, amount: float, reported_value: float) -> None:
        super().__init__(amount=amount, reported_value=reported_value)

class LeftoverIncomeLockedError(AppError):
    code = "leftover_income_locked"

class LeftoverNotPendingError(AppError):
    code = "leftover_not_pending"

    def __init__(self, decision: str | None) -> None:
        super().__init__(decision=decision)
