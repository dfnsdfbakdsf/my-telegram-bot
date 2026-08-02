import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import sys
import datetime
import asyncio
import re

# 🛡️ Токен и настройки
TOKEN = os.getenv('DISCORD_TOKEN')
# ID канала, куда приходят анкеты (обновлён)
CHANNEL_ID = 1533430617524539545 

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Храним временную связь: ID анкеты -> ID пользователя
# Ключ (key) - это ID сообщения с анкетой в канале. Значение - ID игрока, который её отправил.
pending_applications = {}

# ==========================================
# 1. КНОПКА ДЛЯ СТАРТА
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("📨 Я отправил вам анкету в Личные Сообщения! Проверьте вкладку с ботом.", ephemeral=True)
        await ask_questions(interaction.user)

# ==========================================
# 2. АНКЕТА В ЛС (С вопросами и проверками)
# ==========================================
async def ask_questions(user: discord.User):
    try:
        # ✅ Добавлен вопрос про возраст
        questions = [
            {"key": "name", "q": "**Как вас зовут?** (Ваше реальное имя)", "type": "text"},
            {"key": "age", "q": "**Сколько вам лет?** (Введите число)", "type": "number"},
            {"key": "nickname", "q": "**Ваш никнейм на сервере Minecraft?**", "type": "text"},
            {"key": "donate", "q": "**Какой у вас донат?** (VIP, Premium или без доната)", "type": "text"},
            {"key": "playtime", "q": "**Сколько часов в день вы играете?** (Введите только число)", "type": "number"},
            {"key": "pvp", "q": "**Оцените свой навык PvP (от 1 до 10)?** (Введите число)", "type": "range"},
            {"key": "pve", "q": "**Оцените свой навык PvE (от 1 до 10)?** (Введите число)", "type": "range"},
            {"key": "server_population", "q": "**Сколько всего вы играете на сервере?** (Напишите количество)", "type": "text"}
        ]
        
        answers = {}
        await user.send("👋 **Привет! Я бот для сбора анкет в клан.**\nОтвечай на мои вопросы по очереди, и в конце я отправлю твою анкету.")

        for question in questions:
            while True:
                await user.send(question["q"])
                
                def check(msg):
                    return msg.author == user and isinstance(msg.channel, discord.DMChannel)
                
                try:
                    reply = await bot.wait_for('message', timeout=300.0, check=check)
                    answer_text = reply.content.strip()

                    if question["type"] == "number":
                        if not answer_text.isdigit() or int(answer_text) < 1:
                            await user.send("❌ Ошибка! Пожалуйста, введите **положительное число**. Попробуйте снова.")
                            continue
                    
                    if question["type"] == "range":
                        if not answer_text.isdigit():
                            await user.send("❌ Ошибка! Введите **только цифру** от 1 до 10.")
                            continue
                        num = int(answer_text)
                        if num < 1 or num > 10:
                            await user.send("❌ Ошибка! Введите число **от 1 до 10**.")
                            continue

                    answers[question["key"]] = answer_text
                    break 

                except asyncio.TimeoutError:
                    await user.send("⏳ Время вышло! Чтобы начать заново, напишите в чат `!anketa`.")
                    return

        # ==========================================
        # 3. ФОРМИРОВАНИЕ И ОТПРАВКА АНКЕТЫ В КАНАЛ
        # ==========================================
        embed = discord.Embed(
            title="📥 Новая анкета на вступление!",
            description=f"От: {user.mention} (ID: {user.id})",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="👤 Реальное имя", value=answers["name"], inline=False)
        embed.add_field(name="🎂 Возраст", value=f"{answers['age']} лет", inline=False)
        embed.add_field(name="🪪 Никнейм MC", value=answers["nickname"], inline=False)
        embed.add_field(name="💰 Донат", value=answers["donate"], inline=False)
        embed.add_field(name="⏳ В день играет", value=f"{answers['playtime']} ч.", inline=False)
        embed.add_field(name="⚔️ PvP (1-10)", value=answers["pvp"], inline=True)
        embed.add_field(name="👹 PvE (1-10)", value=answers["pve"], inline=True)
        embed.add_field(name="👥 Сколько играют на сервере", value=answers["server_population"], inline=False)

        try:
            target_channel = bot.get_channel(CHANNEL_ID)
            if target_channel:
                # Отправляем анкету и сохраняем ID сообщения в словарь
                sent_message = await target_channel.send(embed=embed)
                
                # Сохраняем связь: ID сообщения анкеты -> ID игрока
                pending_applications[sent_message.id] = user.id
                
                await user.send("✅ **Готово! Твоя анкета успешно отправлена в канал для рассмотрения!** Ожидай ответа от руководства.")
            else:
                await user.send("❌ Ошибка: Я не могу найти указанный канал. Сообщите администратору.")
        except Exception as e:
            await user.send("❌ Произошла ошибка при отправке анкеты.")
            print(f"Ошибка отправки в канал: {e}")

    except Exception as e:
        print(f"Ошибка в анкете для {user.name}: {e}")

