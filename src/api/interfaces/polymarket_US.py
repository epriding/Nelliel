from base_interfaces import WebsocketClient, RestClient
from ..polymarket.polyUS_api import PolymarketAPI
from ..polymarket.polyus_websocket import PolyUSWebsocket
from typing import List, Dict
import asyncio
from ...utilities.classes import OrderIntent, OrderRecord, Position, MarketInfo, BookSnapshotEvent, PriceChangeEvent

class PolyUsClient(RestClient):
    def __init__(self, key_id: str, secret_key: str):
        self.polymarket_api = PolymarketAPI(key_id=key_id, secret_key=secret_key)

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
                    market['marketSides'][1]['descrption'].upper(): market['marketSides'][1]['id']
                },
                active=market['active'],
                tradable={
                    market['marketSides'][0]['description'].upper(): market['marketSides'][0]['tradable'],
                    market['marketSides'][1]['descrption'].upper(): market['marketSides'][1]['tradable']
                },
                volume=market['volume'],
                prices={
                    market['marketSides'][0]['description'].upper(): market['marketSides'][0]['price'],
                    market['marketSides'][1]['descrption'].upper(): market['marketSides'][1]['price']
                },
            )
            markets.append(market_info)

        return markets

    async def get_orderbook(self, market_id: str, outcome: str) -> Dict:
        