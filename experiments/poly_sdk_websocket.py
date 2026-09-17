import requests
import json
import asyncio
from polymarket import AsyncPublicClient
from polymarket.models.clob.market_events import MarketPriceChangeEvent, MarketBookEvent
from polymarket.streams import MarketSpec
from websockets.exceptions import ConnectionClosed
from typing import Optional, List



class PolySDKWebsocket():

    def __init__(self, api_key: Optional[str]=None, private_key: Optional[str]=None, passphrase: Optional[str]=None, subscriptions: List[str]=[]):
        self.api_key = api_key
        self.private_key = private_key
        self.subscriptions = subscriptions
        self.queue = asyncio.Queue()
        self.debug_num = 0

    def _handle_book_message(self, data):
        print(data)
        print("handled book event")


    def _handle_price_change_message(self, data):
        print("handled price change event")
        

    async def _event_handler(self):
        """Handles events from the websocket and divides them between topics"""

        print("Event Processor successfully started")

        while True:
            
            event = await self.queue.get()
            try:
 
                if isinstance(event, MarketBookEvent):
                    # Book message - full orderbook snapshot
                    self._handle_book_message(event)
                elif isinstance(event, MarketPriceChangeEvent):
                    # Price change message - incremental updates
                    self._handle_price_change_message(event)

                else:
                    # Unknown message type - log for debugging
                    print(f"Unknown WebSocket event type: {type(event)}")
            
            except json.JSONDecodeError as e:
                print(f"Failed to parse WebSocket event: {e}")
            except Exception as e:
                print(f"Error handling WebSocket event: {e}")

            self.queue.task_done()




    def _return_data(self):
        pass

    async def _stream_websocket(self):
        async with AsyncPublicClient() as client:
            while True:
                try:
                    print("Initializing Secure WebSocket Connection...")

                    async with await client.subscribe(MarketSpec(token_ids=self.subscriptions))as stream:
                        print("Client Successfully Connected!")

                        async for event in stream:
                            await self.queue.put(event)

                except (ConnectionClosed, asyncio.TimeoutError) as e:
                    print(f"Secure stream dropped ({e}). Reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                
                except Exception as e:
                    print(f"Critical error in secure stream: {e}. Retrying in 10 seconds...")
                    await asyncio.sleep(10)


    async def main(self):
        await asyncio.gather(self._stream_websocket(), self._event_handler())

    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            print("Websocket stopped safely")

    def add_ids(self, new_ids: List[str]):
        self.subscriptions.extend(new_ids)



if __name__ == '__main__':
    gamma_url = "https://gamma-api.polymarket.com"

    slug =  'nfl-ne-sea-2026-09-09'
    market = requests.get(f"{gamma_url}/markets/slug/{slug}")

    market_data = market.json()
    print(market_data)
    token_ids = json.loads(market_data['clobTokenIds'])

    yes_tokenids = token_ids[0]
    no_tokenids = token_ids[1]

    subscriptions = [yes_tokenids, no_tokenids]

    websocket = PolySDKWebsocket(subscriptions=subscriptions)
    websocket.run()
