import asyncio
import logging
import os
import re
import time
from aiogram import Bot, Dispatcher, types
import requests

# =======================
# Настройки через переменные окружения
# =======================
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Telegram токен бота
CLIENT_ID = os.getenv("FATSECRET_CLIENT_ID")  # FatSecret Client ID
CLIENT_SECRET = os.getenv("FATSECRET_CLIENT_SECRET")  # FatSecret Client Secret

if not TOKEN or not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Не заданы обязательные переменные окружения: TELEGRAM_TOKEN, FATSECRET_CLIENT_ID, FATSECRET_CLIENT_SECRET")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =======================
# Кэш токена FatSecret
# =======================
fatsecret_token_cache = {"token": None, "expires_at": 0}

def get_fatsecret_token():
    now = time.time()
    if fatsecret_token_cache["token"] and fatsecret_token_cache["expires_at"] > now + 10:
        return fatsecret_token_cache["token"]

    token_url = "https://oauth.fatsecret.com/connect/token"
    data = {"grant_type": "client_credentials"}
    try:
        response = requests.post(token_url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))
        response.raise_for_status()
        resp_json = response.json()
        token = resp_json.get("access_token")
        expires_in = resp_json.get("expires_in", 3600)
        if token:
            fatsecret_token_cache["token"] = token
            fatsecret_token_cache["expires_at"] = now + expires_in
            return token
        else:
            logging.error("Не удалось получить токен FatSecret")
            return None
    except Exception as e:
        logging.error(f"Ошибка получения токена FatSecret: {e}")
        return None

# =======================
# Поиск продукта на FatSecret
# =======================
def search_food(query: str):
    token = get_fatsecret_token()
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": query, "format": "json"}
    url = "https://platform.fatsecret.com/rest/server.api?method=foods.search"

    logging.debug(f"[FatSecret] Token (first 20 chars): {token[:20]}")
    logging.debug(f"[FatSecret] Request URL: {url}")
    logging.debug(f"[FatSecret] Request params: {params}")

    try:
        r = requests.get(url, headers=headers, params=params)
        logging.debug(f"[FatSecret] Response status code: {r.status_code}")
        logging.debug(f"[FatSecret] Response body: {r.text}")
        r.raise_for_status()
        data = r.json()

        if "foods" in data and "food" in data["foods"]:
            food_item = data["foods"]["food"][0]
            name = food_item["food_name"]
            calories = int(food_item.get("calories", 0))
            protein = float(food_item.get("protein", 0))
            fat = float(food_item.get("fat", 0))
            carbs = float(food_item.get("carbohydrate", 0))
            return {"name": name, "calories": calories, "белки": protein, "жиры": fat, "углеводы": carbs}
    except Exception as e:
        logging.error(f"Ошибка при поиске продукта '{query}': {e}")

    return None

# =======================
# Обработка сообщений
# =======================
@dp.message()
async def handle_message(message: types.Message):
    text = message.text.strip()
    if not text:
        return

    # Разделяем продукты по запятой
    products_input = [p.strip() for p in text.split(",") if p.strip()]
    responses = []

    for p in products_input:
        numbers = re.findall(r"\d+", p)
        if numbers:
            weight = int(numbers[0])
            product_name = re.sub(r"\d+", "", p).strip()
        else:
            weight = 100
            product_name = p

        if not product_name:
            responses.append("Не удалось определить продукт")
            continue

        product = search_food(product_name)
        if product:
            factor = weight / 100
            responses.append(
                f"{product['name']} ({weight} г):\n"
                f"Калории: {int(product['calories'] * factor)} ккал\n"
                f"Белки: {round(product['белки'] * factor, 1)} г\n"
                f"Жиры: {round(product['жиры'] * factor, 1)} г\n"
                f"Углеводы: {round(product['углеводы'] * factor, 1)} г"
            )
        else:
            responses.append(f"Продукт '{product_name}' не найден в FatSecret")

    await message.answer("\n\n".join(responses))

# =======================
# Запуск бота
# =======================
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(dp.start_polling(bot))
