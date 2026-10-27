import argparse
import sqlite3
import sys
from pathlib import Path
from app.db.connection import connect

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = "data/financial_assistant.db"


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def create_database(path: str | Path) -> None:
    db_path = Path(path)
    if db_path.exists():
        raise FileExistsError(f"O banco ja existe: {db_path}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(db_path)
    try:
        apply_schema(conn)
    except Exception:
        conn.close()
        db_path.unlink(missing_ok=True)
        raise
    conn.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cria o banco do Financial_Assistant.")
    parser.add_argument("--path", default=DEFAULT_DB_PATH, help="caminho do arquivo .db")
    parser.add_argument(
        "--force",
        action="store_true",
        help="apaga o banco existente e recria (perde todos os dados)",
    )
    args = parser.parse_args(argv)

    db_path = Path(args.path)
    if db_path.exists():
        if not args.force:
            print(f"O banco ja existe: {db_path}. Use --force para apagar e recriar.")
            return 1
        db_path.unlink()
        print(f"Banco antigo apagado: {db_path}")

    create_database(db_path)
    print(f"Banco criado: {db_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
