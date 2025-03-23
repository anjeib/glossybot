import discord
import os
import requests
import random
import re
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from googletrans import Translator

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
translator = Translator()

def extract_content(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Извлечение OG-данных
        title = soup.find("meta", property="og:title")
        image = soup.find("meta", property="og:image")
        
        # Извлечение основного текста
        article_text = ""
        
        # Попытка найти основной контент
        article = soup.find('article') or soup.find(class_=re.compile('article|content|post|story'))
        
        if article:
            paragraphs = article.find_all('p')
            article_text = ' '.join([p.text for p in paragraphs])
        else:
            # Запасной вариант - берем все параграфы
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.text for p in paragraphs])
        
        # Определение языка текста
        lang = 'en' if is_english(article_text) else 'ru'
            
        return {
            "title": title["content"] if title else "Без заголовка",
            "image_url": image["content"] if image else None,
            "text": article_text,
            "lang": lang
        }
    except Exception as e:
        print(f"Ошибка при извлечении контента: {e}")
        return {
            "title": "Ошибка парсинга", 
            "image_url": None,
            "text": "",
            "lang": "ru"
        }

def is_english(text):
    # Простая проверка на английский язык
    english_words = ['the', 'and', 'is', 'in', 'it', 'to', 'of', 'for', 'with', 'on']
    text_lower = text.lower()
    english_count = sum(1 for word in english_words if f" {word} " in text_lower)
    return english_count >= 3

def translate_text(text, from_lang='en', to_lang='ru'):
    try:
        translated = translator.translate(text, src=from_lang, dest=to_lang)
        return translated.text
    except Exception as e:
        print(f"Ошибка перевода: {e}")
        return text

def rewrite_in_glossy_style(text, title, max_words=140):
    # Обрабатываем текст
    text_to_process = text[:2000]  # Ограничиваем размер текста
    
    # Разделение текста на предложения
    sentences = split_into_sentences(text_to_process)
    
    # Эмоциональные фразы в стиле канала
    glossy_intros = [
        "Вы не поверите, но...",
        "Серьезно?",
        "Боже, как это больно видеть.",
        "Трясущимися руками листаю ленту.",
        "Мода снова обнажает наши раны.",
        "Ирония жизни режет по живому.",
        "В этом есть что-то надломленное и прекрасное.",
        "Стиль как диагноз эпохи.",
        "За идеальной картинкой — всегда трещина."
    ]
    
    # Эмоциональные фразы для заключения
    glossy_outros = [
        "#ОсколкиГлянца",
        "Мода — это диагноз. Наш диагноз.",
        "В каждом тренде — наша боль.",
        "Стиль говорит громче слов.",
        "Глянец разбивается о реальность.",
        "Мода отражает наше одиночество.",
        "За каждым образом — история потери."
    ]
    
    # Создаем новый текст
    if not sentences:
        content = f"{random.choice(glossy_intros)} {title}. {random.choice(glossy_outros)}"
    else:
        # Берем несколько предложений из оригинала и добавляем эмоциональный контекст
        selected_sentences = sentences[:min(3, len(sentences))]
        content_text = ' '.join(selected_sentences)
        
        # Формируем пост
        content = f"{random.choice(glossy_intros)} {content_text}\n\n{random.choice(glossy_outros)}"
    
    # Ограничиваем количество слов
    words = content.split()
    if len(words) > max_words:
        content = ' '.join(words[:max_words])
    
    return content

def split_into_sentences(text):
    # Простая функция разделения текста на предложения
    text = text.replace('!', '.').replace('?', '.')
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    return sentences

@client.event
async def on_ready():
    print(f"✅ Бот запущен как {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith("http"):
        processing_msg = await message.channel.send("🔍 Обрабатываю ссылку...")

        data = extract_content(message.content)
        title = data["title"]
        image_url = data["image_url"]
        text = data["text"]
        lang = data["lang"]
        
        # Перевод текста если он на английском
        if lang == 'en':
            await message.channel.send("🌐 Текст на английском, выполняю перевод...")
            text = translate_text(text, from_lang='en', to_lang='ru')
            title = translate_text(title, from_lang='en', to_lang='ru')
        
        # Переписываем текст в стиле канала
        glossy_text = rewrite_in_glossy_style(text, title)

        if image_url:
            try:
                img_data = requests.get(image_url).content
                file = discord.File(BytesIO(img_data), filename="image.jpg")
                await processing_msg.delete()
                await message.channel.send(content=glossy_text, file=file)
                return
            except Exception as e:
                await processing_msg.delete()
                await message.channel.send(f"{glossy_text}\n(Не удалось прикрепить изображение)")
                return

        await processing_msg.delete()
        await message.channel.send(glossy_text)
    elif message.content.startswith("!стиль "):
        # Прямая стилизация текста без парсинга ссылки
        text = message.content[7:]  # Убираем "!стиль " из начала
        glossy_text = rewrite_in_glossy_style(text, "")
        await message.channel.send(glossy_text)
    else:
        await message.channel.send("📎 Кинь ссылку на статью или напиши '!стиль [текст]', и я сделаю пост в стиле \"Осколки глянца\".")

client.run(TOKEN)
