import asyncio 
from polymarket_us import PolymarketUS
from websockets.exceptions import ConnectionClosed
from typing import Dict, Optional, List
import json
from src.utilities.logger import setup_logger


logger = setup_logger(__name__)


class PolyUSWebsocket():

    def __init__(self, key_id: Optional[str], secret_key: Optional[str]):
        #PolymarketUS client information
        self.key_id = key_id
        self.secret_key = secret_key
        self.client = PolymarketUS(key_id=self.key_id, secret_key=self.secret_key)

        #Websocket status variables
        self.market_ws_connected = False
        self.private_ws_connected = False
        self.successful_private_ws_close = asyncio.Event()
        self.successful_market_ws_close = asyncio.Event()

        #reconnection variables
        self.reconnected_attemps = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 5


        #Track inputs and outputs
        #subscriptions dictionary structure:
        self.subscriptions: Dict[ str:
        Dict[
            "request_type": Dict[       # consider switching subscription type to key
                "subscription_type": str,
                "market_slugs": List[str]
            ]
        ]] = {}
        self.queue = asyncio.Queue()
        

    async def _reconnect(self) -> bool:
        """Handles reconnection logic for the websocket"""
        if self.reconnected_attemps < self.max_reconnect_attempts:
            self.reconnected_attemps += 1

            logger.debug(f"Attempting to reconnect... ({self.reconnected_attemps}/{self.max_reconnect_attempts})")

            await asyncio.sleep(self.reconnect_delay)
            return True
            
        else:
            logger.error("Max reconnection attempts reached. Please check your connection or credentials.")
            return False


    async def _stream_market_websocket(self):
        """Streams market data from the Polymarket US websocket"""
        ws = self.client.ws.markets()

        # Register event handlers
        #replace lambda functions for actual methods to handle the events
        ws.on("market_data", lambda d: logger.debug(f"Book: {d}"))
        ws.on("market_data_lite", lambda d: logger.debug(f"BBO: {d}"))
        ws.on("trade", lambda d: logger.debug(f"Trade: {d}"))

        while True:
            try:
                #starts websocket
                await ws.connect()

                self.market_ws_connected = True
                logger.debug("Market WebSocket successfully connected!")
        

                #loads subscriptions
                for request_type, details in self.subscriptions['market'].items():
                    await ws.subscribe(request_type, details["subscription_type"], details["market_slugs"])


            except (ConnectionClosed, asyncio.TimeoutError) as e:
                logger.error(f"Secure stream dropped: ({e}). Attemping to reconnect...")
                status = await self._reconnect()

                if not status:
                    break  # Exit the loop if reconnection fails

            except KeyboardInterrupt:
                logger.info("Market WebSocket streaming interrupted by user.")
                #Add logic to safely close the websocket, get rid of all manual orders
                #and leave the ride orders
                self.market_ws_connected = False
                self.successful_market_ws_close.set()
                logger.debug("Market WebSocket closed safely.")
            
            except Exception as e:
                logger.error(f"Critical error in secure stream: {e}")
                raise e 

    async def _stream_private_websocket(self):
        """Streams private data from the Polymarket US websocket"""
        ws = self.client.ws.private()

        # Register event handlers
        #replace lambda functions for actual methods to handle the events
        ws.on("order_snapshot", lambda d: logger.debug(f"Orders: {d}"))
        ws.on("order_update", lambda d: logger.debug(f"Order update: {d}"))
        ws.on("position_snapshot", lambda d: logger.debug(f"Positions: {d}"))
        ws.on("position_update", lambda d: logger.debug(f"Position update: {d}"))
        ws.on("account_balance_snapshot", lambda d: logger.debug(f"Balance: {d}"))
        ws.on("error", lambda e: logger.error(f"Error: {e}"))

        while True:
            try:
                #starts websocket
                await ws.connect()

                self.private_ws_connected = True
                logger.debug("Private WebSocket successfully connected!")

                #loads subscriptions
                for request_type, details in self.subscriptions['private'].items():
                    await ws.subscribe(request_type, details["subscription_type"], details["market_slugs"])


            except (ConnectionClosed, asyncio.TimeoutError) as e:
                logger.error(f"Secure stream dropped: ({e}). Attemping to reconnect...")
                status = await self._reconnect()

                if not status:
                    break  # Exit the loop if reconnection fails

            except KeyboardInterrupt:
                logger.info("Private WebSocket streaming interrupted by user.")
                #Add logic to safely close the websocket, get rid of all manual orders
                #and leave the ride orders
                self.private_ws_connected = False
                self.successful_private_ws_close.set()
                logger.debug("Private WebSocket closed safely.")

            except Exception as e:
                logger.error(f"Critical error in secure stream: {e}")
                raise e

    async def _stream_both_websockets(self):
        """Starts the websocket streaming for both market and private data"""
        tasks = [
            asyncio.create_task(self._stream_market_websocket()),
            asyncio.create_task(self._stream_private_websocket())
        ]

        await asyncio.gather(*tasks)


    async def _await_websockets_closed(self):
        """Waits for both websockets to close"""
        if not self.private_ws_connected:
            await self.successful_private_ws_close.wait()

        if not self.market_ws_connected:
            await self.successful_market_ws_close.wait()


    def run(self, private: bool = True, market: bool = True):
        """Runs the websocket streaming for both market and private data"""
        try:
            if not private and not market:
                logger.error("At least one of 'private' or 'market' must be True.")
                return

            elif private == True and market == True:
                asyncio.run(self._stream_both_websockets())

            elif private == True:
                asyncio.run(self._stream_private_websocket())

            elif market == True:
                asyncio.run(self._stream_market_websocket())


        except KeyboardInterrupt:
            asyncio.run(self._await_websockets_closed())
            logger.info("Websocket(s) closed safely.")

        except Exception as e:
            logger.error(f"Error occurred while streaming both websockets: {e}")