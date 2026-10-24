from datetime import date
import pytest
from app.controllers import catalog_controller as catalog
from app.controllers import month_routine_controller as routine
from app.controllers.session import session
from app.errors import DefaultCategoryLockedError, NameAlreadyExistsError, NotFoundError
from tests.controllers.conftest import read

KINDS = [
    pytest.param(
        catalog.list_fixed_expenses,
        catalog.create_fixed_expense,
        catalog.update_fixed_expense,
        "month_fixed_expense",
        "fixed_expense",
        id="fixed_expenses",
    ),
    pytest.param(
        catalog.list_savings_quotas,
        catalog.create_savings_quota,
        catalog.update_savings_quota,
        "month_savings_quota",
        "savings_quota",
        id="savings_quotas",
    ),
]

def copies(table, month_id):
    return read(f"SELECT template_id, name, amount FROM {table} WHERE month_id = ? ORDER BY id", (month_id,))

def open_month_id():
    return read("SELECT id FROM month WHERE status = 'open'")[0]["id"]

@pytest.mark.parametrize(("list_", "create", "update", "table", "resource"), KINDS)
class TestTemplates:
    def test_create_returns_the_item_with_its_id(self, db_path, list_, create, update, table, resource):
        item = create("  Aluguel  ", 1200.0)
        assert item == {"id": item["id"], "name": "Aluguel", "amount": 1200.0, "is_active": True}
        assert list_() == [item]

    def test_create_without_an_open_month_creates_no_copy(self, db_path, list_, create, update, table, resource):
        create("Aluguel", 1200.0)
        assert read(f"SELECT * FROM {table}") == []

    def test_create_with_an_open_month_adds_the_copy_to_it(self, seed_october, list_, create, update, table, resource):
        seed_october()
        month_id = open_month_id()
        before = len(copies(table, month_id))
        item = create("Internet", 100.0)
        rows = copies(table, month_id)
        assert len(rows) == before + 1
        assert rows[-1] == {"template_id": item["id"], "name": "Internet", "amount": 100.0}

    def test_changing_the_amount_updates_the_open_month_copy(self, seed_october, list_, create, update, table, resource):
        seed_october()
        item = create("Internet", 100.0)
        updated = update(item["id"], amount=129.9)
        assert updated["amount"] == 129.9
        assert copies(table, open_month_id())[-1]["amount"] == 129.9

    def test_closed_months_never_change(self, seed_october, list_, create, update, table, resource):
        seeded = seed_october()
        item = create("Internet", 100.0)
        routine.run(today=date(2026, 11, 2))  
        update(item["id"], amount=150.0)

        october = [r for r in copies(table, seeded["month_id"]) if r["template_id"] == item["id"]]
        november = [r for r in copies(table, open_month_id()) if r["template_id"] == item["id"]]
        assert [r["amount"] for r in october] == [100.0]
        assert [r["amount"] for r in november] == [150.0]

    def test_deactivating_removes_the_copy_from_the_open_month_and_reactivating_brings_it_back(
        self, seed_october, list_, create, update, table, resource
    ):
        seed_october()
        item = create("Internet", 100.0)
        month_id = open_month_id()

        assert update(item["id"], is_active=False)["is_active"] is False
        assert item["id"] not in [r["template_id"] for r in copies(table, month_id)]

        assert update(item["id"], is_active=True)["is_active"] is True
        assert item["id"] in [r["template_id"] for r in copies(table, month_id)]

    def test_deactivated_template_stays_in_the_list_and_is_not_copied_to_new_months(
        self, seed_october, list_, create, update, table, resource
    ):
        seed_october()
        item = create("Internet", 100.0)
        update(item["id"], is_active=False)
        assert item["id"] in [t["id"] for t in list_()]
        routine.run(today=date(2026, 11, 2))
        assert item["id"] not in [r["template_id"] for r in copies(table, open_month_id())]

    def test_patch_changes_only_the_given_fields(self, db_path, list_, create, update, table, resource):
        item = create("Internet", 100.0)
        renamed = update(item["id"], name="  Internet fibra ")
        assert (renamed["name"], renamed["amount"], renamed["is_active"]) == ("Internet fibra", 100.0, True)

    def test_renaming_updates_the_open_month_copy(self, seed_october, list_, create, update, table, resource):
        seed_october()
        item = create("Internet", 100.0)
        update(item["id"], name="Internet fibra")
        assert copies(table, open_month_id())[-1]["name"] == "Internet fibra"

    def test_unknown_id(self, db_path, list_, create, update, table, resource):
        with pytest.raises(NotFoundError) as info:
            update(999, amount=10.0)
        assert info.value.code == "not_found"
        assert info.value.params == {"resource": resource, "id": 999}

    def test_amount_is_rounded(self, db_path, list_, create, update, table, resource):
        assert create("Luz", 150.004)["amount"] == 150.0

