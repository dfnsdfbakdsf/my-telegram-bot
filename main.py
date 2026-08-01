import telebot
from telebot import types
import time
import logging

# Включаем логирование для отладки
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw' # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
ADMIN_IDS = [6805635660,7334259357]                 # *** ДОБАВЬТЕ СЮДА СВОИ TELEGRAM ID ***
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
admin_reports_map = {}
forwarding_users = {}  # Словарь для режима пересылки сообщений после анкеты


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Сразу начинаем анкету с вопроса про имя."""
    chat_id = message.chat.id
    
    # Игнорируем команду /start в группе администрации
    if chat_id == GROUP_CHAT_ID:
        bot.reply_to(message, "❌ Эта команда не работает в группе. Напишите мне в личные сообщения!")
        return

    # Проверяем, не заполняет ли уже пользователь анкету
    if chat_id in user_data or chat_id in forwarding_users:
        bot.send_message(chat_id, "Вы уже проходите анкету или уже заполнили её!")
        return

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
        'Твоя заявка принята к рассмотрению!\n'
        'Теперь ты можешь писать в этом чате, и сообщения будут пересылаться администрации.'
    )
    
    # Создаем кнопку для связи с кандидатом
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
        f"⏳ Стаж: {experience_text}.\n\n"
        f"📌 Чтобы ответить кандидату, просто ответьте (reply) на это сообщение!"
    )

    bot.send_message(chat_id, final_text_user)
    
    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report, reply_markup=markup)
    
    # Сохраняем информацию о заявке
    admin_reports_map[sent_admin_msg.message_id] = {
        'user_chat_id': chat_id,
        'user_name': user_data[chat_id]['name'],
        'user_username': user_data[chat_id]['telegram_username'],
        'timestamp': time.time()
    }
    
    logger.info(f"✅ Заявка сохранена! ID сообщения: {sent_admin_msg.message_id}, Пользователь: {chat_id}")
    
    # Включаем режим свободной отправки сообщений от кандидата в группу
    forwarding_users[chat_id] = True
    
    # Очищаем данные пользователя
    del user_data[chat_id]
    _cleanup_old_reports(sent_admin_msg.message_id)

def _cleanup_old_reports(current_msg_id: int):
    """Очистка старых записей в admin_reports_map"""
    threshold = current_msg_id - 1000
    keys_to_delete = [key for key in list(admin_reports_map.keys()) if key < threshold]
    for key in keys_to_delete:
        admin_reports_map.pop(key, None)


# *** КОМАНДЫ ДЛЯ АДМИНИСТРАТОРОВ (работают в ЛС и в группе) ***
@bot.message_handler(commands=['applications'])
def list_applications(message):
    """Показать активные заявки"""
    # Проверяем, что пользователь - администратор
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет прав для этой команды!")
        return
    
    if not admin_reports_map:
        bot.reply_to(message, "📭 Нет активных заявок.")
        return
    
    text = "📋 **Активные заявки:**\n\n"
    for msg_id, data in admin_reports_map.items():
        user_name = data.get('user_name', 'Неизвестно')
        user_username = data.get('user_username', '@не_указан')
        timestamp = data.get('timestamp', 0)
        time_ago = int((time.time() - timestamp) / 60) if timestamp else 0
        
        text += f"👤 {user_name} {user_username}\n"
        text += f"🆔 ID пользователя: {data['user_chat_id']}\n"
        text += f"📨 ID сообщения с заявкой: {msg_id}\n"
        text += f"⏱️ {time_ago} мин. назад\n"
        text += f"📌 Ответьте на сообщение #{msg_id} в группе\n\n"
    
    bot.reply_to(message, text)


@bot.message_handler(commands=['status'])
def status_command(message):
    """Проверить статус бота"""
    # Проверяем, что пользователь - администратор
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет прав для этой команды!")
        return
    
    status_text = (
        "📊 **Статус бота**\n\n"
        f"👥 Активных заявок: {len(admin_reports_map)}\n"
        f"📨 Пользователей в режиме пересылки: {len(forwarding_users)}\n"
        f"📝 Пользователей в процессе анкеты: {len(user_data)}\n\n"
        f"📋 ID группы: {GROUP_CHAT_ID}\n"
        f"👤 Ваш ID: {message.from_user.id}\n"
    )
    
    # Добавляем список пользователей в режиме пересылки
    if forwarding_users:
        status_text += "\n👥 Пользователи в режиме пересылки:\n"
        for user_id in forwarding_users:
            status_text += f"  - {user_id}\n"
    
    bot.reply_to(message, status_text)


@bot.message_handler(commands=['clear_applications'])
def clear_applications(message):
    """Очистить все заявки"""
    # Проверяем, что пользователь - администратор
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет прав для этой команды!")
        return
    
    admin_reports_map.clear()
    bot.reply_to(message, "🗑️ Все заявки очищены!")


@bot.message_handler(commands=['myid'])
def myid_command(message):
    """Показать свой ID"""
    bot.reply_to(message, f"🆔 Ваш ID: {message.from_user.id}")


@bot.message_handler(commands=['help_admin'])
def help_admin(message):
    """Помощь для администраторов"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет прав для этой команды!")
        return
    
    help_text = (
        "🤖 **Команды для администраторов:**\n\n"
        "📋 `/applications` - Показать все активные заявки\n"
        "📊 `/status` - Статус бота\n"
        "🗑️ `/clear_applications` - Очистить все заявки\n"
        "🆔 `/myid` - Показать свой ID\n"
        "❓ `/help_admin` - Эта справка\n\n"
        "📌 **Как ответить кандидату:**\n"
        "1. Найдите сообщение с заявкой в группе\n"
        "2. Нажмите 'Ответить' (Reply) на это сообщение\n"
        "3. Напишите своё сообщение и отправьте\n"
        "4. Бот перешлёт его кандидату в ЛС"
    )
    
    bot.reply_to(message, help_text)


