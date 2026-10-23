import sqlite3
import pytest
from app.db.init_db import create_database
from app.db.connection import connect

# --------------------------------------------------------------------------
# Auxiliares
# --------------------------------------------------------------------------
def add_open_month(conn, year=2026, month_number=10, salary=3000.0):
    cur = conn.execute(
        "INSERT INTO month (year, month_number, status, salary) VALUES (?, ?, 'open', ?)",
        (year, month_number, salary),
    )
    return cur.lastrowid

def add_closed_month(
    conn,
    year=2026,
    month_number=9,
    final_balance=100.0,
    result="green",
    leftover_decision="pending",
    closed_at="2026-10-01",
):
    cur = conn.execute(
        """INSERT INTO month (year, month_number, status, salary, result,
                              final_balance, closed_at, leftover_decision)
           VALUES (?, ?, 'closed', 3000.0, ?, ?, ?, ?)""",
        (year, month_number, result, final_balance, closed_at, leftover_decision),
    )
    return cur.lastrowid

def add_expense(conn, month_id, amount=10.9, occurred_on="2026-10-05", category_id=1):
    return conn.execute(
        "INSERT INTO expense (month_id, amount, occurred_on, category_id) VALUES (?, ?, ?, ?)",
        (month_id, amount, occurred_on, category_id),
    ).lastrowid

# --------------------------------------------------------------------------
# Estrutura geral
# --------------------------------------------------------------------------
def test_schema_version_is_1(conn):
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 1


def test_has_twelve_tables(conn):
    names = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    assert names == {
        "settings",
        "month",
        "fixed_expense_template",
        "savings_quota_template",
        "month_fixed_expense",
        "month_savings_quota",
        "extra_income",
        "category",
        "expense",
        "credit_card",
        "credit_card_month",
        "credit_card_entry",
    }

