"""SQL das tabelas `month`, `month_fixed_expense` e `month_savings_quota`.

Os repositorios recebem a conexao, executam SQL e devolvem dicionarios com os
tipos do banco. As regras de estado (mes aberto ou fechado) ficam no schema e
nos casos de uso: aqui os UPDATEs trazem no WHERE a condicao que protege contra
duas requisicoes ao mesmo tempo, e devolvem False quando nada foi alterado.
"""

import sqlite3

# Nomes de tabela nao podem ser parametros do SQL. Esta lista fechada garante que
# so estes dois entram nas consultas montadas com f-string.
_COPY_TABLES = ("month_fixed_expense", "month_savings_quota")


# --------------------------------------------------------------------------
# Mes
# --------------------------------------------------------------------------
def get_month(conn: sqlite3.Connection, month_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM month WHERE id = ?", (month_id,)).fetchone()
    return dict(row) if row else None


def get_open_month(conn: sqlite3.Connection) -> dict | None:
    """O unico mes aberto, ou None (antes do primeiro salario)."""
    row = conn.execute("SELECT * FROM month WHERE status = 'open'").fetchone()
    return dict(row) if row else None


def list_closed_months(conn: sqlite3.Connection) -> list[dict]:
    """Meses fechados, do mais antigo para o mais novo."""
    rows = conn.execute(
        "SELECT * FROM month WHERE status = 'closed' ORDER BY year, month_number"
    ).fetchall()
    return [dict(row) for row in rows]


def create_month(conn: sqlite3.Connection, year: int, month_number: int, salary: float) -> int:
    """Cria um mes aberto e devolve o id. O schema recusa um segundo mes aberto."""
    cursor = conn.execute(
        "INSERT INTO month (year, month_number, status, salary) VALUES (?, ?, 'open', ?)",
        (year, month_number, salary),
    )
    return cursor.lastrowid


def close_month(
    conn: sqlite3.Connection,
    month_id: int,
    final_balance: float,
    result: str,
    closed_at: str,
    leftover_decision: str | None,
) -> bool:
    """Fecha o mes. So vale para mes aberto: False se ele ja estava fechado."""
    cursor = conn.execute(
        """UPDATE month
           SET status = 'closed', final_balance = ?, result = ?, closed_at = ?,
               leftover_decision = ?
           WHERE id = ? AND status = 'open'""",
        (final_balance, result, closed_at, leftover_decision, month_id),
    )
    return cursor.rowcount == 1


def update_salary(conn: sqlite3.Connection, month_id: int, salary: float) -> bool:
    """Altera o salario de um mes aberto. False se o mes nao esta aberto."""
    cursor = conn.execute(
        "UPDATE month SET salary = ? WHERE id = ? AND status = 'open'", (salary, month_id)
    )
    return cursor.rowcount == 1


def set_leftover_decision(conn: sqlite3.Connection, month_id: int, decision: str) -> bool:
    """Grava a resposta da sobra. So vale se ela ainda esta pendente: False no duplo clique."""
    cursor = conn.execute(
        """UPDATE month SET leftover_decision = ?
           WHERE id = ? AND status = 'closed' AND leftover_decision = 'pending'""",
        (decision, month_id),
    )
    return cursor.rowcount == 1


# --------------------------------------------------------------------------
# Copias do mes (as duas tabelas tem o mesmo formato)
# --------------------------------------------------------------------------
def _list_copies(conn: sqlite3.Connection, table: str, month_id: int) -> list[dict]:
    assert table in _COPY_TABLES
    rows = conn.execute(
        f"SELECT * FROM {table} WHERE month_id = ? ORDER BY id", (month_id,)
    ).fetchall()
    return [dict(row) for row in rows]


def _insert_copy(
    conn: sqlite3.Connection,
    table: str,
    month_id: int,
    template_id: int | None,
    name: str,
    amount: float,
) -> int:
    assert table in _COPY_TABLES
    cursor = conn.execute(
        f"INSERT INTO {table} (month_id, template_id, name, amount) VALUES (?, ?, ?, ?)",
        (month_id, template_id, name, amount),
    )
    return cursor.lastrowid


def _update_copy(conn: sqlite3.Connection, table: str, copy_id: int, name: str, amount: float) -> bool:
    assert table in _COPY_TABLES
    cursor = conn.execute(
        f"UPDATE {table} SET name = ?, amount = ? WHERE id = ?", (name, amount, copy_id)
    )
    return cursor.rowcount == 1


def _delete_copy(conn: sqlite3.Connection, table: str, copy_id: int) -> bool:
    assert table in _COPY_TABLES
    cursor = conn.execute(f"DELETE FROM {table} WHERE id = ?", (copy_id,))
    return cursor.rowcount == 1


def _sum_copies(conn: sqlite3.Connection, table: str, month_id: int) -> float:
    assert table in _COPY_TABLES
    row = conn.execute(
        f"SELECT ROUND(COALESCE(SUM(amount), 0), 2) FROM {table} WHERE month_id = ?", (month_id,)
    ).fetchone()
    return row[0]


def list_fixed_expenses(conn: sqlite3.Connection, month_id: int) -> list[dict]:
    return _list_copies(conn, "month_fixed_expense", month_id)


def insert_fixed_expense(
    conn: sqlite3.Connection, month_id: int, template_id: int | None, name: str, amount: float
) -> int:
    return _insert_copy(conn, "month_fixed_expense", month_id, template_id, name, amount)


def update_fixed_expense(conn: sqlite3.Connection, copy_id: int, name: str, amount: float) -> bool:
    return _update_copy(conn, "month_fixed_expense", copy_id, name, amount)


def delete_fixed_expense(conn: sqlite3.Connection, copy_id: int) -> bool:
    return _delete_copy(conn, "month_fixed_expense", copy_id)


def sum_fixed_expenses(conn: sqlite3.Connection, month_id: int) -> float:
    return _sum_copies(conn, "month_fixed_expense", month_id)


def list_savings_quotas(conn: sqlite3.Connection, month_id: int) -> list[dict]:
    return _list_copies(conn, "month_savings_quota", month_id)


def insert_savings_quota(
    conn: sqlite3.Connection, month_id: int, template_id: int | None, name: str, amount: float
) -> int:
    return _insert_copy(conn, "month_savings_quota", month_id, template_id, name, amount)


def update_savings_quota(conn: sqlite3.Connection, copy_id: int, name: str, amount: float) -> bool:
    return _update_copy(conn, "month_savings_quota", copy_id, name, amount)


def delete_savings_quota(conn: sqlite3.Connection, copy_id: int) -> bool:
    return _delete_copy(conn, "month_savings_quota", copy_id)


def sum_savings_quotas(conn: sqlite3.Connection, month_id: int) -> float:
    return _sum_copies(conn, "month_savings_quota", month_id)
