import sqlite3
import pytest
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings

def test_settings_starts_empty(conn):
    row = settings.get(conn)
    assert type(row) is dict
    assert row == {"current_salary": None, "last_checked_date": None, "pending_notices": "[]"}

def test_settings_setters_update_the_single_row(conn):
    settings.set_current_salary(conn, 3500.5)
    settings.set_last_checked_date(conn, "2026-10-23")
    settings.set_pending_notices(conn, '[{"id": 1, "code": "unused_months", "params": {}}]')
    row = settings.get(conn)
    assert row["current_salary"] == 3500.5
    assert row["last_checked_date"] == "2026-10-23"
    assert row["pending_notices"] == '[{"id": 1, "code": "unused_months", "params": {}}]'
    assert conn.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 1

def test_settings_keep_the_schema_rules(conn):
    with pytest.raises(sqlite3.IntegrityError):
        settings.set_last_checked_date(conn, "2026-02-30")
    with pytest.raises(sqlite3.IntegrityError):
        settings.set_pending_notices(conn, "not json")
    with pytest.raises(sqlite3.IntegrityError):
        settings.set_current_salary(conn, 100.123)

def test_no_open_month_before_the_first_salary(conn):
    assert months.get_open_month(conn) is None
    assert months.list_closed_months(conn) == []

def test_create_month_returns_the_id_and_opens_it(conn):
    month_id = months.create_month(conn, 2026, 10, 3000.0)
    month = months.get_open_month(conn)
    assert month["id"] == month_id
    assert (month["year"], month["month_number"], month["salary"]) == (2026, 10, 3000.0)
    assert month["status"] == "open"
    assert month["result"] is None and month["closed_at"] is None
    assert months.get_month(conn, month_id) == month

def test_get_month_of_unknown_id_is_none(conn):
    assert months.get_month(conn, 999) is None

def test_second_open_month_is_refused_by_the_schema(conn):
    months.create_month(conn, 2026, 10, 3000.0)
    with pytest.raises(sqlite3.IntegrityError):
        months.create_month(conn, 2026, 11, 3000.0)

def test_close_month_writes_the_result_and_frees_the_open_slot(conn):
    month_id = months.create_month(conn, 2026, 10, 3000.0)
    assert months.close_month(conn, month_id, 249.25, "green", "2026-11-01", "pending") is True

    assert months.get_open_month(conn) is None
    closed = months.get_month(conn, month_id)
    assert closed["status"] == "closed"
    assert closed["final_balance"] == 249.25
    assert closed["result"] == "green"
    assert closed["closed_at"] == "2026-11-01"
    assert closed["leftover_decision"] == "pending"
    months.create_month(conn, 2026, 11, 3000.0)  

def test_close_month_twice_does_not_change_anything(conn):
    month_id = months.create_month(conn, 2026, 10, 3000.0)
    months.close_month(conn, month_id, 249.25, "green", "2026-11-01", "pending")
    assert months.close_month(conn, month_id, -5.0, "red", "2026-12-01", None) is False
    month = months.get_month(conn, month_id)
    assert (month["final_balance"], month["result"], month["closed_at"]) == (
        249.25,
        "green",
        "2026-11-01",
    )

def test_close_month_with_inconsistent_values_is_refused_by_the_schema(conn):
    month_id = months.create_month(conn, 2026, 10, 3000.0)
    with pytest.raises(sqlite3.IntegrityError):
        months.close_month(conn, month_id, -50.0, "green", "2026-11-01", None)

def test_list_closed_months_is_oldest_first_and_only_closed(conn):
    for year, month in [(2026, 9), (2025, 12), (2026, 1)]:
        month_id = months.create_month(conn, year, month, 1000.0)
        months.close_month(conn, month_id, 0.0, "green", "2026-10-01", None)
    months.create_month(conn, 2026, 10, 1000.0)
    listed = months.list_closed_months(conn)
    assert [(m["year"], m["month_number"]) for m in listed] == [(2025, 12), (2026, 1), (2026, 9)]

def test_update_salary_only_works_on_an_open_month(conn):
    month_id = months.create_month(conn, 2026, 10, 3000.0)
    assert months.update_salary(conn, month_id, 3200.0) is True
    assert months.get_month(conn, month_id)["salary"] == 3200.0

    months.close_month(conn, month_id, 100.0, "green", "2026-11-01", "pending")
    assert months.update_salary(conn, month_id, 9999.0) is False
    assert months.get_month(conn, month_id)["salary"] == 3200.0

