import asyncio 
from polymarket_us import PolymarketUS
from websockets.exceptions import ConnectionClosed
from typing import Dict, Optional, List, Callable, Any
import json
from src.utilities.logger import setup_logger


logger = setup_logger(__name__)


class PolyUSWebsocket():

    def __init__(self, key_id: Optional[str], secret_key: Optional[str], handlers: Dict[str, Callable], error_handler: Callable, close_handler: Callable, market_subscriptions: Dict[str, Dict[str, List[str]]] = None):
        #PolymarketUS client information
        self.key_id: Optional[str] = key_id
        self.secret_key: Optional[str] = secret_key
        self.client: PolymarketUS = PolymarketUS(key_id=self.key_id, secret_key=self.secret_key)

        #websockets
        self._ws: Dict[str, Any] = {} #once its connection function will add the instances

        #Handlers
        self.handlers: Dict[str, Callable] = handlers
        self.on_error: Callable = error_handler
        self.on_close: Callable = close_handler

        #events
        self.MARKET_EVENTS = {'market_data', 'market_data_lite', 'trade'}
        self.PRIVATE_EVENTS = {'order_snapshot', 'order_update', 'position_snapshot', 'position_update',
                                'account_balance_snapshot', 'account_balance_update'}

        #Websocket status variables
        self._connected: Dict[str, bool] = {'market': False, 'private': False}
        self._disconnected: Dict[str, asyncio.Event] = {'market': asyncio.Event(), 'private': asyncio.Event()}

        #fix variables if keeping them or delete them
        self.successful_private_ws_close = asyncio.Event()
        self.successful_market_ws_close = asyncio.Event()

        #reconnection variables
        self._attempts: Dict[str, int] = {'market': 0, 'private': 0}
        self._max_reconnect_attempts: int = 10
        self._reconnect_delay: int = 5

        #Track inputs and outputs
        #subscriptions dictionary structure:
        self.market_subscriptions: Dict[str, Dict[str, List[str]]] = market_subscriptions
        self.private_subscriptions: Dict[str, str] = {
            'orders': 'SUBSCRIPTION_TYPE_ORDER',
            'positions': 'SUBCRIPTION_TYPE_POSITION',
            'balance': 'SUBSCRIPTION_TYPE_ACCOUNT_BALANCE'
        }

        #Misc

        #Rid map
        self.RID_MAP = {
            'SUBSCRIPTION_TYPE_MARKET_DATA': 'market_data',
            'SUBSCRIPTION_TYPE_MARKET_DATA': 'market_data_lite',
            'SUBSCRIPTION_TYPE_TRADE': 'trade'
        }

    def _register_handlers(self, ws_type: str, ws) -> None:
        allowed = self.MARKET_EVENTS if ws_type == "market" else self.PRIVATE_EVENTS
        for event, handler in self.handlers.items():
            if event in allowed:
                ws.on(event, handler)

    async def _load_subscriptions(self, ws_type: str, ws) -> None:
        if ws_type == 'market':
            if not self.market_subscriptions:
                return

            for slug, info in self.market_subscriptions.items():
                for sub_type in info['sub_types']:
                    rid = self._get_rid(sub_type=sub_type, slug=slug)
                    ws.subscribe(rid, sub_type, [slug])

        else:
            for rid, sub_type in self.private_subscriptions.items():
                ws.subscribe(rid, sub_type)
        
    def _get_rid(self, sub_type: str, slug: str) -> str:
        """creates the rid for subscriptions"""
        suffix = self.RID_MAP[sub_type]
        return f'{slug}:{suffix}'


    async def add_market_subscription(self, sub_types: List[str], slug: str) -> None:
        """Adds a market subscription to the websocket subscription list"""
        for sub_type in sub_types:
            rid = self._get_rid(sub_type=sub_type, slug=slug)
            self._ws['market'].subscribe(rid, sub_type, [slug])

        self.market_subscriptions[slug] = {'sub_type': sub_types, 'slug': slug}

    async def remove_market_subscription(self, slug: str) -> None:
        """Removes a market subscription"""
        subscription_data = self.market_subscriptions.pop(slug, None)

        if subscription_data is None:
            logger.error('Error: failed to fetch market subscription data.')
            return
        
        for sub_type in subscription_data['sub_types']:
            rid = self._get_rid(slug=slug)
            self._ws['market'].unsubscribe(rid)


    async def _close_websocket(self, ws_type: str) -> None:
        """Closes websocket"""
        await self._ws[ws_type].close()
        del self._ws[ws_type]

    async def _connect(self, ws_type: str) -> None:
        """Connects the websocket to Polymarket US"""
        ws = self.client.ws.markets() if ws_type == 'market' else self.client.ws.private()
        self._register_handlers(ws_type=ws_type, ws=ws)

        await ws.connect()

        self._ws[ws_type] = ws

    async def _start_stream(self, ws_type: str) -> None:
        """Streams market or private data depending on websocket type: ws_type"""
        try:
            if ws_type not in self._ws:
                self._connect

            while True:
                await self._disconnected[ws_type].wait()

                while True:
                    if self._attempts[ws_type] >= self._max_reconnect_attempts:
                        logger.error(f"{ws_type.upper()} WS: max reconnection attempts reached.")
                        return

                    delay = min(self._reconnect_delay * 2 ** self._attempts[ws_type], 60)
                    self._attempts[ws_type] += 1
                    await asyncio.sleep(delay)

                    try:
                        await self._connect(ws_type=ws_type)
                        break

                    except (ConnectionClosed, asyncio.Timeout, OSError) as e:
                        logger.error(f"{ws_type.upper()} WS: reconnect failed: {e}")

        except asyncio.CancelledError:
            self._close_websocket(ws_type=ws_type)
            raise


    async def start(self) -> None:
        await self._connect('market')
        await self._connect('private')

    async def run(self) -> None:
        await asyncio.gather(self._start_stream('market'), self._start_stream('private'))
