import sqlite3

def get(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT current_salary, last_checked_date, pending_notices FROM settings WHERE id = 1"
    ).fetchone()
    return dict(row)

def set_current_salary(conn: sqlite3.Connection, salary: float) -> None:
    conn.execute("UPDATE settings SET current_salary = ? WHERE id = 1", (salary,))

def set_last_checked_date(conn: sqlite3.Connection, checked_on: str) -> None:
    conn.execute("UPDATE settings SET last_checked_date = ? WHERE id = 1", (checked_on,))

def set_pending_notices(conn: sqlite3.Connection, notices_json: str) -> None:
    conn.execute("UPDATE settings SET pending_notices = ? WHERE id = 1", (notices_json,))
