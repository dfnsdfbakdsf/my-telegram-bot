import telebot
from telebot import types
from threading import Timer # Для задержки кнопок

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHxvw' # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
ADMIN_IDS = [123456789]                 # ДОБАВЬТЕ СЮДА СВОИ TELEGRAM ID
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}  # Хранит данные кандидата при заполнении анкеты
forwarding_users = {}  # Словарь {chat_id_кандидата: list_of_messages_in_group}
admin_reports_map = {}  # Связь системных анкет в группе с кандидатами


def get_user_chat_id(message):
    """
    Ищет chat-id кандидата по сообщению из группы.
    Работает через Reply или кнопку.
    """
    if isinstance(message, int): # Передан просто ID чата
        return message

    callback_data = getattr(message, 'data', None)
    if callback_data and callback_data.startswith('reply_'):
        return int(callback_data.split('_')[1])
    
    original_message = message.reply_to_message
    if not original_message or original_message.from_user.id == bot.get_me().id:
        return None # Это системное сообщение бота, игнорируем

    # Вариант А: Ответ на системную заявку (сообщение бота)
    target_chat_id = admin_reports_map.get(original_message.message_id, {}).get('user_chat_id')

    # Вариант Б: Ответ на прямое сообщение кандидата (его фото/текст/голосовое)
    for uid, messages in forwarding_users.items():
        if original_message.message_id in messages:
            target_chat_id = uid
            break

    # Вариант В: Страховка. Парсим никнейм вручную.
    # На случай, если вдруг все связи потерялись.
    if not target_chat_id:
        username_part = original_message.text.split('@')[1].split(')')[0]
        for uid, data in user_data.items():
            if data['telegram_username'].endswith(username_part):
                target_chat_id = uid
                break

    return target_chat_id


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Запускает опрос."""
    if message.chat.type != 'private':
        return

    chat_id = message.chat.id

    # Проверка, чтобы избежать дублирования данных
    if chat_id in user_data:
        del user_data[chat_id]

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
    bot.register_next_step_handler(message, process_poll)


def process_poll(message):
    """
    Универсальный обработчик всех шагов анкеты.
    Он автоматически определяет, какой вопрос сейчас актуален.
    """
    chat_id = message.chat.id

    # ⚠️ Блок защиты от команд внутри анкеты
    # Если человек написал /start или любую другую команду
    if '/start' in message.text.lower() or '/' in message.text[:1]:
        # Удаляем старые данные, чтобы не было путаницы
        if chat_id in user_data:
            del user_data[chat_id]
        
        # Предупреждаем человека
        bot.send_message(
            chat_id,
            "Ты начал заполнять анкету, но отправил команду.\n"
            "Если хочешь продолжить, напиши ответ на последний вопрос:\n\n"
            + _get_current_question(chat_id),
            parse_mode='HTML'
        )
        return

    # ⚡️ Определяем текущий шаг
    current_field = next((
        field for field in [
            'name',
            'age',
            'donate',
            'discord',
            'microphone',
            'pve_rating',
            'pvp_rating',
            'hours_per_day',
            'experience'
        ] if user_data.get(chat_id).get(field) is None
    ), None)

    # Пользователь ещё не начал анкету
    if current_field is None:
        handle_start(message)
        return

    try:
        # Проверки валидности ответов
        if current_field == 'age':
            age = int(message.text.strip())
            if age <= 10:
                raise ValueError("Вы слишком молоды")
        
        elif current_field.endswith('_rating'): # pve_rating или pvp_rating
            rating = int(message.text.strip())
            if not (1 <= rating <= 10):
                raise ValueError()

        # Записываем ответ
        user_data[chat_id][current_field] = message.text.strip().capitalize()
    
    except Exception as e:
        error_text = str(e) or 'Пожалуйста, введите корректные данные.'
        bot.send_message(
            chat_id,
            f"<b>Ошибка:</b>\n{error_text}\n\n" +
            _get_current_question(chat_id),
            parse_mode='HTML'
        )
        return

    # Переход к следующему шагу
    handlers = {
        'name': lambda msg: bot.send_message(msg.chat.id, 'Сколько тебе лет?'),
        'age': lambda msg: bot.send_message(msg.chat.id, 'А какой у вас донат в игре?'),
        'donate': lambda msg: bot.send_message(msg.chat.id, 'Ваш дискорд?'),
        'discord': lambda msg: bot.send_message(msg.chat.id, 'Есть ли у тебя микрофон? (Да/Нет)'),
        'microphone': lambda msg: bot.send_message(msg.chat.id, 'Оцените своё ПвЕ по шкале от 1 до 10.'),
        'pve_rating': lambda msg: bot.send_message(msg.chat.id, 'Теперь оцените своё ПвП по шкале от 1 до 10.'),
        'pvp_rating': lambda msg: bot.send_message(msg.chat.id, 'Сколько часов в день ты можешь играть?\n(Например: 3 или "пару часов")'),
        'hours_per_day': lambda msg: bot.send_message(msg.chat.id, 'Теперь скажи, сколько времени ты уже играешь в проект?\n(Например: 2 года, 5 месяцев)')
    }

    handler = handlers[current_field](message)

    # Последний шаг — отправка заявки в группу
    if current_field == 'experience':
        experience_text = message.text.strip()

        final_text_user = (
            f'Спасибо за ответы, <b>{user_data[chat_id]["name"]}</b>!\n\n'
            f'<b>Возраст</b>: {user_data[chat_id]["age"]}\n'
            f'<b>Донат</b>: {user_data[chat_id]["donate"]}\n'
            f'<b>Дискорд</b>: {user_data[chat_id]["discord"]}\n'
            f'<b>Микрофон</b>: {user_data[chat_id]["microphone"]}\n'
            f'<b>Часов в день</b>: {user_data[chat_id]["hours_per_day"]}\n'
            f'<b>🎮 ПвЕ</b>: {user_data[chat_id]["pve_rating"]}/10\n'
            f'<b>🔥 ПвП</b>: {user_data[chat_id]["pvp_rating"]}/10\n'
            f'<b>Стаж игры</b>: {experience_text}.\n\n'
            '<i>Твоя заявка принята к рассмотрению!</i>'
        )

        admin_report = (
            "📋 НОВАЯ ЗАЯВКА 📋\n"
            f"👤 Имя: {user_data[chat_id]['name']} ({user_data[chat_id]['telegram_username']})\n"
            f"❄️ Возраст: {user_data[chat_id]['age']}\n"
            f"💰 Донат: {user_data[chat_id]['donate']}\n"
            f"🖥️ Дискорд: {user_data[chat_id]['discord']}\n"
            f"🎤 Микрофон: {user_data[chat_id]['microphone']}\n"
            f"⏱ Часов в день: {user_data[chat_id]['hours_per_day']}\n"
            f"🎮 ПвЕ: {user_data[chat_id]['pve_rating']}/10\n"
            f"🔥 ПвП: {user_data[chat_id]['pvp_rating']}/10\n"
            f"⏳ Стаж: {experience_text}"
        )

        sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report)

        # Сохраняем связь между сообщением-заявкой и кандидатом
        # Чтобы администратор мог нажать Reply прямо под ней
        admin_reports_map[sent_admin_msg.message_id] = {'user_chat_id': chat_id}

        # Включаем режим свободной переписки
        # Все последующие сообщения будут уходить в группу
        forwarding_users.setdefault(chat_id, []).append(sent_admin_msg.message_id)

        # Очищаем словарь анкеты, оставив только ссылку на чат
        user_data[chat_id] = {'telegram_username': user_data[chat_id]['telegram_username']}

        # Отвечаем кандидату
        bot.send_message(chat_id, final_text_user, parse_mode='HTML')


def _get_current_question(chat_id):
    """
    Вспомогательная функция для получения текущего вопроса.
    Нужна для вывода ошибки пользователю.
    """
    current_field = next((
        field for field in [
            'name',
            'age',
            'donate',
            'discord',
            'microphone',
            'pve_rating',
            'pvp_rating',
            'hours_per_day',
            'experience'
        ] if user_data.get(chat_id).get(field) is None
    ))

    questions = {
        'name': 'Как тебя зовут?',
        'age': 'Сколько тебе лет?',
        'donate': 'Какой у вас донат в игре?',
        'discord': 'Ваш дискорд?',
        'microphone': 'Есть ли у тебя микрофон? (Да/Нет)',
        'pve_rating': 'Оцените своё ПвЕ по шкале от 1 до 10.',
        'pvp_rating': 'Теперь оцените своё ПвП по шкале от 1 до 10.',
        'hours_per_day': 'Сколько часов в день ты можешь играть?\n(Например: 3 или "пару часов")',
        'experience': 'Теперь скажи, сколько времени ты уже играешь в проект?\n(Например: 2 года, 5 месяцев)'
    }

    return f"<b>{questions[current_field]}</b>"


# *** ОБРАБОТЧИК РЕЖИМА ПЕРЕСЫЛКИ ***
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

    # ⚠️ Проверка статуса пользователя
    # Мы сохраняем его chat_id в словаре даже после отправки анкеты
    # Но удаляем все поля кроме telegram_username
    is_in_poll = chat_id in user_data

    # Если это /start — запускаем анкету заново
    if '/start' in message.text.lower():
        handle_start(message)
        return

    # Если пользователь заполняет анкету — обрабатывает её универсально
    if is_in_poll:
        # Вызов универсального обработчика
        process_poll(message)
        return

    # ⚡️ Режим свободной переписки
    # После завершения анкеты каждое сообщение уходит в группу
    forwarded_message = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)

    # Прикрепляем кнопку ответа с задержкой
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    button = types.InlineKeyboardButton(text='✉️ Ответить кандидату', callback_data=f'reply_{chat_id}')
    keyboard.add(button)

    def attach_button():
        try:
            bot.edit_message_reply_markup(
                GROUP_CHAT_ID,
                forwarded_message.message_id,
                reply_markup=keyboard
            )
        except Exception as e:
            print(f'[ERROR] Не удалось прикрепить кнопку: {e}')
    
    Timer(1.5, attach_button).start()

    # Запоминаем это сообщение, чтобы админ мог нажать кнопку
    forwarding_users.setdefault(chat_id, []).append(forwarded_message.message_id)


# Обработчик нажатия кнопки ✉️ Ответить кандидату
@bot.callback_query_handler(func=lambda call: True)
def answer_to_candidate(call):
    candidate_id = get_user_chat_id(call)
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

    # Получаем ID кандидата
    candidate_id = get_user_chat_id(message)

    # Отправляем ответ кандидату
    if candidate_id:
        full_text = f"✉️ <b>Ответ от администрации</b>:\n\n{message.text}", parse_mode='HTML'

        try:
            if message.content_type == 'text':
                bot.send_message(candidate_id, *full_text)
            elif message_content := getattr(message, message.content_type):
                file_id = getattr(message_content, 'file_id')
                method = getattr(bot, f'send_{message.content_type}')
                kwargs = {}
                if hasattr(message, 'caption') and message.caption:
                    kwargs['caption'] = full_text[0]
                method(candidate_id, file_id, **kwargs)
            
            # Уведомление администратору о доставке
            bot.reply_to(message, "🗣 Сообщение доставлено.", parse_mode=None)

        except Exception as e:
            print(f"[ERROR] Ошибка доставки: {e}")
            bot.reply_to(message, "🚫 Не удалось доставить сообщение.", parse_mode=None)

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()