# *** ГЛАВНЫЙ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ***
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'voice', 'sticker', 'audio', 'location', 'contact'])
def main_router(message):
    chat_id = message.chat.id
    
    # Игнорируем команды, которые уже обработаны другими хендлерами
    if message.content_type == 'text' and message.text.startswith('/'):
        # Проверяем, не является ли это командой для админов
        known_commands = ['/applications', '/status', '/clear_applications', '/myid', '/help_admin']
        if any(message.text.startswith(cmd) for cmd in known_commands):
            return  # Команда уже обработана другим хендлером
    
    # Логируем входящее сообщение
    logger.info(f"📨 Сообщение от {message.from_user.id} в чат {chat_id}")
    logger.info(f"📝 Текст: {message.text if message.text else 'Медиа'}")
    if message.reply_to_message:
        logger.info(f"🔍 Reply_to: {message.reply_to_message.message_id}")
    
    # *** ПЕРВАЯ ПРОВЕРКА: Сообщения в группе администрации ***
    if message.chat.id == GROUP_CHAT_ID:
        logger.info("📌 Сообщение в группе администрации")
        
        # 1. Если это команда /start в группе - игнорируем
        if message.content_type == 'text' and message.text == '/start':
            bot.reply_to(message, "❌ Эта команда не работает в группе. Напишите мне в личные сообщения!")
            return
        
        # 2. Если сообщение от админа
        if message.from_user.id in ADMIN_IDS:
            logger.info(f"👤 Сообщение от админа {message.from_user.id}")
            
            # Проверяем, является ли это ответом на заявку
            if message.reply_to_message:
                replied_msg_id = message.reply_to_message.message_id
                logger.info(f"🔄 Ответ на сообщение ID: {replied_msg_id}")
                logger.info(f"📋 Admin_reports_map: {admin_reports_map}")
                
                if replied_msg_id in admin_reports_map:
                    target_data = admin_reports_map[replied_msg_id]
                    target_user_id = target_data['user_chat_id']
                    user_name = target_data.get('user_name', 'Пользователь')
                    
                    logger.info(f"✅ Найден пользователь для ответа: {target_user_id} ({user_name})")
                    
                    # Отправляем сообщение пользователю
                    try:
                        if message.content_type == 'text':
                            bot.send_message(
                                target_user_id, 
                                f"✉️ Ответ от администрации:\n\n{message.text}"
                            )
                            logger.info(f"✅ Текстовое сообщение отправлено пользователю {target_user_id}")
                        elif message.content_type == 'photo':
                            file_id = message.photo[-1].file_id
                            caption = message.caption if message.caption else "✉️ Ответ от администрации с фото:"
                            bot.send_photo(target_user_id, file_id, caption=caption)
                            logger.info(f"✅ Фото отправлено пользователю {target_user_id}")
                        elif message.content_type == 'video':
                            file_id = message.video.file_id
                            caption = message.caption if message.caption else "✉️ Ответ от администрации с видео:"
                            bot.send_video(target_user_id, file_id, caption=caption)
                            logger.info(f"✅ Видео отправлено пользователю {target_user_id}")
                        elif message.content_type == 'document':
                            file_id = message.document.file_id
                            caption = message.caption if message.caption else "✉️ Ответ от администрации с документом:"
                            bot.send_document(target_user_id, file_id, caption=caption)
                            logger.info(f"✅ Документ отправлен пользователю {target_user_id}")
                        elif message.content_type == 'voice':
                            file_id = message.voice.file_id
                            bot.send_voice(target_user_id, file_id)
                            logger.info(f"✅ Голосовое отправлено пользователю {target_user_id}")
                        elif message.content_type == 'sticker':
                            file_id = message.sticker.file_id
                            bot.send_sticker(target_user_id, file_id)
                            logger.info(f"✅ Стикер отправлен пользователю {target_user_id}")
                        elif message.content_type == 'audio':
                            file_id = message.audio.file_id
                            caption = message.caption if message.caption else "✉️ Ответ от администрации с аудио:"
                            bot.send_audio(target_user_id, file_id, caption=caption)
                            logger.info(f"✅ Аудио отправлено пользователю {target_user_id}")
                        else:
                            bot.send_message(target_user_id, f"✉️ Ответ от администрации (медиафайл):")
                            bot.forward_message(target_user_id, GROUP_CHAT_ID, message.message_id)
                            logger.info(f"✅ Медиа переслано пользователю {target_user_id}")
                        
                        # Подтверждаем администратору, что сообщение отправлено
                        bot.reply_to(
                            message, 
                            f"✅ Сообщение отправлено пользователю {user_name}!"
                        )
                        logger.info(f"✅ Подтверждение отправлено админу")
                        
                    except Exception as e:
                        error_msg = f"❌ Ошибка отправки пользователю: {str(e)}"
                        logger.error(error_msg)
                        bot.reply_to(message, error_msg)
                else:
                    logger.warning(f"⚠️ ID сообщения {replied_msg_id} не найден в admin_reports_map")
                    bot.reply_to(message, "⚠️ Эта заявка уже неактивна или была удалена.")
            else:
                logger.info("ℹ️ Сообщение от админа без reply, игнорируем")
            
            # ВСЕ сообщения от админов в группе игнорируем (не пересылаем и не отвечаем)
            return
        
        # 3. Если сообщение в группе от НЕ админа - игнорируем
        logger.info("🚫 Сообщение от не-админа в группе, игнорируем")
        return

    # *** ВТОРАЯ ПРОВЕРКА: Личные сообщения боту ***
    # Если пользователь в режиме пересылки сообщений
    if chat_id in forwarding_users:
        logger.info(f"📤 Пересылка сообщения от {chat_id}")
        
        # Проверяем, не является ли пользователь администратором
        if chat_id in ADMIN_IDS:
            # Если админ случайно в списке пересылки - удаляем его
            del forwarding_users[chat_id]
            bot.send_message(chat_id, "Вы администратор, режим пересылки отключен.")
            return
            
        try:
            # Пересылаем сообщение в группу
            forwarded = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)
            
            # Добавляем пометку, кто отправил
            bot.send_message(
                GROUP_CHAT_ID,
                f"💬 Сообщение от кандидата (ID: {chat_id})",
                reply_to_message_id=forwarded.message_id
            )
            logger.info(f"✅ Сообщение переслано в группу")
        except Exception as e:
            error_msg = f"❌ Ошибка отправки: {e}"
            logger.error(error_msg)
            bot.send_message(chat_id, error_msg)
        return

    # Если пользователь в процессе заполнения анкеты
    if chat_id in user_data:
        logger.info(f"📝 Пользователь {chat_id} в процессе анкеты")
        # Обработка анкеты уже идет через register_next_step_handler
        return

    # *** ТРЕТЬЯ ПРОВЕРКА: Обычные сообщения ***
    # Если это команда /start
    if message.content_type == 'text' and message.text == '/start':
        handle_start(message)
        return

    # Если это сообщение в личку
    if isinstance(message.chat, types.Chat) and message.chat.type == 'private':
        bot.send_message(chat_id, "Чтобы подать заявку, напишите команду /start.")


if __name__ == '__main__':
    print("=" * 50)
    print("🤖 Бот запущен...")
    print(f"📋 Группа админов: {GROUP_CHAT_ID}")
    print(f"👥 Администраторы: {ADMIN_IDS}")
    print("📝 Логирование включено. Смотрите консоль для отладки.")
    print("=" * 50)
    print("\n📌 Команды для администраторов (работают в ЛС и в группе):")
    print("  /applications - Показать активные заявки")
    print("  /status - Статус бота")
    print("  /clear_applications - Очистить заявки")
    print("  /myid - Показать свой ID")
    print("  /help_admin - Справка")
    print("=" * 50)
    bot.infinity_polling()
