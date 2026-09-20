from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class MarketInfo:
    market_id: str
    slug: str
    token_ids: Dict[str, str]
    active: bool
    tradable: bool
    volume: float = 0.0
    price_yes: Optional[float] = None
    price_no: Optional[float] = None


@dataclass
class OrderIntent:
    market_id: str
    side: Side
    outcome: str
    size: float
    price: float
    strategy: str
    reason: str = ""
    paper_trading: bool = True


@dataclass
class OrderRecord:
    order_id: str
    market_id: str
    outcome: str
    side: Side
    size: float
    price: float
    status: str = "PENDING"
    strategy: str = ""

#might need to turn this to regular class so it can update its price automatically
@dataclass
class Position:
    market_id: str
    outcome: str
    size: float
    entry_price: float
    side: Side
    strategy: str
    #consider adding a current price to the dataclass, would need to somehow update price real time

class TradingConfig:
    def __init__(self):
        self.paper_trading: bool = True
        self.poll_interval_seconds: float = 1.0
        self.max_markets_per_subscription: int = 200
        self.max_open_positions: int = 25
        self.max_total_exposure: float = 1000.0
        self.max_position_size: float = 100.0
        self.stop_loss_pct: float = 10.0
        self.api_key: Optional[str] = None
        self.private_key: Optional[str] = None


@dataclass(frozen=True)
class Snapshot:
    timestamp: float
    markets: Dict[str, MarketInfo]              # from state.markets
    orderbooks: Dict[str, Dict[str, Any]]        # from state.orderbooks, keyed by market_id/outcome
    positions: Dict[str, Position]               # from state.positions
    open_orders: Dict[str, OrderRecord]          # from state.open_orders
    balance: Dict[str, float]                    # from state.balance
    exposure: float                              # derived, see below