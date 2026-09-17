from ..utilities.trading_state import TradingState
from ..utilities.classes import OrderIntent
from typing import Dict, Any, List
from ..market_decisions.risk_manager import RiskManager
from ..market_decisions.order_coordinator import OrderCoordinator

class Strategy:
    """Base class for all trading strategies."""

    def __init__(self, name: str, state: TradingState, risk: RiskManager, coordinator: OrderCoordinator):
        self.name = name
        self.state = state
        self.risk = risk
        self.coordinator = coordinator

    async def on_snapshot(self, snapshot: Dict[str, Any]) -> List[OrderIntent]:
        raise NotImplementedError