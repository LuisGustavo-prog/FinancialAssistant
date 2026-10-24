import calendar
from datetime import date

def first_day_of_month(day: date) -> date:
    return day.replace(day=1)

def last_day_of_month(day: date) -> date:
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=last)

def days_left_in_month(today: date) -> int:
    return (last_day_of_month(today) - today).days

def days_since(earlier: date, today: date) -> int:
    return (today - earlier).days

def is_same_month(first: date, second: date) -> bool:
    return (first.year, first.month) == (second.year, second.month)

def next_month(year: int, month: int) -> tuple[int, int]:
    if not 1 <= month <= 12:
        raise ValueError(f"Mes invalido: {month}")
    if month == 12:
        return year + 1, 1
    return year, month + 1

MONTH_NAMES_PT = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)

def month_name_pt(month_number: int) -> str:
    if not 1 <= month_number <= 12:
        raise ValueError(f"Mes invalido: {month_number}")
    return MONTH_NAMES_PT[month_number - 1]

def month_label(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"

def year_month(day: date) -> str:
    return month_label(day.year, day.month)

def months_between(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    months: list[tuple[int, int]] = []
    current = next_month(*start)
    while current < end:
        months.append(current)
        current = next_month(*current)
    return months
