import os
from typing import List
from datetime import datetime
import logging
import pandas as pd
from polymarket import PublicClient, OrderSide
from fetch_markets import fetch_all_tags, fetch_events_by_tag_slug, fetch_markets_from_event
logging.basicConfig(level=logging.INFO)

for proxy_var in [
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "SOCKS_PROXY",
    "socks_proxy",
]:
    os.environ.pop(proxy_var, None)

# Use the Polymarket public client for read-only market data
client = PublicClient()

#schema for the dataframe
class dataframe_schema:
    tag_id: int
    tag_slug: str
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

time = datetime.now()

all_tags = fetch_all_tags(limit=100, max_pages=1)

tags_df = pd.DataFrame(all_tags)
market_rows = []


def get_market_token_id(market):
    """Safely extract yes/no token ids from a market object or dict.

    Returns a list [yes_token_id, no_token_id] where elements may be None.
    """

    if not market:
        return []

    try:
        token_list = [market.outcomes.yes.token_id, market.outcomes.no.token_id]
        return token_list

    except Exception as e:
        logging.warning("Unable to find token_id: %s", e)

    # Handle mapping when market is a dict
    """if isinstance(market, dict):
        outcomes = market.get("outcomes")

        if isinstance(outcomes, dict):
            yes = outcomes.get("yes") or {}
            no = outcomes.get("no") or {}
            yes_id = yes.get("token_id") if isinstance(yes, dict) else None
            no_id = no.get("token_id") if isinstance(no, dict) else None
            if yes_id or no_id:
                return [yes_id, no_id]

        if isinstance(outcomes, tuple):
            yes_id = None
            no_id = None
            for o in outcomes:
                name = (o.get("name") or "").lower()
                if "yes" in name:
                    yes_id = o.get("token_id")
                if "no" in name:
                    no_id = o.get("token_id")
            if yes_id or no_id:
                return [yes_id, no_id]

        # fallback fields
        yes_id = market.get("yes_token_id") or market.get("yesTokenId")
        no_id = market.get("no_token_id") or market.get("noTokenId")
        if yes_id or no_id:
            return [yes_id, no_id]

    # Handle object-like (attributes)
    try:
        outcomes = getattr(market, "outcomes", None)
    except Exception:
        outcomes = None

    if outcomes:
        try:
            yes = getattr(outcomes, "yes", None)
            no = getattr(outcomes, "no", None)
            yes_id = getattr(yes, "token_id", None) if yes is not None else None
            no_id = getattr(no, "token_id", None) if no is not None else None
            return [yes_id, no_id]
        except Exception:
            pass


    return []
"""

def get_token_prices(client, token_id):
    """Return (buy_price, sell_price) for a single token id, or (None, None)."""
    if not token_id:
        return None, None

    try:
        buy_price = client.get_price(token_id=token_id, side="BUY")
        sell_price = client.get_price(token_id=token_id, side="SELL")
        # Convert to float when possible
        try:
            buy_price = float(buy_price) if buy_price is not None else None
        except Exception:
            logging.warning("Unable to convert buy_price for token %s: %r", token_id, buy_price)
            buy_price = None

        try:
            sell_price = float(sell_price) if sell_price is not None else None
        except Exception:
            logging.warning("Unable to convert sell_price for token %s: %r", token_id, sell_price)
            sell_price = None

        return buy_price, sell_price
    except Exception as exc:
        logging.warning("price fetch failed for token %s: %s", token_id, exc)
        return None, None


def get_market_prices(client, token_ids):
    for token_id in token_ids:
        if not token_id:
            continue
        try:
            buy_price = client.get_price(token_id=token_id, side=OrderSide.BUY)
            sell_price = client.get_price(token_id=token_id, side=OrderSide.SELL)
            return buy_price, sell_price
        except Exception:
            continue

    return None, None

for tag in all_tags:
    tag_id = tag.get("id")
    tag_slug = tag.get("slug")
    events = fetch_events_by_tag_slug(tag_slug, limit=1)

    for event in events:
        event_id = event.get("id")
        event_title = event.get("title")
        negRisk = event.get("negRisk")
        markets = fetch_markets_from_event(event)
        new_markets = []
        for market in markets:
            # SDK expects exactly one of `id`, `slug`, or `url` (keyword-only).
            # Use the market's `id` field from the event payload (documented parameter name).
            market_id = None
            if isinstance(market, dict):
                market_id = market.get("id")
            else:
                try:
                    market_id = getattr(market, "id", None)
                except Exception:
                    market_id = None

            if not market_id:
                logging.info("Skipping market: no 'id' field present in payload")
                continue

            try:
                m = client.get_market(id=market_id)
            except Exception as exc:
                logging.warning("Failed to fetch market for id %s: %s", market_id, exc)
                continue

            if not m:
                logging.info("Skipping missing market for id %s", market_id)
                continue

            # if market dict/object has explicit inactive flags, skip
            m_active = None
            if isinstance(m, dict):
                m_active = m.get("active")
                if m_active is False:
                    logging.info("Skipping inactive market id %s", m.get("id"))
                    continue

            new_markets.append(m)

        market_ids = []
        market_names = []
        yes_prices = []
        no_prices = []

        for market in new_markets:
            # support both dict payloads and SDK `Market` model objects
            if isinstance(market, dict):
                market_id = market.get("id")
                market_name = market.get("name") or market.get("question")
            else:
                market_id = getattr(market, "id", None)
                # SDK Market uses `question` for the market text
                market_name = getattr(market, "question", None) or getattr(market, "slug", None)

            token_ids = get_market_token_id(market)

            market_ids.append(market_id)
            market_names.append(market_name)

            if token_ids:
                # Expect token_ids = [yes_id, no_id]
                yes_id = token_ids[0] if len(token_ids) > 0 else None
                no_id = token_ids[1] if len(token_ids) > 1 else None

                yes_buy, yes_sell = get_token_prices(client, yes_id)
                no_buy, no_sell = get_token_prices(client, no_id)

                # prefer the buy-side price as the market price for each side
                yes_prices.append(yes_buy)
                no_prices.append(no_buy)
            else:
                yes_prices.append(None)
                no_prices.append(None)

        market_rows.append({
            "tag_id": tag_id,
            "tag_slug": tag_slug,
            "event_id": event_id,
            "event_title": event_title,
            "negRisk": negRisk,
            "market_ids": market_ids,
            "market_names": market_names,
            "yes_prices": yes_prices,
            "no_prices": no_prices,
            "sum_yes_prices": sum(value for value in yes_prices if value is not None),
            "sum_no_prices": sum(value for value in no_prices if value is not None),
            "fee": event.get("fee", 0.0),
        })

market_df = pd.DataFrame(market_rows)

output_filename = f"market_data_{time.strftime('%Y%m%d_%H%M%S')}.csv"
market_df.to_csv(output_filename, index=False)
logging.info("Market data saved to %s", output_filename)