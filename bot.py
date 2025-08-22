import requests
from bs4 import BeautifulSoup
import asyncio
from telegram import Bot
from telegram.error import TelegramError
import json
import os
from datetime import datetime
import logging

# تنظیم لاگ
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --------------------------
# تنظیمات - این مقادیر را تغییر دهید
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # توکن از BotFather
CHAT_ID = "YOUR_CHAT_ID_HERE"               # آی‌دی عددی خودت
# --------------------------

# لیست سایت‌های خبری با تنظیمات مخصوص
NEWS_SOURCES = {
    "ایران اینترنشنال": {
        "url": "https://www.iranintl.com/",
        "selectors": ["h1", "h2", ".title", ".headline"]
    },
    "بی‌بی‌سی فارسی": {
        "url": "https://www.bbc.com/persian",
        "selectors": ["h1", "h2", ".media__title", ".title-link__title-text"]
    },
    "هاآرتص": {
        "url": "https://www.haaretz.com/",
        "selectors": ["h1", "h2", ".headline", ".title"]
    },
    "کانال 13": {
        "url": "https://13tv.co.il/",
        "selectors": ["h1", "h2", ".title"]
    },
    "n12": {
        "url": "https://m.n12.co.il/",
        "selectors": ["h1", "h2", ".article-title"]
    },
    "ایرنا": {
        "url": "https://www.irna.ir/",
        "selectors": ["h1", "h2", ".title", ".news-title"]
    },
    "فارس نیوز": {
        "url": "https://farsnews.ir/showcase",
        "selectors": ["h1", "h2", ".title", ".news-title"]
    }
}

# فایل ذخیره خبرهای ارسال‌شده
SENT_NEWS_FILE = "sent_news.json"

# headers برای درخواست‌ها
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fa,en-US;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

def load_sent_news():
    """بارگذاری خبرهای ارسال‌شده از فایل"""
    if os.path.exists(SENT_NEWS_FILE):
        try:
            with open(SENT_NEWS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"خطا در بارگذاری فایل sent_news: {e}")
    return {}

def save_sent_news(sent_news):
    """ذخیره خبرهای ارسال‌شده در فایل"""
    try:
        with open(SENT_NEWS_FILE, 'w', encoding='utf-8') as f:
            json.dump(sent_news, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"خطا در ذخیره فایل sent_news: {e}")

# بارگذاری خبرهای قبلی
sent_news = load_sent_news()

# ربات تلگرام
bot = Bot(token=TELEGRAM_BOT_TOKEN)

def get_news_from_site(site_name, site_config):
    """استخراج اخبار از یک سایت"""
    try:
        logger.info(f"در حال بررسی {site_name}...")
        
        response = requests.get(
            site_config["url"], 
            headers=HEADERS, 
            timeout=15
        )
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        titles = []
        
        # جستجو با selector های مختلف
        for selector in site_config["selectors"]:
            elements = soup.select(selector)
            for element in elements:
                title = element.get_text().strip()
                
                # فیلتر کردن عناوین معقول
                if (50 <= len(title) <= 200 and 
                    title not in titles and
                    not title.lower().startswith(('تبلیغات', 'اعلان', 'advertisement'))):
                    titles.append(title)
                    
                # حداکثر 3 خبر از هر سایت
                if len(titles) >= 3:
                    break
            
            if len(titles) >= 3:
                break
        
        logger.info(f"از {site_name} تعداد {len(titles)} خبر پیدا شد")
        return titles
        
    except requests.RequestException as e:
        logger.error(f"خطای درخواست برای {site_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"خطای عمومی برای {site_name}: {e}")
        return []

async def send_message_safe(text):
    """ارسال پیام با مدیریت خطا"""
    try:
        # محدود کردن طول پیام
        if len(text) > 4000:
            text = text[:3950] + "\n\n... [متن کوتاه شده]"
            
        await bot.send_message(
            chat_id=CHAT_ID, 
            text=text, 
            parse_mode='HTML',
            disable_web_page_preview=True
        )
        logger.info("پیام ارسال شد")
        return True
        
    except TelegramError as e:
        logger.error(f"خطای تلگرام: {e}")
        return False
    except Exception as e:
        logger.error(f"خطای ارسال پیام: {e}")
        return False

async def check_and_send_news():
    """بررسی و ارسال اخبار جدید"""
    global sent_news
    new_news_count = 0
    
    for site_name, site_config in NEWS_SOURCES.items():
        try:
            titles = get_news_from_site(site_name, site_config)
            
            # بررسی خبرهای جدید
            for title in titles:
                if title not in sent_news.get(site_name, []):
                    # پیام خبر
                    message = f"""📰 <b>خبر جدید</b>

🌐 <b>منبع:</b> {site_name}
📄 <b>عنوان:</b> {title}

⏰ <b>زمان:</b> {datetime.now().strftime('%Y/%m/%d - %H:%M')}

🔗 <b>سایت:</b> {site_config['url']}"""

                    if await send_message_safe(message):
                        # ثبت خبر ارسال شده
                        if site_name not in sent_news:
                            sent_news[site_name] = []
                        sent_news[site_name].append(title)
                        new_news_count += 1
                        
                        # فاصله بین پیام‌ها
                        await asyncio.sleep(3)
            
            # محدود کردن تعداد خبرهای ذخیره شده (حداکثر 50 خبر از هر سایت)
            if site_name in sent_news and len(sent_news[site_name]) > 50:
                sent_news[site_name] = sent_news[site_name][-30:]
                
        except Exception as e:
            logger.error(f"خطا در پردازش {site_name}: {e}")
    
    # ذخیره خبرهای ارسال شده
    if new_news_count > 0:
        save_sent_news(sent_news)
        logger.info(f"تعداد {new_news_count} خبر جدید ارسال شد")
    else:
        logger.info("خبر جدیدی پیدا نشد")

async def test_bot():
    """تست اتصال ربات"""
    try:
        bot_info = await bot.get_me()
        logger.info(f"ربات متصل شد: @{bot_info.username}")
        
        await send_message_safe("🤖 ربات خبری شروع به کار کرد!")
        return True
    except Exception as e:
        logger.error(f"خطا در تست ربات: {e}")
        return False

async def main_loop():
    """حلقه اصلی اجرا"""
    logger.info("🚀 شروع ربات خبری...")
    
    # تست اتصال
    if not await test_bot():
        logger.error("❌ اتصال ربات ناموفق - لطفاً توکن و chat_id را بررسی کنید")
        return
    
    # حلقه اصلی
    while True:
        try:
            logger.info(f"⏰ شروع چک اخبار: {datetime.now().strftime('%Y/%m/%d - %H:%M:%S')}")
            await check_and_send_news()
            
            logger.info("😴 استراحت 5 دقیقه‌ای...")
            await asyncio.sleep(300)  # 5 دقیقه
            
        except KeyboardInterrupt:
            logger.info("🛑 ربات توسط کاربر متوقف شد")
            break
        except Exception as e:
            logger.error(f"❌ خطای کلی: {e}")
            await asyncio.sleep(60)  # در صورت خطا، یک دقیقه صبر کن

if __name__ == "__main__":
    # بررسی تنظیمات
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE" or CHAT_ID == "YOUR_CHAT_ID_HERE":
        print("❌ لطفاً ابتدا TELEGRAM_BOT_TOKEN و CHAT_ID را در کد تنظیم کنید!")
        exit(1)
    
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n🛑 ربات متوقف شد")
    except Exception as e:
        print(f"❌ خطای اجرا: {e}")async def send_message_safe(text):
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
