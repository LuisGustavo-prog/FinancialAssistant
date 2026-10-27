from datetime import date
from pydantic import BaseModel
from app.api.schemas.common import Description, PositiveMoney


class ExtraIncomeIn(BaseModel):
    amount: PositiveMoney
    occurred_on: date | None = None
    description: Description | None = None


class ExtraIncomePatch(BaseModel):
    amount: PositiveMoney | None = None
    occurred_on: date | None = None
    description: Description | None = None


class ExtraIncomeOut(BaseModel):
    id: int
    amount: float
    occurred_on: date
    description: str | None
    source: str
    is_editable: bool
