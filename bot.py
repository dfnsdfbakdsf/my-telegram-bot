import os
import re
import logging
import subprocess
import shutil
import json
from io import BytesIO
from difflib import SequenceMatcher

import telebot
from telebot import types
import pytesseract
from PIL import Image
import cv2
import numpy as np
import requests
from googlesearch import search
from fuzzywuzzy import fuzz

# ==================== НАСТРОЙКИ TESSERACT ====================
# Ищем Tesseract в системе (через shutil)
tesseract_path = shutil.which('tesseract')
if tesseract_path:
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
    print(f"✅ Tesseract найден по пути: {tesseract_path}")
else:
    # Пробуем стандартные пути (на случай, если shutil не сработал)
    possible_paths = ['/usr/bin/tesseract', '/usr/local/bin/tesseract', '/bin/tesseract']
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Tesseract найден по пути: {path}")
            break
    else:
        print("❌ Tesseract НЕ НАЙДЕН! Убедитесь, что он установлен.")
        # Можно выйти или продолжить, но OCR не будет работать

# Проверяем, что Tesseract работает
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

# ==================== БАЗА ЗНАНИЙ (краткая версия) ====================
knowledge_base = {
    "формулы сокращенного умножения": "(a+b)² = a² + 2ab + b²; (a-b)² = a² - 2ab + b²; a² - b² = (a-b)(a+b)",
    "квадрат суммы": "(a+b)² = a² + 2ab + b²",
    "квадрат разности": "(a-b)² = a² - 2ab + b²",
    "разность квадратов": "a² - b² = (a-b)(a+b)",
    "линейное уравнение": "Уравнение вида ax + b = 0, где a ≠ 0. Решение: x = -b/a",
    "сумма углов треугольника": "180°",
    "свойство смежных углов": "Сумма смежных углов равна 180°",
    "скорость": "v = s/t",
    "плотность": "ρ = m/V",
    "сила тяжести": "F = mg",
    "давление": "p = F/S",
    "архимедова сила": "F = ρgV",
    "работа": "A = Fs",
    "мощность": "N = A/t",
    "атом": "Мельчайшая частица химического элемента",
    "молекула": "Мельчайшая частица вещества",
    "валентность": "Способность атомов присоединять другие атомы",
    "фотосинтез": "Образование органических веществ на свету",
    "клетка": "Элементарная единица живого",
    "царства живой природы": "Бактерии, Грибы, Растения, Животные",
    "материки": "Евразия, Африка, Северная Америка, Южная Америка, Антарктида, Австралия",
    "океаны": "Тихий, Атлантический, Индийский, Северный Ледовитый, Южный",
    "крещение руси": "988 год",
    "куликовская битва": "1380 год",
    "конституция": "Основной закон",
    "present simple": "Действие происходит регулярно",
    "past simple": "Действие произошло в прошлом",
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
    "get along with": "ладить с кем-то",
    "get on with": "ладить, продолжать",
    "get over": "оправиться от, пережить",
    "take off": "взлетать, снимать (одежду)",
    "take up": "заниматься (хобби), начинать",
    "look for": "искать",
    "look after": "заботиться, присматривать",
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
            "full_text": """Прочитайте текст и вставьте пропущенные слова/словосочетания...
Два мальчика, соревнуясь в перетягивании каната, тянут его в разные стороны. Один из них, двигаясь равномерно, перетянул канат на себя. Если сравнивать механические работы сил, приложенных к канату, то несмотря на то, что один из мальчиков перетянул его, работы сил, приложенных к канату, равны по модулю. Силы, приложенные к канату, равны. У одного мальчика направление силы, приложенной к канату, совпадает с направлением его перемещения, а у другого – противоположно. Поскольку перемещения, на которых действуют силы, равны, то работы этих сил равны по модулю. В данном случае можно сказать, что работы, совершенные мальчиками, равны по модулю и неравны по знаку.""",
            "answers": {"1": "равны по модулю", "2": "равны", "3": "перемещения", "4": "равны", "5": "неравны по знаку"},
            "similarity": 90
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
                }
            ],
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
        return best_match, best_score

