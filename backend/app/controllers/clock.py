from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo
from app.config import load_config

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def today(timezone_name: str | None = None) -> date:
    name = timezone_name or load_config().timezone
    return _utc_now().astimezone(ZoneInfo(name)).date()
