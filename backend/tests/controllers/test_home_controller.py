from datetime import date
import pytest
from app.controllers import credit_card_controller as cc
from app.controllers import expense_controller as expenses_ctl
from app.controllers import home_controller as home_ctl
from app.controllers import month_controller as month_ctl
from app.controllers import month_routine_controller as routine
from app.controllers import settings_controller as settings_ctl
from app.controllers.session import session
from app.db.repositories import settings_repository as settings
import json


def stored_notices():
    with session() as conn:
        return json.loads(settings.get(conn)["pending_notices"])


@pytest.fixture
def open_month(db_path):
    settings_ctl.save_current_salary(3000.0, today=date(2026, 10, 1))


def test_before_the_first_salary_the_home_needs_setup(db_path):
    assert home_ctl.get_home(today=date(2026, 10, 23)) == {"status": "needs_setup"}


def test_after_the_first_salary_the_home_is_ok(open_month):
    assert home_ctl.get_home(today=date(2026, 10, 1))["status"] == "ok"


def test_home_has_the_month_the_balance_and_the_breakdown(seed_october):
    seeded = seed_october()
    home = home_ctl.get_home(today=date(2026, 10, 30))
    assert home["status"] == "ok"
    assert home["month"] == {
        "id": seeded["month_id"],
        "year": 2026,
        "month_number": 10,
        "status": "open",
        "days_left": 1,
    }
    assert home["free_balance"] == 249.25
    assert home["breakdown"] == {
        "salary": 3000.0,
        "extra_incomes": 0.0,
        "fixed_expenses": 1200.0,
        "savings_quotas": 300.0,
        "debit_expenses": 450.5,
        "credit_card_total": 800.25,
    }
    assert home["pending_leftover"] is None


def test_the_free_balance_follows_every_launch(open_month):
    expenses_ctl.create_expense(10.9, today=date(2026, 10, 1))
    expenses_ctl.create_expense(10.9, today=date(2026, 10, 1))
    home = home_ctl.get_home(today=date(2026, 10, 1))
    assert home["breakdown"]["debit_expenses"] == 21.8
    assert home["free_balance"] == 2978.2


def test_recent_expenses_are_the_newest_five(open_month):
    ids = [expenses_ctl.create_expense(1.0, date(2026, 10, day), today=date(2026, 10, 10))["id"] for day in range(1, 8)]
    recent = home_ctl.get_home(today=date(2026, 10, 10))["recent_expenses"]
    assert [e["id"] for e in recent] == [ids[6], ids[5], ids[4], ids[3], ids[2]]
    assert recent[0]["category"] == {"id": 1, "name": "Outros"}


def test_home_without_expenses_has_an_empty_list(open_month):
    assert home_ctl.get_home(today=date(2026, 10, 1))["recent_expenses"] == []


def test_no_notices_on_a_quiet_day(open_month):
    assert home_ctl.get_home(today=date(2026, 10, 5))["notices"] == []


def test_month_ending_notice_in_the_last_three_days(open_month):
    notices = home_ctl.get_home(today=date(2026, 10, 30))["notices"]
    assert notices == [{"id": None, "code": "month_ending", "params": {"days_left": 1, "has_active_cards": False}}]


def test_month_ending_notice_knows_about_active_cards(open_month):
    cc.create_card("Nubank", today=date(2026, 10, 1))
    cc.update_reported_value(1, 10.0, today=date(2026, 10, 30))
    notices = home_ctl.get_home(today=date(2026, 10, 31))["notices"]
    assert notices[0]["params"] == {"days_left": 0, "has_active_cards": True}


def test_card_not_updated_notice_from_day_ten(open_month):
    cc.create_card("Nubank", today=date(2026, 10, 1))
    cc.create_card("Itau", today=date(2026, 10, 1))
    assert home_ctl.get_home(today=date(2026, 10, 9))["notices"] == []
    notices = home_ctl.get_home(today=date(2026, 10, 10))["notices"]
    assert notices == [{"id": None, "code": "credit_card_not_updated", "params": {"card_names": ["Nubank", "Itau"]}}]

    cc.update_reported_value(1, 100.0, today=date(2026, 10, 12))
    notices = home_ctl.get_home(today=date(2026, 10, 12))["notices"]
    assert notices[0]["params"] == {"card_names": ["Itau"]}


