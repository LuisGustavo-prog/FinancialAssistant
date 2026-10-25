"""O fluxo do plano pela API, com o relogio trocado a cada passo."""

import pytest


def build_october(client):
    """Outubro como no plano: salario 3000, fixo 1200, cota 300, gasto 450.50 e cartao 800.25.
    Saldo livre de outubro: 249.25."""
    client.put("/settings", json={"current_salary": 3000})
    client.post("/fixed-expenses", json={"name": "Aluguel", "amount": 1200})
    client.post("/savings-quotas", json={"name": "Reserva", "amount": 300})
    card = client.post("/credit-cards", json={"name": "Nubank"}).json()
    client.put(f"/credit-cards/{card['id']}/current-month", json={"reported_value": 800.25})
    client.post("/expenses", json={"amount": 450.50, "occurred_on": "2026-10-05"})
    return card


# --------------------------------------------------------------------------
# Home
# --------------------------------------------------------------------------
def test_home_before_the_first_salary(client):
    response = client.get("/home")
    assert (response.status_code, response.json()) == (200, {"status": "needs_setup"})


def test_home_with_everything_ready_to_show(client):
    build_october(client)
    home = client.get("/home").json()
    assert home["status"] == "ok"
    assert home["month"]["year"] == 2026 and home["month"]["month_number"] == 10
    assert (home["month"]["status"], home["month"]["days_left"]) == ("open", 8)
    assert home["free_balance"] == 249.25
    assert home["breakdown"] == {
        "salary": 3000.0,
        "extra_incomes": 0.0,
        "fixed_expenses": 1200.0,
        "savings_quotas": 300.0,
        "debit_expenses": 450.5,
        "credit_card_total": 800.25,
    }
    assert home["notices"] == []
    assert home["pending_leftover"] is None
    assert [e["amount"] for e in home["recent_expenses"]] == [450.5]


# --------------------------------------------------------------------------
# Avisos calculados
# --------------------------------------------------------------------------
def test_month_ending_and_card_notices_have_their_texts(client, freeze):
    client.put("/settings", json={"current_salary": 3000})
    client.post("/credit-cards", json={"name": "Nubank"})

    freeze(2026, 10, 10)
    notices = client.get("/home").json()["notices"]
    assert notices == [
        {
            "id": None,
            "code": "credit_card_not_updated",
            "params": {"card_names": ["Nubank"]},
            "message": "O cartão Nubank ainda não foi atualizado neste mês.",
        }
    ]

    freeze(2026, 10, 30)
    notices = client.get("/home").json()["notices"]
    assert [n["code"] for n in notices] == ["month_ending", "credit_card_not_updated"]
    assert notices[0]["message"] == "O mês fecha em 1 dia. Atualize o valor dos cartões."


# --------------------------------------------------------------------------
# Virada do mes, historico e sobra
# --------------------------------------------------------------------------
def test_the_month_turn_happens_on_the_first_request_of_the_new_month(client, freeze):
    build_october(client)
    freeze(2026, 11, 2)
    home = client.get("/home").json()  # esta requisicao roda a rotina antes de responder

    assert home["month"]["month_number"] == 11
    assert home["free_balance"] == 1500.0  # 3000 - 1200 - 300, cartao zerado
    assert home["breakdown"]["debit_expenses"] == 0.0
    assert home["pending_leftover"] == {
        "month_id": 1,
        "year": 2026,
        "month_number": 10,
        "amount": 249.25,
        "message": "Outubro fechou com sobra de R$ 249,25. Quer levar esse valor para este mês?",
    }
    assert client.get("/expenses").json() == []  # a lista e so do mes aberto


def test_history_and_month_detail(client, freeze):
    card = build_october(client)
    freeze(2026, 11, 2)
    months = client.get("/months").json()
    assert months == [
        {
            "id": 1,
            "year": 2026,
            "month_number": 10,
            "status": "closed",
            "result": "green",
            "final_balance": 249.25,
            "leftover_decision": "pending",
        }
    ]

    detail = client.get("/months/1").json()
    assert detail["breakdown"]["debit_expenses"] == 450.5
    assert [e["amount"] for e in detail["expenses"]] == [450.5]
    assert detail["fixed_expenses"] == [{"name": "Aluguel", "amount": 1200.0}]
    assert detail["savings_quotas"] == [{"name": "Reserva", "amount": 300.0}]
    assert detail["credit_cards"] == [{"id": card["id"], "name": "Nubank", "total": 800.25}]


def test_detail_of_the_open_month_or_an_unknown_month_is_404(client, freeze):
    build_october(client)
    freeze(2026, 11, 2)
    open_id = client.get("/home").json()["month"]["id"]
    for month_id in (open_id, 999):
        response = client.get(f"/months/{month_id}")
        assert (response.status_code, response.json()["code"]) == (404, "not_found")
        assert response.json()["message"] == "Não encontramos o mês."


