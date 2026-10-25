import pytest

from app.api import messages
from app.core.dates import MONTH_NAMES_PT


def test_month_names_match_the_core():
    assert messages.MONTH_NAMES == MONTH_NAMES_PT


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (0, "R$ 0,00"),
        (5.5, "R$ 5,50"),
        (1234.56, "R$ 1.234,56"),
        (1000000, "R$ 1.000.000,00"),
        (-1300.25, "-R$ 1.300,25"),
    ],
)
def test_brl(value, text):
    assert messages.brl(value) == text


def test_join_pt():
    assert messages.join_pt([]) == ""
    assert messages.join_pt(["a"]) == "a"
    assert messages.join_pt(["a", "b"]) == "a e b"
    assert messages.join_pt(["a", "b", "c"]) == "a, b e c"


def test_month_name_from_the_label():
    assert messages.month_name("2026-03") == "março"
    assert messages.month_name("2026-12") == "dezembro"


# --------------------------------------------------------------------------
# Erros
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("code", "params", "expected"),
    [
        (
            "value_decreased",
            {"difference": 50.0},
            "O valor do cartão diminuiu R$ 50,00. Foi um pagamento ou um estorno?",
        ),
        (
            "month_closed",
            {"closed_month": "2026-10", "current_month": "2026-11"},
            "O mês de outubro já fechou. Quer registrar em novembro?",
        ),
        ("future_date", {}, "Não é possível registrar com data de mês futuro. Escolha uma data deste mês."),
        (
            "payment_exceeds_reported_value",
            {"amount": 120.0, "reported_value": 100.0},
            "O pagamento de R$ 120,00 é maior que o valor informado do cartão (R$ 100,00).",
        ),
        ("leftover_income_locked", {}, "Esta renda veio da sobra do mês e não pode ser editada nem apagada."),
        ("name_already_exists", {"name": "Mercado"}, 'Já existe uma categoria chamada "Mercado".'),
        ("default_category_locked", {}, 'A categoria "Outros" não pode ser desativada.'),
        ("category_inactive", {}, "Esta categoria está desativada. Escolha outra."),
        ("no_open_month", {}, "Informe o seu salário em Cadastros antes de fazer lançamentos."),
        ("not_found", {"resource": "category", "id": 7}, "Não encontramos a categoria."),
        ("not_found", {}, "Não encontramos o item pedido."),
        ("internal_error", {}, "Algo deu errado no servidor. Tente de novo em instantes."),
        ("something_new", {}, "Não foi possível concluir a operação."),
    ],
)
def test_error_messages(code, params, expected):
    assert messages.error_message(code, params) == expected


def test_validation_error_message_lists_the_fields():
    params = {"fields": [{"field": "amount", "message": "x"}, {"field": "occurred_on", "message": "y"}]}
    assert messages.error_message("validation_error", params) == "Dados inválidos. Confira: amount e occurred_on."
    assert messages.error_message("validation_error", {"fields": []}) == "Dados inválidos."


def test_not_found_for_a_card_without_total_in_the_month():
    text = messages.error_message("not_found", {"resource": "credit_card_month", "id": 1})
    assert "Reative o cartão" in text


# --------------------------------------------------------------------------
# Avisos
# --------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("days_left", "cards", "expected"),
    [
        (2, False, "O mês fecha em 2 dias."),
        (1, False, "O mês fecha em 1 dia."),
        (0, False, "Hoje é o último dia do mês."),
        (2, True, "O mês fecha em 2 dias. Atualize o valor dos cartões."),
        (1, True, "O mês fecha em 1 dia. Atualize o valor dos cartões."),
        (0, True, "Hoje é o último dia do mês. Atualize o valor dos cartões antes de virar."),
    ],
)
def test_month_ending_notice(days_left, cards, expected):
    params = {"days_left": days_left, "has_active_cards": cards}
    assert messages.notice_message("month_ending", params) == expected


def test_card_not_updated_notice_singular_and_plural():
    one = messages.notice_message("credit_card_not_updated", {"card_names": ["Nubank"]})
    assert one == "O cartão Nubank ainda não foi atualizado neste mês."
    many = messages.notice_message("credit_card_not_updated", {"card_names": ["Nubank", "Itaú", "Inter"]})
    assert many == "Os cartões Nubank, Itaú e Inter ainda não foram atualizados neste mês."


def test_negative_month_notice():
    text = messages.notice_message(
        "month_closed_negative",
        {"closed_month": "2026-10", "current_month": "2026-11", "final_balance": -1300.25},
    )
    assert text == "Outubro fechou no negativo (R$ 1.300,25 abaixo de zero). O valor não passa para novembro."


def test_unused_months_notice_singular_and_plural():
    assert messages.notice_message("unused_months", {"months": ["2026-11"]}) == (
        "O mês de novembro ficou sem registro, porque o app não foi aberto."
    )
    assert messages.notice_message("unused_months", {"months": ["2026-11", "2026-12"]}) == (
        "Os meses de novembro e dezembro ficaram sem registro, porque o app não foi aberto."
    )


def test_leftover_question():
    assert messages.leftover_message(10, 249.25) == (
        "Outubro fechou com sobra de R$ 249,25. Quer levar esse valor para este mês?"
    )
