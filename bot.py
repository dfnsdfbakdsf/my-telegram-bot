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
from PIL import Image
import requests
from googlesearch import search
from fuzzywuzzy import fuzz

# Импортируем все модули
from knowledge_base import knowledge_base
from phrasal_verbs import phrasal_verbs
from topic_keywords import topic_keywords
from mesh_tests import MESHTestsDatabase
from utils import (
    preprocess_image, extract_test_questions, 
    format_full_test_answer, format_matching_answer, 
    format_individual_answers, detect_topic
)

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

# ==================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ====================
mesh_db = MESHTestsDatabase()

# ==================== ПОИСК ОТВЕТОВ ====================

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
    
    for key, value in knowledge_base.items():
        if key in q:
            return value
    
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

# ==================== ОБРАБОТЧИКИ КОМАНД ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📚 Предметы"), types.KeyboardButton("📊 Статистика"))
    markup.add(types.KeyboardButton("🔍 Найти тест"), types.KeyboardButton("❓ Помощь"))
    bot.reply_to(message, 
        "👋 Привет! Я бот для решения тестов МЭШ 7-8 классов.\n\n"
        "📸 Отправь мне фото теста, и я найду ответы!\n"
        "Или просто задай вопрос текстом.\n\n"
        "📚 Я знаю все предметы: Математика, Геометрия, Физика, Химия, Биология,\n"
        "География, История, Обществознание, Русский язык, Литература,\n"
        "Английский язык, Информатика и ОБЖ!", 
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
        "📚 Предметы 7-8 класс:\n\n"
        "📐 Математика\n"
        "📐 Геометрия\n"
        "🔬 Физика\n"
        "⚗️ Химия\n"
        "🧬 Биология\n"
        "🌍 География\n"
        "📜 История\n"
        "👥 Обществознание\n"
        "📖 Русский язык\n"
        "📕 Литература\n"
        "🇬🇧 Английский язык\n"
        "💻 Информатика\n"
        "🛡️ ОБЖ")

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
    bot.reply_to(message, f"📊 Тестов: {total}\n📝 Вопросов: {qcount}\n📚 Предметов: 12")

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
        "📚 Английские идиомы:\n\n"
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
        "😊 Идиомы про эмоции:\n\n"
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
        "📚 Предлоги русского языка:\n\n"
        "🔹 Слитно:\n"
        "• ввиду (из-за) – ввиду болезни\n"
        "• вследствие (из-за) – вследствие дождей\n"
        "• насчёт (о) – насчёт работы\n"
        "• наподобие (как) – наподобие круга\n"
        "• вроде (как) – вроде шара\n"
        "• навстречу (к) – навстречу другу\n"
        "• наперекор (вопреки) – наперекор судьбе\n\n"
        "🔹 Раздельно:\n"
        "• в виду (по причине) – в виду непогоды\n"
        "• в виде – в виде исключения\n"
        "• в связи – в связи с отъездом\n"
        "• в течение – в течение дня\n"
        "• в продолжение – в продолжение разговора\n"
        "• по мере – по мере продвижения\n"
        "• в отличие – в отличие от других\n\n"
        "⚠️ Важно: в течениИ реки (И), в течениЕ дня (Е)")

@bot.message_handler(commands=['russian'])
def show_russian(message):
    bot.reply_to(message,
        "📚 Правила русского языка:\n\n"
        "1. Существительные на -ИЕ в предл. падеже → -ИИ\n"
        "   • в течени**И** реки\n"
        "   • о решени**И** задачи\n\n"
        "2. Существительные 1-го скл. в дат. падеже → -Е\n"
        "   • по дорог**Е**\n"
        "   • к мам**Е**\n\n"
        "3. Производные предлоги:\n"
        "   • ввиду (слитно) – из-за\n"
        "   • в виду (раздельно) – по причине\n"
        "   • вследствие (слитно) – из-за\n"
        "   • в течение (раздельно) – предлог\n\n"
        "4. В течение (предлог) – Е\n"
        "   В течении (сущ.) – И")

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
            '--psm 4', '--psm 3', '--psm 6', '--psm 11', '--psm 12', '--psm 13'
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

        print(f"Распознанный текст: {text[:500]}")

        text_lower = text.lower()
        detected_topic = detect_topic(text, topic_keywords)
        print(f"Определённая тема: {detected_topic}")

        # === ПОИСК ПО ТЕМЕ ===
        if detected_topic:
            best_match = None
            best_score = 0
            for test_id, test_data in mesh_db.tests.items():
                if test_data.get('subject', '').lower() == detected_topic:
                    score = 80
                    if 'questions' in test_data:
                        for q in test_data['questions']:
                            q_text = q.get('question', '').lower()
                            ratio = fuzz.partial_ratio(text_lower, q_text)
                            if ratio > score:
                                score = ratio
                    if score > best_score:
                        best_score = score
                        best_match = test_data
            
            if best_match and best_score > 30:
                answer_text = format_full_test_answer(best_match, best_score)
                bot.edit_message_text(
                    f"✅ Найден тест в базе:\n\n{answer_text}",
                    message.chat.id,
                    processing_msg.message_id
                )
                os.remove(image_path)
                if os.path.exists(processed_path):
                    os.remove(processed_path)
                return

        # === ЗАДАНИЕ НА СООТВЕТСТВИЕ ===
        if "соответствие" in text_lower or "единицами измерения" in text_lower:
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
                if term in text_lower or term.replace(' ', '') in text_lower.replace(' ', ''):
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

        # === ОБЫЧНЫЙ ПОИСК ===
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
            answer_text = format_individual_answers(questions, find_answer_with_context, search_in_internet)
            bot.edit_message_text(
                f"📝 Найдены ответы:\n\n{answer_text}",
                message.chat.id,
                processing_msg.message_id
            )

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
    print(f"📚 Всего тестов: {len(mesh_db.tests)}")
    print(f"📝 Всего вопросов: {sum(len(t.get('questions', [])) for t in mesh_db.tests.values())}")
    print(f"📚 Предметов: 12")
    print(f"📖 Записей в базе знаний: {len(knowledge_base)}")
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
