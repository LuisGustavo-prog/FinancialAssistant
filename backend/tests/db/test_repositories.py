import sqlite3

import pytest

from app.db.repositories import category_repository as categories
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import expense_repository as expenses
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months
from app.db.repositories import settings_repository as settings
from app.db.repositories import template_repository as templates


# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# month: leitura e criacao
# --------------------------------------------------------------------------
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


# --------------------------------------------------------------------------
# month: fechamento
# --------------------------------------------------------------------------
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
    months.create_month(conn, 2026, 11, 3000.0)  # agora cabe o novo mes aberto


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


# --------------------------------------------------------------------------
# month: salario e sobra
# --------------------------------------------------------------------------
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
    assert months.set_leftover_decision(conn, month_id, "declined") is False  # duplo clique
    assert months.get_month(conn, month_id)["leftover_decision"] == "carried"


def test_leftover_decision_does_not_apply_to_month_without_leftover(conn):
    month_id = months.create_month(conn, 2026, 10, 1000.0)
    months.close_month(conn, month_id, -20.0, "red", "2026-11-01", None)
    assert months.set_leftover_decision(conn, month_id, "carried") is False


def test_leftover_decision_does_not_apply_to_an_open_month(conn):
    month_id = months.create_month(conn, 2026, 10, 1000.0)
    assert months.set_leftover_decision(conn, month_id, "carried") is False


# --------------------------------------------------------------------------
# Copias do mes: gastos fixos e cotas (mesmo formato, mesmas funcoes)
# --------------------------------------------------------------------------
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

    def test_total_is_rounded_and_float_even_when_empty(
        self, conn, month_id, list_, insert, update, delete, total, template_table
    ):
        empty = total(conn, month_id)
        assert empty == 0.0 and isinstance(empty, float)
        insert(conn, month_id, None, "A", 0.1)
        insert(conn, month_id, None, "B", 0.2)
        assert total(conn, month_id) == 0.3

    def test_each_month_only_sees_its_own_copies(
        self, conn, month_id, list_, insert, update, delete, total, template_table
    ):
        months.close_month(conn, month_id, 0.0, "green", "2026-11-01", None)
        other_month = months.create_month(conn, 2026, 11, 3000.0)
        insert(conn, month_id, None, "Antigo", 500.0)
        insert(conn, other_month, None, "Novo", 70.0)
        assert [r["name"] for r in list_(conn, other_month)] == ["Novo"]
        assert total(conn, other_month) == 70.0
        assert total(conn, month_id) == 500.0

    def test_the_same_template_cannot_be_copied_twice_into_a_month(
        self, conn, month_id, list_, insert, update, delete, total, template_table
    ):
        template_id = conn.execute(f"INSERT INTO {template_table} (name, amount) VALUES ('Modelo', 100)").lastrowid
        insert(conn, month_id, template_id, "Modelo", 100.0)
        with pytest.raises(sqlite3.IntegrityError):
            insert(conn, month_id, template_id, "Modelo", 100.0)

    def test_invalid_amount_is_refused_by_the_schema(
        self, conn, month_id, list_, insert, update, delete, total, template_table
    ):
        with pytest.raises(sqlite3.IntegrityError):
            insert(conn, month_id, None, "Errado", 10.999)


# --------------------------------------------------------------------------
# Modelos (gastos fixos e cotas, mesmo formato)
# --------------------------------------------------------------------------
TEMPLATE_KINDS = [
    pytest.param(
        templates.list_fixed_expense_templates,
        templates.get_fixed_expense_template,
        templates.insert_fixed_expense_template,
        templates.update_fixed_expense_template,
        id="fixed_expense_templates",
    ),
    pytest.param(
        templates.list_savings_quota_templates,
        templates.get_savings_quota_template,
        templates.insert_savings_quota_template,
        templates.update_savings_quota_template,
        id="savings_quota_templates",
    ),
]


