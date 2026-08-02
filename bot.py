import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
import os
import sys
import datetime

# 🛡️ Токен и настройки
TOKEN = os.getenv('DISCORD_TOKEN')
# 👇 ВСТАВЬТЕ СВОЙ ЦИФРОВОЙ ID (включите режим разработчика в Discord -> ПКМ по себе -> Копировать ID)
ADMIN_ID = 1459971163013910641  # ЗАМЕНИТЕ ЭТО ЧИСЛО НА ВАШ ID

if TOKEN is None:
    print('❌ ОШИБКА: Не найден токен (переменная DISCORD_TOKEN)')
    sys.exit()

intents = discord.Intents().all()
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# ==========================================
# 1. ФОРМА АНКЕТЫ (Всплывающее окно)
# ==========================================
class ClanApplicationModal(Modal, title="📋 Анкета в клан Minecraft"):
    
    name = TextInput(label="Как вас зовут? (реальное имя)", placeholder="Ваше имя...", required=True)
    nickname = TextInput(label="Ваш никнейм на сервере Minecraft", placeholder="Например: _Vortex_", required=True)
    donate = TextInput(label="Какой у вас донат?", placeholder="VIP, Premium, Без доната...", required=True)
    playtime = TextInput(label="Сколько часов в день играете?", placeholder="Например: 3-4 часа", required=True)
    pvp = TextInput(label="Оцените свой навык PvP (от 1 до 10)", placeholder="Число от 1 до 10", required=True)
    pve = TextInput(label="Оцените свой навык PvE (от 1 до 10)", placeholder="Число от 1 до 10", required=True)
    server_population = TextInput(label="Сколько всего человек играет на сервере?", placeholder="Например: 50-100", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📥 Новая анкета на вступление!",
            description=f"От: {interaction.user.mention} (ID: {interaction.user.id})",
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

        try:
            admin_user = await bot.fetch_user(ADMIN_ID)
            await admin_user.send(embed=embed)
            await interaction.response.send_message("✅ **Ваша анкета успешно отправлена администрации!** Ожидайте ответа.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("❌ **Ошибка!** Не удалось отправить анкету. Попробуйте позже.", ephemeral=True)
            print(f"❗ Ошибка: {e}")

# ==========================================
# 2. КНОПКА (Чтобы открыть форму)
# ==========================================
class StartButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 Заполнить анкету", style=discord.ButtonStyle.success)
    async def start_survey(self, interaction: discord.Interaction, button: Button):
        # По нажатию на кнопку открывается модальное окно
        await interaction.response.send_modal(ClanApplicationModal())

# ==========================================
# 3. СОБЫТИЯ И КОМАНДЫ
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

# 👇 ТЕПЕРЬ ЭТО РАБОТАЕТ ИДЕАЛЬНО
@bot.command()
async def anketa(ctx):
    # Отправляем кнопку в чат, при нажатии откроется анкета
    await ctx.send("👋 Нажмите на кнопку ниже, чтобы начать заполнение анкеты:", view=StartButtonView())

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 Команды для набора в клан",
        color=discord.Color.gold()
    )
    embed.add_field(name="!anketa", value="📝 Открыть анкету (нажмите кнопку)", inline=False)
    embed.add_field(name="!help", value="Показать помощь", inline=False)
    await ctx.send(embed=embed)

# ==========================================
# ЗАПУСК
# ==========================================
if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f'❌ ОШИБКА ЗАПУСКА: {e}')
