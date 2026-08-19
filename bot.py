import os
import logging
from io import BytesIO
from PIL import Image
import easyocr
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

# === Инициализация EasyOCR (русский + английский) ===
# Модели загрузятся при первом вызове, это может занять 10–20 секунд
reader = easyocr.Reader(['ru', 'en'], gpu=False)  # gpu=False, т.к. на Railway GPU нет

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Функция распознавания через EasyOCR ===
def extract_text_from_image(image_bytes):
    """
    Извлекает текст с помощью EasyOCR.
    Возвращает объединённый текст из всех найденных блоков.
    """
    try:
        image = Image.open(BytesIO(image_bytes))
        # EasyOCR принимает numpy-массив или путь к файлу, поэтому конвертируем
        import numpy as np
        image_np = np.array(image)
        
        # Распознаём текст
        result = reader.readtext(image_np, detail=0, paragraph=True)
        # result — это список строк (текст без координат)
        text = ' '.join(result).strip()
        return text
    except Exception as e:
        logging.error(f"Ошибка EasyOCR: {e}")
        return ""

# === Обработчики команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник для решения учебных заданий.\n"
        "Отправьте текст или фото с задачей, и я отвечу через DeepSeek.\n\n"
        "Команды:\n"
        "/help – справка"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 Как я работаю:\n"
        "1. Отправьте текст или фото.\n"
        "2. Я распознаю текст (если фото) и передам в DeepSeek.\n"
        "3. Получите ответ.\n\n"
        "⚠️ Для лучшего распознавания отправляйте чёткие фото."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_query(update, update.message.text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    
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
    
    await update.message.reply_text(f"📝 Распознано:\n{extracted[:500]}...")
    await process_query(update, extracted)

async def process_query(update: Update, query: str):
    if not query or len(query.strip()) < 2:
        await update.message.reply_text("❌ Запрос слишком короткий.")
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
            model="deepseek-v4-pro",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        
        answer = response.choices[0].message.content.strip()
        if len(answer) > 4000:
            answer = answer[:4000] + "...\n\n(ответ обрезан)"
        
        await update.message.reply_text(f"✅ Ответ:\n\n{answer}")
    
    except Exception as e:
        logging.error(f"Ошибка DeepSeek API: {e}")
        await update.message.reply_text("❌ Ошибка при обращении к DeepSeek. Попробуйте позже.")

# === Запуск ===
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logging.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
