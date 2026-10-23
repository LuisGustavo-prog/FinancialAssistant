import os
from dataclasses import dataclass

DEFAULT_DATABASE_PATH = "data/financial_assistant.db"
DEFAULT_ALLOWED_ORIGINS = "http://127.0.0.1:8080,http://localhost:8080"
DEFAULT_ALLOWED_HOSTS = "127.0.0.1,localhost"
DEFAULT_TIMEZONE = "America/Sao_Paulo"

@dataclass(frozen=True)
class Config:
    database_path: str
    allowed_origins: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    timezone: str

def _split_list(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())

def load_config() -> Config:
    return Config(
        database_path=os.environ.get("DATABASE_PATH") or DEFAULT_DATABASE_PATH,
        allowed_origins=_split_list(os.environ.get("ALLOWED_ORIGINS") or DEFAULT_ALLOWED_ORIGINS),
        allowed_hosts=_split_list(os.environ.get("ALLOWED_HOSTS") or DEFAULT_ALLOWED_HOSTS),
        timezone=os.environ.get("TIMEZONE") or DEFAULT_TIMEZONE,
    )
