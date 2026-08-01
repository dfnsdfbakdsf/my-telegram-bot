import telebot
from telebot import types
import time
import logging
import sqlite3
from datetime import datetime
import threading
import re

# Включаем логирование для отладки
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ ---
BOT_TOKEN = '8935278169:AAFfVupDDFrp2rHufzQYJrsnWJxtI54Xxvw'  # ЗАМЕНИТЕ НА ВАШ ТОКЕН!
GROUP_CHAT_ID = -1004291446609  # ID вашей группы/админа
ADMIN_IDS = [123456789, 987654321]  # *** ДОБАВЬТЕ СЮДА СВОИ TELEGRAM ID ***
# -----------------

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}
admin_reports_map = {}
forwarding_users = {}  # Словарь для режима пересылки сообщений после анкеты
pending_questions = {}  # Для хранения вопросов админов к кандидатам

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    """Создание базы данных для хранения заявок"""
    conn = sqlite3.connect('applications.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS applications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  username TEXT,
                  name TEXT,
                  age INTEGER,
                  donate TEXT,
                  discord TEXT,
                  microphone TEXT,
                  hours_per_day TEXT,
                  pve_rating INTEGER,
                  pvp_rating INTEGER,
                  experience TEXT,
                  status TEXT,
                  date TIMESTAMP,
                  admin_notes TEXT)''')
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

def save_application(user_id, data, status='pending'):
    """Сохранить заявку в базу данных"""
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        c.execute('''INSERT INTO applications 
                     (user_id, username, name, age, donate, discord, microphone, 
                      hours_per_day, pve_rating, pvp_rating, experience, status, date)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, data['telegram_username'], data['name'], data['age'],
                   data['donate'], data['discord'], data['microphone'],
                   data['hours_per_day'], data['pve_rating'], data['pvp_rating'],
                   data['experience'], status, datetime.now()))
        conn.commit()
        conn.close()
        logger.info(f"✅ Заявка сохранена в БД для пользователя {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения в БД: {e}")
        return False

def update_application_status(user_id, status, notes=None):
    """Обновить статус заявки"""
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        if notes:
            c.execute('''UPDATE applications SET status=?, admin_notes=? 
                         WHERE user_id=? AND status="pending"''', 
                      (status, notes, user_id))
        else:
            c.execute('''UPDATE applications SET status=? 
                         WHERE user_id=? AND status="pending"''', 
                      (status, user_id))
        conn.commit()
        conn.close()
        logger.info(f"✅ Статус заявки обновлен для {user_id}: {status}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статуса: {e}")
        return False

def check_duplicate_application(user_id):
    """Проверить, есть ли у пользователя активная заявка"""
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        pending = c.execute('''SELECT COUNT(*) FROM applications 
                              WHERE user_id=? AND status="pending"''', (user_id,)).fetchone()[0]
        conn.close()
        return pending > 0
    except Exception as e:
        logger.error(f"❌ Ошибка проверки дубликатов: {e}")
        return False

def get_application_history(user_id, limit=5):
    """Получить историю заявок пользователя"""
    try:
        conn = sqlite3.connect('applications.db')
        c = conn.cursor()
        history = c.execute('''SELECT name, status, date FROM applications 
                              WHERE user_id=? ORDER BY date DESC LIMIT ?''', 
                           (user_id, limit)).fetchall()
        conn.close()
        return history
    except Exception as e:
        logger.error(f"❌ Ошибка получения истории: {e}")
        return []