@pytest.mark.parametrize(("list_", "get", "insert", "update"), TEMPLATE_KINDS)
class TestTemplates:
    def test_insert_creates_an_active_template(self, conn, list_, get, insert, update):
        template_id = insert(conn, "Aluguel", 1200.0)
        assert get(conn, template_id) == {
            "id": template_id,
            "name": "Aluguel",
            "amount": 1200.0,
            "is_active": 1,
        }

    def test_list_includes_inactive_templates_in_creation_order(self, conn, list_, get, insert, update):
        first = insert(conn, "Aluguel", 1200.0)
        second = insert(conn, "Academia", 99.9)
        update(conn, second, "Academia", 99.9, False)
        listed = list_(conn)
        assert [t["id"] for t in listed] == [first, second]
        assert [t["is_active"] for t in listed] == [1, 0]

    def test_update_changes_everything_and_can_reactivate(self, conn, list_, get, insert, update):
        template_id = insert(conn, "Luz", 150.0)
        assert update(conn, template_id, "Energia", 180.5, False) is True
        assert get(conn, template_id) == {
            "id": template_id,
            "name": "Energia",
            "amount": 180.5,
            "is_active": 0,
        }
        update(conn, template_id, "Energia", 180.5, True)
        assert get(conn, template_id)["is_active"] == 1

    def test_unknown_id(self, conn, list_, get, insert, update):
        assert get(conn, 999) is None
        assert update(conn, 999, "x", 1.0, True) is False

    def test_schema_rules_still_apply(self, conn, list_, get, insert, update):
        with pytest.raises(sqlite3.IntegrityError):
            insert(conn, "Errado", 0)
        template_id = insert(conn, "Certo", 10.0)
        with pytest.raises(sqlite3.IntegrityError):
            update(conn, template_id, "Certo", 10.001, True)


# --------------------------------------------------------------------------
# Categorias
# --------------------------------------------------------------------------
def test_default_category_outros_exists(conn):
    default = categories.get_default_category(conn)
    assert (default["name"], default["is_default"], default["is_active"]) == ("Outros", 1, 1)
    assert [c["name"] for c in categories.list_categories(conn)] == ["Outros"]


def test_insert_category_is_active_and_not_default(conn):
    category_id = categories.insert_category(conn, "Mercado")
    assert categories.get_category(conn, category_id) == {
        "id": category_id,
        "name": "Mercado",
        "is_default": 0,
        "is_active": 1,
    }


def test_category_name_is_unique_ignoring_case(conn):
    categories.insert_category(conn, "Mercado")
    with pytest.raises(sqlite3.IntegrityError):
        categories.insert_category(conn, "mercado")


def test_rename_deactivate_and_reactivate_a_category(conn):
    category_id = categories.insert_category(conn, "Mercado")
    assert categories.update_category(conn, category_id, "Supermercado", False) is True
    row = categories.get_category(conn, category_id)
    assert (row["name"], row["is_active"]) == ("Supermercado", 0)
    categories.update_category(conn, category_id, "Supermercado", True)
    assert categories.get_category(conn, category_id)["is_active"] == 1
    assert [c["id"] for c in categories.list_categories(conn)][-1] == category_id


def test_the_default_category_cannot_be_deactivated(conn):
    default = categories.get_default_category(conn)
    with pytest.raises(sqlite3.IntegrityError):
        categories.update_category(conn, default["id"], default["name"], False)


def test_unknown_category(conn):
    assert categories.get_category(conn, 999) is None
    assert categories.update_category(conn, 999, "x", True) is False


# --------------------------------------------------------------------------
# Gastos no debito
# --------------------------------------------------------------------------
def add_expense(conn, month_id, amount=10.9, occurred_on="2026-10-05", description=None, category_id=None):
    if category_id is None:
        category_id = categories.get_default_category(conn)["id"]
    return expenses.insert_expense(conn, month_id, amount, occurred_on, description, category_id)


