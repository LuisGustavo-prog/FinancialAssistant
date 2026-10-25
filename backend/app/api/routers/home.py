from fastapi import APIRouter
from app.api.messages import leftover_message, notice_message
from app.api.schemas.home import HomeOut
from app.controllers import home_controller

router = APIRouter(tags=["home"])

@router.get("/home", response_model=HomeOut)
def get_home():
    home = home_controller.get_home()
    if home["status"] != "ok":
        return home

    home["notices"] = [
        {**notice, "message": notice_message(notice["code"], notice["params"])}
        for notice in home["notices"]
    ]
    leftover = home["pending_leftover"]
    if leftover is not None:
        leftover["message"] = leftover_message(leftover["month_number"], leftover["amount"])
    return home

@router.post("/notices/{notice_id}/dismiss", status_code=204)
def dismiss_notice(notice_id: int):
    home_controller.dismiss_notice(notice_id)
