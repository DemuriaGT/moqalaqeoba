import pdfplumber, json, re

def parse():
    questions = []
    current = None
    last_key = None
    with pdfplumber.open("ტესტები_სამართლის_ძირითად_საფუძვლებშილი.pdf") as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            for line in (text or "").split("\n"):
                line = line.strip()
                if re.match(r"^\d+\.", line):
                    current = {"id": len(questions)+1, "question": line.split(".", 1)[1].strip(), "options": {}, "correct": None}
                    last_key = None
                elif re.match(r"^[აბგდ]\)", line) and current:
                    last_key = line[0]
                    current["options"][last_key] = line[2:].strip()
                elif "სწორი" in line and "პასუხი" in line and current:
                    m = re.search(r"([აბგდ])", line)
                    if m:
                        current["correct"] = {"ა":"A","ბ":"B","გ":"C","დ":"D"}[m.group(1)]
                        current["options"] = { ({"ა":"A","ბ":"B","გ":"C","დ":"D"}[k]): v for k, v in current["options"].items() }
                        questions.append(current)
                        current = None
                elif current and last_key:
                    current["options"][last_key] += " " + line
                elif current:
                    current["question"] += " " + line

    with open("questions_law.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Право: {len(questions)} вопр.")

parse()