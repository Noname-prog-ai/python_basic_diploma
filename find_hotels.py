from telebot import types
from bot_settings import bot, headers
import requests
import re
import json
from user_data import *
import calendars
import history
from datetime import datetime
import telebot


def delete_spans(data: str) -> str:
    """
    Функция, удаляющая спецсимволы HTML.

    :param data: строка, содержащая теги HTML
    :return: строка без HTML тегов
    """
    result = re.compile(r'<.*?>')
    return result.sub('', data)


def modify_number(number: str) -> int or float:
    """
    Функция принимает число с типом данных str и заменяет символ запятой на точку.

    :param number: целочисленное или вещественное число с запятой
    :return: целочисленное или вещественное число в соответствии с правилами ЯП Python
    """

    if re.sub(",", ".", number.split()[0], 1).isdigit():
        modified_num = int(re.sub(",", ".", number.split()[0], 1))
    else:
        modified_num = float(re.sub(",", ".", number.split()[0], 1))
    return modified_num


def modify_price(num: str) -> int:
    """
    Т.к. Rapid API возвращает значение стоимости с разделителями в виде запятой,
    данная функция предназначена для удаления запятой.

    :param num: строка
    :return: число
    """
    return int(re.sub(r'[^0-9]+', "", num))


def add_indent(s: int) -> str:
    """
    Функция в значение стоимости добавляет разделитель для удобства чтения информации.

    :param s: число
    :return: строка
    """
    return '{0:,}'.format(s).replace(',', ' ')


def is_number_float(line: str) -> bool:
    """
    Функция проверяет, является ли число float.

    :param line: строка
    :return: True or False
    """

    i = re.match(r'\d*\.?\d+', line)
    if i:
        return i.group() == line
    return False


def calculate_price_for_night(date_1: str, date_2: str, price_for_certain_period: str) -> int:
    """
    Функция считает стоимость проживания в отеле за ночь.

    :param date_1: дата заезда
    :param date_2: дата выезда
    :param price_for_certain_period: стоимость проживания за весь период
    :return: стоимость проживания за ночь
    """

    d_1 = datetime.strptime(str(date_1), "%Y-%m-%d")
    d_2 = datetime.strptime(str(date_2), "%Y-%m-%d")
    date_delta = int((d_2 - d_1).days)
    return int(price_for_certain_period) // date_delta


def request_to_api(url: str, headers: dict, querystring: dict) -> dict or None:
    """
    Функция, производящая запрос к API.

    :param url: ссылка
    :param headers: headers
    :param querystring: parameters
    :return:
    """

    try:
        response = requests.request("GET", url,
                                    headers=headers,
                                    params=querystring,
                                    timeout=10)
        if response.status_code == requests.codes.ok:
            return response.text
    except requests.exceptions.Timeout:
        return None


def find_location(message: telebot.types.Message) -> telebot.types.Message or None:
    """
    Функция для определния локации поиска.

    :param message:
    :return:
    """
    user = User.get_user(message.from_user.id)
    user.city = message.text
    markup = types.InlineKeyboardMarkup()

    url_for_destination_id = "https://hotels4.p.rapidapi.com/locations/v2/search"

    querystring_for_destination_id = {"query": user.city,
                                      "locale": "ru_RU",
                                      "currency": "USD"
                                      }

    response = request_to_api(url=url_for_destination_id,
                              headers=headers,
                              querystring=querystring_for_destination_id)

    if not response:
        bot.send_message(message.chat.id, "Произошла ошибка.\nПопробуйте снова.")
    else:
        result = json.loads(response)['suggestions'][0]['entities']
        if result:
            caption_dict_with_destination_id = dict()
            for i_elem in result:
                if "<" in i_elem.get("caption"):
                    cap = delete_spans(i_elem.get("caption"))
                    if (user.city.title() in cap) or (user.city.lower() in cap):
                        caption_dict_with_destination_id[cap] = i_elem.get("destinationId")

            for elem in caption_dict_with_destination_id:
                markup.add(types.InlineKeyboardButton(elem, callback_data=caption_dict_with_destination_id[elem]))

            bot.send_message(message.chat.id, "Выберите локацию", reply_markup=markup)
        else:
            return bot.send_message(message.chat.id, "По Вашему запросу ничего не найдено.\n"
                                                     "Пожалуйста, проверьте, правильно ли указан город.")

    @bot.callback_query_handler(func=lambda call: True)
    def callback_inline(call):
        user.destination_id = call.data
        msg = bot.edit_message_text(chat_id=call.message.chat.id,
                                    message_id=call.message.message_id,
                                    text="Введите кол-во отелей (максимум - 10):",
                                    reply_markup=None)

        bot.register_next_step_handler(msg, set_hotels_number)


