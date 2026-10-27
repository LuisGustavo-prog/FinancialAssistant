from datetime import date
from pydantic import BaseModel
from app.api.schemas.common import Description, PositiveMoney


class ExpenseIn(BaseModel):
    amount: PositiveMoney
    occurred_on: date | None = None
    description: Description | None = None
    category_id: int | None = None


class ExpensePatch(BaseModel):
    amount: PositiveMoney | None = None
    occurred_on: date | None = None
    description: Description | None = None
    category_id: int | None = None


class CategoryRef(BaseModel):
    id: int
    name: str


class ExpenseOut(BaseModel):
    id: int
    amount: float
    occurred_on: date
    description: str | None
    category: CategoryRef
    payment_method: str
