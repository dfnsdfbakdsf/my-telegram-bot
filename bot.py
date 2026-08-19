import os
import re
import logging
import subprocess
import shutil
import json
import time
from io import BytesIO
from difflib import SequenceMatcher

import telebot
from telebot import types
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import requests
from googlesearch import search
from fuzzywuzzy import fuzz

# ==================== НАСТРОЙКИ TESSERACT ====================
tesseract_path = shutil.which('tesseract')
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"✅ Tesseract найден по пути: {tesseract_path}")
else:
    possible_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract', '/bin/tesseract']
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Tesseract найден по пути: {path}")
            break
    else:
        print("❌ Tesseract НЕ НАЙДЕН!")

try:
    subprocess.run([pytesseract.pytesseract.tesseract_cmd, '--version'], capture_output=True, check=True)
    print("✅ Tesseract работает")
except Exception as e:
    print(f"❌ Tesseract не отвечает: {e}")

# ==================== ТОКЕН ====================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

bot = telebot.TeleBot(TOKEN)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==================== БАЗА ЗНАНИЙ ====================
knowledge_base = {
    # Математика
    "формулы сокращенного умножения": "(a+b)² = a² + 2ab + b²; (a-b)² = a² - 2ab + b²; a² - b² = (a-b)(a+b)",
    "квадрат суммы": "(a+b)² = a² + 2ab + b²",
    "квадрат разности": "(a-b)² = a² - 2ab + b²",
    "разность квадратов": "a² - b² = (a-b)(a+b)",
    "линейное уравнение": "Уравнение вида ax + b = 0, где a ≠ 0. Решение: x = -b/a",
    "сумма углов треугольника": "180°",
    "свойство смежных углов": "Сумма смежных углов равна 180°",
    
    # Физика
    "скорость": "v = s/t",
    "плотность": "ρ = m/V",
    "сила тяжести": "F = mg",
    "давление": "p = F/S",
    "архимедова сила": "F = ρgV",
    "работа": "A = Fs",
    "мощность": "N = A/t",
    "работа единица измерения": "Джоуль (Дж)",
    "вес тела единица измерения": "Ньютон (Н)",
    "путь единица измерения": "Метр (м)",
    "сила единица измерения": "Ньютон (Н)",
    "масса единица измерения": "Килограмм (кг)",
    "давление единица измерения": "Паскаль (Па)",
    "плотность единица измерения": "кг/м³",
    "энергия единица измерения": "Джоуль (Дж)",
    "мощность единица измерения": "Ватт (Вт)",
    "время единица измерения": "Секунда (с)",
    "температура единица измерения": "Кельвин (К)",
    
    # Химия
    "атом": "Мельчайшая частица химического элемента",
    "молекула": "Мельчайшая частица вещества",
    "валентность": "Способность атомов присоединять другие атомы",
    "оксиды": "Соединения элементов с кислородом",
    "кислоты": "Вещества, содержащие водород и кислотный остаток",
    
    # Биология
    "фотосинтез": "Образование органических веществ на свету",
    "клетка": "Элементарная единица живого",
    "царства живой природы": "Бактерии, Грибы, Растения, Животные",
    
    # География
    "материки": "Евразия, Африка, Северная Америка, Южная Америка, Антарктида, Австралия",
    "океаны": "Тихий, Атлантический, Индийский, Северный Ледовитый, Южный",
    
    # История
    "крещение руси": "988 год",
    "куликовская битва": "1380 год",
    
    # Обществознание
    "конституция": "Основной закон",
    "права ребенка": "Права до 18 лет",
    
    # Английский
    "present simple": "Действие происходит регулярно",
    "past simple": "Действие произошло в прошлом",
    "irregular verbs": "Неправильные глаголы",
    
    # 8 класс
    "теорема пифагора": "c² = a² + b²",
    "площадь треугольника": "S = ½ · a · h",
    "количество теплоты": "Q = cmΔt",
    "дискриминант": "D = b² - 4ac",
    "квадратное уравнение": "ax² + bx + c = 0, где a ≠ 0",
    
    # ===== ИНФОРМАТИКА / ПРЕЗЕНТАЦИИ =====
    "ошибочное утверждение презентация": "Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории",
    "правила оформления презентации": "Используйте не более двух шрифтов, однотонные фоны, минимум анимации, один вид переходов",
    "презентация правила": "1) Однотонные фоны; 2) Не более 2 шрифтов; 3) Минимум анимации; 4) Один вид переходов",
    "как оформить презентацию": "Однотонные фоны, не более 2 шрифтов, минимум анимации, один вид переходов",
    "что нельзя делать в презентации": "Добавлять много анимации на слайды",
    "ошибка в презентации": "Много анимации на слайдах",
}

