# Bot Architecture Sketch

This folder contains a conceptual blueprint for a cleaner Polymarket trading bot.

## Core idea

Keep the system layered and single-owner:

- Market data layer
- State layer
- Risk layer
- Order execution layer
- Strategy layer
- Bot orchestration layer

## Important design goals

1. One owner of shared mutable state
2. Async network I/O only
3. No direct strategy writes to exchange state
4. Serialized order submission
5. Proper paper trading simulation
6. Reconciliation on startup and periodically

## Files

- `bot_architecture.py` — class sketch with responsibilities and flow

## Summary flow

```text
MarketWebSocket -> TradingState -> StrategyRunner -> OrderIntent -> OrderCoordinator -> PolymarketClient
```

The order coordinator is the only component allowed to validate risk and submit orders.