def test_expense_comes_with_the_category_name(conn, month_id):
    category_id = categories.insert_category(conn, "Mercado")
    expense_id = add_expense(conn, month_id, 45.5, "2026-10-07", "Compras da semana", category_id)
    assert expenses.get_expense(conn, expense_id) == {
        "id": expense_id,
        "month_id": month_id,
        "amount": 45.5,
        "occurred_on": "2026-10-07",
        "description": "Compras da semana",
        "category_id": category_id,
        "category_name": "Mercado",
        "payment_method": "debit",
    }


def test_expenses_are_listed_newest_first_by_date_then_id(conn, month_id):
    a = add_expense(conn, month_id, occurred_on="2026-10-05")
    b = add_expense(conn, month_id, occurred_on="2026-10-20")
    c = add_expense(conn, month_id, occurred_on="2026-10-05")
    assert [e["id"] for e in expenses.list_expenses(conn, month_id)] == [b, c, a]


def test_recent_expenses_respect_the_limit(conn, month_id):
    ids = [add_expense(conn, month_id, occurred_on=f"2026-10-{day:02d}") for day in range(1, 8)]
    recent = expenses.list_recent_expenses(conn, month_id, 3)
    assert [e["id"] for e in recent] == [ids[6], ids[5], ids[4]]


def test_update_expense_changes_all_fields(conn, month_id):
    expense_id = add_expense(conn, month_id)
    other = categories.insert_category(conn, "Lazer")
    assert expenses.update_expense(conn, expense_id, 99.99, "2026-10-12", "Cinema", other) is True
    row = expenses.get_expense(conn, expense_id)
    assert (row["amount"], row["occurred_on"], row["description"], row["category_name"]) == (
        99.99,
        "2026-10-12",
        "Cinema",
        "Lazer",
    )
    assert expenses.update_expense(conn, 999, 1.0, "2026-10-12", None, other) is False


def test_delete_expense(conn, month_id):
    expense_id = add_expense(conn, month_id)
    assert expenses.delete_expense(conn, expense_id) is True
    assert expenses.get_expense(conn, expense_id) is None
    assert expenses.delete_expense(conn, expense_id) is False


def test_expense_total_is_rounded_float_and_zero_when_empty(conn, month_id):
    empty = expenses.sum_expenses(conn, month_id)
    assert empty == 0.0 and isinstance(empty, float)
    add_expense(conn, month_id, 0.1)
    add_expense(conn, month_id, 0.2)
    assert expenses.sum_expenses(conn, month_id) == 0.3


def test_each_month_only_sees_its_own_expenses(conn, month_id):
    months.close_month(conn, month_id, 0.0, "green", "2026-11-01", None)
    other_month = months.create_month(conn, 2026, 11, 3000.0)
    add_expense(conn, month_id, 500.0)
    add_expense(conn, other_month, 70.0)
    assert [e["amount"] for e in expenses.list_expenses(conn, other_month)] == [70.0]
    assert expenses.sum_expenses(conn, other_month) == 70.0
    assert expenses.list_recent_expenses(conn, month_id, 10)[0]["amount"] == 500.0


def test_expense_with_unknown_category_is_refused(conn, month_id):
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, month_id, category_id=999)


# --------------------------------------------------------------------------
# Rendas extras
# --------------------------------------------------------------------------
def add_income(conn, month_id, amount=200.0, occurred_on="2026-10-10", description="Freela", source="manual"):
    return incomes.insert_extra_income(conn, month_id, amount, occurred_on, description, source)


def test_insert_and_get_extra_income(conn, month_id):
    income_id = add_income(conn, month_id)
    assert incomes.get_extra_income(conn, income_id) == {
        "id": income_id,
        "month_id": month_id,
        "amount": 200.0,
        "occurred_on": "2026-10-10",
        "description": "Freela",
        "source": "manual",
    }
    assert incomes.get_extra_income(conn, 999) is None


def test_extra_incomes_are_listed_newest_first(conn, month_id):
    a = add_income(conn, month_id, occurred_on="2026-10-02")
    b = add_income(conn, month_id, occurred_on="2026-10-15")
    assert [i["id"] for i in incomes.list_extra_incomes(conn, month_id)] == [b, a]


