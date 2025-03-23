import discord
import os
import requests
import re
import logging
import sys
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from io import BytesIO
from anthropic import Anthropic

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('discord_bot')

# Переменные окружения
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

logger.info(f"Токен Discord: {'Настроен' if TOKEN else 'ОТСУТСТВУЕТ'}")
logger.info(f"API ключ Anthropic: {'Настроен' if ANTHROPIC_API_KEY else 'ОТСУТСТВУЕТ'}")

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

try:
    anthropic = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
    logger.info("Anthropic клиент инициализирован успешно")
except Exception as e:
    logger.error(f"Ошибка инициализации Anthropic: {e}")
    anthropic = None

def extract_content(url):
    try:
        logger.info(f"Извлечение контента из: {url}")
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        
        title = soup.find("meta", property="og:title")
        if not title:
            title = soup.find("title")
            
        image = soup.find("meta", property="og:image")
        
        article_text = ""
        article = soup.find('article') or soup.find(class_=re.compile('article|content|post|story'))
        
        if article:
            paragraphs = article.find_all('p')
            article_text = ' '.join([p.text for p in paragraphs])
        else:
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.text for p in paragraphs])
        
        title_text = title["content"] if title and hasattr(title, "content") else (title.text if title else "Без заголовка")
        logger.info(f"Извлечено: заголовок '{title_text[:30]}...', текст {len(article_text)} символов, изображение: {'найдено' if image else 'не найдено'}")
        
        return {
            "title": title_text,
            "image_url": image["content"] if image else None,
            "text": article_text,
        }
    except Exception as e:
        logger.error(f"Ошибка при извлечении контента: {e}")
        return {
            "title": "Ошибка парсинга", 
            "image_url": None,
            "text": "",
        }

def translate_accurately(text):
    if not text or not anthropic:
        return text
    
    try:
        logger.info(f"Перевод текста длиной {len(text)} символов")
        text_to_process = text[:1500] if len(text) > 1500 else text
        
        prompt = f"Переведи с английского на русский максимально точно и ясно (не более 1500 символов):\n\n{text_to_process}"
        response = anthropic.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=600,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
            timeout=25
        )
        result = response.content[0].text.strip()
        if len(result) > 1950:
            result = result[:1900] + "..."
        logger.info(f"Перевод успешен, получено {len(result)} символов")
        return result
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}")
        fashion_terms = {
            "release": "релиз", 
            "collection": "коллекция",
            "fashion": "мода",
            "style": "стиль",
            "collaboration": "коллаборация"
        }
        for eng, rus in fashion_terms.items():
            text = text.replace(eng, rus)
        return text[:1950] if len(text) > 1950 else text

def is_english(text):
    if not text:
        return False
    english_words = ['the', 'and', 'is', 'in', 'it', 'to', 'of', 'for', 'with', 'on']
    text_lower = text.lower()
    english_count = sum(1 for word in english_words if f" {word} " in text_lower)
    result = english_count >= 3
    logger.info(f"Определение языка: {'английский' if result else 'русский'}")
    return result

def story_rewrite(text):
    if not text or not anthropic:
        return text
    
    try:
        logger.info(f"Стилизация текста длиной {len(text)} символов")
        text_to_process = text[:800] if len(text) > 800 else text
        
        prompt = f"""Ты — молодая, острая, дерзкая редакторка Telegram-канала "ОСКОЛКИ ГЛЯНЦА".
Тебе 21, у тебя язвительный взгляд на модную индустрию и глянец.

Перепиши следующий текст как личный, эмоциональный пост от первого лица, будто делишься с друзьями:
1. Начни с обращения "Ребят" или другого молодежного обращения
2. Используй междометия, восклицания, эмоциональные реакции
3. Добавь личный, почти дневниковый стиль с элементами разговорной речи
4. Включи острые наблюдения о классовых противоречиях в моде
5. Добавь метафоры, связанные с болью, рассечением, холодом
6. Передай чувство одиночества наблюдателя за абсурдностью модной индустрии
7. Используй короткие, рубленые предложения для создания напряжения
8. ВАЖНО: Текст должен быть НЕ ДЛИННЕЕ 140 СЛОВ
9. Обязательно покажи иронию и противоречивость модных трендов

Вот оригинал:
{text_to_process}"""

        response = anthropic.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=350,
            temperature=1.0,
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        
        rewritten_text = response.content[0].text.strip()
        
        if "#ОсколкиГлянца" not in rewritten_text:
            rewritten_text += "\n\n#ОсколкиГлянца"
        
        # Проверяем количество слов
        words = rewritten_text.split()
        if len(words) > 140:
            rewritten_text = ' '.join(words[:140])
            if "#ОсколкиГлянца" not in rewritten_text:
                rewritten_text += "\n\n#ОсколкиГлянца"
        
        logger.info(f"Стилизация успешна, получено {len(rewritten_text.split())} слов")
        return rewritten_text
    except Exception as e:
        logger.error(f"Ошибка стилизации: {e}")
        fallback = f"Ребят, вы видели это? {text[:100]}... \n\nМода как всегда режет по живому. #ОсколкиГлянца"
        return fallback

