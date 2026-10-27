from collections.abc import Iterable
from datetime import date
from app.core.dates import days_left_in_month, month_label, months_between
from app.core.models import CardStatus, ClosedMonth, Notice, NoticeCode
from app.core.money import round_money

MONTH_ENDING_LAST_DAYS = 3
CARD_NOT_UPDATED_FROM_DAY = 10


def month_ending_notice(today: date, has_active_cards: bool) -> Notice | None:
    days_left = days_left_in_month(today)
    if days_left >= MONTH_ENDING_LAST_DAYS:
        return None
    return Notice(
        id=None,
        code=NoticeCode.MONTH_ENDING,
        params={"days_left": days_left, "has_active_cards": has_active_cards},
    )


def card_not_updated_notice(today: date, cards: Iterable[CardStatus]) -> Notice | None:
    if today.day < CARD_NOT_UPDATED_FROM_DAY:
        return None
    names = [card.name for card in cards if card.updated_at is None]
    if not names:
        return None
    return Notice(id=None, code=NoticeCode.CREDIT_CARD_NOT_UPDATED, params={"card_names": names})


def closing_notices(closed: ClosedMonth, current_year: int, current_month: int) -> list[Notice]:
    notices: list[Notice] = []

    final_balance = round_money(closed.final_balance)
    if final_balance < 0:
        notices.append(
            Notice(
                id=None,
                code=NoticeCode.MONTH_CLOSED_NEGATIVE,
                params={
                    "closed_month": month_label(closed.year, closed.month_number),
                    "current_month": month_label(current_year, current_month),
                    "final_balance": final_balance,
                },
            )
        )

    skipped = months_between((closed.year, closed.month_number), (current_year, current_month))
    if skipped:
        notices.append(
            Notice(
                id=None,
                code=NoticeCode.UNUSED_MONTHS,
                params={"months": [month_label(year, month) for year, month in skipped]},
            )
        )
    return notices


def store_notices(existing: Iterable[Notice], new_notices: Iterable[Notice]) -> list[Notice]:
    stored = list(existing)
    next_id = max((n.id for n in stored if n.id is not None), default=0) + 1
    for notice in new_notices:
        stored.append(Notice(id=next_id, code=notice.code, params=notice.params))
        next_id += 1
    return stored


def dismiss_stored_notice(existing: Iterable[Notice], notice_id: int) -> list[Notice]:
    return [n for n in existing if n.id != notice_id]


def active_notices(
    stored: Iterable[Notice],
    today: date,
    cards: Iterable[CardStatus],
) -> list[Notice]:
    card_list = list(cards)
    notices = sorted(stored, key=lambda n: n.id if n.id is not None else 0)

    month_ending = month_ending_notice(today, has_active_cards=bool(card_list))
    if month_ending is not None:
        notices.append(month_ending)

    card_notice = card_not_updated_notice(today, card_list)
    if card_notice is not None:
        notices.append(card_notice)
    return notices
