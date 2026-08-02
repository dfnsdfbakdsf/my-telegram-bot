import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import sys
import datetime
import asyncio

# 🛡️ Токен и настройки
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ID = 1459971163013910641  # 🔴 ЗАМЕНИТЕ НА ВАШ ID!

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 1. КНОПКА ДЛЯ ОТКРЫТИЯ ЛС
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=120) # Кнопка живет 2 минуты

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        # Отвечаем, чтобы Discord не ругался
        await interaction.response.send_message("📨 Я отправил вам анкету в Личные Сообщения! Проверьте вкладку с ботом.", ephemeral=True)
        
        # Запускаем анкетирование в ЛС
        await ask_questions(interaction.user)

# ==========================================
# 2. ЛОГИКА АНКЕТЫ В ЛС (Самый надежный метод)
# ==========================================
async def ask_questions(user: discord.User):
    try:
        # Определяем вопросы и куда сохранять ответы
        questions = [
            {"key": "name", "q": "**Как вас зовут?** (Ваше реальное имя)"},
            {"key": "nickname", "q": "**Ваш никнейм на сервере Minecraft?**"},
            {"key": "donate", "q": "**Какой у вас донат?** (VIP, Premium или без доната)"},
            {"key": "playtime", "q": "**Сколько часов в день играете?**"},
            {"key": "pvp", "q": "**Оцените свой навык PvP (от 1 до 10)?**"},
            {"key": "pve", "q": "**Оцените свой навык PvE (от 1 до 10)?**"},
            {"key": "server_population", "q": "**Сколько всего человек играет на сервере?**"}
        ]
        
        answers = {} # Словарь для ответов
        await user.send("👋 **Привет! Я бот для сбора анкет в клан.**\nОтвечай на мои вопросы по очереди, и в конце я отправлю твою анкету админу.")

        for question in questions:
            # Отправляем вопрос и ждем 1 ответ (таймаут 5 минут)
            await user.send(question["q"])
            
            def check(msg):
                return msg.author == user and isinstance(msg.channel, discord.DMChannel)
            
            try:
                # Ждем ответ от пользователя
                reply = await bot.wait_for('message', timeout=300.0, check=check)
                answers[question["key"]] = reply.content
            except asyncio.TimeoutError:
                await user.send("⏳ Время вышло! Чтобы начать заново, напишите в чат `!anketa`.")
                return

        # ==========================================
        # 3. ВСЕ ОТВЕТЫ СОБРАНЫ - ОТПРАВЛЯЕМ АДМИНУ
        # ==========================================
        embed = discord.Embed(
            title="📥 Новая анкета на вступление!",
            description=f"От: {user.mention} (ID: {user.id})",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=user.display_avatar.url)

        embed.add_field(name="👤 Реальное имя", value=answers["name"], inline=False)
        embed.add_field(name="🪪 Никнейм MC", value=answers["nickname"], inline=False)
        embed.add_field(name="💰 Донат", value=answers["donate"], inline=False)
        embed.add_field(name="⏳ В день играет", value=answers["playtime"], inline=False)
        embed.add_field(name="⚔️ PvP (1-10)", value=answers["pvp"], inline=True)
        embed.add_field(name="👹 PvE (1-10)", value=answers["pve"], inline=True)
        embed.add_field(name="👥 Онлайн сервера", value=answers["server_population"], inline=False)

        # Отправляем админу в ЛС
        try:
            admin_user = await bot.fetch_user(ADMIN_ID)
            await admin_user.send(embed=embed)
            await user.send("✅ **Готово! Твоя анкета успешно отправлена администрации клана!** Ожидай ответа.")
        except Exception as e:
            await user.send("❌ Произошла ошибка при отправке анкеты админу. Пожалуйста, свяжитесь с руководством клана.")
            print(f"Ошибка отправки админу: {e}")

    except Exception as e:
        print(f"Ошибка в анкете для {user.name}: {e}")

# ==========================================
# 4. КОМАНДЫ БОТА
# ==========================================
@bot.event
async def on_ready():
    print('='*40)
    print(f'✅ Бот запущен! Имя: {bot.user.name}')
    print(f'📬 Анкеты будут отправляться админу с ID: {ADMIN_ID}')
    print('='*40)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def anketa(ctx):
    await ctx.send("👋 Нажмите на кнопку ниже, чтобы начать анкету:", view=StartButtonView())

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📋 Команды", color=discord.Color.gold())
    embed.add_field(name="!anketa", value="📝 Открыть анкету", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ ОШИБКА ЗАПУСКА: {e}')
