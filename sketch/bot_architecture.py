"""Design sketch for a cleaner Polymarket bot architecture.

This file is intentionally illustrative, not wired into the running bot.
It shows the class layout and flow I would use for a new bot.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from enum import Enum
import asyncio


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
        self.paper_trading: bool = True
        self.poll_interval_seconds: float = 1.0
        self.max_markets_per_subscription: int = 200
        self.max_open_positions: int = 25
        self.max_total_exposure: float = 1000.0
        self.max_position_size: float = 100.0
        self.stop_loss_pct: float = 10.0
        self.api_key: Optional[str] = None
        self.private_key: Optional[str] = None


class PolymarketClient:
    """Thin exchange client: public + authenticated API wrappers."""

    def __init__(self, api_key: Optional[str], private_key: Optional[str]):
        self.api_key = api_key
        self.private_key = private_key

    async def get_markets(self, active: bool = True, limit: int = 200) -> List[Dict[str, Any]]:
        raise NotImplementedError

    async def get_orderbook(self, market_id: str, outcome: str) -> Dict[str, Any]:
        raise NotImplementedError

    async def get_positions(self) -> List[Position]:
        raise NotImplementedError

    async def get_open_orders(self) -> List[OrderRecord]:
        raise NotImplementedError

    async def place_order(self, order: OrderIntent) -> OrderRecord:
        raise NotImplementedError

    async def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError

    async def get_balance(self) -> Dict[str, float]:
        raise NotImplementedError


class MarketWebSocket:
    """Handles market data ingestion only; no strategy decisions."""

    def __init__(self, client: PolymarketClient):
        self.client = client
        self.queue: asyncio.Queue = asyncio.Queue()

    async def start(self) -> None:
        raise NotImplementedError

    async def subscribe(self, token_ids: List[str]) -> None:
        raise NotImplementedError

    async def run(self) -> None:
        raise NotImplementedError


class TradingState:
    """Single owner of all mutable shared trading state."""

    def __init__(self):
        self.markets: Dict[str, MarketInfo] = {}
        self.orderbooks: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, Position] = {}
        self.open_orders: Dict[str, OrderRecord] = {}
        self.balance: Dict[str, float] = {"USDC": 0.0}
        self.lock = asyncio.Lock()

    async def update_market_snapshot(self, market: MarketInfo) -> None:
        raise NotImplementedError

    async def update_orderbook(self, market_id: str, orderbook: Dict[str, Any]) -> None:
        raise NotImplementedError

    async def reconcile(self, positions: List[Position], orders: List[OrderRecord]) -> None:
        raise NotImplementedError

    async def snapshot(self) -> Dict[str, Any]:
        raise NotImplementedError


class RiskManager:
    """Checks exposure, position size, and drawdown only."""

    def __init__(self, config: TradingConfig):
        self.config = config

    def check_trade_allowed(self, position: Position, order: OrderIntent) -> bool:
        raise NotImplementedError

    def check_open_exposure(self, state: TradingState) -> bool:
        raise NotImplementedError

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        raise NotImplementedError


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


class MarketSelector:
    """Builds the subscription universe from market discovery."""

    def __init__(self, client: PolymarketClient):
        self.client = client

    async def get_subscription_candidates(self) -> List[MarketInfo]:
        raise NotImplementedError

    async def get_token_ids(self) -> List[str]:
        raise NotImplementedError


class Strategy:
    """Base class for all trading strategies."""

    def __init__(self, name: str, state: TradingState, risk: RiskManager, coordinator: OrderCoordinator):
        self.name = name
        self.state = state
        self.risk = risk
        self.coordinator = coordinator

    async def on_snapshot(self, snapshot: Dict[str, Any]) -> List[OrderIntent]:
        raise NotImplementedError


class MarketMakingStrategy(Strategy):
    async def on_snapshot(self, snapshot: Dict[str, Any]) -> List[OrderIntent]:
        raise NotImplementedError


class MicroSpreadStrategy(Strategy):
    async def on_snapshot(self, snapshot: Dict[str, Any]) -> List[OrderIntent]:
        raise NotImplementedError


class SingleArbStrategy(Strategy):
    async def on_snapshot(self, snapshot: Dict[str, Any]) -> List[OrderIntent]:
        raise NotImplementedError


class StrategyRunner:
    """Runs strategy evaluation on snapshots and sends intents to coordinator."""

    def __init__(self, strategies: List[Strategy]):
        self.strategies = strategies

    async def run_once(self, snapshot: Dict[str, Any]) -> None:
        raise NotImplementedError


class PaperTradingEngine:
    """Simulates fills, P&L, and positions for testing without live trading."""

    def __init__(self, state: TradingState):
        self.state = state

    async def simulate_fill(self, order: OrderIntent, market: MarketInfo) -> Position:
        raise NotImplementedError

    async def update_pnl(self) -> None:
        raise NotImplementedError


class Bot:
    """Top-level orchestrator: wires everything together."""

    def __init__(
        self,
        config: TradingConfig,
        client: PolymarketClient,
        ws: MarketWebSocket,
        state: TradingState,
        risk: RiskManager,
        selector: MarketSelector,
        coordinator: OrderCoordinator,
        strategies: List[Strategy],
    ):
        self.config = config
        self.client = client
        self.ws = ws
        self.state = state
        self.risk = risk
        self.selector = selector
        self.coordinator = coordinator
        self.strategies = strategies

    async def start(self) -> None:
        raise NotImplementedError

    async def loop(self) -> None:
        raise NotImplementedError

    async def shutdown(self) -> None:
        raise NotImplementedError


# Example startup flow:
#
# bot = Bot(
#     config=TradingConfig(),
#     client=PolymarketClient(...),
#     ws=MarketWebSocket(...),
#     state=TradingState(),
#     risk=RiskManager(...),
#     selector=MarketSelector(...),
#     coordinator=OrderCoordinator(...),
#     strategies=[
#         MarketMakingStrategy(...),
#         MicroSpreadStrategy(...),
#         SingleArbStrategy(...),
#     ],
# )
# asyncio.run(bot.start())
