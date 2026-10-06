from decimal import Decimal
from typing import Optional
from base_interfaces import WebsocketClient, RestClient
from ..polymarket.polyUS_api import PolymarketAPI
from ..polymarket.polyus_websocket import PolyUSWebsocket
from typing import List, Dict
import asyncio
from ...utilities.classes import OrderIntent, OrderRecord, Position, MarketInfo, BookSnapshotEvent, PriceChangeEvent, OrderBook, Side, OrderStatus, TimeInForce
import time


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
            market_info = MarketInfo(
                market_id=market['id'],
                slug=market['slug'],
                token_ids={
                    market['marketSides'][0]['description'].upper(): market['marketSides'][0]['id'],
                    market['marketSides'][1]['description'].upper(): market['marketSides'][1]['id']
                },
                active=market['active'],
                tradable={
                    market['marketSides'][0]['description'].upper(): market['marketSides'][0]['tradable'],
                    market['marketSides'][1]['description'].upper(): market['marketSides'][1]['tradable']
                },
                volume=market['volume'],
                prices={
                    market['marketSides'][0]['description'].upper(): market['marketSides'][0]['price'],
                    market['marketSides'][1]['description'].upper(): market['marketSides'][1]['price']
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
        market_id = market["id"]
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
            net = Decimal(raw["netPositionDecimal"])
            if net == 0:
                continue

            outcome = "YES" if net > 0 else "NO"
            size = abs(net)

            qty_bought = Decimal(raw["qtyBoughtDecimal"])
            cost = Decimal(raw["cost"]) / Decimal(1_000_000)
            entry_price = (cost / qty_bought) if qty_bought else Decimal(0)

            market_id = await self._get_market_id(slug)

            positions.append(Position(
                market_id=market_id,
                exchange="polymarket_us",
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
        try:
            status = self._STATUS_MAP[state]

            return status

        except KeyError:
            #Log error 
            #cancel order because we are unsure of the current status
            return 

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
                order_id=order["id"],
                market_id=await self._get_market_id(slug=order["marketSlug"]),
                exchange="POLYMARKET_US",
                outcome=outcome,
                side=side,
                size=float(order["leavesQuantity"]),   # leavesQuantity is remaining orders left unfilled
                price=float(order["price"]["value"]),
                status=self._get_order_state(state=order['state']),
                strategy="",                        # exchange doesn't know strategies but state.reconcile carries it over
                tif=self._get_tif(tif=order["tif"])
            ))

        return orders

    async def place_order(self, order: OrderIntent) -> OrderRecord:
        response = self.polymarket_api.create_order(
            slug=self._get_market_id(order.market_id),
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

        payload = response['executions'][0]
        outcome, side = self._INTENT_MAP[payload['order']['side']]

        record = OrderRecord(
            order_id=payload["order"]["id"],
            market_id=self._get_market_id(slug=payload["order"]['marketSlug']),
            exchange="POLYMARKET_US",
            outcome=outcome,
            side=side,
            size=float(payload['order']['leavesQuantity']),
            price=float(payload['order']['price']['value']),
            status=self._get_order_state(state=payload['order']['state']),
            strategy=order.strategy,
            tif=self._get_tif(tif=payload['order']['tif'])
        )

        return record

    async def cancel_order(self, order_id: str, market_id: str) -> None:
        slug = self._get_slug(market_id=market_id)
        response = self.polymarket_api.cancel_order(order_id=order_id, slug=slug)

        return

    async def get_balance(self) -> Dict[str, float]:
        response = await self.polymarket_api.get_balance()
        return {"USD": float(response["buyingPower"])}


class PolyUsWebsocketClient(WebsocketClient):
    def __init__(self, key_id: Optional[str], secret_key: Optional[str]):
        self.websocket = PolyUSWebsocket(key_id=key_id, secret_key=secret_key)
        self.queue: asyncio.Queue = asyncio.Queue()

    async def start(self) -> None:
        pass

    async def subscribe(self, token_ids: List[str]) -> None:
        pass

    async def run(self) -> None:
        """Connect, listen, normalize events, push MarketEvent onto queue"""
        pass