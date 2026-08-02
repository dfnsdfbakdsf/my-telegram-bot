import discord
from discord.ext import commands
from discord.ui import View, Button  # Добавили для создания кнопок (как в Telegram)
import sys
import os

# 🛡️ Берем токен из переменной окружения
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен в переменных окружения!')
    print('❗ Проверьте настройки хостинга (переменная DISCORD_TOKEN)')
    sys.exit()

print(f'🚀 ЗАПУСК БОТА...')

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- Класс для создания Кнопок (как клавиатура в Telegram) ---
class MenuView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🕒 Время", style=discord.ButtonStyle.green)
    async def time_button(self, interaction: discord.Interaction, button: Button):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        await interaction.response.send_message(f"🕒 Текущее время: {now}", ephemeral=True)

    @discord.ui.button(label="📊 Инфо", style=discord.ButtonStyle.blurple)
    async def info_button(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title=f"Информация о боте",
            color=discord.Color.blue()
        )
        embed.add_field(name="Серверов", value=len(bot.guilds))
        embed.add_field(name="Задержка", value=f"{round(bot.latency * 1000)}ms")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="❌ Закрыть меню", style=discord.ButtonStyle.red)
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="✅ Меню закрыто.", view=None, embed=None)

# --- События ---
@bot.event
async def on_ready():
    print('='*60)
    print('✅ БОТ УСПЕШНО ЗАПУЩЕН!')
    print(f'📌 Имя: {bot.user.name}')
    print(f'🆔 ID: {bot.user.id}')
    print('='*60)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# --- Команды ---

# 1. Классическое приветствие
@bot.command()
async def start(ctx):
    await ctx.send(f'Привет, {ctx.author.mention}! Я твой Discord-бот 🤖')

@bot.command()
async def hello(ctx):
    await ctx.send(f'Привет, {ctx.author.mention}! 👋')

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Понг! {latency}ms')

# 2. Команда с меню (аналог Inline Keyboard в Telegram)
@bot.command()
async def menu(ctx):
    embed = discord.Embed(
        title="📋 Главное меню",
        description="Нажмите на кнопки ниже, чтобы получить информацию:",
        color=discord.Color.green()
    )
    # Отправляем Embed вместе с кнопками
    await ctx.send(embed=embed, view=MenuView())

# 3. Команда info
@bot.command()
async def info(ctx):
    embed = discord.Embed(
        title=f"Информация о {bot.user.name}",
        color=discord.Color.green()
    )
    embed.add_field(name="ID", value=bot.user.id)
    embed.add_field(name="Серверов", value=len(bot.guilds))
    embed.add_field(name="Задержка", value=f"{round(bot.latency * 1000)}ms")
    embed.add_field(name="Префикс", value="!")
    await ctx.send(embed=embed)

# 4. Очистка чата (аналог /clear)
@bot.command()
async def clear(ctx, amount: int = 5):
    if amount < 1 or amount > 100:
        await ctx.send("❌ Укажите число от 1 до 100")
        return
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Удалено {amount} сообщений", delete_after=3)

# 5. Обновленная команда Help
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 Список команд",
        description="Используйте `!` перед командой",
        color=discord.Color.gold()
    )
    
    commands_list = [
        ("start / hello", "Поздороваться с ботом"),
        ("ping", "Проверить задержку"),
        ("menu", "Открыть меню с кнопками"),
        ("info", "Информация о боте"),
        ("clear [число]", "Очистить сообщения (1-100)"),
        ("help", "Показать это сообщение")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=f"!{cmd}", value=desc, inline=False)
    
    await ctx.send(embed=embed)

# --- Запуск ---
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print('❌ ОШИБКА: Неверный токен!')
    except Exception as e:
        print(f'❌ ОШИБКА: {e}')
