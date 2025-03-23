
import discord
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"✅ Бот запущен как {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    await message.channel.send("Окей, принял!")

client.run(TOKEN)
