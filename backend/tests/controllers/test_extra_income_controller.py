from datetime import date

import pytest

from app.controllers import extra_income_controller as incomes_ctl
from app.controllers import month_routine_controller as routine
from app.controllers import settings_controller as settings_ctl
from app.controllers.breakdown import build_breakdown
from app.controllers.session import session
from app.controllers.unset import UNSET
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months
from app.errors import (
    FutureDateError,
    LeftoverIncomeLockedError,
    MonthClosedError,
    NoOpenMonthError,
    NotFoundError,
)

TODAY = date(2026, 10, 23)


@pytest.fixture
def open_month(db_path):
    settings_ctl.save_current_salary(3000.0, today=TODAY)


def extra_total() -> float:
    with session() as conn:
        return build_breakdown(conn, months.get_open_month(conn)).extra_incomes


def add_leftover_income() -> int:
    """Uma renda vinda da sobra, como o caso de uso da sobra a cria."""
    with session() as conn:
        month = months.get_open_month(conn)
        return incomes.insert_extra_income(conn, month["id"], 250.0, "2026-10-02", "Sobra de setembro", "leftover")


def test_without_an_open_month_the_list_is_empty_and_creating_is_refused(db_path):
    assert incomes_ctl.list_extra_incomes() == []
    with pytest.raises(NoOpenMonthError):
        incomes_ctl.create_extra_income(100.0, today=TODAY)


def test_create_a_manual_income_with_today_as_the_default_date(open_month):
    item = incomes_ctl.create_extra_income(200.0, description="  Freela ", today=TODAY)
    assert item == {
        "id": item["id"],
        "amount": 200.0,
        "occurred_on": "2026-10-23",
        "description": "Freela",
        "source": "manual",
        "is_editable": True,
    }
    assert incomes_ctl.list_extra_incomes() == [item]
    assert extra_total() == 200.0


def test_date_in_a_closed_or_future_month_is_refused(open_month):
    with pytest.raises(MonthClosedError) as info:
        incomes_ctl.create_extra_income(100.0, date(2026, 9, 28), today=TODAY)
    assert info.value.params == {"closed_month": "2026-09", "current_month": "2026-10"}
    with pytest.raises(FutureDateError):
        incomes_ctl.create_extra_income(100.0, date(2026, 11, 3), today=TODAY)
    assert incomes_ctl.list_extra_incomes() == []


@pytest.mark.parametrize("bad_amount", [0, -1.0, 0.004])
def test_non_positive_amount_is_refused(open_month, bad_amount):
    with pytest.raises(ValueError):
        incomes_ctl.create_extra_income(bad_amount, today=TODAY)


def test_list_is_newest_first_and_only_the_open_month(open_month):
    older = incomes_ctl.create_extra_income(10.0, date(2026, 10, 2), today=TODAY)
    newer = incomes_ctl.create_extra_income(20.0, date(2026, 10, 15), today=TODAY)
    assert [i["id"] for i in incomes_ctl.list_extra_incomes()] == [newer["id"], older["id"]]
    routine.run(today=date(2026, 11, 2))
    assert incomes_ctl.list_extra_incomes() == []


def test_patch_changes_only_the_given_fields_and_description_can_be_cleared(open_month):
    item = incomes_ctl.create_extra_income(200.0, date(2026, 10, 5), "Freela", today=TODAY)
    updated = incomes_ctl.update_extra_income(item["id"], amount=250.0, description=UNSET, today=TODAY)
    assert (updated["amount"], updated["occurred_on"], updated["description"]) == (250.0, "2026-10-05", "Freela")
    cleared = incomes_ctl.update_extra_income(item["id"], description=None, today=TODAY)
    assert cleared["description"] is None
    assert extra_total() == 250.0


def test_changing_the_date_respects_the_month_locks(open_month):
    item = incomes_ctl.create_extra_income(200.0, today=TODAY)
    assert (
        incomes_ctl.update_extra_income(item["id"], occurred_on=date(2026, 10, 3), today=TODAY)["occurred_on"]
        == "2026-10-03"
    )
    with pytest.raises(MonthClosedError):
        incomes_ctl.update_extra_income(item["id"], occurred_on=date(2026, 9, 30), today=TODAY)
    with pytest.raises(FutureDateError):
        incomes_ctl.update_extra_income(item["id"], occurred_on=date(2026, 11, 1), today=TODAY)


def test_delete_removes_the_income_and_the_balance_recovers(open_month):
    keep = incomes_ctl.create_extra_income(100.0, today=TODAY)
    gone = incomes_ctl.create_extra_income(50.0, today=TODAY)
    assert incomes_ctl.delete_extra_income(gone["id"], today=TODAY) is None
    assert [i["id"] for i in incomes_ctl.list_extra_incomes()] == [keep["id"]]
    assert extra_total() == 100.0


def test_unknown_income(open_month):
    with pytest.raises(NotFoundError) as info:
        incomes_ctl.update_extra_income(999, amount=1.0, today=TODAY)
    assert info.value.params == {"resource": "extra_income", "id": 999}
    with pytest.raises(NotFoundError):
        incomes_ctl.delete_extra_income(999, today=TODAY)


# --------------------------------------------------------------------------
# Renda travada (origem sobra)
# --------------------------------------------------------------------------
def test_leftover_income_is_listed_as_not_editable(open_month):
    income_id = add_leftover_income()
    manual = incomes_ctl.create_extra_income(10.0, today=TODAY)
    flags = {i["id"]: i["is_editable"] for i in incomes_ctl.list_extra_incomes()}
    assert flags == {income_id: False, manual["id"]: True}


def test_leftover_income_cannot_be_edited_or_deleted(open_month):
    income_id = add_leftover_income()
    with pytest.raises(LeftoverIncomeLockedError) as info:
        incomes_ctl.update_extra_income(income_id, amount=1.0, today=TODAY)
    assert info.value.code == "leftover_income_locked"
    with pytest.raises(LeftoverIncomeLockedError):
        incomes_ctl.delete_extra_income(income_id, today=TODAY)
    item = incomes_ctl.list_extra_incomes()[0]
    assert (item["amount"], item["description"]) == (250.0, "Sobra de setembro")
    assert extra_total() == 250.0


# --------------------------------------------------------------------------
# Mes fechado
# --------------------------------------------------------------------------
def test_income_of_a_closed_month_cannot_be_edited_or_deleted(open_month):
    item = incomes_ctl.create_extra_income(200.0, today=TODAY)
    routine.run(today=date(2026, 11, 2))
    with pytest.raises(MonthClosedError) as info:
        incomes_ctl.update_extra_income(item["id"], amount=1.0, today=date(2026, 11, 2))
    assert info.value.params["closed_month"] == "2026-10"
    with pytest.raises(MonthClosedError):
        incomes_ctl.delete_extra_income(item["id"], today=date(2026, 11, 2))
