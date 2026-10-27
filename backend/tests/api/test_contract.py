import json


def nullable(shape):
    return ("null", shape)


CATEGORY = {"id": "int", "name": "str"}
EXPENSE = {
    "id": "int",
    "amount": "number",
    "occurred_on": "str",
    "description": nullable("str"),
    "category": CATEGORY,
    "payment_method": "str",
}
EXTRA_INCOME = {
    "id": "int",
    "amount": "number",
    "occurred_on": "str",
    "description": nullable("str"),
    "source": "str",
    "is_editable?": "bool",
}
NOTICE = {"id": nullable("int"), "code": "str", "params": "dict", "message": "str"}
BREAKDOWN = {
    "salary": "number",
    "extra_incomes": "number",
    "fixed_expenses": "number",
    "savings_quotas": "number",
    "debit_expenses": "number",
    "credit_card_total": "number",
}
PENDING_LEFTOVER = {
    "month_id": "int",
    "year": "int",
    "month_number": "int",
    "amount": "number",
    "message": "str",
}
HOME_OK = {
    "status": "str",
    "month": {"id": "int", "year": "int", "month_number": "int", "status": "str", "days_left": "int"},
    "free_balance": "number",
    "breakdown": BREAKDOWN,
    "notices": [NOTICE],
    "pending_leftover": nullable(PENDING_LEFTOVER),
    "recent_expenses": [EXPENSE],
}
HOME_NEEDS_SETUP = {"status": "str"}
CATEGORY_ITEM = {"id": "int", "name": "str", "is_default": "bool", "is_active": "bool"}
CARD_ENTRY = {"id": "int", "type": "str", "amount": "number", "occurred_on": "str"}
CREDIT_CARD = {
    "id": "int",
    "name": "str",
    "is_active": "bool",
    "in_current_month": "bool",
    "reported_value": nullable("number"),
    "payments_total": nullable("number"),
    "total": nullable("number"),
    "updated_at": nullable("str"),
    "days_since_update": nullable("int"),
    "is_outdated": "bool",
    "entries": [CARD_ENTRY],
}
SETTINGS = {"current_salary": nullable("number"), "current_month_salary": nullable("number")}
TEMPLATE = {"id": "int", "name": "str", "amount": "number", "is_active": "bool"}
MONTH_ITEM = {
    "id": "int",
    "year": "int",
    "month_number": "int",
    "status": "str",
    "result": "str",
    "final_balance": "number",
    "leftover_decision": nullable("str"),
}
MONTH_DETAIL = {
    **MONTH_ITEM,
    "breakdown": BREAKDOWN,
    "expenses": [EXPENSE],
    "extra_incomes": [EXTRA_INCOME],
    "fixed_expenses": [{"name": "str", "amount": "number"}],
    "savings_quotas": [{"name": "str", "amount": "number"}],
    "credit_cards": [{"id": "int", "name": "str", "total": "number"}],
}
API_ERROR = {"code": "str", "message": "str", "params": "dict"}


def problems(value, shape, path="$"):
    if isinstance(shape, tuple):  # ("null", X)
        return [] if value is None else problems(value, shape[1], path)
    if isinstance(shape, str):
        checks = {
            "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
            "str": lambda v: isinstance(v, str),
            "bool": lambda v: isinstance(v, bool),
            "dict": lambda v: isinstance(v, dict),
        }
        return [] if checks[shape](value) else [f"{path}: esperado {shape}, veio {json.dumps(value)}"]
    if isinstance(shape, list):
        if not isinstance(value, list):
            return [f"{path}: esperado lista, veio {json.dumps(value)}"]
        found = []
        for index, item in enumerate(value):
            found += problems(item, shape[0], f"{path}[{index}]")
        return found

    if not isinstance(value, dict):
        return [f"{path}: esperado objeto, veio {json.dumps(value)}"]
    required = {key for key in shape if not key.endswith("?")}
    allowed = {key.rstrip("?") for key in shape}
    found = [f"{path}: falta o campo '{key}'" for key in sorted(required - value.keys())]
    found += [f"{path}: campo '{key}' nao esperado pelo front" for key in sorted(value.keys() - allowed)]
    for key, item in value.items():
        wanted = shape.get(key, shape.get(key + "?"))
        if wanted is not None:
            found += problems(item, wanted, f"{path}.{key}")
    return found


def assert_contract(response, shape, status=200):
    assert response.status_code == status, response.text
    assert problems(response.json(), shape) == []


def test_checker_finds_missing_extra_and_wrong_type_fields():
    shape = {"id": "int", "name": "str", "note?": nullable("str")}
    assert problems({"id": 1, "name": "a"}, shape) == []
    assert problems({"id": 1, "name": "a", "note": None}, shape) == []
    assert problems({"id": 1}, shape) == ["$: falta o campo 'name'"]
    assert problems({"id": 1, "name": "a", "x": 1}, shape) == ["$: campo 'x' nao esperado pelo front"]
    assert problems({"id": "1", "name": "a"}, shape) == ['$.id: esperado int, veio "1"']
    assert problems({"id": True, "name": "a"}, shape) != []  # bool nao e numero


