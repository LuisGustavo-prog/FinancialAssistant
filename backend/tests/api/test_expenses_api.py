import pytest


def create(client, **body):
    return client.post("/expenses", json={"amount": 10.9, **body})


def test_create_with_only_the_amount_uses_today_and_outros(ready):
    response = create(ready)
    assert response.status_code == 201
    item = response.json()
    assert item == {
        "id": item["id"],
        "amount": 10.9,
        "occurred_on": "2026-10-23",
        "description": None,
        "category": {"id": 1, "name": "Outros"},
        "payment_method": "debit",
    }
    assert ready.get("/expenses").json() == [item]


def test_the_balance_drops_right_away(ready):
    create(ready)
    create(ready)
    home = ready.get("/home").json()
    assert home["breakdown"]["debit_expenses"] == 21.8
    assert home["free_balance"] == 2978.2
    assert [e["amount"] for e in home["recent_expenses"]] == [10.9, 10.9]


def test_create_with_all_fields(ready):
    category = ready.post("/categories", json={"name": "Mercado"}).json()
    response = create(ready, occurred_on="2026-10-07", description=" Compras ", category_id=category["id"])
    assert response.status_code == 201
    assert response.json()["occurred_on"] == "2026-10-07"
    assert response.json()["description"] == " Compras ".strip()
    assert response.json()["category"] == {"id": category["id"], "name": "Mercado"}


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"amount": 0},
        {"amount": -5},
        {"amount": 0.004},
        {"amount": "dez"},
        {"amount": 10, "occurred_on": "23/10/2026"},
        {"amount": 10, "occurred_on": "2026-02-30"},
        {"amount": 10, "description": "a" * 256},
        {"amount": 10, "category_id": "x"},
    ],
)
def test_invalid_bodies_are_422_and_save_nothing(ready, body):
    response = ready.post("/expenses", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert ready.get("/expenses").json() == []


def test_amount_with_more_than_two_decimals_is_rounded(ready):
    assert create(ready, amount=10.999).json()["amount"] == 11.0


def test_closed_month_date_is_422_with_the_plan_message(ready):
    response = create(ready, occurred_on="2026-09-28")
    assert response.status_code == 422
    assert response.json() == {
        "code": "month_closed",
        "message": "O mês de setembro já fechou. Quer registrar em outubro?",
        "params": {"closed_month": "2026-09", "current_month": "2026-10"},
    }


def test_future_month_date_is_422(ready):
    response = create(ready, occurred_on="2026-11-01")
    assert response.status_code == 422
    assert response.json()["code"] == "future_date"
    assert response.json()["params"] == {}


def test_unknown_and_inactive_categories(ready):
    assert create(ready, category_id=999).status_code == 404
    category = ready.post("/categories", json={"name": "Lazer"}).json()
    ready.patch(f"/categories/{category['id']}", json={"is_active": False})
    response = create(ready, category_id=category["id"])
    assert response.status_code == 422
    assert response.json()["code"] == "category_inactive"


def test_expenses_cannot_be_created_before_the_first_salary(client):
    response = client.post("/expenses", json={"amount": 10})
    assert response.status_code == 409
    assert response.json()["code"] == "no_open_month"
    assert client.get("/expenses").json() == []


# --------------------------------------------------------------------------
# Editar e apagar
# --------------------------------------------------------------------------
def test_patch_changes_only_what_was_sent(ready):
    item = create(ready, description="Padaria", occurred_on="2026-10-05").json()
    response = ready.patch(f"/expenses/{item['id']}", json={"amount": 12.5})
    assert response.status_code == 200
    assert (response.json()["amount"], response.json()["description"], response.json()["occurred_on"]) == (
        12.5,
        "Padaria",
        "2026-10-05",
    )


def test_description_null_clears_and_omitting_keeps(ready):
    item = create(ready, description="Padaria").json()
    kept = ready.patch(f"/expenses/{item['id']}", json={"amount": 11})
    assert kept.json()["description"] == "Padaria"
    cleared = ready.patch(f"/expenses/{item['id']}", json={"description": None})
    assert cleared.json()["description"] is None


def test_patch_date_rules(ready):
    item = create(ready).json()
    assert ready.patch(f"/expenses/{item['id']}", json={"occurred_on": "2026-10-02"}).status_code == 200
    assert ready.patch(f"/expenses/{item['id']}", json={"occurred_on": "2026-09-30"}).json()["code"] == "month_closed"
    assert ready.patch(f"/expenses/{item['id']}", json={"occurred_on": "2026-11-01"}).json()["code"] == "future_date"


def test_patch_and_delete_of_unknown_expense(ready):
    patch = ready.patch("/expenses/999", json={"amount": 1})
    assert (patch.status_code, patch.json()["message"]) == (404, "Não encontramos o gasto.")
    assert ready.delete("/expenses/999").status_code == 404


def test_delete_returns_204_with_no_body_and_the_balance_recovers(ready):
    keep = create(ready, amount=10).json()
    gone = create(ready, amount=25).json()
    response = ready.delete(f"/expenses/{gone['id']}")
    assert (response.status_code, response.content) == (204, b"")
    assert [e["id"] for e in ready.get("/expenses").json()] == [keep["id"]]
    assert ready.get("/home").json()["breakdown"]["debit_expenses"] == 10.0
