import random
import asyncio
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

API_TOKEN = "8266658627:AAEZeEYaZ7NdIGKtLelw_RCv01edftra6tc"  # 🔹 сюда вставь свой токен

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- БД ---
conn = sqlite3.connect("users.db")
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    count INTEGER DEFAULT 0,
    reset_time TEXT,
    end_time TEXT
)
""")
conn.commit()


def get_user(uid):
    cur.execute("SELECT count, reset_time, end_time FROM users WHERE user_id=?", (uid,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, count, reset_time, end_time) VALUES (?, ?, ?, ?)", (uid, 0, None, None))
        conn.commit()
        return 0, None, None
    return row


def update_user(uid, count=None, reset_time=None, end_time=None):
    if count is not None:
        cur.execute("UPDATE users SET count=? WHERE user_id=?", (count, uid))
    if reset_time is not None:
        cur.execute("UPDATE users SET reset_time=? WHERE user_id=?", (reset_time, uid))
    if end_time is not None:
        cur.execute("UPDATE users SET end_time=? WHERE user_id=?", (end_time, uid))
    conn.commit()


# --- Главное меню ---
main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton("Demo versiya"), KeyboardButton("Full versiya"))


# --- Генерация прогнозов ---
def generate_predictions(return_end=False):
    now = datetime.now()
    times, coef = [], []
    for offset in [9, 12, 15, 17, 19]:
        t = now + timedelta(minutes=offset)
        x = f"1.{random.randint(22, 35)}x"
        times.append(t)
        coef.append(x)

    result = "\n".join([f"Soat {times[i].strftime('%H:%M')} da kiring, {coef[i]} da oling ✅" for i in range(5)])

    if return_end:
        return result, times[-1]
    return result


# --- /start ---
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("Assalomu alaykum!\nVersiyani tanlang 👇", reply_markup=main_kb)


# --- Demo ---
@dp.message_handler(lambda m: m.text == "Demo versiya")
async def demo(msg: types.Message):
    uid = msg.from_user.id
    count, reset_time, end_time = get_user(uid)

    # если уже в демо процессе
    if count > 0 and reset_time is None:
        await msg.answer("Siz demo versiyani allaqachon boshlagansiz ✅\n\"Yana\" tugmasidan foydalaning.")
        return

    # если есть блокировка 24ч
    if reset_time:
        reset_time_dt = datetime.fromisoformat(reset_time)
        if datetime.now() < reset_time_dt:
            await msg.answer("Demo versiya tugadi, 24 soatdan keyin yana xarakat qiling yoki Full versiyani sotib oling")
            return

    # новый запуск
    update_user(uid, count=0, reset_time=None, end_time=None)

    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Boshlash", callback_data="boshlash"))
    await msg.answer(
        "Har bir etilgan soatda kirib, past uchishlardan keyin (past uchish deganda boshida aviatorga kirib tepadi "
        "Bo'lim tarixini kuzatasiz yani 1.00-1.30x atrofida 2-3 marta tez uchib ketgandan keyin siz 1 marta tiking)\n\n"
        "10-20 mingdan tiking va etilgan songa yutuqni oling 🚀",
        reply_markup=kb
    )


# --- Boshlash ---
@dp.callback_query_handler(lambda c: c.data == "boshlash")
async def start_demo(call: types.CallbackQuery):
    uid = call.from_user.id
    count, reset_time, _ = get_user(uid)

    if count >= 5:
        new_reset = (datetime.now() + timedelta(hours=24)).isoformat()
        update_user(uid, reset_time=new_reset)
        await call.message.answer("Demo versiya tugadi, 24 soatdan keyin yana xarakat qiling yoki Full versiyani sotib oling")
        return

    text, end_time = generate_predictions(return_end=True)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Yana", callback_data="yana"))
    await call.message.answer(text, reply_markup=kb)
    update_user(uid, count=count+1, end_time=end_time.isoformat())


# --- Yana ---
@dp.callback_query_handler(lambda c: c.data == "yana")
async def next_demo(call: types.CallbackQuery):
    uid = call.from_user.id
    count, reset_time, end_time = get_user(uid)

    if count >= 5:
        new_reset = (datetime.now() + timedelta(hours=24)).isoformat()
        update_user(uid, reset_time=new_reset, end_time=None)
        await call.message.answer("Demo versiya tugadi, 24 soatdan keyin yana xarakat qiling yoki Full versiyani sotib oling")
        return

    # проверка времени
    if end_time:
        end_time_dt = datetime.fromisoformat(end_time)
        if datetime.now() < end_time_dt:
            await call.message.answer(f"Ushbu habardan foydalaning va {end_time_dt.strftime('%H:%M')} dan keyin \"yana\" tugmasini bosishingiz mumkun")
            return

    text, new_end = generate_predictions(return_end=True)
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Yana", callback_data="yana"))
    await call.message.answer(text, reply_markup=kb)
    update_user(uid, count=count+1, end_time=new_end.isoformat())


# --- Full ---
@dp.message_handler(lambda m: m.text == "Full versiya")
async def full(msg: types.Message):
    kb = InlineKeyboardMarkup().add(InlineKeyboardButton("To'ladim", callback_data="toladim"))
    await msg.answer(
        "Full versiya narxi 500.000 Sum.\n"
        "Sotib olish uchun @smilebroken bilan bog'lanishingiz zarur. Admin, sizga to'lov uchun karta raqamini tashlaydi. To'lovni amalga oshirganingizdan so'ng 'To'ladim' tugmasini bosing va bot full versiyaga o'tadi.",
        reply_markup=kb
    )


@dp.callback_query_handler(lambda c: c.data == "toladim")
async def paid(call: types.CallbackQuery):
    await call.message.answer("To'lov tekshirilmoqda... Tez orada sizga Full botni ochib beramiz.")


# --- авто-сброс demo через 24ч ---
async def check_demo_reset():
    while True:
        now = datetime.now()
        cur.execute("SELECT user_id, reset_time FROM users WHERE reset_time IS NOT NULL")
        rows = cur.fetchall()
        for uid, reset_time in rows:
            reset_time_dt = datetime.fromisoformat(reset_time)
            if now >= reset_time_dt:
                update_user(uid, count=0, reset_time=None, end_time=None)
                kb = InlineKeyboardMarkup().add(InlineKeyboardButton("Boshlash", callback_data="boshlash"))
                try:
                    await bot.send_message(uid, "Limit tugadi, yana Demo versiyadan foydalanishungiz mumkin", reply_markup=kb)
                except:
                    pass
        await asyncio.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.create_task(check_demo_reset())
    executor.start_polling(dp, skip_updates=True)