def generate_filler_post():
    if not anthropic:
        return "Ошибка: API ключ не настроен"
    
    try:
        topics = [
            "fashion", "style", "cinema", "psychology", "music", "art", 
            "feelings", "city", "nostalgia"
        ]
        import random
        topic = random.choice(topics)
        
        logger.info(f"Генерация живого поста на тему: {topic}")
        prompt = f"Сгенерируй короткий (НЕ БОЛЕЕ 100 СЛОВ) авторский пост в стиле редактора глянцевого Telegram-канала. Тема — {topic}. Пост должен быть живым, умным, личным и атмосферным. Это может быть наблюдение, микроистория, размышление или культурная отсылка. Без ссылок. Без медиа. Только текст."
        
        response = anthropic.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=300,
            temperature=0.9,
            messages=[{"role": "user", "content": prompt}],
            timeout=30
        )
        
        raw_text = response.content[0].text.strip()
        return story_rewrite(raw_text)
    except Exception as e:
        logger.error(f"Ошибка генерации живого поста: {e}")
        return f"Ошибка генерации: {str(e)}"

@client.event
async def on_ready():
    logger.info(f"✅ Бот запущен как {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    try:
        if message.content.startswith("http"):
            logger.info(f"Получена ссылка: {message.content}")
            processing_msg = await message.channel.send("🔍 Обрабатываю ссылку...")

            try:
                data = extract_content(message.content)
                title = data["title"]
                image_url = data["image_url"]
                text = data["text"]
                
                # Перевод если нужно (с таймаутом)
                if is_english(text):
                    translate_msg = await message.channel.send("🌐 Текст на английском, выполняю перевод...")
                    try:
                        text = translate_accurately(text)
                        title = translate_accurately(title)
                        await translate_msg.delete()
                    except Exception as e:
                        logger.error(f"Ошибка в процессе перевода: {e}")
                        await translate_msg.edit(content="⚠️ Проблема с переводом, продолжаю со смешанным текстом")
                
                # Стилизация через Claude (с таймаутом и резервным вариантом)
                style_msg = await message.channel.send("✏️ Стилизую текст...")
                try:
                    glossy_text = story_rewrite(text)
                except Exception as e:
                    logger.error(f"Ошибка в процессе стилизации: {e}")
                    # Резервный вариант стилизации
                    glossy_text = f"Ребят, это просто невероятно! {title}\n\nГлянец снова делает нас заложниками своих фантазий. Больно смотреть, как мы покупаемся на эти игры.\n\n#ОсколкиГлянца"
                finally:
                    await style_msg.delete()

                if image_url:
                    try:
                        img_data = requests.get(image_url, timeout=5).content
                        file = discord.File(BytesIO(img_data), filename="image.jpg")
                        
                        # Проверяем длину сообщения
                        if len(glossy_text) > 1950:
                            # Делим на две части
                            first_part = glossy_text[:1900]
                            second_part = glossy_text[1900:]
                            
                            # Отправляем сначала текст, потом изображение с оставшимся текстом
                            await processing_msg.delete()
                            await message.channel.send(content=first_part)
                            
                            # Отправляем изображение с короткой второй частью или без текста
                            second_text = second_part if len(second_part) < 1950 else "#ОсколкиГлянца"
                            await message.channel.send(content=second_text, file=file)
                        else:
                            # Текст помещается в одно сообщение
                            await processing_msg.delete()
                            await message.channel.send(content=glossy_text, file=file)
                        return
                    except Exception as e:
                        logger.error(f"Ошибка загрузки изображения: {e}")
                        # Пробуем отправить без изображения
                        if len(glossy_text) > 1950:
                            parts = [glossy_text[i:i+1900] for i in range(0, len(glossy_text), 1900)]
                            await processing_msg.delete()
                            for part in parts:
                                await message.channel.send(part)
                        else:
                            await processing_msg.delete()
                            await message.channel.send(glossy_text)
                        return

                await processing_msg.delete()
                await message.channel.send(glossy_text)
            except Exception as e:
                logger.error(f"Общая ошибка обработки ссылки: {e}")
                await processing_msg.edit(content=f"⚠️ Не удалось обработать ссылку: {str(e)}")
        
        elif message.content.startswith("!стиль "):
            logger.info("Получена команда !стиль")
            text = message.content[7:]
            processing_msg = await message.channel.send("✏️ Стилизую текст...")
            try:
                glossy_text = story_rewrite(text)
                await processing_msg.delete()
                await message.channel.send(glossy_text)
            except Exception as e:
                logger.error(f"Ошибка стилизации текста: {e}")
                await processing_msg.edit(content=f"⚠️ Не удалось стилизовать текст: {str(e)}")
        
        elif message.content == "!живой":
            logger.info("Получена команда !живой")
            processing_msg = await message.channel.send("Генерирую живой пост...")
            try:
                filler_text = generate_filler_post()
                await processing_msg.delete()
                await message.channel.send(filler_text)
            except Exception as e:
                logger.error(f"Ошибка генерации живого поста: {e}")
                await processing_msg.edit(content=f"⚠️ Не удалось сгенерировать пост: {str(e)}")
        
        elif message.content == "!ping":
            # Диагностическая команда
            await message.channel.send("Pong! Бот работает.")
        
        else:
            await message.channel.send("📎 Кинь ссылку на статью, напиши '!стиль [текст]' для стилизации, или '!живой' для генерации живого поста.")
    
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        try:
            await message.channel.send(f"⚠️ Произошла ошибка: {str(e)}")
        except:
            pass

try:
    logger.info("Запуск бота...")
    client.run(TOKEN)
except Exception as e:
    logger.critical(f"Критическая ошибка при запуске бота: {e}")
