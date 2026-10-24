"""Modelos usados pelas regras do core. Dataclasses simples, sem logica."""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class CardEntryType(StrEnum):
    """Tipo de uma linha do cartao. Pagamento conta no total, estorno nao."""

    PAYMENT = "payment"
    REFUND = "refund"


class MonthResult(StrEnum):
    """Resultado de um mes fechado. Verde: saldo final >= 0. Vermelho: negativo."""

    GREEN = "green"
    RED = "red"


@dataclass(frozen=True, slots=True)
class Breakdown:
    """Os totais do mes que entram na formula do saldo livre (todos em reais, >= 0)."""

    salary: float
    extra_incomes: float
    fixed_expenses: float
    savings_quotas: float
    debit_expenses: float
    credit_card_total: float


@dataclass(frozen=True, slots=True)
class CardEntry:
    """Uma linha fixada do cartao (pagamento ou estorno)."""

    type: CardEntryType
    amount: float


class IncomeSource(StrEnum):
    """Origem de uma renda extra. A renda vinda da sobra fica travada."""

    MANUAL = "manual"
    LEFTOVER = "leftover"


class LeftoverDecision(StrEnum):
    """Estado da decisao sobre a sobra de um mes fechado."""

    PENDING = "pending"
    CARRIED = "carried"
    DECLINED = "declined"


@dataclass(frozen=True, slots=True)
class ClosedMonth:
    """O que as regras da sobra precisam saber de um mes fechado."""

    year: int
    month_number: int
    final_balance: float
    leftover_decision: LeftoverDecision | None


@dataclass(frozen=True, slots=True)
class NewExtraIncome:
    """Uma renda extra a ser criada (ainda sem id)."""

    amount: float
    occurred_on: date
    description: str
    source: IncomeSource


@dataclass(frozen=True, slots=True)
class LeftoverOutcome:
    """Resultado de decidir a sobra: a decisao e, se levou, a renda a criar."""

    decision: LeftoverDecision
    extra_income: NewExtraIncome | None


@dataclass(frozen=True, slots=True)
class Template:
    """Modelo de gasto fixo ou de cota de poupanca (as duas tabelas tem o mesmo formato)."""

    id: int
    name: str
    amount: float
    is_active: bool


@dataclass(frozen=True, slots=True)
class MonthCopy:
    """Copia de um modelo dentro de um mes (month_fixed_expense ou month_savings_quota)."""

    id: int
    template_id: int | None
    name: str
    amount: float


@dataclass(frozen=True, slots=True)
class NewMonthCopy:
    """Uma copia a ser criada no mes (ainda sem id)."""

    template_id: int
    name: str
    amount: float
