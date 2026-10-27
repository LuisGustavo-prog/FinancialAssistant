from fastapi import APIRouter
from app.api.schemas.credit_cards import (
    CardIn,
    CardPatch,
    CreditCardOut,
    EntryOut,
    EntryPatch,
    PaymentIn,
    ReportedValueIn,
)
from app.controllers import credit_card_controller

router = APIRouter(tags=["credit-cards"])


@router.get("/credit-cards", response_model=list[CreditCardOut])
def list_cards():
    return credit_card_controller.list_cards()


@router.post("/credit-cards", response_model=CreditCardOut, status_code=201)
def create_card(body: CardIn):
    return credit_card_controller.create_card(body.name)


@router.patch("/credit-cards/{card_id}", response_model=CreditCardOut)
def update_card(card_id: int, body: CardPatch):
    return credit_card_controller.update_card(card_id, name=body.name, is_active=body.is_active)


@router.put("/credit-cards/{card_id}/current-month", response_model=CreditCardOut)
def update_reported_value(card_id: int, body: ReportedValueIn):
    return credit_card_controller.update_reported_value(card_id, body.reported_value, entry_type=body.type)


@router.post("/credit-cards/{card_id}/current-month/payments", response_model=CreditCardOut, status_code=201)
def register_payment(card_id: int, body: PaymentIn):
    return credit_card_controller.register_payment(card_id, body.amount)


@router.patch("/credit-card-entries/{entry_id}", response_model=EntryOut)
def update_entry(entry_id: int, body: EntryPatch):
    return credit_card_controller.update_entry(
        entry_id, entry_type=body.type, amount=body.amount, occurred_on=body.occurred_on
    )


@router.delete("/credit-card-entries/{entry_id}", status_code=204)
def delete_entry(entry_id: int):
    credit_card_controller.delete_entry(entry_id)
