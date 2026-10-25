from fastapi import APIRouter
from app.api.schemas.catalog import TemplateIn, TemplateOut, TemplatePatch
from app.controllers import catalog_controller

router = APIRouter(prefix="/savings-quotas", tags=["savings-quotas"])

@router.get("", response_model=list[TemplateOut])
def list_savings_quotas():
    return catalog_controller.list_savings_quotas()

@router.post("", response_model=TemplateOut, status_code=201)
def create_savings_quota(body: TemplateIn):
    return catalog_controller.create_savings_quota(body.name, body.amount)

@router.patch("/{template_id}", response_model=TemplateOut)
def update_savings_quota(template_id: int, body: TemplatePatch):
    return catalog_controller.update_savings_quota(
        template_id, name=body.name, amount=body.amount, is_active=body.is_active
    )
