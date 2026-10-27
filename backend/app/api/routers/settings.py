from fastapi import APIRouter
from app.api.schemas.settings import SettingsIn, SettingsOut
from app.controllers import settings_controller

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def get_settings():
    return settings_controller.get_settings()


@router.put("/settings", response_model=SettingsOut)
def save_settings(body: SettingsIn):
    return settings_controller.save_current_salary(body.current_salary)
