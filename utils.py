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
        
        # Увеличение размера
        img = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        
        # Преобразование в оттенки серого
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Увеличение контраста
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Адаптивный порог
        binary = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 15, 3)
        
        # Удаление шума
        denoised = cv2.medianBlur(binary, 3)
        
        # Морфологическая операция
        kernel = np.ones((1, 2), np.uint8)
        denoised = cv2.dilate(denoised, kernel, iterations=1)
        
        processed_path = image_path.replace('.jpg', '_processed.jpg')
        cv2.imwrite(processed_path, denoised)
        return processed_path
    except Exception as e:
        print(f"Ошибка предобработки: {e}")
        return image_path

def extract_test_questions(text):
    """Улучшенное извлечение вопросов из распознанного текста"""
    lines = text.split('\n')
    questions = []
    current_q = ""
    current_opts = []
    in_question = False
    
    # Сначала ищем задания с вариантами
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Проверка на начало задания
        if re.search(r'ЗАДАНИЕ\s*\d+', line, re.I) or re.search(r'Вопрос\s*\d+', line, re.I):
            if current_q:
                questions.append({'question': current_q, 'options': current_opts})
            current_q = line
            current_opts = []
            in_question = True
        elif in_question:
            # Проверка на варианты ответов
            if re.match(r'^[•●○▪\-]\s*', line) or re.match(r'^[А-Яа-яA-Za-z]\)', line) or re.match(r'^[0-9]+[.)]', line):
                # Убираем маркер
                clean_option = re.sub(r'^[•●○▪\-]\s*', '', line)
                clean_option = re.sub(r'^[А-Яа-яA-Za-z]\)\s*', '', clean_option)
                clean_option = re.sub(r'^[0-9]+[.)]\s*', '', clean_option)
                if clean_option:
                    current_opts.append(clean_option)
            elif line and len(line) > 5:
                # Если это продолжение вопроса
                if not current_q.endswith('...') and not current_q.endswith('?'):
                    current_q += " " + line
                else:
                    current_q = line
    
    if current_q:
        questions.append({'question': current_q, 'options': current_opts})
    
    # Если не нашли структурированных вопросов, пытаемся найти по ключевым словам
    if not questions:
        # Ищем текст между "ЗАДАНИЕ" и вариантами ответов
        zadanie_match = re.search(r'ЗАДАНИЕ\s*\d+.*?(?=[•●○▪\-]|\n\n)', text, re.DOTALL | re.IGNORECASE)
        if zadanie_match:
            q_text = zadanie_match.group(0).strip()
            # Ищем варианты
            options = re.findall(r'[•●○▪\-]\s*([^\n]+)', text)
            if options:
                # Очищаем варианты
                clean_options = [re.sub(r'^[•●○▪\-]\s*', '', opt).strip() for opt in options]
                questions.append({'question': q_text, 'options': clean_options})
    
    return questions

def clean_text_for_deepseek(question, options):
    """Подготовка текста для отправки в DeepSeek"""
    clean_q = re.sub(r'[^\w\s.,;:!?()"\'\-]', '', question)
    clean_q = re.sub(r'\s+', ' ', clean_q).strip()
    
    if options:
        clean_options = [re.sub(r'[^\w\s.,;:!?()"\'\-]', '', opt) for opt in options]
        clean_options = [re.sub(r'\s+', ' ', opt).strip() for opt in clean_options if opt]
        return clean_q, clean_options
    return clean_q, []

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

def format_individual_answers(questions, find_answer_func, search_func):
    """Форматирование ответов по отдельным вопросам"""
    lines = []
    for idx, q in enumerate(questions, 1):
        ans = find_answer_func(q['question'])
        if not ans:
            ans = search_func(q['question']) or "Не удалось найти ответ"
        lines.append(f"📌 Вопрос {idx}: {q['question'][:150]}")
        if q.get('options'):
            lines.append("📋 Варианты:")
            for opt in q['options']:
                lines.append(f"  • {opt}")
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