def test_fixed_expenses_and_savings_quotas_are_separate_lists(db_path):
    catalog.create_fixed_expense("Aluguel", 1200.0)
    catalog.create_savings_quota("Reserva", 300.0)
    assert [i["name"] for i in catalog.list_fixed_expenses()] == ["Aluguel"]
    assert [i["name"] for i in catalog.list_savings_quotas()] == ["Reserva"]

def test_the_default_category_comes_first(db_path):
    assert catalog.list_categories() == [{"id": 1, "name": "Outros", "is_default": True, "is_active": True}]

def test_create_category_returns_the_item_with_its_id(db_path):
    item = catalog.create_category("  Mercado ")
    assert item == {"id": item["id"], "name": "Mercado", "is_default": False, "is_active": True}
    assert [c["name"] for c in catalog.list_categories()] == ["Outros", "Mercado"]

def test_duplicate_name_is_refused_ignoring_case(db_path):
    catalog.create_category("Mercado")
    with pytest.raises(NameAlreadyExistsError) as info:
        catalog.create_category("mercado")
    assert info.value.code == "name_already_exists"
    assert info.value.params == {"name": "mercado"}
    assert len(catalog.list_categories()) == 2

def test_cannot_create_a_category_named_like_the_default(db_path):
    with pytest.raises(NameAlreadyExistsError):
        catalog.create_category("outros")

def test_rename_deactivate_and_reactivate(db_path):
    item = catalog.create_category("Mercado")
    assert catalog.update_category(item["id"], name="Supermercado")["name"] == "Supermercado"
    assert catalog.update_category(item["id"], is_active=False)["is_active"] is False
    assert catalog.update_category(item["id"], is_active=True)["is_active"] is True
    assert catalog.list_categories()[-1]["name"] == "Supermercado"

def test_renaming_to_the_same_name_with_other_case_is_allowed(db_path):
    item = catalog.create_category("mercado")
    assert catalog.update_category(item["id"], name="Mercado")["name"] == "Mercado"

def test_renaming_to_another_existing_name_is_refused(db_path):
    catalog.create_category("Mercado")
    other = catalog.create_category("Lazer")
    with pytest.raises(NameAlreadyExistsError):
        catalog.update_category(other["id"], name="MERCADO")
    assert catalog.list_categories()[-1]["name"] == "Lazer"

def test_the_default_category_cannot_be_deactivated_but_can_be_renamed(db_path):
    with pytest.raises(DefaultCategoryLockedError) as info:
        catalog.update_category(1, is_active=False)
    assert info.value.code == "default_category_locked"
    assert catalog.list_categories()[0]["is_active"] is True
    assert catalog.update_category(1, name="Diversos")["name"] == "Diversos"

def test_unknown_category(db_path):
    with pytest.raises(NotFoundError) as info:
        catalog.update_category(999, name="x")
    assert info.value.params == {"resource": "category", "id": 999}

def test_category_in_use_can_still_be_deactivated(db_path):
    item = catalog.create_category("Mercado")
    with session() as conn:
        conn.execute("INSERT INTO month (year, month_number, status, salary) VALUES (2026, 10, 'open', 100)")
        conn.execute(
            "INSERT INTO expense (month_id, amount, occurred_on, category_id) VALUES (1, 10, '2026-10-05', ?)",
            (item["id"],),
        )
    assert catalog.update_category(item["id"], is_active=False)["is_active"] is False
