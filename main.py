import telebot
from telebot import types

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw'  # ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
ADMIN_IDS = [YOUR_TELEGRAM_ID]                 # ВАШ TELEGRAM ID! (можно несколько через запятую)
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}  # Хранит данные кандидата при заполнении анкеты
forwarding_users = {}  # Словарь {chat_id_кандидата: list_of_messages_in_group}
admin_reports_map = {}  # Связь системных анкет в группе с кандидатами


def get_user_chat_id(message):
    """Ищет chat-id кандидата по сообщению из группы."""
    if isinstance(message, int):  # Передан просто ID чата
        return message

    callback_data = getattr(message, "data", None)
    if callback_data and callback_data.startswith("reply_"):
        return int(callback_data.split("_")[1])
    
    original_message = message.reply_to_message
    if not original_message or original_message.from_user.id == bot.get_me().id:
        return None  # Это сообщение самого бота

    # Вариант А: Ответ на системное сообщение-заявку
    target_chat_id = admin_reports_map.get(original_message.message_id, {}).get("user_chat_id")

    # Вариант Б: Ответ на прямое пересланное сообщение кандидата
    for uid, messages in forwarding_users.items():
        if original_message.forward_from and original_message.forward_from.id == uid:
            target_chat_id = uid
            break

    return target_chat_id


@bot.message_handler(commands=["start"])
def handle_start(message):
    """
    Начинает опрос или перезапускает его.
    """
    if message.chat.type != "private":
        return

    chat_id = message.chat.id

    # Если пользователь уже начал анкету, но не завершил,
    # удаляем старые данные и начинаем заново.
    if chat_id in user_data:
        del user_data[chat_id]

    telegram_username = f"@{message.from_user.username}" if message.from_user.username else "@не_указан"
    
    user_data[chat_id] = {
        "name": None,
        "age": None,
        "donate": None,
        "discord": None,
        "microphone": None,
        "hours_per_day": None,
        "pve_rating": None,
        "pvp_rating": None,
        "experience": None,
        "telegram_username": telegram_username  
    }

    markup = types.ReplyKeyboardRemove()
    bot.send_message(chat_id, "📋 *Заполнение заявки* 📋\nКак тебя зовут?", reply_markup=markup, parse_mode="Markdown")


def process_poll(message):
    """
    Универсальный обработчик всей анкеты.
    Он автоматически определяет текущий незаполненный пункт.
    """
    chat_id = message.chat.id

    # Проверка статуса пользователя
    is_in_poll = chat_id in user_data and user_data[chat_id].get("name") is not None

    # ⚠️ Блок защиты от команд внутри анкеты
    # Если человек написал /start или любую другую команду
    if "/" in message.text[:1]:
        if is_in_poll:
            # Пользователь заполнял анкету — просим продолжить
            current_field = _find_current_field(user_data[chat_id])
            question = _get_question(current_field)
            bot.send_message(
                chat_id,
                f"❗ Ты сейчас заполняешь заявку.\nЧтобы начать заново, напиши слово **Сброс**."
                f"\n\nТекущий вопрос:\n{question}",
                parse_mode="Markdown",
            )
        else:
            # Обычная команда вне анкеты
            handle_start(message)
        
        return

    # ⚡️ Обработка шагов анкеты
    current_field = _find_current_field(user_data[chat_id])

    try:
        # Валидаторы ответов
        if current_field == "age":
            age = int(message.text.strip())
            if age <= 10:
                raise ValueError("Вы слишком молоды.")

        elif current_field.endswith("_rating"):  # pve_rating или pvp_rating
            rating = int(message.text.strip())
            if not (1 <= rating <= 10):
                raise ValueError("Нужно ввести число от 1 до 10!")

        # Сохранение ответа
        user_data[chat_id][current_field] = message.text.strip()
    
    except Exception as e:
        error_text = str(e) or "Пожалуйста, введите корректные данные."
        bot.send_message(
            chat_id,
            f"<b>Ошибка:</b>\n{error_text}\n\nВопрос повторяется.",
            parse_mode="HTML",
        )
        return

    # Переход к следующему шагу
    next_field = _find_current_field(user_data[chat_id])  # Следующий пустой пункт
    if next_field:
        question = _get_question(next_field)
        bot.send_message(chat_id, question, parse_mode=None)
    else:
        # Анкета завершена
        send_application(chat_id)


def _find_current_field(data):
    """
    Ищем первый незаполненный пункт анкеты.
    Возвращает название поля или None, если всё заполнено.
    """
    fields_order = [
        "name",
        "age",
        "donate",
        "discord",
        "microphone",
        "pve_rating",
        "pvp_rating",
        "hours_per_day",
        "experience",
    ]

    for field in fields_order:
        if data.get(field) is None:
            return field
    return None


