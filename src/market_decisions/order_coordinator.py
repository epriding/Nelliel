from  ..api.interfaces.base_interfaces import RestClient
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

    def __init__(self, client: RestClient, risk: RiskManager, state: TradingState, paper_engine: PaperTradingEngine):
        self.client = client
        self.risk = risk
        self.state = state
        self.paper_engine = paper_engine
        self.lock = asyncio.Lock()

    async def submit(self, order: OrderIntent) -> Optional[OrderRecord]:
        async with self.lock:

            if not self.risk.check_trade_allowed(order=order):

                if self.state.paper_trading[order.strategy]:
                    market = self.state.markets[f"{order.exchange}:{order.market_id}"]
                    record = await self.paper_engine.simulate_fill(order, market)
                else:
                    #need the polymarket us adapter for the api
                    pass

                if record.status == "FILLED":
                    await self._apply_fill(record)

                await self.state.update_open_order(record)
                return record

    def _merge_position(self, existing: Optional[Position], order: OrderRecord) -> Optional[Position]:
        """Returns the new/updated Position, or None if the fill fully closes it."""
        if existing is None:
            return Position(
                market_id=order.market_id,
                exchange=order.exchange,
                outcome=order.outcome,
                size=order.size,
                entry_price=order.price,
                side=order.side,
                strategy=order.strategy,
            )
        elif existing.side == order.side:
            total_size = existing.size + order.size
            avg_price = ((existing.entry_price * existing.size) + (order.price * order.size)) / total_size
            existing.size = total_size
            existing.entry_price = avg_price
            return existing
        else:
            if order.size < existing.size:
                existing.size -= order.size
                return existing
            elif order.size == existing.size:
                return None
            else:
                raise NotImplementedError("Position flip not handled yet")


    async def _apply_fill(self, order: OrderRecord) -> None:
        key = self.state._position_key(order.market_id, order.outcome, order.exchange, order.strategy)

        result = self._merge_position(self.state.positions.get(key), order)
        if result is None:
            await self.state.remove_position(order.market_id, order.outcome, order.exchange, order.strategy)
        else:
            await self.state.update_position(result)

        strategy_key = f"{order.exchange}:{order.market_id}:{order.outcome}"
        strategy_existing = self.state.strategy_positions.get(order.strategy, {}).get(strategy_key)
        strategy_result = self._merge_position(strategy_existing, order)

        if strategy_result is None:
            await self.state.remove_strategy_position(order.strategy, order.market_id, order.outcome, order.exchange)
        else:
            await self.state.update_strategy_position(strategy_result)

    async def cancel(self, order_id: str) -> None:
        raise NotImplementedError

    async def reconcile(self) -> None:
        async with self.lock:
            live_positions = await self.client.get_positions()
            live_orders = await self.client.get_open_orders()
            live_orders_by_keys = {f"{o.exchange}:{o.order_id}": o for o in live_orders}

            stale_orders = {}
            for k, o in self.state.open_orders.items():
                if self.state.paper_trading.get(o.strategy, False):
                    continue
                live_o = live_orders_by_keys.get(k)
                if live_o is None or abs(o.size - live_o.size) > 1e-9:
                    stale_orders[k] = o

            for p in live_positions:
                strategy_key = f"{p.exchange}:{p.market_id}:{p.outcome}"
                local_key = f"LIVE:{p.exchange}:{p.market_id}:{p.outcome}"
                existing = self.state.positions.get(local_key)
                difference = p.size - (existing.size if existing else 0.0)

                if abs(difference) < 1e-9:
                    continue  # already position size is in sync

                match_key = None
                for order_key, o in stale_orders.items():
                    if f"{o.exchange}:{o.market_id}:{o.outcome}" != strategy_key:
                        continue
                    if abs(o.size - difference) < 1e-6:
                        match_key = order_key
                        break
                    if difference < o.size and match_key is None:
                        match_key = order_key

                if match_key is None:
                    #genuine order orphan
                    continue  # genuine orphan (or difference > o.size)

                o = stale_orders.pop(match_key)
                filled_size = min(difference, o.size)
                remaining = o.size - filled_size

                await self._apply_fill(OrderRecord(
                    order_id=o.order_id, market_id=o.market_id, exchange=o.exchange,
                    outcome=o.outcome, side=o.side, size=filled_size, price=o.price,
                    status="FILLED", strategy=o.strategy, tif=o.tif
                ))

                if remaining < 1e-6:
                    await self.state.remove_open_order(o.order_id, o.exchange)
                else:
                    await self.state.update_open_order(OrderRecord(
                        order_id=o.order_id, market_id=o.market_id, exchange=o.exchange,
                        outcome=o.outcome, side=o.side, size=remaining, price=o.price,
                        status="PARTIALLY_FILLED", strategy=o.strategy, tif=o.tif
                    ))

            await self.state.reconcile(live_positions, live_orders)