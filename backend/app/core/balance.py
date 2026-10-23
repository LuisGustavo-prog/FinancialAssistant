from app.core.models import Breakdown, MonthResult
from app.core.money import round_money, sum_money

def free_balance(breakdown: Breakdown) -> float:
    return sum_money(
        [
            breakdown.salary,
            breakdown.extra_incomes,
            -breakdown.fixed_expenses,
            -breakdown.savings_quotas,
            -breakdown.debit_expenses,
            -breakdown.credit_card_total,
        ]
    )

def month_result(final_balance: float) -> MonthResult:
    return MonthResult.GREEN if round_money(final_balance) >= 0 else MonthResult.RED

def has_leftover(final_balance: float) -> bool:
    return round_money(final_balance) > 0
