import asyncio
import json
import random
import os
import copy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
app = FastAPI()
TOKEN = os.getenv("BOT_TOKEN") # Берем токен из настроек Render
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния для бота
class QuizState(StatesGroup):
    working = State()

# Конфигурация файлов (общая для сайта и бота)
DATA_FILES = {
    "history": "questions_history.json",
    "law": "questions_law.json",
    "language": "questions_language.json"
}

all_questions = {}

# Загрузка данных (общая функция)
def load_all_data():
    for subject, filename in DATA_FILES.items():
        if os.path.exists(filename):
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
                for q in data:
                    q["real_id"] = f"{subject}_{q['id']}"
                    q["subject_key"] = subject
                all_questions[subject] = data
    print("✅ Все данные для сайта и бота загружены")

load_all_data()

# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---
letter_to_index = {"A": 0, "B": 1, "C": 2, "D": 3}

def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🇬🇪 Грузинский язык")
    builder.button(text="📜 История")
    builder.button(text="⚖️ Право")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите тему для теста:", reply_markup=main_menu_kb())

@dp.message(F.text.in_({"🇬🇪 Грузинский язык", "📜 История", "⚖️ Право"}))
async def start_quiz(message: types.Message, state: FSMContext):
    subject_map = {"🇬🇪 Грузинский язык": "language", "📜 История": "history", "⚖️ Право": "law"}
    key = subject_map[message.text]
    
    questions_pool = random.sample(all_questions[key], min(len(all_questions[key]), 10))
    await state.update_data(questions=questions_pool, current_idx=0, score=0)
    await state.set_state(QuizState.working)
    await send_next_question(message.from_user.id, state)

async def send_next_question(user_id: int, state: FSMContext):
    data = await state.get_data()
    questions = data.get('questions', [])
    idx = data.get('current_idx', 0)

    if idx < len(questions):
        q = questions[idx]
        await bot.send_poll(
            chat_id=user_id,
            question=f"[{idx+1}/10] {q['question']}"[:300],
            options=list(q["options"].values()),
            type='quiz',
            correct_option_id=letter_to_index[q["correct"]],
            is_anonymous=False
        )
    else:
        await bot.send_message(user_id, f"✅ Тест окончен! Результат: {data['score']}/10", reply_markup=main_menu_kb())
        await state.clear()

@dp.poll_answer()
async def handle_answer(poll_answer: types.PollAnswer, state: FSMContext):
    data = await state.get_data()
    if not data: return
    
    correct_idx = letter_to_index[data['questions'][data['current_idx']]["correct"]]
    new_score = data['score'] + (1 if poll_answer.option_ids[0] == correct_idx else 0)
    
    await state.update_data(current_idx=data['current_idx'] + 1, score=new_score)
    await send_next_question(poll_answer.user.id, state)

# --- ЛОГИКА FASTAPI (ТВОЙ КОД) ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def root():
    return {
        "status": "working",
        "message": "Система тестирования (Сайт + Бот) запущена!",
        "bot_username": "@moqalaqeoba_bot"
    }
    
@app.get("/start/{subject}")
def start_test(subject: str):
    source = []
    if subject == "mix":
        for s in DATA_FILES.keys():
            if all_questions[s]:
                source.extend(random.sample(all_questions[s], min(len(all_questions[s]), 10)))
        random.shuffle(source)
    else:
        if subject not in all_questions:
            raise HTTPException(status_code=404, detail="Subject not found")
        source = random.sample(all_questions[subject], min(len(all_questions[subject]), 10))
    
    # Клонируем и подменяем ID на уникальный real_id, скрываем правильный ответ
    output = []
    for q in source:
        q_copy = copy.deepcopy(q)
        q_copy["id"] = q_copy["real_id"] # Фронтенд будет работать с уникальной строкой
        q_copy.pop("correct", None)
        output.append(q_copy)
    return {"status": "ok", "message": "API работает вместе с ботом"}

# --- ЗАПУСК ВСЕГО ВМЕСТЕ ---
@app.on_event("startup")
async def on_startup():
    # Запускаем бота в фоновом режиме при старте FastAPI
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)



