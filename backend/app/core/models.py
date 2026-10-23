from dataclasses import dataclass
from enum import StrEnum

class CardEntryType(StrEnum):
    PAYMENT = "payment"
    REFUND = "refund"

class MonthResult(StrEnum):
    GREEN = "green"
    RED = "red"

@dataclass(frozen=True, slots=True)
class Breakdown:
    salary: float
    extra_incomes: float
    fixed_expenses: float
    savings_quotas: float
    debit_expenses: float
    credit_card_total: float

@dataclass(frozen=True, slots=True)
class CardEntry:

    type: CardEntryType
    amount: float