# --- СОЗДАНИЕ КНОПОК ДЛЯ АДМИНОВ ---
def create_admin_buttons(user_id, user_name):
    """Создать инлайн-кнопки для администратора"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    btn_accept = types.InlineKeyboardButton(
        "✅ Принять", 
        callback_data=f"accept_{user_id}"
    )
    btn_reject = types.InlineKeyboardButton(
        "❌ Отклонить", 
        callback_data=f"reject_{user_id}"
    )
    btn_question = types.InlineKeyboardButton(
        "❓ Задать вопрос", 
        callback_data=f"question_{user_id}"
    )
    btn_history = types.InlineKeyboardButton(
        "📜 История", 
        callback_data=f"history_{user_id}"
    )
    btn_contact = types.InlineKeyboardButton(
        "📩 Написать", 
        callback_data=f"contact_{user_id}"
    )
    
    markup.add(btn_accept, btn_reject)
    markup.add(btn_question, btn_history)
    markup.add(btn_contact)
    return markup


# --- ОБРАБОТКА КНОПОК АДМИНОВ ---
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обработка нажатий на инлайн-кнопки"""
    try:
        # Проверяем, что пользователь - администратор
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ У вас нет прав для этого действия!", show_alert=True)
            return
        
        # Парсим callback_data
        action, user_id_str = call.data.split('_')
        target_user_id = int(user_id_str)
        
        logger.info(f"🔄 Кнопка '{action}' от {call.from_user.id} для {target_user_id}")
        
        if action == 'accept':
            # Принять заявку
            if update_application_status(target_user_id, 'accepted'):
                bot.send_message(target_user_id, 
                    "🎉 **Поздравляем! Ваша заявка принята!**\n\n"
                    "Добро пожаловать в клан! Скоро с вами свяжется администрация для дальнейших инструкций.")
                
                # Обновляем сообщение в группе
                try:
                    # Получаем имя из сообщения
                    msg_text = call.message.text
                    name_line = [line for line in msg_text.split('\n') if '👤 Имя:' in line]
                    user_name = name_line[0].replace('👤 Имя:', '').strip() if name_line else 'Пользователь'
                    
                    bot.edit_message_text(
                        f"✅ **ЗАЯВКА ПРИНЯТА**\n"
                        f"Пользователь {user_name} принят в клан!",
                        call.message.chat.id,
                        call.message.message_id
                    )
                except Exception as e:
                    logger.error(f"Ошибка при обновлении сообщения: {e}")
                
                # Удаляем из активных заявок
                for msg_id, data in list(admin_reports_map.items()):
                    if data['user_chat_id'] == target_user_id:
                        del admin_reports_map[msg_id]
                        break
                
                bot.answer_callback_query(call.id, "✅ Заявка принята!")
                logger.info(f"✅ Заявка {target_user_id} принята")
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка при сохранении!", show_alert=True)
                
        elif action == 'reject':
            # Отклонить заявку
            if update_application_status(target_user_id, 'rejected'):
                bot.send_message(target_user_id, 
                    "😔 **К сожалению, ваша заявка отклонена.**\n\n"
                    "Мы благодарим вас за интерес к нашему клану. Вы можете подать заявку снова через 30 дней.")
                
                # Обновляем сообщение в группе
                try:
                    msg_text = call.message.text
                    name_line = [line for line in msg_text.split('\n') if '👤 Имя:' in line]
                    user_name = name_line[0].replace('👤 Имя:', '').strip() if name_line else 'Пользователь'
                    
                    bot.edit_message_text(
                        f"❌ **ЗАЯВКА ОТКЛОНЕНА**\n"
                        f"Пользователь {user_name} не прошел отбор.",
                        call.message.chat.id,
                        call.message.message_id
                    )
                except Exception as e:
                    logger.error(f"Ошибка при обновлении сообщения: {e}")
                
                # Удаляем из активных заявок
                for msg_id, data in list(admin_reports_map.items()):
                    if data['user_chat_id'] == target_user_id:
                        del admin_reports_map[msg_id]
                        break
                
                bot.answer_callback_query(call.id, "❌ Заявка отклонена!")
                logger.info(f"❌ Заявка {target_user_id} отклонена")
            else:
                bot.answer_callback_query(call.id, "❌ Ошибка при сохранении!", show_alert=True)
                
        elif action == 'question':
            # Задать вопрос
            pending_questions[call.from_user.id] = {
                'target_user_id': target_user_id,
                'message_id': call.message.message_id
            }
            bot.send_message(call.from_user.id, 
                f"✍️ **Напишите ваш вопрос для пользователя.**\n\n"
                f"Вопрос будет отправлен анонимно от администрации.\n\n"
                f"Чтобы отменить, отправьте /cancel")
            bot.answer_callback_query(call.id, "✍️ Напишите ваш вопрос в чат с ботом")
            
        elif action == 'history':
            # Показать историю заявок пользователя
            history = get_application_history(target_user_id)
            if history:
                text = f"📜 **История заявок пользователя:**\n\n"
                for name, status, date in history:
                    status_emoji = "✅" if status == "accepted" else "❌" if status == "rejected" else "⏳"
                    date_str = datetime.strptime(date, '%Y-%m-%d %H:%M:%S.%f').strftime('%d.%m.%Y %H:%M')
                    text += f"{status_emoji} {name} - {status} ({date_str})\n"
                bot.send_message(call.from_user.id, text)
            else:
                bot.send_message(call.from_user.id, "📭 У пользователя нет предыдущих заявок.")
            bot.answer_callback_query(call.id)
            
        elif action == 'contact':
            # Создать кнопку для связи
            username = None
            user_name = "Пользователь"
            for msg_id, data in admin_reports_map.items():
                if data['user_chat_id'] == target_user_id:
                    username = data.get('user_username', '')
                    user_name = data.get('user_name', 'Пользователь')
                    break
            
            markup = types.InlineKeyboardMarkup()
            if username and username != '@не_указан':
                btn = types.InlineKeyboardButton(
                    "📩 Написать в ЛС",
                    url=f"tg://resolve?domain={username.lstrip('@')}"
                )
                markup.add(btn)
                bot.send_message(call.from_user.id, 
                    f"📩 Нажмите кнопку, чтобы написать пользователю:\n"
                    f"👤 {user_name}",
                    reply_markup=markup)
            else:
                bot.send_message(call.from_user.id, 
                    f"⚠️ У пользователя нет username.\n"
                    f"🆔 Его ID: `{target_user_id}`\n\n"
                    f"Вы можете использовать этот ID для поиска в Telegram.")
            bot.answer_callback_query(call.id)
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_callback: {e}")
        bot.answer_callback_query(call.id, f"❌ Ошибка: {str(e)}", show_alert=True)


