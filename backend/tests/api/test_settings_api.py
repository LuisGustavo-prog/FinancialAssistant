import pytest


def test_before_the_first_salary_both_values_are_null(client):
    assert client.get("/settings").json() == {"current_salary": None, "current_month_salary": None}


def test_the_first_salary_creates_the_first_month(client):
    response = client.put("/settings", json={"current_salary": 3000})
    assert response.status_code == 200
    assert response.json() == {"current_salary": 3000.0, "current_month_salary": 3000.0}
    assert client.get("/settings").json() == response.json()
    assert client.get("/home").json()["status"] == "ok"


def test_changing_the_current_salary_recalculates_the_open_month(ready):
    ready.put("/settings", json={"current_salary": 4200.5})
    assert ready.get("/settings").json() == {"current_salary": 4200.5, "current_month_salary": 4200.5}
    assert ready.get("/home").json()["free_balance"] == 4200.5


def test_the_salary_is_rounded_to_cents(client):
    response = client.put("/settings", json={"current_salary": 3000.004})
    assert response.json()["current_salary"] == 3000.0


@pytest.mark.parametrize("body", [{}, {"current_salary": -1}, {"current_salary": "muito"}, {"current_salary": None}])
def test_invalid_salary_bodies(client, body):
    response = client.put("/settings", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
    assert client.get("/settings").json()["current_salary"] is None


def test_month_salary_changes_only_the_open_month(ready):
    response = ready.patch("/months/current/salary", json={"salary": 3300})
    assert response.status_code == 200
    assert response.json() == {"current_salary": 3000.0, "current_month_salary": 3300.0}


def test_month_salary_without_an_open_month(client):
    response = client.patch("/months/current/salary", json={"salary": 3300})
    assert response.status_code == 409
    assert response.json() == {
        "code": "no_open_month",
        "message": "Informe o seu salário em Cadastros antes de fazer lançamentos.",
        "params": {},
    }
