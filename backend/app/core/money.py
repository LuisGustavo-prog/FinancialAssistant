import math
from collections.abc import Iterable

CENT_DIGITS = 2

def round_money(value: float) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Valor monetario invalido: {value!r}")
    return round(number, CENT_DIGITS) + 0.0

def sum_money(values: Iterable[float]) -> float:
    return round_money(math.fsum(values))

def money_equals(first: float, second: float) -> bool:
    return round_money(first) == round_money(second)
