from datetime import date
from app.core.dates import is_same_month, year_month
from app.core.models import IncomeSource
from app.errors import FutureDateError, LeftoverIncomeLockedError, MonthClosedError


def check_entry_date(entry_date: date, today: date) -> None:
    if is_same_month(entry_date, today):
        return
    if (entry_date.year, entry_date.month) < (today.year, today.month):
        raise MonthClosedError(
            closed_month=year_month(entry_date),
            current_month=year_month(today),
        )
    raise FutureDateError()


def check_entry_edit(current_date: date, new_date: date, today: date) -> None:
    check_entry_date(current_date, today)
    check_entry_date(new_date, today)


def is_income_editable(source: IncomeSource | str) -> bool:
    return source != IncomeSource.LEFTOVER


def ensure_income_editable(source: IncomeSource | str) -> None:
    if not is_income_editable(source):
        raise LeftoverIncomeLockedError()
