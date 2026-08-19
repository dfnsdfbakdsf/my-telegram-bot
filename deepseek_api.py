import os
import requests
import json
import logging

logger = logging.getLogger(__name__)

# ===== НАСТРОЙКИ DEEPSEEK API =====
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

def ask_deepseek(question, context=""):
    """
    Отправляет запрос в DeepSeek API и возвращает ответ
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY не задан!")
        return None

    try:
        prompt = f"""Ты — помощник для решения тестов МЭШ (Московская электронная школа) для 7-8 классов.
Твоя задача — дать точный ответ на вопрос по школьной программе.

Вопрос: {question}

Дополнительный контекст (если есть): {context}

Ответь кратко и чётко. Если это тест с вариантами ответов, укажи правильный вариант.
"""

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты — эксперт по школьной программе 7-8 классов. Отвечай кратко и точно."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer.strip()
        else:
            logger.error(f"Ошибка DeepSeek API: {response.status_code}")
            return None

    except requests.exceptions.Timeout:
        logger.error("Таймаут при запросе к DeepSeek API")
        return None
    except Exception as e:
        logger.error(f"Ошибка при запросе к DeepSeek: {e}")
        return None

def ask_deepseek_with_options(question, options):
    """
    Отправляет запрос в DeepSeek с вариантами ответов
    """
    if not DEEPSEEK_API_KEY:
        return None

    try:
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])

        prompt = f"""Ты — помощник для решения тестов МЭШ.

Вопрос: {question}

Варианты ответов:
{options_text}

Укажи номер правильного ответа и сам ответ. Например: "3. Лодка проплыла мимо и мы бросились догонять её."
Ответ должен быть кратким и точным.
"""

        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "Ты — эксперт по школьной программе. Отвечай кратко и точно."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 200
        }

        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return answer.strip()
        else:
            logger.error(f"Ошибка DeepSeek API: {response.status_code}")
            return None

    except Exception as e:
        logger.error(f"Ошибка при запросе к DeepSeek: {e}")
        return None
