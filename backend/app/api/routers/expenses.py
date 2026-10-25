from fastapi import APIRouter
from app.api.schemas.expenses import ExpenseIn, ExpenseOut, ExpensePatch
from app.controllers import expense_controller
from app.controllers.unset import UNSET

router = APIRouter(prefix="/expenses", tags=["expenses"])

@router.get("", response_model=list[ExpenseOut])
def list_expenses():
    return expense_controller.list_expenses()

@router.post("", response_model=ExpenseOut, status_code=201)
def create_expense(body: ExpenseIn):
    return expense_controller.create_expense(
        amount=body.amount,
        occurred_on=body.occurred_on,
        description=body.description,
        category_id=body.category_id,
    )

@router.patch("/{expense_id}", response_model=ExpenseOut)
def update_expense(expense_id: int, body: ExpensePatch):
    return expense_controller.update_expense(
        expense_id,
        amount=body.amount,
        occurred_on=body.occurred_on,
        description=body.description if "description" in body.model_fields_set else UNSET,
        category_id=body.category_id,
    )

@router.delete("/{expense_id}", status_code=204)
def delete_expense(expense_id: int):
    expense_controller.delete_expense(expense_id)
