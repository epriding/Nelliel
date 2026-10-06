# Dict Data Structures (no dedicated class)

Dicts whose shape is only defined by convention. Values that are dataclasses (`Position`, `OrderRecord`, etc.) are named but not expanded.

Legend: **key** -> **value**. `mode` is `paper` or `live`. `exchange` is e.g. `polymarket_us`.

---

## 1. `TradingState` (src/utilities/trading_state.py)

| Attribute | Type | Key format | Value |
|---|---|---|---|
| `markets` | `Dict[str, MarketInfo]` | `exchange:market_id` | `MarketInfo` |
| `orderbooks` | `Dict[str, OrderBook]` | `exchange:market_id:outcome` | `OrderBook` |
| `positions` | `Dict[str, Position]` | `mode:exchange:market_id:outcome` | `Position` (net aggregate, paper and live never share a key) |
| `strategy_positions` | `Dict[str, Dict[str, Position]]` | outer: `strategy`; inner: `exchange:market_id:outcome` | `Position` (that strategy's own contribution; no mode prefix, a strategy is always paper or always live) |
| `open_orders` | `Dict[str, OrderRecord]` | `exchange:order_id` | `OrderRecord` |
| `balance` | `Dict[str, float]` | currency, e.g. `"USDC"` | amount |
| `paper_trading` | `Dict[str, bool]` | `strategy` name | `True` = paper. Same object as `TradingConfig.paper_trading` (shared reference, not a copy). Missing strategy -> use `.get(name, False)` |

Example:

```python
positions = {"live:polymarket_us:1234:YES": Position(...)}
strategy_positions = {"market_maker": {"polymarket_us:1234:YES": Position(...)}}
open_orders = {"polymarket_us:abc-123": OrderRecord(...)}
```

Notes:
- `positions` keys must always be built with `TradingState._position_key(market_id, outcome, exchange, strategy)`. `reconcile()` builds `live:` keys inline.
- `Snapshot` (classes.py) holds these same dicts. Its `orderbooks` comment says "market_id/outcome" but the real key is `exchange:market_id:outcome`.

---

## 2. Dicts inside dataclasses (classes.py)

| Field | Type | Key | Value |
|---|---|---|---|
| `MarketInfo.token_ids` | `Dict[str, str]` | outcome, uppercased (`"YES"`, `"NO"`) | token / market-side id |
| `MarketInfo.tradable` | `Dict[str, bool]` | outcome | tradable flag |
| `MarketInfo.prices` | `Dict[str, float]` | outcome | last price |
| `OrderBook.bids` / `.asks` | `Dict[float, float]` | price | size at that level |
| `BookSnapshotEvent.bids` / `.asks` | `Dict[float, float]` | price | size (full replace) |

`PriceChangeEvent` is not a dict: one level (`price`, `size`, `side`). `size == 0` removes the level.

---

## 3. `PolyUsClient` caches (polymarket_US.py)

| Attribute | Key | Value |
|---|---|---|
| `_slug_cache` | `market_id` | `slug` |
| `_market_id_cache` | `slug` | `market_id` |

Both are filled together in `_get_market_id`. `_get_slug` only fills `_slug_cache`.

---

## 4. `PolyUSWebsocket.subscriptions` (polyus_websocket.py)

The current type annotation is not valid typing. Intended shape from how it is used:

```python
subscriptions = {
    "market":  {request_type: {"subscription_type": str, "market_slugs": List[str]}},
    "private": {request_type: {"subscription_type": str, "market_slugs": List[str]}},
}
```

It starts as `{}`, so `self.subscriptions['market']` raises `KeyError` until something populates it.

---

## 5. Raw API responses (polyUS_api.py)

Shapes below are only what the existing code reads. Anything not listed is unknown.

**`PolymarketAPI.get_markets()` returns**
```python
{"markets": [<raw market>, ...], "offset": int}   # offset = next offset
```
`get_all_markets()` returns `{"markets": [...]}`.

**Raw market** (fields read in `PolyUsClient.get_markets`)
```python
{
  "id": str, "slug": str, "active": bool, "volume": ...,
  "marketSides": [
      {"description": str, "id": str, "tradable": bool, "price": ...},   # index 0 and 1
      {...},
  ],
}
```

**Raw order book** (`get_orderbook`, `_invert_book`, `_to_orderbook`)
```python
{"bids":   [{"px": {"value": ..., "currency": str}, "qty": ...}, ...],
 "offers": [{"px": {"value": ..., "currency": str}, "qty": ...}, ...]}
```
- `get_orderbook(slug, outcome)` returns the YES book for `"YES"`, an inverted book for `"NO"`, and `{"YES": ..., "NO": ...}` if `outcome` is None.
- Type of `px.value` is unverified: `_to_orderbook` casts with `float()`, but `_invert_book` does `1.0 - value` with no cast.

**Raw positions** (`_to_position`)
```python
{"positions": {
    <slug>: {"netPositionDecimal": str, "qtyBoughtDecimal": str, "cost": str/int, ...}
}}
```
Sign of `netPositionDecimal`: positive = YES, negative = NO. Entry price = `cost / 1_000_000 / qtyBoughtDecimal`.

**Raw open orders** (`get_orders()` -> `client.orders.list()`): shape not confirmed anywhere in the repo. See the `get_open_orders` assumptions.

---

## 6. Request payload dicts (polyUS_api.py)

| Method | Payload keys |
|---|---|
| `create_order` (limit) | `slug, intent, type, price, quantity, tif` |
| `create_order` (non-limit) | `slug, intent, type, quantity, tif, slippageTolerance: {currentPrice: {value, currency}, ticks}` |
| `cancel_order` | `{"marketSlug": slug}` (order id passed separately) |
| `cancel_all_orders` | `{"marketSlug": slug}` or none |
| `get_preview` | `slug, intent, type, price: {value, currency}, quantity` |
| `close_position` | `marketSlug` and optional `slippageTolerance` (same shape as above) |
| `get_activities` | `limit, cursor, types, marketSlug, sortOrder` |

Known issues: `create_order` references an undefined `logger`. `get_activities` builds `params` with a comprehension that filters nothing, so `None` values are sent.

---