def test_carrying_the_leftover_creates_a_locked_income_and_clears_the_question(client, freeze):
    build_october(client)
    freeze(2026, 11, 2)

    response = client.post("/months/1/leftover-decision", json={"decision": "carried"})
    assert response.status_code == 200
    body = response.json()
    assert body["leftover_decision"] == "carried"
    income = body["extra_income"]
    assert (income["amount"], income["occurred_on"], income["description"]) == (249.25, "2026-11-02", "Sobra de outubro")
    assert (income["source"], income["is_editable"]) == ("leftover", False)

    home = client.get("/home").json()
    assert home["pending_leftover"] is None
    assert home["breakdown"]["extra_incomes"] == 249.25
    assert home["free_balance"] == 1749.25

    # A renda travada: nao pode ser editada nem apagada.
    patch = client.patch(f"/extra-incomes/{income['id']}", json={"amount": 1})
    assert patch.status_code == 409
    assert patch.json() == {
        "code": "leftover_income_locked",
        "message": "Esta renda veio da sobra do mês e não pode ser editada nem apagada.",
        "params": {},
    }
    assert client.delete(f"/extra-incomes/{income['id']}").status_code == 409
    assert client.get("/extra-incomes").json()[0]["is_editable"] is False


def test_declining_the_leftover_creates_no_income(client, freeze):
    build_october(client)
    freeze(2026, 11, 2)
    response = client.post("/months/1/leftover-decision", json={"decision": "declined"})
    assert response.json()["leftover_decision"] == "declined"
    assert response.json()["extra_income"] is None
    assert client.get("/extra-incomes").json() == []


def test_answering_the_leftover_twice_is_409(client, freeze):
    build_october(client)
    freeze(2026, 11, 2)
    client.post("/months/1/leftover-decision", json={"decision": "carried"})
    response = client.post("/months/1/leftover-decision", json={"decision": "carried"})
    assert (response.status_code, response.json()["code"]) == (409, "leftover_not_pending")
    assert len(client.get("/extra-incomes").json()) == 1


@pytest.mark.parametrize("body", [{}, {"decision": "pending"}, {"decision": "talvez"}])
def test_invalid_leftover_decisions(client, freeze, body):
    build_october(client)
    freeze(2026, 11, 2)
    response = client.post("/months/1/leftover-decision", json=body)
    assert (response.status_code, response.json()["code"]) == (422, "validation_error")
    assert client.get("/months").json()[0]["leftover_decision"] == "pending"


def test_the_leftover_questions_come_oldest_first(client, freeze):
    build_october(client)
    freeze(2026, 11, 2)
    client.get("/home")
    freeze(2026, 12, 2)
    pending = client.get("/home").json()["pending_leftover"]
    assert pending["month_number"] == 10

    client.post("/months/1/leftover-decision", json={"decision": "declined"})
    assert client.get("/home").json()["pending_leftover"]["month_number"] == 11


# --------------------------------------------------------------------------
# Avisos guardados
# --------------------------------------------------------------------------
def test_negative_month_notice_has_an_id_and_can_be_dismissed(client, freeze):
    client.put("/settings", json={"current_salary": 1000})
    client.post("/expenses", json={"amount": 1300})
    freeze(2026, 11, 2)

    home = client.get("/home").json()
    assert home["pending_leftover"] is None
    assert home["notices"] == [
        {
            "id": 1,
            "code": "month_closed_negative",
            "params": {"closed_month": "2026-10", "current_month": "2026-11", "final_balance": -300.0},
            "message": "Outubro fechou no negativo (R$ 300,00 abaixo de zero). O valor não passa para novembro.",
        }
    ]
    assert client.get("/months").json()[0]["result"] == "red"

    response = client.post("/notices/1/dismiss")
    assert (response.status_code, response.content) == (204, b"")
    assert client.get("/home").json()["notices"] == []
    assert client.post("/notices/1/dismiss").status_code == 204  # repetir nao da erro


def test_months_without_use_notice(client, freeze):
    client.put("/settings", json={"current_salary": 1000})
    freeze(2027, 1, 15)
    notices = client.get("/home").json()["notices"]
    assert [n["code"] for n in notices] == ["unused_months"]
    assert notices[0]["message"] == "Os meses de novembro e dezembro ficaram sem registro, porque o app não foi aberto."
    assert [m["month_number"] for m in client.get("/months").json()] == [10]


# --------------------------------------------------------------------------
# Relogio
# --------------------------------------------------------------------------
def test_at_9pm_in_brasilia_on_the_last_day_the_month_has_not_turned(client, freeze):
    build_october(client)
    freeze(2026, 11, 1, hour=0)  # 21h de 31/10 em Brasilia, 00h de 01/11 em UTC
    home = client.get("/home").json()
    assert home["month"]["month_number"] == 10
    assert home["month"]["days_left"] == 0
    assert client.get("/months").json() == []

    freeze(2026, 11, 1, hour=3)  # meia-noite em Brasilia
    assert client.get("/home").json()["month"]["month_number"] == 11


def test_a_clock_that_went_back_never_reopens_a_closed_month(client, freeze):
    build_october(client)
    freeze(2026, 11, 5)
    client.get("/home")
    freeze(2026, 10, 20)  # o relogio do computador voltou
    home = client.get("/home").json()
    assert home["month"]["month_number"] == 11
    response = client.post("/expenses", json={"amount": 5, "occurred_on": "2026-10-20"})
    assert (response.status_code, response.json()["code"]) == (422, "month_closed")
    assert client.post("/expenses", json={"amount": 5}).json()["occurred_on"] == "2026-11-05"
