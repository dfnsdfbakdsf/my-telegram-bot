import discord
from discord.ext import commands
import sys

# ВСТАВЬТЕ ТОКЕН СЮДА (Только ваш токен, без лишних кавычек)
TOKEN = 'ВАШ_ТОКЕН_БОТА_СЮДА'

if TOKEN == 'ВАШ_ТОКЕН_БОТА_СЮДА':
    print('❌ ОШИБКА: Вы не вставили токен!')
    sys.exit()

print(f'🚀 ЗАПУСК БОТА...')

intents = discord.Intents().all()

# 👇 ГЛАВНОЕ ИСПРАВЛЕНИЕ: Добавлено help_command=None
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

@bot.event
async def on_ready():
    print('='*60)
    print('✅ БОТ УСПЕШНО ЗАПУЩЕН!')
    print(f'📌 Имя: {bot.user.name}')
    print(f'🆔 ID: {bot.user.id}')
    print(f'📊 На серверах: {len(bot.guilds)}')
    
    for guild in bot.guilds:
        print(f'  📁 {guild.name}')
        for channel in guild.text_channels:
            try:
                await channel.send('✅ Бот запущен! Используйте `!hello`')
                print(f'  ✅ Сообщение отправлено в #{channel.name}')
                break
            except:
                pass
    
    print('='*60)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)

@bot.command()
async def hello(ctx):
    await ctx.send(f'Привет, {ctx.author.mention}! 👋')

@bot.command()
async def ping(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f'🏓 Понг! {latency}ms')

@bot.command()
async def test(ctx):
    await ctx.send('✅ Бот работает!')

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

@bot.command()
async def clear(ctx, amount: int = 5):
    if amount < 1 or amount > 100:
        await ctx.send("❌ Укажите число от 1 до 100")
        return
    await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ Удалено {amount} сообщений", delete_after=3)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="📋 Список команд",
        description="Используйте `!` перед командой",
        color=discord.Color.gold()
    )
    
    commands_list = [
        ("hello", "Поздороваться"),
        ("ping", "Проверить задержку"),
        ("test", "Проверить работу"),
        ("info", "Информация о боте"),
        ("clear [число]", "Очистить сообщения (1-100)"),
        ("help", "Показать это сообщение")
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=f"!{cmd}", value=desc, inline=False)
    
    await ctx.send(embed=embed)

if __name__ == "__main__":
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print('❌ ОШИБКА: Неверный токен!')
    except Exception as e:
        print(f'❌ ОШИБКА: {e}')