# ==================== БАЗА ФРАЗОВЫХ ГЛАГОЛОВ ====================
phrasal_verbs = {
    "fall out with": "поссориться с кем-то",
    "fall out": "поссориться, выпасть",
    "fall behind": "отставать",
    "get along with": "ладить с кем-то",
    "get on with": "ладить, продолжать",
    "get over": "оправиться от, пережить",
    "take off": "взлетать, снимать (одежду)",
    "take up": "заниматься (хобби), начинать",
    "look for": "искать",
    "look after": "заботиться, присматривать",
    "look forward to": "ждать с нетерпением",
    "put on": "надевать, включать (свет)",
    "put off": "откладывать, отвлекать",
    "turn on": "включать",
    "turn off": "выключать",
    "come in": "входить",
    "come out": "выходить, появляться",
    "run out of": "заканчиваться",
    "break down": "сломаться, разобрать",
    "break up": "расставаться",
    "give up": "сдаваться, бросать",
    "make up": "выдумывать, мириться",
    "call off": "отменять",
    "carry on": "продолжать",
    "fill in": "заполнять",
    "find out": "узнавать",
    "pick up": "подбирать, забирать",
    "set up": "устанавливать, организовывать",
    "sort out": "разобраться, решить",
    "work out": "решать, тренироваться",
}

