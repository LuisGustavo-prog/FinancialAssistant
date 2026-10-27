from typing import Literal
from pydantic import BaseModel
from app.api.schemas.expenses import ExpenseOut
from app.api.schemas.extra_incomes import ExtraIncomeOut


class LeftoverDecisionIn(BaseModel):
    decision: Literal["carried", "declined"]


class BreakdownOut(BaseModel):
    salary: float
    extra_incomes: float
    fixed_expenses: float
    savings_quotas: float
    debit_expenses: float
    credit_card_total: float


class MonthItemOut(BaseModel):
    id: int
    year: int
    month_number: int
    status: str
    result: str | None
    final_balance: float | None
    leftover_decision: str | None


class NameAmountOut(BaseModel):
    name: str
    amount: float


class CardTotalOut(BaseModel):
    id: int
    name: str
    total: float


class MonthDetailOut(MonthItemOut):
    breakdown: BreakdownOut
    expenses: list[ExpenseOut]
    extra_incomes: list[ExtraIncomeOut]
    fixed_expenses: list[NameAmountOut]
    savings_quotas: list[NameAmountOut]
    credit_cards: list[CardTotalOut]


class LeftoverDecisionOut(MonthItemOut):
    extra_income: ExtraIncomeOut | None
