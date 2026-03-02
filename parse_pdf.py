import pdfplumber
import json
import re

def parse_test_file(pdf_path, output_json):
    questions = []
    current_question = None
    last_option_key = None

    def flush_question(q_list, q_obj):
        if q_obj and len(q_obj["options"]) == 4 and q_obj["correct"]:
            # Конвертируем грузинские буквы в латиницу
            geo_to_lat = {"ა": "A", "ბ": "B", "გ": "C", "დ": "D", "১": "A"} # Добавлена поддержка символа ১
            q_obj["options"] = {geo_to_lat.get(k, k): v for k, v in q_obj["options"].items()}
            q_list.append(q_obj)

    print(f"--- Обработка: {pdf_path} ---")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text: continue

                for line in text.split("\n"):
                    line = line.strip()
                    if not line: continue

                    # 1. Поиск номера вопроса (1. или I.1.1. или 1.1.1.)
                    # Исключаем строки, которые являются просто ответами (содержат тире и букву в конце)
                    if re.match(r"^(?:[IVX]+\.)?\d+(?:\.\d+)*\.", line) and not re.search(r"-\s*[აბგდ১]\)$", line):
                        flush_question(questions, current_question)
                        parts = line.split(".", 1)
                        # Для сложных номеров типа I.1.1 берем последнюю часть как ID или весь текст
                        q_text = parts[1].strip() if len(parts) > 1 else ""
                        
                        current_question = {
                            "id": len(questions) + 1, # Используем порядковый номер для надежности
                            "question": q_text,
                            "options": {},
                            "correct": None
                        }
                        last_option_key = None

                    # 2. Варианты ответов (ა), ბ), გ), დ) или ১))
                    elif re.match(r"^[აბგდ১]\)", line) and current_question:
                        key = "ა" if line[0] == "১" else line[0]
                        current_question["options"][key] = line[2:].strip()
                        last_option_key = key

                    # 3. Поиск правильного ответа (два формата)
                    elif current_question:
                        # Формат 1: "სწორი პასუხი: ბ"
                        # Формат 2: "1.1.1. - ბ)"
                        ans_match = re.search(r"(?:სწორი\s+პასუხი[:\s]+|[\d.]+\s*-\s*)([აბგდ১])(?:\)|$)", line)
                        if ans_match:
                            geo_letter = "ა" if ans_match.group(1) == "১" else ans_match.group(1)
                            current_question["correct"] = {"ა":"A","ბ":"B","გ":"C","დ":"D"}[geo_letter]
                            last_option_key = None
                        
                        # 4. Продолжение текста
                        elif last_option_key:
                            current_question["options"][last_option_key] += " " + line
                        else:
                            current_question["question"] += " " + line

        flush_question(questions, current_question)
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False, indent=2)
        print(f"Готово! Сохранено вопросов: {len(questions)}\n")

    except Exception as e:
        print(f"Ошибка в {pdf_path}: {e}")

files_to_process = [
    ("ტესტები_საქართველოს_ისტორიაში.pdf", "questions_history.json"),
    ("ტესტები_სამართლის_ძირითად_საფუძვლებშილი.pdf", "questions_law.json"),
    ("ტესტები-ქართულ-ენაში.pdf", "questions_language.json")
]

if __name__ == "__main__":
    for pdf, js in files_to_process:
        parse_test_file(pdf, js)