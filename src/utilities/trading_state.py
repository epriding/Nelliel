from __future__ import annotations
from typing import Dict, Any, List, TYPE_CHECKING
import asyncio
from .classes import Position, OrderRecord, MarketInfo, Snapshot, OrderBook
import time

if TYPE_CHECKING:
    # only needed for type hints — avoids the runtime circular import with risk_manager.py
    from ..market_decisions.risk_manager import RiskManager



class TradingState:
    """Single owner of all mutable shared trading state."""

    def __init__(self, risk_manager: RiskManager):
        self.markets: Dict[str, MarketInfo] = {}
        self.orderbooks: Dict[str, OrderBook] = {}
        self.positions: Dict[str, Position] = {}
        self.strategy_positions: Dict[str, Dict[str, Position]] = {}  # strategy -> {key: Position}
        self.open_orders: Dict[str, OrderRecord] = {}
        self.balance: Dict[str, float] = {"USDC": 0.0}
        self.risk_manager: RiskManager = risk_manager
        self.paper_trading: Dict[str, bool] = risk_manager.config.paper_trading
        self.lock = asyncio.Lock()

    def _position_key(self, market_id: str, outcome: str, exchange: str, strategy: str) -> str:
        mode = "PAPER" if self.paper_trading.get(strategy, False) else "LIVE"
        return f"{mode}:{exchange}:{market_id}:{outcome}"

    async def update_position(self, position: Position) -> None:
        """Adds or overwrites a single position. Key encodes paper/live mode
        so paper and live fills for the same market never merge."""
        async with self.lock:
            key = self._position_key(position.market_id, position.outcome, position.exchange, position.strategy)
            self.positions[key] = position

    async def remove_position(self, market_id: str, outcome: str, exchange: str, strategy: str) -> None:
        """Removes a position, e.g. when fully closed. Needs strategy now to
        know whether to remove the paper or live key."""
        async with self.lock:
            key = self._position_key(market_id, outcome, exchange, strategy)
            self.positions.pop(key, None)
   
    async def update_trading_state(self, market: MarketInfo) -> None:
        async with self.lock:
           self.markets[f'{market.exchange}:{market.market_id}'] = market

    async def update_orderbook(self, orderbook: OrderBook) -> None:
        async with self.lock:
            self.orderbooks[f"{orderbook.exchange}:{orderbook.market_id}:{orderbook.outcome}"] = orderbook

    async def update_open_order(self, order: OrderRecord) -> None:
        """Adds or overwrites a single open order."""
        async with self.lock:
            self.open_orders[f"{order.exchange}:{order.order_id}"] = order

    async def remove_open_order(self, order_id: str, exchange: str) -> None:
        """Removes an order, e.g. once filled or cancelled."""
        async with self.lock:
            key = f"{exchange}:{order_id}"
            self.open_orders.pop(key, None)

    async def reconcile(self, positions: List[Position], orders: List[OrderRecord]) -> None:
        async with self.lock:
            paper_positions = {
                k: v for k, v in self.positions.items() if k.startswith("PAPER:")
            }

            live_positions = {}
            for p in positions:
                key = f"LIVE:{p.exchange}:{p.market_id}:{p.outcome}"
                strategy_key = f"{p.exchange}:{p.market_id}:{p.outcome}"
                existing = self.positions.get(key)

                if existing is not None:
                    p.strategy = existing.strategy
                else:
                    pass
                    # orphan position, log critical

                strategies_size = sum(
                    positions_by_key[strategy_key].size
                    for strategy, positions_by_key in self.strategy_positions.items()
                    if not self.paper_trading.get(strategy, False) and strategy_key in positions_by_key
                )
                if abs(strategies_size - p.size) > 1e-9:
                    pass
                    # log warning: drift for {strategy_key}

                live_positions[key] = p

            self.positions = {**paper_positions, **live_positions}

            # --- orders ---
            paper_orders = {
                k: v for k, v in self.open_orders.items()
                if self.paper_trading.get(v.strategy, False)
            }

            live_orders = {}
            for o in orders:
                key = f"{o.exchange}:{o.order_id}"
                existing = self.open_orders.get(key)

                if existing is not None:
                    o.strategy = existing.strategy  # carry over local attribution
                else:
                    pass
                    # order exists on exchange but not locally tracked
                    # log warning: untracked order found — placed outside this bot? crashed before local write?

                live_orders[key] = o

            self.open_orders = {**paper_orders, **live_orders}

    async def get_cached_orderbook(self, market_id: str, outcome: str, exchange: str) -> OrderBook:
        async with self.lock:
            key = f"{exchange}:{market_id}:{outcome}"
            orderbook = self.orderbooks.get(key)

            if orderbook is None:
                raise KeyError(f"No orderbook cached for {key}")

            return orderbook

    async def snapshot(self) -> Snapshot:
        current_snapshot = Snapshot(
            timestamp=time.time(),
            markets=self.markets,
            orderbooks=self.orderbooks,
            positions=self.positions,
            open_orders=self.open_orders,
            balance=self.balance,
            exposure=self.risk_manager.get_exposure(self)

        )

        return current_snapshot