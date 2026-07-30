import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8693929419:AAGgphaBqhCi25EcEIATAo4Gr3Gfl9Q_zB0'
FORWARD_CHAT_ID = -1004291446609  # <-- ID Группы без кавычек
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def handle_start_help(message):
    chat_id = message.chat.id
    user_data.pop(chat_id, None)
    
    bot.send_message(chat_id, 'Привет! Как тебя зовут?', reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id] = {'name': message.text}
    bot.send_message(chat_id, 'Сколько тебе лет?')
    bot.register_next_step_handler(message, check_age)

def check_age(message):
    chat_id = message.chat.id
    try:
        age = int(message.text)
        if age > 10:
            user_data[chat_id]['age'] = age
            bot.send_message(chat_id, 'Хорошо, давай продолжим?\nНапиши "Да" или "Нет"')
            bot.register_next_step_handler(message, ask_to_continue)
        else:
            bot.send_message(chat_id, 'Извини, этот бот для пользователей старше 10 лет.')
    except ValueError:
        bot.send_message(chat_id, 'Пожалуйста, введите именно число. Например: 25')
        bot.register_next_step_handler(message, check_age)

def ask_to_continue(message):
    chat_id = message.chat.id
    if message.text.lower() == 'да':
        bot.send_message(chat_id, 'Отлично!\nА какой у вас донат в игре?')
        bot.register_next_step_handler(message, get_donate)
    elif message.text.lower() == 'нет':
        bot.send_message(chat_id, 'Понял. Если что, всегда можно начать заново командой /start')
    else:
        bot.send_message(chat_id, 'Я не понял твой ответ. Напиши "Да" или "Нет".')
        bot.register_next_step_handler(message, ask_to_continue)

def get_donate(message):
    chat_id = message.chat.id
    name = user_data[chat_id]['name']
    user_data[chat_id]['donate'] = message.text
    bot.send_message(chat_id, f'Принято, {name}!\nТеперь скажи, сколько лет ты уже играешь?')
    bot.register_next_step_handler(message, get_experience)
    
def get_experience(message):
    """Главная функция: собирает всё воедино и отправляет анкету"""
    chat_id = message.chat.id
    name = user_data[chat_id]['name']
    
    try:
        experience = int(message.text)
        user_data[chat_id]['experience'] = experience
        
        # Собираем финальный текст анкеты
        final_text_user = (
            f'Спасибо за ответы, {name}!\n\n'
            f'Возраст: {user_data[chat_id]["age"]}\n'
            f'Донат: {user_data[chat_id]["donate"]}\n'
            f'Стаж игры: {experience} лет.\n\n'
            'Ваша заявка принята к рассмотрению!'
        )
        
        # Собираем текст ДЛЯ АДМИНА (чтобы отправить в группу)
        admin_report = (
            "📝 НОВАЯ АНКЕТА 📝\n"
            f"👤 Имя: {name}\n"
            f"🆔 Telegram ID: {message.from_user.id}\n"
            f"❄️ Возраст: {user_data[chat_id]['age']}\n"
            f"💰 Донат: {user_data[chat_id]['donate']}\n"
            f"⏳ Стаж: {experience} лет."
        )
        
        # Отправляем пользователю его копию
        bot.send_message(chat_id, final_text_user)
        
        # ОТПРАВЛЯЕМ АНКЕТУ В ГРУППУ
        try:
            bot.send_message(FORWARD_CHAT_ID, admin_report)
        except Exception as e:
             print(f"Ошибка отправки админу: {e}")
             bot.send_message(chat_id, "(Анкета собрана, но возникла ошибка при уведомлении администрации).")
            
    except ValueError:
        bot.send_message(chat_id, 'Пожалуйста, введите количество лет числом.')
        bot.register_next_step_handler(message, get_experience)


if __name__ == '__main__':
    bot.infinity_polling()