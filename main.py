import asyncio
import json
import random
import os
import copy
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
# Рекомендую в Render добавить переменную BOT_TOKEN, но если нет — вставь токен сюда
TOKEN = os.getenv("BOT_TOKEN", "8269266664:AAGEt3cEHfQxRrgQthPAp_PVUmGr_rCrt6w")

app = FastAPI()
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния бота
class QuizState(StatesGroup):
    working = State()

# Конфигурация данных (единая для всех)
DATA_FILES = {
    "history": "questions_history.json",
    "law": "questions_law.json",
    "language": "questions_language.json"
}

all_questions = {}
letter_to_index = {"A": 0, "B": 1, "C": 2, "D": 3}

def load_all_data():
    for subject, filename in DATA_FILES.items():
        if os.path.exists(filename):
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
                for q in data:
                    q["real_id"] = f"{subject}_{q['id']}"
                    q["subject_key"] = subject
                all_questions[subject] = data
            print(f"✅ Загружено для всех: {subject} ({len(all_questions[subject])} вопр.)")
        else:
            all_questions[subject] = []

load_all_data()

# --- ЛОГИКА КЛАВИАТУР БОТА ---
def main_menu_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🇬🇪 Грузинский язык (10 вопросов)")
    builder.button(text="📜 История (10 вопросов)")
    builder.button(text="⚖️ Право (10 вопросов)")
    builder.button(text="🔥 Все темы сразу (30 вопросов)")
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

def cancel_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔙 Прервать тест и выйти в меню")
    return builder.as_markup(resize_keyboard=True)

# --- ОБРАБОТЧИКИ БОТА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выберите тему экзамена для тренировки:", reply_markup=main_menu_kb())

@dp.message(F.text == "🔙 Прервать тест и выйти в меню")
async def process_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Тест прерван. Вы вернулись в меню.", reply_markup=main_menu_kb())

@dp.message(F.text.in_({
    "🇬🇪 Грузинский язык (10 вопросов)", 
    "📜 История (10 вопросов)", 
    "⚖️ Право (10 вопросов)", 
    "🔥 Все темы сразу (30 вопросов)"
}))
async def start_quiz(message: types.Message, state: FSMContext):
    if "Грузинский" in message.text:
        pool = random.sample(all_questions["language"], min(len(all_questions["language"]), 10))
    elif "История" in message.text:
        pool = random.sample(all_questions["history"], min(len(all_questions["history"]), 10))
    elif "Право" in message.text:
        pool = random.sample(all_questions["law"], min(len(all_questions["law"]), 10))
    else: # Все темы
        q1 = random.sample(all_questions["language"], min(len(all_questions["language"]), 10))
        q2 = random.sample(all_questions["history"], min(len(all_questions["history"]), 10))
        q3 = random.sample(all_questions["law"], min(len(all_questions["law"]), 10))
        pool = q1 + q2 + q3
        random.shuffle(pool)

    await state.update_data(questions=pool, current_idx=0, score=0)
    await state.set_state(QuizState.working)
    await message.answer(f"Начинаем! Вопросов: {len(pool)}", reply_markup=types.ReplyKeyboardRemove())
    await send_next_question(message.from_user.id, state)

async def send_next_question(user_id: int, state: FSMContext):
    data = await state.get_data()
    questions = data.get('questions', [])
    idx = data.get('current_idx', 0)

    if idx < len(questions):
        q = questions[idx]
        raw_options = q["options"]
        options_list = list(raw_options.values())
        correct_id = letter_to_index[q["correct"]]
        max_opt_len = max(len(opt) for opt in options_list)

        if max_opt_len > 100:
            full_text = f"<b>Вопрос {idx+1}/{len(questions)}:</b>\n{q['question']}\n\n"
            for L, txt in raw_options.items():
                full_text += f"<b>{L}:</b> {txt}\n"
            await bot.send_message(user_id, full_text, parse_mode='HTML', reply_markup=cancel_kb())
            poll_opts = [f"Вариант {L}" for L in raw_options.keys()]
        else:
            poll_opts = options_list

        await bot.send_poll(
            chat_id=user_id,
            question=f"Выберите ответ (Вопрос {idx+1}):" if max_opt_len > 100 else f"[{idx+1}/{len(questions)}] {q['question']}"[:300],
            options=poll_opts,
            type='quiz',
            correct_option_id=correct_id,
            is_anonymous=False,
            reply_markup=cancel_kb()
        )
    else:
        score = data.get('score', 0)
        await bot.send_message(user_id, f"✅ Тест завершен!\nРезультат: {score} из {len(questions)}", reply_markup=main_menu_kb())
        await state.clear()

@dp.poll_answer()
async def handle_poll_answer(poll_answer: types.PollAnswer, state: FSMContext):
    data = await state.get_data()
    if not data: return
    
    correct_id = letter_to_index[data['questions'][data['current_idx']]["correct"]]
    new_score = data['score'] + (1 if poll_answer.option_ids[0] == correct_id else 0)
    
    await state.update_data(current_idx=data['current_idx'] + 1, score=new_score)
    await send_next_question(poll_answer.user.id, state)

# --- ЛОГИКА САЙТА (FASTAPI) ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

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
    
    output = []
    for q in source:
        q_copy = copy.deepcopy(q)
        q_copy["id"] = q_copy["real_id"]
        q_copy.pop("correct", None)
        output.append(q_copy)
    return output

@app.post("/submit/{subject}")
def submit_test(subject: str, payload: dict):
    user_answers = payload.get("answers", {})
    score, mistakes = 0, []
    stats = {"history": 0, "law": 0, "language": 0}
    
    lookup = {q["real_id"]: q for s in all_questions for q in all_questions[s]}

    for qid, ans in user_answers.items():
        if qid in lookup:
            orig = lookup[qid]
            if ans == orig["correct"]:
                score += 1
                stats[orig["subject_key"]] += 1
            else:
                mistakes.append({"question": orig["question"], "your_answer": ans, "correct_answer": orig["correct"], "options": orig["options"], "subject": orig["subject_key"]})
    return {"score": score, "total": len(user_answers), "mistakes": mistakes, "stats": stats}

# --- ЗАПУСК ---
@app.on_event("startup")
async def on_startup():
    # Запускаем бота как фоновую задачу
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    import uvicorn
    # Render сам подставит нужный порт
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