# ==================== БАЗА ТЕСТОВ МЭШ ====================
class MESHTestsDatabase:
    def __init__(self):
        self.tests = {}
        self._init_tests()

    def _init_tests(self):
        # Физика 7 класс: Механическая работа
        self.tests["phys_7_001"] = {
            "id": "phys_7_001",
            "subject": "Физика",
            "class": "7",
            "topic": "Механическая работа",
            "questions": [
                {
                    "number": 1,
                    "type": "text",
                    "question": "Два мальчика, соревнуясь в перетягивании каната, тянут его в разные стороны. Один из них, двигаясь равномерно, перетянул канат на себя. Если сравнивать механические работы сил, приложенных к канату, то несмотря на то, что один из мальчиков перетянул его, работы сил, приложенных к канату,",
                    "answer": "равны по модулю",
                    "options": ["равны по модулю", "не равны", "равны по знаку"]
                },
                {
                    "number": 2,
                    "type": "text",
                    "question": "Силы, приложенные к канату,",
                    "answer": "равны",
                    "options": ["равны", "не равны", "противоположны"]
                },
                {
                    "number": 3,
                    "type": "text",
                    "question": "У одного мальчика направление силы, приложенной к канату, совпадает с направлением его",
                    "answer": "перемещения",
                    "options": ["перемещения", "скорости", "ускорения"]
                },
                {
                    "number": 4,
                    "type": "text",
                    "question": "Поскольку перемещения, на которых действуют силы,",
                    "answer": "равны",
                    "options": ["равны", "не равны", "противоположны"]
                },
                {
                    "number": 5,
                    "type": "text",
                    "question": "Работы, совершенные мальчиками, равны по модулю и",
                    "answer": "неравны по знаку",
                    "options": ["неравны по знаку", "равны по знаку", "противоположны"]
                }
            ],
            "full_text": "Прочитайте текст и вставьте пропущенные слова/словосочетания. Два мальчика, соревнуясь в перетягивании каната, тянут его в разные стороны. Один из них, двигаясь равномерно, перетянул канат на себя. Если сравнивать механические работы сил, приложенных к канату, то несмотря на то, что один из мальчиков перетянул его, работы сил, приложенных к канату, равны по модулю. Силы, приложенные к канату, равны. У одного мальчика направление силы, приложенной к канату, совпадает с направлением его перемещения, а у другого – противоположно. Поскольку перемещения, на которых действуют силы, равны, то работы этих сил равны по модулю. В данном случае можно сказать, что работы, совершенные мальчиками, равны по модулю и неравны по знаку.",
            "answers": {"1": "равны по модулю", "2": "равны", "3": "перемещения", "4": "равны", "5": "неравны по знаку"},
            "similarity": 90
        }
        
        # Физика 7 класс: Единицы измерения (соответствие)
        self.tests["phys_7_006"] = {
            "id": "phys_7_006",
            "subject": "Физика",
            "class": "7",
            "topic": "Единицы измерения физических величин",
            "type": "matching",
            "questions": [
                {
                    "number": 1,
                    "type": "matching",
                    "question": "Установите соответствие между физическими величинами и их единицами измерения.",
                    "pairs": {
                        "работа": "Джоуль (Дж)",
                        "вес тела": "Ньютон (Н)",
                        "путь": "Метр (м)",
                        "скорость": "м/с",
                        "масса": "кг",
                        "сила": "Н",
                        "давление": "Па",
                        "плотность": "кг/м³",
                        "энергия": "Дж",
                        "мощность": "Вт",
                        "время": "с",
                        "температура": "К",
                        "сила тока": "А",
                        "напряжение": "В",
                        "сопротивление": "Ом"
                    }
                }
            ],
            "full_text": "Установите соответствие между физическими величинами и их единицами измерения.\n\nработа → Джоуль (Дж)\nвес тела → Ньютон (Н)\nпуть → Метр (м)\nскорость → м/с\nмасса → кг\nсила → Н\nдавление → Па\nплотность → кг/м³",
            "answers": {
                "работа": "Джоуль (Дж)",
                "вес тела": "Ньютон (Н)",
                "путь": "Метр (м)"
            },
            "similarity": 95
        }
        
        # Английский 7: Идиомы
        self.tests["eng_7_002"] = {
            "id": "eng_7_002",
            "subject": "Английский язык",
            "class": "7",
            "topic": "Idioms",
            "questions": [
                {
                    "number": 1,
                    "type": "text",
                    "question": "Forget about the broken vase. It's no use crying over spilt milk.",
                    "answer": "crying over spilt milk",
                    "options": ["crying over spilt milk", "crying over broken glass", "crying over water"]
                },
                {
                    "number": 2,
                    "type": "text",
                    "question": "Look at Billy! He is so cheerful today! He is really on cloud nine.",
                    "answer": "on cloud nine",
                    "options": ["on cloud nine", "down in the dumps", "under the weather"]
                }
            ],
            "similarity": 95
        }
        
        # Русский 7: Предлоги
        self.tests["rus_7_003"] = {
            "id": "rus_7_003",
            "subject": "Русский язык",
            "class": "7",
            "topic": "Правописание производных предлогов",
            "questions": [
                {
                    "number": 1,
                    "type": "text",
                    "question": "Не поехали (в) виду непогоды. Как пишется предлог?",
                    "answer": "раздельно - в виду",
                    "options": ["слитно - ввиду", "раздельно - в виду", "через дефис"]
                },
                {
                    "number": 2,
                    "type": "text",
                    "question": "(В)следствие дождей. Как пишется предлог?",
                    "answer": "слитно - вследствие",
                    "options": ["слитно - вследствие", "раздельно - в следствие"]
                }
            ],
            "similarity": 95
        }
        
        # Русский 7: Окончания
        self.tests["rus_7_001"] = {
            "id": "rus_7_001",
            "subject": "Русский язык",
            "class": "7",
            "topic": "Правописание окончаний существительных",
            "questions": [
                {
                    "number": 1,
                    "type": "text",
                    "question": "В каком примере на месте пропуска пишется буква 'и'?",
                    "answer": "в течении реки",
                    "options": ["по мере продвижения", "в виде исключения", "наподобие шара", "в течении реки"]
                }
            ],
            "similarity": 95
        }
        
        # ===== ИНФОРМАТИКА 7 класс: Оформление презентаций =====
        self.tests["info_7_001"] = {
            "id": "info_7_001",
            "subject": "Информатика",
            "class": "7",
            "topic": "Оформление презентаций",
            "questions": [
                {
                    "number": 1,
                    "type": "text",
                    "question": "Укажите ошибочное утверждение.",
                    "answer": "Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории",
                    "options": [
                        "Отдавайте предпочтение однотонным фонам, это облегчает восприятие представленной на слайде информации",
                        "Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории",
                        "Чтобы выдержать единый стиль презентации, рекомендуется использовать один вид перехода между слайдами",
                        "Используйте не более двух шрифтов: один для заголовков, другой для текста"
                    ]
                }
            ],
            "full_text": "Укажите ошибочное утверждение.\n1. Отдавайте предпочтение однотонным фонам, это облегчает восприятие представленной на слайде информации.\n2. Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории.\n3. Чтобы выдержать единый стиль презентации, рекомендуется использовать один вид перехода между слайдами.\n4. Используйте не более двух шрифтов: один для заголовков, другой для текста.",
            "answers": {
                "1": "Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории"
            },
            "similarity": 95
        }

    def find_test_by_text(self, text):
        if not text:
            return None, 0
        clean_text = text.lower().strip()
        best_match = None
        best_score = 0
        
        for test_id, test_data in self.tests.items():
            # По ID
            test_words = set(test_id.replace('_', ' ').split())
            question_words = set(clean_text.split())
            common = test_words & question_words
            if common:
                score = len(common) / len(test_words) * 100
                if score > best_score:
                    best_score = score
                    best_match = test_data
            
            # По вопросам
            if 'questions' in test_data:
                for q in test_data['questions']:
                    q_text = q.get('question', '').lower()
                    if len(q_text) > 10:
                        ratio = fuzz.partial_ratio(clean_text, q_text)
                        if ratio > best_score and ratio > 40:
                            best_score = ratio
                            best_match = test_data
            
            # По полному тексту
            if 'full_text' in test_data:
                ft = test_data['full_text'].lower()
                ratio = fuzz.partial_ratio(clean_text, ft[:300])
                if ratio > best_score and ratio > 30:
                    best_score = ratio
                    best_match = test_data
        
        # Если не нашли точного совпадения, проверяем по ключевым словам
        if best_score < 50:
            for test_id, test_data in self.tests.items():
                # Проверяем по теме
                if test_data.get('topic', '').lower() in clean_text:
                    return test_data, 80
                # Проверяем по ключевым словам в вопросе
                if 'questions' in test_data:
                    for q in test_data['questions']:
                        q_text = q.get('question', '').lower()
                        # Проверяем, есть ли ключевые слова из вопроса в распознанном тексте
                        words = q_text.split()
                        for word in words:
                            if len(word) > 3 and word in clean_text:
                                return test_data, 70
        
        return best_match, best_score