mesh_db = MESHTestsDatabase()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def preprocess_image(image_path):
    """Улучшенная предобработка для OCR"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return image_path
        # Увеличение размера
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Адаптивный порог для лучшего распознавания текста
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
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
    lines.append(f"🔍 {similarity:.0f}% МЭШ\n")
    lines.append(f"📚 {test_data['subject']} {test_data['class']} класс")
    lines.append(f"📖 Тема: {test_data['topic']}\n")
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
        lines.append(f"💡 Ответ: {ans}\n")
    return '\n'.join(lines)

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📚 Предметы"), types.KeyboardButton("📊 Статистика"))
    markup.add(types.KeyboardButton("🔍 Найти тест"), types.KeyboardButton("❓ Помощь"))
    bot.reply_to(message, "👋 Привет! Я бот для решения тестов МЭШ 7-8 классов.\n\n📸 Отправь мне фото теста, и я найду ответы!", reply_markup=markup)

@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message, "📚 Команды:\n/start – начать\n/help – помощь\n/subjects – предметы\n/all_tests – список тестов\n/test_stats – статистика\n/find_test <ключ> – поиск\n/idioms – идиомы\n/emotions – эмоции\n/prepositions – предлоги\n/russian – правила")

@bot.message_handler(commands=['subjects'])
def send_subjects(message):
    bot.reply_to(message, "📚 Математика, Физика, Химия, Биология, География, История, Литература, Обществознание, Английский язык")

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
    bot.reply_to(message, "📚 Идиомы:\n1. cry over spilt milk – плакать над пролитым молоком\n2. bookworm – книжный червь\n3. on cloud nine – на седьмом небе\n4. raining cats and dogs – льет как из ведра\n5. heart of a lion – храбрый")

@bot.message_handler(commands=['emotions'])
def show_emotions(message):
    bot.reply_to(message, "😊 Идиомы эмоций:\n• on cloud nine – счастлив\n• down in the dumps – грустный\n• butterflies in the stomach – волноваться")

@bot.message_handler(commands=['prepositions'])
def show_prepositions(message):
    bot.reply_to(message, "📚 Предлоги: слитно – ввиду, вследствие, насчёт; раздельно – в виду, в течение, по мере")

@bot.message_handler(commands=['russian'])
def show_russian(message):
    bot.reply_to(message, "📚 Правила: в течении реки (И), в течение дня (Е), ввиду (слитно), в виду (раздельно)")

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
            '--psm 3'
        ]
        for config in configs:
            try:
                text = pytesseract.image_to_string(img, lang='rus+eng', config=config)
                if len(text.strip()) > 10:
                    break
            except:
                continue

        if not text.strip():
            bot.edit_message_text("❌ Не удалось распознать текст. Попробуйте другое фото.", message.chat.id, processing_msg.message_id)
            return

        # Логируем распознанный текст (для отладки)
        print(f"Распознанный текст: {text[:300]}")

        test_data, similarity = mesh_db.find_test_by_text(text)
        if test_data and similarity > 30:
            answer_text = format_full_test_answer(test_data, similarity)
            if len(answer_text) > 4000:
                parts = [answer_text[i:i+4000] for i in range(0, len(answer_text), 4000)]
                bot.edit_message_text(f"✅ Найден тест в базе:\n\n{parts[0]}", message.chat.id, processing_msg.message_id)
                for part in parts[1:]:
                    bot.send_message(message.chat.id, part)
            else:
                bot.edit_message_text(f"✅ Найден тест в базе:\n\n{answer_text}", message.chat.id, processing_msg.message_id)
        else:
            questions = extract_test_questions(text)
            if not questions:
                questions = [{'question': text, 'options': []}]
            answer_text = format_individual_answers(questions)
            bot.edit_message_text(f"📝 Найдены ответы:\n\n{answer_text}", message.chat.id, processing_msg.message_id)

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
    if text in ["привет", "здравствуйте", "hi"]:
        bot.reply_to(message, "Привет! Отправь фото теста или задай вопрос.")
        return
    if text in ["📚 предметы", "предметы"]:
        send_subjects(message)
        return
    if text in ["📊 статистика", "статистика"]:
        test_stats(message)
        return
    if text in ["🔍 найти тест", "найти тест"]:
        bot.reply_to(message, "Используй /find_test <ключевые слова>")
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
