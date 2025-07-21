import asyncio
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import F
from aiogram.types import Message, CallbackQuery
from aiogram.client.default import DefaultBotProperties
import logging

TOKEN = "7628435014:AAEmjBCfuoO4C0JPwU7pS7AVz9RtVmuYZKM"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

user_data = {}
user_cooldowns = {}  # user_id: datetime

class Form(StatesGroup):
    waiting_for_id = State()
    waiting_for_pair = State()
    ready_for_signals = State()

pairs = ["USD/CHF OTC", "AUD/USD OTC", "USD/JPY OTC", "USD/CAD OTC"]
timeframes = ["1 минута"] * 7 + ["3 минуты"] * 2 + ["15 минут"]
budget_options = ["10% от банка", "15% от банка", "20% от банка"]
directions = ["📈 Вверх", "📉 Вниз"]

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await message.answer("👋 Привет! Пожалуйста, отправь мне свой ID аккаунта")
    await state.set_state(Form.waiting_for_id)

@dp.message(Form.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    user_data[message.from_user.id] = {"id": message.text}
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=p, callback_data=f"pair:{p}")] for p in pairs]
    )
    await message.answer("✅ ID принят. Теперь выбери валютную пару:", reply_markup=kb)
    await state.set_state(Form.waiting_for_pair)

@dp.callback_query(F.data.startswith("pair:"))
async def select_pair(callback: CallbackQuery, state: FSMContext):
    pair = callback.data.split(":")[1]
    user_data[callback.from_user.id]["pair"] = pair
    btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📩 ПОЛУЧИТЬ СИГНАЛ", callback_data="get_signal")]]
    )
    await callback.message.answer(f"Отличная пара: {pair}\nГотов отправить сигнал. 👇", reply_markup=btn)
    await state.set_state(Form.ready_for_signals)

# 🔥 ФИКС: переместили хендлер ВНЕ другого хендлера!
@dp.callback_query(F.data == "get_signal")
async def send_signal(callback: CallbackQuery):
    user_id = callback.from_user.id
    now = datetime.utcnow()

    # Проверка кулдауна
    if user_id in user_cooldowns and now < user_cooldowns[user_id]:
        remaining = int((user_cooldowns[user_id] - now).total_seconds())
        await callback.answer(f"⏳ Подожди {remaining} сек. до следующего сигнала.", show_alert=True)
        return

    # Устанавливаем кулдаун
    user_cooldowns[user_id] = now + timedelta(minutes=5)

    # Заглушка
    msg = await callback.message.answer("⏳ Подготовка сигнала...")
    await asyncio.sleep(5)
    await msg.delete()

    # Генерация сигнала
    user = user_data.get(user_id, {})
    pair = user.get("pair", "USD/JPY OTC")
    tf = random.choice(timeframes)
    budget = random.choice(budget_options)
    direction = random.choice(directions)
    send_time = (datetime.utcnow() + timedelta(hours=5, minutes=2)).strftime("%H:%M")

    signal_text = (
        f"Пара: *{pair}*\n"
        f"Таймфрейм: *{tf}*\n"
        f"Время: *{send_time}*\n"
        f"Бюджет: *{budget}*\n"
        f"Направление: *{direction}*"
    )

    btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📩 ПОЛУЧИТЬ СИГНАЛ", callback_data="get_signal")]]
    )

    await callback.message.answer(signal_text, reply_markup=btn)


async def scheduled_signals():
    while True:
        now = datetime.utcnow() + timedelta(hours=5)
        hour = now.hour
        if 8 <= hour < 18:
            wait = random.randint(60*60, 3*60*60)
        elif 19 <= hour <= 23:
            wait = 60*60
        else:
            await asyncio.sleep(60)
            continue

        for uid, data in user_data.items():
            if "pair" in data:
                pair = random.choice(pairs)
                tf = random.choice(timeframes)
                budget = random.choice(budget_options)
                direction = random.choice(directions)
                send_time = (datetime.utcnow() + timedelta(hours=5, minutes=2)).strftime("%H:%M")

                text = (
                    f"Пара: *{pair}*\n"
                    f"Таймфрейм: *{tf}*\n"
                    f"Время: *{send_time}*\n"
                    f"Бюджет: *{budget}*\n"
                    f"Направление: *{direction}*"
                )

                btn = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="📩 ПОЛУЧИТЬ СИГНАЛ", callback_data="get_signal")]]
                )

                try:
                    await bot.send_message(uid, text, reply_markup=btn)
                except:
                    continue

        await asyncio.sleep(wait)

async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(scheduled_signals())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
