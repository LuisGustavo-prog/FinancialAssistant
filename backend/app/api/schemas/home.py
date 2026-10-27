from typing import Annotated, Literal
from pydantic import BaseModel, Field
from app.api.schemas.expenses import ExpenseOut
from app.api.schemas.months import BreakdownOut


class HomeMonthOut(BaseModel):
    id: int
    year: int
    month_number: int
    status: str
    days_left: int


class NoticeOut(BaseModel):
    id: int | None
    code: str
    params: dict
    message: str


class PendingLeftoverOut(BaseModel):
    month_id: int
    year: int
    month_number: int
    amount: float
    message: str


class HomeOk(BaseModel):
    status: Literal["ok"]
    month: HomeMonthOut
    free_balance: float
    breakdown: BreakdownOut
    notices: list[NoticeOut]
    pending_leftover: PendingLeftoverOut | None
    recent_expenses: list[ExpenseOut]


class HomeNeedsSetup(BaseModel):
    status: Literal["needs_setup"]


HomeOut = Annotated[HomeOk | HomeNeedsSetup, Field(discriminator="status")]
