import json
from datetime import date, datetime, timezone
import pytest
from app.controllers import clock, month_routine_controller as routine
from app.controllers.month_routine_controller import RoutineResult
from app.controllers.session import session
from app.db.repositories import settings_repository as settings
from tests.controllers.conftest import read

def month_of(year, month_number):
    rows = read("SELECT * FROM month WHERE year = ? AND month_number = ?", (year, month_number))
    return rows[0] if rows else None

def stored_notices():
    with session() as conn:
        return json.loads(settings.get(conn)["pending_notices"])

def last_checked():
    with session() as conn:
        return settings.get(conn)["last_checked_date"]

def test_first_run_without_salary_creates_no_month_but_records_the_date(db_path):
    result = routine.run(today=date(2026, 10, 23))
    assert result == RoutineResult(date(2026, 10, 23), None, None)
    assert read("SELECT * FROM month") == []
    assert last_checked() == "2026-10-23"

def test_a_new_day_in_the_same_month_changes_only_the_checked_date(seed_october):
    seed_october(last_checked="2026-10-20")
    result = routine.run(today=date(2026, 10, 23))
    assert (result.closed_month_id, result.created_month_id) == (None, None)
    assert last_checked() == "2026-10-23"
    assert month_of(2026, 10)["status"] == "open"
    assert len(read("SELECT * FROM month")) == 1

def test_a_second_run_on_the_same_day_does_nothing(seed_october):
    seed_october(last_checked="2026-10-20")
    routine.run(today=date(2026, 10, 23))
    result = routine.run(today=date(2026, 10, 23))
    assert result == RoutineResult(date(2026, 10, 23), None, None)
    assert len(read("SELECT * FROM month")) == 1

def test_month_turn_closes_october_and_opens_november(seed_october):
    seeded = seed_october()
    result = routine.run(today=date(2026, 11, 2))

    october = month_of(2026, 10)
    assert result.closed_month_id == seeded["month_id"] == october["id"]
    assert october["status"] == "closed"
    assert october["final_balance"] == 249.25
    assert october["result"] == "green"
    assert october["closed_at"] == "2026-11-02"
    assert october["leftover_decision"] == "pending"

    november = month_of(2026, 11)
    assert result.created_month_id == november["id"]
    assert november["status"] == "open"
    assert november["salary"] == 3500.0  
    assert last_checked() == "2026-11-02"
    assert stored_notices() == []

def test_new_month_copies_active_templates_and_gives_each_active_card_a_zero_total(seed_october):
    seed_october()
    result = routine.run(today=date(2026, 11, 2))
    month_id = result.created_month_id

    fixed = read("SELECT name, amount FROM month_fixed_expense WHERE month_id = ?", (month_id,))
    assert fixed == [{"name": "Aluguel", "amount": 1200.0}]  # a desativada nao entra
    quotas = read("SELECT name, amount FROM month_savings_quota WHERE month_id = ?", (month_id,))
    assert quotas == [{"name": "Reserva", "amount": 300.0}]

    card_months = read("SELECT reported_value, updated_at FROM credit_card_month WHERE month_id = ?", (month_id,))
    assert card_months == [{"reported_value": 0.0, "updated_at": None}]

def test_closed_month_keeps_its_own_copies_and_expenses(seed_october):
    seeded = seed_october()
    routine.run(today=date(2026, 11, 2))
    assert len(read("SELECT * FROM month_fixed_expense WHERE month_id = ?", (seeded["month_id"],))) == 1
    assert len(read("SELECT * FROM expense WHERE month_id = ?", (seeded["month_id"],))) == 1

def test_negative_month_is_red_and_stores_the_notice(seed_october):
    seed_october(debit=2000.0)  
    routine.run(today=date(2026, 11, 2))
    october = month_of(2026, 10)
    assert (october["result"], october["final_balance"], october["leftover_decision"]) == ("red", -1300.25, None)
    assert stored_notices() == [
        {
            "id": 1,
            "code": "month_closed_negative",
            "params": {"closed_month": "2026-10", "current_month": "2026-11", "final_balance": -1300.25},
        }
    ]

def test_months_without_use_are_not_created_and_leave_a_notice(seed_october):
    seed_october()
    result = routine.run(today=date(2027, 1, 15))
    assert month_of(2026, 11) is None and month_of(2026, 12) is None
    assert month_of(2027, 1)["id"] == result.created_month_id
    assert stored_notices() == [
        {"id": 1, "code": "unused_months", "params": {"months": ["2026-11", "2026-12"]}}
    ]

def test_new_notices_get_ids_after_the_existing_ones(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2027, 1, 15))  # negativo e meses sem uso
    assert [n["id"] for n in stored_notices()] == [1, 2]
    assert [n["code"] for n in stored_notices()] == ["month_closed_negative", "unused_months"]

def test_running_twice_after_the_turn_does_not_duplicate_anything(seed_october):
    seed_october(debit=2000.0)
    routine.run(today=date(2026, 11, 2))
    routine.run(today=date(2026, 11, 2))
    routine.run(today=date(2026, 11, 3))
    assert len(read("SELECT * FROM month")) == 2
    assert len(stored_notices()) == 1
    assert len(read("SELECT * FROM month_fixed_expense")) == 2  # uma copia em outubro, uma em novembro

def test_clock_going_back_never_reopens_a_closed_month(seed_october):
    seed_october()
    routine.run(today=date(2026, 11, 5))
    result = routine.run(today=date(2026, 10, 20))  # o relogio voltou para outubro
    assert result.today == date(2026, 11, 5)
    assert (result.closed_month_id, result.created_month_id) == (None, None)
    assert month_of(2026, 10)["status"] == "closed"
    assert month_of(2026, 11)["status"] == "open"
    assert last_checked() == "2026-11-05"


def freeze_utc(monkeypatch, *args):
    monkeypatch.setattr(clock, "_utc_now", lambda: datetime(*args, tzinfo=timezone.utc))


def test_at_9pm_in_brasilia_on_the_last_day_the_month_has_not_turned(seed_october, monkeypatch):
    seed_october()
    freeze_utc(monkeypatch, 2026, 11, 1, 0, 0)  
    result = routine.run()
    assert result.today == date(2026, 10, 31)
    assert result.closed_month_id is None
    assert month_of(2026, 10)["status"] == "open"
    assert month_of(2026, 11) is None

def test_at_midnight_in_brasilia_the_month_turns(seed_october, monkeypatch):
    seed_october()
    freeze_utc(monkeypatch, 2026, 11, 1, 3, 0)  
    result = routine.run()
    assert result.today == date(2026, 11, 1)
    assert result.closed_month_id is not None
    assert month_of(2026, 11)["status"] == "open"

def test_a_failure_in_the_middle_undoes_the_whole_turn(seed_october, monkeypatch):
    seed_october()

    def explode(*args, **kwargs):
        raise RuntimeError("falha ao criar o total do cartao")

    with monkeypatch.context() as patch:
        patch.setattr(routine.cards, "insert_card_month", explode)
        with pytest.raises(RuntimeError):
            routine.run(today=date(2026, 11, 2))

    assert month_of(2026, 10)["status"] == "open"  
    assert month_of(2026, 11) is None
    assert last_checked() == "2026-10-30"
    assert stored_notices() == []

    routine.run(today=date(2026, 11, 2))  
    assert month_of(2026, 10)["status"] == "closed"
    assert month_of(2026, 11)["status"] == "open"
