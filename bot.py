import requests
from bs4 import BeautifulSoup
import telebot
import time
import asyncio
from datetime import datetime
import logging

# --------------------------
# توکن ربات تلگرام و چت‌آی‌دی رو اینجا وارد کن:
TELEGRAM_BOT_TOKEN = "8306283242:AAFXKM2507eI5pUd0Y3TyAVOow1SMj6LC8E"   # توکن ربات از BotFather
CHAT_ID = "1456594312"  # آی‌دی عددی خودت یا گروه
# --------------------------

# لیست سایت‌های خبری
NEWS_SOURCES = [
    "https://www.iranintl.com/",
    "https://www.bbc.com/persian",
    "https://www.haaretz.com/",
    "https://13tv.co.il/",
    "https://m.n12.co.il/",
    "https://www.irna.ir/",
    "https://farsnews.ir/showcase"
]

# ربات تلگرام
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ذخیره آخرین خبرهای ارسال‌شده
last_sent = {}

def get_news(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        titles = [t.get_text().strip() for t in soup.find_all("h2")][:5]
        return titles
    except Exception as e:
        print(f"❌ خطا در خواندن {url}: {e}")
        return []

async def send_message_safe(text):
    """ارسال پیام با مدیریت خطا"""
    try:
        # محدود کردن طول پیام (تلگرام حداکثر 4096 کاراکتر)
        if len(text) > 4000:
            text = text[:3950] + "\n\n... [متن کوتاه شده]"
        await bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='HTML')
        print("✅ پیام ارسال شد")
    except Exception as e:
        print(f"❌ خطا در ارسال پیام: {e}")

async def send_news():
    """دریافت و ارسال اخبار"""
    global last_sent
    for site in NEWS_SOURCES:
        titles = get_news(site)
        for title in titles:
            if title not in last_sent.get(site, []):
                msg = f"📢 خبر جدید از {site}:\n\n{title}"
                await send_message_safe(msg)
                last_sent.setdefault(site, []).append(title)

async def main_loop():
    """حلقه اصلی اجرا هر 5 دقیقه"""
    while True:
        await send_news()
        print("✅ چک شد:", datetime.now())
        await asyncio.sleep(300)  # هر ۵ دقیقه

if __name__ == "__main__":
    asyncio.run(main_loop())
        print(f"❌ خطا در خواندن {url}: {e}")
        return []

def send_news():
    global last_sent
    for site in NEWS_SOURCES:
        titles = get_news(site)
        for title in titles:
            if title not in last_sent.get(site, []):
                bot.send_message(CHAT_ID, f"📢 خبر جدید از {site}:\n\n{title}")
                last_sent.setdefault(site, []).append(title)

# اجرای همیشگی
def main_loop():
    while True:
        send_news()
        print("✅ چک شد:", datetime.now())
        time.sleep(300)  # هر ۵ دقیقه

if __name__ == "__main__":
    main_loop()
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
