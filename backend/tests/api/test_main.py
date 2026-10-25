from fastapi.testclient import TestClient

from app.main import create_app

ORIGIN = "http://localhost:8080"


# --------------------------------------------------------------------------
# Hosts e CORS
# --------------------------------------------------------------------------
def test_an_allowed_host_works(client):
    assert client.get("/home").status_code == 200


def test_an_unknown_host_is_refused_against_dns_rebinding(client):
    assert client.get("/home", headers={"Host": "evil.example.com"}).status_code == 400


def test_cors_preflight_for_the_front_origin(client):
    response = client.options(
        "/expenses",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN


def test_cors_header_on_normal_and_error_responses(client):
    ok = client.get("/home", headers={"Origin": ORIGIN})
    assert ok.headers["access-control-allow-origin"] == ORIGIN
    error = client.get("/months/999", headers={"Origin": ORIGIN})
    assert error.status_code == 404
    assert error.headers["access-control-allow-origin"] == ORIGIN


def test_other_origins_get_no_cors_header(client):
    response = client.get("/home", headers={"Origin": "http://evil.example.com"})
    assert "access-control-allow-origin" not in response.headers


# --------------------------------------------------------------------------
# Inicio
# --------------------------------------------------------------------------
def test_startup_creates_the_database_when_missing(tmp_path, monkeypatch, freeze):
    path = tmp_path / "data" / "new.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    monkeypatch.setenv("ALLOWED_HOSTS", "testserver")
    assert not path.exists()
    with TestClient(create_app()) as test_client:
        assert path.exists()
        assert test_client.get("/home").json() == {"status": "needs_setup"}


def test_the_docs_are_available_without_the_database_being_touched(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert {"/home", "/expenses", "/credit-cards/{card_id}/current-month"} <= set(response.json()["paths"])


# --------------------------------------------------------------------------
# Formato unico dos erros
# --------------------------------------------------------------------------
def test_unknown_route_has_the_standard_error_format(client):
    response = client.get("/nowhere")
    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "Não encontramos o item pedido.",
        "params": {},
    }


def test_wrong_method_has_the_standard_error_format(client):
    response = client.delete("/home")
    assert response.status_code == 405
    assert response.json()["code"] == "method_not_allowed"
    assert "detail" not in response.json()


def test_validation_error_lists_the_fields(ready):
    response = ready.post("/expenses", json={"amount": 0, "occurred_on": "ontem"})
    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "validation_error"
    assert {f["field"] for f in body["params"]["fields"]} == {"amount", "occurred_on"}
    assert body["message"].startswith("Dados inválidos. Confira:")
    assert "detail" not in body


def test_invalid_json_and_invalid_path_parameter_are_validation_errors(ready):
    broken = ready.post("/expenses", content="{nao e json", headers={"Content-Type": "application/json"})
    assert (broken.status_code, broken.json()["code"]) == (422, "validation_error")
    bad_id = ready.patch("/expenses/abc", json={"amount": 1})
    assert (bad_id.status_code, bad_id.json()["code"]) == (422, "validation_error")


def test_unexpected_error_is_a_500_in_the_standard_format_with_cors(db_path, freeze, monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("ALLOWED_ORIGINS", ORIGIN)

    def explode():
        raise RuntimeError("falha de teste")

    monkeypatch.setattr("app.api.routers.expenses.expense_controller.list_expenses", explode)
    with TestClient(create_app(), raise_server_exceptions=False) as test_client:
        response = test_client.get("/expenses", headers={"Origin": ORIGIN})
    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "Algo deu errado no servidor. Tente de novo em instantes.",
        "params": {},
    }
    assert response.headers["access-control-allow-origin"] == ORIGIN
