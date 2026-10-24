from app.core.models import MonthCopy, NewMonthCopy, Template
from app.core.template_sync import (
    SyncAction,
    SyncPlan,
    build_month_copies,
    plan_template_sync,
)

def template(id=1, name="Aluguel", amount=1200.0, is_active=True):
    return Template(id=id, name=name, amount=amount, is_active=is_active)

def copy(id=10, template_id=1, name="Aluguel", amount=1200.0):
    return MonthCopy(id=id, template_id=template_id, name=name, amount=amount)

def test_new_active_template_is_created_in_the_open_month():
    plan = plan_template_sync(template(), [])
    assert plan == SyncPlan(SyncAction.CREATE, name="Aluguel", amount=1200.0)

def test_reactivated_template_comes_back_to_the_open_month():
    plan = plan_template_sync(template(is_active=True), [copy(id=11, template_id=2, name="Luz")])
    assert plan.action == SyncAction.CREATE


def test_changed_amount_updates_the_copy():
    plan = plan_template_sync(template(amount=1350.0), [copy()])
    assert plan == SyncPlan(SyncAction.UPDATE, copy_id=10, name="Aluguel", amount=1350.0)

def test_changed_name_updates_the_copy():
    plan = plan_template_sync(template(name="Aluguel do apto"), [copy()])
    assert plan == SyncPlan(SyncAction.UPDATE, copy_id=10, name="Aluguel do apto", amount=1200.0)

def test_nothing_changed_does_nothing():
    assert plan_template_sync(template(), [copy()]) == SyncPlan(SyncAction.NONE)

def test_floating_point_noise_in_the_amount_is_not_a_change():
    plan = plan_template_sync(template(amount=0.1 + 0.2), [copy(amount=0.3)])
    assert plan.action == SyncAction.NONE

def test_update_amount_is_rounded():
    plan = plan_template_sync(template(amount=99.99000000000001), [copy(amount=50.0)])
    assert plan.amount == 99.99

def test_deactivated_template_removes_its_copy_from_the_open_month():
    plan = plan_template_sync(template(is_active=False), [copy()])
    assert plan == SyncPlan(SyncAction.DELETE, copy_id=10)

def test_deactivated_template_without_copy_does_nothing():
    assert plan_template_sync(template(is_active=False), []) == SyncPlan(SyncAction.NONE)

def test_only_the_copy_of_the_same_template_is_considered():
    copies = [
        copy(id=10, template_id=1, name="Aluguel", amount=1200.0),
        copy(id=11, template_id=2, name="Luz", amount=150.0),
        copy(id=12, template_id=None, name="Avulso", amount=30.0),
    ]
    plan = plan_template_sync(template(id=2, name="Luz", amount=180.0), copies)
    assert plan == SyncPlan(SyncAction.UPDATE, copy_id=11, name="Luz", amount=180.0)

def test_copy_without_template_is_never_touched():
    copies = [copy(id=12, template_id=None, name="Aluguel", amount=1200.0)]
    plan = plan_template_sync(template(id=1), copies)
    assert plan.action == SyncAction.CREATE

def test_new_month_copies_only_active_templates_in_order():
    templates = [
        template(id=1, name="Aluguel", amount=1200.0),
        template(id=2, name="Academia", amount=99.9, is_active=False),
        template(id=3, name="Internet", amount=100.0),
    ]
    assert build_month_copies(templates) == [
        NewMonthCopy(template_id=1, name="Aluguel", amount=1200.0),
        NewMonthCopy(template_id=3, name="Internet", amount=100.0),
    ]

def test_new_month_without_templates_has_no_copies():
    assert build_month_copies([]) == []
    assert build_month_copies([template(is_active=False)]) == []

def test_new_month_copy_amounts_are_rounded():
    copies = build_month_copies([template(amount=0.1 + 0.2)])
    assert copies[0].amount == 0.3
