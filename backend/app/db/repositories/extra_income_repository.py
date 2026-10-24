import sqlite3

_NEWEST_FIRST = "ORDER BY occurred_on DESC, id DESC"

def insert_extra_income(
    conn: sqlite3.Connection,
    month_id: int,
    amount: float,
    occurred_on: str,
    description: str | None,
    source: str,
) -> int:
    cursor = conn.execute(
        """INSERT INTO extra_income (month_id, amount, occurred_on, description, source)
           VALUES (?, ?, ?, ?, ?)""",
        (month_id, amount, occurred_on, description, source),
    )
    return cursor.lastrowid

def get_extra_income(conn: sqlite3.Connection, income_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM extra_income WHERE id = ?", (income_id,)).fetchone()
    return dict(row) if row else None

def list_extra_incomes(conn: sqlite3.Connection, month_id: int) -> list[dict]:
    rows = conn.execute(
        f"SELECT * FROM extra_income WHERE month_id = ? {_NEWEST_FIRST}", (month_id,)
    ).fetchall()
    return [dict(row) for row in rows]

def update_extra_income(
    conn: sqlite3.Connection,
    income_id: int,
    amount: float,
    occurred_on: str,
    description: str | None,
) -> bool:
    cursor = conn.execute(
        "UPDATE extra_income SET amount = ?, occurred_on = ?, description = ? WHERE id = ?",
        (amount, occurred_on, description, income_id),
    )
    return cursor.rowcount == 1

def delete_extra_income(conn: sqlite3.Connection, income_id: int) -> bool:
    cursor = conn.execute("DELETE FROM extra_income WHERE id = ?", (income_id,))
    return cursor.rowcount == 1

def sum_extra_incomes(conn: sqlite3.Connection, month_id: int) -> float:
    row = conn.execute(
        "SELECT ROUND(COALESCE(SUM(amount), 0), 2) FROM extra_income WHERE month_id = ?",
        (month_id,),
    ).fetchone()
    return row[0]
