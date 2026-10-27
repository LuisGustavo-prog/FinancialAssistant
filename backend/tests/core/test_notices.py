from datetime import date

import pytest

from app.core.models import CardStatus, ClosedMonth, LeftoverDecision, Notice, NoticeCode
from app.core.notices import (
    active_notices,
    card_not_updated_notice,
    closing_notices,
    dismiss_stored_notice,
    month_ending_notice,
    store_notices,
)


def closed(year=2026, month=10, balance=-120.0):
    return ClosedMonth(year, month, balance, None if balance <= 0 else LeftoverDecision.PENDING)


def stored(id, code=NoticeCode.MONTH_CLOSED_NEGATIVE, **params):
    return Notice(id=id, code=code, params=params)


# --------------------------------------------------------------------------
# Fim de mes
# --------------------------------------------------------------------------
@pytest.mark.parametrize("day", [1, 15, 27, 28])
def test_no_month_ending_notice_before_the_last_three_days(day):
    assert month_ending_notice(date(2026, 10, day), has_active_cards=True) is None


@pytest.mark.parametrize(("day", "days_left"), [(29, 2), (30, 1), (31, 0)])
def test_month_ending_notice_in_the_last_three_days(day, days_left):
    notice = month_ending_notice(date(2026, 10, day), has_active_cards=True)
    assert notice == Notice(
        id=None,
        code=NoticeCode.MONTH_ENDING,
        params={"days_left": days_left, "has_active_cards": True},
    )


def test_month_ending_notice_tells_when_there_is_no_active_card():
    notice = month_ending_notice(date(2026, 10, 30), has_active_cards=False)
    assert notice.params == {"days_left": 1, "has_active_cards": False}


def test_month_ending_in_february_and_leap_year():
    assert month_ending_notice(date(2026, 2, 25), True) is None
    assert month_ending_notice(date(2026, 2, 26), True).params["days_left"] == 2
    assert month_ending_notice(date(2028, 2, 26), True) is None
    assert month_ending_notice(date(2028, 2, 27), True).params["days_left"] == 2


# --------------------------------------------------------------------------
# Cartao nao atualizado
# --------------------------------------------------------------------------
def test_no_card_notice_before_day_ten():
    cards = [CardStatus("Nubank", None)]
    assert card_not_updated_notice(date(2026, 10, 9), cards) is None


def test_card_notice_from_day_ten_lists_the_cards_never_updated():
    cards = [CardStatus("Nubank", None), CardStatus("Itau", date(2026, 10, 5)), CardStatus("Inter", None)]
    notice = card_not_updated_notice(date(2026, 10, 10), cards)
    assert notice == Notice(
        id=None,
        code=NoticeCode.CREDIT_CARD_NOT_UPDATED,
        params={"card_names": ["Nubank", "Inter"]},
    )


def test_no_card_notice_when_every_card_was_updated_or_there_are_no_cards():
    assert card_not_updated_notice(date(2026, 10, 20), [CardStatus("Nubank", date(2026, 10, 2))]) is None
    assert card_not_updated_notice(date(2026, 10, 20), []) is None


# --------------------------------------------------------------------------
# Avisos criados no fechamento
# --------------------------------------------------------------------------
def test_negative_month_creates_the_negative_notice():
    notices = closing_notices(closed(balance=-120.0), 2026, 11)
    assert notices == [
        Notice(
            id=None,
            code=NoticeCode.MONTH_CLOSED_NEGATIVE,
            params={"closed_month": "2026-10", "current_month": "2026-11", "final_balance": -120.0},
        )
    ]


@pytest.mark.parametrize("balance", [0.0, 50.0, -5e-17])
def test_zero_positive_or_noise_balance_creates_no_negative_notice(balance):
    assert closing_notices(closed(balance=balance), 2026, 11) == []


def test_skipped_months_create_the_unused_months_notice():
    notices = closing_notices(closed(balance=100.0), 2027, 1)
    assert notices == [Notice(id=None, code=NoticeCode.UNUSED_MONTHS, params={"months": ["2026-11", "2026-12"]})]


def test_negative_and_skipped_months_create_both_notices_in_order():
    notices = closing_notices(closed(balance=-30.0), 2026, 12)
    assert [n.code for n in notices] == [NoticeCode.MONTH_CLOSED_NEGATIVE, NoticeCode.UNUSED_MONTHS]
    assert notices[0].params["current_month"] == "2026-12"
    assert notices[1].params == {"months": ["2026-11"]}


def test_closing_notice_params_are_json_friendly():
    import json

    for notice in closing_notices(closed(balance=-30.0), 2027, 1):
        json.dumps(notice.params)


# --------------------------------------------------------------------------
# Avisos guardados
# --------------------------------------------------------------------------
def test_store_notices_assigns_sequential_ids_starting_at_one():
    new = closing_notices(closed(balance=-30.0), 2027, 1)
    result = store_notices([], new)
    assert [n.id for n in result] == [1, 2]
    assert [n.code for n in result] == [n.code for n in new]


def test_store_notices_continues_after_the_highest_existing_id():
    existing = [stored(3), stored(7)]
    result = store_notices(existing, [Notice(None, NoticeCode.UNUSED_MONTHS, {"months": ["2026-11"]})])
    assert [n.id for n in result] == [3, 7, 8]


def test_ids_are_not_reused_after_dismissing_the_last_one():
    result = dismiss_stored_notice([stored(1), stored(2)], 2)
    assert [n.id for n in result] == [1]
    # o proximo recebe 2 de novo; ok porque o aviso 2 ja nao existe em lugar nenhum
    assert store_notices(result, [Notice(None, NoticeCode.UNUSED_MONTHS, {})])[-1].id == 2


def test_dismiss_removes_only_the_requested_notice():
    result = dismiss_stored_notice([stored(1), stored(2), stored(3)], 2)
    assert [n.id for n in result] == [1, 3]


def test_dismiss_of_unknown_id_changes_nothing():
    original = [stored(1), stored(2)]
    assert dismiss_stored_notice(original, 99) == original


# --------------------------------------------------------------------------
# Lista da home
# --------------------------------------------------------------------------
def test_home_has_no_notices_in_a_quiet_day():
    assert active_notices([], date(2026, 10, 5), [CardStatus("Nubank", None)]) == []


def test_home_order_is_stored_then_month_ending_then_card():
    today = date(2026, 10, 30)
    cards = [CardStatus("Nubank", None)]
    notices = active_notices([stored(2), stored(1, NoticeCode.UNUSED_MONTHS)], today, cards)
    assert [(n.id, n.code) for n in notices] == [
        (1, NoticeCode.UNUSED_MONTHS),
        (2, NoticeCode.MONTH_CLOSED_NEGATIVE),
        (None, NoticeCode.MONTH_ENDING),
        (None, NoticeCode.CREDIT_CARD_NOT_UPDATED),
    ]


def test_month_ending_in_home_knows_whether_there_are_active_cards():
    with_cards = active_notices([], date(2026, 10, 31), [CardStatus("Nubank", date(2026, 10, 20))])
    without_cards = active_notices([], date(2026, 10, 31), [])
    assert with_cards[0].params["has_active_cards"] is True
    assert without_cards[0].params["has_active_cards"] is False
