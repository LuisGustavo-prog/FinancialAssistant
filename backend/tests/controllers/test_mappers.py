from datetime import date
import pytest
from app.controllers import mappers
from app.core.models import CardEntry, CardEntryType, Notice, NoticeCode, Template

def test_dates_round_trip_through_text():
    assert mappers.to_date_or_none("2026-10-23") == date(2026, 10, 23)
    assert mappers.to_date_or_none(None) is None
    assert mappers.to_iso(date(2026, 3, 1)) == "2026-03-01"
    assert mappers.to_date(mappers.to_iso(date(2026, 3, 1))) == date(2026, 3, 1)

def test_invalid_date_text_fails():
    with pytest.raises(ValueError):
        mappers.to_date("2026-02-30")

@pytest.mark.parametrize(("flag", "expected"), [(1, True), (0, False)])
def test_template_converts_is_active_to_bool(flag, expected):
    row = {"id": 3, "name": "Aluguel", "amount": 1200.0, "is_active": flag}
    template = mappers.to_template(row)
    assert template == Template(3, "Aluguel", 1200.0, expected)
    assert template.is_active is expected

def test_card_entry_converts_the_type_to_the_enum():
    row = {"id": 1, "type": "refund", "amount": 40.0, "occurred_on": "2026-10-05"}
    assert mappers.to_card_entry(row) == CardEntry(CardEntryType.REFUND, 40.0)

def test_empty_notices_json():
    assert mappers.notices_from_json("[]") == []
    assert mappers.notices_to_json([]) == "[]"

def test_notices_round_trip_through_json():
    notices = [
        Notice(1, NoticeCode.MONTH_CLOSED_NEGATIVE, {"closed_month": "2026-10", "final_balance": -120.5}),
        Notice(2, NoticeCode.UNUSED_MONTHS, {"months": ["2026-11", "2026-12"]}),
    ]
    assert mappers.notices_from_json(mappers.notices_to_json(notices)) == notices

def test_notices_json_keeps_accents_readable():
    text = mappers.notices_to_json([Notice(1, NoticeCode.CREDIT_CARD_NOT_UPDATED, {"card_names": ["Cartão Nubank"]})])
    assert "Cartão Nubank" in text
