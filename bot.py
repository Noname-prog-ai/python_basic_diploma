import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext, State
from aiogram.utils import executor
from aiogram.dispatcher import FSMQueue

# Включаем логирование
logging.basicConfig(level=logging.INFO)

# Создаем объект бота с токеном
API_TOKEN = 'YOUR_BOT_API_TOKEN'  # Замените на ваш токен
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Состояния
class Form(StatesGroup):
    city = State()
    location = State()
    check_in_date = State()
    check_out_date = State()
    price_range = State()

# Команды
@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я бот для поиска отелей. Используйте команды: \n"
                        "/help - помощь\n"
                        "/low - минимальные цены на отели\n"
                        "/high - максимальные цены на отели\n"
                        "/history - история запросов")

@dp.message_handler(commands=['low'])
async def low_cmd(message: types.Message):
    await Form.city.set()
    await message.answer("Введите город для поиска:")

@dp.message_handler(commands=['high'])
async def high_cmd(message: types.Message):
    await Form.city.set()
    await message.answer("Введите город для поиска:")

# Получение города
@dp.message_handler(state=Form.city)
async def city_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text
    await Form.location.set()
    await message.answer("Уточните локацию:", reply_markup=location_keyboard())

# Уточнение локации с клавиатурой
def location_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = ["Центр", "Окрестности", "Случайная"]
    keyboard.add(*buttons)
    return keyboard

@dp.message_handler(state=Form.location)
async def location_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['location'] = message.text
    await Form.check_in_date.set()
    await message.answer("Введите дату заезда (в формате ГГГГ-ММ-ДД):")

# Получение даты заезда
@dp.message_handler(state=Form.check_in_date)
async def check_in_date_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['check_in_date'] = message.text
    await Form.check_out_date.set()
    await message.answer("Введите дату выезда (в формате ГГГГ-ММ-ДД):")

# Получение даты выезда
@dp.message_handler(state=Form.check_out_date)
async def check_out_date_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['check_out_date'] = message.text
    await Form.price_range.set()
    await message.answer("Введите диапазон цен (например, 100-200):")

# Получение диапазона цен
@dp.message_handler(state=Form.price_range)
async def price_range_received(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['price_range'] = message.text

    await message.answer("Ищу отели...")
    await show_results(data)
    await state.finish()  # Завершение состояния

# Вывод результатов
async def show_results(data):
    result_message = (
        f"Город: {data['city']}\n"
        f"Локация: {data['location']}\n"
        f"Даты: {data['check_in_date']} - {data['check_out_date']}\n"
        f"Диапазон цен: {data['price_range']}\n"
        f"Результаты поиска:\n"
        f"1. Название: Пример бюджетного отеля\n"
        f"   Ссылка на бронирование: [ссылка](https://example.com)\n"
        f"   Описание: Уютный отель с отличным сервисом.\n"
        f"   Цена: 100\n"
        f"   Фотография: ![фото](https://example.com/image.jpg)\n"
        f"   Координаты: 12.345678, 98.765432\n"
    )
    await bot.send_message(chat_id=data['user_id'], text=result_message, parse_mode='Markdown')

# Команда истории
@dp.message_handler(commands=['history'])
async def history_cmd(message: types.Message):
    await message.answer("История запросов:\n"
                         "- Дата: 2023-10-01\n"
                         "- Ссылка на бронирование: [пример](https://example.com)\n"
                         "- Описание: Пример описания.\n"
                         "- Цена: 150\n"
                         "- Фотографии: ![фото](https://example.com/image.jpg)\n"
                         "- Координаты: 12.345678, 98.765432")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
