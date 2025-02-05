import requests
import datetime
import asyncio
import aiohttp
from logger import logger

WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"
FOOD_API_URL = "https://world.openfoodfacts.org/cgi/search.pl"


async def get_temperature(city, api_key):
    params = {
            'q': city,
            'appid': api_key,
            'units': 'metric'
        }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(WEATHER_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data["main"]["temp"]
            logger.error("Get temperature http response error: {}", response.status)
    
    return None


async def get_food_info(product_name):
    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "action": "process",
        "fields": "product_name,nutriments",
        "json": 1,
        "page_size": 1
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(FOOD_API_URL, params=params) as response:
            if response.status == 200:
                data = await response.json()
                products = data.get('products', [])
                if products:
                    first_product = products[0]
                    return {
                        'name': first_product.get('product_name', 'Неизвестно'),
                        'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                    }
            else:
                logger.error("Get food info http response error: {}", response.status)
    
    return None
