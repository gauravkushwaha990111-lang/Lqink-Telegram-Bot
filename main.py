# /home/gauravwhy/Lqink_bot/main.py (Final Code with Security & ScraperAPI Integration)
import logging
import re
import os # Environment variables ke liye zaroori
import sys
import asyncio 
from telegram import Bot 
from typing import Final
from flask import Flask, request, jsonify 

# scraper.py से फंक्शन इम्पोर्ट करना 
try:
    from scraper import run_scraper, clean_up_files 
except ImportError:
    pass

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECURE TOKEN AND KEY LOADING ---
# 1. BOT TOKEN
BOT_TOKEN: Final = os.environ.get("BOT_TOKEN") 
if not BOT_TOKEN:
    logger.error("❌ FATAL: BOT_TOKEN environment variable not set!")
    sys.exit(1)

# 2. SCRAPER API KEY (इसे scraper.py में भी लोड किया जाता है, पर यहां सिर्फ चेक कर लेते हैं)
SCRAPER_API_KEY: Final = os.environ.get("SCRAPER_API_KEY") 
if not SCRAPER_API_KEY:
    logger.warning("⚠️ SCRAPER_API_KEY not found. Scraping will likely fail.")
    
BOT = Bot(token=BOT_TOKEN)
# ---------------------

# --- ASYNC HELPER (Required for PTB v22.5) ---
def run_sync(coroutine):
    """Safely runs an async coroutine synchronously."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    return loop.run_until_complete(coroutine)
# ---------------------

# URL Regex
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://' 
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' 
    r'localhost|' 
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
    r'(?::\d+)?' 
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

# --- CORE HANDLER FUNCTIONS ---

def handle_update(update_data):
    """Processes a single Telegram Update dictionary (Raw JSON)."""
    message_data = update_data.get('message', {})
    text = message_data.get('text', '').strip()
    chat_id = message_data.get('chat', {}).get('id')
    
    if not chat_id or not text:
        return

    try:
        # Handle /start command
        if text == "/start":
            run_sync(BOT.send_message(chat_id, "Hello! I am Lqink Bot. Please send me the URL."))
            return

        # Handle URL 
        if not URL_REGEX.fullmatch(text):
            run_sync(BOT.send_message(chat_id, "Please send a valid and complete URL (starting with http/https)."))
            return

        user_url = text
        
        run_sync(BOT.send_message(chat_id, f"🔍 Searching for content on: **{user_url}**...", parse_mode='Markdown'))

        # 1. Scraper को चलाएं (अब यह ScraperAPI का उपयोग करेगा)
        scrape_result = run_scraper(user_url)
        
        # 2. रिजल्ट के आधार पर जवाब दें
        if scrape_result['status'] == 'success':
            response_text = f"✅ Content found for: **{user_url}**\n\n"
            
            # Links जोड़ें
            if scrape_result.get('links'):
                response_text += "\n**🔗 Extracted Links:**\n"
                for text, href in scrape_result['links'].items():
                    # Only show first 5 links
                    response_text += f"- [{text[:50]}...]({href})\n" 
            
            # Fallback अगर कोई लिंक नहीं मिला
            if not scrape_result.get('links'):
                response_text += "ℹ️ No specific links found, but the page loaded successfully via API."

        else:
            # अगर scraping विफल होता है (API या नेटवर्क एरर)
            response_text = f"❌ Scraping Failed: {scrape_result.get('message', 'Unknown Error')}\n\n_Check SCRAPER_API_KEY or URL validity._"

        run_sync(BOT.send_message(chat_id, response_text, parse_mode='Markdown'))

    except Exception as e:
        logger.error(f"Main handling error: {e}")
        error_text = f"❌ An unexpected error occurred during processing: {e}"
        run_sync(BOT.send_message(chat_id, error_text))

# --- FLASK APPLICATION SETUP (Gunicorn Fix) ---

# ⚠️ यह फ़ंक्शन अनिवार्य है! wsgi.py इसे इम्पोर्ट करता है।
def create_app():  
    """Creates the Flask app and webhook route."""
    app = Flask(__name__)

    @app.route('/telegram', methods=['POST'])
    def webhook():
        if request.method == "POST":
            update_data = request.get_json()
            handle_update(update_data)

        # Telegram को तुरंत 200 OK जवाब देना चाहिए
        return jsonify({'status': 'ok'}), 200 

    return app
