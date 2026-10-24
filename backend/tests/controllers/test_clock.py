from datetime import date, datetime, timezone
import pytest
from zoneinfo import ZoneInfoNotFoundError
from app.controllers import clock

def freeze_utc(monkeypatch, *args):
    monkeypatch.setattr(clock, "_utc_now", lambda: datetime(*args, tzinfo=timezone.utc))

def test_plan_example_9pm_in_brasilia_is_still_the_same_day(monkeypatch):
    freeze_utc(monkeypatch, 2026, 11, 1, 0, 0)
    assert clock.today("America/Sao_Paulo") == date(2026, 10, 31)
    assert clock.today("UTC") == date(2026, 11, 1)

def test_midnight_in_brasilia_is_the_new_day(monkeypatch):
    freeze_utc(monkeypatch, 2026, 11, 1, 3, 0)
    assert clock.today("America/Sao_Paulo") == date(2026, 11, 1)

def test_default_timezone_comes_from_the_configuration(monkeypatch):
    freeze_utc(monkeypatch, 2026, 11, 1, 1, 0)
    monkeypatch.delenv("TIMEZONE", raising=False)
    assert clock.today() == date(2026, 10, 31)  
    monkeypatch.setenv("TIMEZONE", "UTC")
    assert clock.today() == date(2026, 11, 1)

def test_unknown_timezone_fails_loudly():
    with pytest.raises(ZoneInfoNotFoundError):
        clock.today("Nowhere/Land")

def test_the_real_clock_returns_a_date():
    assert isinstance(clock.today(), date)