mesh_db = MESHTestsDatabase()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def preprocess_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        denoised = cv2.medianBlur(binary, 3)
        processed_path = image_path.replace('.jpg', '_processed.jpg')
        cv2.imwrite(processed_path, denoised)
        return processed_path
    except Exception as e:
        logger.error(f"Ошибка предобработки: {e}")
        return image_path

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^\w\s.,;:!?()"\'\-]', '', text)
    return text.strip()

def extract_test_questions(text):
    lines = text.split('\n')
    questions = []
    current_q = ""
    current_opts = []
    in_question = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.search(r'^\d+[.)]\s*', line) or re.search(r'^(Вопрос|Задание)\s*\d+', line, re.I):
            if current_q:
                questions.append({'question': current_q, 'options': current_opts})
            current_q = line
            current_opts = []
            in_question = True
        elif in_question:
            if re.match(r'^[А-Яа-яA-Za-z]\)', line) or re.match(r'^\d+\)', line):
                current_opts.append(line)
            else:
                current_q += " " + line
    
    if current_q:
        questions.append({'question': current_q, 'options': current_opts})
    return questions

def find_answer_in_knowledge(question):
    if not question:
        return None
    q = question.lower().strip()
    q = re.sub(r'[^\w\s?]', '', q)
    q = re.sub(r'\s+', ' ', q).strip()
    
    if q in knowledge_base:
        return knowledge_base[q]
    
    for verb, meaning in phrasal_verbs.items():
        if verb in q:
            return f"{verb} = {meaning}"
    
    best_match = None
    best_score = 0
    for key, value in knowledge_base.items():
        score = fuzz.partial_ratio(q, key)
        if score > best_score and score > 60:
            best_score = score
            best_match = value
    
    return best_match

