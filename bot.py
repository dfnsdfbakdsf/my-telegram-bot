import os
import re
import logging
import json
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

# ==================== НАСТРОЙКИ ====================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не задан в переменных окружения!")

# Для Windows раскомментируйте:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

bot = telebot.TeleBot(TOKEN)
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==================== БАЗА ЗНАНИЙ (краткая версия) ====================
knowledge_base = {
    # Математика 7
    "формулы сокращенного умножения": "(a+b)² = a² + 2ab + b²; (a-b)² = a² - 2ab + b²; a² - b² = (a-b)(a+b)",
    "квадрат суммы": "(a+b)² = a² + 2ab + b²",
    "квадрат разности": "(a-b)² = a² - 2ab + b²",
    "разность квадратов": "a² - b² = (a-b)(a+b)",
    "линейное уравнение": "Уравнение вида ax + b = 0, где a ≠ 0. Решение: x = -b/a",
    "решите уравнение 2x 3 7": "x = 2",
    "решите уравнение 3x 5 10": "x = 5",
    "степень с натуральным показателем": "aⁿ = a · a · ... · a (n раз)",
    # Геометрия 7
    "сумма углов треугольника": "180°",
    "свойство смежных углов": "Сумма смежных углов равна 180°",
    "свойство вертикальных углов": "Вертикальные углы равны",
    "признаки параллельности": "1) Накрест лежащие углы равны; 2) Соответственные углы равны; 3) Сумма односторонних углов = 180°",
    "равнобедренный треугольник": "Треугольник с двумя равными сторонами",
    # Физика 7
    "скорость": "v = s/t, путь в единицу времени",
    "плотность": "ρ = m/V",
    "сила тяжести": "F = mg",
    "давление": "p = F/S",
    "архимедова сила": "F = ρgV, выталкивающая сила",
    "работа": "A = Fs",
    "мощность": "N = A/t",
    # Химия 7
    "атом": "Мельчайшая частица химического элемента",
    "молекула": "Мельчайшая частица вещества",
    "валентность": "Способность атомов присоединять другие атомы",
    "оксиды": "Соединения элементов с кислородом",
    "кислоты": "Вещества, содержащие водород и кислотный остаток",
    # Биология 7
    "фотосинтез": "Образование органических веществ на свету",
    "клетка": "Элементарная единица живого",
    "царства живой природы": "Бактерии, Грибы, Растения, Животные",
    # География 7
    "материки": "Евразия, Африка, Северная Америка, Южная Америка, Антарктида, Австралия",
    "океаны": "Тихий, Атлантический, Индийский, Северный Ледовитый, Южный",
    # История 7
    "крещение руси": "988 год",
    "куликовская битва": "1380 год",
    # Литература 7
    "пушкин": "Великий русский поэт (1799-1837)",
    "гоголь": "Русский писатель (1809-1852)",
    # Обществознание 7
    "конституция": "Основной закон",
    "права ребенка": "Права до 18 лет",
    # Английский 7
    "present simple": "Действие происходит регулярно",
    "past simple": "Действие произошло в прошлом",
    "irregular verbs": "Неправильные глаголы",
    "go went gone": "Идти",
    # 8 класс (кратко)
    "теорема пифагора": "c² = a² + b²",
    "площадь треугольника": "S = ½ · a · h",
    "количество теплоты": "Q = cmΔt",
    "дискриминант": "D = b² - 4ac",
    "квадратное уравнение": "ax² + bx + c = 0, где a ≠ 0",
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
    "turn up": "появляться, увеличивать (громкость)",
    "come in": "входить",
    "come out": "выходить, появляться",
    "run out of": "заканчиваться (о запасах)",
    "break down": "сломаться, разобрать",
    "break up": "расставаться, разбивать",
    "give up": "сдаваться, бросать (привычку)",
    "give in": "сдаваться, уступать",
    "make up": "выдумывать, мириться, составлять",
    "call off": "отменять",
    "carry on": "продолжать",
    "check in": "регистрироваться (в отеле)",
    "check out": "выезжать, проверять",
    "fill in": "заполнять (форму)",
    "find out": "узнавать, выяснять",
    "get rid of": "избавляться от",
    "go on": "продолжать, происходить",
    "hand in": "сдавать (работу)",
    "hold on": "подождать, держаться",
    "keep up with": "идти в ногу, не отставать",
    "pick up": "подбирать, забирать, учить (язык)",
    "point out": "указывать",
    "set up": "устанавливать, организовывать",
    "sort out": "разобраться, решить",
    "stand up": "вставать, выдерживать",
    "stick to": "придерживаться",
    "sum up": "подводить итог",
    "take care of": "заботиться о",
    "talk over": "обсуждать",
    "think over": "обдумывать",
    "try on": "примерять",
    "wear off": "сходить на нет",
    "work out": "решать, тренироваться, срабатывать",
}

