import telebot
import json
import os
import requests
from bs4 import BeautifulSoup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Инициализация бота
TOKEN = '7666340013:AAFyx5erqTZ2xLPE1pKkRt6zI7Qsr3SdVHg'
bot = telebot.TeleBot(TOKEN)

# Файл для хранения отправленных скидок
DISCOUNTS_FILE = "discounts.json"

# Функция для загрузки данных о скидках
def load_sent_discounts():
    if os.path.exists(DISCOUNTS_FILE):
        with open(DISCOUNTS_FILE, "r") as file:
            return json.load(file)
    return []

# Функция для сохранения данных о скидках
def save_sent_discounts(discounts):
    with open(DISCOUNTS_FILE, "w") as file:
        json.dump(discounts, file)

# Загружаем отправленные скидки
sent_discounts = load_sent_discounts()

# Функция для парсинга описания игры с сайта
def parse_game_description(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # Извлекаем описание по классу 'game_description_snippet'
        description = soup.find('div', class_='game_description_snippet').get_text(strip=True)
        return description
    except Exception as e:
        print(f"Ошибка при парсинге описания: {e}")
        return "Описание недоступно"

# Функция отправки сообщения о скидке
def send_discount(chat_id, game_name, discount, old_price, new_price, description_url, discount_end, game_url):
    if game_name not in sent_discounts:
        # Парсим краткое описание с сайта
        description = parse_game_description(description_url)

        # Создаем клавиатуру с кнопкой
        markup = InlineKeyboardMarkup()
        button = InlineKeyboardButton("Смотреть 👀", url=game_url)
        markup.add(button)

        # Текст сообщения
        message_text = f"""
🎮 {game_name}
🔥 Скидка: {discount}%
💰 Цена до: {old_price}
💸 Цена после: {new_price}

{description}

⏳ Скидка заканчивается: {discount_end}
        """

        # Отправляем сообщение
        bot.send_message(chat_id, message_text, reply_markup=markup)

        # Добавляем игру в список отправленных
        sent_discounts.append(game_name)
        save_sent_discounts(sent_discounts)
    else:
        print(f"Скидка на {game_name} уже была отправлена.")

# Пример данных для отправки
games = [
    {
        "name": "Game 1",
        "discount": 50,
        "old_price": "500₽",
        "new_price": "250₽",
        "description_url": "https://example.com/game1",  # ссылка на игру для парсинга описания
        "discount_end": "31 декабря 2024",
        "url": "https://example.com/game1"
    },
    {
        "name": "Game 2",
        "discount": 100,
        "old_price": "700₽",
        "new_price": "0₽",
        "description_url": "https://example.com/game2",  # ссылка на игру для парсинга описания
        "discount_end": "15 ноября 2024",
        "url": "https://example.com/game2"
    }
]

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я буду отправлять тебе скидки на игры!")

# Обработчик команды /send_discounts для тестирования отправки скидок
@bot.message_handler(commands=['send_discounts'])
def send_discounts(message):
    for game in games:
        send_discount(
            message.chat.id,
            game['name'],
            game['discount'],
            game['old_price'],
            game['new_price'],
            game['description_url'],
            game['discount_end'],
            game['url']
        )

# Запуск бота
bot.polling()
