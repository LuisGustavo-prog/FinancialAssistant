from fastapi import APIRouter
from app.api.schemas.catalog import CategoryIn, CategoryOut, CategoryPatch
from app.controllers import catalog_controller

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories():
    return catalog_controller.list_categories()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(body: CategoryIn):
    return catalog_controller.create_category(body.name)


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, body: CategoryPatch):
    return catalog_controller.update_category(category_id, name=body.name, is_active=body.is_active)
