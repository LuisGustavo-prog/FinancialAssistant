from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from app.core.models import MonthCopy, NewMonthCopy, Template
from app.core.money import money_equals, round_money


class SyncAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class SyncPlan:
    action: SyncAction
    copy_id: int | None = None
    name: str | None = None
    amount: float | None = None


def plan_template_sync(template: Template, open_month_copies: Iterable[MonthCopy]) -> SyncPlan:
    copy = next((c for c in open_month_copies if c.template_id == template.id), None)
    amount = round_money(template.amount)

    if not template.is_active:
        if copy is None:
            return SyncPlan(SyncAction.NONE)
        return SyncPlan(SyncAction.DELETE, copy_id=copy.id)

    if copy is None:
        return SyncPlan(SyncAction.CREATE, name=template.name, amount=amount)

    if copy.name == template.name and money_equals(copy.amount, amount):
        return SyncPlan(SyncAction.NONE)
    return SyncPlan(SyncAction.UPDATE, copy_id=copy.id, name=template.name, amount=amount)


def build_month_copies(templates: Iterable[Template]) -> list[NewMonthCopy]:
    return [NewMonthCopy(template_id=t.id, name=t.name, amount=round_money(t.amount)) for t in templates if t.is_active]
