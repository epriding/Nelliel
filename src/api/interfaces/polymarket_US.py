from decimal import Decimal
from typing import Optional
from .base_interfaces import WebsocketClient, RestClient
from ..polymarket.polyUS_api import PolymarketAPI
from ..polymarket.polyus_websocket import PolyUSWebsocket
from typing import List, Dict
import asyncio
from datetime import datetime
from ...utilities.classes import (
    OrderIntent, OrderRecord, Position, MarketInfo, OrderBookSnapshotEvent,
    LiteOrderBookSnapshotEvent, TradeEvent, OrderSnapshotEvent,
    OrderUpdateEvent, PositionSnapshotEvent, PositionUpdateEvent, BalanceSnapshotEvent,
    BalanceUpdateEvent, RfqEvent, OrderBook, Side, OrderStatus, TimeInForce,
)
from ...utilities.logger import setup_logger
import time


logger = setup_logger(__name__)


class PolyUsClient(RestClient):
    def __init__(self, key_id: str, secret_key: str):
        self.polymarket_api: PolymarketAPI = PolymarketAPI(key_id=key_id, secret_key=secret_key)
        self._slug_cache: Dict[str, str] = {}
        self._market_id_cache: Dict[str, str] = {}
        self._INTENT_MAP = {
            "ORDER_INTENT_BUY_LONG":   ("YES", Side.BUY),
            "ORDER_INTENT_SELL_LONG":  ("YES", Side.SELL),
            "ORDER_INTENT_BUY_SHORT":  ("NO",  Side.BUY),
            "ORDER_INTENT_SELL_SHORT": ("NO",  Side.SELL),
        }
        self._REVERSE_INTENT_MAP = {
            ("YES", Side.BUY):  "ORDER_INTENT_BUY_LONG",
            ("YES", Side.SELL): "ORDER_INTENT_SELL_LONG",
            ("NO",  Side.BUY):  "ORDER_INTENT_BUY_SHORT",
            ("NO",  Side.SELL): "ORDER_INTENT_SELL_SHORT",
        }
        self._STATUS_MAP = {
            "ORDER_STATE_PENDING_NEW": OrderStatus.NEW,
            "ORDER_STATE_PENDING_REPLACE": OrderStatus.NEW,
            "ORDER_STATE_PENDING_CANCEL": OrderStatus.NEW,
            "ORDER_STATE_PENDING_RISK": OrderStatus.NEW,
            "ORDER_STATE_NEW": OrderStatus.NEW,
            "ORDER_STATE_PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "ORDER_STATE_FILLED": OrderStatus.FILLED,
            "ORDER_STATE_CANCELED": OrderStatus.CANCELED,
            "ORDER_STATE_REJECTED": OrderStatus.REJECTED,
            "ORDER_STATE_EXPIRED": OrderStatus.EXPIRED,
        }
        self._TIF_MAP = {
            "TIME_IN_FORCE_GOOD_TILL_CANCEL": TimeInForce.GTC,
            "TIME_IN_FORCE_GOOD_TILL_DATE": TimeInForce.GTD,
            "TIME_IN_FORCE_IMMEDIATE_OR_CANCEL": TimeInForce.IOC,
            "TIME_IN_FORCE_FILL_OR_KILL": TimeInForce.FOK,
        }

    async def get_markets(self, active: bool = True, limit: int = 100, offset: int = 0) -> List[MarketInfo]:
        response = await self.polymarket_api.get_markets(active=active, limit=limit, offset=offset)

        market_details = response['markets']

        markets = []

        for market in market_details:
            yes_side, no_side = market.marketSides
            market_info = MarketInfo(
                market_id=market.id,
                exchange="POLYMARKET_US",
                slug=market.slug,
                token_ids={
                    yes_side.description.upper(): yes_side.id,
                    no_side.description.upper(): no_side.id
                },
                active=market.active,
                tradable={
                    yes_side.description.upper(): yes_side.tradable,
                    no_side.description.upper(): no_side.tradable
                },
                volume=market.volume,
                prices={
                    yes_side.description.upper(): yes_side.price,
                    no_side.description.upper(): no_side.price
                },
            )
            markets.append(market_info)

        return markets

    async def _get_slug(self, market_id: str) -> str:
        slug = self._slug_cache.get(market_id, None)

        if slug is not None:
            return slug

        market = await self.polymarket_api.get_market(market_id=market_id)
        self._slug_cache[market_id] = market.slug

        return market.slug

    async def _get_market_id(self, slug: str) -> str:
        market_id = self._market_id_cache.get(slug)
        if market_id is not None:
            return market_id

        market = await self.polymarket_api.get_market_by_slug(slug=slug)
        market_id = market.id
        self._market_id_cache[slug] = market_id
        self._slug_cache[market_id] = slug  # populate the reverse cache too
        return market_id

    def _to_orderbook(self, raw: Dict, market_id: str, outcome: str) -> OrderBook:
        """Converts a raw Polymarket US book response into the canonical OrderBook."""
        bids = {float(level["px"]["value"]): float(level["qty"]) for level in raw.get("bids", [])}
        asks = {float(level["px"]["value"]): float(level["qty"]) for level in raw.get("offers", [])}

        return OrderBook(
            market_id=market_id,
            exchange="POLYMARKET_US",
            outcome=outcome,
            bids=bids,
            asks=asks,
            timestamp=time.time(),
        )

    async def _to_position(self, raw_positions: Dict, strategy: str = "") -> List[Position]:
        """Converts client.portfolio.positions() response into canonical Positions.
        Outcome derived from sign of netPositionDecimal: positive = YES, negative = NO.
        """
        positions = []

        for slug, raw in raw_positions.get("positions", {}).items():
            net = Decimal(raw.netPosition)
            if net == 0:
                continue

            outcome = "YES" if net > 0 else "NO"
            size = abs(net)

            qty_bought = Decimal(raw.qtyBoughtDecimal)
            cost = Decimal(raw.cost) / Decimal(1_000_000)
            entry_price = (cost / qty_bought) if qty_bought else Decimal(0)

            market_id = await self._get_market_id(slug)

            positions.append(Position(
                market_id=market_id,
                exchange="POLYMARKET_US",
                outcome=outcome,
                size=float(size),
                entry_price=float(entry_price),
                side=Side.BUY,
                strategy=strategy,
            ))

        return positions

    async def get_orderbook(self, market_id: str, outcome: str) -> OrderBook:
        slug = await self._get_slug(market_id=market_id)
        raw_orderbook = await self.polymarket_api.get_orderbook(slug=slug, outcome=outcome)
        orderbook = self._to_orderbook(raw=raw_orderbook, market_id=market_id, outcome=outcome)

        return orderbook

    async def get_positions(self) -> List[Position]:
        raw_positions = await self.polymarket_api.get_positions()
        positions = await self._to_position(raw_positions=raw_positions)

        return positions

    def _get_order_state(self, state: str) -> OrderStatus:
        status = self._STATUS_MAP.get(state)

        if status is None:
            #log error for unknown status
            return OrderStatus.UNKNOWN

        return status



    def _get_tif(self, tif: str) -> TimeInForce:
        try:
            time_in_force = self._TIF_MAP[tif]

            return time_in_force

        except KeyError:
            #Log error
            return TimeInForce.FOK  #returns default so entire order gets filled

    async def get_open_orders(self) -> List[OrderRecord]:
        raw = await self.polymarket_api.get_orders()
        orders = []

        for order in raw.get("orders", []):
            outcome, side = self._INTENT_MAP[order["intent"]]
            orders.append(OrderRecord(
                order_id=order.id,
                market_id=await self._get_market_id(slug=order.marketSlug),
                exchange="POLYMARKET_US",
                outcome=outcome,
                side=side,
                size=float(order.leavesQuantity),   # leavesQuantity is remaining orders left unfilled
                price=float(order.price.value),
                status=self._get_order_state(state=order.state),
                strategy="",                        # exchange doesn't know strategies but state.reconcile carries it over
                tif=self._get_tif(tif=order.tif)
            ))

        return orders

    async def place_order(self, order: OrderIntent) -> OrderRecord:
        response = await self.polymarket_api.create_order(
            slug=await self._get_slug(order.market_id),
            intent=self._REVERSE_INTENT_MAP[(order.outcome, order.side)],
            order_type=order.order_type,
            price=order.price,
            quantity=order.size,
            tif=order.tif,
            slippage=order.slippage,
            currency="USD" #add a strategy config change in future maybe
        )

        if 'error' in response:
            #log an error and return none
            return None

        payload = response.executions.order
        outcome, side = self._INTENT_MAP[payload.intent]
        size = payload.leavesQuantity if payload.leavesQuantity else payload.cumQuantity
        record = OrderRecord(
            order_id=payload.id,
            market_id=await self._get_market_id(slug=payload.marketSlug),
            exchange="POLYMARKET_US",
            outcome=outcome,
            side=side,
            size=float(size),
            price=float(payload.price.value),
            status=self._get_order_state(state=payload.state),
            strategy=order.strategy,
            tif=self._get_tif(tif=payload.tif)
        )

        return record

    async def cancel_order(self, order_id: str, market_id: str) -> None:
        slug = await self._get_slug(market_id=market_id)
        response = await self.polymarket_api.cancel_order(order_id=order_id, slug=slug)

        return

    async def get_balance(self) -> Dict[str, float]:
        response = await self.polymarket_api.get_balance()
        return {"USD": float(response.buyingPower)}


