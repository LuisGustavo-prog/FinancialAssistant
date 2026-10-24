import sqlite3
from collections import defaultdict
from app.controllers.mappers import to_card_entry
from app.core.credit_card import card_total
from app.core.models import Breakdown, CardEntry
from app.core.money import sum_money
from app.db.repositories import credit_card_repository as cards
from app.db.repositories import expense_repository as expenses
from app.db.repositories import extra_income_repository as incomes
from app.db.repositories import month_repository as months

def build_breakdown(conn: sqlite3.Connection, month: dict) -> Breakdown:
    month_id = month["id"]

    entries_by_card_month: dict[int, list[CardEntry]] = defaultdict(list)
    for row in cards.list_entries_by_month(conn, month_id):
        entries_by_card_month[row["credit_card_month_id"]].append(to_card_entry(row))

    card_totals = [
        card_total(card_month["reported_value"], entries_by_card_month[card_month["id"]])
        for card_month in cards.list_card_months(conn, month_id)
    ]

    return Breakdown(
        salary=month["salary"],
        extra_incomes=incomes.sum_extra_incomes(conn, month_id),
        fixed_expenses=months.sum_fixed_expenses(conn, month_id),
        savings_quotas=months.sum_savings_quotas(conn, month_id),
        debit_expenses=expenses.sum_expenses(conn, month_id),
        credit_card_total=sum_money(card_totals),
    )
