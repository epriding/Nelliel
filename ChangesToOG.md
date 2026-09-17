The main components are:

main.py: command-line entrypoint.
src/bot.py: central orchestrator.
adapter.py: unified exchange interface.
rest_client.py: REST requests and order operations.
polymarket_websocket.py: real-time order-book connection.
market_cache.py: shared market and price cache.
src/strategies/: trading algorithms.
risk_manager.py: exposure and trade checks.
order_coordinator.py: local order bookkeeping.
state_manager.py: JSON persistence.
The separate poly_botv1 repository is not used by this bot.

How It Runs
The normal command is:


The bot:

Loads config.yaml.
Creates a PolymarketAdapter.
The adapter creates:
A REST client, always.
A WebSocket client, if enabled.
Creates the risk manager, order coordinator, state manager, cache, and strategies.
Restores local positions and orders from bot_state.json.
Enters a loop, normally every five seconds.
Runs each enabled strategy sequentially:
Scan markets.
Find opportunities.
Check risk limits.
Place orders.
Checks stop losses.
Saves state on shutdown.
The current configuration defaults to:

Paper trading enabled.
Exchange adapter enabled.
WebSocket enabled.
Several strategies enabled.
Five-second polling interval.
The WebSocket is used primarily for market data. Orders still go through the REST client.

Main Architectural Flaws
1. Paper mode is not enforced safely
In main.py, --paper sets:


But with the adapter enabled, actual order placement checks:


Therefore, python main.py --paper may still leave the REST client in live mode if the configuration says otherwise.

This is the most serious safety flaw. The paper/live mode should be owned by one immutable configuration object or explicitly propagated to every execution client.

2. The REST order-book fallback appears to use the wrong identifier
The adapter calls the REST client with a market ID:


But rest_client.py documents its parameter as a token ID and sends it as token_id.

That means:

WebSocket-cached books may work.
REST fallback may request the wrong asset.
The strategy may receive empty or invalid books without clearly failing.
Market IDs, condition IDs, and token IDs need separate types or clearly named parameters.

3. WebSocket order books become stale
polymarket_websocket.py receives incremental price_change events but currently only logs them. It does not merge those changes into the cached book.

As a result, the bot can trade on an old full snapshot. The cache also lacks a strict freshness check before returning data.

4. Stop loss does not actually close the exchange position
In src/bot.py, _check_stop_losses() calls:


That only closes the position in local memory. It does not submit a sell order to Polymarket.

So the bot can report a position as closed while the real exchange position remains open.

It also always requests the YES price, even when the position may be for another outcome.

5. Risk checks ignore pending orders
risk_manager.py calculates exposure from tracked positions only.

Pending orders are not reserved against the risk limits. Multiple strategies can place orders whose combined value exceeds the configured exposure while positions still appear empty.

Risk should calculate:


6. Order coordination is only local bookkeeping
order_coordinator.py knows about locally created orders, but it is not the authoritative exchange state.

Problems include:

Reconciliation is not regularly called.
Direct REST cancellations do not necessarily update the coordinator.
Filled orders may remain locally pending.
A restart restores pending orders without verifying them against Polymarket.
This can cause duplicate prevention to block valid orders or allow incorrect assumptions about existing orders.

7. Position tracking is inconsistent between strategies
Some strategies add positions immediately after placing an order. Others track their own order dictionaries or arbitrage state.

That creates inconsistent behavior for:

Exposure calculations.
Stop losses.
P&L.
Restart recovery.
Duplicate prevention.
Every strategy should use one execution and position lifecycle rather than maintaining separate local interpretations.

8. All strategies run sequentially
The main loop runs strategies one after another:


If one strategy scans hundreds of markets or waits for a WebSocket subscription, every later strategy is delayed.

The five-second polling interval is also not a guaranteed interval. If an iteration takes eight seconds, the next iteration starts immediately after it finishes.

This is not really high-frequency trading architecture. It is a polling-based multi-strategy bot with optional streaming data.

9. Strategy failures are isolated, but execution consistency is weak
A failed strategy is logged and the next strategy runs. That is good for availability, but there is no transaction boundary around a multi-leg trade.

For example:

Buy first leg.
Second leg fails.
Bot is left with unwanted directional exposure.
Arbitrage and hedging strategies need explicit state machines for:


10. Client interfaces are inconsistent
There are three overlapping abstractions:

Legacy PolymarketClient.
PolymarketRESTClient.
PolymarketAdapter.
Their method signatures and return values are not fully consistent. For example, get_markets() may return either a list or a pagination dictionary depending on the path.

This forces callers such as MarketCache to inspect return types dynamically. A clean interface should guarantee one return shape.

11. State restoration trusts stale local data
state_manager.py restores positions and pending orders from JSON but does not immediately reconcile them with the exchange.

After a crash or network failure, the local state may disagree with:

Actual fills.
Cancelled orders.
Closed positions.
Orders placed by another process.
State restoration should be followed by a mandatory exchange reconciliation before trading resumes.

12. Secrets are stored in configuration
The current config.yaml contains a Telegram bot token. That token should be considered exposed and rotated.

Credentials should only come from environment variables or a secret manager. The configuration file should contain placeholders only.

Recommended Direction
For a new bot, I would keep the general shape but simplify and strengthen it:

Keep one ExchangeClient interface.
Make the REST client and WebSocket client implementation details.
Remove or quarantine the legacy PolymarketClient.
Make paper/live mode a single immutable runtime setting.
Use token IDs explicitly for order books.
Make WebSocket books incrementally update and expire when stale.
Treat pending orders as risk exposure.
Centralize all order placement, cancellation, fills, and position updates.
Reconcile with the exchange on startup and periodically.
Use strategy state machines for multi-leg trades.
Replace the sequential polling loop with event-driven strategy triggers where latency matters.
Remove secrets from config.yaml and rotate the exposed Telegram token.
The current repository is a useful prototype and strategy laboratory, but I would not trust it for live trading without fixing the paper-mode bug, identifier mismatch, stop-loss behavior, pending-order risk, and exchange reconciliation first.