from dataclasses import dataclass, field
from ..utilities.trading_state import TradingState
from ..utilities.classes import OrderIntent, MarketInfo, Position

class PaperTradingEngine:
    """Simulates fills, P&L, and positions for testing without live trading."""

    def __init__(self, state: TradingState):
        self.state = state

    async def simulate_fill(self, order: OrderIntent, market: MarketInfo) -> Position:
        raise NotImplementedError

    async def update_pnl(self) -> None:
        raise NotImplementedError