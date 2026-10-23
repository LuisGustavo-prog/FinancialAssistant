from datetime import date

import pytest

from app.core.credit_card import (
    OUTDATED_AFTER_DAYS,
    card_total,
    days_since_update,
    is_outdated,
    payments_total,
    plan_payment,
    plan_reported_value_update,
)
from app.core.models import CardEntry, CardEntryType
from app.errors import PaymentExceedsReportedValueError, ValueDecreasedError

PAYMENT = CardEntryType.PAYMENT
REFUND = CardEntryType.REFUND


# --------------------------------------------------------------------------
# Total do cartao
# --------------------------------------------------------------------------
def test_total_without_entries_is_the_reported_value():
    assert card_total(150.0, []) == 150.0


def test_payments_total_ignores_refunds():
    entries = [CardEntry(PAYMENT, 20.0), CardEntry(REFUND, 40.0), CardEntry(PAYMENT, 10.5)]
    assert payments_total(entries) == 30.5


def test_total_ignores_refund_lines():
    assert card_total(60.0, [CardEntry(REFUND, 40.0)]) == 60.0


def test_total_rounds_floating_point_noise():
    assert card_total(0.1, [CardEntry(PAYMENT, 0.2)]) == 0.3


# --------------------------------------------------------------------------
# Os dois exemplos do plano
# --------------------------------------------------------------------------
def test_plan_example_1_pay_everything_mid_month_and_keep_using_the_card():
    # 1. O banco mostra 150. Total: 150.
    reported = 150.0
    entries: list[CardEntry] = []
    assert card_total(reported, entries) == 150.0

    # 2. Paga os 150 e toca em "Registrar pagamento": linha de 150, valor informado zera.
    plan = plan_payment(reported, 150.0)
    entries.append(plan.entry)
    reported = plan.new_reported_value
    assert plan.entry == CardEntry(PAYMENT, 150.0)
    assert reported == 0.0
    assert card_total(reported, entries) == 150.0

    # 3. Gasta mais 50 e o banco mostra 50. Total: 50 + 150 = 200.
    assert plan_reported_value_update(reported, 50.0) is None  # aumento nao cria linha
    reported = 50.0
    assert card_total(reported, entries) == 200.0


def test_plan_example_2_partial_payment_stores_the_difference_not_the_old_value():
    # 1. O banco mostra 50. O usuario paga 20 e o banco passa a mostrar 30.
    entries: list[CardEntry] = []
    line = plan_reported_value_update(50.0, 30.0, PAYMENT)
    assert line == CardEntry(PAYMENT, 20.0)  # a linha guarda 20, e nao 50
    entries.append(line)

    # 2. Total: 30 + 20 = 50.
    assert card_total(30.0, entries) == 50.0

    # 3. Guardar o valor antigo daria 50 + 30 = 80, contando o mesmo dinheiro duas vezes.
    wrong_entries = [CardEntry(PAYMENT, 50.0)]
    assert card_total(30.0, wrong_entries) == 80.0


# --------------------------------------------------------------------------
# Atualizar o valor informado
# --------------------------------------------------------------------------
@pytest.mark.parametrize("new_value", [100.0, 100.01, 250.0])
def test_same_or_higher_value_creates_no_line(new_value):
    assert plan_reported_value_update(100.0, new_value) is None


def test_decrease_without_type_raises_value_decreased_with_the_difference():
    with pytest.raises(ValueDecreasedError) as info:
        plan_reported_value_update(100.0, 50.0)
    assert info.value.code == "value_decreased"
    assert info.value.params == {"difference": 50.0}


def test_decrease_as_payment_creates_a_payment_line_with_the_difference():
    assert plan_reported_value_update(100.0, 60.0, PAYMENT) == CardEntry(PAYMENT, 40.0)


def test_decrease_as_refund_creates_a_refund_line_and_the_total_shrinks():
    line = plan_reported_value_update(100.0, 60.0, REFUND)
    assert line == CardEntry(REFUND, 40.0)
    assert card_total(60.0, [line]) == 60.0


def test_difference_is_rounded():
    line = plan_reported_value_update(0.3, 0.1, PAYMENT)
    assert line == CardEntry(PAYMENT, 0.2)


def test_decrease_type_is_ignored_when_the_value_did_not_decrease():
    assert plan_reported_value_update(100.0, 120.0, PAYMENT) is None


def test_reported_value_can_go_down_to_zero():
    assert plan_reported_value_update(80.0, 0.0, PAYMENT) == CardEntry(PAYMENT, 80.0)


def test_negative_reported_value_is_refused():
    with pytest.raises(ValueError):
        plan_reported_value_update(80.0, -1.0, PAYMENT)


# --------------------------------------------------------------------------
# Botao "Registrar pagamento"
# --------------------------------------------------------------------------
def test_partial_payment_reduces_the_reported_value():
    plan = plan_payment(100.0, 30.0)
    assert plan.entry == CardEntry(PAYMENT, 30.0)
    assert plan.new_reported_value == 70.0


def test_payment_equal_to_the_reported_value_is_allowed():
    plan = plan_payment(100.0, 100.0)
    assert plan.new_reported_value == 0.0


def test_payment_greater_than_the_reported_value_is_refused():
    with pytest.raises(PaymentExceedsReportedValueError) as info:
        plan_payment(100.0, 100.01)
    assert info.value.code == "payment_exceeds_reported_value"
    assert info.value.params == {"amount": 100.01, "reported_value": 100.0}


def test_payment_comparison_rounds_first():
    plan = plan_payment(0.3, 0.1 + 0.2)  # 0.30000000000000004 e igual a 0.3
    assert plan.new_reported_value == 0.0


@pytest.mark.parametrize("bad_amount", [0.0, -5.0])
def test_payment_must_be_positive(bad_amount):
    with pytest.raises(ValueError):
        plan_payment(100.0, bad_amount)


def test_payment_on_a_zero_reported_value_is_refused():
    with pytest.raises(PaymentExceedsReportedValueError):
        plan_payment(0.0, 10.0)


# --------------------------------------------------------------------------
# Atualizado ha X dias
# --------------------------------------------------------------------------
TODAY = date(2026, 10, 23)


def test_never_updated_has_no_days_and_is_outdated():
    assert days_since_update(None, TODAY) is None
    assert is_outdated(None, TODAY) is True


def test_updated_today_is_zero_days_and_fresh():
    assert days_since_update(TODAY, TODAY) == 0
    assert is_outdated(TODAY, TODAY) is False


def test_outdated_only_after_more_than_seven_days():
    assert OUTDATED_AFTER_DAYS == 7
    assert is_outdated(date(2026, 10, 16), TODAY) is False  # 7 dias
    assert is_outdated(date(2026, 10, 15), TODAY) is True  # 8 dias


def test_days_since_update_across_months():
    assert days_since_update(date(2026, 9, 28), date(2026, 10, 2)) == 4


def test_future_update_date_never_gives_negative_days():
    assert days_since_update(date(2026, 10, 25), TODAY) == 0
    assert is_outdated(date(2026, 10, 25), TODAY) is False
