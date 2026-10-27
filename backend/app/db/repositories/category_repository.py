import sqlite3


def list_categories(conn: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in conn.execute("SELECT * FROM category ORDER BY id").fetchall()]


def get_category(conn: sqlite3.Connection, category_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM category WHERE id = ?", (category_id,)).fetchone()
    return dict(row) if row else None


def get_default_category(conn: sqlite3.Connection) -> dict:
    return dict(conn.execute("SELECT * FROM category WHERE is_default = 1").fetchone())


def insert_category(conn: sqlite3.Connection, name: str) -> int:
    cursor = conn.execute("INSERT INTO category (name) VALUES (?)", (name,))
    return cursor.lastrowid


def update_category(conn: sqlite3.Connection, category_id: int, name: str, is_active: bool) -> bool:
    cursor = conn.execute(
        "UPDATE category SET name = ?, is_active = ? WHERE id = ?",
        (name, int(is_active), category_id),
    )
    return cursor.rowcount == 1
