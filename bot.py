import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import sys
import datetime
import asyncio
import re
import json
import time

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

# Инициализация данных
admin_ids = load_admins()
stats = load_stats()
blacklist = load_blacklist()

# ВАЖНО: pending_applications теперь хранит ID анкеты, ID игрока И время создания (в секундах)
# {"msg_id": [user_id, timestamp]}
pending_applications = {}

# ==========================================
# 1. КНОПКА ДЛЯ СТАРТА АНКЕТЫ
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        
        # 🚫 ПРОВЕРКА НА ЧЕРНЫЙ СПИСОК
        if user_id in blacklist:
            await interaction.response.send_message("⛔ **Вы в черном списке клана!** Вам запрещено подавать заявки.", ephemeral=True)
            return
            
        await interaction.response.send_message("📨 Я отправил вам анкету в ЛС! Проверьте вкладку с ботом.", ephemeral=True)
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

        await user.send("⏳ Ваша анкета обрабатывается и отправляется руководству...")
        
        try:
            target_channel = bot.get_channel(CHANNEL_ID)
            if target_channel:
                sent_message = await target_channel.send(embed=embed)
                
                # 💾 Сохраняем анкету: ID сообщения -> [ID юзера, ВРЕМЯ СОЗДАНИЯ]
                pending_applications[sent_message.id] = [user.id, int(time.time())]
                
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
# 3. ОБРАБОТКА ОТВЕТОВ ОТ АДМИНА (С ПРОВЕРКОЙ НА 3 ДНЯ)
# ==========================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    if message.channel.id != CHANNEL_ID:
        return

    if bot.user not in message.mentions:
        return

    admin_reply_text = message.content
    clean_text = re.sub(rf'<@!?{bot.user.id}>', '', admin_reply_text).strip()

    if not clean_text:
        return

    target_user_id = None
    target_msg_id = None

    # 🔍 Ищем анкету в истории
    async for msg in message.channel.history(limit=20):
        if msg.author == bot.user and msg.embeds:
            if msg.id in pending_applications:
                target_user_id = pending_applications[msg.id][0]
                target_msg_id = msg.id
                break

    if target_user_id:
        # ⏳ ПРОВЕРКА НА 3 ДНЯ
        creation_time = pending_applications[target_msg_id][1]
        current_time = int(time.time())
        
        # 3 дня = 3 * 24 * 60 * 60 = 259200 секунд
        if current_time - creation_time > 259200:
            await message.reply("⏰ **Анкета устарела (прошло более 3 дней).** Я удалил её из памяти и не буду отправлять ответы на неё.", mention_author=False)
            del pending_applications[target_msg_id] # Удаляем старую анкету
            return

        try:
            player_user = await bot.fetch_user(target_user_id)
            final_message = f"📩 **Ответ от руководства клана по вашей заявке:**\n\n{clean_text}"
            await player_user.send(final_message)
            
            await message.reply(f"✅ Ответ успешно отправлен игроку {player_user.mention} в личные сообщения.", mention_author=False)
            # Анкета НЕ удаляется из памяти, чтобы можно было отвечать несколько раз
            
        except Exception as e:
            await message.reply(f"❌ Не удалось отправить сообщение игроку. Ошибка: {e}")
    else:
        await message.reply("⚠️ Я не нашёл анкету перед этим сообщением. Убедитесь, что вы ответили под анкетой.", mention_author=False)

# ==========================================
# 4. НОВЫЕ КОМАНДЫ (Пункт 4: !view и Пункт 5: !blacklist)
# ==========================================
@bot.event
async def on_ready():
    print('='*40)
    print(f'✅ Бот запущен! Имя: {bot.user.name}')
    print(f'📬 Всего подано заявок: {stats["total_applications"]}')
    print('='*40)

# 📝 Команда !view для просмотра анкеты по нику
@bot.command()
async def view(ctx, member: discord.Member):
    # Ищем анкету этого участника в списке pending_applications
    found_application = False
    
    for msg_id, data in list(pending_applications.items()):
        user_id = data[0]
        if user_id == member.id:
            # Нашли анкету! Теперь нужно получить сообщение по ID
            try:
                target_channel = bot.get_channel(CHANNEL_ID)
                msg = await target_channel.fetch_message(msg_id)
                # Отправляем анкету заново
                await ctx.send(f"📄 **Анкета игрока {member.mention}:**")
                await ctx.send(embed=msg.embeds[0])
                found_application = True
                break
            except:
                # Если сообщение удалено из чата, удаляем и из памяти
                del pending_applications[msg_id]
                continue

    if not found_application:
        await ctx.send(f"❌ Не найдено активных анкет для игрока {member.mention} (или анкета устарела и удалена).")

# 🚫 Команда !blacklist
@bot.command()
async def blacklist(ctx, member: discord.Member):
    if member.id in blacklist:
        await ctx.send(f"⛔ {member.mention} уже находится в черном списке.")
        return
    
    blacklist.append(member.id)
    save_blacklist(blacklist)
    await ctx.send(f"✅ {member.mention} добавлен в черный список клана. Он не сможет подавать заявки.")

# ✅ Команда !unblacklist
@bot.command()
async def unblacklist(ctx, member: discord.Member):
    if member.id not in blacklist:
        await ctx.send(f"✅ {member.mention} не находится в черном списке.")
        return
    
    blacklist.remove(member.id)
    save_blacklist(blacklist)
    await ctx.send(f"✅ {member.mention} удален из черного списка клана. Теперь он может подавать заявки.")

# ==========================================
# 5. ОСТАЛЬНЫЕ КОМАНДЫ
# ==========================================
@bot.command()
async def start(ctx):
    embed = discord.Embed(
        title="🎮 Добро пожаловать в клан!",
        description="Мы рады видеть тебя здесь! Чтобы вступить в наш клан Minecraft, тебе нужно заполнить анкету.\n\nНажми на кнопку ниже, чтобы начать!",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Анкета займёт всего пару минут")
    await ctx.send(embed=embed, view=StartButtonView())

@bot.command()
async def anketa(ctx):
    await ctx.send("👋 Нажмите на кнопку ниже, чтобы начать анкету:", view=StartButtonView())

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

@bot.command()
async def stats(ctx):
    embed = discord.Embed(
        title="📊 Статистика набора в клан",
        color=discord.Color.purple()
    )
    embed.add_field(name="📨 Всего подано анкет", value=str(stats["total_applications"]), inline=False)
    embed.add_field(name="👑 Администраторов (могут отвечать)", value=str(len(admin_ids)), inline=False)
    embed.add_field(name="⛔ В черном списке", value=str(len(blacklist)), inline=False)
    embed.set_footer(text="Статистика обновляется в реальном времени")
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 Команды бота",
        color=discord.Color.gold()
    )
    embed.add_field(name="!start / !anketa", value="🎮 Начать анкету", inline=False)
    embed.add_field(name="!view @Ник", value="📄 Показать анкету игрока", inline=False)
    embed.add_field(name="!blacklist @Ник", value="🚫 Забанить игрока (запретить анкеты)", inline=False)
    embed.add_field(name="!unblacklist @Ник", value="✅ Разбанить игрока", inline=False)
    embed.add_field(name="!stats", value="📊 Показать статистику", inline=False)
    embed.add_field(name="!addadmin @Ник", value="👑 Добавить админа", inline=False)
    embed.add_field(name="!removeadmin @Ник", value="👑 Удалить админа", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ ОШИБКА ЗАПУСКА: {e}')
