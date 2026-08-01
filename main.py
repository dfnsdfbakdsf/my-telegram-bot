import telebot
from telebot import types
import time

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw' # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609                     # ID вашей группы/админа
ADMIN_IDS = [123456789, 987654321]                 # *** ДОБАВЬТЕ СЮДА СВОИ TELEGRAM ID ***
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
admin_reports_map = {}
forwarding_users = {}  # Словарь для режима пересылки сообщений после анкеты


@bot.message_handler(commands=['start'])
def handle_start(message):
    """Сразу начинаем анкету с вопроса про имя."""
    chat_id = message.chat.id

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
    admin_reports_map[sent_admin_msg.message_id] = {
        'user_chat_id': chat_id,
        'user_name': user_data[chat_id]['name'],
        'timestamp': time.time()
    }
    
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


# *** ГЛАВНЫЙ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ ОТ ПОЛЬЗОВАТЕЛЕЙ И АДМИНОВ ***
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'voice', 'sticker', 'audio', 'location', 'contact'])
def main_router(message):
    chat_id = message.chat.id

    # 1. Если сообщение пришло ОТ АДМИНА внутри ГРУППЫ
    if message.chat.id == GROUP_CHAT_ID and message.from_user.id in ADMIN_IDS:
        
        # А) Если админ отвечает на системное сообщение-заявку (из admin_reports_map)
        if message.reply_to_message and message.reply_to_message.message_id in admin_reports_map:
            target_data = admin_reports_map[message.reply_to_message.message_id]
            target_user_id = target_data['user_chat_id']
            user_name = target_data.get('user_name', 'Пользователь')
            
            # Отправляем сообщение пользователю
            try:
                if message.content_type == 'text':
                    bot.send_message(
                        target_user_id, 
                        f"✉️ Ответ от администрации:\n\n{message.text}"
                    )
                elif message.content_type == 'photo':
                    file_id = message.photo[-1].file_id
                    caption = message.caption if message.caption else "✉️ Ответ от администрации с фото:"
                    bot.send_photo(target_user_id, file_id, caption=caption)
                elif message.content_type == 'video':
                    file_id = message.video.file_id
                    caption = message.caption if message.caption else "✉️ Ответ от администрации с видео:"
                    bot.send_video(target_user_id, file_id, caption=caption)
                elif message.content_type == 'document':
                    file_id = message.document.file_id
                    caption = message.caption if message.caption else "✉️ Ответ от администрации с документом:"
                    bot.send_document(target_user_id, file_id, caption=caption)
                elif message.content_type == 'voice':
                    file_id = message.voice.file_id
                    bot.send_voice(target_user_id, file_id)
                elif message.content_type == 'sticker':
                    file_id = message.sticker.file_id
                    bot.send_sticker(target_user_id, file_id)
                elif message.content_type == 'audio':
                    file_id = message.audio.file_id
                    caption = message.caption if message.caption else "✉️ Ответ от администрации с аудио:"
                    bot.send_audio(target_user_id, file_id, caption=caption)
                else:
                    bot.send_message(target_user_id, f"✉️ Ответ от администрации (медиафайл):")
                    bot.forward_message(target_user_id, GROUP_CHAT_ID, message.message_id)
                
                # Подтверждаем администратору, что сообщение отправлено
                bot.reply_to(
                    message, 
                    f"✅ Сообщение отправлено пользователю {user_name}!"
                )
                
            except Exception as e:
                bot.reply_to(
                    message, 
                    f"❌ Ошибка отправки пользователю: {str(e)}"
                )
                
        # Б) Если админ пишет обычное сообщение в группе (не ответ), оно НЕ уходит пользователям
        # Но можно добавить возможность отправки через команду
        if message.content_type == 'text' and message.text.startswith('/send'):
            parts = message.text.split(maxsplit=1)
            if len(parts) > 1:
                try:
                    # Поиск пользователя по имени или ID
                    for msg_id, data in admin_reports_map.items():
                        if data['user_name'].lower() in parts[1].lower():
                            bot.send_message(data['user_chat_id'], f"✉️ Сообщение от администрации:\n\n{parts[1]}")
                            bot.reply_to(message, f"✅ Сообщение отправлено!")
                            break
                except:
                    pass
        return

    # 2. Если сообщение пришло ОТ КАНДИДАТА (личным сообщением боту)
    if chat_id in forwarding_users:
        try:
            # Пересылаем его в группу как есть
            forwarded = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)
            
            # Можно добавить пометку, кто отправил
            bot.send_message(
                GROUP_CHAT_ID,
                f"💬 Сообщение от кандидата (ID: {chat_id})",
                reply_to_message_id=forwarded.message_id
            )
        except Exception as e:
            bot.send_message(chat_id, f"❌ Ошибка отправки: {e}")
        return

    # 3. Если это /start от человека, который еще не в режиме заявки
    if message.content_type == 'text' and message.text == '/start':
        handle_start(message)
        return

    # 4. Если человек написал что-то рандомное боту вне анкеты
    bot.send_message(chat_id, "Чтобы подать заявку, напишите команду /start.")


# Команда для просмотра активных заявок (только для админов)
@bot.message_handler(commands=['applications'])
def list_applications(message):
    """Показать активные заявки"""
    if message.chat.id != GROUP_CHAT_ID or message.from_user.id not in ADMIN_IDS:
        return
    
    if not admin_reports_map:
        bot.send_message(GROUP_CHAT_ID, "Нет активных заявок.")
        return
    
    text = "📋 Активные заявки:\n\n"
    for msg_id, data in admin_reports_map.items():
        user_name = data.get('user_name', 'Неизвестно')
        timestamp = data.get('timestamp', 0)
        time_ago = int((time.time() - timestamp) / 60) if timestamp else 0
        text += f"• {user_name} (ID: {data['user_chat_id']}) - {time_ago} мин. назад\n"
        text += f"  Ответьте на сообщение с заявкой (ID: {msg_id})\n\n"
    
    bot.send_message(GROUP_CHAT_ID, text)


# Команда для очистки старых заявок (только для админов)
@bot.message_handler(commands=['clear_applications'])
def clear_applications(message):
    """Очистить все заявки"""
    if message.chat.id != GROUP_CHAT_ID or message.from_user.id not in ADMIN_IDS:
        return
    
    admin_reports_map.clear()
    bot.send_message(GROUP_CHAT_ID, "🗑️ Все заявки очищены!")


if __name__ == '__main__':
    print("🤖 Бот запущен...")
    print(f"📋 Группа админов: {GROUP_CHAT_ID}")
    print(f"👥 Администраторы: {ADMIN_IDS}")
    bot.infinity_polling()
