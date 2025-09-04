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
import sqlite3

TOKEN = "8160440178:AAENyedvsEdYdxkAnePFE8SeofMUGbyag_c"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher(storage=MemoryStorage())

user_cooldowns = {}  # user_id: datetime

class Form(StatesGroup):
    waiting_for_id = State()
    waiting_for_type = State()
    waiting_for_pair = State()
    ready_for_signals = State()

# ================== DB ==================

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        pair TEXT
    )
    """)
    conn.commit()
    conn.close()

def save_pair(user_id: int, pair: str):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO users (user_id, pair) VALUES (?, ?)", (user_id, pair))
    conn.commit()
    conn.close()

def get_pair(user_id: int) -> str | None:
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT pair FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# ================== Пары ==================

otc_pairs = [
    "EUR/USD OTC", "USD/CHF OTC", "AUD/USD OTC", "Gold OTC",
    "AUD/CAD OTC", "AUD/CHF OTC", "AUD/JPY OTC", "AUD/NZD OTC",
    "CAD/CHF OTC", "CAD/JPY OTC", "CHF/JPY OTC"
]
real_pairs = [
    "EUR/USD", "AUD/USD", "Gold", "AUD/CAD", "AUD/JPY", "CAD/JPY"
]
index_pairs = [
    "Compound Index", "Asia Composite Index", "Crypto Composite Index"
]

all_pairs = otc_pairs + real_pairs + index_pairs

timeframes = ["1 minuto"] * 7 + ["3 minutos"] * 2 + ["15 minutos"]
budget_options = ["10% del banco", "15% del banco", "20% del banco"]
directions = ["📈 Arriba", "📉 Abajo"]

# ================== Клавиатуры ==================

def get_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕹 Pares OTC", callback_data="type_otc")],
        [InlineKeyboardButton(text="📈 Parejas reales", callback_data="type_real")],
        [InlineKeyboardButton(text="📊 Índices", callback_data="type_index")]
    ])

def get_pairs_keyboard(pairs):
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=p, callback_data=f"pair:{p}")] for p in pairs] +
                        [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_types")]]
    )

# ================== Логика ==================

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await message.answer("👋 ¡Hola! Por favor, envíame tu ID de cuenta.")
    await state.set_state(Form.waiting_for_id)

@dp.message(Form.waiting_for_id)
async def process_id(message: Message, state: FSMContext):
    await message.answer(
        "✅ ID aceptado. Ahora seleccione el tipo de par de divisas:", 
        reply_markup=get_type_keyboard()
    )
    await state.set_state(Form.waiting_for_type)

@dp.callback_query(F.data == "type_otc")
async def show_otc_pairs(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Seleccione el par de divisas OTC:", reply_markup=get_pairs_keyboard(otc_pairs))
    await state.set_state(Form.waiting_for_pair)

@dp.callback_query(F.data == "type_real")
async def show_real_pairs(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Seleccione un par de divisas real:", reply_markup=get_pairs_keyboard(real_pairs))
    await state.set_state(Form.waiting_for_pair)

@dp.callback_query(F.data == "type_index")
async def show_index_pairs(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Seleccionar índice:", reply_markup=get_pairs_keyboard(index_pairs))
    await state.set_state(Form.waiting_for_pair)

@dp.callback_query(F.data == "back_to_types")
async def back_to_type_selection(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Seleccione el tipo de pares de divisas:", reply_markup=get_type_keyboard())
    await state.set_state(Form.waiting_for_type)

@dp.callback_query(F.data.startswith("pair:"))
async def select_pair(callback: CallbackQuery, state: FSMContext):
    await callback.answer()  # подтверждаем клик, чтобы не дублировалось

    pair = callback.data.split(":", 1)[1]
    uid = callback.from_user.id

    # сохраняем пару в БД
    save_pair(uid, pair)

    btn = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 RECIBIR SEÑAL", callback_data="get_signal")],
            [InlineKeyboardButton(text="🔙 Atrás", callback_data="back_to_types")]
        ]
    )

    await callback.message.answer(
        f"Gran pareja: {pair}\nListo para enviar señal. 👇",
        reply_markup=btn
    )
    await state.set_state(Form.ready_for_signals)

@dp.callback_query(F.data == "get_signal")
async def send_signal(callback: CallbackQuery):
    user_id = callback.from_user.id
    now = datetime.now()

    cooldown_until = user_cooldowns.get(user_id)
    if cooldown_until:
        remaining = (cooldown_until - now).total_seconds()
        if remaining > 0:
            minutes = int(remaining) // 60
            seconds = int(remaining) % 60
            await callback.answer(
                f"⏳ Espera {minutes}min {seconds}seg hasta la próxima señal",
                show_alert=True
            )
            return

    # кулдаун 5 мин
    user_cooldowns[user_id] = now + timedelta(minutes=5)

    msg = await callback.message.answer("⏳ Preparando señal...")
    await asyncio.sleep(5)
    await msg.delete()

    pair = get_pair(user_id)
    tf = random.choice(timeframes)
    budget = random.choice(budget_options)
    direction = random.choice(directions)

    signal_text = (
        f"Par: *{pair}*\n"
        f"Periodo de tiempo: *{tf}*\n"
        f"Presupuesto: *{budget}*\n"
        f"Dirección: *{direction}*"
    )

    btn = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📩 RECIBIR SEÑAL", callback_data="get_signal")],
            [InlineKeyboardButton(text="🔙 Atrás", callback_data="back_to_types")]
        ]
    )

    await callback.message.answer(signal_text, reply_markup=btn)

# ================== Плановые сигналы ==================

async def scheduled_signals():
    while True:
        now = datetime.utcnow() - timedelta(hours=5)
        hour = now.hour
        if 8 <= hour < 18:
            wait = 3*60*60
        elif 18 <= hour <= 23:
            wait = 30*60
        else:
            await asyncio.sleep(60)
            continue

        for uid in []:  # пока не трогаем, пусть random
            pass

        await asyncio.sleep(wait)

# ================== MAIN ==================

async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()  # инициализация базы
    asyncio.create_task(scheduled_signals())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
