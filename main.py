print("VERSION CHECK")  # <-- это просто метка, чтобы увидеть, что файл новый
import json
import os
import re
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
import asyncio

logging.basicConfig(level=logging.INFO)

# --- Получаем токен из переменной окружения Railway ---
TOKEN = os.environ.get("TOKEN")  # В Railway нужно добавить переменную окружения TOKEN с токеном бота

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Загружаем продукты ---
PRODUCTS_FILE = "products.json"

def load_products():
    try:
        with open(PRODUCTS_FILE, encoding="utf-8") as f:
            products = json.load(f)
            print("LOADING PRODUCTS FILE")
            print(products)  # Показываем, что продукты реально загружены
            return products
    except Exception as e:
        print("Error loading products:", e)
        return {}

products = load_products()

# --- Обработка команды /start ---
@dp.message(Command(commands=["start"]))
async def cmd_start(message: Message):
    await message.answer("Привет! Я бот, который считает калории.\nОтправь продукт и количество, чтобы получить калории.")

# --- Обработка любого текста ---
@dp.message()
async def handle_message(message: Message):
    text = message.text.lower().strip()

    # Extract amount (grams) from the message — look for the first integer or float
    amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
    if amount_match:
        amount = float(amount_match.group(1))
    else:
        amount = 100.0  # default to 100g if no number provided

    found = []
    for product in products:
        if product["name"] in text:
            ratio = amount / 100
            kcal   = round(product["kcal"]    * ratio, 1)
            protein = round(product["protein"] * ratio, 1)
            fat    = round(product["fat"]      * ratio, 1)
            carbs  = round(product["carbs"]    * ratio, 1)
            found.append(
                f"{product['name']} ({int(amount) if amount == int(amount) else amount}г): {kcal} ккал, "
                f"Белки: {protein}г, "
                f"Жиры: {fat}г, "
                f"Углеводы: {carbs}г"
            )
    if found:
        await message.answer("\n".join(found))
    else:
        await message.answer("Продукт не найден. Добавь его в products.json.")

# --- Основной запуск ---
async def main():
    print("BOT STARTED")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
