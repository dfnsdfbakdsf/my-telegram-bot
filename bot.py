import os
import logging
from io import BytesIO
from PIL import Image
import pytesseract
from openai import OpenAI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === Чтение переменных окружения ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Не заданы TELEGRAM_TOKEN или DEEPSEEK_API_KEY в переменных окружения")

# === Инициализация клиента DeepSeek (совместим с OpenAI SDK) ===
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

# Для Windows раскомментируйте следующую строку и укажите путь к tesseract.exe
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(level=logging.INFO)

# === Обработчики команд ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник для решения заданий.\n"
        "Отправь текст или фото с заданием, и я отвечу через DeepSeek."
    )

def extract_text_from_image(image_bytes):
    """Извлекает текст из фото с помощью Tesseract OCR."""
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='rus+eng')
        return text.strip()
    except Exception as e:
        logging.error(f"OCR error: {e}")
        return ""

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await process_query(update, update.message.text)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_bytes = await photo_file.download_as_bytearray()
    extracted = extract_text_from_image(image_bytes)
    if not extracted:
        await update.message.reply_text("❌ Не удалось распознать текст на картинке.")
        return
    await update.message.reply_text(f"📝 Распознано:\n{extracted[:500]}...")
    await process_query(update, extracted)

async def process_query(update: Update, query: str):
    if not query:
        await update.message.reply_text("❌ Запрос пуст.")
        return

    await update.message.reply_text("⏳ Думаю... (DeepSeek)")

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
            max_tokens=1000
        )
        answer = response.choices[0].message.content.strip()

        if len(answer) > 4000:
            answer = answer[:4000] + "...\n\n(ответ обрезан)"

        await update.message.reply_text(f"✅ Ответ:\n\n{answer}")

    except Exception as e:
        logging.error(f"DeepSeek API error: {e}")
        await update.message.reply_text("❌ Ошибка при обращении к DeepSeek. Попробуйте позже.")

# === Запуск бота ===
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logging.info("Бот запущен и слушает сообщения...")
    app.run_polling()

if __name__ == "__main__":
    main()