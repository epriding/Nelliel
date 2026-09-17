import os
from typing import List
from datetime import datetime
import logging
import pandas as pd
from polymarket import PublicClient
from polymarket.errors import TransportError
from dotenv import load_dotenv
import requests
import time

logging.basicConfig(level=logging.INFO)

load_dotenv()

#schema for the dataframe
class dataframe_schema:
    event_id: int
    event_title: str
    negRisk: bool
    market_ids: List[int]
    market_names: List[str]
    yes_prices: List[float]
    no_prices: List[float]
    sum_yes_prices: float
    sum_no_prices: float
    fee: float

def get_events(pages=None):
    gamma_url = os.getenv('GAMMA_API_URL')

    session = requests.Session()

    params = {
        'limit': 25, 
        'closed': False,

    }


    page_count = 1
    all_events = []

    while True:
        response = session.get(f'{gamma_url}/events/keyset', params=params)

        if response.status_code != 200:
            logging.warning(f'Error fetching page: {page_count}: {response.status_code}')
            break

        data = response.json()

        events_page = data.get('events', [])
        cursor = data.get('next_cursor', [])

        if not events_page:
            logging.info(f'Grabbed Events Successfully: Grabbed {len(all_events)} events')
            break

        all_events.extend(events_page)
        logging.info(f'Page {page_count}: Grabbed {len(events_page)} events: current total {len(all_events)} ')

        if cursor:
            params['after_cursor'] = cursor
            page_count += 1

            time.sleep(0.5)

        else:
            logging.info(f'Grabbed Events Successfully: Grabbed {len(all_events)} events')
            break

        if pages is not None and pages == (page_count-1):
            logging.info(f'Grabbed Events Successfully: Grabbed {len(all_events)} events, pages: {page_count}')
            break

    session.close()
    return all_events


def get_prices(condition_id, max_retries=None, retry_delay=1):
    client = PublicClient()

    attempts = 1

    while attempts <= max_retries if max_retries is not None else True:
        try:
            sdk_market = client.list_markets(condition_ids=condition_id)
            indv_market = sdk_market.first_page().items[0]


            yes_id = indv_market.outcomes.yes.token_id
            no_id = indv_market.outcomes.no.token_id


            yes_price = client.get_price(token_id=yes_id, side="BUY")
            no_price = client.get_price(token_id=no_id, side="SELL")

            logging.info(f"Success: fetched prices for: {indv_market.slug} prices: yes: {yes_price} no: {no_price}")
            return {"yes": yes_price, "no": no_price}

        except TransportError as e:
            logging.warning(f"Error: client error: {e}")
            time.sleep(retry_delay)
            retry_delay *= 2
            attempts += 1

            if attempts is not None and attempts > max_retries:
                logging.warning(f"Error: unable to reach client: {e}")
                raise e 

            logging.info(f"Retrying client connection: attempt(s): {attempts-1}")

        except Exception as e:
            logging.warning(f"Error: failed to fetch prices: {e}")
            raise e



def market_status(current_market):
    if current_market.get('closed', True) or not current_market.get('active', False):
        logging.info(f"Market Status: {current_market.get('slug')} is closed: continuing to next market")
        return True
    else:
        return False



events = get_events(1)
data = []

for event in events:
    event_id = event.get('id')
    event_title = event.get('title')
    neg_risk = event.get('negRisk', None)

    market_ids = []
    market_names = []
    yes_prices = []
    no_prices = []

    for market in event['markets']:
        if market_status(market):
            continue

        market_ids.append(market.get('id'))
        market_names.append(market.get('slug'))

        conditionId = market.get('conditionId')
        pricing = get_prices(condition_id=conditionId)

        yes_prices.append(pricing['yes'])
        no_prices.append(pricing['no'])


    event_data = {
        'event_id': event_id,
        'event_title': event_title,
        'negrisk': neg_risk,
        'market_ids': market_ids,
        'market_names': market_names,
        'yes_prices': yes_prices,
        'no_prices': no_prices,
        'sum_yes_prices': sum(yes_prices),
        'sum_no_prices': sum(no_prices)
    }

    logging.info(f"Sucess: processed {event_title}: total of {len(event['markets'])} market(s)")
    data.append(event_data)


logging.info(f"Success: processed {len(data)} events")
event_df = pd.DataFrame(data)

output_filename = f"market_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"

event_df.to_csv(output_filename, index=False)
logging.info(f"Success: data successfully saved to: {output_filename}")