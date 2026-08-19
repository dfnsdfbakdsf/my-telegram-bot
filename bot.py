import os
import logging
from io import BytesIO
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === Чтение переменных окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Не заданы TELEGRAM_TOKEN или DEEPSEEK_API_KEY в переменных окружения")

# === Инициализация клиента DeepSeek ===
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Для Windows раскомментируйте следующую строку и укажите путь к tesseract.exe
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Функция улучшенного распознавания текста ===
def extract_text_from_image(image_bytes):
    """
    Извлекает текст из фото с предварительной обработкой:
    - перевод в оттенки серого
    - увеличение контраста
    - бинаризация (ч/б)
    - применение фильтра для подавления шума
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        
        # Переводим в оттенки серого
        image = image.convert('L')
        
        # Увеличиваем контраст
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # Бинаризация: порог 128
        image = image.point(lambda x: 0 if x < 128 else 255, '1')
        
        # Применяем медианный фильтр для удаления шума
        image = image.filter(ImageFilter.MedianFilter(size=3))
        
        # Распознаём текст (русский + английский)
        text = pytesseract.image_to_string(image, lang='rus+eng')
        return text.strip()
    
    except Exception as e:
        logging.error(f"Ошибка OCR: {e}")
        return ""

# === Обработчики команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник для решения учебных заданий.\n"
        "Просто отправь текст или фото с задачей, и я отвечу через DeepSeek.\n\n"
        "Команды:\n"
        "/help – показать это сообщение\n"
        "/start – приветствие"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Как я работаю:\n"
        "1. Отправьте текст с заданием или фото.\n"
        "2. Я распознаю текст с фото (если нужно) и передам в DeepSeek.\n"
        "3. DeepSeek проанализирует и даст ответ.\n\n"
        "⚠️ Старайтесь отправлять чёткие фото, чтобы распознавание было точным."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_query(update, update.message.text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем файл самого качественного фото
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    
    # Распознаём текст
    extracted = extract_text_from_image(image_bytes)
    
    if not extracted:
        await update.message.reply_text(
            "❌ Не удалось распознать текст на картинке.\n"
            "Попробуйте:\n"
            "• сделать фото при хорошем освещении\n"
            "• сфотографировать текст крупнее\n"
            "• отправить задание текстом"
        )
        return
    
    # Показываем пользователю, что распознали (первые 500 символов)
    await update.message.reply_text(f"📝 Распознано:\n{extracted[:500]}...")
    
    # Передаём распознанный текст на обработку
    await process_query(update, extracted)

async def process_query(update: Update, query: str):
    if not query or len(query.strip()) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий. Напишите задание подробнее.")
        return
    
    await update.message.reply_text("⏳ Обрабатываю запрос через DeepSeek...")
    
    try:
        prompt = (
            "Ты — эксперт по решению школьных и университетских заданий. "
            "Дай точный, подробный и правильный ответ на следующий вопрос или задачу. "
            "Если это задача с вариантами ответа, укажи правильный вариант. "
            "Если это задание с открытым ответом, дай развёрнутое решение.\n\n"
            f"Запрос: {query}"
        )
        
        response = client.chat.completions.create(
            model="deepseek-v4-pro",          # или "deepseek-v4-flash" для экономии
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        
        answer = response.choices[0].message.content.strip()
        
        # Обрезаем, если слишком длинный (Telegram лимит 4096 символов)
        if len(answer) > 4000:
            answer = answer[:4000] + "...\n\n(ответ обрезан)"
        
        await update.message.reply_text(f"✅ Ответ:\n\n{answer}")
    
    except Exception as e:
        logging.error(f"Ошибка DeepSeek API: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обращении к DeepSeek.\n"
            "Попробуйте позже или отправьте задание текстом."
        )

# === Запуск бота ===
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    logging.info("Бот запущен и слушает сообщения...")
    app.run_polling()

if __name__ == "__main__":
    main()
