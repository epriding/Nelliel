import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

# Finds the directory where interpret_data.py lives
SCRIPT_DIR = Path(__file__).parent 

path_name = 'test_data.csv'

# Joins that directory path with your file name
csv_path = SCRIPT_DIR / path_name

data = pd.read_csv(csv_path)

logging.info('Success: Found {path_name}')

multiple_markets = data[data['market_ids'].str.contains(',', na=False)]

sum_prices = multiple_markets.loc[:,['event_title', 'sum_yes_prices', 'sum_no_prices']]

print(sum_prices)

multiple_markets.to_csv('final_data.csv', index=False)
logging.info('Success: wrote data to final_data.csv')