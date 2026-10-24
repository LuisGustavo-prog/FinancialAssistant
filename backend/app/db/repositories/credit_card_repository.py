import sqlite3

_CARD_MONTH_SELECT = """
    SELECT m.id, m.credit_card_id, m.month_id, m.reported_value, m.updated_at,
           c.name AS card_name, c.is_active
    FROM credit_card_month m
    JOIN credit_card c ON c.id = m.credit_card_id
"""

def list_cards(conn: sqlite3.Connection) -> list[dict]:
    return [dict(row) for row in conn.execute("SELECT * FROM credit_card ORDER BY id").fetchall()]

def list_active_card_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT id FROM credit_card WHERE is_active = 1 ORDER BY id").fetchall()
    return [row["id"] for row in rows]

def get_card(conn: sqlite3.Connection, card_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM credit_card WHERE id = ?", (card_id,)).fetchone()
    return dict(row) if row else None

def insert_card(conn: sqlite3.Connection, name: str) -> int:
    cursor = conn.execute("INSERT INTO credit_card (name) VALUES (?)", (name,))
    return cursor.lastrowid

def update_card(conn: sqlite3.Connection, card_id: int, name: str, is_active: bool) -> bool:
    cursor = conn.execute(
        "UPDATE credit_card SET name = ?, is_active = ? WHERE id = ?",
        (name, int(is_active), card_id),
    )
    return cursor.rowcount == 1

def insert_card_month(conn: sqlite3.Connection, card_id: int, month_id: int) -> int:
    cursor = conn.execute(
        "INSERT INTO credit_card_month (credit_card_id, month_id) VALUES (?, ?)",
        (card_id, month_id),
    )
    return cursor.lastrowid

def get_card_month(conn: sqlite3.Connection, card_id: int, month_id: int) -> dict | None:
    row = conn.execute(
        f"{_CARD_MONTH_SELECT} WHERE m.credit_card_id = ? AND m.month_id = ?", (card_id, month_id)
    ).fetchone()
    return dict(row) if row else None

def list_card_months(conn: sqlite3.Connection, month_id: int) -> list[dict]:
    rows = conn.execute(
        f"{_CARD_MONTH_SELECT} WHERE m.month_id = ? ORDER BY c.id", (month_id,)
    ).fetchall()
    return [dict(row) for row in rows]

def update_reported_value(
    conn: sqlite3.Connection, card_month_id: int, reported_value: float, updated_at: str
) -> bool:
    cursor = conn.execute(
        "UPDATE credit_card_month SET reported_value = ?, updated_at = ? WHERE id = ?",
        (reported_value, updated_at, card_month_id),
    )
    return cursor.rowcount == 1

def insert_entry(
    conn: sqlite3.Connection, card_month_id: int, entry_type: str, amount: float, occurred_on: str
) -> int:
    cursor = conn.execute(
        """INSERT INTO credit_card_entry (credit_card_month_id, type, amount, occurred_on)
           VALUES (?, ?, ?, ?)""",
        (card_month_id, entry_type, amount, occurred_on),
    )
    return cursor.lastrowid

def get_entry(conn: sqlite3.Connection, entry_id: int) -> dict | None:
    row = conn.execute(
        """SELECT e.id, e.credit_card_month_id, e.type, e.amount, e.occurred_on,
                  m.month_id, m.credit_card_id
           FROM credit_card_entry e
           JOIN credit_card_month m ON m.id = e.credit_card_month_id
           WHERE e.id = ?""",
        (entry_id,),
    ).fetchone()
    return dict(row) if row else None

def list_entries(conn: sqlite3.Connection, card_month_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM credit_card_entry WHERE credit_card_month_id = ? ORDER BY occurred_on, id",
        (card_month_id,),
    ).fetchall()
    return [dict(row) for row in rows]

def list_entries_by_month(conn: sqlite3.Connection, month_id: int) -> list[dict]:
    rows = conn.execute(
        """SELECT e.id, e.credit_card_month_id, e.type, e.amount, e.occurred_on
           FROM credit_card_entry e
           JOIN credit_card_month m ON m.id = e.credit_card_month_id
           WHERE m.month_id = ?
           ORDER BY e.credit_card_month_id, e.occurred_on, e.id""",
        (month_id,),
    ).fetchall()
    return [dict(row) for row in rows]

def update_entry(
    conn: sqlite3.Connection, entry_id: int, entry_type: str, amount: float, occurred_on: str
) -> bool:
    cursor = conn.execute(
        "UPDATE credit_card_entry SET type = ?, amount = ?, occurred_on = ? WHERE id = ?",
        (entry_type, amount, occurred_on, entry_id),
    )
    return cursor.rowcount == 1

def delete_entry(conn: sqlite3.Connection, entry_id: int) -> bool:
    cursor = conn.execute("DELETE FROM credit_card_entry WHERE id = ?", (entry_id,))
    return cursor.rowcount == 1
