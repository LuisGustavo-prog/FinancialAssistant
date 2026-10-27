import pytest

KINDS = [
    pytest.param("/fixed-expenses", "o gasto fixo", id="fixed_expenses"),
    pytest.param("/savings-quotas", "a cota", id="savings_quotas"),
]


@pytest.mark.parametrize(("path", "resource_name"), KINDS)
class TestTemplates:
    def test_create_list_and_patch(self, ready, path, resource_name):
        created = ready.post(path, json={"name": "  Internet ", "amount": 100})
        assert created.status_code == 201
        item = created.json()
        assert item == {"id": item["id"], "name": "Internet", "amount": 100.0, "is_active": True}
        assert ready.get(path).json() == [item]

        patched = ready.patch(f"{path}/{item['id']}", json={"amount": 129.9})
        assert patched.status_code == 200
        assert patched.json() == {**item, "amount": 129.9}

        deactivated = ready.patch(f"{path}/{item['id']}", json={"is_active": False})
        assert deactivated.json()["is_active"] is False
        assert ready.get(path).json()[0]["is_active"] is False

    @pytest.mark.parametrize(
        "body",
        [
            {"name": "", "amount": 10},
            {"name": "x", "amount": 0},
            {"name": "x"},
            {"amount": 10},
            {"name": "a" * 101, "amount": 10},
        ],
    )
    def test_invalid_bodies(self, ready, path, resource_name, body):
        response = ready.post(path, json=body)
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"
        assert ready.get(path).json() == []

    def test_unknown_id(self, ready, path, resource_name):
        response = ready.patch(f"{path}/999", json={"amount": 10})
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"
        assert response.json()["message"] == f"Não encontramos {resource_name}."


def test_a_new_fixed_expense_reaches_the_open_month(ready):
    ready.post("/fixed-expenses", json={"name": "Aluguel", "amount": 1200})
    home = ready.get("/home").json()
    assert home["breakdown"]["fixed_expenses"] == 1200.0
    assert home["free_balance"] == 1800.0


def test_a_new_savings_quota_reaches_the_open_month(ready):
    ready.post("/savings-quotas", json={"name": "Reserva", "amount": 300})
    assert ready.get("/home").json()["breakdown"]["savings_quotas"] == 300.0


# --------------------------------------------------------------------------
# Categorias
# --------------------------------------------------------------------------
def test_categories_start_with_the_default_one(client):
    assert client.get("/categories").json() == [{"id": 1, "name": "Outros", "is_default": True, "is_active": True}]


def test_create_rename_and_deactivate_a_category(client):
    created = client.post("/categories", json={"name": " Mercado "})
    assert created.status_code == 201
    category = created.json()
    assert category == {"id": category["id"], "name": "Mercado", "is_default": False, "is_active": True}

    renamed = client.patch(f"/categories/{category['id']}", json={"name": "Supermercado"})
    assert renamed.json()["name"] == "Supermercado"
    off = client.patch(f"/categories/{category['id']}", json={"is_active": False})
    assert off.json()["is_active"] is False


def test_duplicate_category_name_ignoring_case(client):
    client.post("/categories", json={"name": "Mercado"})
    response = client.post("/categories", json={"name": "mercado"})
    assert response.status_code == 409
    assert response.json() == {
        "code": "name_already_exists",
        "message": 'Já existe uma categoria chamada "mercado".',
        "params": {"name": "mercado"},
    }


def test_the_default_category_cannot_be_deactivated(client):
    response = client.patch("/categories/1", json={"is_active": False})
    assert response.status_code == 409
    assert response.json()["code"] == "default_category_locked"
    assert response.json()["message"] == 'A categoria "Outros" não pode ser desativada.'


def test_unknown_category(client):
    response = client.patch("/categories/999", json={"name": "x"})
    assert (response.status_code, response.json()["code"]) == (404, "not_found")
    assert response.json()["message"] == "Não encontramos a categoria."
