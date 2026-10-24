import json
from datetime import date
from app.core.models import CardEntry, CardEntryType, Notice, NoticeCode, Template

def to_date(text: str) -> date:
    return date.fromisoformat(text)

def to_date_or_none(text: str | None) -> date | None:
    return None if text is None else date.fromisoformat(text)

def to_iso(day: date) -> str:
    return day.isoformat()

def to_template(row: dict) -> Template:
    return Template(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        is_active=bool(row["is_active"]),
    )

def to_card_entry(row: dict) -> CardEntry:
    return CardEntry(type=CardEntryType(row["type"]), amount=row["amount"])

def notices_from_json(text: str) -> list[Notice]:
    return [
        Notice(id=item["id"], code=NoticeCode(item["code"]), params=item["params"])
        for item in json.loads(text)
    ]

def notices_to_json(notices: list[Notice]) -> str:
    return json.dumps(
        [{"id": n.id, "code": n.code.value, "params": n.params} for n in notices],
        ensure_ascii=False,
    )
