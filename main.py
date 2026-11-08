import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

# --- НАСТРОЙКИ (ВСТАВЬ СВОИ ДАННЫЕ) ---
BOT_TOKEN = "ТВОЙ_ТОКЕН_ОТ_BOTFATHER" 
WEB_APP_URL = "https://твой-бот.bothost.tech" # Ссылка на домен, который даст BotHost
PORT = 3000

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

def get_player(user_id):
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, level, xp FROM players WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO players (user_id) VALUES (?)", (user_id,))
        conn.commit()
        row = (0.0, 1, 0)
    conn.close()
    return row

def update_player(user_id, balance_add, xp_add):
    conn = sqlite3.connect("game.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, level, xp FROM players WHERE user_id = ?", (user_id,))
    balance, level, xp = cursor.fetchone()
    
    new_balance = balance + balance_add
    new_xp = xp + xp_add
    new_level = level
    
    if new_xp >= 100:
        new_xp -= 100
        new_level += 1
    
    cursor.execute("UPDATE players SET balance = ?, level = ?, xp = ? WHERE user_id = ?", 
                   (new_balance, new_level, new_xp, user_id))
    conn.commit()
    conn.close()
    return new_balance, new_level, new_xp

# --- ВЕБ-СЕРВЕР (FASTAPI) ---
app = FastAPI()
app.mount("/photos", StaticFiles(directory="photos"), name="photos")

class ClickData(BaseModel):
    user_id: int

@app.get("/")
async def get_index():
    with open("index.html", "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/click")
async def process_click(data: ClickData):
    new_balance, new_level, new_xp = update_player(data.user_id, 0.01, 1)
    return JSONResponse(content={"balance": round(new_balance, 2), "level": new_level, "xp": new_xp})

@app.get("/api/profile")
async def get_profile(user_id: int):
    balance, level, xp = get_player(user_id)
    return JSONResponse(content={"balance": round(balance, 2), "level": level, "xp": xp})

# --- БОТ (AIogram) ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_command(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎮 Открыть игру", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer("Привет! Нажми на кнопку ниже, чтобы открыть игру и начать зарабатывать!", reply_markup=keyboard)

# --- ЗАПУСК ---
async def main():
    init_db()
    config = uvicorn.Config(app, host="0.0.0.0", port=PORT, log_level="info")
    server = uvicorn.Server(config)
    await asyncio.gather(server.serve(), dp.start_polling(bot))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