# --- ОБРАБОТКА ВОПРОСОВ ОТ АДМИНОВ ---
@bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.chat.type == 'private' and m.text and not m.text.startswith('/'))
def handle_admin_question(message):
    """Обработка вопроса админа к кандидату"""
    if message.from_user.id in pending_questions:
        question_data = pending_questions[message.from_user.id]
        target_user_id = question_data['target_user_id']
        
        # Отправляем вопрос кандидату
        bot.send_message(target_user_id, 
            f"❓ **Вопрос от администрации:**\n\n{message.text}\n\n"
            f"📌 Пожалуйста, ответьте на этот вопрос в личные сообщения боту.")
        
        # Подтверждаем админу
        bot.send_message(message.from_user.id, 
            f"✅ Ваш вопрос отправлен пользователю!")
        
        # Удаляем из ожидания
        del pending_questions[message.from_user.id]
        logger.info(f"✅ Вопрос отправлен от {message.from_user.id} к {target_user_id}")
    else:
        # Если админ не в режиме вопроса, но пишет боту
        bot.send_message(message.from_user.id, 
            "ℹ️ Вы можете использовать команды:\n"
            "/applications - Показать заявки\n"
            "/status - Статус бота\n"
            "/help_admin - Помощь")


# --- ОТМЕНА ВОПРОСА ---
@bot.message_handler(commands=['cancel'])
def cancel_question(message):
    """Отмена отправки вопроса"""
    if message.from_user.id in pending_questions:
        del pending_questions[message.from_user.id]
        bot.send_message(message.from_user.id, "✅ Отправка вопроса отменена.")
    else:
        bot.send_message(message.from_user.id, "ℹ️ У вас нет активных вопросов.")


