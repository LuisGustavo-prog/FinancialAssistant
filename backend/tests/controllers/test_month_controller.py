from datetime import date
import pytest
from app.controllers import extra_income_controller as incomes_ctl
from app.controllers import month_controller as month_ctl
from app.controllers import month_routine_controller as routine
from app.errors import LeftoverIncomeLockedError, LeftoverNotPendingError, NotFoundError
from tests.controllers.conftest import read

NOVEMBER_2 = date(2026, 11, 2)

@pytest.fixture
def october_closed(seed_october):
    seeded = seed_october()
    routine.run(today=NOVEMBER_2)
    return seeded

def leftover_incomes():
    return read("SELECT amount, occurred_on, description, source FROM extra_income WHERE source = 'leftover'")

def test_history_is_empty_without_closed_months(db_path):
    assert month_ctl.list_months() == []

def test_history_lists_closed_months_newest_first(october_closed):
    routine.run(today=date(2026, 12, 2))
    items = month_ctl.list_months()
    assert [(m["year"], m["month_number"]) for m in items] == [(2026, 11), (2026, 10)]
    october = items[1]
    assert october == {
        "id": october_closed["month_id"],
        "year": 2026,
        "month_number": 10,
        "status": "closed",
        "result": "green",
        "final_balance": 249.25,
        "leftover_decision": "pending",
    }

def test_months_without_use_do_not_appear_in_the_history(seed_october):
    seed_october()
    routine.run(today=date(2027, 1, 15))
    assert [(m["year"], m["month_number"]) for m in month_ctl.list_months()] == [(2026, 10)]

def test_month_detail(october_closed):
    detail = month_ctl.get_month(october_closed["month_id"])
    assert detail["result"] == "green"
    assert detail["final_balance"] == 249.25
    assert detail["breakdown"] == {
        "salary": 3000.0,
        "extra_incomes": 0.0,
        "fixed_expenses": 1200.0,
        "savings_quotas": 300.0,
        "debit_expenses": 450.5,
        "credit_card_total": 800.25,
    }
    assert [(e["amount"], e["occurred_on"]) for e in detail["expenses"]] == [(450.5, "2026-10-05")]
    assert detail["expenses"][0]["category"]["name"] == "Outros"
    assert detail["fixed_expenses"] == [{"name": "Aluguel", "amount": 1200.0}]
    assert detail["savings_quotas"] == [{"name": "Reserva", "amount": 300.0}]
    assert detail["credit_cards"] == [
        {"id": october_closed["card_id"], "name": "Nubank", "total": 800.25}
    ]
    assert detail["extra_incomes"] == []

def test_the_detail_breakdown_matches_the_stored_final_balance(october_closed):
    detail = month_ctl.get_month(october_closed["month_id"])
    b = detail["breakdown"]
    balance = round(
        b["salary"] + b["extra_incomes"] - b["fixed_expenses"] - b["savings_quotas"]
        - b["debit_expenses"] - b["credit_card_total"],
        2,
    )
    assert balance == detail["final_balance"]

def test_the_detail_of_a_closed_month_never_offers_editing(db_path, seed_october):
    seeded = seed_october()
    incomes_ctl.create_extra_income(200.0, date(2026, 10, 10), "Freela", today=date(2026, 10, 30))
    routine.run(today=NOVEMBER_2)
    detail = month_ctl.get_month(seeded["month_id"])
    assert [(i["description"], i["is_editable"]) for i in detail["extra_incomes"]] == [("Freela", False)]


def test_the_detail_shows_each_card_total_with_payments_but_without_refunds(seed_october):
    from app.controllers import credit_card_controller as cc

    seeded = seed_october()
    cc.register_payment(seeded["card_id"], 100.0, today=date(2026, 10, 30))  
    cc.update_reported_value(seeded["card_id"], 650.25, "refund", today=date(2026, 10, 30))  
    routine.run(today=NOVEMBER_2)
    detail = month_ctl.get_month(seeded["month_id"])
    assert detail["credit_cards"][0]["total"] == 750.25
    assert detail["breakdown"]["credit_card_total"] == 750.25

