from pydantic import BaseModel
from app.api.schemas.common import Name, PositiveMoney

class TemplateIn(BaseModel):
    name: Name
    amount: PositiveMoney

class TemplatePatch(BaseModel):
    name: Name | None = None
    amount: PositiveMoney | None = None
    is_active: bool | None = None

class TemplateOut(BaseModel):
    id: int
    name: str
    amount: float
    is_active: bool

class CategoryIn(BaseModel):
    name: Name

class CategoryPatch(BaseModel):
    name: Name | None = None
    is_active: bool | None = None

class CategoryOut(BaseModel):
    id: int
    name: str
    is_default: bool
    is_active: bool
