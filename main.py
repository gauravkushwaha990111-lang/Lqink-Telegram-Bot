# /home/gauravwhy/Lqink_bot/main.py (Final Code with Security & Bypass Fix for Railway)
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

# --- SECURE BOT TOKEN LOADING ---
# ⚠️ FIX: BOT_TOKEN को Environment Variable से लोड करना
BOT_TOKEN: Final = os.environ.get("BOT_TOKEN") 
if not BOT_TOKEN:
    # App yahan crash ho jayega agar Railway/Variables mein token set nahi hai
    logger.error("❌ FATAL: BOT_TOKEN environment variable not set!")
    sys.exit(1)
    
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

# --- CORE HANDLER FUNCTIONS (Scraper bypassed) ---

def handle_update(update_data):
    """Processes a single Telegram Update dictionary (Raw JSON)."""
    message_data = update_data.get('message', {})
    text = message_data.get('text', '').strip()
    chat_id = message_data.get('chat', {}).get('id')
    
    if not chat_id or not text:
        return

    try:
        if text == "/start":
            run_sync(BOT.send_message(chat_id, "Hello! I am Lqink Bot. Please send me the URL."))
            return

        if not URL_REGEX.fullmatch(text):
            run_sync(BOT.send_message(chat_id, "Please send a valid and complete URL (starting with http/https)."))
            return

        user_url = text
        
        # ⚠️ SCRAPING LOGIC BYPASSED
        success_message = f"✅ URL received: **{user_url}**\n\n_Scraping logic is currently bypassed due to network restrictions. This confirms your bot is running stable._"
        run_sync(BOT.send_message(chat_id, success_message, parse_mode='Markdown'))
        
    except Exception as e:
        logger.error(f"Main handling error: {e}")
        error_text = f"❌ An unexpected error occurred: {e}"
        run_sync(BOT.send_message(chat_id, error_text))

# --- FLASK APPLICATION SETUP ---

def create_app():
    """Creates the Flask app and webhook route."""
    app = Flask(__name__)

    @app.route('/telegram', methods=['POST'])
    def webhook():
        if request.method == "POST":
            update_data = request.get_json()
            handle_update(update_data)

        return jsonify({'status': 'ok'}), 200 

    return app
