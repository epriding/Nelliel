from dotenv import load_dotenv
import os
import time
import requests

load_dotenv()


def get_json_with_retries(url, params=None, max_retries=3, timeout=30, backoff=1):
    session = requests.Session()
    session.trust_env = False

    for attempt in range(1, max_retries + 1):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError) as exc:
            if attempt == max_retries:
                raise
            time.sleep(backoff * (2 ** (attempt - 1)))
        except requests.RequestException:
            raise


def fetch_tags_page(page=1, limit=100, slug=None):
    url_base = os.getenv("GAMMA_API_URL")
    if not url_base:
        raise RuntimeError("GAMMA_API_URL is not set")

    full_url = f"{url_base}/tags"
    offset = (page - 1) * limit if page and limit else 0
    params = {"offset": offset, "limit": limit}
    if slug is not None:
        params["slug"] = slug

    return get_json_with_retries(full_url, params=params)


def normalize_tag_response(response_data):
    if isinstance(response_data, dict):
        if "data" in response_data:
            return response_data["data"]
        if "tags" in response_data:
            return response_data["tags"]
        if "results" in response_data:
            return response_data["results"]
        return []

    if isinstance(response_data, list):
        return response_data

    raise ValueError("Unexpected tag response format")


def fetch_all_tags(limit=100, max_pages=50):
    all_tags = []
    page = 1

    while page <= max_pages:
        response_data = fetch_tags_page(page=page, limit=limit)
        batch = normalize_tag_response(response_data)
        if not batch:
            break

        all_tags.extend(batch)

        if len(batch) < limit:
            break

        page += 1

    return all_tags


def fetch_tag_by_slug(target_slug):
    target_slug = (target_slug or "").strip().lower()

    try:
        response_data = fetch_tags_page(page=1, limit=100, slug=target_slug)
        batch = normalize_tag_response(response_data)
        for tag in batch:
            if (tag.get("slug") or "").lower() == target_slug:
                return tag
    except requests.RequestException:
        pass

    for tag in fetch_all_tags(limit=100):
        if (tag.get("slug") or "").lower() == target_slug:
            return tag

    return None


def fetch_events_by_tag_slug(target_slug, limit=50):
    tag = fetch_tag_by_slug(target_slug)
    if not tag:
        print(f"No events found for tag with slug '{target_slug}'.")
        return []

    tag_id = tag.get("id")
    print(f"Found event(s) for tag: ({target_slug}) ({tag_id})")

    events_url = f"{os.getenv('GAMMA_API_URL')}/events"
    params = {
        "tag_id": tag_id,
        "active": "true",
        "closed": "false",
        "limit": limit,
    }

    events = get_json_with_retries(events_url, params=params)

    return events

def fetch_markets_from_event(event, only_active=True): 
    markets = event.get("markets", []) or []

    def _is_active(market: dict) -> bool:
        # Explicit boolean flags
        if market.get("active") is False:
            return False
        if market.get("closed") is True:
            return False
        if market.get("isResolved") is True:
            return False
        if market.get("resolved") is True:
            return False
        if market.get("settled") is True:
            return False

        # Status field checks (normalize to uppercase)
        status = (market.get("status") or "").upper()
        if status and status not in ("OPEN", "ACTIVE", "LIVE", "TRADING"):
            return False

        # If none of the checks disqualified the market, assume active
        return True

    if only_active:
        markets = [m for m in markets if isinstance(m, dict) and _is_active(m)]

    return markets


if __name__ == "__main__":
   pass