# ==================== БАЗА ТЕСТОВ МЭШ (сокращённая) ====================
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
            "full_text": """Прочитайте текст и вставьте пропущенные слова/словосочетания, подходящие по смыслу.
Два мальчика, соревнуясь в перетягивании каната, тянут его в разные стороны. Один из них, двигаясь равномерно, перетянул канат на себя. Если сравнивать механические работы сил, приложенных к канату, то несмотря на то, что один из мальчиков перетянул его, работы сил, приложенных к канату, равны по модулю. Силы, приложенные к канату, равны. У одного мальчика направление силы, приложенной к канату, совпадает с направлением его перемещения, а у другого – противоположно. Поскольку перемещения, на которых действуют силы, равны, то работы этих сил равны по модулю. В данном случае можно сказать, что работы, совершенные мальчиками, равны по модулю и неравны по знаку.""",
            "answers": {
                "1": "равны по модулю",
                "2": "равны",
                "3": "перемещения",
                "4": "равны",
                "5": "неравны по знаку"
            },
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
                        "плотность": "кг/м³"
                    }
                }
            ],
            "similarity": 92
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
        # Математика 7: Формулы сокращённого умножения
        self.tests["math_7_001"] = {
            "id": "math_7_001",
            "subject": "Математика",
            "class": "7",
            "topic": "Формулы сокращенного умножения",
            "questions": [
                {
                    "number": 1,
                    "type": "text",
                    "question": "Квадрат суммы двух выражений равен квадрату первого выражения плюс удвоенное произведение первого и второго выражений плюс",
                    "answer": "квадрат второго выражения",
                    "options": ["квадрат второго", "удвоенное произведение", "сумма"]
                }
            ],
            "similarity": 90
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

        return best_match, best_score

mesh_db = MESHTestsDatabase()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def preprocess_image(image_path):
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        img = cv2.resize(img, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        denoised = cv2.medianBlur(binary, 3)
        processed_path = image_path.replace('.jpg', '_processed.jpg')
        cv2.imwrite(processed_path, denoised)
        return processed_path
    except Exception as e:
        logger.error(f"Ошибка предобработки: {e}")
        return image_path

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
                lines.append("Соответствия:")
                for term, defin in q['pairs'].items():
                    lines.append(f"  • {term} → {defin}")
            else:
                lines.append(f"✅ Ответ: {q.get('answer', '')}")
                if q.get('options'):
                    lines.append(f"📋 Варианты: {', '.join(q['options'])}")
            lines.append("")
    elif 'full_text' in test_data and 'answers' in test_data:
        lines.append("📝 Полный текст с ответами:")
        lines.append(test_data['full_text'])
        lines.append("")
        lines.append("✅ Все ответы:")
        for k, v in test_data['answers'].items():
            lines.append(f"{k}) {v}")
    return '\n'.join(lines)

def format_individual_answers(questions):
    lines = []
    for idx, q in enumerate(questions, 1):
        ans = find_answer_with_context(q['question'])
        if not ans:
            ans = search_in_internet(q['question']) or "Не удалось найти ответ"
        lines.append(f"📌 Вопрос {idx}: {q['question'][:100]}")
        if q.get('options'):
            lines.append(f"📋 Варианты: {', '.join(q['options'])}")
        lines.append(f"💡 Ответ: {ans}")
        lines.append("")
    return '\n'.join(lines)

# ==================== ОБРАБОТЧИКИ TELEGRAM ====================

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📚 Предметы"), types.KeyboardButton("📊 Статистика"))
    markup.add(types.KeyboardButton("🔍 Найти тест"), types.KeyboardButton("❓ Помощь"))
    bot.reply_to(message,
        "👋 Привет! Я бот для решения тестов МЭШ 7-8 классов.\n\n"
        "📸 Отправь мне фото теста, и я найду ответы!\n"
        "Или просто задай вопрос текстом.", reply_markup=markup)

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
        "• Обществознание\n• Английский язык")

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
    bot.reply_to(message, f"📊 Статистика:\nТестов: {total}\nВопросов: {qcount}\nПредметов: ~9")

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
        for psm in [6, 4, 3]:
            try:
                text = pytesseract.image_to_string(img, lang='rus+eng', config=f'--psm {psm}')
                if len(text.strip()) > 20:
                    break
            except:
                continue

        if not text.strip():
            bot.edit_message_text("❌ Не удалось распознать текст. Попробуйте другое фото.",
                                  message.chat.id, processing_msg.message_id)
            return

        test_data, similarity = mesh_db.find_test_by_text(text)
        if test_data and similarity > 30:
            answer_text = format_full_test_answer(test_data, similarity)
            if len(answer_text) > 4000:
                parts = [answer_text[i:i+4000] for i in range(0, len(answer_text), 4000)]
                bot.edit_message_text(f"✅ Найден тест в базе:\n\n{parts[0]}",
                                      message.chat.id, processing_msg.message_id)
                for part in parts[1:]:
                    bot.send_message(message.chat.id, part)
            else:
                bot.edit_message_text(f"✅ Найден тест в базе:\n\n{answer_text}",
                                      message.chat.id, processing_msg.message_id)
        else:
            questions = extract_test_questions(text)
            if not questions:
                questions = [{'question': text, 'options': []}]
            answer_text = format_individual_answers(questions)
            bot.edit_message_text(f"📝 Найдены ответы:\n\n{answer_text}",
                                  message.chat.id, processing_msg.message_id)

        bot.send_message(message.chat.id, f"📄 Распознанный текст:\n{text[:1500]}")
        os.remove(image_path)
        if os.path.exists(processed_path):
            os.remove(processed_path)

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)}")

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
    print("🚀 Бот для решения тестов МЭШ запущен!")
    bot.infinity_polling()