# ==========================================
# 4. ПЕРЕХВАТ ОТВЕТОВ ОТ АДМИНА В КАНАЛЕ (Самая важная часть!)
# ==========================================
@bot.event
async def on_message(message):
    # Игнорируем сообщения от самого бота
    if message.author == bot.user:
        return

    # Обрабатываем команды
    await bot.process_commands(message)

    # Если сообщение НЕ в том канале, куда приходят заявки, игнорируем
    if message.channel.id != CHANNEL_ID:
        return

    # Если админ упоминает бота (пишет @newbot2) в этом канале
    if bot.user in message.mentions:
        # Перехватываем текст сообщения-ответа админа
        admin_reply_text = message.content

        # Чистим текст от упоминания бота (например, @newbot2 Принят -> Принят)
        clean_text = re.sub(rf'<@!?{bot.user.id}>', '', admin_reply_text).strip()

        if not clean_text:
            return # Если написали просто @newbot2 без текста, ничего не делаем

        # Проверяем, есть ли в этом канале сообщение-анкета перед этим ответом
        # Мы ищем последнюю анкету перед ответом
        target_user_id = None
        
        async for msg in message.channel.history(limit=20):
            # Если нашли сообщение, отправленное ботом, у которого есть embed анкеты
            if msg.author == bot.user and msg.embeds:
                # Проверяем, есть ли этот ID в нашей базе ожидающих ответа
                if msg.id in pending_applications:
                    target_user_id = pending_applications[msg.id]
                    break # Нашли нужную анкету

        if target_user_id:
            try:
                # Получаем игрока по его ID
                player_user = await bot.fetch_user(target_user_id)
                
                # Отправляем ответ от админа игроку в ЛС
                final_message = f"📩 **Ответ от руководства клана по вашей заявке:**\n\n{clean_text}"
                await player_user.send(final_message)
                
                # Сообщаем админу в канале, что ответ доставлен
                await message.reply(f"✅ Ответ успешно отправлен игроку {player_user.mention} в личные сообщения.", mention_author=False)
                
                # Удаляем анкету из "ожидающих", чтобы не перепутать с другими
                del pending_applications[msg.id]
                
            except Exception as e:
                await message.reply(f"❌ Не удалось отправить сообщение игроку. Возможно, у него закрыты ЛС. Ошибка: {e}")
        else:
            await message.reply("⚠️ Я не нашёл анкету перед этим сообщением. Убедитесь, что вы ответили под анкетой (в том же канале).", mention_author=False)

# ==========================================
# 5. КОМАНДЫ БОТА
# ==========================================
@bot.event
async def on_ready():
    print('='*40)
    print(f'✅ Бот запущен! Имя: {bot.user.name}')
    print(f'📬 Анкеты будут отправляться в канал с ID: {CHANNEL_ID}')
    print(f'💬 Я буду следить за ответами в этом канале и пересылать их игрокам.')
    print('='*40)

@bot.command()
async def anketa(ctx):
    await ctx.send("👋 Нажмите на кнопку ниже, чтобы начать анкету:", view=StartButtonView())

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📋 Команды", color=discord.Color.gold())
    embed.add_field(name="!anketa", value="📝 Открыть анкету для вступления", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ ОШИБКА ЗАПУСКА: {e}')
