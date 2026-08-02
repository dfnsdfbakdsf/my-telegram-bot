import discord

# ТОКЕН КОТОРЫЙ РАБОТАЕТ (из вашей проверки)
TOKEN = 'MTUzMzQ0Mzc3NzY5ODcyOTk5NQ.GjTrJ-.XK5zgrlqpdU-M8k_CgJ3Bmg3W2jhV8w8FSK_HA'

print('🚀 ЗАПУСК БОТА...')

# Включаем все разрешения
intents = discord.Intents.all()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print('='*60)
    print('✅ БОТ УСПЕШНО ПОДКЛЮЧИЛСЯ!')
    print(f'📌 Имя: {client.user.name}')
    print(f'🆔 ID: {client.user.id}')
    print(f'📊 На серверах: {len(client.guilds)}')
    
    if len(client.guilds) == 0:
        print('⚠️ БОТ НЕ ДОБАВЛЕН НА СЕРВЕР!')
        print(f'🔗 Ссылка: https://discord.com/oauth2/authorize?client_id={client.user.id}&permissions=8&scope=bot')
    else:
        for guild in client.guilds:
            print(f'  📁 {guild.name}')
            # Отправляем приветствие
            for channel in guild.text_channels:
                try:
                    await channel.send('✅ БОТ ЗАПУЩЕН! Напишите !hello')
                    print(f'  ✅ Сообщение отправлено в #{channel.name}')
                    break
                except Exception as e:
                    print(f'  ❌ Ошибка: {e}')
    
    print('='*60)

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    print(f'📨 {message.author.name}: {message.content}')
    
    if message.content == '!hello':
        await message.channel.send(f'Привет, {message.author.mention}! 👋')
        print('✅ Ответ отправлен!')
    elif message.content == '!ping':
        await message.channel.send('🏓 Понг!')
        print('✅ Ответ отправлен!')
    elif message.content == '!test':
        await message.channel.send('✅ Бот работает!')
        print('✅ Ответ отправлен!')

try:
    client.run(TOKEN)
except discord.LoginFailure:
    print('❌ ОШИБКА: Неверный токен!')
except Exception as e:
    print(f'❌ ОШИБКА: {e}')
