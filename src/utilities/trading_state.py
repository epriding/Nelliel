from typing import Dict, Any, List
import asyncio
from classes import Position, OrderRecord, MarketInfo, Snapshot
from ..market_decisions.risk_manager import RiskManager
import time


class TradingState:
    """Single owner of all mutable shared trading state."""

    def __init__(self, risk_manager: RiskManager):
        self.markets: Dict[str, MarketInfo] = {}
        self.orderbooks: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, Position] = {}
        self.open_orders: Dict[str, OrderRecord] = {}
        self.balance: Dict[str, float] = {"USDC": 0.0}
        self.risk_manager: RiskManager = risk_manager
        self.lock = asyncio.Lock()

    async def update_trading_state(self, market: MarketInfo) -> None:
        async with self.lock:
           self.markets[market.market_id] = market

    async def update_orderbook(self, market_id: str, outcome: str, orderbook: Dict[str, Any]) -> None:
        async with self.lock:
            self.orderbooks[f"{market_id}:{outcome}"] = orderbook

    async def reconcile(self, positions: List[Position], orders: List[OrderRecord]) -> None:
        async with self.lock:
            self.positions = {f"{p.market_id}:{p.outcome}": p for p in positions}
            self.open_orders = {o.order_id: o for o in orders}

    async def snapshot(self) -> Snapshot:
        current_snapshot = Snapshot(
            time=time.time(),
            markets=self.markets,
            orderbooks=self.orderbooks,
            positions=self.positions,
            open_orders=self.open_orders,
            balance=self.balance,
            exposure=self.risk_manager.get_exposure(self)

        )

        return current_snapshot