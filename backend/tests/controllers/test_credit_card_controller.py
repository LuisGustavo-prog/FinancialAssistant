from datetime import date
import pytest
from app.controllers import credit_card_controller as cc
from app.controllers import month_routine_controller as routine
from app.controllers import settings_controller as settings_ctl
from app.controllers.breakdown import build_breakdown
from app.controllers.session import session
from app.db.repositories import credit_card_repository as card_repo
from app.db.repositories import month_repository as months
from app.errors import (
    MonthClosedError,
    NoOpenMonthError,
    NotFoundError,
    PaymentExceedsReportedValueError,
    ValueDecreasedError,
)
from tests.controllers.conftest import read

TODAY = date(2026, 10, 23)

@pytest.fixture
def open_month(db_path):
    settings_ctl.save_current_salary(3000.0, today=TODAY)

def card_total_in_breakdown() -> float:
    with session() as conn:
        return build_breakdown(conn, months.get_open_month(conn)).credit_card_total

def seed_card_month(card_id, reported_value, updated_at):
    with session() as conn:
        card_month = card_repo.get_card_month(conn, card_id, months.get_open_month(conn)["id"])
        card_repo.update_reported_value(conn, card_month["id"], reported_value, updated_at)

def entries_in_db():
    return read("SELECT type, amount, occurred_on FROM credit_card_entry ORDER BY id")

def test_card_created_before_the_first_salary_has_no_total_until_the_month_exists(db_path):
    item = cc.create_card("  Nubank ", today=TODAY)
    assert item["name"] == "Nubank"
    assert item["in_current_month"] is False
    assert (item["reported_value"], item["total"], item["entries"]) == (None, None, [])
    assert item["is_outdated"] is False

    settings_ctl.save_current_salary(3000.0, today=TODAY)  
    assert cc.list_cards(today=TODAY)[0]["in_current_month"] is True

def test_plan_example_card_created_in_the_middle_of_the_month_gets_a_zero_total_right_away(open_month):
    item = cc.create_card("Nubank", today=TODAY)
    assert item == {
        "id": item["id"],
        "name": "Nubank",
        "is_active": True,
        "in_current_month": True,
        "reported_value": 0.0,
        "payments_total": 0.0,
        "total": 0.0,
        "updated_at": None,
        "days_since_update": None,
        "is_outdated": True,
        "entries": [],
    }

def test_list_includes_every_card_active_or_not(open_month):
    first = cc.create_card("Nubank", today=TODAY)
    second = cc.create_card("Itau", today=TODAY)
    cc.update_card(second["id"], is_active=False, today=TODAY)
    listed = cc.list_cards(today=TODAY)
    assert [(c["id"], c["is_active"]) for c in listed] == [(first["id"], True), (second["id"], False)]

