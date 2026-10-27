from datetime import date, datetime, timezone
import pytest
from app.controllers import clock, month_routine_controller as routine, settings_controller as settings_ctl
from app.controllers.breakdown import build_breakdown
from app.controllers.session import session
from app.core.balance import free_balance
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings
from app.db.repositories import template_repository as templates
from app.errors import NoOpenMonthError
from tests.controllers.conftest import read

TODAY = date(2026, 10, 23)


def last_checked():
    with session() as conn:
        return settings.get(conn)["last_checked_date"]


def test_before_the_first_salary_both_values_are_none(db_path):
    assert settings_ctl.get_settings() == {"current_salary": None, "current_month_salary": None}


def test_first_salary_creates_the_first_month(db_path):
    result = settings_ctl.save_current_salary(3000.0, today=TODAY)
    assert result == {"current_salary": 3000.0, "current_month_salary": 3000.0}

    rows = read("SELECT year, month_number, status, salary FROM month")
    assert rows == [{"year": 2026, "month_number": 10, "status": "open", "salary": 3000.0}]
    assert last_checked() == "2026-10-23"
    assert settings_ctl.get_settings() == result


def test_first_month_gets_copies_of_the_active_templates_and_a_zero_card_total(db_path):
    with session() as conn:
        active = templates.insert_fixed_expense_template(conn, "Aluguel", 1200.0)
        inactive = templates.insert_fixed_expense_template(conn, "Academia", 99.9)
        templates.update_fixed_expense_template(conn, inactive, "Academia", 99.9, False)
        templates.insert_savings_quota_template(conn, "Reserva", 300.0)
        cards.insert_card(conn, "Nubank")

    settings_ctl.save_current_salary(3000.0, today=TODAY)

    assert [r["name"] for r in read("SELECT name FROM month_fixed_expense")] == ["Aluguel"]
    assert [r["name"] for r in read("SELECT name FROM month_savings_quota")] == ["Reserva"]
    assert read("SELECT reported_value, updated_at FROM credit_card_month") == [
        {"reported_value": 0.0, "updated_at": None}
    ]
    assert active


def test_first_salary_reads_the_clock_when_no_date_is_given(db_path, monkeypatch):
    monkeypatch.setattr(clock, "_utc_now", lambda: datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc))
    settings_ctl.save_current_salary(3000.0)
    month = read("SELECT year, month_number FROM month")[0]
    assert (month["year"], month["month_number"]) == (2026, 10)


def test_the_routine_does_nothing_right_after_the_first_salary(db_path):
    settings_ctl.save_current_salary(3000.0, today=TODAY)
    result = routine.run(today=TODAY)
    assert (result.closed_month_id, result.created_month_id) == (None, None)
    assert len(read("SELECT * FROM month")) == 1


def test_changing_the_current_salary_recalculates_the_open_month(seed_october):
    seeded = seed_october()
    result = settings_ctl.save_current_salary(4000.0, today=TODAY)
    assert result == {"current_salary": 4000.0, "current_month_salary": 4000.0}
    with session() as conn:
        month = months.get_month(conn, seeded["month_id"])
        assert free_balance(build_breakdown(conn, month)) == 1249.25


def test_closed_months_keep_the_salary_they_had(seed_october):
    seeded = seed_october()
    routine.run(today=date(2026, 11, 2))
    settings_ctl.save_current_salary(5000.0, today=date(2026, 11, 3))
    with session() as conn:
        assert months.get_month(conn, seeded["month_id"])["salary"] == 3000.0
        assert months.get_open_month(conn)["salary"] == 5000.0


def test_the_new_month_born_after_a_change_uses_the_new_current_salary(seed_october):
    seed_october()
    settings_ctl.save_current_salary(4200.0, today=TODAY)
    result = routine.run(today=date(2026, 11, 2))
    with session() as conn:
        assert months.get_month(conn, result.created_month_id)["salary"] == 4200.0


def test_salary_is_rounded_and_negative_values_are_refused(db_path):
    assert settings_ctl.save_current_salary(3000.004, today=TODAY)["current_salary"] == 3000.0
    with pytest.raises(ValueError):
        settings_ctl.save_current_salary(-1.0, today=TODAY)


def test_a_failure_while_creating_the_first_month_undoes_the_salary(db_path, monkeypatch):
    with session() as conn:
        cards.insert_card(conn, "Nubank")

    def explode(*args, **kwargs):
        raise RuntimeError("falha")

    with monkeypatch.context() as patch:
        patch.setattr(routine.cards, "insert_card_month", explode)
        with pytest.raises(RuntimeError):
            settings_ctl.save_current_salary(3000.0, today=TODAY)

    assert settings_ctl.get_settings() == {"current_salary": None, "current_month_salary": None}
    assert read("SELECT * FROM month") == []


def test_month_salary_changes_without_touching_the_current_salary(seed_october):
    seeded = seed_october()
    result = settings_ctl.update_current_month_salary(3300.0)
    assert result == {"current_salary": 3500.0, "current_month_salary": 3300.0}
    with session() as conn:
        assert months.get_month(conn, seeded["month_id"])["salary"] == 3300.0


def test_month_salary_without_an_open_month_is_refused(db_path):
    with pytest.raises(NoOpenMonthError) as info:
        settings_ctl.update_current_month_salary(3300.0)
    assert info.value.code == "no_open_month"


def test_month_salary_refuses_negative_values(seed_october):
    seed_october()
    with pytest.raises(ValueError):
        settings_ctl.update_current_month_salary(-5.0)
