import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import sys
import datetime
import asyncio
import re
import json

# 🛡️ Токен и настройки
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1533430617524539545  # ID канала с анкетами

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 0. ФАЙЛЫ ДЛЯ ХРАНЕНИЯ ДАННЫХ
# ==========================================
ADMINS_FILE = "admins.json"
STATS_FILE = "stats.json"

# Загружаем список админов
def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r') as f:
            return json.load(f)
    return []

# Сохраняем список админов
def save_admins(admins_list):
    with open(ADMINS_FILE, 'w') as f:
        json.dump(admins_list, f)

# Загружаем статистику
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"total_applications": 0}

# Сохраняем статистику
def save_stats(stats_data):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats_data, f)

# Инициализация
admin_ids = load_admins()
stats = load_stats()
pending_applications = {} # ID сообщения анкеты -> ID игрока

# ==========================================
# 1. КНОПКА ДЛЯ СТАРТА АНКЕТЫ
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("📨 Я отправил вам анкету в Личные Сообщения! Проверьте вкладку с ботом.", ephemeral=True)
        await ask_questions(interaction.user)

# ==========================================
# 2. ЛОГИКА АНКЕТЫ В ЛС
# ==========================================
async def ask_questions(user: discord.User):
    try:
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
                    await user.send("⏳ Время вышло! Чтобы начать заново, напишите в чат `!anketa` или `!start`.")
                    return

        # ==========================================
        # 3. ФОРМИРОВАНИЕ И ОТПРАВКА АНКЕТЫ
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
                sent_message = await target_channel.send(embed=embed)
                
                # Сохраняем ID анкеты в память для ответов
                pending_applications[sent_message.id] = user.id
                
                # 📊 УВЕЛИЧИВАЕМ СЧЕТЧИК СТАТИСТИКИ
                stats["total_applications"] += 1
                save_stats(stats)
                
                await user.send("✅ **Готово! Твоя анкета успешно отправлена!** Ожидай ответа от руководства.")
            else:
                await user.send("❌ Ошибка: Я не могу найти указанный канал. Сообщите администратору.")
        except Exception as e:
            await user.send("❌ Произошла ошибка при отправке анкеты.")
            print(f"Ошибка отправки в канал: {e}")

    except Exception as e:
        print(f"Ошибка в анкете для {user.name}: {e}")

# ==========================================
# 4. ПЕРЕХВАТ ОТВЕТОВ ОТ АДМИНА
# ==========================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id != CHANNEL_ID:
        return

    if bot.user in message.mentions:
        
        if message.author.id not in admin_ids:
            await message.reply("⛔ **Доступ запрещен!** Только добавленные администраторы могут отвечать на анкеты.", mention_author=False)
            return

        admin_reply_text = message.content
        clean_text = re.sub(rf'<@!?{bot.user.id}>', '', admin_reply_text).strip()

        if not clean_text:
            return

        target_user_id = None
        target_msg_id = None

        async for msg in message.channel.history(limit=20):
            if msg.author == bot.user and msg.embeds:
                if msg.id in pending_applications:
                    target_user_id = pending_applications[msg.id]
                    target_msg_id = msg.id
                    break

        if target_user_id:
            try:
                player_user = await bot.fetch_user(target_user_id)
                final_message = f"📩 **Ответ от руководства клана по вашей заявке:**\n\n{clean_text}"
                await player_user.send(final_message)
                
                await message.reply(f"✅ Ответ успешно отправлен игроку {player_user.mention} в личные сообщения.", mention_author=False)
                del pending_applications[target_msg_id]
            except Exception as e:
                await message.reply(f"❌ Не удалось отправить сообщение игроку. Ошибка: {e}")
        else:
            await message.reply("⚠️ Я не нашёл анкету перед этим сообщением. Убедитесь, что вы ответили под анкетой.", mention_author=False)

# ==========================================
# 5. КОМАНДЫ БОТА (Здесь изменения)
# ==========================================
@bot.event
async def on_ready():
    print('='*40)
    print(f'✅ Бот запущен! Имя: {bot.user.name}')
    print(f'📬 Всего подано заявок: {stats["total_applications"]}')
    print('='*40)

# ✅ Добавили команду !start (она полностью дублирует !anketa, но с приветствием)
@bot.command()
async def start(ctx):
    embed = discord.Embed(
        title="🎮 Добро пожаловать в клан!",
        description="Мы рады видеть тебя здесь! Чтобы вступить в наш клан Minecraft, тебе нужно заполнить анкету.\n\nНажми на кнопку ниже, чтобы начать!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Анкета займёт всего пару минут")
    await ctx.send(embed=embed, view=StartButtonView())

# Старая команда тоже работает
@bot.command()
async def anketa(ctx):
    await ctx.send("👋 Нажмите на кнопку ниже, чтобы начать анкету:", view=StartButtonView())

# Добавление админа
@bot.command()
async def addadmin(ctx, member: discord.Member):
    if ctx.author.id != 1459971163013910641:
        await ctx.send("⛔ Только владелец бота может добавлять администраторов.")
        return

    if member.id in admin_ids:
        await ctx.send(f"👑 {member.mention} уже есть в списке администраторов.")
    else:
        admin_ids.append(member.id)
        save_admins(admin_ids)
        await ctx.send(f"✅ {member.mention} теперь может отвечать на анкеты через бота!")

# Удаление админа
@bot.command()
async def removeadmin(ctx, member: discord.Member):
    if ctx.author.id != 1459971163013910641:
        await ctx.send("⛔ Только владелец бота может удалять администраторов.")
        return

    if member.id in admin_ids:
        admin_ids.remove(member.id)
        save_admins(admin_ids)
        await ctx.send(f"✅ {member.mention} больше не может отвечать на анкеты.")
    else:
        await ctx.send(f"👑 {member.mention} нет в списке администраторов.")

# Статистика
@bot.command()
async def stats(ctx):
    embed = discord.Embed(
        title="📊 Статистика набора в клан",
        color=discord.Color.purple()
    )
    embed.add_field(name="📨 Всего подано анкет", value=str(stats["total_applications"]), inline=False)
    embed.add_field(name="👑 Администраторов (могут отвечать)", value=str(len(admin_ids)), inline=False)
    embed.set_footer(text="Статистика обновляется в реальном времени")
    await ctx.send(embed=embed)

# Помощь
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 Команды бота",
        color=discord.Color.gold()
    )
    embed.add_field(name="!start", value="🎮 Показать приветствие и начать анкету", inline=False)
    embed.add_field(name="!anketa", value="📝 Открыть анкету для вступления", inline=False)
    embed.add_field(name="!stats", value="📊 Показать статистику заявок", inline=False)
    embed.add_field(name="!addadmin @ник", value="👑 Добавить админа (для владельца)", inline=False)
    embed.add_field(name="!removeadmin @ник", value="👑 Удалить админа (для владельца)", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ ОШИБКА ЗАПУСКА: {e}')
