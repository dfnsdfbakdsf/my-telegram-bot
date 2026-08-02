import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import sys
import datetime
import asyncio

# 🛡️ Токен и настройки
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ID = 1459971163013910641  # Ваш ID (оставил на всякий случай)
CHANNEL_ID = 1526651138378567842  # 🆕 ID канала, куда отправлять анкеты

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 1. КНОПКА
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("📨 Я отправил вам анкету в Личные Сообщения! Проверьте вкладку с ботом.", ephemeral=True)
        await ask_questions(interaction.user)

# ==========================================
# 2. АНКЕТА В ЛС (С проверками)
# ==========================================
async def ask_questions(user: discord.User):
    try:
        questions = [
            {"key": "name", "q": "**Как вас зовут?** (Ваше реальное имя)", "type": "text"},
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
            while True: # Цикл для проверки ответа
                await user.send(question["q"])
                
                def check(msg):
                    return msg.author == user and isinstance(msg.channel, discord.DMChannel)
                
                try:
                    reply = await bot.wait_for('message', timeout=300.0, check=check)
                    answer_text = reply.content.strip()

                    # ✅ Проверка для числовых полей
                    if question["type"] == "number":
                        if not answer_text.isdigit():
                            await user.send("❌ Ошибка! Пожалуйста, введите **только число** (например: 3). Попробуйте снова.")
                            continue # Запускает вопрос заново
                    
                    # ✅ Проверка для PvP и PvE (число от 1 до 10)
                    if question["type"] == "range":
                        if not answer_text.isdigit():
                            await user.send("❌ Ошибка! Введите **только цифру** от 1 до 10.")
                            continue
                        num = int(answer_text)
                        if num < 1 or num > 10:
                            await user.send("❌ Ошибка! Введите число **от 1 до 10**.")
                            continue

                    # Если всё проверки пройдены, сохраняем ответ и идём к следующему вопросу
                    answers[question["key"]] = answer_text
                    break 

                except asyncio.TimeoutError:
                    await user.send("⏳ Время вышло! Чтобы начать заново, напишите в чат `!anketa`.")
                    return

        # ==========================================
        # 3. ОТПРАВКА АНКЕТЫ В КАНАЛ (по ID)
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
        embed.add_field(name="⏳ В день играет", value=f"{answers['playtime']} ч.", inline=False)
        embed.add_field(name="⚔️ PvP (1-10)", value=answers["pvp"], inline=True)
        embed.add_field(name="👹 PvE (1-10)", value=answers["pve"], inline=True)
        embed.add_field(name="👥 Сколько играют на сервере", value=answers["server_population"], inline=False)

        # Отправляем в УКАЗАННЫЙ КАНАЛ
        try:
            target_channel = bot.get_channel(CHANNEL_ID)
            if target_channel:
                await target_channel.send(embed=embed)
                await user.send("✅ **Готово! Твоя анкета успешно отправлена в канал для рассмотрения!** Ожидай ответа.")
            else:
                # Если бот не видит канал (например, его там нет)
                await user.send("❌ Ошибка: Я не могу найти указанный канал или у меня нет туда доступа. Сообщите администратору.")
                print(f"Ошибка: Не найден канал с ID {CHANNEL_ID}")
        except Exception as e:
            await user.send("❌ Произошла ошибка при отправке анкеты.")
            print(f"Ошибка отправки в канал: {e}")

    except Exception as e:
        print(f"Ошибка в анкете для {user.name}: {e}")

# ==========================================
# 4. КОМАНДЫ БОТА
# ==========================================
@bot.event
async def on_ready():
    print('='*40)
    print(f'✅ Бот запущен! Имя: {bot.user.name}')
    print(f'📬 Анкеты будут отправляться в канал с ID: {CHANNEL_ID}')
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
