from typing import Annotated
from pydantic import AfterValidator, Field, StringConstraints


def _round_cents(value: float) -> float:
    return round(value, 2) + 0.0


def _positive_cents(value: float) -> float:
    rounded = _round_cents(value)
    if rounded <= 0:
        raise ValueError("o valor precisa ser de pelo menos R$ 0,01")
    return rounded


PositiveMoney = Annotated[float, Field(gt=0, allow_inf_nan=False), AfterValidator(_positive_cents)]
NonNegativeMoney = Annotated[float, Field(ge=0, allow_inf_nan=False), AfterValidator(_round_cents)]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
Description = Annotated[str, StringConstraints(max_length=255)]
