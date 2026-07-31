import telebot
from telebot import types
from threading import Timer # Для задержки кнопок

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw' # ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ВАШ ID ГРУППЫ!
ADMIN_IDS = [123456789]                 # ВАШ TELEGRAM ID!
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}  # Хранит данные во время заполнения анкеты
forwarding_users = {}  # Словарь формата {chat_id_кандидата: [list_of_messages_in_group]}
admin_reports_map = {}  # Связь сообщений-анкет в группе с кандидатами


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

    bot.send_message(chat_id, 'Привет! Как тебя зовут?', reply_markup=types.ReplyKeyboardRemove())
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
    Финал анкеты. Отправляет заявку в группу и включает режим свободной переписки.
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
        f"🔥 ПвП: {user_data[chat_id]['pvp_rating']}/10\n"
        f"⏳ Стаж: {experience_text}"
    )

    # ⚡️ Самое важное изменение здесь
    # Сохраняем связь системного сообщения в группе с кандидатом
    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report)
    admin_reports_map[sent_admin_msg.message_id] = {'user_chat_id': chat_id}

    del user_data[chat_id]

    # Отвечаем кандидату
    bot.send_message(chat_id, final_text_user)


# *** ОБРАБОТЧИК ОТВЕТОВ АДМИНА ***
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

    # Проверим статус пользователя
    is_in_poll = chat_id in forwarding_users and len(forwarding_users[chat_id]) > 0

    # Если пользователь заполняет анкету — продолжаем цепочку
    if chat_id in user_data and user_data[chat_id].get('name') is not None:
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
    # Все его сообщения будут уходить в вашу группу
    if is_in_poll:
        forwarded_message = bot.forward_message(
            GROUP_CHAT_ID,
            chat_id,
            message.message_id
        )

        # Запоминаем это сообщение, чтобы админ смог нажать кнопку ответа
        forwarding_users[chat_id].append(forwarded_message.message_id)

    # Если человек написал что-то рандомное вне анкеты
    else:
        bot.send_message(chat_id, "Чтобы подать заявку, напишите команду /start.")


# Обработчик нажатия кнопки ✉️ Ответить кандидату под любым его сообщением
@bot.callback_query_handler(func=lambda call: True)
def answer_to_candidate(call):
    candidate_id = int(call.data.split('_')[1])  # Извлекаем ID кандидата
    send_reply(call.message, candidate_id)


# Главный обработчик ответов администратора в группе
@bot.message_handler(func=lambda m: m.chat.id == GROUP_CHAT_ID and m.reply_to_message)
def answer_from_group(message):
    """
    Этот обработчик срабатывает, когда администратор отвечает (Reply)
    на любое сообщение внутри группы.
    """
    # Проверка, является ли администратор автором сообщения
    if message.from_user.id not in ADMIN_IDS:
        return

    original_message = message.reply_to_message

    # Вариант А: Админ ответил на системную анкету (сообщение бота).
    # Мы ищем его через словарь admin_reports_map.
    target_chat_id = admin_reports_map.get(original_message.message_id, {}).get('user_chat_id')

    # Вариант Б: Админ ответил на прямое сообщение кандидата (его фото/текст/голосовое),
    # которые были переадресованы после завершения анкеты.
    # Мы ищем его через список всех сообщений кандидата.
    if not target_chat_id and original_message.forward_date:
        for uid, messages in forwarding_users.items():
            if original_message.message_id in messages:
                target_chat_id = uid
                break

    # Вариант В: Страховка. На случай если вдруг все связи потерялись.
    # Парсим никнейм из текста анкеты вручную.
    if not target_chat_id:
        username_part = original_message.text.split('@')[1].split(')')[0]
        for uid, data in list(user_data.items()):
            if data['telegram_username'].endswith(username_part):
                target_chat_id = uid
                break

    # Отправляем ответ кандидату
    if target_chat_id:
        full_text = f"✉️ Ответ от администрации:\n\n{message.text}"

        # Отправляем кандидату
        try:
            if message.content_type == 'text':
                bot.send_message(target_chat_id, full_text)
            elif message.content_type == 'photo':
                file_id = message.photo[-1].file_id; caption = message.caption or ''
                bot.send_photo(target_chat_id, file_id, caption=full_text)
            elif message_content := getattr(message, message.content_type): # video/document/voice/sticker
                file_id = getattr(message_content, 'file_id')
                method = getattr(bot, f'send_{message.content_type}')
                method(target_chat_id, file_id, caption=full_text)
            
            # Уведомление администратору о доставке
            bot.reply_to(message, "🗣 Сообщение доставлено.", parse_mode=None)

        except Exception as e:
            print(f"[ERROR] Ошибка доставки: {e}")
            bot.reply_to(message, "🚫 Не удалось доставить сообщение.", parse_mode=None)
