from datetime import date
import pytest
from app.controllers import catalog_controller as catalog
from app.controllers import expense_controller as expenses_ctl
from app.controllers import month_routine_controller as routine
from app.controllers import settings_controller as settings_ctl
from app.controllers.breakdown import build_breakdown
from app.controllers.session import session
from app.controllers.unset import UNSET
from app.db.repositories import month_repository as months
from app.errors import (
    CategoryInactiveError,
    FutureDateError,
    MonthClosedError,
    NoOpenMonthError,
    NotFoundError,
)
TODAY = date(2026, 10, 23)

@pytest.fixture
def open_month(db_path):
    settings_ctl.save_current_salary(3000.0, today=TODAY)

def debit_total() -> float:
    with session() as conn:
        return build_breakdown(conn, months.get_open_month(conn)).debit_expenses

def test_without_an_open_month_the_list_is_empty_and_creating_is_refused(db_path):
    assert expenses_ctl.list_expenses() == []
    with pytest.raises(NoOpenMonthError):
        expenses_ctl.create_expense(10.0, today=TODAY)

def test_without_date_and_category_it_uses_today_and_outros(open_month):
    item = expenses_ctl.create_expense(45.5, today=TODAY)
    assert item == {
        "id": item["id"],
        "amount": 45.5,
        "occurred_on": "2026-10-23",
        "description": None,
        "category": {"id": 1, "name": "Outros"},
        "payment_method": "debit",
    }
    assert expenses_ctl.list_expenses() == [item]

def test_create_with_all_fields(open_month):
    category = catalog.create_category("Mercado")
    item = expenses_ctl.create_expense(
        120.9, date(2026, 10, 7), "  Compras da semana ", category["id"], today=TODAY
    )
    assert item["occurred_on"] == "2026-10-07"
    assert item["description"] == "Compras da semana"
    assert item["category"] == {"id": category["id"], "name": "Mercado"}

def test_blank_description_becomes_none(open_month):
    assert expenses_ctl.create_expense(10.0, description="   ", today=TODAY)["description"] is None

def test_the_balance_drops_right_away(open_month):
    expenses_ctl.create_expense(10.9, today=TODAY)
    expenses_ctl.create_expense(10.9, today=TODAY)
    assert debit_total() == 21.8

def test_a_later_day_of_the_current_month_is_accepted(open_month):
    assert expenses_ctl.create_expense(10.0, date(2026, 10, 31), today=TODAY)["occurred_on"] == "2026-10-31"

def test_date_in_a_closed_month_is_refused(open_month):
    with pytest.raises(MonthClosedError) as info:
        expenses_ctl.create_expense(10.0, date(2026, 9, 28), today=TODAY)
    assert info.value.params == {"closed_month": "2026-09", "current_month": "2026-10"}
    assert expenses_ctl.list_expenses() == []

def test_date_in_a_future_month_is_refused(open_month):
    with pytest.raises(FutureDateError):
        expenses_ctl.create_expense(10.0, date(2026, 11, 1), today=TODAY)

@pytest.mark.parametrize("bad_amount", [0, -5.0, 0.004])
def test_non_positive_amount_is_refused(open_month, bad_amount):
    with pytest.raises(ValueError):
        expenses_ctl.create_expense(bad_amount, today=TODAY)

def test_amount_is_rounded(open_month):
    assert expenses_ctl.create_expense(10.999, today=TODAY)["amount"] == 11.0

def test_unknown_category_is_refused(open_month):
    with pytest.raises(NotFoundError) as info:
        expenses_ctl.create_expense(10.0, category_id=999, today=TODAY)
    assert info.value.params == {"resource": "category", "id": 999}

def test_inactive_category_cannot_be_chosen_for_a_new_expense(open_month):
    category = catalog.create_category("Mercado")
    catalog.update_category(category["id"], is_active=False)
    with pytest.raises(CategoryInactiveError) as info:
        expenses_ctl.create_expense(10.0, category_id=category["id"], today=TODAY)
    assert info.value.code == "category_inactive"

def test_list_is_newest_first_and_only_the_open_month(seed_october):
    seed_october()  
    later = expenses_ctl.create_expense(10.0, date(2026, 10, 20), today=TODAY)
    listed = expenses_ctl.list_expenses()
    assert [e["id"] for e in listed][0] == later["id"]
    assert [e["occurred_on"] for e in listed] == ["2026-10-20", "2026-10-05"]

    routine.run(today=date(2026, 11, 2))
    assert expenses_ctl.list_expenses() == []  

