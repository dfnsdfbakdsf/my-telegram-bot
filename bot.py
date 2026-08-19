import os
import logging
from io import BytesIO
import numpy as np
from PIL import Image
import easyocr
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === Переменные окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Не заданы TELEGRAM_TOKEN или DEEPSEEK_API_KEY")

# === DeepSeek ===
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# === EasyOCR (русский + английский) ===
# Модели скачаются при первом вызове, займёт ~1 минуту и ~1.5 ГБ диска
reader = easyocr.Reader(['ru', 'en'], gpu=False)

logging.basicConfig(level=logging.INFO)

# === OCR ===
def extract_text_from_image(image_bytes):
    try:
        image = Image.open(BytesIO(image_bytes))
        image_np = np.array(image)
        # detail=0 – только текст, paragraph=True – объединять в абзацы
        result = reader.readtext(image_np, detail=0, paragraph=True)
        return ' '.join(result).strip()
    except Exception as e:
        logging.error(f"OCR error: {e}")
        return ""

# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я решаю учебные задания.\n"
        "Отправь фото или текст – я распознаю и отвечу через DeepSeek."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📚 Отправь фото с заданием или просто текст.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_query(update, update.message.text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = await update.message.photo[-1].get_file()
    image_bytes = await photo.download_as_bytearray()
    text = extract_text_from_image(image_bytes)
    if not text:
        await update.message.reply_text(
            "❌ Не распознано. Попробуйте:\n"
            "• сделать фото при ярком свете\n"
            "• сфотографировать крупнее\n"
            "• отправить текст вручную"
        )
        return
    await update.message.reply_text(f"📝 Распознано:\n{text[:300]}...")
    await process_query(update, text)

async def process_query(update: Update, query: str):
    if len(query.strip()) < 3:
        await update.message.reply_text("❌ Слишком короткий запрос.")
        return

    await update.message.reply_text("⏳ Думаю через DeepSeek...")

    try:
        prompt = (
            "Ты — эксперт по решению школьных заданий. "
            "Дай точный ответ. Если есть варианты – укажи правильный.\n\n"
            f"Запрос: {query}"
        )
        response = client.chat.completions.create(
            model="deepseek-v4-pro",   # или "deepseek-v4-flash" (дешевле)
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        answer = response.choices[0].message.content.strip()
        if len(answer) > 4000:
            answer = answer[:4000] + "..."
        await update.message.reply_text(f"✅ Ответ:\n\n{answer}")
    except Exception as e:
        logging.error(f"DeepSeek error: {e}")
        await update.message.reply_text("❌ Ошибка API. Попробуйте позже.")

# === Запуск ===
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logging.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
