import json
import re
import asyncio
import logging
import os
from datetime import date
from aiogram import Bot, Dispatcher, types
from tinydb import TinyDB, Query

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN variable is not set!")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# TinyDB для дневного журнала
journal_db = TinyDB("journal.json")
journal_table = journal_db.table("journal")

# Загружаем продукты из файла при старте
products_db = TinyDB("products.json")
products_table = products_db.table("products")
with open("products.json", encoding="utf-8") as f:
    products = json.load(f)
products_table.truncate()  # очищаем старую базу
products_table.insert_multiple(products)

# Функция для парсинга продукта
def parse_product(text):
    """
    Поддерживает форматы:
    курица 150г
    150г курица
    яйцо 2шт
    молоко 200мл
    """
    text = text.lower().strip()
    match = re.match(r'(\d+)\s*(г|мл|шт)?\s*(.+)', text)
    if match:
        amount, unit, name = match.groups()
        return name.strip(), int(amount), unit or "г"
    match = re.match(r'(.+?)\s+(\d+)\s*(г|мл|шт)?', text)
    if match:
        name, amount, unit = match.groups()
        return name.strip(), int(amount), unit or "г"
    return None, None, None

# Обработка сообщений
@dp.message()
async def handle_message(message: types.Message):
    text = message.text.lower()
    if text.startswith("/today"):
        today = str(date.today())
        records = journal_table.search(Query().date == today)
        if not records:
            await message.answer("Сегодня ещё нет добавленных продуктов.")
            return

        total_kcal = sum(r["kcal"] for r in records)
        total_protein = sum(r["protein"] for r in records)
        total_fat = sum(r["fat"] for r in records)
        total_carbs = sum(r["carbs"] for r in records)

        msg = f"Сегодняшний дневной итог:\nКкал: {total_kcal:.1f}\nБелки: {total_protein:.1f} г\nЖиры: {total_fat:.1f} г\nУглеводы: {total_carbs:.1f} г"
        await message.answer(msg)
        return

    # Можно писать несколько продуктов через запятую
    entries = [e.strip() for e in text.split(",") if e.strip()]
    responses = []

    for entry in entries:
        name, amount, unit = parse_product(entry)
        if not name or not amount:
            responses.append(f"Не удалось распознать: '{entry}'")
            continue

        Product = Query()
        result = products_table.search(Product.name == name)
        if not result:
            responses.append(f"Продукт '{name}' не найден.")
            continue

        product = result[0]
        kcal = product["kcal"] * amount / 100
        protein = product["protein"] * amount / 100
        fat = product["fat"] * amount / 100
        carbs = product["carbs"] * amount / 100

        journal_table.insert({
            "date": str(date.today()),
            "name": name,
            "amount": amount,
            "unit": unit,
            "kcal": kcal,
            "protein": protein,
            "fat": fat,
            "carbs": carbs
        })

        responses.append(f"{amount}{unit} {name}:\nКкал: {kcal:.1f}\nБелки: {protein:.1f} г\nЖиры: {fat:.1f} г\nУглеводы: {carbs:.1f} г")

    await message.answer("\n\n".join(responses))

async def main():
    print("Bot started")
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())
