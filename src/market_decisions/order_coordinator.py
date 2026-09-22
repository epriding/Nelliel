from ..api.interfaces.polymarket_US import PolyUsClient
from ..market_decisions.risk_manager import RiskManager
from ..utilities.trading_state import TradingState
from ..utilities.classes import OrderIntent, OrderRecord, Position
from ..paper_trading.paper_trading_engine import PaperTradingEngine
from ..utilities.logger import setup_logger
from typing import Optional
import asyncio

logger = setup_logger(__name__)

class OrderCoordinator:
    """Serializes all order actions and maintains local correctness."""

    def __init__(self, client: PolyUsClient, risk: RiskManager, state: TradingState, paper_engine: PaperTradingEngine):
        self.client = client
        self.risk = risk
        self.state = state
        self.paper_engine = paper_engine
        self.lock = asyncio.Lock()

    async def submit(self, order: OrderIntent) -> Optional[OrderRecord]:
        async with self.lock:

            if not self.risk.check_trade_allowed(order=order):

                if self.state.paper_trading[order.strategy]:
                    market = self.state.markets[order.market_id]
                    record = await self.paper_engine.simulate_fill(order, market)
                else:
                    #need the polymarket us adapter for the api
                    pass

                if record.status == "FILLED":
                    await self._apply_fill(record)

                await self.state.update_open_order(record)
                return record

    async def _apply_fill(self, order: OrderRecord) -> None:
        key = f"{order.market_id}:{order.outcome}"
        existing = self.state.positions.get(key)

        if existing is None:
            new_position = Position(
                market_id=order.market_id,
                outcome=order.outcome,
                size=order.size,
                entry_price=order.price,
                side=order.side,
                strategy=order.strategy,
            )
            await self.state.update_position(new_position)

        elif existing.side == order.side:
            # same-side add: weighted-average entry price
            total_size = existing.size + order.size
            avg_price = ((existing.entry_price * existing.size) + (order.price * order.size)) / total_size
            existing.size = total_size
            existing.entry_price = avg_price
            await self.state.update_position(existing)

        else:
            # opposite side: reduce or close
            if order.size < existing.size:
                existing.size -= order.size
                await self.state.update_position(existing)
            elif order.size == existing.size:
                await self.state.remove_position(order.market_id, order.outcome)
            else:
                # order.size > existing.size — flips direction, unresolved, see note below
                raise NotImplementedError("Position flip not handled yet")
                
    async def cancel(self, order_id: str) -> None:
        raise NotImplementedError

    async def reconcile(self) -> None:
        raise NotImplementedError