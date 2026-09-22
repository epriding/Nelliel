from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

@dataclass(frozen=True)
class MarketDataEvent:
    """Common fields every event carries."""
    market_id: str
    outcome: str
    timestamp: float


@dataclass(frozen=True)
class BookSnapshotEvent(MarketDataEvent):
    """Full orderbook replace."""
    bids: Dict[float, float]   # price -> size
    asks: Dict[float, float]


@dataclass(frozen=True)
class PriceChangeEvent(MarketDataEvent):
    """Incremental update — merge into existing book, don't replace."""
    price: float
    size: float
    side: str  # "BID" or "ASK"

class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

#consider making this more descriptive by adding more values example: subject, volume24hr, volume1hr, etc.
@dataclass
class MarketInfo:
    market_id: str
    slug: str
    token_ids: Dict[str, str]
    active: bool
    tradable: Dict[str, bool]
    volume: float = 0.0
    prices: Dict[str, float] = field(default_factory=dict)


@dataclass
class OrderIntent:
    market_id: str
    side: Side
    outcome: str
    size: float
    price: float
    strategy: str
    reason: str = ""


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


@dataclass
class Position:
    market_id: str
    outcome: str
    size: float
    entry_price: float
    side: Side
    strategy: str

class TradingConfig:
    def __init__(self):
        #consider adding a strategies dict where we list the strateigies we want and specific details about them
        self.paper_trading: Dict[str, bool] = {}
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