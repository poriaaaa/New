import asyncio
import feedparser
import datetime
import os
from telegram import Bot
from telegram.error import TelegramError
from newspaper import Article
from telethon import TelegramClient, events
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH")
PHONE = os.getenv("PHONE")
CHANNELS = os.getenv("CHANNELS", "").split(",")

RSS_FEEDS = [
    "https://www.iranintl.com/feed",
    "https://www.bbc.com/persian/index.xml",
    "https://www.irna.ir/rss",
]

bot = Bot(token=BOT_TOKEN)

def summarize_article(url):
    try:
        article = Article(url, language="fa")
        article.download()
        article.parse()
        article.nlp()
        return article.summary[:500] if article.summary else "خلاصه در دسترس نیست"
    except Exception:
        return "خلاصه در دسترس نیست"

async def send_message_safe(text):
    try:
        if len(text) > 4000:
            text = text[:3950] + "\n\n... [متن کوتاه شده]"
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode="HTML")
    except TelegramError as e:
        logger.error(f"خطا در ارسال پیام: {e}")

def get_latest_news():
    news_items = []
    now = datetime.datetime.utcnow()
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            published_time = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_time = datetime.datetime(*entry.published_parsed[:6])
            if not published_time or (now - published_time).total_seconds() <= 300:
                title = getattr(entry, "title", "بدون عنوان")
                summary = summarize_article(entry.link)
                source = getattr(feed.feed, "title", "منبع نامشخص")
                news_items.append((title, entry.link, source, summary))
    return news_items

async def rss_loop():
    while True:
        news = get_latest_news()
        for title, link, source, summary in news:
            msg = f'''📰 <b>{title}</b>

🌐 <b>منبع:</b> {source}
📌 <b>خلاصه:</b> {summary}

🔗 <a href="{link}">مطالعه کامل</a>'''
            await send_message_safe(msg)
            await asyncio.sleep(2)
        await asyncio.sleep(300)

client = TelegramClient("userbot", API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNELS))
async def handler(event):
    text = event.raw_text
    if not text or len(text.strip()) < 10:
        return
    username = event.chat.username
    link = f"https://t.me/{username}/{event.id}" if username else f"پیام از {event.chat.title}"
    msg = f'''📢 <b>خبر جدید از {event.chat.title}</b>

{text}

🔗 {link}'''
    await send_message_safe(msg)

async def main():
    await client.start(PHONE)
    await send_message_safe("🤖 ربات خبری شروع به کار کرد!")
    await asyncio.gather(rss_loop(), client.run_until_disconnected())

if __name__ == "__main__":
    asyncio.run(main())
