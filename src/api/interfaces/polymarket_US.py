from decimal import Decimal
from base_interfaces import WebsocketClient, RestClient
from ..polymarket.polyUS_api import PolymarketAPI
from ..polymarket.polyus_websocket import PolyUSWebsocket
from typing import List, Dict
import asyncio
from ...utilities.classes import OrderIntent, OrderRecord, Position, MarketInfo, BookSnapshotEvent, PriceChangeEvent, OrderBook, Side
import time


class PolyUsClient(RestClient):
    def __init__(self, key_id: str, secret_key: str):
        self.polymarket_api: PolymarketAPI = PolymarketAPI(key_id=key_id, secret_key=secret_key)
        self._slug_cache: Dict[str, str] = {}
        self._market_id_cache: Dict[str, str] = {}

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
            exchange="polymarket_us",
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