def test_rename(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    assert cc.update_card(card["id"], name="  Nubank Ultravioleta ", today=TODAY)["name"] == "Nubank Ultravioleta"

def test_unknown_card(open_month):
    with pytest.raises(NotFoundError) as info:
        cc.update_card(999, name="x", today=TODAY)
    assert info.value.params == {"resource": "credit_card", "id": 999}

def test_deactivating_in_the_middle_of_the_month_keeps_the_total_until_the_month_closes(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 300.0, today=TODAY)
    deactivated = cc.update_card(card["id"], is_active=False, today=TODAY)
    assert deactivated["is_active"] is False
    assert deactivated["in_current_month"] is True
    assert deactivated["total"] == 300.0
    assert card_total_in_breakdown() == 300.0

def test_a_deactivated_card_is_not_in_the_next_month(open_month):
    active = cc.create_card("Nubank", today=TODAY)
    inactive = cc.create_card("Itau", today=TODAY)
    cc.update_card(inactive["id"], is_active=False, today=TODAY)

    routine.run(today=date(2026, 11, 2))
    flags = {c["id"]: c["in_current_month"] for c in cc.list_cards(today=date(2026, 11, 2))}
    assert flags == {active["id"]: True, inactive["id"]: False}

def test_reactivating_in_the_middle_of_the_month_creates_the_total_right_away(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_card(card["id"], is_active=False, today=TODAY)
    routine.run(today=date(2026, 11, 2))
    assert cc.list_cards(today=date(2026, 11, 2))[0]["in_current_month"] is False

    reactivated = cc.update_card(card["id"], is_active=True, today=date(2026, 11, 3))
    assert reactivated["is_active"] is True
    assert reactivated["in_current_month"] is True
    assert (reactivated["reported_value"], reactivated["total"]) == (0.0, 0.0)

def test_reactivating_in_the_same_month_does_not_duplicate_the_total(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 120.0, today=TODAY)
    cc.update_card(card["id"], is_active=False, today=TODAY)
    again = cc.update_card(card["id"], is_active=True, today=TODAY)
    assert again["total"] == 120.0  # o valor do mes foi mantido
    assert len(read("SELECT * FROM credit_card_month")) == 1

def test_updating_the_reported_value_sets_value_total_and_date(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    item = cc.update_reported_value(card["id"], 150.0, today=TODAY)
    assert (item["reported_value"], item["payments_total"], item["total"]) == (150.0, 0.0, 150.0)
    assert (item["updated_at"], item["days_since_update"], item["is_outdated"]) == ("2026-10-23", 0, False)
    assert card_total_in_breakdown() == 150.0

def test_an_increase_or_the_same_value_creates_no_line_but_refreshes_the_date(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    seed_card_month(card["id"], 150.0, "2026-10-20")
    same = cc.update_reported_value(card["id"], 150.0, today=TODAY)
    assert (same["updated_at"], same["days_since_update"]) == ("2026-10-23", 0)
    item = cc.update_reported_value(card["id"], 180.0, today=TODAY)
    assert item["entries"] == []
    assert item["updated_at"] == "2026-10-23"
    assert entries_in_db() == []

def test_plan_example_1_pay_everything_in_the_middle_of_the_month_and_keep_using_the_card(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    assert cc.update_reported_value(card["id"], 150.0, today=TODAY)["total"] == 150.0

    paid = cc.register_payment(card["id"], 150.0, today=TODAY)
    assert (paid["reported_value"], paid["payments_total"], paid["total"]) == (0.0, 150.0, 150.0)
    assert [(e["type"], e["amount"]) for e in paid["entries"]] == [("payment", 150.0)]

    again = cc.update_reported_value(card["id"], 50.0, today=TODAY)  # gastou mais 50
    assert (again["reported_value"], again["payments_total"], again["total"]) == (50.0, 150.0, 200.0)
    assert card_total_in_breakdown() == 200.0

def test_plan_example_2_partial_payment_stores_the_difference(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 50.0, today=TODAY)
    item = cc.update_reported_value(card["id"], 30.0, "payment", today=TODAY)
    assert [(e["type"], e["amount"]) for e in item["entries"]] == [("payment", 20.0)]
    assert (item["reported_value"], item["total"]) == (30.0, 50.0)

def test_a_refund_makes_the_total_shrink(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 100.0, today=TODAY)
    item = cc.update_reported_value(card["id"], 60.0, "refund", today=TODAY)
    assert [(e["type"], e["amount"]) for e in item["entries"]] == [("refund", 40.0)]
    assert (item["payments_total"], item["total"]) == (0.0, 60.0)

def test_a_decrease_without_type_asks_for_it_and_changes_nothing(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    seed_card_month(card["id"], 100.0, "2026-10-20")
    with pytest.raises(ValueDecreasedError) as info:
        cc.update_reported_value(card["id"], 60.0, today=TODAY)
    assert info.value.code == "value_decreased"
    assert info.value.params == {"difference": 40.0}

    item = cc.list_cards(today=TODAY)[0]
    assert (item["reported_value"], item["updated_at"], item["entries"]) == (100.0, "2026-10-20", [])

def test_the_second_submission_with_the_type_works(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 100.0, today=TODAY)
    with pytest.raises(ValueDecreasedError):
        cc.update_reported_value(card["id"], 70.0, today=TODAY)
    item = cc.update_reported_value(card["id"], 70.0, "payment", today=TODAY)
    assert item["entries"][0]["amount"] == 30.0

def test_invalid_values_and_types_are_refused(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    with pytest.raises(ValueError):
        cc.update_reported_value(card["id"], -1.0, today=TODAY)
    with pytest.raises(ValueError):
        cc.update_reported_value(card["id"], 10.0, "purchase", today=TODAY)

def test_reported_value_without_an_open_month_or_for_unknown_cards(db_path):
    card = cc.create_card("Nubank", today=TODAY)
    with pytest.raises(NoOpenMonthError):
        cc.update_reported_value(card["id"], 10.0, today=TODAY)
    with pytest.raises(NotFoundError):
        cc.update_reported_value(999, 10.0, today=TODAY)

def test_a_card_without_a_total_in_the_month_cannot_be_updated(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_card(card["id"], is_active=False, today=TODAY)
    routine.run(today=date(2026, 11, 2))
    with pytest.raises(NotFoundError) as info:
        cc.update_reported_value(card["id"], 10.0, today=date(2026, 11, 2))
    assert info.value.params == {"resource": "credit_card_month", "id": card["id"]}

def test_partial_payment_reduces_the_reported_value(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 100.0, today=TODAY)
    item = cc.register_payment(card["id"], 30.0, today=TODAY)
    assert (item["reported_value"], item["payments_total"], item["total"]) == (70.0, 30.0, 100.0)

def test_payment_greater_than_the_reported_value_is_refused_and_changes_nothing(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    seed_card_month(card["id"], 100.0, "2026-10-20")
    with pytest.raises(PaymentExceedsReportedValueError) as info:
        cc.register_payment(card["id"], 100.01, today=TODAY)
    assert info.value.params == {"amount": 100.01, "reported_value": 100.0}
    item = cc.list_cards(today=TODAY)[0]
    assert (item["reported_value"], item["updated_at"], item["entries"]) == (100.0, "2026-10-20", [])

def test_payment_must_be_positive(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 100.0, today=TODAY)
    with pytest.raises(ValueError):
        cc.register_payment(card["id"], 0, today=TODAY)

def test_days_since_update_and_outdated_flag(open_month):
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 100.0, today=TODAY)

    two_days = cc.list_cards(today=date(2026, 10, 25))[0]
    assert (two_days["days_since_update"], two_days["is_outdated"]) == (2, False)
    seven_days = cc.list_cards(today=date(2026, 10, 30))[0]
    assert (seven_days["days_since_update"], seven_days["is_outdated"]) == (7, False)
    eight_days = cc.list_cards(today=date(2026, 10, 31))[0]
    assert (eight_days["days_since_update"], eight_days["is_outdated"]) == (8, True)

def card_with_a_payment_of_20():
    card = cc.create_card("Nubank", today=TODAY)
    cc.update_reported_value(card["id"], 50.0, today=TODAY)
    item = cc.update_reported_value(card["id"], 30.0, "payment", today=TODAY)
    return card["id"], item["entries"][0]["id"]

def test_editing_a_line_recalculates_the_total(open_month):
    card_id, entry_id = card_with_a_payment_of_20()
    entry = cc.update_entry(entry_id, amount=25.5, today=TODAY)
    assert entry == {"id": entry_id, "type": "payment", "amount": 25.5, "occurred_on": "2026-10-23"}
    assert cc.list_cards(today=TODAY)[0]["total"] == 55.5  # 30 + 25.5

    cc.update_entry(entry_id, entry_type="refund", today=TODAY)  # estorno nao entra no total
    assert cc.list_cards(today=TODAY)[0]["total"] == 30.0

def test_the_date_of_a_line_respects_the_month_locks(open_month):
    _, entry_id = card_with_a_payment_of_20()
    assert cc.update_entry(entry_id, occurred_on=date(2026, 10, 3), today=TODAY)["occurred_on"] == "2026-10-03"
    with pytest.raises(MonthClosedError):
        cc.update_entry(entry_id, occurred_on=date(2026, 9, 30), today=TODAY)

def test_line_must_stay_positive_and_typed(open_month):
    _, entry_id = card_with_a_payment_of_20()
    with pytest.raises(ValueError):
        cc.update_entry(entry_id, amount=0, today=TODAY)
    with pytest.raises(ValueError):
        cc.update_entry(entry_id, entry_type="purchase", today=TODAY)

def test_deleting_a_line_recalculates_the_total(open_month):
    _, entry_id = card_with_a_payment_of_20()
    assert cc.delete_entry(entry_id, today=TODAY) is None
    item = cc.list_cards(today=TODAY)[0]
    assert (item["entries"], item["total"]) == ([], 30.0)

def test_lines_of_a_closed_month_cannot_be_edited_or_deleted(open_month):
    _, entry_id = card_with_a_payment_of_20()
    routine.run(today=date(2026, 11, 2))
    with pytest.raises(MonthClosedError) as info:
        cc.update_entry(entry_id, amount=1.0, today=date(2026, 11, 2))
    assert info.value.params["closed_month"] == "2026-10"
    with pytest.raises(MonthClosedError):
        cc.delete_entry(entry_id, today=date(2026, 11, 2))
    assert len(entries_in_db()) == 1

def test_unknown_line(open_month):
    with pytest.raises(NotFoundError) as info:
        cc.update_entry(999, amount=1.0, today=TODAY)
    assert info.value.params == {"resource": "credit_card_entry", "id": 999}
    with pytest.raises(NotFoundError):
        cc.delete_entry(999, today=TODAY)

def test_each_card_keeps_its_own_lines_and_the_month_sums_all_totals(open_month):
    first = cc.create_card("Nubank", today=TODAY)
    second = cc.create_card("Itau", today=TODAY)
    cc.update_reported_value(first["id"], 150.0, today=TODAY)
    cc.register_payment(first["id"], 20.0, today=TODAY)
    cc.update_reported_value(second["id"], 0.1, today=TODAY)

    listed = {c["id"]: c for c in cc.list_cards(today=TODAY)}
    assert [e["amount"] for e in listed[first["id"]]["entries"]] == [20.0]
    assert listed[second["id"]]["entries"] == []
    assert card_total_in_breakdown() == 150.1  
