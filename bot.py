import discord
from discord.ext import commands
from discord.ui import Modal, TextInput
import os
import sys
import datetime

# 🛡️ Токен из переменной окружения
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

# Настройки бота
intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 1. СОЗДАЕМ МОДАЛЬНОЕ ОКНО (ФОРМА АНКЕТЫ)
# ==========================================
class ClanApplicationModal(Modal, title="📋 Анкета на вступление в клан"):
    
    # Поля для заполнения (как вопросы в Google Форме)
    name = TextInput(
        label="Как вас зовут? (реальное имя)",
        placeholder="Введите ваше имя...",
        required=True,
        style=discord.TextStyle.short
    )
    
    nickname = TextInput(
        label="Ваш никнейм на сервере Minecraft",
        placeholder="Например: _Vortex_",
        required=True,
        style=discord.TextStyle.short
    )
    
    donate = TextInput(
        label="Какой у вас донат?",
        placeholder="VIP, Premium, Без доната, и т.д.",
        required=True,
        style=discord.TextStyle.short
    )
    
    playtime = TextInput(
        label="Сколько часов в день играете?",
        placeholder="Например: 3-4 часа",
        required=True,
        style=discord.TextStyle.short
    )

    pvp = TextInput(
        label="Оцените свой навык PvP (от 1 до 10)",
        placeholder="Введите число от 1 до 10",
        required=True,
        style=discord.TextStyle.short
    )

    pve = TextInput(
        label="Оцените свой навык PvE (от 1 до 10)",
        placeholder="Введите число от 1 до 10",
        required=True,
        style=discord.TextStyle.short
    )

    server_population = TextInput(
        label="Сколько всего человек играет на сервере?",
        placeholder="Например: 50-100",
        required=True,
        style=discord.TextStyle.short
    )

    # Что происходит, когда пользователь нажал "Отправить"
    async def on_submit(self, interaction: discord.Interaction):
        # Собираем всё в одну красивую анкету
        embed = discord.Embed(
            title="📥 Новая анкета на вступление в клан!",
            description=f"От: {interaction.user.mention}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        embed.add_field(name="👤 Реальное имя", value=self.name.value, inline=False)
        embed.add_field(name="🪪 Никнейм MC", value=self.nickname.value, inline=False)
        embed.add_field(name="💰 Донат", value=self.donate.value, inline=False)
        embed.add_field(name="⏳ В день играет", value=self.playtime.value, inline=False)
        embed.add_field(name="⚔️ PvP (1-10)", value=self.pvp.value, inline=True)
        embed.add_field(name="👹 PvE (1-10)", value=self.pve.value, inline=True)
        embed.add_field(name="👥 Онлайн сервера", value=self.server_population.value, inline=False)
        
        embed.set_footer(text=f"ID заявителя: {interaction.user.id}")

        # Отправляем анкету прямо в этот же чат (чтобы все видели)
        await interaction.response.send_message(embed=embed)
        
        # (Опционально) Если хотите, чтобы анкета дублировалась вам в ЛС, раскомментируйте:
        # await interaction.user.send("✅ Ваша анкета отправлена! Ожидайте ответа от руководства клана.")

    # Если пользователь нажал "Отмена" или закрыл окно
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message("❌ Произошла ошибка при отправке анкеты. Попробуйте снова.", ephemeral=True)

# ==========================================
# 2. СОБЫТИЯ И КОМАНДЫ
# ==========================================

@bot.event
async def on_ready():
    print('='*40)
    print(f'✅ Бот запущен! Имя: {bot.user.name}')
    print(f'🚀 Готов принимать анкеты!')
    print('='*40)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# Команда для вызова анкеты
@bot.command()
async def anketa(ctx):
    # Открываем модальное окно перед пользователем
    await ctx.send("📝 Открываю форму для заполнения анкеты...", ephemeral=True)
    await ctx.interaction.response.send_modal(ClanApplicationModal())

# Простая команда помощи
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 Команды для набора в клан",
        description="Используйте `!` перед командой",
        color=discord.Color.gold()
    )
    embed.add_field(name="!anketa", value="📝 Открыть анкету на вступление в клан", inline=False)
    embed.add_field(name="!help", value="Показать это сообщение", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК БОТА
# ==========================================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ ОШИБКА ЗАПУСКА: {e}')
