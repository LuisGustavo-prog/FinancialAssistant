import pytest


def create(client, **body):
    return client.post("/extra-incomes", json={"amount": 200, **body})


def test_create_list_patch_and_delete(ready):
    created = create(ready, description=" Freela ")
    assert created.status_code == 201
    item = created.json()
    assert item == {
        "id": item["id"],
        "amount": 200.0,
        "occurred_on": "2026-10-23",
        "description": "Freela",
        "source": "manual",
        "is_editable": True,
    }
    assert ready.get("/extra-incomes").json() == [item]
    assert ready.get("/home").json()["breakdown"]["extra_incomes"] == 200.0

    patched = ready.patch(f"/extra-incomes/{item['id']}", json={"amount": 250, "description": None})
    assert (patched.json()["amount"], patched.json()["description"]) == (250.0, None)

    assert ready.delete(f"/extra-incomes/{item['id']}").status_code == 204
    assert ready.get("/extra-incomes").json() == []


@pytest.mark.parametrize("body", [{}, {"amount": 0}, {"amount": 0.004}, {"amount": 10, "occurred_on": "x"}])
def test_invalid_bodies(ready, body):
    response = ready.post("/extra-incomes", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_date_rules(ready):
    assert create(ready, occurred_on="2026-09-30").json()["code"] == "month_closed"
    assert create(ready, occurred_on="2026-11-02").json()["code"] == "future_date"


def test_without_an_open_month(client):
    assert create(client).json()["code"] == "no_open_month"


def test_unknown_income(ready):
    response = ready.patch("/extra-incomes/999", json={"amount": 1})
    assert (response.status_code, response.json()["message"]) == (404, "Não encontramos a renda extra.")
    assert ready.delete("/extra-incomes/999").status_code == 404
