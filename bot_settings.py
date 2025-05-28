import telebot
from decouple import config
from peewee import *

# Создаем бота
bot = telebot.TeleBot(config('TELEGRAM_BOT_TOKEN'))

# Заголовки для API
headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': config('API_KEY')  # Здесь используем API_KEY из .env
}

# Подключение к базе данных
my_db = MySQLDatabase(
    config("DB_name"),
    user="root",
    password=config("DB_password"),
    host='localhost',
    port=int(config("DB_port"))
) 
