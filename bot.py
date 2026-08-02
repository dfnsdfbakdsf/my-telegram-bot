import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import sys
import datetime
import re
import json
import time
import asyncio

# 🛡️ Токен и настройки
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = 1533430617524539545

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 0. ФАЙЛЫ
# ==========================================
ADMINS_FILE = "admins.json"
STATS_FILE = "stats.json"
BLACKLIST_FILE = "blacklist.json"

def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_admins(admins_list):
    with open(ADMINS_FILE, 'w') as f:
        json.dump(admins_list, f)

def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {"total_applications": 0}

def save_stats(stats_data):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats_data, f)

def load_blacklist():
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r') as f:
            return json.load(f)
    return []

def save_blacklist(blacklist_list):
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump(blacklist_list, f)

admin_ids = load_admins()
stats_data = load_stats() # 🛡️ ПЕРЕИМЕНОВАНО, ЧТОБЫ НЕ БЫЛО КОНФЛИКТА
blacklisted_users = load_blacklist()
pending_applications = {}
pending_confirmations = {}

# ==========================================
# 1. КНОПКА ДЛЯ ОТКРЫТИЯ АНКЕТЫ
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        user = interaction.user
        
        if user.id in blacklisted_users:
            await interaction.response.send_message("⛔ Вы в черном списке клана!", ephemeral=True)
            return
        
        await interaction.response.send_message("📨 Я отправил вам анкету в Личные Сообщения! Проверьте вкладку с ботом.", ephemeral=True)
        await start_dm_application(user)

