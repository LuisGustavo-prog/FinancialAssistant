from fastapi import APIRouter
from app.api.schemas.catalog import TemplateIn, TemplateOut, TemplatePatch
from app.controllers import catalog_controller

router = APIRouter(prefix="/fixed-expenses", tags=["fixed-expenses"])


@router.get("", response_model=list[TemplateOut])
def list_fixed_expenses():
    return catalog_controller.list_fixed_expenses()


@router.post("", response_model=TemplateOut, status_code=201)
def create_fixed_expense(body: TemplateIn):
    return catalog_controller.create_fixed_expense(body.name, body.amount)


@router.patch("/{template_id}", response_model=TemplateOut)
def update_fixed_expense(template_id: int, body: TemplatePatch):
    return catalog_controller.update_fixed_expense(
        template_id, name=body.name, amount=body.amount, is_active=body.is_active
    )
