"""Regras de datas e de limites do mes. Python puro e sem relogio.

Estas funcoes sempre recebem a data como parametro. Quem le o relogio (no
fuso configurado) e o controller, nunca o core.
"""

import calendar
from datetime import date


def first_day_of_month(day: date) -> date:
    """Primeiro dia do mes de `day`."""
    return day.replace(day=1)


def last_day_of_month(day: date) -> date:
    """Ultimo dia do mes de `day` (considera anos bissextos)."""
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=last)


def days_left_in_month(today: date) -> int:
    """Dias que faltam para o ultimo dia do mes. No ultimo dia vale 0."""
    return (last_day_of_month(today) - today).days


def days_since(earlier: date, today: date) -> int:
    """Dias corridos de `earlier` ate `today`. O resultado tem sinal:
    e negativo se `earlier` for depois de `today`."""
    return (today - earlier).days


def is_same_month(first: date, second: date) -> bool:
    """True se as duas datas estao no mesmo mes do mesmo ano."""
    return (first.year, first.month) == (second.year, second.month)


def next_month(year: int, month: int) -> tuple[int, int]:
    """Devolve (ano, mes) do mes seguinte. Dezembro vira janeiro do ano seguinte."""
    if not 1 <= month <= 12:
        raise ValueError(f"Mes invalido: {month}")
    if month == 12:
        return year + 1, 1
    return year, month + 1