# --- ОСНОВНЫЕ КОМАНДЫ БОТА ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Сразу начинаем анкету с вопроса про имя."""
    chat_id = message.chat.id
    
    # Игнорируем команду /start в группе администрации
    if chat_id == GROUP_CHAT_ID:
        bot.reply_to(message, "❌ Эта команда не работает в группе. Напишите мне в личные сообщения!")
        return

    # Проверяем, не заполняет ли уже пользователь анкету
    if chat_id in user_data:
        bot.send_message(chat_id, "⏳ Вы уже проходите анкету. Ответьте на последний вопрос!")
        return
    
    if chat_id in forwarding_users:
        bot.send_message(chat_id, "⚠️ Вы уже заполнили анкету и находитесь в режиме общения с администрацией.")
        return

    # Проверяем на дубликаты заявок
    if check_duplicate_application(chat_id):
        bot.send_message(chat_id, 
            "⚠️ У вас уже есть активная заявка в обработке!\n"
            "Пожалуйста, дождитесь решения администрации.")
        return
    
    # Проверяем историю отклонений
    history = get_application_history(chat_id)
    if history:
        recent_rejected = [h for h in history if h[1] == 'rejected']
        if recent_rejected:
            try:
                last_rejected = datetime.strptime(recent_rejected[0][2], '%Y-%m-%d %H:%M:%S.%f')
                days_passed = (datetime.now() - last_rejected).days
                if days_passed < 30:
                    bot.send_message(chat_id, 
                        f"⚠️ Ваша предыдущая заявка была отклонена {days_passed} дней назад.\n"
                        f"Вы можете подать новую заявку через {30 - days_passed} дней.")
                    return
            except:
                pass

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

    bot.send_message(chat_id, '👋 Привет! Давай заполним анкету.\n\nКак тебя зовут?')
    bot.register_next_step_handler(message, get_name)


