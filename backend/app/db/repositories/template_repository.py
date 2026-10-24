import sqlite3

_TEMPLATE_TABLES = ("fixed_expense_template", "savings_quota_template")

def _list(conn: sqlite3.Connection, table: str) -> list[dict]:
    assert table in _TEMPLATE_TABLES
    return [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()]

def _get(conn: sqlite3.Connection, table: str, template_id: int) -> dict | None:
    assert table in _TEMPLATE_TABLES
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (template_id,)).fetchone()
    return dict(row) if row else None

def _insert(conn: sqlite3.Connection, table: str, name: str, amount: float) -> int:
    assert table in _TEMPLATE_TABLES
    cursor = conn.execute(f"INSERT INTO {table} (name, amount) VALUES (?, ?)", (name, amount))
    return cursor.lastrowid

def _update(
    conn: sqlite3.Connection, table: str, template_id: int, name: str, amount: float, is_active: bool
) -> bool:
    assert table in _TEMPLATE_TABLES
    cursor = conn.execute(
        f"UPDATE {table} SET name = ?, amount = ?, is_active = ? WHERE id = ?",
        (name, amount, int(is_active), template_id),
    )
    return cursor.rowcount == 1

def list_fixed_expense_templates(conn: sqlite3.Connection) -> list[dict]:
    return _list(conn, "fixed_expense_template")

def get_fixed_expense_template(conn: sqlite3.Connection, template_id: int) -> dict | None:
    return _get(conn, "fixed_expense_template", template_id)

def insert_fixed_expense_template(conn: sqlite3.Connection, name: str, amount: float) -> int:
    return _insert(conn, "fixed_expense_template", name, amount)

def update_fixed_expense_template(
    conn: sqlite3.Connection, template_id: int, name: str, amount: float, is_active: bool
) -> bool:
    return _update(conn, "fixed_expense_template", template_id, name, amount, is_active)

def list_savings_quota_templates(conn: sqlite3.Connection) -> list[dict]:
    return _list(conn, "savings_quota_template")

def get_savings_quota_template(conn: sqlite3.Connection, template_id: int) -> dict | None:
    return _get(conn, "savings_quota_template", template_id)

def insert_savings_quota_template(conn: sqlite3.Connection, name: str, amount: float) -> int:
    return _insert(conn, "savings_quota_template", name, amount)

def update_savings_quota_template(
    conn: sqlite3.Connection, template_id: int, name: str, amount: float, is_active: bool
) -> bool:
    return _update(conn, "savings_quota_template", template_id, name, amount, is_active)
