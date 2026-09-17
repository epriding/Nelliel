from ..api.polymarket.polyUS_client import PolymarketClient
from ..market_decisions.risk_manager import RiskManager
from ..utilities.trading_state import TradingState
from ..utilities.classes import OrderIntent, OrderRecord
from typing import Optional
import asyncio

class OrderCoordinator:
    """Serializes all order actions and maintains local correctness."""

    def __init__(self, client: PolymarketClient, risk: RiskManager, state: TradingState):
        self.client = client
        self.risk = risk
        self.state = state
        self.lock = asyncio.Lock()

    async def submit(self, order: OrderIntent) -> Optional[OrderRecord]:
        raise NotImplementedError

    async def cancel(self, order_id: str) -> None:
        raise NotImplementedError

    async def reconcile(self) -> None:
        raise NotImplementedError