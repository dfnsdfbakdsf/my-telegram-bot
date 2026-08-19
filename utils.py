import os
import re
import cv2
import numpy as np
from PIL import Image
import pytesseract
from fuzzywuzzy import fuzz

# ===== ОБРАБОТКА ИЗОБРАЖЕНИЙ =====

def preprocess_image(image_path):
    """Улучшенная предобработка для OCR"""
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
        print(f"Ошибка предобработки: {e}")
        return image_path

def extract_test_questions(text):
    """Извлечение вопросов из распознанного текста"""
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

# ===== ФОРМАТИРОВАНИЕ ОТВЕТОВ =====

def format_full_test_answer(test_data, similarity):
    """Форматирование полного ответа из базы тестов"""
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
    
    # Добавляем объяснение для биологии
    if test_data.get('topic') == "Селекция растений":
        lines.append("📖 Объяснение:")
        lines.append("Задачи селекции растений:")
        lines.append("✅ Верные задачи:")
        lines.append("1. Повышение урожайности и качества культур")
        lines.append("2. Разработка методов создания и совершенствования сортов")
        lines.append("3. Создание сортов и гибридов с нужными человеку свойствами")
        lines.append("")
        lines.append("❌ Не относятся к селекции:")
        lines.append("• Разработка приёмов возделывания (это агротехника)")
        lines.append("• Наблюдение и анализ роста урожаев (это мониторинг)")
    
    # Добавляем объяснение для союзов
    if test_data.get('topic') == "Союзы в сложных предложениях":
        lines.append("📖 Объяснение:")
        lines.append("• В предложении 'Лодка проплыла мимо и мы бросились догонять её'")
        lines.append("  союз И соединяет две части сложного предложения.")
        lines.append("• В других вариантах союз И соединяет однородные члены.")
    
    return '\n'.join(lines)

def format_matching_answer(pairs):
    """Форматирование ответа для задания на соответствие"""
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
    return '\n'.join(lines)

def format_individual_answers(questions, find_answer_with_context, search_in_internet):
    """Форматирование ответов по отдельным вопросам"""
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

def detect_topic(text, topic_keywords):
    """Определение темы по ключевым словам"""
    text_lower = text.lower()
    for topic, keywords in topic_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                return topic
    return None