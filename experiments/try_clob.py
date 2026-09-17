import requests
from polymarket import PublicClient

url = "https://gamma-api.polymarket.com"
client = PublicClient()

response = requests.get(url+"/markets", params={"limit": 1})
response = response.json()
condition_id = response[0].get("conditionId")
status = response[0].get("closed")
print(type(status))
print(type(False))

print(condition_id)

markets = client.list_markets(condition_ids=condition_id)
first_page = markets.first_page()
market = first_page.items[0]

print(market.slug)