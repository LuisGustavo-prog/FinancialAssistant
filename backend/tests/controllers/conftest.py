import pytest
from app.controllers.session import session
from app.db.init_db import create_database
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import expense_repository as expenses
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings
from app.db.repositories import template_repository as templates


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "app.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    monkeypatch.delenv("TIMEZONE", raising=False)
    create_database(path)
    return path


@pytest.fixture
def seed_october(db_path):
    def seed(salary=3000.0, debit=450.50, card_reported=800.25, last_checked="2026-10-30"):
        with session() as conn:
            settings.set_current_salary(conn, 3500.0)
            settings.set_last_checked_date(conn, last_checked)

            fixed_active = templates.insert_fixed_expense_template(conn, "Aluguel", 1200.0)
            fixed_inactive = templates.insert_fixed_expense_template(conn, "Academia", 99.9)
            templates.update_fixed_expense_template(conn, fixed_inactive, "Academia", 99.9, False)
            quota = templates.insert_savings_quota_template(conn, "Reserva", 300.0)
            card_id = cards.insert_card(conn, "Nubank")

            month_id = months.create_month(conn, 2026, 10, salary)
            months.insert_fixed_expense(conn, month_id, fixed_active, "Aluguel", 1200.0)
            months.insert_savings_quota(conn, month_id, quota, "Reserva", 300.0)
            category_id = 1
            if debit:
                expenses.insert_expense(conn, month_id, debit, "2026-10-05", None, category_id)
            card_month_id = cards.insert_card_month(conn, card_id, month_id)
            cards.update_reported_value(conn, card_month_id, card_reported, "2026-10-28")
        return {"month_id": month_id, "card_id": card_id, "card_month_id": card_month_id}

    return seed


def read(sql, params=()):
    with session() as conn:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