def test_contract_before_the_first_salary(client):
    assert_contract(client.get("/home"), HOME_NEEDS_SETUP)
    assert_contract(client.get("/settings"), SETTINGS)
    assert_contract(client.get("/categories"), [CATEGORY_ITEM])
    assert_contract(client.get("/months"), [MONTH_ITEM])
    assert_contract(client.get("/expenses"), [EXPENSE])
    assert_contract(client.get("/credit-cards"), [CREDIT_CARD])


def test_contract_of_every_endpoint_with_data(client, freeze):
    assert_contract(client.put("/settings", json={"current_salary": 3000}), SETTINGS)
    assert_contract(client.patch("/months/current/salary", json={"salary": 3000}), SETTINGS)
    assert_contract(client.post("/fixed-expenses", json={"name": "Aluguel", "amount": 1200}), TEMPLATE, 201)
    assert_contract(client.post("/savings-quotas", json={"name": "Reserva", "amount": 300}), TEMPLATE, 201)
    category = client.post("/categories", json={"name": "Mercado"})
    assert_contract(category, CATEGORY_ITEM, 201)
    card = client.post("/credit-cards", json={"name": "Nubank"})
    assert_contract(card, CREDIT_CARD, 201)
    card_id = card.json()["id"]

    assert_contract(client.put(f"/credit-cards/{card_id}/current-month", json={"reported_value": 800.25}), CREDIT_CARD)
    assert_contract(
        client.post(f"/credit-cards/{card_id}/current-month/payments", json={"amount": 100}), CREDIT_CARD, 201
    )
    refund = client.put(f"/credit-cards/{card_id}/current-month", json={"reported_value": 650.25, "type": "refund"})
    assert_contract(refund, CREDIT_CARD)
    entry_id = refund.json()["entries"][0]["id"]
    assert_contract(client.patch(f"/credit-card-entries/{entry_id}", json={"amount": 40}), CARD_ENTRY)

    expense = client.post(
        "/expenses",
        json={"amount": 450.5, "description": "Mercado", "category_id": category.json()["id"]},
    )
    assert_contract(expense, EXPENSE, 201)
    assert_contract(client.patch(f"/expenses/{expense.json()['id']}", json={"amount": 450.5}), EXPENSE)
    assert_contract(client.post("/extra-incomes", json={"amount": 200, "description": "Freela"}), EXTRA_INCOME, 201)

    assert_contract(client.get("/fixed-expenses"), [TEMPLATE])
    assert_contract(client.get("/savings-quotas"), [TEMPLATE])
    assert_contract(client.get("/categories"), [CATEGORY_ITEM])
    assert_contract(client.get("/expenses"), [EXPENSE])
    assert_contract(client.get("/extra-incomes"), [EXTRA_INCOME])
    assert_contract(client.get("/credit-cards"), [CREDIT_CARD])
    assert_contract(client.get("/home"), HOME_OK)

    freeze(2026, 10, 30)
    home = client.get("/home")
    assert_contract(home, HOME_OK)
    assert home.json()["notices"], "o aviso de fim de mes deveria aparecer"

    freeze(2026, 11, 2)
    home = client.get("/home")
    assert_contract(home, HOME_OK)
    assert home.json()["pending_leftover"] is not None
    month_id = home.json()["pending_leftover"]["month_id"]
    assert_contract(client.get("/months"), [MONTH_ITEM])
    assert_contract(client.get(f"/months/{month_id}"), MONTH_DETAIL)

    decision = client.post(f"/months/{month_id}/leftover-decision", json={"decision": "carried"})
    assert decision.status_code == 200
    assert problems(decision.json(), {**MONTH_ITEM, "extra_income": EXTRA_INCOME}) == []
    incomes = client.get("/extra-incomes")
    assert_contract(incomes, [EXTRA_INCOME])
    assert any(item["source"] == "leftover" and item["is_editable"] is False for item in incomes.json())


def test_contract_of_the_stored_notice_and_of_errors(client, freeze):
    client.put("/settings", json={"current_salary": 1000})
    client.post("/expenses", json={"amount": 1300})
    freeze(2026, 11, 2)

    home = client.get("/home")
    assert_contract(home, HOME_OK)
    assert [n["id"] for n in home.json()["notices"]] == [1]

    errors = [
        client.post("/expenses", json={"amount": 0}),
        client.post("/expenses", json={"amount": 10, "occurred_on": "2026-09-01"}),
        client.post("/expenses", json={"amount": 10, "occurred_on": "2026-12-01"}),
        client.patch("/expenses/999", json={"amount": 1}),
        client.post("/months/1/leftover-decision", json={"decision": "carried"}),
    ]
    for response in errors:
        assert response.status_code >= 400
        assert problems(response.json(), API_ERROR) == [], response.text
