import pdfplumber, json, re

def parse():
    questions = []
    current = None
    with pdfplumber.open("ტესტები_საქართველოს_ისტორიაში.pdf") as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            for line in text.split("\n"):
                line = line.strip()
                if re.match(r"^\d+\.", line):
                    current = {"id": len(questions)+1, "question": line.split(".", 1)[1].strip(), "options": {}, "correct": None}
                elif re.match(r"^[აბგდ]\)", line) and current:
                    current["options"][line[0]] = line[2:].strip()
                elif "სწორი პასუხი" in line and current:
                    match = re.search(r"([აბგდ])", line.split(":")[1])
                    if match:
                        current["correct"] = {"ა":"A","ბ":"B","გ":"C","დ":"D"}[match.group(1)]
                        # Конвертируем ключи и сохраняем
                        current["options"] = { ({"ა":"A","ბ":"B","გ":"C","დ":"D"}[k]): v for k, v in current["options"].items() }
                        questions.append(current)
                        current = None
    with open("questions_history.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"История: {len(questions)} вопр.")

parse()