class PolyUsWebsocketClient(WebsocketClient):
    def __init__(self, key_id: Optional[str], secret_key: Optional[str]):
        self._market_id_by_slug: Dict[str, str] = {}
        self._INTENT_MAP = {
            "ORDER_INTENT_BUY_LONG": ("YES", Side.BUY),
            "ORDER_INTENT_SELL_LONG": ("YES", Side.SELL),
            "ORDER_INTENT_BUY_SHORT": ("NO", Side.BUY),
            "ORDER_INTENT_SELL_SHORT": ("NO", Side.SELL),
        }
        self.polymarket_api = PolymarketAPI(key_id=key_id, secret_key=secret_key)
        self.websocket = PolyUSWebsocket(
            key_id=key_id,
            secret_key=secret_key,
            handlers={
                "market_data": self._handle_market_data,
                "market_data_lite": self._handle_market_data_lite,
                "trade": self._handle_trade,
                "order_snapshot": self._handle_order_snapshot,
                "order_update": self._handle_order_update,
                "position_snapshot": self._handle_position_snapshot,
                "position_update": self._handle_position_update,
                "account_balance_snapshot": self._handle_account_balance_snapshot,
                "account_balance_update": self._handle_account_balance_update,
                "rfq_event": self._handle_rfq_event,
            },
        )
        self.queue: asyncio.Queue = asyncio.Queue()

    @staticmethod
    def _amount(value) -> float:
        """Extract the numeric value from the SDK's Amount shape or a scalar."""
        if isinstance(value, dict):
            value = value.get("value", 0)
        return float(value or 0)

    @staticmethod
    def _timestamp(value) -> float:
        if not value:
            return time.time()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except (AttributeError, TypeError, ValueError):
            try:
                return float(value)
            except (TypeError, ValueError):
                return time.time()

    def _handle_market_data(self, message: Dict) -> None:
        """Convert a Polymarket US full-book message into YES and NO snapshots."""
        payload = message.get("marketData", {})
        slug = payload.get("marketSlug")
        market_id = self._market_id_by_slug.get(slug)
        if not market_id:
            return

        try:
            yes_bids = {
                self._amount(level.get("px")): self._amount(level.get("qty"))
                for level in payload.get("bids", [])
            }
            yes_asks = {
                self._amount(level.get("px")): self._amount(level.get("qty"))
                for level in payload.get("offers", [])
            }
            timestamp = self._timestamp(payload.get("transactTime"))

            self.queue.put_nowait(OrderBookSnapshotEvent(
                exchange="POLYMARKET_US", timestamp=timestamp,
                market_id=market_id, outcome="YES",
                bids=yes_bids, asks=yes_asks,
            ))
            # The US API publishes a YES-denominated book; derive the complementary NO book.
            no_bids = {1.0 - price: size for price, size in yes_asks.items()}
            no_asks = {1.0 - price: size for price, size in yes_bids.items()}
            self.queue.put_nowait(OrderBookSnapshotEvent(
                exchange="POLYMARKET_US", timestamp=timestamp,
                market_id=market_id, outcome="NO",
                bids=no_bids, asks=no_asks,
            ))
        except (AttributeError, TypeError, ValueError) as exc:
            logger.error("Invalid Polymarket US market data message: %s", exc)

    def _market_event_fields(self, payload: Dict, outcome: Optional[str] = None) -> Dict:
        slug = payload.get("marketSlug")
        return {
            "market_id": self._market_id_by_slug.get(slug, slug or ""),
            "outcome": outcome or "YES",
            "timestamp": self._timestamp(payload.get("transactTime") or payload.get("tradeTime")),
            "exchange": "POLYMARKET_US",
        }

    @staticmethod
    def _find_market_slug(value) -> Optional[str]:
        """Find marketSlug in nested SDK event payloads such as order executions."""
        if isinstance(value, dict):
            slug = value.get("marketSlug")
            if slug:
                return slug
            for nested_value in value.values():
                slug = PolyUsWebsocketClient._find_market_slug(nested_value)
                if slug:
                    return slug
        elif isinstance(value, list):
            for nested_value in value:
                slug = PolyUsWebsocketClient._find_market_slug(nested_value)
                if slug:
                    return slug
        return None

    def _handle_market_data_lite(self, message: Dict) -> None:
        payload = message.get("marketDataLite", {})
        try:
            self.queue.put_nowait(LiteOrderBookSnapshotEvent(
                **self._market_event_fields(payload),
                best_bid=self._amount(payload.get("bestBid")) if payload.get("bestBid") else None,
                best_ask=self._amount(payload.get("bestAsk")) if payload.get("bestAsk") else None,
                last_price=self._amount(payload.get("currentPx") or payload.get("lastTradePx"))
                if payload.get("currentPx") or payload.get("lastTradePx") else None,
            ))
        except (AttributeError, TypeError, ValueError) as exc:
            logger.error("Invalid Polymarket US lite market data message: %s", exc)

    def _handle_trade(self, message: Dict) -> None:
        payload = message.get("trade", {})
        maker = payload.get("maker", {})
        intent = maker.get("intent", "ORDER_INTENT_BUY_LONG")
        outcome = "NO" if intent.endswith("SHORT") else "YES"
        try:
            self.queue.put_nowait(TradeEvent(
                **self._market_event_fields(payload, outcome),
                trade_id=payload.get("tradeId"),
                price=self._amount(payload.get("price")),
                quantity=self._amount(payload.get("quantity")),
                side=Side.BUY if payload.get("taker", {}).get("side", "ORDER_SIDE_BUY").endswith("BUY") else Side.SELL,
            ))
        except (AttributeError, TypeError, ValueError) as exc:
            logger.error("Invalid Polymarket US trade message: %s", exc)

    def _to_order_record(self, raw: Dict) -> OrderRecord:
        outcome, side = self._INTENT_MAP.get(raw.get("intent"), ("YES", Side.BUY))
        price = raw.get("price", {})
        if isinstance(price, dict):
            price = price.get("value", 0)
        size = raw.get("leavesQuantity")
        if size is None:
            size = raw.get("quantity", raw.get("cumQuantity", 0))
        return OrderRecord(
            order_id=str(raw.get("id", "")), market_id=self._market_id_by_slug.get(raw.get("marketSlug"), raw.get("marketSlug", "")),
            exchange="POLYMARKET_US", outcome=outcome, side=side,
            size=self._amount(size), price=self._amount(price),
            status=self._websocket_order_status(raw.get("state", "")),
            tif=self._websocket_tif(raw.get("tif", "")),
        )

    @staticmethod
    def _websocket_order_status(state: str) -> OrderStatus:
        return {
            "ORDER_STATE_PENDING_NEW": OrderStatus.NEW,
            "ORDER_STATE_NEW": OrderStatus.NEW,
            "ORDER_STATE_PENDING_REPLACE": OrderStatus.NEW,
            "ORDER_STATE_PENDING_CANCEL": OrderStatus.NEW,
            "ORDER_STATE_PENDING_RISK": OrderStatus.NEW,
            "ORDER_STATE_PARTIALLY_FILLED": OrderStatus.PARTIALLY_FILLED,
            "ORDER_STATE_FILLED": OrderStatus.FILLED,
            "ORDER_STATE_CANCELED": OrderStatus.CANCELED,
            "ORDER_STATE_REPLACED": OrderStatus.CANCELED,
            "ORDER_STATE_REJECTED": OrderStatus.REJECTED,
            "ORDER_STATE_EXPIRED": OrderStatus.EXPIRED,
        }.get(state, OrderStatus.UNKNOWN)

    @staticmethod
    def _websocket_tif(tif: str) -> TimeInForce:
        return {
            "TIME_IN_FORCE_GOOD_TILL_CANCEL": TimeInForce.GTC,
            "TIME_IN_FORCE_GOOD_TILL_DATE": TimeInForce.GTD,
            "TIME_IN_FORCE_IMMEDIATE_OR_CANCEL": TimeInForce.IOC,
            "TIME_IN_FORCE_FILL_OR_KILL": TimeInForce.FOK,
        }.get(tif, TimeInForce.FOK)

    def _handle_order_snapshot(self, message: Dict) -> None:
        payload = message.get("orderSubscriptionSnapshot", {})
        self.queue.put_nowait(OrderSnapshotEvent(
            exchange="POLYMARKET_US", timestamp=time.time(),
            orders=[self._to_order_record(order) for order in payload.get("orders", [])],
            complete=payload.get("eof", False),
        ))

    def _handle_order_update(self, message: Dict) -> None:
        payload = message.get("orderSubscriptionUpdate", {})
        execution = payload.get("execution", {})
        raw_order = execution.get("order", {})
        order = self._to_order_record(raw_order) if raw_order else None
        fill = None
        if order is not None and execution.get("lastShares") is not None:
            fill_quantity = self._amount(execution.get("lastShares"))
            fill_price = self._amount(execution.get("lastPx"))
        else:
            fill_quantity = fill_price = None
        if order is None:
            return
        self.queue.put_nowait(OrderUpdateEvent(
            exchange="POLYMARKET_US", timestamp=time.time(),
            order=order, fill_quantity=fill_quantity, fill_price=fill_price,
        ))

    def _handle_position_snapshot(self, message: Dict) -> None:
        payload = message.get("positionSubscriptionSnapshot", {})
        raw_positions = payload.get("positions", [])
        if isinstance(raw_positions, dict):
            raw_positions = list(raw_positions.values())
        positions = [
            position for raw in raw_positions
            if (position := self._position_from_payload(raw)) is not None
        ]
        self.queue.put_nowait(PositionSnapshotEvent(
            exchange="POLYMARKET_US", timestamp=time.time(), positions=positions,
        ))

    def _handle_position_update(self, message: Dict) -> None:
        payload = message.get("positionSubscription", message.get("positionSubscriptionUpdate", {}))
        self._handle_position_payload(payload)

    def _handle_position_payload(self, payload: Dict) -> None:
        position = self._position_from_payload(payload)
        if position is None and not self._find_market_slug(payload):
            return
        self.queue.put_nowait(PositionUpdateEvent(
            exchange="POLYMARKET_US", timestamp=self._timestamp(payload.get("updateTime")),
            position=position, removed=position is None,
        ))

    def _position_from_payload(self, payload: Dict) -> Optional[Position]:
        after = payload.get("afterPosition", payload)
        slug = self._find_market_slug(payload)
        if not slug:
            return None
        market_id = self._market_id_by_slug.get(slug, slug)
        net = self._amount(after.get("netPositionDecimal", after.get("netPosition", 0)))
        if net == 0:
            return None
        outcome = "YES" if net > 0 else "NO"
        quantity_bought = self._amount(after.get("qtyBoughtDecimal", abs(net)))
        cost = self._amount(after.get("cost", {}).get("value", after.get("cost", 0)))
        return Position(
            market_id=market_id, exchange="POLYMARKET_US", outcome=outcome,
            size=abs(net), entry_price=cost / quantity_bought if quantity_bought else 0.0,
            side=Side.BUY, strategy="",
        )

    def _handle_account_balance_snapshot(self, message: Dict) -> None:
        payload = message.get("accountBalancesSnapshot", message.get("accountBalanceSubscriptionSnapshot", {}))
        balances = {}
        for item in payload.get("balances", []):
            currency = item.get("currency", "USD")
            balances[currency] = self._amount(item.get("buyingPower", item.get("currentBalance")))
        self.queue.put_nowait(BalanceSnapshotEvent(
            exchange="POLYMARKET_US", timestamp=time.time(), balances=balances
        ))

    def _handle_account_balance_update(self, message: Dict) -> None:
        payload = message.get("accountBalancesUpdate", message.get("accountBalanceSubscriptionUpdate", {}))
        change = payload.get("balanceChange", payload)
        after = change.get("afterBalance", {})
        currency = after.get("currency", "USD")
        self.queue.put_nowait(BalanceUpdateEvent(
            exchange="POLYMARKET_US", timestamp=self._timestamp(change.get("updateTime")),
            currency=currency,
            balance=self._amount(after.get("buyingPower", after.get("currentBalance", after.get("balance", 0)))),
        ))

    def _handle_rfq_event(self, message: Dict) -> None:
        envelope = message.get("rfqEvent", {})
        if not envelope:
            return
        event_type, payload = next(iter(envelope.items()))
        slug = self._find_market_slug(payload)
        raw_trade = payload.get("trade", {}) if event_type == "rfqTrade" else {}
        trade = None
        if raw_trade:
            trade = TradeEvent(
                exchange="POLYMARKET_US",
                timestamp=self._timestamp(raw_trade.get("executedTime")),
                market_id=self._market_id_by_slug.get(slug, raw_trade.get("symbol", "")),
                outcome="YES",
                trade_id=raw_trade.get("tradeId"),
                price=self._amount(raw_trade.get("price")),
                quantity=self._amount(raw_trade.get("qtyDecimal")),
                side=Side.BUY if raw_trade.get("aggressorSide", "SIDE_BUY").endswith("BUY") else Side.SELL,
            )
        self.queue.put_nowait(RfqEvent(
            exchange="POLYMARKET_US", timestamp=self._timestamp(
                payload.get("executedTime") or payload.get("updateTime")
            ), event_type=event_type, request_id=message.get("requestId"),
            market_id=self._market_id_by_slug.get(slug) if slug else None,
            trade=trade,
        ))

    async def start(self) -> None:
        await self.websocket.start()

    async def subscribe(self, market_ids: List[str]) -> None:
        for market_id in market_ids:
            cached_slug = next(
                (slug for slug, cached_id in self._market_id_by_slug.items() if cached_id == market_id),
                None,
            )
            if cached_slug is None:
                market = await self.polymarket_api.get_market(market_id)
                slug = market.slug
            else:
                slug = cached_slug
            self._market_id_by_slug[slug] = market_id
            await self.websocket.add_market_subscription(
                {"SUBSCRIPTION_TYPE_MARKET_DATA"}, slug
            )

    async def run(self) -> None:
        """Connect, listen, normalize events, push MarketEvent onto queue"""
        if not any(self.websocket._connected.values()):
            await self.start()
        await self.websocket.run()
