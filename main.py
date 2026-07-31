import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw' # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
ADMIN_IDS = [123456789]                 # ДОБАВЬТЕ СЮДА СВОИ TELEGRAM ID
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}  # Хранит данные пользователя во время заполнения анкеты
forwarding_users = {}  # Словарь для режима пересылки сообщений после анкеты


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Сразу начинаем опрос."""
    if message.chat.type != 'private':
        return

    chat_id = message.chat.id
    
    telegram_username = f'@{message.from_user.username}' if message.from_user.username else '@не_указан'
    
    user_data[chat_id] = {
        'name': None,
        'age': None,
        'donate': None,
        'discord': None,
        'microphone': None,
        'hours_per_day': None,
        'pve_rating': None,
        'pvp_rating': None,
        'experience': None,
        'telegram_username': telegram_username  
    }

    bot.send_message(chat_id, 'Привет! Как тебя зовут?')
    bot.register_next_step_handler(message, get_name)


def get_name(message):
    chat_id = message.chat.id
    user_data[chat_id]['name'] = message.text.strip()
    bot.send_message(chat_id, 'Сколько тебе лет?', reply_markup=types.ReplyKeyboardRemove())
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
        if not (1 <= rating <= 10):
            raise ValueError('Нужно ввести число от 1 до 10!')

        user_data[chat_id]['pve_rating'] = rating
        bot.send_message(chat_id, 'Теперь оцените своё ПвП по шкале от 1 до 10.')
        bot.register_next_step_handler(message, get_pvp_rating)

    except ValueError as e:
        error_text = str(e)
        bot.send_message(chat_id, error_text)
        bot.register_next_step_handler(message, get_pve_rating)


def get_pvp_rating(message):
    chat_id = message.chat.id
    try:
        rating = int(message.text)
        if not (1 <= rating <= 10):
            raise ValueError('Нужно ввести число от 1 до 10!')

        user_data[chat_id]['pvp_rating'] = rating
        bot.send_message(chat_id, 'Сколько часов в день ты можешь играть?\n(Например: 3 или "пару часов")')
        bot.register_next_step_handler(message, get_hours)

    except ValueError as e:
        error_text = str(e)
        bot.send_message(chat_id, error_text)
        bot.register_next_button_handler(message, get_pvp_rating)


def get_hours(message):
    chat_id = message.chat.id
    user_data[chat_id]['hours_per_day'] = message.text.strip()
    bot.send_message(
        chat_id,
        'Теперь скажи, сколько времени ты уже играешь в проект?\n(Например: 2 года, 5 месяцев)'
    )
    bot.register_next_step_handler(message, get_experience)


def get_experience(message):
    """
    Финал анкеты.
    Отправляет заявку в группу и включает режим свободной переписки.
    """
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
        'Твоя заявка принята к рассмотрению!'
    )

    admin_report = (
        "📋 НОВАЯ ЗАЯВКА 📋\n"
        f"👤 Имя: {user_data[chat_id]['name']} ({user_data[chat_id]['telegram_username']})\n"
        f"❄️ Возраст: {user_data[chat_id]['age']}\n"
        f"💰 Донат: {user_data[chat_id]['donate']}\n"
        f"🖥️ Дискорд: {user_data[chat_id]['discord']}\n"
        f"🎤 Микрофон: {user_data[chat_id]['microphone']}\n"
        f"⏱️ Часов в день: {user_data[chat_id]['hours_per_day']}\n"
        f"🎮 ПвЕ: {user_data[chat_id]['pve_rating']}/10\n"
        f"🔥 ПвП: {user[comment]: <>('chat_id')['pvp_rating']}/10\n"
        f"⏳ Стаж: {experience_text}."
    )

    # Сохраняем ссылку на системное сообщение-заявку
    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report)
    forwarding_users.setdefault(chat_id, []).append(sent_admin_msg.message_id)

    # Включаем режим свободного чата
    del user_data[chat_id]

    # Отвечаем кандидату
    bot.send_message(chat_id, final_text_user)


# *** ГЛАВНЫЙ ОБРАБОТЧИК ***
@bot.message_handler(func=lambda m: True, content_types=[
    'text', 
    'photo',
    'video',
    'document',
    'voice',
    'sticker',
])
def main_router(message):
    """
    Работает только в личных сообщениях.
    Либо завершает анкету, либо пересылает сообщения в группу.
    """

    # Игнорируем всё из группы
    if message.chat.type != 'private':
        return

    chat_id = message.chat.id

    # Если это /start — запускаем анкету заново
    if '/start' in message.text.lower():
        handle_start(message)
        return

    # Если пользователь заполняет анкету — продолжаем цепочку
    if chat_id in user_data and user_data[chat_id].get('name'):
        # Проверим текущий шаг
        if user_data[chat_id].get('age') is None:
            check_age(message)
        elif user_data[chat_id].get('donate') is None:
            get_donate(message)
        elif user_data[chat_id].get('discord') is None:
            get_discord(message)
        elif user_data[chat_id].get('microphone') is None:
            get_microphone(message)
        elif user_data[chat_id].get('pve_rating') is None:
            get_pve_rating(message)
        elif user_data[chat_id].get('pvp_rating') is None:
            get_pvp_rating(message)
        elif user_data[chat_id].get('hours_per_day') is None:
            get_hours(message)
        else:
            # Последний шаг перед отправкой анкеты
            get_experience(message)
        
        return

    # Пользователь завершил анкету → включаем режим свободной переписки
    # Все его сообщения будут уходить в группу
    forwarded_message = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)

    # Добавляем кнопку ответа под этим сообщением
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    button = types.InlineKeyboardButton(text='✉️ Ответить кандидату', callback_data=f'reply_{chat_id}')
    keyboard.add(button)

    # Прикрепляем её через несколько секунд, чтобы она успела появиться
    def attach_button():
        try:
            bot.edit_message_reply_markup(
                GROUP_CHAT_ID,
                forwarded_message.message_id,
                reply_markup=keyboard
            )
        except Exception:
            pass  # Не страшно, если кнопка не прикрепилась

    from threading import Timer
    Timer(1.5, attach_button).start()  # Задержка нужна, т.к. Telegram иногда блокирует моментальное редактирование

    # Запоминаем это сообщение, чтобы админ мог нажать кнопку
    forwarding_users.setdefault(chat_id, []).append(forwarded_message.message_id)


# Обработчик кнопок в группе
@bot.callback_query_handler(func=lambda call: True)
def answer_to_candidate(call):
    """
    Администратор нажал кнопку «Ответить кандидату»
    под любым сообщением кандидата в группе.
    """
    chat_id = int(call.data.split('_')[1])  # Извлекаем ID кандидата
    target_chat_id = chat_id

    # Просим администратора написать текст ответа
    msg = bot.send_message(
        call.message.chat.id,
        f"Введите текст вашего сообщения кандидату @{call.from_user.username}:",
        parse_mode=None
    )

    # Ждём ввода текста
    bot.register_next_step_handler(msg, send_reply, target_chat_id)


def send_reply(message, target_chat_id):
    """
    Отправляет ответ кандидату с пометкой администрации.
    """
    # Формируем сообщение с подписью
    full_text = f"✉️ Ответ от администрации:\n\n{message.text}"

    # Отправляем кандидату
    try:
        if message.content_type == 'text':
            bot.send_message(target_chat_id, full_text)
        elif message.content_type == 'photo':
            file_id = message.photo[-1].file_id; caption = message.caption or ''
            bot.send_photo(target_chat_id, file_id, caption=full_text)
        elif message.content_type == 'video':
            file_id = message.video.file_id; caption = message.caption or ''
            bot.send_video(target_chat_id, file_id, caption=full_text)
        elif message.content_type == 'document':
            file_id = message.document.file_id; caption = message.caption or ''
            bot.send_document(target_chat_id, file_id, caption=full_text)
        elif message.content_type == 'voice':
            file_id = message.voice.file_id
            bot.send_voice(target_chat_id, file_id, caption=full_text)
        elif message.content_type == 'sticker':
            file_id = message.sticker.file_id
            bot.send_sticker(target_chat_id, file_id)

        # Уведомление администратору о доставке
        bot.reply_to(message, "🗣 Сообщение доставлено.")

    except Exception as e:
        print(f"Ошибка доставки: {e}")
        bot.reply_to(message, "🚫 Не удалось доставить сообщение.", parse_mode=None)


if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