def test_foreign_keys_are_enabled(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_create_database_makes_file_and_refuses_to_overwrite(tmp_path):
    db_file = tmp_path / "sub" / "test.db"
    create_database(db_file)
    assert db_file.exists()
    with pytest.raises(FileExistsError):
        create_database(db_file)
    check = connect(db_file)
    assert check.execute("PRAGMA user_version").fetchone()[0] == 1
    check.close()

# --------------------------------------------------------------------------
# settings
# --------------------------------------------------------------------------
def test_settings_starts_with_single_row_without_salary(conn):
    rows = conn.execute("SELECT * FROM settings").fetchall()
    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["current_salary"] is None
    assert rows[0]["last_checked_date"] is None
    assert rows[0]["pending_notices"] == "[]"

def test_settings_refuses_second_row(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO settings (id) VALUES (2)")


@pytest.mark.parametrize("bad", ["not json", "{}", '"text"'])
def test_settings_notices_must_be_a_json_array(conn, bad):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE settings SET pending_notices = ?", (bad,))

def test_settings_accepts_valid_salary_and_notices(conn):
    conn.execute(
        "UPDATE settings SET current_salary = 3500.5, pending_notices = ?", ('[{"id": 1}]',)
    )
    assert conn.execute("SELECT current_salary FROM settings").fetchone()[0] == 3500.5

# --------------------------------------------------------------------------
# category
# --------------------------------------------------------------------------
def test_default_category_outros_is_seeded(conn):
    row = conn.execute("SELECT * FROM category").fetchone()
    assert (row["name"], row["is_default"], row["is_active"]) == ("Outros", 1, 1)

def test_default_category_cannot_be_deactivated(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE category SET is_active = 0 WHERE is_default = 1")

def test_only_one_default_category(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO category (name, is_default) VALUES ('Outra padrao', 1)")

def test_category_name_is_unique_ignoring_case(conn):
    conn.execute("INSERT INTO category (name) VALUES ('Mercado')")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO category (name) VALUES ('mercado')")

def test_category_name_cannot_be_blank(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO category (name) VALUES ('   ')")

# --------------------------------------------------------------------------
# month
# --------------------------------------------------------------------------
def test_open_month_is_accepted(conn):
    assert add_open_month(conn) > 0

def test_same_year_and_month_cannot_repeat(conn):
    add_closed_month(conn, year=2026, month_number=9)
    with pytest.raises(sqlite3.IntegrityError):
        add_open_month(conn, year=2026, month_number=9)

def test_only_one_open_month(conn):
    add_open_month(conn, month_number=10)
    with pytest.raises(sqlite3.IntegrityError):
        add_open_month(conn, month_number=11)

def test_closed_months_can_be_many(conn):
    add_closed_month(conn, month_number=7)
    add_closed_month(conn, month_number=8)
    add_open_month(conn, month_number=9)

def test_open_month_cannot_have_result(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO month (year, month_number, status, salary, result) "
            "VALUES (2026, 10, 'open', 3000, 'green')"
        )

def test_closed_month_requires_result_balance_and_date(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO month (year, month_number, status, salary) "
            "VALUES (2026, 9, 'closed', 3000)"
        )

def test_green_result_with_negative_balance_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_closed_month(conn, final_balance=-50.0, result="green", leftover_decision=None)

def test_red_result_with_positive_balance_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_closed_month(conn, final_balance=50.0, result="red")

def test_red_month_accepted_without_leftover_decision(conn):
    add_closed_month(conn, final_balance=-50.0, result="red", leftover_decision=None)

def test_positive_leftover_requires_a_decision(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_closed_month(conn, final_balance=100.0, result="green", leftover_decision=None)

def test_zero_balance_is_green_and_has_no_decision(conn):
    add_closed_month(conn, final_balance=0.0, result="green", leftover_decision=None)
    with pytest.raises(sqlite3.IntegrityError):
        add_closed_month(
            conn, month_number=8, final_balance=0.0, result="green", leftover_decision="pending"
        )

def test_red_month_refuses_leftover_decision(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_closed_month(conn, final_balance=-10.0, result="red", leftover_decision="pending")

@pytest.mark.parametrize("decision", ["pending", "carried", "declined"])
def test_valid_leftover_decisions(conn, decision):
    add_closed_month(conn, leftover_decision=decision)

def test_invalid_leftover_decision_is_refused(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_closed_month(conn, leftover_decision="maybe")

# --------------------------------------------------------------------------
# Dinheiro e datas
# --------------------------------------------------------------------------
@pytest.mark.parametrize("bad_amount", [0.30000000000000004, 10.999, 0, -5.0])
def test_expense_refuses_bad_amounts(conn, bad_amount):
    month_id = add_open_month(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, month_id, amount=bad_amount)

@pytest.mark.parametrize("good_amount", [0.01, 10.9, 1234.56, 10])
def test_expense_accepts_cent_amounts(conn, good_amount):
    month_id = add_open_month(conn)
    assert add_expense(conn, month_id, amount=good_amount) > 0

def test_salary_refuses_more_than_two_decimals(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_open_month(conn, salary=3000.123)

def test_sum_of_cent_amounts_is_exact_after_round(conn):
    month_id = add_open_month(conn)
    for _ in range(3):
        add_expense(conn, month_id, amount=0.1)
    total = conn.execute(
        "SELECT ROUND(SUM(amount), 2) FROM expense WHERE month_id = ?", (month_id,)
    ).fetchone()[0]
    assert total == 0.3

@pytest.mark.parametrize("bad_date", ["2026-1-5", "05/10/2026", "2026-02-30", "2026-13-01", "abc", ""])
def test_expense_refuses_bad_dates(conn, bad_date):
    month_id = add_open_month(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, month_id, occurred_on=bad_date)

def test_expense_accepts_valid_date(conn):
    month_id = add_open_month(conn)
    add_expense(conn, month_id, occurred_on="2026-02-28")

# --------------------------------------------------------------------------
# expense e extra_income
# --------------------------------------------------------------------------
def test_expense_requires_existing_month_and_category(conn):
    month_id = add_open_month(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, 999)
    with pytest.raises(sqlite3.IntegrityError):
        add_expense(conn, month_id, category_id=999)

def test_expense_payment_method_is_only_debit(conn):
    month_id = add_open_month(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO expense (month_id, amount, occurred_on, category_id, payment_method) "
            "VALUES (?, 10, '2026-10-05', 1, 'cash')",
            (month_id,),
        )

def test_category_with_expenses_cannot_be_deleted(conn):
    month_id = add_open_month(conn)
    add_expense(conn, month_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM category WHERE id = 1")

def test_extra_income_source_and_amount(conn):
    month_id = add_open_month(conn)
    conn.execute(
        "INSERT INTO extra_income (month_id, amount, occurred_on) VALUES (?, 200, '2026-10-10')",
        (month_id,),
    )
    assert conn.execute("SELECT source FROM extra_income").fetchone()[0] == "manual"
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO extra_income (month_id, amount, occurred_on, source) "
            "VALUES (?, 50, '2026-10-10', 'gift')",
            (month_id,),
        )

# --------------------------------------------------------------------------
# Modelos e copias do mes
# --------------------------------------------------------------------------
def test_template_amount_must_be_positive_cents(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO fixed_expense_template (name, amount) VALUES ('Aluguel', 0)")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO savings_quota_template (name, amount) VALUES ('Reserva', 10.001)")

@pytest.mark.parametrize("bad_flag", [2, -1])
def test_is_active_accepts_only_zero_or_one(conn, bad_flag):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO fixed_expense_template (name, amount, is_active) VALUES ('Luz', 100, ?)",
            (bad_flag,),
        )

def test_deleting_template_sets_copy_template_id_to_null(conn):
    month_id = add_open_month(conn)
    template_id = conn.execute(
        "INSERT INTO fixed_expense_template (name, amount) VALUES ('Aluguel', 1200)"
    ).lastrowid
    conn.execute(
        "INSERT INTO month_fixed_expense (month_id, template_id, name, amount) "
        "VALUES (?, ?, 'Aluguel', 1200)",
        (month_id, template_id),
    )
    conn.execute("DELETE FROM fixed_expense_template WHERE id = ?", (template_id,))
    row = conn.execute("SELECT template_id, name FROM month_fixed_expense").fetchone()
    assert row["template_id"] is None
    assert row["name"] == "Aluguel"

def test_template_cannot_be_copied_twice_into_same_month(conn):
    month_id = add_open_month(conn)
    template_id = conn.execute(
        "INSERT INTO savings_quota_template (name, amount) VALUES ('Reserva', 300)"
    ).lastrowid
    sql = (
        "INSERT INTO month_savings_quota (month_id, template_id, name, amount) "
        "VALUES (?, ?, 'Reserva', 300)"
    )
    conn.execute(sql, (month_id, template_id))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql, (month_id, template_id))

def test_copies_without_template_can_repeat_in_same_month(conn):
    month_id = add_open_month(conn)
    sql = (
        "INSERT INTO month_fixed_expense (month_id, template_id, name, amount) "
        "VALUES (?, NULL, 'Avulso', 50)"
    )
    conn.execute(sql, (month_id,))
    conn.execute(sql, (month_id,))

# --------------------------------------------------------------------------
# Cartao de credito
# --------------------------------------------------------------------------
def add_card_month(conn, month_id, reported_value=500.0):
    card_id = conn.execute("INSERT INTO credit_card (name) VALUES ('Nubank')").lastrowid
    return conn.execute(
        "INSERT INTO credit_card_month (credit_card_id, month_id, reported_value) VALUES (?, ?, ?)",
        (card_id, month_id, reported_value),
    ).lastrowid, card_id

def test_card_month_is_unique_per_card_and_month(conn):
    month_id = add_open_month(conn)
    _, card_id = add_card_month(conn, month_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO credit_card_month (credit_card_id, month_id) VALUES (?, ?)",
            (card_id, month_id),
        )

def test_reported_value_cannot_be_negative_but_can_be_zero(conn):
    month_id = add_open_month(conn)
    add_card_month(conn, month_id, reported_value=0.0)
    other_card = conn.execute("INSERT INTO credit_card (name) VALUES ('Itau')").lastrowid
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO credit_card_month (credit_card_id, month_id, reported_value) "
            "VALUES (?, ?, -1)",
            (other_card, month_id),
        )

def test_card_updated_at_validates_date(conn):
    month_id = add_open_month(conn)
    card_id = conn.execute("INSERT INTO credit_card (name) VALUES ('Nubank')").lastrowid
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO credit_card_month (credit_card_id, month_id, updated_at) "
            "VALUES (?, ?, '2026-02-30')",
            (card_id, month_id),
        )

@pytest.mark.parametrize("entry_type", ["payment", "refund"])
def test_card_entry_valid_types(conn, entry_type):
    month_id = add_open_month(conn)
    card_month_id, _ = add_card_month(conn, month_id)
    conn.execute(
        "INSERT INTO credit_card_entry (credit_card_month_id, type, amount, occurred_on) "
        "VALUES (?, ?, 100, '2026-10-05')",
        (card_month_id, entry_type),
    )

def test_card_entry_refuses_bad_type_and_zero_amount(conn):
    month_id = add_open_month(conn)
    card_month_id, _ = add_card_month(conn, month_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO credit_card_entry (credit_card_month_id, type, amount, occurred_on) "
            "VALUES (?, 'purchase', 100, '2026-10-05')",
            (card_month_id,),
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO credit_card_entry (credit_card_month_id, type, amount, occurred_on) "
            "VALUES (?, 'payment', 0, '2026-10-05')",
            (card_month_id,),
        )