def set_hotels_number(message: telebot.types.Message) -> telebot.types.Message or None:
    """
    Сеттер для кол-ва выводимых отелей.
    Проверяет, правильно ли пользователь ввел кол-во отелей для вывода.
    Значение выводимых отелей должно быть числом и не должно превышаь 10.

    :param message:
    :return:
    """
    user = User.get_user(message.from_user.id)

    if message.text.isdigit():
        if int(message.text) > 10:
            return bot.send_message(message.chat.id, "Вы ввели значение, превышающее 10.\nПопробуйте снова.")

        user.hotels_number_to_show = int(message.text)
        if user.command == "/lowprice" or user.command == "/highprice":
            return calendars.set_arrival_date(message)
        msg = bot.send_message(message.chat.id, "Введите диапазон цен (пример ввода: 1000-5000):")
        return bot.register_next_step_handler(msg, set_price_range)

    bot.send_message(message.chat.id, "Ошибка ввода. Необходимо ввести число от 1 до 25.")


# ----------------------------------------------------------------------------------------------------------------------
"""Функции для команды Best Deal: set_price_range, set_distance_from_center"""


def set_price_range(message: telebot.types.Message) -> None:
    """
    Сеттер для диапазона цен.
    Проверяет, правилньо ли пользователь ввел диапазон цен в соответствии с примером.

    :param message:
    :return:
    """
    user = User.get_user(message.from_user.id)
    price_range = message.text.split("-")
    if len(price_range) == 2:
        if price_range[0].isdigit() and price_range[1].isdigit():
            if int(price_range[0]) < int(price_range[1]):
                price_min, price_max = int(price_range[0]), int(price_range[1])
            else:
                price_min, price_max = int(price_range[1]), int(price_range[0])
            user.min_price, user.max_price = price_min, price_max
            msg = bot.send_message(message.chat.id, "Введите удаленность от центра в км:")

            bot.register_next_step_handler(msg, set_distance_from_center)

    else:
        bot.send_message(message.chat.id, "Ошибка ввода. Попробуйте снова.")


def set_distance_from_center(message: types.Message):
    """
    Сеттер для расстояния от центра.
    Проверяет, правильно ли пользователь ввел данные.

    :param message:
    :return:
    """
    user = User.get_user(message.from_user.id)
    if message.text.isdigit() or is_number_float(str(modify_number(message.text))):
        user.distance_from_center = message.text + " км"
        return calendars.set_arrival_date(message)


#  ---------------------------------------------------------------------------------------------------------------------


def show_or_not_to_show_hotels_photo(message: telebot.types.Message) -> None:
    """
    Данная функция спрашивает у пользователя: показать фото?

    :param message:
    :return:
    """

    photo_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    photo_markup.add("Да", "Нет")
    msg = bot.send_message(message.chat.id, "Показать фото?", reply_markup=photo_markup)
    bot.register_next_step_handler(msg, photos_handler)


def photos_handler(message: telebot.types.Message) -> None:
    """
    Функция, обрабатывающая ответ пользователя из функции show_or_not_to_show_hotels_photo
    :param message:
    :return:
    """

    user = User.get_user(message.from_user.id)

    if message.text == "Да":
        user.photos_uploaded["status"] = True
        msg = bot.send_message(message.chat.id, "Сколько фото загрузить? (максимум - 4)")
        bot.register_next_step_handler(msg, photos_number_setter)
    elif message.text == "Нет":
        user.photos_uploaded["status"] = False
        find_hotels_id(message)


