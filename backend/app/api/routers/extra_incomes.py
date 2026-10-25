from fastapi import APIRouter
from app.api.schemas.extra_incomes import ExtraIncomeIn, ExtraIncomeOut, ExtraIncomePatch
from app.controllers import extra_income_controller
from app.controllers.unset import UNSET

router = APIRouter(prefix="/extra-incomes", tags=["extra-incomes"])

@router.get("", response_model=list[ExtraIncomeOut])
def list_extra_incomes():
    return extra_income_controller.list_extra_incomes()

@router.post("", response_model=ExtraIncomeOut, status_code=201)
def create_extra_income(body: ExtraIncomeIn):
    return extra_income_controller.create_extra_income(
        amount=body.amount, occurred_on=body.occurred_on, description=body.description
    )

@router.patch("/{income_id}", response_model=ExtraIncomeOut)
def update_extra_income(income_id: int, body: ExtraIncomePatch):
    return extra_income_controller.update_extra_income(
        income_id,
        amount=body.amount,
        occurred_on=body.occurred_on,
        description=body.description if "description" in body.model_fields_set else UNSET,
    )

@router.delete("/{income_id}", status_code=204)
def delete_extra_income(income_id: int):
    extra_income_controller.delete_extra_income(income_id)