def find_matching_pairs(text):
    pairs = {}
    match_lines = re.findall(r'([а-яА-Яa-zA-Z\s]+)\s*[→-]\s*([а-яА-Яa-zA-Z\s()]+)', text)
    if match_lines:
        for term, definition in match_lines:
            term_clean = term.strip().lower()
            def_clean = definition.strip()
            if term_clean in ['работа', 'вес тела', 'путь', 'скорость', 'масса', 'сила', 'давление', 'плотность']:
                pairs[term_clean] = def_clean
    return pairs

def find_answer_with_context(question):
    if not question:
        return None
    q = question.lower().strip()
    
    if re.search(r'___|\.\.\.|\([A-Za-z]+\)', q):
        for verb in phrasal_verbs.keys():
            if verb.replace(' ', '') in q.replace(' ', '') or verb in q:
                return verb
        if 'fall' in q and 'with' in q:
            return "out (fall out with = поссориться)"
        if 'get' in q and 'with' in q:
            return "along (get along with = ладить)"
    
    # Проверка на презентации
    if "презентация" in q or "ошибочное утверждение" in q:
        return knowledge_base.get("ошибочное утверждение презентация", None)
    
    kb_answer = find_answer_in_knowledge(question)
    if kb_answer:
        return kb_answer
    
    test_data, sim = mesh_db.find_test_by_text(question)
    if test_data and sim > 30:
        if 'questions' in test_data and test_data['questions']:
            return test_data['questions'][0].get('answer', None)
        if 'answers' in test_data:
            return list(test_data['answers'].values())[0]
    return None

def search_in_internet(query):
    try:
        results = list(search(f"{query} ответ МЭШ", num_results=2, lang='ru'))
        if results:
            return f"🔗 Возможно, ответ: {results[0]}"
    except:
        pass
    return None

def format_full_test_answer(test_data, similarity):
    if not test_data:
        return None
    lines = []
    lines.append(f"🔍 {similarity:.0f}% МЭШ")
    lines.append("")
    lines.append(f"📚 {test_data['subject']} {test_data['class']} класс")
    lines.append(f"📖 Тема: {test_data['topic']}")
    lines.append("")
    
    if 'questions' in test_data:
        for q in test_data['questions']:
            lines.append(f"Вопрос {q.get('number', '?')}: {q.get('question', '')}")
            if q.get('type') == 'matching' and 'pairs' in q:
                lines.append("📋 Соответствия:")
                for term, defin in q['pairs'].items():
                    lines.append(f"  • {term} → {defin}")
            else:
                lines.append(f"✅ Ответ: {q.get('answer', '')}")
                if q.get('options'):
                    lines.append("📋 Варианты:")
                    for opt in q['options']:
                        if opt == q.get('answer', ''):
                            lines.append(f"  • {opt} ✓")
                        else:
                            lines.append(f"  • {opt}")
            lines.append("")
    
    # Добавляем объяснение для презентаций
    if test_data.get('topic') == "Оформление презентаций":
        lines.append("📖 Объяснение:")
        lines.append("Правила оформления презентаций:")
        lines.append("1. Используйте однотонные фоны — облегчает восприятие")
        lines.append("2. Не перегружайте слайды анимацией — отвлекает внимание")
        lines.append("3. Используйте один вид переходов — единый стиль")
        lines.append("4. Не более двух шрифтов — один для заголовков, другой для текста")
        lines.append("")
        lines.append("❌ Ошибочное утверждение:")
        lines.append("«Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории»")
        lines.append("Правильно: анимации должно быть минимум, она не должна отвлекать.")
    
    return '\n'.join(lines)

