"""Built-in Arrow overrides registered on ``polymarket.frames`` import."""

from __future__ import annotations

from typing import TYPE_CHECKING

from polymarket.frames._overrides import register_override
from polymarket.models import OrderBook

if TYPE_CHECKING:
    import pyarrow as pa


@register_override(OrderBook)
def _orderbook_to_arrow(value: object) -> pa.Table:  # pyright: ignore[reportUnusedFunction]
    # Single book -> [side, level, price, size]. Sequence of books ->
    # [market, token_id, timestamp, hash, side, level, price, size] so
    # rows stay attributable across instruments AND snapshots of the same
    # instrument over time.
    from polymarket.frames._arrow import _build_table_from_rows

    if isinstance(value, OrderBook):
        return _build_table_from_rows(_orderbook_rows(value))

    assert isinstance(value, (list, tuple))
    rows: list[dict[str, object]] = []
    for book in value:
        assert isinstance(book, OrderBook)
        identity = {
            "market": book.market,
            "token_id": book.token_id,
            "timestamp": book.timestamp,
            "hash": book.hash,
        }
        for r in _orderbook_rows(book):
            rows.append({**identity, **r})
    return _build_table_from_rows(rows)


def _orderbook_rows(book: OrderBook) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for level_idx, lvl in enumerate(book.bids):
        rows.append({"side": "bid", "level": level_idx, "price": lvl.price, "size": lvl.size})
    for level_idx, lvl in enumerate(book.asks):
        rows.append({"side": "ask", "level": level_idx, "price": lvl.price, "size": lvl.size})
    return rows