# ==========================================
# 2. ЛОГИКА АНКЕТЫ В ЛС
# ==========================================
async def start_dm_application(user: discord.User):
    try:
        questions = [
            {"key": "name", "q": "**Как вас зовут?** (Ваше реальное имя)"},
            {"key": "age", "q": "**Сколько вам лет?** (Введите число)"},
            {"key": "nickname", "q": "**Ваш никнейм на сервере Minecraft?**"},
            {"key": "donate", "q": "**Какой у вас донат?** (VIP, Premium или без доната)"},
            {"key": "playtime", "q": "**Сколько часов в день вы играете?** (Введите только число)"},
            {"key": "pvp", "q": "**Оцените свой навык PvP (от 1 до 10)?** (Введите число)"},
            {"key": "pve", "q": "**Оцените свой навык PvE (от 1 до 10)?** (Введите число)"},
            {"key": "server_population", "q": "**Сколько всего вы играете на сервере?** (Напишите количество)"}
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

                    if question["key"] in ["age", "playtime"]:
                        if not answer_text.isdigit() or int(answer_text) < 1:
                            await user.send("❌ Ошибка! Пожалуйста, введите **положительное число**. Попробуйте снова.")
                            continue
                    
                    if question["key"] in ["pvp", "pve"]:
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
                pending_applications[sent_message.id] = [user.id, int(time.time())]
                stats_data["total_applications"] += 1
                save_stats(stats_data)
                await user.send("✅ **Готово! Твоя анкета успешно отправлена!** Ожидай ответа от руководства.")
            else:
                await user.send("❌ Ошибка: канал не найден.")
        except Exception as e:
            await user.send("❌ Произошла ошибка при отправке анкеты.")
            print(f"Ошибка: {e}")

    except Exception as e:
        print(f"Ошибка в анкете для {user.name}: {e}")

# ==========================================
# 3. ОТВЕТЫ АДМИНА (ДВУХЭТАПНАЯ ПРОВЕРКА)
# ==========================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

    # 1. Обработка подтверждения
    if message.reference and message.reference.message_id in pending_confirmations:
        if message.content.strip().lower() == "да":
            data = pending_confirmations.pop(message.reference.message_id, None)
            if data:
                target_user_id, reply_text = data
                try:
                    player = await bot.fetch_user(target_user_id)
                    await player.send(f"📩 **Ответ от руководства:**\n\n{reply_text}")
                    await message.reply(f"✅ Ответ успешно отправлен!", mention_author=False)
                except:
                    await message.reply("❌ Не удалось отправить ответ.", mention_author=False)
                return
        else:
            await message.reply("❌ Подтверждение не получено. Отправка отменена. Чтобы подтвердить, напишите просто **Да**.")
            return

    # 2. Обработка упоминаний бота в канале анкет
    if message.channel.id != CHANNEL_ID:
        return
    if bot.user not in message.mentions:
        return

    clean_text = re.sub(rf'<@!?{bot.user.id}>', '', message.content).strip()
    if not clean_text:
        return

    target_user_id = None
    target_msg_id = None
    async for msg in message.channel.history(limit=20):
        if msg.author == bot.user and msg.embeds:
            if msg.id in pending_applications:
                target_user_id = pending_applications[msg.id][0]
                target_msg_id = msg.id
                break

    if target_user_id:
        if int(time.time()) - pending_applications[target_msg_id][1] > 259200:
            await message.reply("⏰ Анкета устарела (более 3 дней).", mention_author=False)
            del pending_applications[target_msg_id]
            return
        
        confirm_msg = await message.reply(
            f"🛡️ **Подтверждение отправки**\nВы собираетесь отправить игроку:\n```{clean_text}```\n\nНапишите **Да** в ответ на это сообщение, чтобы подтвердить отправку.",
            mention_author=False
        )
        pending_confirmations[confirm_msg.id] = [target_user_id, clean_text]
    else:
        await message.reply("⚠️ Не найдена анкета перед этим сообщением.", mention_author=False)

# ==========================================
# 4. КОМАНДЫ БОТА
# ==========================================
@bot.event
async def on_ready():
    print('✅ Бот запущен! Статистика исправлена.')

@bot.command()
async def start(ctx):
    if ctx.author.id in blacklisted_users:
        await ctx.send("⛔ Вы в черном списке.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎮 Добро пожаловать в клан!",
        description="Мы рады видеть тебя здесь! Чтобы вступить в наш клан Minecraft, тебе нужно заполнить анкету.\n\nНажми на кнопку ниже, чтобы начать!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Анкета займёт всего пару минут")
    await ctx.send(embed=embed, view=StartButtonView())

@bot.command()
async def anketa(ctx):
    await ctx.invoke(bot.get_command("start"))

@bot.command()
async def view(ctx, member: discord.Member):
    for msg_id, data in list(pending_applications.items()):
        if data[0] == member.id:
            try:
                msg = await bot.get_channel(CHANNEL_ID).fetch_message(msg_id)
                await ctx.send(embed=msg.embeds[0])
                return
            except:
                del pending_applications[msg_id]
    await ctx.send("❌ Анкета не найдена или устарела.")

@bot.command()
async def blacklist(ctx, member: discord.Member):
    if ctx.author.id != 1459971163013910641:
        await ctx.send("⛔ Только владелец.", ephemeral=True)
        return
    if member.id in blacklisted_users:
        await ctx.send("⛔ Уже в ЧС.")
        return
    blacklisted_users.append(member.id)
    save_blacklist(blacklisted_users)
    await ctx.send(f"✅ {member.mention} в ЧС.")

@bot.command()
async def unblacklist(ctx, member: discord.Member):
    if ctx.author.id != 1459971163013910641:
        await ctx.send("⛔ Только владелец.", ephemeral=True)
        return
    if member.id not in blacklisted_users:
        await ctx.send("✅ Не в ЧС.")
        return
    blacklisted_users.remove(member.id)
    save_blacklist(blacklisted_users)
    await ctx.send(f"✅ {member.mention} удален из ЧС.")

@bot.command()
async def stats(ctx):
    embed = discord.Embed(
        title="📊 Статистика набора в клан",
        color=discord.Color.purple()
    )
    embed.add_field(name="📨 Всего подано анкет", value=str(stats_data["total_applications"]), inline=False)
    embed.add_field(name="👑 Администраторов (могут отвечать)", value=str(len(admin_ids)), inline=False)
    embed.add_field(name="⛔ В черном списке", value=str(len(blacklisted_users)), inline=False)
    embed.set_footer(text="Статистика обновляется в реальном времени")
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📋 Команды", color=discord.Color.gold())
    embed.add_field(name="!start / !anketa", value="📝 Открыть анкету (с кнопкой)", inline=False)
    embed.add_field(name="!view @Ник", value="📄 Показать анкету", inline=False)
    embed.add_field(name="!blacklist @Ник", value="🚫 В ЧС (владелец)", inline=False)
    embed.add_field(name="!unblacklist @Ник", value="✅ Из ЧС (владелец)", inline=False)
    embed.add_field(name="!stats", value="📊 Статистика", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    bot.run(TOKEN)
