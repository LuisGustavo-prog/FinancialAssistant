from datetime import date
from typing import Literal
from pydantic import BaseModel
from app.api.schemas.common import Name, NonNegativeMoney, PositiveMoney

EntryType = Literal["payment", "refund"]


class CardIn(BaseModel):
    name: Name


class CardPatch(BaseModel):
    name: Name | None = None
    is_active: bool | None = None


class ReportedValueIn(BaseModel):
    reported_value: NonNegativeMoney
    type: EntryType | None = None


class PaymentIn(BaseModel):
    amount: PositiveMoney


class EntryPatch(BaseModel):
    type: EntryType | None = None
    amount: PositiveMoney | None = None
    occurred_on: date | None = None


class EntryOut(BaseModel):
    id: int
    type: str
    amount: float
    occurred_on: date


class CreditCardOut(BaseModel):
    id: int
    name: str
    is_active: bool
    in_current_month: bool
    reported_value: float | None
    payments_total: float | None
    total: float | None
    updated_at: date | None
    days_since_update: int | None
    is_outdated: bool
    entries: list[EntryOut]
