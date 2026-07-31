import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw' # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
admin_reports_map = {}
forwarding_users = {}  # Словарь для режима пересылки сообщений после анкеты

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Сразу начинаем анкету с вопроса про имя."""
    chat_id = message.chat.id

    telegram_username = f'@{message.from_user.username}' if message.from_user.username else '@не_указан'
    
    user_data[chat_id] = {
        'name': None,
        'age': None,
        'donate': None,
        'experience': None,
        'discord': None,
        'microphone': None,
        'hours_per_day': None,
        'pve_rating': None,
        'pvp_rating': None,
        'telegram_username': telegram_username  
    }

    bot.send_message(chat_id, 'Привет! Как тебя зовут?')
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text.strip()
    bot.send_message(chat_id, 'Сколько тебе лет?')
    bot.register_next_step_handler(message, check_age)

def check_age(message):
    chat_id = message.chat.id
    try:
        age = int(message.text)
        if age <= 10:
            raise ValueError("Вы слишком молоды")
        user_data[chat_id]['age'] = age
        bot.send_message(chat_id, 'Отлично!\nА какой у вас донат в игре?')
        bot.register_next_step_handler(message, get_donate)
    except ValueError as e:
        error_text = str(e) or 'Пожалуйста, введи число.'
        bot.send_message(chat_id, error_text)
        bot.register_next_step_handler(message, check_age)

def get_donate(message):
    chat_id = message.chat.id
    user_data[chat_id]['donate'] = message.text.strip().capitalize()
    bot.send_message(chat_id, 'Ваш дискорд?')
    bot.register_next_step_handler(message, get_discord)

def get_discord(message):
    chat_id = message.chat.id
    user_data[chat_id]['discord'] = message.text.strip()
    bot.send_message(chat_id, 'Есть ли у тебя микрофон? (Да/Нет)')
    bot.register_next_step_handler(message, get_microphone)

def get_microphone(message):
    chat_id = message.chat.id
    user_data[chat_id]['microphone'] = message.text.strip().capitalize()
    bot.send_message(chat_id, 'Оцените своё ПвЕ по шкале от 1 до 10.')
    bot.register_next_step_handler(message, get_pve_rating)

def get_pve_rating(message):
    chat_id = message.chat.id
    try:
        rating = int(message.text)
        if rating < 1 or rating > 10:
            raise ValueError("Нужно ввести число от 1 до 10!")
        user_data[chat_id]['pve_rating'] = rating
        bot.send_message(chat_id, 'Теперь оцените своё ПвП по шкале от 1 до 10.')
        bot.register_next_step_handler(message, get_pvp_rating)
    except ValueError as e:
        error_text = str(e) or 'Пожалуйста, введи число от 1 до 10!'
        bot.send_message(chat_id, error_text)
        bot.register_next_step_handler(message, get_pve_rating)

def get_pvp_rating(message):
    chat_id = message.chat.id
    try:
        rating = int(message.text)
        if rating < 1 or rating > 10:
            raise ValueError("Нужно ввести число от 1 до 10!")
        user_data[chat_id]['pvp_rating'] = rating
        bot.send_message(chat_id, 'Сколько часов в день ты можешь играть?\n(Например: 3 или "пару часов")')
        bot.register_next_step_handler(message, get_hours)
    except ValueError as e:
        error_text = str(e) or 'Пожалуйста, введи число от 1 до 10!'
        bot.send_message(chat_id, error_text)
        bot.register_next_step_handler(message, get_pvp_rating)

def get_hours(message):
    chat_id = message.chat.id
    user_data[chat_id]['hours_per_day'] = message.text.strip()
    bot.send_message(chat_id, 'Теперь скажи, сколько времени ты уже играешь в проект?\n(Например: 2 года, 5 месяцев)')
    bot.register_next_step_handler(message, get_experience)
    
def get_experience(message):
    """Финал анкеты и переход в режим свободного чата"""
    chat_id = message.chat.id
    experience_text = message.text.strip()
    if not experience_text:
        bot.send_message(chat_id, 'Пожалуйста, напиши свой стаж.')
        bot.register_next_step_handler(message, get_experience)
        return

    user_data[chat_id]['experience'] = experience_text

    final_text_user = (
        f'Спасибо за ответы, {user_data[chat_id]["name"]}!\n\n'
        f'Возраст: {user_data[chat_id]["age"]}\n'
        f'Донат: {user_data[chat_id]["donate"]}\n'
        f'Дискорд: {user_data[chat_id]["discord"]}\n'
        f'Микрофон: {user_data[chat_id]["microphone"]}\n'
        f'Часов в день: {user_data[chat_id]["hours_per_day"]}\n'
        f'🎮 ПвЕ: {user_data[chat_id]["pve_rating"]}/10\n'
        f'🔥 ПвП: {user_data[chat_id]["pvp_rating"]}/10\n'
        f'Стаж игры: {experience_text}.\n\n'
        'Твоя заявка принята к рассмотрению!\n\n'
        'Теперь ты можешь присылать сюда скриншоты, видео или вопросы — они будут видны руководству.\n'
        'Чтобы выключить этот режим, напиши /stop.'
    )
    
    markup = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(
        text="📩 Написать кандидату",
        url=f'tg://resolve?domain={user_data[chat_id]["telegram_username"].lstrip("@")}'
    )
    markup.add(url_button)

    admin_report = (
        "📋 НОВАЯ ЗАЯВКА 📋\n"
        f"👤 Имя: {user_data[chat_id]['name']} ({user_data[chat_id]['telegram_username']})\n"
        f"❄️ Возраст: {user_data[chat_id]['age']}\n"
        f"💰 Донат: {user_data[chat_id]['donate']}\n"
        f"🖥️ Дискорд: {user_data[chat_id]['discord']}\n"
        f"🎤 Микрофон: {user_data[chat_id]['microphone']}\n"
        f"⏱️ Часов в день: {user_data[chat_id]['hours_per_day']}\n"
        f"🎮 ПвЕ: {user_data[chat_id]['pve_rating']}/10\n"
        f"🔥 ПвП: {user_data[chat_id]['pvp_rating']}/10\n"
        f"⏳ Стаж: {experience_text}."
    )

    bot.send_message(chat_id, final_text_user)
    
    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report, reply_markup=markup)
    admin_reports_map[sent_admin_msg.message_id] = {'user_chat_id': chat_id}
    
    # *** ВКЛЮЧЕНИЕ РЕЖИМА ЧАТА ***
    forwarding_users[chat_id] = True
    
    del user_data[chat_id]
    _cleanup_old_reports(sent_admin_msg.message_id)

def _cleanup_old_reports(current_msg_id: int):
    threshold = current_msg_id - 1000
    keys_to_delete = [key for key in list(admin_reports_map.keys()) if key < threshold]
    for key in keys_to_delete:
        admin_reports_map.pop(key, None)

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'voice', 'sticker', 'audio', 'location', 'contact'])
def main_router(message):
    """
    Главный диспетчер. Проверяет, не находится ли юзер в режиме пересылки.
    Если да — шлем всё в группу.
    """
    chat_id = message.chat.id

    # Если пользователь включил режим отправки сообщений в группу
    if chat_id in forwarding_users:
        try:
            # Пересылаем сообщение В ТОЧНОСТИ как оно пришло (сохраняя автора!)
            bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Ошибка отправки: {e}")
        return

    # Если это текстовые команды управления
    if message.content_type == 'text':
        txt = message.text.lower()
        
        if txt == '/stop':
            if chat_id in forwarding_users:
                del forwarding_users[chat_id]
                bot.send_message(chat_id, "🔴 Режим свободной отправки отключен. Чтобы подать новую заявку, напиши /start.")
            else:
                bot.send_message(chat_id, "Режим и так был выключен.", reply_markup=types.ReplyKeyboardRemove())
            return
            
        # Если человек просто написал боту рандомный текст НЕ в режиме заявки
        help_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
        help_markup.add(types.KeyboardButton("✍️ Начать подачу заявки"))
        bot.send_message(chat_id, "Я жду команд:\n• /start — чтобы подать заявку.\n• /stop — если вы писали в чат и хотите остановиться.", reply_markup=help_markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    """Обработчик кнопок под заявкой в группе (для админов)"""
    if call.data.startswith("reply_"):
        parts = call.data.split('_')
        target_id = int(parts[1])
        msg_id_to_reply = int(parts[2])
        
        # Просим админа написать ответ пользователю
        bot.answer_callback_query(call.id, "Напишите ответ этому пользователю:")
        bot.register_next_step_handler_by_chat_id(call.message.chat.id, lambda m: send_reply_to_user(m, target_id, msg_id_to_reply))

def send_reply_to_user(message, target_chat_id, replied_to_msg_id):
    """Пересылка ответа админа пользователю"""
    try:
        bot.send_message(target_chat_id, f"✉️ Ответ от администрации на вашу заявку:\n\n{message.text}")
    except Exception as e:
        print(f"Ошибка при отправке личного сообщения: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