def test_detail_of_the_open_month_or_of_an_unknown_month_is_not_found(october_closed):
    open_month_id = read("SELECT id FROM month WHERE status = 'open'")[0]["id"]
    for bad_id in (open_month_id, 999):
        with pytest.raises(NotFoundError) as info:
            month_ctl.get_month(bad_id)
        assert info.value.params == {"resource": "month", "id": bad_id}

def test_carrying_creates_a_locked_income_in_the_current_month(october_closed):
    result = month_ctl.decide_leftover(october_closed["month_id"], "carried", today=NOVEMBER_2)

    assert result["leftover_decision"] == "carried"
    income = result["extra_income"]
    assert (income["amount"], income["occurred_on"], income["description"]) == (249.25, "2026-11-02", "Sobra de outubro")
    assert (income["source"], income["is_editable"]) == ("leftover", False)

    november = read("SELECT id FROM month WHERE status = 'open'")[0]["id"]
    assert read("SELECT month_id FROM extra_income")[0]["month_id"] == november
    assert month_ctl.get_month(october_closed["month_id"])["leftover_decision"] == "carried"

def test_the_carried_income_cannot_be_edited_or_deleted(october_closed):
    result = month_ctl.decide_leftover(october_closed["month_id"], "carried", today=NOVEMBER_2)
    income_id = result["extra_income"]["id"]
    with pytest.raises(LeftoverIncomeLockedError):
        incomes_ctl.update_extra_income(income_id, amount=1.0, today=NOVEMBER_2)
    with pytest.raises(LeftoverIncomeLockedError):
        incomes_ctl.delete_extra_income(income_id, today=NOVEMBER_2)

def test_declining_only_marks_the_decision(october_closed):
    result = month_ctl.decide_leftover(october_closed["month_id"], "declined", today=NOVEMBER_2)
    assert result["leftover_decision"] == "declined"
    assert result["extra_income"] is None
    assert leftover_incomes() == []

def test_answering_twice_is_refused_and_creates_only_one_income(october_closed):
    month_ctl.decide_leftover(october_closed["month_id"], "carried", today=NOVEMBER_2)
    with pytest.raises(LeftoverNotPendingError) as info:
        month_ctl.decide_leftover(october_closed["month_id"], "carried", today=NOVEMBER_2)
    assert info.value.code == "leftover_not_pending"
    assert info.value.params == {"decision": "carried"}
    assert len(leftover_incomes()) == 1

def test_a_late_answer_enters_the_month_of_the_answer(october_closed):
    routine.run(today=date(2027, 1, 15))
    result = month_ctl.decide_leftover(october_closed["month_id"], "carried", today=date(2027, 1, 15))
    income = result["extra_income"]
    assert (income["occurred_on"], income["description"]) == ("2027-01-15", "Sobra de outubro")
    january = read("SELECT id FROM month WHERE status = 'open'")[0]["id"]
    assert read("SELECT month_id FROM extra_income")[0]["month_id"] == january

def test_a_month_without_leftover_cannot_be_decided(seed_october):
    seeded = seed_october(debit=2000.0)  
    routine.run(today=NOVEMBER_2)
    with pytest.raises(LeftoverNotPendingError) as info:
        month_ctl.decide_leftover(seeded["month_id"], "carried", today=NOVEMBER_2)
    assert info.value.params == {"decision": None}

def test_the_open_month_and_unknown_months_cannot_be_decided(october_closed):
    open_month_id = read("SELECT id FROM month WHERE status = 'open'")[0]["id"]
    with pytest.raises(LeftoverNotPendingError):
        month_ctl.decide_leftover(open_month_id, "carried", today=NOVEMBER_2)
    with pytest.raises(NotFoundError):
        month_ctl.decide_leftover(999, "carried", today=NOVEMBER_2)

@pytest.mark.parametrize("bad", ["pending", "maybe", ""])
def test_the_decision_must_be_carried_or_declined(october_closed, bad):
    with pytest.raises(ValueError):
        month_ctl.decide_leftover(october_closed["month_id"], bad, today=NOVEMBER_2)
    assert month_ctl.list_months()[0]["leftover_decision"] == "pending"