def photos_number_setter(message: telebot.types.Message) -> None:
    """
    Сеттер. Проверяет, правильно ли пользователь ввел значение кол-ва выводимых фото
    :param message:
    :return:
    """
    user = User.get_user(message.from_user.id)
    if message.text.isdigit():
        if int(message.text) > 4:
            bot.send_message(message.chat.id, "Вы ввели значение, превышающее 4.\n"
                                              "Кол-во фото будет задано по умолчанию - 4.")
            user.photos_uploaded["number_of_photos"] = 4
        else:
            user.photos_uploaded["number_of_photos"] = int(message.text)
        find_hotels_id(message)
    else:
        bot.send_message(message.chat.id, "Значение кол-ва фото должно быть числом.")


def find_hotels_id(message: telebot.types.Message):
    """
    На первоначальном этапе функция делает запрос к API.
    В случае получения положительного статуса запроса функция собирает данные по каждому отелю.

    Далее проверяется статуса показа фотографий отеля.
    Если условие вывода фото user.photos_uploaded["status"] == False, то
    в бот отправляет пользователю собранные сведения об отелях.

    В противном случае, вызывается функция получения фотографий отелей (get_photos).

    :param message:
    :return:
    """

    user = User.get_user(message.from_user.id)
    bot.send_message(message.chat.id, "Идет поиск...")

    url_for_hotels_id_list = "https://hotels4.p.rapidapi.com/properties/list"

    if user.command == "/lowprice" or user.command == "/highprice":
        querystring_for_hotels_list = {"destinationId": user.destination_id,
                                       "pageNumber": "1",
                                       "pageSize": user.hotels_number_to_show,
                                       "checkIn": user.arrival_date,
                                       "checkOut": user.departure_date,
                                       "adults1": "1",
                                       "sortOrder": "PRICE_HIGHEST_FIRST" if user.command == "/highprice" else "PRICE",
                                       "locale": "ru_RU",
                                       "currency": "RUB"
                                       }

    else:
        querystring_for_hotels_list = {"destinationId": user.destination_id,
                                       "pageNumber": "1",
                                       "pageSize": user.hotels_number_to_show,
                                       "checkIn": user.arrival_date,
                                       "checkOut": user.departure_date,
                                       "adults1": "1",
                                       "priceMin": user.min_price,
                                       "priceMax": user.max_price,
                                       "sortOrder": "DISTANCE_FROM_LANDMARK",
                                       "locale": "ru_RU",
                                       "currency": "RUB",
                                       "landmarkIds": "Центр города " + user.distance_from_center}

    response_for_hotels_id_list = request_to_api(url=url_for_hotels_id_list,
                                                 headers=headers,
                                                 querystring=querystring_for_hotels_list)

    if not response_for_hotels_id_list:
        bot.send_message(message.chat.id, "Произошла ошибка.\nПопробуйте снова.")
    else:
        result_of_hotels_id_list = json.loads(response_for_hotels_id_list)["data"]["body"]["searchResults"]["results"]
        if result_of_hotels_id_list:
            user.list_of_hotels_id = {i.get('id'):
                                          {"hotel_name": i.get('name'),
                                           "hotel_address": i["address"].get("streetAddress"),
                                           "distance_from_center": i["landmarks"][0].get("distance"),
                                           "hotel_website": f"https://ru.hotels.com/ho{i.get('id')}",
                                           "price_for_certain_period": modify_price(
                                               i['ratePlan']['price'].get('current')),
                                           "photos": []} for i in result_of_hotels_id_list
                                      }

            if user.photos_uploaded["status"] is False:
                text_for_database = ""
                for hotel in user.list_of_hotels_id:
                    price_for_night = calculate_price_for_night(user.arrival_date,
                                                                user.departure_date,
                                                                user.list_of_hotels_id[hotel][
                                                                    'price_for_certain_period'])
                    bot.send_message(message.chat.id,
                                     f"Отель: {user.list_of_hotels_id[hotel]['hotel_name']}\n"
                                     f"Сайт отеля: {user.list_of_hotels_id[hotel]['hotel_website']}\n"
                                     f"Адрес: {user.list_of_hotels_id[hotel]['hotel_address']}\n"
                                     f"Расстояние до центра: {user.list_of_hotels_id[hotel]['distance_from_center']}\n"
                                     f"Период проживания: с {user.arrival_date} по {user.departure_date}\n"
                                     f"Цена за указанный период проживания:"
                                     f" {add_indent(user.list_of_hotels_id[hotel]['price_for_certain_period'])} руб.\n"
                                     f"Цена за ночь: {add_indent(price_for_night)} руб.")

                    text_for_database += f"{user.list_of_hotels_id[hotel]['hotel_name']};"

                history.add_user_data(user.user_id, user.command, user.request_time, text_for_database)
                return bot.send_message(message.chat.id,
                                        f"Поиск завершен.\nНайдено предложений: {len(user.list_of_hotels_id)}")
            return get_photos(message)
        else:
            return bot.send_message(message.chat.id, "По Вашему запросу ничего не найдено")


