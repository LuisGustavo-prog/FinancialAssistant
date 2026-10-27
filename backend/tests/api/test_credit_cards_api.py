import pytest


@pytest.fixture
def card(ready):
    response = ready.post("/credit-cards", json={"name": "Nubank"})
    assert response.status_code == 201
    return response.json()


def put_value(client, card_id, value, **extra):
    return client.put(f"/credit-cards/{card_id}/current-month", json={"reported_value": value, **extra})


def card_state(client, card_id):
    return next(c for c in client.get("/credit-cards").json() if c["id"] == card_id)


def test_a_new_card_comes_with_a_zero_total_in_the_open_month(card):
    assert card == {
        "id": card["id"],
        "name": "Nubank",
        "is_active": True,
        "in_current_month": True,
        "reported_value": 0.0,
        "payments_total": 0.0,
        "total": 0.0,
        "updated_at": None,
        "days_since_update": None,
        "is_outdated": True,
        "entries": [],
    }


def test_card_created_before_the_first_salary_is_outside_the_month(client):
    created = client.post("/credit-cards", json={"name": "Nubank"}).json()
    assert created["in_current_month"] is False
    assert created["total"] is None and created["updated_at"] is None


def test_updating_the_reported_value(ready, card):
    response = put_value(ready, card["id"], 150)
    assert response.status_code == 200
    state = response.json()
    assert (
        state["reported_value"],
        state["total"],
        state["updated_at"],
        state["days_since_update"],
        state["is_outdated"],
    ) == (
        150.0,
        150.0,
        "2026-10-23",
        0,
        False,
    )
    assert ready.get("/home").json()["breakdown"]["credit_card_total"] == 150.0


def test_value_decreased_flow_ask_then_send_again_with_the_type(ready, card):
    put_value(ready, card["id"], 100)

    asked = put_value(ready, card["id"], 60)
    assert asked.status_code == 409
    assert asked.json() == {
        "code": "value_decreased",
        "message": "O valor do cartão diminuiu R$ 40,00. Foi um pagamento ou um estorno?",
        "params": {"difference": 40.0},
    }
    assert card_state(ready, card["id"])["reported_value"] == 100.0  # nada mudou

    sent = put_value(ready, card["id"], 60, type="payment")
    assert sent.status_code == 200
    assert [(e["type"], e["amount"]) for e in sent.json()["entries"]] == [("payment", 40.0)]
    assert (sent.json()["reported_value"], sent.json()["total"]) == (60.0, 100.0)


def test_a_refund_makes_the_total_shrink(ready, card):
    put_value(ready, card["id"], 100)
    state = put_value(ready, card["id"], 60, type="refund").json()
    assert [(e["type"], e["amount"]) for e in state["entries"]] == [("refund", 40.0)]
    assert state["total"] == 60.0


@pytest.mark.parametrize(
    "body", [{}, {"reported_value": -1}, {"reported_value": 10, "type": "purchase"}, {"reported_value": "x"}]
)
def test_invalid_reported_value_bodies(ready, card, body):
    response = ready.put(f"/credit-cards/{card['id']}/current-month", json=body)
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_register_payment(ready, card):
    put_value(ready, card["id"], 150)
    response = ready.post(f"/credit-cards/{card['id']}/current-month/payments", json={"amount": 150})
    assert response.status_code == 201
    state = response.json()
    assert (state["reported_value"], state["payments_total"], state["total"]) == (0.0, 150.0, 150.0)

    again = put_value(ready, card["id"], 50).json()  # gastou mais 50
    assert (again["reported_value"], again["total"]) == (50.0, 200.0)


def test_payment_greater_than_the_reported_value(ready, card):
    put_value(ready, card["id"], 100)
    response = ready.post(f"/credit-cards/{card['id']}/current-month/payments", json={"amount": 100.01})
    assert response.status_code == 422
    assert response.json() == {
        "code": "payment_exceeds_reported_value",
        "message": "O pagamento de R$ 100,01 é maior que o valor informado do cartão (R$ 100,00).",
        "params": {"amount": 100.01, "reported_value": 100.0},
    }
    assert card_state(ready, card["id"])["entries"] == []


@pytest.mark.parametrize("amount", [0, -5, "x"])
def test_invalid_payment_amounts(ready, card, amount):
    response = ready.post(f"/credit-cards/{card['id']}/current-month/payments", json={"amount": amount})
    assert (response.status_code, response.json()["code"]) == (422, "validation_error")


def test_rename_deactivate_and_reactivate(ready, card):
    assert (
        ready.patch(f"/credit-cards/{card['id']}", json={"name": "Nubank Ultravioleta"}).json()["name"]
        == "Nubank Ultravioleta"
    )
    off = ready.patch(f"/credit-cards/{card['id']}", json={"is_active": False}).json()
    assert (off["is_active"], off["in_current_month"]) == (False, True)  # vale ate o mes fechar
    on = ready.patch(f"/credit-cards/{card['id']}", json={"is_active": True}).json()
    assert on["is_active"] is True


def test_unknown_card_and_empty_name(ready):
    assert ready.patch("/credit-cards/999", json={"name": "x"}).status_code == 404
    assert put_value(ready, 999, 10).json()["message"] == "Não encontramos o cartão."
    assert ready.post("/credit-cards", json={"name": "  "}).status_code == 422


def test_updating_a_card_without_an_open_month(client):
    card = client.post("/credit-cards", json={"name": "Nubank"}).json()
    response = put_value(client, card["id"], 10)
    assert (response.status_code, response.json()["code"]) == (409, "no_open_month")


# --------------------------------------------------------------------------
# Linhas
# --------------------------------------------------------------------------
@pytest.fixture
def entry(ready, card):
    put_value(ready, card["id"], 50)
    state = put_value(ready, card["id"], 30, type="payment").json()
    return state["entries"][0]


def test_edit_a_line_and_the_total_follows(ready, card, entry):
    response = ready.patch(f"/credit-card-entries/{entry['id']}", json={"amount": 25.5})
    assert response.status_code == 200
    assert response.json() == {"id": entry["id"], "type": "payment", "amount": 25.5, "occurred_on": "2026-10-23"}
    assert card_state(ready, card["id"])["total"] == 55.5  # 30 + 25.5

    ready.patch(f"/credit-card-entries/{entry['id']}", json={"type": "refund"})
    assert card_state(ready, card["id"])["total"] == 30.0


def test_line_date_and_validation_rules(ready, entry):
    assert (
        ready.patch(f"/credit-card-entries/{entry['id']}", json={"occurred_on": "2026-09-30"}).json()["code"]
        == "month_closed"
    )
    assert ready.patch(f"/credit-card-entries/{entry['id']}", json={"amount": 0}).status_code == 422
    assert ready.patch(f"/credit-card-entries/{entry['id']}", json={"type": "purchase"}).status_code == 422


def test_delete_a_line(ready, card, entry):
    response = ready.delete(f"/credit-card-entries/{entry['id']}")
    assert (response.status_code, response.content) == (204, b"")
    assert card_state(ready, card["id"])["entries"] == []
    assert ready.delete(f"/credit-card-entries/{entry['id']}").status_code == 404