# --- ФУНКЦИИ АНКЕТЫ ---
def get_name(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    name = message.text.strip()
    if len(name) < 2:
        bot.send_message(chat_id, '❌ Пожалуйста, введите ваше имя (минимум 2 символа).')
        bot.register_next_step_handler(message, get_name)
        return
    user_data[chat_id]['name'] = name
    bot.send_message(chat_id, '❄️ Сколько тебе лет?')
    bot.register_next_step_handler(message, check_age)

def check_age(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    try:
        age = int(message.text)
        if age < 12:
            bot.send_message(chat_id, "❌ Извините, но минимальный возраст для вступления - 12 лет.")
            bot.register_next_step_handler(message, check_age)
            return
        if age > 60:
            bot.send_message(chat_id, "❌ Пожалуйста, введите реальный возраст.")
            bot.register_next_step_handler(message, check_age)
            return
        user_data[chat_id]['age'] = age
        bot.send_message(chat_id, '💰 Какой у вас донат в игре?')
        bot.register_next_step_handler(message, get_donate)
    except ValueError:
        bot.send_message(chat_id, '❌ Пожалуйста, введите число (ваш возраст).')
        bot.register_next_step_handler(message, check_age)

def get_donate(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    user_data[chat_id]['donate'] = message.text.strip().capitalize()
    bot.send_message(chat_id, '🖥️ Ваш Discord? (Пример: username#1234)')
    bot.register_next_step_handler(message, get_discord)

def get_discord(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    discord = message.text.strip()
    if '#' not in discord or len(discord) < 5:
        bot.send_message(chat_id, '⚠️ Пожалуйста, введите корректный Discord тег (содержит #)')
        bot.register_next_step_handler(message, get_discord)
        return
    user_data[chat_id]['discord'] = discord
    bot.send_message(chat_id, '🎤 Есть ли у тебя микрофон? (Да/Нет)')
    bot.register_next_step_handler(message, get_microphone)

def get_microphone(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    mic = message.text.strip().capitalize()
    if mic not in ['Да', 'Нет', 'Есть', 'Нету', 'Есть микрофон']:
        bot.send_message(chat_id, '⚠️ Пожалуйста, ответьте "Да" или "Нет"')
        bot.register_next_step_handler(message, get_microphone)
        return
    user_data[chat_id]['microphone'] = 'Да' if mic in ['Да', 'Есть', 'Есть микрофон'] else 'Нет'
    bot.send_message(chat_id, '🎮 Оцените своё ПвЕ по шкале от 1 до 10.')
    bot.register_next_step_handler(message, get_pve_rating)

def get_pve_rating(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    try:
        rating = int(message.text)
        if rating < 1 or rating > 10:
            raise ValueError
        user_data[chat_id]['pve_rating'] = rating
        bot.send_message(chat_id, '⚔️ Оцените своё ПвП по шкале от 1 до 10.')
        bot.register_next_step_handler(message, get_pvp_rating)
    except ValueError:
        bot.send_message(chat_id, '❌ Пожалуйста, введите число от 1 до 10!')
        bot.register_next_step_handler(message, get_pve_rating)

def get_pvp_rating(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    try:
        rating = int(message.text)
        if rating < 1 or rating > 10:
            raise ValueError
        user_data[chat_id]['pvp_rating'] = rating
        bot.send_message(chat_id, '⏱️ Сколько часов в день ты можешь играть?\n(Например: 3 или "3-4 часа")')
        bot.register_next_step_handler(message, get_hours)
    except ValueError:
        bot.send_message(chat_id, '❌ Пожалуйста, введите число от 1 до 10!')
        bot.register_next_step_handler(message, get_pvp_rating)

def get_hours(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    user_data[chat_id]['hours_per_day'] = message.text.strip()
    bot.send_message(chat_id, '📅 Сколько времени ты уже играешь в проект?\n(Например: 2 года, 5 месяцев)')
    bot.register_next_step_handler(message, get_experience)

def get_experience(message):
    """Финал анкеты и переход в режим свободного чата"""
    chat_id = message.chat.id
    if chat_id not in user_data:
        return
    
    experience_text = message.text.strip()
    if not experience_text:
        bot.send_message(chat_id, '❌ Пожалуйста, напиши свой стаж.')
        bot.register_next_step_handler(message, get_experience)
        return

    user_data[chat_id]['experience'] = experience_text

    final_text_user = (
        f'✅ **Спасибо за ответы, {user_data[chat_id]["name"]}!**\n\n'
        f'📋 **Ваша анкета:**\n'
        f'❄️ Возраст: {user_data[chat_id]["age"]}\n'
        f'💰 Донат: {user_data[chat_id]["donate"]}\n'
        f'🖥️ Дискорд: {user_data[chat_id]["discord"]}\n'
        f'🎤 Микрофон: {user_data[chat_id]["microphone"]}\n'
        f'⏱️ Часов в день: {user_data[chat_id]["hours_per_day"]}\n'
        f'🎮 ПвЕ: {user_data[chat_id]["pve_rating"]}/10\n'
        f'⚔️ ПвП: {user_data[chat_id]["pvp_rating"]}/10\n'
        f'📅 Стаж игры: {experience_text}\n\n'
        '📌 **Твоя заявка принята к рассмотрению!**\n'
        'Администрация свяжется с тобой в ближайшее время.\n'
        'Ты можешь продолжать общение в этом чате.'
    )

    admin_report = (
        "📋 **НОВАЯ ЗАЯВКА**\n"
        f"👤 Имя: {user_data[chat_id]['name']} ({user_data[chat_id]['telegram_username']})\n"
        f"❄️ Возраст: {user_data[chat_id]['age']}\n"
        f"💰 Донат: {user_data[chat_id]['donate']}\n"
        f"🖥️ Дискорд: {user_data[chat_id]['discord']}\n"
        f"🎤 Микрофон: {user_data[chat_id]['microphone']}\n"
        f"⏱️ Часов в день: {user_data[chat_id]['hours_per_day']}\n"
        f"🎮 ПвЕ: {user_data[chat_id]['pve_rating']}/10\n"
        f"⚔️ ПвП: {user_data[chat_id]['pvp_rating']}/10\n"
        f"📅 Стаж: {experience_text}\n\n"
        f"📌 Используйте кнопки для управления заявкой"
    )

    # Сохраняем в базу данных
    if not save_application(chat_id, user_data[chat_id]):
        bot.send_message(chat_id, "⚠️ Ошибка при сохранении анкеты. Попробуйте позже.")
        del user_data[chat_id]
        return

    bot.send_message(chat_id, final_text_user)
    
    # Создаем инлайн-кнопки для админов
    admin_markup = create_admin_buttons(chat_id, user_data[chat_id]['name'])
    sent_admin_msg = bot.send_message(GROUP_CHAT_ID, admin_report, reply_markup=admin_markup)
    
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


# --- КОМАНДЫ ДЛЯ АДМИНИСТРАТОРОВ ---
@bot.message_handler(commands=['applications'])
def list_applications(message):
    """Показать активные заявки"""
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
        text += f"🆔 ID пользователя: `{data['user_chat_id']}`\n"
        text += f"📨 ID сообщения: `{msg_id}`\n"
        text += f"⏱️ {time_ago} мин. назад\n\n"
    
    bot.reply_to(message, text)


@bot.message_handler(commands=['status'])
def status_command(message):
    """Проверить статус бота"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет прав для этой команды!")
        return
    
    status_text = (
        "📊 **Статус бота**\n\n"
        f"👥 Активных заявок: {len(admin_reports_map)}\n"
        f"📨 Пользователей в режиме пересылки: {len(forwarding_users)}\n"
        f"📝 Пользователей в процессе анкеты: {len(user_data)}\n"
        f"❓ Вопросов в обработке: {len(pending_questions)}\n\n"
        f"📋 ID группы: `{GROUP_CHAT_ID}`\n"
        f"👤 Ваш ID: `{message.from_user.id}`\n"
        f"✅ Вы в списке админов: {message.from_user.id in ADMIN_IDS}"
    )
    
    bot.reply_to(message, status_text)


@bot.message_handler(commands=['clear_applications'])
def clear_applications(message):
    """Очистить все заявки"""
    if message.from_user.id not in ADMIN_IDS:
        bot.reply_to(message, "❌ У вас нет прав для этой команды!")
        return
    
    admin_reports_map.clear()
    bot.reply_to(message, "🗑️ Все заявки очищены!")


@bot.message_handler(commands=['myid'])
def myid_command(message):
    """Показать свой ID"""
    bot.reply_to(message, f"🆔 Ваш ID: `{message.from_user.id}`")


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
        "❓ `/help_admin` - Эта справка\n"
        "❌ `/cancel` - Отменить отправку вопроса\n\n"
        "📌 **Как управлять заявками:**\n"
        "1. Нажмите на кнопку под заявкой\n"
        "2. Выберите действие:\n"
        "   • ✅ Принять - одобрить кандидата\n"
        "   • ❌ Отклонить - отклонить кандидата\n"
        "   • ❓ Задать вопрос - написать вопрос кандидату\n"
        "   • 📜 История - посмотреть историю заявок кандидата\n"
        "   • 📩 Написать - связаться с кандидатом"
    )
    
    bot.reply_to(message, help_text)


# --- ГЛАВНЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ---
@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'voice', 'sticker', 'audio', 'location', 'contact'])
def main_router(message):
    chat_id = message.chat.id
    
    # Игнорируем команды, которые уже обработаны другими хендлерами
    if message.content_type == 'text' and message.text and message.text.startswith('/'):
        known_commands = ['/applications', '/status', '/clear_applications', '/myid', '/help_admin', '/cancel', '/start']
        if any(message.text.startswith(cmd) for cmd in known_commands):
            return
    
    # Логируем входящее сообщение
    logger.info(f"📨 Сообщение от {message.from_user.id} в чат {chat_id}")
    if message.text:
        logger.info(f"📝 Текст: {message.text[:100]}...")
    if message.reply_to_message:
        logger.info(f"🔍 Reply_to: {message.reply_to_message.message_id}")
    
    # *** ПЕРВАЯ ПРОВЕРКА: Сообщения в группе администрации ***
    if message.chat.id == GROUP_CHAT_ID:
        logger.info("📌 Сообщение в группе администрации")
        
        if message.content_type == 'text' and message.text == '/start':
            bot.reply_to(message, "❌ Эта команда не работает в группе. Напишите мне в личные сообщения!")
            return
        
        # Если сообщение от админа
        if message.from_user.id in ADMIN_IDS:
            logger.info(f"👤 Сообщение от админа {message.from_user.id}")
            
            # Проверяем, является ли это ответом на заявку
            if message.reply_to_message:
                replied_msg_id = message.reply_to_message.message_id
                logger.info(f"🔄 Ответ на сообщение ID: {replied_msg_id}")
                
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
                                f"✉️ **Ответ от администрации:**\n\n{message.text}"
                            )
                        else:
                            bot.send_message(target_user_id, f"✉️ **Ответ от администрации:**")
                            bot.forward_message(target_user_id, GROUP_CHAT_ID, message.message_id)
                        
                        bot.reply_to(message, f"✅ Сообщение отправлено пользователю {user_name}!")
                        logger.info(f"✅ Сообщение отправлено {target_user_id}")
                        
                    except Exception as e:
                        error_msg = f"❌ Ошибка отправки: {str(e)}"
                        logger.error(error_msg)
                        bot.reply_to(message, error_msg)
                else:
                    logger.warning(f"⚠️ ID сообщения {replied_msg_id} не найден в admin_reports_map")
                    bot.reply_to(message, "⚠️ Эта заявка уже неактивна.")
            
            return  # ВСЕ сообщения от админов в группе игнорируем
        
        # Если сообщение в группе от НЕ админа - игнорируем
        logger.info("🚫 Сообщение от не-админа в группе, игнорируем")
        return

    # *** ВТОРАЯ ПРОВЕРКА: Личные сообщения боту ***
    # Если пользователь в режиме пересылки сообщений
    if chat_id in forwarding_users:
        logger.info(f"📤 Пересылка сообщения от {chat_id}")
        
        if chat_id in ADMIN_IDS:
            del forwarding_users[chat_id]
            bot.send_message(chat_id, "Вы администратор, режим пересылки отключен.")
            return
            
        try:
            forwarded = bot.forward_message(GROUP_CHAT_ID, chat_id, message.message_id)
            bot.send_message(
                GROUP_CHAT_ID,
                f"💬 Сообщение от кандидата (ID: `{chat_id}`)",
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
        return

    # *** ТРЕТЬЯ ПРОВЕРКА: Обычные сообщения ***
    if message.content_type == 'text' and message.text == '/start':
        handle_start(message)
        return

    # Если это сообщение в личку
    if isinstance(message.chat, types.Chat) and message.chat.type == 'private':
        bot.send_message(chat_id, "Чтобы подать заявку, напишите команду /start.")


if __name__ == '__main__':
    print("=" * 60)
    print("🤖 БОТ ЗАПУЩЕН С РАСШИРЕННЫМИ ФУНКЦИЯМИ")
    print("=" * 60)
    print(f"📋 Группа админов: {GROUP_CHAT_ID}")
    print(f"👥 Администраторы: {ADMIN_IDS}")
    print("=" * 60)
    print("\n📌 КОМАНДЫ ДЛЯ АДМИНИСТРАТОРОВ:")
    print("  /applications - Показать активные заявки")
    print("  /status - Статус бота")
    print("  /clear_applications - Очистить заявки")
    print("  /myid - Показать свой ID")
    print("  /help_admin - Справка")
    print("  /cancel - Отменить отправку вопроса")
    print("=" * 60)
    print("\n📌 ФУНКЦИОНАЛ:")
    print("  ✅ Инлайн-кнопки для управления заявками")
    print("  ✅ База данных SQLite для хранения заявок")
    print("  ✅ Проверка дубликатов заявок")
    print("  ✅ Ограничение по времени (30 дней после отказа)")
    print("  ✅ История заявок пользователей")
    print("  ✅ Возможность задавать вопросы кандидатам")
    print("=" * 60)
    
    # Инициализируем базу данных
    init_db()
    
    print("\n🚀 Бот готов к работе!")
    bot.infinity_polling()