def format_matching_answer(pairs):
    if not pairs:
        return None
    lines = []
    lines.append("🔍 95% МЭШ")
    lines.append("")
    lines.append("📚 Физика 7 класс")
    lines.append("📖 Тема: Единицы измерения физических величин")
    lines.append("")
    lines.append("📝 Установите соответствие между физическими величинами и их единицами измерения.")
    lines.append("")
    lines.append("✅ Соответствия:")
    for term, defin in pairs.items():
        lines.append(f"  • {term} → {defin}")
    lines.append("")
    lines.append("📖 Объяснение:")
    if "работа" in pairs:
        lines.append("  • Работа (A) измеряется в Джоулях (Дж) — 1 Дж = 1 Н·м")
    if "вес тела" in pairs:
        lines.append("  • Вес тела (P) измеряется в Ньютонах (Н) — это сила")
    if "путь" in pairs:
        lines.append("  • Путь (s) измеряется в Метрах (м) — основная единица длины в СИ")
    return '\n'.join(lines)

def format_individual_answers(questions):
    lines = []
    for idx, q in enumerate(questions, 1):
        ans = find_answer_with_context(q['question'])
        if not ans:
            ans = search_in_internet(q['question']) or "Не удалось найти ответ"
        lines.append(f"📌 Вопрос {idx}: {q['question'][:150]}")
        if q.get('options'):
            lines.append(f"📋 Варианты: {', '.join(q['options'])}")
        lines.append(f"💡 Ответ: {ans}")
        lines.append("")
    return '\n'.join(lines)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📚 Предметы"), types.KeyboardButton("📊 Статистика"))
    markup.add(types.KeyboardButton("🔍 Найти тест"), types.KeyboardButton("❓ Помощь"))
    bot.reply_to(message, 
        "👋 Привет! Я бот для решения тестов МЭШ 7-8 классов.\n\n"
        "📸 Отправь мне фото теста, и я найду ответы!\n"
        "Или просто задай вопрос текстом.", 
        reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message,
        "📚 Как пользоваться:\n"
        "1. Отправь фото теста из МЭШ\n"
        "2. Я распознаю текст и найду ответы\n"
        "3. Получи готовые ответы с объяснениями\n\n"
        "🔹 Команды:\n"
        "/start – начать\n"
        "/help – помощь\n"
        "/subjects – список предметов\n"
        "/all_tests – все тесты в базе\n"
        "/test_stats – статистика базы\n"
        "/find_test <ключ> – поиск теста\n"
        "/idioms – идиомы английского\n"
        "/emotions – идиомы про эмоции\n"
        "/prepositions – предлоги русского\n"
        "/russian – правила русского языка")

@bot.message_handler(commands=['subjects'])
def send_subjects(message):
    bot.reply_to(message,
        "📚 Предметы 7-8 класс:\n"
        "• Математика (алгебра, геометрия)\n"
        "• Физика\n• Химия\n• Биология\n"
        "• География\n• История\n• Литература\n"
        "• Обществознание\n• Английский язык\n"
        "• Информатика (презентации)")

@bot.message_handler(commands=['all_tests'])
def show_all_tests(message):
    lines = ["📚 База тестов МЭШ:\n"]
    for tid, t in mesh_db.tests.items():
        lines.append(f"• {t['subject']} {t['class']} кл – {t['topic']} (ID: {tid})")
    bot.reply_to(message, '\n'.join(lines)[:4000])

@bot.message_handler(commands=['test_stats'])
def test_stats(message):
    total = len(mesh_db.tests)
    qcount = sum(len(t.get('questions', [])) for t in mesh_db.tests.values())
    bot.reply_to(message, f"📊 Тестов: {total}, Вопросов: {qcount}")

