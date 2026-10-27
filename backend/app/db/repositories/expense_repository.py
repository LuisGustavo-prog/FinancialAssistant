import sqlite3

_SELECT = """
    SELECT e.id, e.month_id, e.amount, e.occurred_on, e.description,
           e.category_id, c.name AS category_name, e.payment_method
    FROM expense e
    JOIN category c ON c.id = e.category_id
"""
_NEWEST_FIRST = "ORDER BY e.occurred_on DESC, e.id DESC"


def insert_expense(
    conn: sqlite3.Connection,
    month_id: int,
    amount: float,
    occurred_on: str,
    description: str | None,
    category_id: int,
) -> int:
    cursor = conn.execute(
        """INSERT INTO expense (month_id, amount, occurred_on, description, category_id)
           VALUES (?, ?, ?, ?, ?)""",
        (month_id, amount, occurred_on, description, category_id),
    )
    return cursor.lastrowid


def get_expense(conn: sqlite3.Connection, expense_id: int) -> dict | None:
    row = conn.execute(f"{_SELECT} WHERE e.id = ?", (expense_id,)).fetchone()
    return dict(row) if row else None


def list_expenses(conn: sqlite3.Connection, month_id: int) -> list[dict]:
    rows = conn.execute(f"{_SELECT} WHERE e.month_id = ? {_NEWEST_FIRST}", (month_id,)).fetchall()
    return [dict(row) for row in rows]


def list_recent_expenses(conn: sqlite3.Connection, month_id: int, limit: int) -> list[dict]:
    rows = conn.execute(f"{_SELECT} WHERE e.month_id = ? {_NEWEST_FIRST} LIMIT ?", (month_id, limit)).fetchall()
    return [dict(row) for row in rows]


def update_expense(
    conn: sqlite3.Connection,
    expense_id: int,
    amount: float,
    occurred_on: str,
    description: str | None,
    category_id: int,
) -> bool:
    cursor = conn.execute(
        """UPDATE expense
           SET amount = ?, occurred_on = ?, description = ?, category_id = ?
           WHERE id = ?""",
        (amount, occurred_on, description, category_id, expense_id),
    )
    return cursor.rowcount == 1


def delete_expense(conn: sqlite3.Connection, expense_id: int) -> bool:
    cursor = conn.execute("DELETE FROM expense WHERE id = ?", (expense_id,))
    return cursor.rowcount == 1


def sum_expenses(conn: sqlite3.Connection, month_id: int) -> float:
    row = conn.execute(
        "SELECT ROUND(COALESCE(SUM(amount), 0), 2) FROM expense WHERE month_id = ?", (month_id,)
    ).fetchone()
    return row[0]
