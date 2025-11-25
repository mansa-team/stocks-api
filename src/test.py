import requests
import os
from dotenv import load_dotenv

load_dotenv()

API = {'KEY': os.getenv('STOCKSAPI_PRIVATE.KEY')}

BASE_URL = "http://localhost:3200"
API_KEY = API['KEY']
headers = {"X-API-Key": API_KEY}

# Historical data
response = requests.get(
    f"{BASE_URL}/api/historical",
    params={
        "search": "AALR3",
        "fields": "DIVIDENDOS,DY,LUCRO LIQUIDO",
        "years": "2019,2020"
    },
    headers=headers
)
print("Historical:")
print(response.json())
print("\n")

# Fundamental by ticker
response = requests.get(
    f"{BASE_URL}/api/fundamental",
    params={
        "search": "VALE3",
        "fields": "ROE,P/L,PRECO",
        "dates": "2025-11-01,2025-11-15"
    },
    headers=headers
)
print("Fundamental by ticker:")
print(response.json())
print("\n")

# Fundamental by name
response = requests.get(
    f"{BASE_URL}/api/fundamental",
    params={
        "search": "Vale",
        "fields": "ROE,P/L,PRECO,DY",
        "dates": "2025-11-01,2025-11-15"
    },
    headers=headers
)
print("Fundamental by name:")
print(response.json())