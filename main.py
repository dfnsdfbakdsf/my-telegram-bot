import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8935278169:AAFfVupDDFrp2rHufzXxvw" # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
ADMIN_IDS = [123456789]                 # ДОБАВЬТЕ СЮДА СВОИ TELEGRAM ID
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
forwarding_users = {}  # Словарь для режима пересылки сообщений после анкеты


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Сразу начинаем анкету."""
    if message.chat.type != 'private':
        return

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
        'telegram_username': telegram_username,
        'forwarded_messages': []  # Список ID сообщений, которые он напишет после анкеты
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
        'Твоя заявка принята к рассмотрению!'
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

    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report, reply_markup=markup)

    # ✅ Сохраняем все способы найти этого человека в группе
    # Это либо системная анкета, либо любые его последующие сообщения
    user_data[chat_id]['forwarded_messages'].append(sent_admin_msg.message_id)

    del user_data[chat_id]


# *** ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ОТ КАНДИДАТОВ ***
@bot.message_handler(func=lambda m: True, content_types=[
    'text', 
    'photo',
    'video',
    'document',
    'voice',
    'sticker',
    'audio',
])
def main_router(message):
    """
    Работает только в личных чатах.
    Либо завершает анкету, либо пересылает сообщения в группу.
    """

    # Игнорируем всё, что происходит вне личного чата
    if message.chat.type != 'private':
        return

    chat_id = message.chat.id

    # Если человек пишет /start во время заполнения анкеты → пропускаем
    if '/start' in message.text and chat_id in user_data:
        return

    # ⚠️ Блок завершения анкеты
    # Если анкета ещё не заполнена, продолжаем её
    if chat_id in user_data and user_data[chat_id].get('name') is None:
        # Проверка нужна, чтобы избежать повторного вызова при нажатии кнопки
        if message.content_type == 'text' and message.text.startswith('/'):
            return

        # Продолжение цепочки вопросов
        if user_data[chat_id].get('age') is None:
            bot.register_next_step_handler(message, check_age)
            return
        elif user_data[chat_id].get('donate') is None:
            bot.register_next_step_handler(message, get_donate)
            return
        elif user_data[chat_id].get('discord') is None:
            bot.register_next_step_handler(message, get_discord)
            return
        elif user_data[chat_id].get('microphone') is None:
            bot.register_next_step_handler(message, get_microphone)
            return
        elif user_data[chat_id].get('pve_rating') is None:
            bot.register_next_step_handler(message, get_pve_rating)
            return
        elif user_data[chat_id].get('pvp_rating') is None:
            bot.register_next_step_handler(message, get_pvp_rating)
            return
        elif user_data[chat_id].get('hours_per_day') is None:
            bot.register_next_step_handler(message, get_hours)
            return
        elif user_data[chat_id].get('experience') is None:
            bot.register_next_step_handler(message, get_experience)
            return

    # ⚠️ Блок свободной переписки
    # После отправки анкеты каждое новое сообщение будет уходить в группу
    # Мы сохраняем ID каждого такого сообщения, чтобы админ мог ответить на него
    if chat_id not in forwarding_users:
        forwarding_users[chat_id] = []

    # Пересылка сообщения в группу
    forwarded_message = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)

    # Создаём кнопку ответа именно на это сообщение
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    button = types.InlineKeyboardButton(text='✉️ Ответить кандидату', callback_data=f'reply_{chat_id}')
    keyboard.add(button)

    # Прикрепляем эту кнопку к сообщению
    # Через несколько секунд она исчезнет, если нажать нельзя
    try:
        bot.edit_message_reply_markup(
            GROUP_CHAT_ID,
            forwarded_message.message_id,
            reply_markup=keyboard
        )
    except Exception:
        pass

    # Запоминаем ID этого сообщения, чтобы админ смог ответить на него
    forwarding_users[chat_id].append(forwarded_message.message_id)


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