def test_leftover_decision_can_only_be_set_once(conn):
    month_id = months.create_month(conn, 2026, 10, 3000.0)
    months.close_month(conn, month_id, 100.0, "green", "2026-11-01", "pending")

    assert months.set_leftover_decision(conn, month_id, "carried") is True
    assert months.set_leftover_decision(conn, month_id, "declined") is False  
    assert months.get_month(conn, month_id)["leftover_decision"] == "carried"

def test_leftover_decision_does_not_apply_to_month_without_leftover(conn):
    month_id = months.create_month(conn, 2026, 10, 1000.0)
    months.close_month(conn, month_id, -20.0, "red", "2026-11-01", None)
    assert months.set_leftover_decision(conn, month_id, "carried") is False

def test_leftover_decision_does_not_apply_to_an_open_month(conn):
    month_id = months.create_month(conn, 2026, 10, 1000.0)
    assert months.set_leftover_decision(conn, month_id, "carried") is False

COPY_KINDS = [
    pytest.param(
        months.list_fixed_expenses,
        months.insert_fixed_expense,
        months.update_fixed_expense,
        months.delete_fixed_expense,
        months.sum_fixed_expenses,
        "fixed_expense_template",
        id="fixed_expenses",
    ),
    pytest.param(
        months.list_savings_quotas,
        months.insert_savings_quota,
        months.update_savings_quota,
        months.delete_savings_quota,
        months.sum_savings_quotas,
        "savings_quota_template",
        id="savings_quotas",
    ),
]

@pytest.fixture
def month_id(conn):
    return months.create_month(conn, 2026, 10, 3000.0)

@pytest.mark.parametrize(("list_", "insert", "update", "delete", "total", "template_table"), COPY_KINDS)
class TestCopies:
    def test_insert_and_list_in_order(self, conn, month_id, list_, insert, update, delete, total, template_table):
        first = insert(conn, month_id, None, "Aluguel", 1200.0)
        second = insert(conn, month_id, None, "Internet", 100.0)
        rows = list_(conn, month_id)
        assert [r["id"] for r in rows] == [first, second]
        assert rows[0] == {
            "id": first,
            "month_id": month_id,
            "template_id": None,
            "name": "Aluguel",
            "amount": 1200.0,
        }

    def test_update_changes_name_and_amount(self, conn, month_id, list_, insert, update, delete, total, template_table):
        copy_id = insert(conn, month_id, None, "Aluguel", 1200.0)
        assert update(conn, copy_id, "Aluguel do apto", 1350.0) is True
        assert list_(conn, month_id)[0]["name"] == "Aluguel do apto"
        assert list_(conn, month_id)[0]["amount"] == 1350.0
        assert update(conn, 999, "x", 1.0) is False

    def test_delete_removes_only_that_copy(self, conn, month_id, list_, insert, update, delete, total, template_table):
        keep = insert(conn, month_id, None, "Luz", 150.0)
        gone = insert(conn, month_id, None, "Agua", 80.0)
        assert delete(conn, gone) is True
        assert [r["id"] for r in list_(conn, month_id)] == [keep]
        assert delete(conn, gone) is False

    def test_total_is_rounded_and_float_even_when_empty(self, conn, month_id, list_, insert, update, delete, total, template_table):
        empty = total(conn, month_id)
        assert empty == 0.0 and isinstance(empty, float)
        insert(conn, month_id, None, "A", 0.1)
        insert(conn, month_id, None, "B", 0.2)
        assert total(conn, month_id) == 0.3

    def test_each_month_only_sees_its_own_copies(self, conn, month_id, list_, insert, update, delete, total, template_table):
        months.close_month(conn, month_id, 0.0, "green", "2026-11-01", None)
        other_month = months.create_month(conn, 2026, 11, 3000.0)
        insert(conn, month_id, None, "Antigo", 500.0)
        insert(conn, other_month, None, "Novo", 70.0)
        assert [r["name"] for r in list_(conn, other_month)] == ["Novo"]
        assert total(conn, other_month) == 70.0
        assert total(conn, month_id) == 500.0

    def test_the_same_template_cannot_be_copied_twice_into_a_month(self, conn, month_id, list_, insert, update, delete, total, template_table):
        template_id = conn.execute(
            f"INSERT INTO {template_table} (name, amount) VALUES ('Modelo', 100)"
        ).lastrowid
        insert(conn, month_id, template_id, "Modelo", 100.0)
        with pytest.raises(sqlite3.IntegrityError):
            insert(conn, month_id, template_id, "Modelo", 100.0)

    def test_invalid_amount_is_refused_by_the_schema(self, conn, month_id, list_, insert, update, delete, total, template_table):
        with pytest.raises(sqlite3.IntegrityError):
            insert(conn, month_id, None, "Errado", 10.999)