@bot.message_handler(commands=['find_test'])
def find_test_cmd(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ Используйте: /find_test <ключевые слова>")
        return
    keyword = parts[1].lower()
    found = []
    for tid, t in mesh_db.tests.items():
        if keyword in tid or keyword in t['topic'].lower():
            found.append(f"{t['subject']} {t['class']} кл – {t['topic']}")
    if found:
        bot.reply_to(message, "🔍 Найдено:\n" + '\n'.join(found[:10]))
    else:
        bot.reply_to(message, "❌ Ничего не найдено.")

@bot.message_handler(commands=['idioms'])
def show_idioms(message):
    bot.reply_to(message,
        "📚 Английские идиомы:\n"
        "1. cry over spilt milk – плакать над пролитым молоком\n"
        "2. bookworm – книжный червь\n"
        "3. butterflies in the stomach – волнение\n"
        "4. raining cats and dogs – льет как из ведра\n"
        "5. on cloud nine – на седьмом небе\n"
        "6. as busy as a bee – трудолюбивый\n"
        "7. heart of a lion – храбрый\n"
        "8. two left feet – неуклюжий\n"
        "9. brain box – умный человек\n"
        "10. born with a silver spoon – родился в рубашке")

@bot.message_handler(commands=['emotions'])
def show_emotions(message):
    bot.reply_to(message,
        "😊 Идиомы про эмоции:\n"
        "• on cloud nine – очень счастлив\n"
        "• over the moon – вне себя от счастья\n"
        "• down in the dumps – грустный\n"
        "• under the weather – нездоров\n"
        "• full of beans – полон энергии\n"
        "• walking on air – летать от счастья\n"
        "• feeling blue – грустить\n"
        "• butterflies in the stomach – волноваться")

@bot.message_handler(commands=['prepositions'])
def show_prepositions(message):
    bot.reply_to(message,
        "📚 Предлоги русского языка:\n"
        "Слитно: ввиду, вследствие, насчёт, наподобие, вроде, навстречу, наперекор\n"
        "Раздельно: в виде, в связи, в целях, в течение, в продолжение, в заключение, по мере, в отличие, в виду\n"
        "Важно: в течениИ реки (сущ.) – И, в течениЕ дня (предлог) – Е")

@bot.message_handler(commands=['russian'])
def show_russian(message):
    bot.reply_to(message,
        "📚 Правила русского языка:\n"
        "• Сущ. на -ИЕ в предл. падеже → -ИИ (в течении реки)\n"
        "• Сущ. 1-го скл. в дат. падеже → -Е (по дороге)\n"
        "• Производные предлоги: ввиду (слитно) vs в виду (раздельно)\n"
        "• В течение (предлог) – Е, в течении (сущ.) – И")

# ==================== ОБРАБОТКА ФОТО ====================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        processing_msg = bot.reply_to(message, "🔍 Распознаю тест...")
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded = bot.download_file(file_info.file_path)
        image_path = f"temp_{message.from_user.id}.jpg"
        with open(image_path, 'wb') as f:
            f.write(downloaded)

        processed_path = preprocess_image(image_path)
        img = Image.open(processed_path)

        text = ""
        configs = [
            '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzАаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя.,;:!?()"\'',
            '--psm 4',
            '--psm 3',
            '--psm 6',
            '--psm 11',
            '--psm 12',
            '--psm 13'
        ]
        for config in configs:
            try:
                text = pytesseract.image_to_string(img, lang='rus+eng', config=config)
                if len(text.strip()) > 10:
                    break
            except Exception as e:
                print(f"Ошибка распознавания с конфигом {config}: {e}")
                continue

        if not text.strip():
            bot.edit_message_text(
                "❌ Не удалось распознать текст. Попробуйте:\n"
                "• Сделать фото более чётким\n"
                "• Использовать скриншот экрана\n"
                "• Улучшить освещение",
                message.chat.id, 
                processing_msg.message_id
            )
            os.remove(image_path)
            if os.path.exists(processed_path):
                os.remove(processed_path)
            return

        # Логируем распознанный текст (только в консоль)
        print(f"Распознанный текст: {text[:500]}")

        # Проверка на задание про презентации
        if "презентация" in text.lower() or "ошибочное утверждение" in text.lower() or "анимации" in text.lower():
            test_data = {
                "subject": "Информатика",
                "class": "7",
                "topic": "Оформление презентаций",
                "questions": [
                    {
                        "number": 1,
                        "type": "text",
                        "question": "Укажите ошибочное утверждение.",
                        "answer": "Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории",
                        "options": [
                            "Отдавайте предпочтение однотонным фонам, это облегчает восприятие",
                            "Старайтесь как можно больше добавить на слайд анимации, это привлечёт внимание аудитории",
                            "Чтобы выдержать единый стиль презентации, рекомендуется использовать один вид перехода",
                            "Используйте не более двух шрифтов: один для заголовков, другой для текста"
                        ]
                    }
                ]
            }
            answer_text = format_full_test_answer(test_data, 95)
            bot.edit_message_text(
                f"✅ Найден тест в базе:\n\n{answer_text}",
                message.chat.id,
                processing_msg.message_id
            )
            os.remove(image_path)
            if os.path.exists(processed_path):
                os.remove(processed_path)
            return

        # Проверяем, есть ли ключевые слова для задания на соответствие
        if "соответствие" in text.lower() or "единицами измерения" in text.lower():
            pairs = {
                "работа": "Джоуль (Дж)",
                "вес тела": "Ньютон (Н)",
                "путь": "Метр (м)",
                "скорость": "м/с",
                "масса": "кг",
                "сила": "Н",
                "давление": "Па",
                "плотность": "кг/м³"
            }
            
            found_pairs = {}
            for term, defin in pairs.items():
                if term in text.lower() or term.replace(' ', '') in text.lower().replace(' ', ''):
                    found_pairs[term] = defin
            
            if found_pairs:
                answer_text = format_matching_answer(found_pairs)
                bot.edit_message_text(
                    f"✅ Найдены соответствия:\n\n{answer_text}",
                    message.chat.id,
                    processing_msg.message_id
                )
                os.remove(image_path)
                if os.path.exists(processed_path):
                    os.remove(processed_path)
                return

        # Поиск в базе тестов МЭШ
        test_data, similarity = mesh_db.find_test_by_text(text)
        
        if test_data and similarity > 30:
            answer_text = format_full_test_answer(test_data, similarity)
            if len(answer_text) > 4000:
                parts = [answer_text[i:i+4000] for i in range(0, len(answer_text), 4000)]
                bot.edit_message_text(
                    f"✅ Найден тест в базе:\n\n{parts[0]}",
                    message.chat.id,
                    processing_msg.message_id
                )
                for part in parts[1:]:
                    bot.send_message(message.chat.id, part)
            else:
                bot.edit_message_text(
                    f"✅ Найден тест в базе:\n\n{answer_text}",
                    message.chat.id,
                    processing_msg.message_id
                )
        else:
            questions = extract_test_questions(text)
            if not questions:
                questions = [{'question': text, 'options': []}]
            
            answer_text = format_individual_answers(questions)
            bot.edit_message_text(
                f"📝 Найдены ответы:\n\n{answer_text}",
                message.chat.id,
                processing_msg.message_id
            )

        # Удаляем временные файлы
        os.remove(image_path)
        if os.path.exists(processed_path):
            os.remove(processed_path)

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")
        logger.error(f"Ошибка в handle_photo: {e}")

# ==================== ОБРАБОТКА ТЕКСТА ====================
@bot.message_handler(func=lambda m: True)
def handle_text(message):
    text = message.text.lower().strip()
    
    if text in ["привет", "здравствуйте", "hi", "hello"]:
        bot.reply_to(message, "Привет! Отправь фото теста или задай вопрос.")
        return
    if text in ["📚 предметы", "предметы"]:
        send_subjects(message)
        return
    if text in ["📊 статистика", "статистика"]:
        test_stats(message)
        return
    if text in ["🔍 найти тест", "найти тест"]:
        bot.reply_to(message, "Используй команду /find_test <ключевые слова>")
        return
    if text in ["❓ помощь", "помощь"]:
        send_help(message)
        return

    answer = find_answer_with_context(message.text)
    if answer:
        bot.reply_to(message, f"💡 Ответ: {answer}")
    else:
        internet = search_in_internet(message.text)
        if internet:
            bot.reply_to(message, f"💡 Найдено в интернете: {internet}")
        else:
            bot.reply_to(message, "🤔 Не нашел ответ. Попробуй отправить фото теста.")

# ==================== ЗАПУСК ====================
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        print("✅ Вебхук отключён")
    except Exception as e:
        print(f"⚠️ Ошибка при отключении вебхука: {e}")
    
    time.sleep(2)
    
    print("🚀 Бот для решения тестов МЭШ запущен!")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
