from polymarket_us import AsyncPolymarketUS
from typing import Dict
import dotenv
import os
import asyncio


dotenv.load_dotenv()

class PolymarketClient():
    def __init__(self, key_id: str, secret_key: str, paper_trading: bool = True):
        self.client = AsyncPolymarketUS(key_id=key_id, secret_key=secret_key)


    async def get_markets(self, active: bool = True, limit: int = 100, offset: int = 0) -> Dict:
        params = {
            'limit': limit,
            'active': active,
            'closed': False if active else True,
            'offset': offset
        }

        response = self.client.markets.list(params)


        values = {
            'markets': response['markets'],
            'offset': offset + len(response['markets']),
        }    

        return values

    async def get_market(self, market_id: str) -> Dict:
        response = self.client.markets.retrieve(market_id)
        return response

    async def get_all_markets(self, limit: int = None, active: bool = True) -> Dict:
        offset = 0
        all_markets = []

        while True:
            response = self.get_markets(active=active, limit=1000, offset=offset)
            all_markets.extend(response['markets'])

            if limit and len(all_markets) >= limit:
                all_markets = all_markets[:limit]
                break
            offset += len(response['markets'])

        return {'markets': all_markets}

    async def get_orderbook(self, slug: str) -> Dict:
        response = self.client.markets.book(slug)
        return response

    async def get_bbo(self, slug: str) -> Dict:
        response = self.client.markets.bbo(slug)
        return response
   
    async def create_order(self, slug: str, intent: str, order_type: str, price: str, quantity: int, tif: str, slippage: float = None, currency: str = "USD") -> Dict:
        """This Creates an order, can be buy, sell, or limits, etc. changed through the intent"""

        if order_type == "ORDER_TYPE_LIMIT":
            params = {
                'slug': slug,
                'intent': intent,
                'type': order_type,
                'price': price,
                'quantity': quantity,
                'tif': tif
            }
            response = self.client.orders.create(params)
            return response 

        elif slippage is not None:
            params = {
                'slug': slug,
                'intent': intent,
                'type': order_type,
                'quantity': quantity,
                'tif': tif,
                'slippageTolerance': {
                    'currentPrice': {'value': price, 'currency': currency},
                    'ticks': slippage
                }
            }

            response = self.client.orders.create(params)
            return response
        else:
            logger.warning("No slippage tolerance specified for order creation.")
            return {'error': 'No slippage tolerance specified for order creation.'}

    async def cancel_order(self, order_id: str, slug: str) -> Dict:
        response = self.client.orders.cancel(order_id, {"marketSlug": slug})
        return response

    async def cancel_all_orders(self, slug: str = None) -> Dict:
            if slug is None:
                #cancels all orders
                response = self.client.orders.cancel_all()
                return response

            #cancel all order for a specific market
            response = self.client.orders.cancel_all({"marketSlug": slug})
            return response

    async def get_preview(self, slug: str, intent: str, order_type: str, price: str, quantity: int, currency: str) -> Dict:
        """Primarily going to be used for paper trading"""
        params = {
                'slug': slug,
                'intent': intent,
                'type': order_type,
                'price': {'value': price, 'currency': currency},
                'quantity': quantity,
            }
        response = self.client.orders.preview(params)
        return response

    async def close_position(self, slug: str, price: str = None, currency: str = "USD", slippage: float = None) -> Dict:
        """Closes all positions for a given market, at a given price if stated"""
        if price is not None and slippage is not None:
            params = {
                'marketSlug': slug,
                'slippageTolerance': {
                    'currentPrice': {'value': price, 'currency': currency},
                    'ticks': slippage
                }
            }
            response = self.client.orders.close_position(params)
            return response

        else:
            params = {
                'marketSlug': slug
            }
            response = self.client.orders.close_position(params)
            return response

    async def get_orders(self):
        """Gets all open orders"""
        response = self.client.orders.list()
        return response

    async def get_positions(self, limit: int = None, cursor: str = None):
        if limit is not None and cursor is not None:
            positions = self.client.portfolio.positions(limit=limit, cursor=cursor)
            return positions

        elif cursor is not None:
            positions = self.client.portfolio.positions(cursor=cursor)
            return positions

        elif limit is not None:
            positions = self.client.portfolio.positions(limit=limit)
            return positions

        else:
            positions = self.client.portfolio.positions()
            return positions

    async def get_activities(self, limit: int = None, cursor: str = None, types: list[str] = None, marketslug: str = None, sortorder: str = 'SORT_ORDER_DESCENDING'):
        raw_params = {
            'limit': limit,
            'cursor': cursor,
            'types' : types,
            'marketSlug': marketslug,
            'sortOrder': sortorder
        }

        params = {k: v for k, v in raw_params.items()}

        activities = self.client.portfolio.activities(params)
        return activities

    async def get_balance(self):
        balances = self.client.account.balances()
        return balances

if __name__ == "__main__":
    client = PolymarketClient(key_id=os.getenv("KEY_ID"), secret_key=os.getenv("SECRET_KEY"))
    markets = client.get_markets(active=True, limit=1)
    orderbook = client.get_orderbook(slug=markets['markets'][0]['slug'])
    activities = client.list_activities()

    print(activities)