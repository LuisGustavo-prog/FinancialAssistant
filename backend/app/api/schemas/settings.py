from pydantic import BaseModel
from app.api.schemas.common import NonNegativeMoney


class SettingsIn(BaseModel):
    current_salary: NonNegativeMoney


class MonthSalaryIn(BaseModel):
    salary: NonNegativeMoney


class SettingsOut(BaseModel):
    current_salary: float | None
    current_month_salary: float | None