def get_photos(message: telebot.types.Message):
    """
    В случае условия user.photos_uploaded["status"] == True
    функция, которая получает ссылки на фото отелей и добавляет их в атрибут класса User.

    :param message:
    :return:
    """

    user = User.get_user(message.from_user.id)

    for hotel_data in user.list_of_hotels_id:

        url_for_hotels_photos = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
        querystring_for_hotels_photos = {"id": hotel_data}

        response_for_hotels_photos = request_to_api(url=url_for_hotels_photos,
                                                    headers=headers,
                                                    querystring=querystring_for_hotels_photos)

        if not response_for_hotels_photos:
            return bot.send_message(message.chat.id, "Произошла ошибка.\nПопробуйте снова.")
        else:
            result_of_hotels_photos = json.loads(response_for_hotels_photos)["roomImages"][0]["images"][
                                      0:user.photos_uploaded["number_of_photos"]]

            for hotel_photos in result_of_hotels_photos:
                photo_url = hotel_photos['baseUrl'].format(size="z")
                user.list_of_hotels_id[hotel_data]['photos'].append(photo_url)

    return show_final_data(message)


def show_final_data(message: telebot.types.Message):
    """
    Конечная функция: отправляет итоговую информацию пользователю.
    Итоговая информация имеет вид - альбом, состоящий из фотогафий с подписью к первой фотографии.

    :param message:
    :return:
    """

    user = User.get_user(message.from_user.id)
    text_for_database = ""
    for hotel in user.list_of_hotels_id:
        price_for_night = calculate_price_for_night(user.arrival_date,
                                                    user.departure_date,
                                                    user.list_of_hotels_id[hotel][
                                                        'price_for_certain_period'])

        text = f"Отель: {user.list_of_hotels_id[hotel]['hotel_name']}\n" \
               f"Сайт отеля: {user.list_of_hotels_id[hotel]['hotel_website']}\n" \
               f"Адрес: {user.list_of_hotels_id[hotel]['hotel_address']}\n" \
               f"Расстояние до центра: {user.list_of_hotels_id[hotel]['distance_from_center']}\n" \
               f"Период проживания: с {user.arrival_date} по {user.departure_date}\n" \
               f"Цена за указанный период проживания: " \
               f"{add_indent(user.list_of_hotels_id[hotel]['price_for_certain_period'])} руб.\n" \
               f"Цена за ночь: {add_indent(price_for_night)} руб."

        text_for_database += f"{user.list_of_hotels_id[hotel]['hotel_name']};"

        photos = [types.InputMediaPhoto(media=url, caption=text) if num == 0
                  else types.InputMediaPhoto(media=url)
                  for num, url in enumerate(user.list_of_hotels_id[hotel]['photos'])]

        bot.send_media_group(message.chat.id, photos)

    history.add_user_data(user.user_id, user.command, user.request_time, text_for_database)

    return bot.send_message(message.chat.id,
                            f"Поиск завершен.\nНайдено предложений: {len(user.list_of_hotels_id)}")