def test_a_deactivated_card_does_not_trigger_the_not_updated_notice(open_month):
    card = cc.create_card("Nubank", today=date(2026, 10, 1))
    cc.update_card(card["id"], is_active=False, today=date(2026, 10, 1))
    assert home_ctl.get_home(today=date(2026, 10, 20))["notices"] == []


def test_negative_month_notice_comes_first_with_an_id_and_can_be_dismissed(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2026, 11, 2))
    notices = home_ctl.get_home(today=date(2026, 11, 2))["notices"]
    assert notices == [
        {
            "id": 1,
            "code": "month_closed_negative",
            "params": {"closed_month": "2026-10", "current_month": "2026-11", "final_balance": -1300.25},
        }
    ]

    assert home_ctl.dismiss_notice(1) is None
    assert home_ctl.get_home(today=date(2026, 11, 2))["notices"] == []
    assert stored_notices() == []


def test_dismissing_twice_or_an_unknown_id_is_harmless(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2026, 11, 2))
    home_ctl.dismiss_notice(1)
    home_ctl.dismiss_notice(1)
    home_ctl.dismiss_notice(999)
    assert stored_notices() == []


def test_dismissing_one_notice_keeps_the_others_in_order(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2027, 1, 15))
    home_ctl.dismiss_notice(1)
    notices = home_ctl.get_home(today=date(2027, 1, 15))["notices"]
    assert [(n["id"], n["code"]) for n in notices] == [
        (2, "unused_months"),
        (None, "credit_card_not_updated"),
    ]


def test_notices_come_stored_first_then_month_ending_then_card(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2026, 11, 29))
    notices = home_ctl.get_home(today=date(2026, 11, 29))["notices"]
    assert [(n["id"], n["code"]) for n in notices] == [
        (1, "month_closed_negative"),
        (None, "month_ending"),
        (None, "credit_card_not_updated"),
    ]


def test_pending_leftover_after_the_month_turn(seed_october):
    seeded = seed_october()
    routine.run(today=date(2026, 11, 2))
    home = home_ctl.get_home(today=date(2026, 11, 2))
    assert home["pending_leftover"] == {
        "month_id": seeded["month_id"],
        "year": 2026,
        "month_number": 10,
        "amount": 249.25,
    }
    assert home["month"]["month_number"] == 11


def test_no_leftover_question_when_the_month_closed_negative(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2026, 11, 2))
    assert home_ctl.get_home(today=date(2026, 11, 2))["pending_leftover"] is None


def test_the_leftover_questions_come_one_at_a_time_oldest_first(seed_october):
    seeded = seed_october()
    routine.run(today=date(2026, 11, 2))
    routine.run(today=date(2026, 12, 2))

    first = home_ctl.get_home(today=date(2026, 12, 2))["pending_leftover"]
    assert (first["month_number"], first["month_id"], first["amount"]) == (10, seeded["month_id"], 249.25)

    month_ctl.decide_leftover(first["month_id"], "declined", today=date(2026, 12, 2))
    second = home_ctl.get_home(today=date(2026, 12, 2))["pending_leftover"]
    assert (second["month_number"], second["amount"]) == (11, 2000.0)

    month_ctl.decide_leftover(second["month_id"], "declined", today=date(2026, 12, 2))
    assert home_ctl.get_home(today=date(2026, 12, 2))["pending_leftover"] is None


def test_carrying_the_leftover_raises_the_balance_and_clears_the_question(seed_october):
    seeded = seed_october()
    routine.run(today=date(2026, 11, 2))
    before = home_ctl.get_home(today=date(2026, 11, 2))["free_balance"]
    month_ctl.decide_leftover(seeded["month_id"], "carried", today=date(2026, 11, 2))

    home = home_ctl.get_home(today=date(2026, 11, 2))
    assert before == 2000.0
    assert home["breakdown"]["extra_incomes"] == 249.25
    assert home["free_balance"] == 2249.25
    assert home["pending_leftover"] is None
