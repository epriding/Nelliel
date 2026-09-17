from __future__ import annotations

from typing import NamedTuple

from polymarket.models.types import OrderSide


class PriceRequest(NamedTuple):
    token_id: str
    side: OrderSide


__all__ = ["PriceRequest"]
