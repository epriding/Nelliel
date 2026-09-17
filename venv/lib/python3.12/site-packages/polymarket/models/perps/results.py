"""Perps session result objects."""

from dataclasses import dataclass

from polymarket.models.perps.orders import PerpsOrder
from polymarket.models.perps.types import PerpsOrderId


@dataclass(frozen=True, slots=True, kw_only=True)
class PerpsPlacedTpSlOrder:
    """One placed take-profit or stop-loss trigger order."""

    order_id: PerpsOrderId
    """Identifier of the trigger order."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PerpsPlacedTpSlOrders:
    """Trigger orders placed alongside an order or position."""

    take_profit: PerpsPlacedTpSlOrder | None = None
    """The placed take-profit trigger, when requested."""
    stop_loss: PerpsPlacedTpSlOrder | None = None
    """The placed stop-loss trigger, when requested."""


@dataclass(frozen=True, slots=True, kw_only=True)
class PerpsOrderPlacement:
    """Result of placing one Perps order."""

    order: PerpsOrder
    """The placed order as first reported on the orders channel."""
    tp_sl: PerpsPlacedTpSlOrders | None = None
    """Trigger orders placed with the order, when requested."""


__all__ = [
    "PerpsOrderPlacement",
    "PerpsPlacedTpSlOrder",
    "PerpsPlacedTpSlOrders",
]
