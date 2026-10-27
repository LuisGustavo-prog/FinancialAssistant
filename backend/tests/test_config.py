import pytest
from app.config import load_config

ENV_NAMES = ["DATABASE_PATH", "ALLOWED_ORIGINS", "ALLOWED_HOSTS", "TIMEZONE"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_defaults_run_without_docker():
    config = load_config()
    assert config.database_path == "data/financial_assistant.db"
    assert config.timezone == "America/Sao_Paulo"
    assert config.allowed_hosts == ("127.0.0.1", "localhost")
    assert config.allowed_origins == ("http://127.0.0.1:8080", "http://localhost:8080")


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", "/tmp/test.db")
    monkeypatch.setenv("TIMEZONE", "UTC")
    config = load_config()
    assert config.database_path == "/tmp/test.db"
    assert config.timezone == "UTC"


def test_lists_are_split_on_commas_and_trimmed(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", " testserver , localhost ,, ")
    assert load_config().allowed_hosts == ("testserver", "localhost")


def test_empty_variable_falls_back_to_default(monkeypatch):
    monkeypatch.setenv("TIMEZONE", "")
    monkeypatch.setenv("ALLOWED_ORIGINS", "")
    config = load_config()
    assert config.timezone == "America/Sao_Paulo"
    assert config.allowed_origins == ("http://127.0.0.1:8080", "http://localhost:8080")


def test_values_are_read_at_call_time(monkeypatch):
    assert load_config().database_path == "data/financial_assistant.db"
    monkeypatch.setenv("DATABASE_PATH", "other.db")
    assert load_config().database_path == "other.db"
