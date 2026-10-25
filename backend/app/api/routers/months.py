from fastapi import APIRouter
from app.api.schemas.months import LeftoverDecisionIn, LeftoverDecisionOut, MonthDetailOut, MonthItemOut
from app.api.schemas.settings import MonthSalaryIn, SettingsOut
from app.controllers import month_controller, settings_controller

router = APIRouter(prefix="/months", tags=["months"])

@router.get("", response_model=list[MonthItemOut])
def list_months():
    return month_controller.list_months()

@router.patch("/current/salary", response_model=SettingsOut)
def update_month_salary(body: MonthSalaryIn):
    return settings_controller.update_current_month_salary(body.salary)

@router.get("/{month_id}", response_model=MonthDetailOut)
def get_month(month_id: int):
    return month_controller.get_month(month_id)

@router.post("/{month_id}/leftover-decision", response_model=LeftoverDecisionOut)
def decide_leftover(month_id: int, body: LeftoverDecisionIn):
    return month_controller.decide_leftover(month_id, body.decision)
