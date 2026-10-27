from dataclasses import dataclass
from datetime import date
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


class IncomeSource(StrEnum):
    MANUAL = "manual"
    LEFTOVER = "leftover"


class LeftoverDecision(StrEnum):
    PENDING = "pending"
    CARRIED = "carried"
    DECLINED = "declined"


@dataclass(frozen=True, slots=True)
class ClosedMonth:
    year: int
    month_number: int
    final_balance: float
    leftover_decision: LeftoverDecision | None


@dataclass(frozen=True, slots=True)
class NewExtraIncome:
    amount: float
    occurred_on: date
    description: str
    source: IncomeSource


@dataclass(frozen=True, slots=True)
class LeftoverOutcome:
    decision: LeftoverDecision
    extra_income: NewExtraIncome | None


@dataclass(frozen=True, slots=True)
class Template:
    id: int
    name: str
    amount: float
    is_active: bool


@dataclass(frozen=True, slots=True)
class MonthCopy:
    id: int
    template_id: int | None
    name: str
    amount: float


@dataclass(frozen=True, slots=True)
class NewMonthCopy:
    template_id: int
    name: str
    amount: float


class NoticeCode(StrEnum):
    MONTH_ENDING = "month_ending"
    CREDIT_CARD_NOT_UPDATED = "credit_card_not_updated"
    MONTH_CLOSED_NEGATIVE = "month_closed_negative"
    UNUSED_MONTHS = "unused_months"


@dataclass(frozen=True, slots=True)
class Notice:
    id: int | None
    code: NoticeCode
    params: dict[str, object]


@dataclass(frozen=True, slots=True)
class CardStatus:
    name: str
    updated_at: date | None
