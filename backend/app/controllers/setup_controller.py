"""Prepara o banco ao iniciar a API."""

from pathlib import Path
from app.config import load_config
from app.db.init_db import create_database


def ensure_database() -> bool:
    path = Path(load_config().database_path)
    if path.exists():
        return False
    create_database(path)
    return True
