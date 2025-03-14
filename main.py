import logging
import os
import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from peewee import SqliteDatabase, Model, CharField, DateTimeField
from api_requests import fetch_lowprice, fetch_guestrating, fetch_bestdeal

# Настройка базы данных
db = SqliteDatabase('history.db')

class SearchHistory(Model):
    user_id = CharField()
    city = CharField()
    date = DateTimeField(default=datetime.datetime.now)
    details = CharField()

    class Meta:
        database = db

db.connect()
db.create_tables([SearchHistory], safe=True)

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Функции команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Привет! Я телеграм-бот для поиска отелей! Введите /help для получения помощи.')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '/lowprice - показать доступные отели\n'
        '/guestrating - показать самые популярные отели\n'
        '/bestdeal - показать отели, ближе всего к центру\n'
        '/history - просмотреть историю поисков'
    )

async def lowprice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = "Москва"  # Здесь можно добавить логику для ввода города
    hotels = fetch_lowprice(city)

    if hotels:
        message = "\n".join([f"{hotel['name']}: {hotel['price']} RUB" for hotel in hotels])
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Нет доступных отелей или ошибка при запросе.")

async def guestrating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = "Москва"
    hotels = fetch_guestrating(city)

    if hotels:
        message = "\n".join([f"{hotel['name']}: Рейтинг {hotel['rating']}" for hotel in hotels])
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Нет данных о популярных отелях или ошибка при запросе.")

async def bestdeal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = "Москва"
    hotels = fetch_bestdeal(city)

    if hotels:
        message = "\n".join([f"{hotel['name']}: Ближе всего к центру - {hotel['price']} RUB" for hotel in hotels])
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Нет данных об отелях ближе к центру или ошибка при запросе.")

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    histories = SearchHistory.select().where(SearchHistory.user_id == user_id)
    if histories:
        message = '\n'.join([f'{record.date}: {record.city} - {record.details}' for record in histories])
        await update.message.reply_text(message)
    else:
        await update.message.reply_text('История поиска пуста.')

# Основная функция
def main():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("lowprice", lowprice))
    application.add_handler(CommandHandler("guestrating", guestrating))
    application.add_handler(CommandHandler("bestdeal", bestdeal))
    application.add_handler(CommandHandler("history", history))

    application.run_polling()

if __name__ == "__main__":
    main()