def _get_question(field_name):
    """Возвращает текст вопроса по названию поля."""
    questions = {
        "name": "Как тебя зовут?",
        "age": "Сколько тебе лет?",
        "donate": "Какой у вас донат в игре? (например: Нет, Бронза)",
        "discord": "Ваш дискорд?",
        "microphone": "Есть ли у тебя микрофон? (Да/Нет)",
        "pve_rating": "Оцените своё ПвЕ по шкале от 1 до 10.",
        "pvp_rating": "Теперь оцените своё ПвП по шкале от 1 до 10.",
        "hours_per_day": "Сколько часов в день ты можешь играть?\n(Например: 3 часа)",
        "experience": "Теперь скажи, сколько времени ты уже играешь в проект?\n(Например: 2 года, 5 месяцев)",
    }
    return questions[field_name]


def send_application(chat_id):
    """
    Отправляет собранную анкету в группу и включает режим свободной переписки.
    """
    experience_text = user_data[chat_id]["experience"]

    final_text_user = (
        f"Спасибо за ответы, <b>{user_data[chat_id]['name']}</b>!\n\n"
        f"🎮 ПвЕ: {user_data[chat_id]['pve_rating']}/10\n"
        f"🔥 ПвП: {user_data[chat_id]['pvp_rating']}/10\n"
        f"Часов в день: {user_data[chat_id]['hours_per_day']}\n"
        f"Стаж игры: {experience_text}.\n\n"
        "<i>Твоя заявка принята к рассмотрению!</i>"
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

    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report, parse_mode="HTML")

    # Сохраняем связь сообщения-анкеты с кандидатом
    # Чтобы администратор мог ответить прямо под ней (*Reply*)
    admin_reports_map[sent_admin_msg.message_id] = {"user_chat_id": chat_id}

    # Включаем режим свободной переписки
    # Все последующие сообщения будут уходить в эту же группу
    forwarding_users.setdefault(chat_id, []).append(sent_admin_msg.message_id)

    # Очищаем словарь анкеты, оставив только ссылку на чат
    # Это важно для экономии памяти сервера
    user_data[chat_id] = {"telegram_username": user_data[chat_id]["telegram_username"]}

    # Отвечаем кандидату
    bot.send_message(chat_id, final_text_user, parse_mode="HTML")


# *** ГЛАВНЫЙ ОБРАБОТЧИК ***
@bot.message_handler(func=lambda m: True, content_types=[
    "text", 
    "photo",
    "video",
    "document",
    "voice",
    "sticker",
])
def main_router(message):
    """
    Работает только в личных сообщениях.
    Либо запускает анкету, либо обрабатывает шаги, либо пересылает сообщения в группу.
    """

    # Игнорируем всё из группы
    if message.chat.type != "private":
        return

    chat_id = message.chat.id

    # ⚠️ Проверка статуса пользователя
    # Мы сохраняем его chat_id в словаре даже после отправки анкеты
    # Но очищаем все поля кроме telegram_username
    is_in_poll = chat_id in user_data

    # Вариант А: Человек пишет /start
    # Если анкета пустая — запускаем; если есть — предлагаем сбросить
    if "/start" in message.text.lower():
        if is_in_poll:
            bot.send_message(
                chat_id,
                "*Внимание!*\nТы уже начал заполнять заявку.\n"
                "Если хочешь начать заново, напиши слово **Сброс**. "
                "Или продолжай отвечать на вопросы.",
                parse_mode="Markdown",
            )
        else:
            handle_start(message)
        return

    # Вариант Б: Команда сброса
    if message.text.lower() == "сброс":
        if chat_id in user_data:
            del user_data[chat_id]
        handle_start(message)
        return

    # Вариант В: Текстовые сообщения во время анкеты
    # Сюда попадает любой текст, включая случайный спам
    if message.content_type == "text":
        # Если анкета активна — обрабатываем её универсально
        if is_in_poll:
            process_poll(message)
            return

        # Любой другой текст при пустом словаре запускает старт
        handle_start(message)
        return

    # ⚡️ РЕЖИМ ПЕРЕСЫЛКИ ПОСЛЕ АНКЕТЫ
    # Сюда попадают фото, видео, голосовые и стикеры
    # После завершения анкеты каждое сообщение уходит в вашу группу
    if is_in_poll:
        # Пересылаем сообщение в группу
        forwarded_message = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)

        # Добавляем кнопку «Ответить кандидату»
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
        forwarding_users[chat_id].append(forwarded_message.message_id)


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
        full_text = f"✉️ *Ответ от администрации*:\n\n{message.text}", parse_mode="Markdown"

        # Отправка текста
        if message.content_type == "text":
            bot.send_message(candidate_id, *full_text)
        
        # Отправка медиа (фото, видео, документы)
        elif hasattr(message, message.content_type):
            file_id = getattr(getattr(message, message.content_type), "file_id")
            method = getattr(bot, f'send_{message.content_type}')
            
            kwargs = {}
            if hasattr(message, "caption") and message.caption:
                kwargs["caption"] = full_text[0]
            
            method(candidate_id, file_id, **kwargs)

        # Уведомление администратору о доставке
        bot.reply_to(message, "🗣 Сообщение доставлено.", parse_mode=None)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True)
