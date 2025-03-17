import os
import requests
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

API_URL = os.getenv("API_URL")  # Используем переменную окружения для URL
API_KEY = os.getenv("API_KEY")

def fetch_lowprice(city):
    response = requests.get(f"{API_URL}/lowprice?city={city}&api_key={API_KEY}")
    if response.ok:
        return response.json().get('hotels', [])
    else:
        return []

def fetch_guestrating(city):
    response = requests.get(f"{API_URL}/guestrating?city={city}&api_key={API_KEY}")  # Исправлено
    if response.ok:
        return response.json().get('hotels', [])
    else:
        return []

def fetch_bestdeal(city):
    response = requests.get(f"{API_URL}/bestdeal?city={city}&api_key={API_KEY}")  # Исправлено
    if response.ok:
        return response.json().get('hotels', [])
    else:
        return []