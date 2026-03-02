import pdfplumber
import json
import re

def parse():
    questions = []
    current = None
    last_key = None
    
    # Шаблон для поиска номера вопроса (например, I.1.1. или 1.1.1.)
    question_pattern = r"^(?:[IVX]+\.)?\d+(?:\.\d+)*\."

    with pdfplumber.open("ტესტები-ქართულ-ენაში.pdf") as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 1. Начало нового вопроса
                # Проверяем, что строка начинается с номера и это не строка с ответом (в которой есть тире и буква в конце)
                if re.match(question_pattern, line) and not (("-" in line) and re.search(r"[აბგდ১]\)$", line)):
                    current = {
                        "id": len(questions) + 1,
                        "question": line,
                        "options": {},
                        "correct": None
                    }
                    last_key = None

                # 2. Варианты ответов (а, б, г, д или специфический символ ১)
                elif re.match(r"^[აბგდ১]\)", line) and current:
                    raw_key = line[0]
                    # Если попался символ '১', считаем его как 'ა' (A)
                    last_key = "ა" if raw_key == "১" else raw_key
                    current["options"][last_key] = line[2:].strip()

                # 3. Поиск правильного ответа (формат: 1.1.1. - ბ))
                elif "-" in line and re.search(r"[აბგდ১]\)$", line) and current:
                    match = re.search(r"([აბგდ১])\)$", line)
                    if match:
                        ans_letter = "ა" if match.group(1) == "১" else match.group(1)
                        # Сразу готовим маппинг в латиницу для фронтенда
                        geo_to_lat = {"ა": "A", "ბ": "B", "გ": "C", "დ": "D"}
                        current["correct"] = geo_to_lat[ans_letter]
                        
                        # Конвертируем ключи вариантов в A, B, C, D
                        formatted_options = {}
                        for k, v in current["options"].items():
                            formatted_options[geo_to_lat.get(k, k)] = v
                        current["options"] = formatted_options
                        
                        questions.append(current)
                        current = None
                        last_key = None

                # 4. Сбор текста (продолжение вопроса или варианта)
                elif current:
                    if last_key:
                        # Если мы уже внутри варианта, дописываем текст туда
                        current["options"][last_key] += " " + line
                    else:
                        # Если варианты еще не начались, значит это подвопрос или текст с пропуском
                        current["question"] += "\n" + line

    with open("questions_language.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    
    print(f"Тесты по языку: успешно спарсено {len(questions)} вопросов.")

if __name__ == "__main__":
    parse()