def test_patch_changes_only_the_given_fields(open_month):
    item = expenses_ctl.create_expense(10.0, date(2026, 10, 5), "Padaria", today=TODAY)
    updated = expenses_ctl.update_expense(item["id"], amount=12.5, today=TODAY)
    assert (updated["amount"], updated["occurred_on"], updated["description"]) == (12.5, "2026-10-05", "Padaria")

def test_description_can_be_cleared_with_none_and_is_kept_when_unset(open_month):
    item = expenses_ctl.create_expense(10.0, description="Padaria", today=TODAY)
    kept = expenses_ctl.update_expense(item["id"], amount=11.0, description=UNSET, today=TODAY)
    assert kept["description"] == "Padaria"
    cleared = expenses_ctl.update_expense(item["id"], description=None, today=TODAY)
    assert cleared["description"] is None
    changed = expenses_ctl.update_expense(item["id"], description="  Mercado ", today=TODAY)
    assert changed["description"] == "Mercado"

def test_the_date_can_change_inside_the_current_month(open_month):
    item = expenses_ctl.create_expense(10.0, today=TODAY)
    assert expenses_ctl.update_expense(item["id"], occurred_on=date(2026, 10, 2), today=TODAY)["occurred_on"] == "2026-10-02"

def test_changing_the_date_to_a_closed_or_future_month_is_refused(open_month):
    item = expenses_ctl.create_expense(10.0, today=TODAY)
    with pytest.raises(MonthClosedError):
        expenses_ctl.update_expense(item["id"], occurred_on=date(2026, 9, 30), today=TODAY)
    with pytest.raises(FutureDateError):
        expenses_ctl.update_expense(item["id"], occurred_on=date(2026, 11, 1), today=TODAY)
    assert expenses_ctl.list_expenses()[0]["occurred_on"] == "2026-10-23"

def test_changing_the_category(open_month):
    category = catalog.create_category("Lazer")
    item = expenses_ctl.create_expense(10.0, today=TODAY)
    updated = expenses_ctl.update_expense(item["id"], category_id=category["id"], today=TODAY)
    assert updated["category"] == {"id": category["id"], "name": "Lazer"}

def test_cannot_move_an_expense_to_an_inactive_category_but_may_keep_its_own(open_month):
    kept = catalog.create_category("Antiga")
    target = catalog.create_category("Nova")
    item = expenses_ctl.create_expense(10.0, category_id=kept["id"], today=TODAY)

    catalog.update_category(kept["id"], is_active=False)
    catalog.update_category(target["id"], is_active=False)

    with pytest.raises(CategoryInactiveError):
        expenses_ctl.update_expense(item["id"], category_id=target["id"], today=TODAY)
    same = expenses_ctl.update_expense(item["id"], amount=20.0, category_id=kept["id"], today=TODAY)
    assert (same["amount"], same["category"]["id"]) == (20.0, kept["id"])

def test_editing_an_expense_of_a_closed_month_is_refused(seed_october):
    seed_october()
    old = expenses_ctl.list_expenses()[0]
    routine.run(today=date(2026, 11, 2))
    with pytest.raises(MonthClosedError) as info:
        expenses_ctl.update_expense(old["id"], amount=1.0, today=date(2026, 11, 2))
    assert info.value.params["closed_month"] == "2026-10"

def test_unknown_expense(open_month):
    with pytest.raises(NotFoundError) as info:
        expenses_ctl.update_expense(999, amount=1.0, today=TODAY)
    assert info.value.params == {"resource": "expense", "id": 999}

def test_delete_removes_the_expense_and_the_balance_recovers(open_month):
    keep = expenses_ctl.create_expense(10.0, today=TODAY)
    gone = expenses_ctl.create_expense(25.0, today=TODAY)
    assert debit_total() == 35.0
    assert expenses_ctl.delete_expense(gone["id"], today=TODAY) is None
    assert [e["id"] for e in expenses_ctl.list_expenses()] == [keep["id"]]
    assert debit_total() == 10.0

def test_deleting_unknown_or_closed_month_expense_is_refused(seed_october):
    seed_october()
    old = expenses_ctl.list_expenses()[0]
    with pytest.raises(NotFoundError):
        expenses_ctl.delete_expense(999, today=TODAY)
    routine.run(today=date(2026, 11, 2))
    with pytest.raises(MonthClosedError):
        expenses_ctl.delete_expense(old["id"], today=date(2026, 11, 2))

def test_a_clock_that_went_back_does_not_let_an_expense_into_a_closed_month(seed_october):
    seed_october()
    routine.run(today=date(2026, 11, 5))
    with pytest.raises(MonthClosedError):
        expenses_ctl.create_expense(10.0, date(2026, 10, 20), today=date(2026, 10, 20))
    assert expenses_ctl.create_expense(10.0, today=date(2026, 10, 20))["occurred_on"] == "2026-11-05"
