import json
import re
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from tinydb import TinyDB, Query
from datetime import date
import logging

logging.basicConfig(level=logging.INFO)

TOKEN = "8658828353:AAHvZmhjuQj038V-_jCzcFENHsHAwcuGcxI"  # <-- Вставь сюда токен своего Telegram-бота

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Загрузка базы продуктов
with open("products.json", encoding="utf-8") as f:
    products_list = json.load(f)

foods = {p["name"].lower(): p for p in products_list}

# TinyDB для дневника
db = TinyDB("db.json")

# Функция для распознавания продукта и граммов
def parse_message(text):
    text = text.lower()
    match = re.search(r'\d+', text)
    if match:
        amount = float(match.group())
    else:
        return None, None

    product = None
    for name in foods.keys():
        if name in text:
            product = name
            break

    return product, amount

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Enter product and grams in one message, for example:\n"
        "`курица 150` or `150 рис`\n"
        "Bot will calculate calories, protein, fat, and carbs."
    )

# Команда /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Enter product and grams in one message, for example:\n"
        "`курица 150` or `150 рис`\n"
        "Bot will calculate calories, protein, fat, and carbs."
    )

# Обработка любых других сообщений
@dp.message()
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text

    product, amount = parse_message(text)
    if not product:
        await message.answer("Product not found or quantity missing.")
        return

    data = foods[product]
    kcal = data["kcal"] * amount / 100
    protein = data["protein"] * amount / 100
    fat = data["fat"] * amount / 100
    carbs = data["carbs"] * amount / 100

    today = str(date.today())
    db.insert({
        "user_id": user_id,
        "product": product,
        "amount": amount,
        "kcal": kcal,
        "protein": protein,
        "fat": fat,
        "carbs": carbs,
        "date": today
    })

    # Итоги за день
    records = db.search((Query().user_id == user_id) & (Query().date == today))
    total_kcal = sum(r["kcal"] for r in records)
    total_protein = sum(r["protein"] for r in records)
    total_fat = sum(r["fat"] for r in records)
    total_carbs = sum(r["carbs"] for r in records)

    await message.answer(
        f"{amount} g {product}\n"
        f"Calories: {kcal:.1f}\n"
        f"Protein: {protein:.1f} g\n"
        f"Fat: {fat:.1f} g\n"
        f"Carbs: {carbs:.1f} g\n\n"
        f"Total today:\n"
        f"Calories: {total_kcal:.1f}\n"
        f"Protein: {total_protein:.1f} g\n"
        f"Fat: {total_fat:.1f} g\n"
        f"Carbs: {total_carbs:.1f} g"
    )

# Запуск бота
async def main():
    await dp.start_polling(bot)

asyncio.run(main())
