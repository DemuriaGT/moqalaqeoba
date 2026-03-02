from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import json
import random
import copy
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_FILES = {
    "history": "questions_history.json",
    "law": "questions_law.json",
    "language": "questions_language.json"
}

all_questions = {}

def load_all_data():
    for subject, filename in DATA_FILES.items():
        if os.path.exists(filename):
            with open(filename, encoding="utf-8") as f:
                data = json.load(f)
                # Делаем ID уникальными: добавляем префикс предмета
                for q in data:
                    q["real_id"] = f"{subject}_{q['id']}"
                    q["subject_key"] = subject
                all_questions[subject] = data
            print(f"✅ Загружено: {subject} ({len(all_questions[subject])} вопр.)")
        else:
            all_questions[subject] = []

load_all_data()

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
    return output

@app.post("/submit/{subject}")
def submit_test(subject: str, payload: dict):
    user_answers = payload.get("answers", {})
    score = 0
    mistakes = []
    stats = {"history": 0, "law": 0, "language": 0}

    # Создаем плоский словарь для моментального поиска по уникальному ID
    lookup = {}
    for s in all_questions:
        for q in all_questions[s]:
            lookup[q["real_id"]] = q

    for qid, ans in user_answers.items():
        if qid in lookup:
            original = lookup[qid]
            if ans == original["correct"]:
                score += 1
                cat = original["subject_key"]
                if cat in stats: stats[cat] += 1
            else:
                mistakes.append({
                    "question": original["question"],
                    "your_answer": ans,
                    "correct_answer": original["correct"],
                    "options": original["options"],
                    "subject": original["subject_key"]
                })

    return {"score": score, "total": len(user_answers), "mistakes": mistakes, "stats": stats}

@app.get("/")
def read_index():
    return FileResponse("static/index.html")
    
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
