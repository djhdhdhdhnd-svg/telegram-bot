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

# Функция для парсинга продукта
def parse_product(text):
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

        msg = (
            f"Сегодняшний дневной итог:\n"
            f"Ккал: {total_kcal:.1f}\n"
            f"Белки: {total_protein:.1f} г\n"
            f"Жиры: {total_fat:.1f} г\n"
            f"Углеводы: {total_carbs:.1f} г"
        )
        await message.answer(msg)
        return

    entries = [e.strip() for e in text.split(",") if e.strip()]
    responses = []

    # Загружаем продукты из файла при каждом сообщении
    with open("products.json", encoding="utf-8") as f:
        products = json.load(f)
        print("LOADING PRODUCTS FILE")

    for entry in entries:
        name, amount, unit = parse_product(entry)
        if not name or not amount:
            responses.append(f"Не удалось распознать: '{entry}'")
            continue

        # Поиск продукта в списке
        product = next((p for p in products if p["name"].lower() == name.lower()), None)
        if not product:
            responses.append(f"Продукт '{name}' не найден.")
            continue

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

        responses.append(
            f"{amount}{unit} {name}:\n"
            f"Ккал: {kcal:.1f}\n"
            f"Белки: {protein:.1f} г\n"
            f"Жиры: {fat:.1f} г\n"
            f"Углеводы: {carbs:.1f} г"
        )

    await message.answer("\n\n".join(responses))

async def main():
    print("Bot started")
    await dp.start_polling(bot)

if name == "__main__":
    asyncio.run(main())
