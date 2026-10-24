from app.controllers.breakdown import build_breakdown
from app.controllers.session import session
from app.core.balance import free_balance
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months

def test_breakdown_of_an_empty_month_is_only_the_salary(db_path):
    with session() as conn:
        month_id = months.create_month(conn, 2026, 10, 3000.0)
        breakdown = build_breakdown(conn, months.get_month(conn, month_id))
    assert (breakdown.salary, breakdown.extra_incomes, breakdown.fixed_expenses) == (3000.0, 0.0, 0.0)
    assert (breakdown.savings_quotas, breakdown.debit_expenses, breakdown.credit_card_total) == (0.0, 0.0, 0.0)

def test_breakdown_of_a_complete_month(seed_october):
    seeded = seed_october()
    with session() as conn:
        incomes.insert_extra_income(conn, seeded["month_id"], 200.0, "2026-10-10", "Freela", "manual")
        month = months.get_month(conn, seeded["month_id"])
        breakdown = build_breakdown(conn, month)
        balance = free_balance(breakdown)
    assert breakdown.salary == 3000.0
    assert breakdown.extra_incomes == 200.0
    assert breakdown.fixed_expenses == 1200.0
    assert breakdown.savings_quotas == 300.0
    assert breakdown.debit_expenses == 450.5
    assert breakdown.credit_card_total == 800.25
    assert balance == 449.25  

def test_card_total_counts_payments_but_not_refunds_and_sums_all_cards(db_path):
    with session() as conn:
        month_id = months.create_month(conn, 2026, 10, 3000.0)
        first = cards.insert_card_month(conn, cards.insert_card(conn, "Nubank"), month_id)
        second = cards.insert_card_month(conn, cards.insert_card(conn, "Itau"), month_id)
        cards.update_reported_value(conn, first, 150.0, "2026-10-10")
        cards.insert_entry(conn, first, "payment", 20.0, "2026-10-09")
        cards.insert_entry(conn, first, "refund", 40.0, "2026-10-08")  
        cards.update_reported_value(conn, second, 0.1, "2026-10-10")
        cards.insert_entry(conn, second, "payment", 0.2, "2026-10-09")
        breakdown = build_breakdown(conn, months.get_month(conn, month_id))
    assert breakdown.credit_card_total == 170.3  
