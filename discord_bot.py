
import discord
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

def extract_og_data(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("meta", property="og:title")
        image = soup.find("meta", property="og:image")
        return {
            "title": title["content"] if title else "Без заголовка",
            "image_url": image["content"] if image else None
        }
    except Exception as e:
        return {"title": "Ошибка парсинга", "image_url": None}

@client.event
async def on_ready():
    print(f"✅ Бот запущен как {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("http"):
        await message.channel.send("🔍 Обрабатываю ссылку...")

        data = extract_og_data(message.content)
        title = data["title"]
        image_url = data["image_url"]

        glossy_text = f"{title}\n\nЭто могла бы быть история. Это мог бы быть стиль."

        if image_url:
            try:
                img_data = requests.get(image_url).content
                file = discord.File(BytesIO(img_data), filename="image.jpg")
                await message.channel.send(content=glossy_text, file=file)
                return
            except Exception as e:
                await message.channel.send(f"{glossy_text}\n(Не удалось прикрепить изображение)")
                return

        await message.channel.send(glossy_text)
    else:
        await message.channel.send("📎 Кинь ссылку на статью, и я сделаю тебе пост.")

client.run(TOKEN)
