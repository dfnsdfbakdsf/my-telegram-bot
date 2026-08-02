import discord
from discord.ext import commands
from discord.ui import Modal, TextInput
import os
import sys
import datetime
import re
import json
import time

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
stats = load_stats()
blacklisted_users = load_blacklist()
pending_applications = {}

# ==========================================
# 1. МОДАЛЬНОЕ ОКНО
# ==========================================
class ApplicationModal(Modal, title="Анкета в клан Minecraft"):
    name = TextInput(label="Как вас зовут? (реальное имя)", placeholder="Введите имя...", required=True)
    age = TextInput(label="Сколько вам лет?", placeholder="Например: 16", required=True)
    nickname = TextInput(label="Ваш никнейм на сервере Minecraft", placeholder="Например: _Vortex_", required=True)
    donate = TextInput(label="Какой у вас донат?", placeholder="VIP, Premium или без доната", required=True)
    playtime = TextInput(label="Сколько часов в день играете?", placeholder="Только число", required=True)
    pvp = TextInput(label="Навык PvP (от 1 до 10)", placeholder="Введите число", required=True)
    pve = TextInput(label="Навык PvE (от 1 до 10)", placeholder="Введите число", required=True)
    server_population = TextInput(label="Сколько всего вы играете на сервере?", placeholder="Напишите количество", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.user

        if user.id in blacklisted_users:
            await interaction.response.send_message("⛔ Вы в черном списке клана!", ephemeral=True)
            return

        embed = discord.Embed(
            title="📥 Новая анкета на вступление!",
            description=f"От: {user.mention} (ID: {user.id})",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="👤 Реальное имя", value=self.name.value, inline=False)
        embed.add_field(name="🎂 Возраст", value=f"{self.age.value} лет", inline=False)
        embed.add_field(name="🪪 Никнейм MC", value=self.nickname.value, inline=False)
        embed.add_field(name="💰 Донат", value=self.donate.value, inline=False)
        embed.add_field(name="⏳ В день играет", value=f"{self.playtime.value} ч.", inline=False)
        embed.add_field(name="⚔️ PvP (1-10)", value=self.pvp.value, inline=True)
        embed.add_field(name="👹 PvE (1-10)", value=self.pve.value, inline=True)
        embed.add_field(name="👥 Сколько играют на сервере", value=self.server_population.value, inline=False)

        try:
            target_channel = bot.get_channel(CHANNEL_ID)
            if target_channel:
                sent_message = await target_channel.send(embed=embed)
                pending_applications[sent_message.id] = [user.id, int(time.time())]
                stats["total_applications"] += 1
                save_stats(stats)
                await interaction.response.send_message("✅ Анкета успешно отправлена руководству! Ожидайте ответа.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ошибка: канал не найден.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ Ошибка при отправке анкеты.", ephemeral=True)
            print(f"Ошибка: {e}")

# ==========================================
# 2. ОТВЕТЫ АДМИНА
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
        try:
            player = await bot.fetch_user(target_user_id)
            await player.send(f"📩 **Ответ от руководства:**\n\n{clean_text}")
            await message.reply(f"✅ Ответ отправлен {player.mention}.", mention_author=False)
        except:
            await message.reply("❌ Не удалось отправить ответ.", mention_author=False)
    else:
        await message.reply("⚠️ Не найдена анкета перед этим сообщением.", mention_author=False)

# ==========================================
# 3. КОМАНДЫ (ПОЛНОСТЬЮ ИСПРАВЛЕНА)
# ==========================================
@bot.event
async def on_ready():
    print('✅ Бот запущен!')

@bot.command()
async def start(ctx):
    if ctx.author.id in blacklisted_users:
        await ctx.send("⛔ Вы в черном списке.", ephemeral=True)
        return

    # ✅ Самое надежное решение: используем ctx.interaction напрямую
    await ctx.interaction.response.send_modal(ApplicationModal())

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
    embed = discord.Embed(title="📊 Статистика", color=discord.Color.purple())
    embed.add_field(name="📨 Анкет", value=str(stats["total_applications"]))
    embed.add_field(name="👑 Админов", value=str(len(admin_ids)))
    embed.add_field(name="⛔ В ЧС", value=str(len(blacklisted_users)))
    await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📋 Команды", color=discord.Color.gold())
    embed.add_field(name="!start / !anketa", value="📝 Открыть анкету", inline=False)
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