def test_update_extra_income_keeps_the_source(conn, month_id):
    income_id = add_income(conn, month_id, description="Sobra de setembro", source="leftover")
    assert incomes.update_extra_income(conn, income_id, 250.0, "2026-10-11", "Outro texto") is True
    row = incomes.get_extra_income(conn, income_id)
    assert (row["amount"], row["occurred_on"], row["description"], row["source"]) == (
        250.0,
        "2026-10-11",
        "Outro texto",
        "leftover",
    )
    assert incomes.update_extra_income(conn, 999, 1.0, "2026-10-11", None) is False


def test_delete_extra_income(conn, month_id):
    income_id = add_income(conn, month_id)
    assert incomes.delete_extra_income(conn, income_id) is True
    assert incomes.delete_extra_income(conn, income_id) is False


def test_extra_income_total_is_rounded_float_and_zero_when_empty(conn, month_id):
    empty = incomes.sum_extra_incomes(conn, month_id)
    assert empty == 0.0 and isinstance(empty, float)
    add_income(conn, month_id, 0.1)
    add_income(conn, month_id, 0.2)
    assert incomes.sum_extra_incomes(conn, month_id) == 0.3


def test_extra_income_with_invalid_source_is_refused(conn, month_id):
    with pytest.raises(sqlite3.IntegrityError):
        add_income(conn, month_id, source="gift")


# --------------------------------------------------------------------------
# Cartoes de credito
# --------------------------------------------------------------------------
def test_cards_can_be_created_renamed_and_deactivated_never_deleted(conn):
    first = cards.insert_card(conn, "Nubank")
    second = cards.insert_card(conn, "Itau")
    assert cards.update_card(conn, second, "Itau Platinum", False) is True
    assert [(c["id"], c["name"], c["is_active"]) for c in cards.list_cards(conn)] == [
        (first, "Nubank", 1),
        (second, "Itau Platinum", 0),
    ]
    assert cards.list_active_card_ids(conn) == [first]
    cards.update_card(conn, second, "Itau Platinum", True)
    assert cards.list_active_card_ids(conn) == [first, second]
    assert cards.get_card(conn, 999) is None
    assert cards.update_card(conn, 999, "x", True) is False


def test_card_month_is_born_zero_and_never_updated(conn, month_id):
    card_id = cards.insert_card(conn, "Nubank")
    card_month_id = cards.insert_card_month(conn, card_id, month_id)
    assert cards.get_card_month(conn, card_id, month_id) == {
        "id": card_month_id,
        "credit_card_id": card_id,
        "month_id": month_id,
        "reported_value": 0.0,
        "updated_at": None,
        "card_name": "Nubank",
        "is_active": 1,
    }
    assert cards.get_card_month(conn, 999, month_id) is None


def test_card_month_is_unique_per_card_and_month(conn, month_id):
    card_id = cards.insert_card(conn, "Nubank")
    cards.insert_card_month(conn, card_id, month_id)
    with pytest.raises(sqlite3.IntegrityError):
        cards.insert_card_month(conn, card_id, month_id)


def test_update_reported_value_sets_the_value_and_the_date(conn, month_id):
    card_id = cards.insert_card(conn, "Nubank")
    card_month_id = cards.insert_card_month(conn, card_id, month_id)
    assert cards.update_reported_value(conn, card_month_id, 150.0, "2026-10-12") is True
    row = cards.get_card_month(conn, card_id, month_id)
    assert (row["reported_value"], row["updated_at"]) == (150.0, "2026-10-12")
    assert cards.update_reported_value(conn, 999, 1.0, "2026-10-12") is False


