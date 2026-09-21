from ..utilities.classes import Position, OrderIntent, TradingConfig
from ..utilities.trading_state import TradingState


class RiskManager:
    """Checks exposure, position size, and drawdown currently."""

    def __init__(self, config: TradingConfig):
        self.config = config

    def check_trade_allowed(self, order: OrderIntent) -> bool:
        raise NotImplementedError

    def get_exposure(self, state: TradingState) -> float:
        """gets current expsoure from open orders and open positions"""
        exposure = 0

        if state.open_orders:
            for order in state.open_orders.values():
                increment = order.size * order.price
                exposure += increment

        if state.positions:
            for position in state.positions.values():
                increment = position.size * position.entry_price
                exposure += increment 

        return exposure


    def check_open_exposure(self, state: TradingState) -> bool:
        raise NotImplementedError

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        raise NotImplementedError