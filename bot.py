import requests
import telebot
from telebot import types
from datetime import datetime
import time
from bs4 import BeautifulSoup
import json

# API ключ Telegram-бота
TELEGRAM_CHAT_ID = '-1002331953667'
TOKEN = '7666340013:AAFyx5erqTZ2xLPE1pKkRt6zI7Qsr3SdVHg'

bot = telebot.TeleBot(TOKEN)

# Множество для хранения отправленных ID игр
sent_game_ids = set()
pinned_messages = {}

def get_steam_sales():
    response = requests.get('https://store.steampowered.com/api/featuredcategories')
    if response.status_code != 200:
        print("Ошибка при получении данных со Steam API")
        return []
    data = response.json()
    discounted_games = [item for item in data['specials']['items'] if item['discount_percent'] > 0]
    return discounted_games

def fetch_game_description(game_id):
    url = f'https://store.steampowered.com/app/{game_id}'
    response = requests.get(url)
    if response.status_code != 200:
        print(f"Ошибка при получении страницы игры: {url}")
        return ""

    soup = BeautifulSoup(response.text, 'html.parser')
    description_div = soup.find('div', class_='game_description_snippet')
    return description_div.get_text(strip=True) if description_div else "Описание недоступно."

def send_discounted_games(games):
    for game in games:
        print(f"Обрабатываем игру: {game['name']}")

        if game['id'] in sent_game_ids:
            print(f"Игра '{game['name']}' уже была отправлена, пропускаем.")
            continue

        # Проверяем наличие изображения
        image_url = game.get('large_capsule_image') or game.get('header_image')
        if not image_url:
            print(f"Изображение для {game['name']} недоступно. Отправляем сообщение без изображения.")
            image_url = None  # Устанавливаем image_url в None, чтобы отправить сообщение без изображения

        # Выводим URL изображения для отладки
        print(f"URL изображения для '{game['name']}': {image_url}")

        # Проверяем доступность URL, если есть изображение
        if image_url:
            try:
                img_response = requests.get(image_url)
                if img_response.status_code != 200:
                    print(f"Ошибка доступа к изображению: {image_url}. Отправляем сообщение без изображения.")
                    image_url = None  # Если изображение недоступно, устанавливаем в None
            except Exception as e:
                print(f"Ошибка при проверке URL изображения: {e}. Отправляем сообщение без изображения.")
                image_url = None  # Если произошла ошибка, устанавливаем в None

        game_description = fetch_game_description(game['id'])
        # Формируем сообщение
        message = (
            f"🎮 *{game['name']}*\n"
            f"🔥 Скидка: {game['discount_percent']}%\n"
            f"💰 Цена до: {game['original_price'] / 100:.2f} {game['currency']}\n"
            f"💸 Цена после: {game['final_price'] / 100:.2f} {game['currency']}\n"
            f"\n{game_description}\n\n"
        )

        if 'discount_expiration' in game:
            expiration_date = datetime.fromtimestamp(game['discount_expiration'])
            message += f"⏳ Скидка заканчивается: {expiration_date.strftime('%Y-%m-%d %H:%M:%S')}\n"

        markup = types.InlineKeyboardMarkup()
        button = types.InlineKeyboardButton("Смотреть 👀", url=f"https://store.steampowered.com/app/{game['id']}")
        markup.add(button)

        attempt = 0
        while attempt < 5:
            try:
                # Если image_url None, отправляем сообщение без фото
                if image_url:
                    sent_message = bot.send_photo(
                        TELEGRAM_CHAT_ID,
                        image_url,
                        caption=message,
                        parse_mode='Markdown',
                        reply_markup=markup
                    )
                else:
                    sent_message = bot.send_message(
                        TELEGRAM_CHAT_ID,
                        message,
                        parse_mode='Markdown',
                        reply_markup=markup
                    )

                if game['discount_percent'] == 100:
                    bot.pin_chat_message(TELEGRAM_CHAT_ID, sent_message.message_id)
                    pinned_messages[game['id']] = sent_message.message_id
                    print(f"Игра '{game['name']}' с 100% скидкой закреплена.")

                sent_game_ids.add(game['id'])
                print(f"Игра '{game['name']}' отправлена.")
                break

            except telebot.apihelper.ApiException as e:
                if e.error_code == 400:
                    print(f"Ошибка 400: Неправильный URL изображения для '{game['name']}'.")
                    print(f"Проверяем URL: {image_url}")
                    break
                elif e.error_code == 429:
                    try:
                        retry_after = int(e.description.split(' ')[-1]) + 5
                    except:
                        retry_after = 5  # Если не удалось разобрать время ожидания
                    print(f"Достигнут лимит частоты запросов. Ожидание {retry_after} секунд...")
                    time.sleep(retry_after)
                    attempt += 1
                else:
                    print(f"Ошибка при отправке '{game['name']}': {e}")
                    break

def check_discount_expiration():
    for game_id, message_id in list(pinned_messages.items()):
        response = requests.get(f'https://store.steampowered.com/api/appdetails?appids={game_id}')
        if response.status_code != 200:
            print(f"Ошибка при получении данных для игры с ID {game_id}")
            continue

        data = response.json()
        if str(game_id) in data and 'data' in data[str(game_id)]:
            game_data = data[str(game_id)]['data']
            if 'discount_expiration' in game_data and game_data['discount_expiration']:
                expiration_timestamp = game_data['discount_expiration']
                if expiration_timestamp < datetime.now().timestamp():
                    bot.unpin_chat_message(TELEGRAM_CHAT_ID, message_id)
                    del pinned_messages[game_id]
                    print(f"Сообщение для игры с ID {game_id} откреплено, так как срок действия скидки истек.")

def main():
    while True:
        try:
            games = get_steam_sales()
            if games:
                send_discounted_games(games)
            else:
                print("Нет скидок на игры.")
            check_discount_expiration()
            # Ждем некоторое время перед следующим циклом (например, 1 час)
            time.sleep(3600)
        except KeyboardInterrupt:
            print("Бот остановлен.")
            break
        except Exception as e:
            print(f"Произошла ошибка: {e}")
            # Ждем перед повторной попыткой
            time.sleep(60)

if __name__ == '__main__':
    main()