def test_list_card_months_includes_deactivated_cards_with_total_in_the_month(conn, month_id):
    active = cards.insert_card(conn, "Nubank")
    inactive = cards.insert_card(conn, "Itau")
    no_total = cards.insert_card(conn, "Inter")
    cards.insert_card_month(conn, active, month_id)
    cards.insert_card_month(conn, inactive, month_id)
    cards.update_card(conn, inactive, "Itau", False)
    listed = cards.list_card_months(conn, month_id)
    assert [(c["credit_card_id"], c["card_name"], c["is_active"]) for c in listed] == [
        (active, "Nubank", 1),
        (inactive, "Itau", 0),
    ]
    assert no_total not in [c["credit_card_id"] for c in listed]


def test_card_months_of_other_months_are_not_listed(conn, month_id):
    card_id = cards.insert_card(conn, "Nubank")
    cards.insert_card_month(conn, card_id, month_id)
    months.close_month(conn, month_id, 0.0, "green", "2026-11-01", None)
    other_month = months.create_month(conn, 2026, 11, 3000.0)
    assert cards.list_card_months(conn, other_month) == []


@pytest.fixture
def card_month_id(conn, month_id):
    card_id = cards.insert_card(conn, "Nubank")
    return cards.insert_card_month(conn, card_id, month_id)


def test_entries_are_listed_by_date_then_id(conn, card_month_id):
    late = cards.insert_entry(conn, card_month_id, "payment", 100.0, "2026-10-20")
    early = cards.insert_entry(conn, card_month_id, "refund", 30.0, "2026-10-05")
    same_day = cards.insert_entry(conn, card_month_id, "payment", 10.0, "2026-10-05")
    assert [e["id"] for e in cards.list_entries(conn, card_month_id)] == [early, same_day, late]


def test_get_entry_knows_its_month_and_card(conn, month_id, card_month_id):
    entry_id = cards.insert_entry(conn, card_month_id, "payment", 100.0, "2026-10-20")
    row = cards.get_entry(conn, entry_id)
    assert row["month_id"] == month_id
    assert row["credit_card_month_id"] == card_month_id
    assert row["credit_card_id"] == cards.get_card_month(conn, row["credit_card_id"], month_id)["credit_card_id"]
    assert (row["type"], row["amount"], row["occurred_on"]) == ("payment", 100.0, "2026-10-20")
    assert cards.get_entry(conn, 999) is None


def test_update_and_delete_entry(conn, card_month_id):
    entry_id = cards.insert_entry(conn, card_month_id, "payment", 100.0, "2026-10-20")
    assert cards.update_entry(conn, entry_id, "refund", 60.0, "2026-10-21") is True
    row = cards.list_entries(conn, card_month_id)[0]
    assert (row["type"], row["amount"], row["occurred_on"]) == ("refund", 60.0, "2026-10-21")
    assert cards.update_entry(conn, 999, "payment", 1.0, "2026-10-21") is False
    assert cards.delete_entry(conn, entry_id) is True
    assert cards.delete_entry(conn, entry_id) is False
    assert cards.list_entries(conn, card_month_id) == []


def test_list_entries_by_month_gathers_all_cards_in_one_query(conn, month_id):
    first_card = cards.insert_card(conn, "Nubank")
    second_card = cards.insert_card(conn, "Itau")
    first = cards.insert_card_month(conn, first_card, month_id)
    second = cards.insert_card_month(conn, second_card, month_id)
    a = cards.insert_entry(conn, second, "payment", 10.0, "2026-10-03")
    b = cards.insert_entry(conn, first, "payment", 20.0, "2026-10-09")
    c = cards.insert_entry(conn, first, "refund", 5.0, "2026-10-01")
    listed = cards.list_entries_by_month(conn, month_id)
    assert [e["id"] for e in listed] == [c, b, a]  # agrupado por cartao do mes, depois por data


def test_entry_schema_rules_still_apply(conn, card_month_id):
    with pytest.raises(sqlite3.IntegrityError):
        cards.insert_entry(conn, card_month_id, "purchase", 10.0, "2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):
        cards.insert_entry(conn, card_month_id, "payment", 0, "2026-10-05")
    with pytest.raises(sqlite3.IntegrityError):
        cards.insert_entry(conn, card_month_id, "payment", 10.0, "2026-02-30")
