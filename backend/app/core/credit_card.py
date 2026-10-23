from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from app.core.dates import days_since
from app.core.models import CardEntry, CardEntryType
from app.core.money import round_money, sum_money
from app.errors import PaymentExceedsReportedValueError, ValueDecreasedError

OUTDATED_AFTER_DAYS = 7


@dataclass(frozen=True, slots=True)
class PaymentPlan:
    entry: CardEntry
    new_reported_value: float


def payments_total(entries: Iterable[CardEntry]) -> float:
    return sum_money(entry.amount for entry in entries if entry.type == CardEntryType.PAYMENT)

def card_total(reported_value: float, entries: Iterable[CardEntry]) -> float:
    return sum_money([reported_value, payments_total(entries)])

def plan_reported_value_update(
    current_value: float,
    new_value: float,
    decrease_type: CardEntryType | None = None,
) -> CardEntry | None:
    current = round_money(current_value)
    new = round_money(new_value)
    if new < 0:
        raise ValueError("O valor informado do cartao nao pode ser negativo.")

    difference = round_money(current - new)
    if difference <= 0:
        return None
    if decrease_type is None:
        raise ValueDecreasedError(difference)
    return CardEntry(type=decrease_type, amount=difference)

def plan_payment(reported_value: float, amount: float) -> PaymentPlan:
    reported = round_money(reported_value)
    paid = round_money(amount)
    if paid <= 0:
        raise ValueError("O valor do pagamento precisa ser maior que zero.")
    if paid > reported:
        raise PaymentExceedsReportedValueError(amount=paid, reported_value=reported)
    return PaymentPlan(
        entry=CardEntry(type=CardEntryType.PAYMENT, amount=paid),
        new_reported_value=round_money(reported - paid),
    )

def days_since_update(updated_at: date | None, today: date) -> int | None:
    if updated_at is None:
        return None
    return max(0, days_since(updated_at, today))

def is_outdated(updated_at: date | None, today: date) -> bool:
    days = days_since_update(updated_at, today)
    return days is None or days > OUTDATED_AFTER_DAYS
