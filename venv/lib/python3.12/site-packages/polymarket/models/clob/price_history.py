from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, TypeAlias

from pydantic import Field

from polymarket.models.base import BaseModel

PriceHistoryInterval: TypeAlias = Literal["max", "1w", "1d", "6h", "1h"]


class PriceHistoryPoint(BaseModel):
    t: int = Field(strict=True)
    p: float = Field(strict=True)

    def _repr_html_(self) -> str:
        from polymarket._jupyter import card, safe_html_repr

        @safe_html_repr
        def render(self: PriceHistoryPoint) -> str:
            ts = datetime.fromtimestamp(self.t, tz=UTC).isoformat()
            return card("PriceHistoryPoint", rows=[("t", ts), ("p", str(self.p))])

        return render(self)


__all__ = ["PriceHistoryInterval", "PriceHistoryPoint"]
