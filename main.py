 # /home/gauravwhy/Lqink_bot/main.py (FINAL LOGIC MIGRATED TO FLASK WEBHOOK)
import logging
import re
import os
import sys
import asyncio 
import tempfile
from telegram import Bot, InputMediaPhoto, InputMediaVideo
from telegram import error as tg_error
from flask import Flask, request, jsonify 
from typing import Final

# scraper.py से फंक्शन इम्पोर्ट करना
try:
    from scraper import run_scraper, clean_up_files
except ImportError:
    # Deployment fail ho jayega agar scraper.py missing hai
    sys.exit(1)

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECURE TOKEN LOADING ---
BOT_TOKEN: Final = os.environ.get("BOT_TOKEN") 
if not BOT_TOKEN:
    logger.error("❌ FATAL: BOT_TOKEN environment variable not set!")
    sys.exit(1)
    
BOT = Bot(token=BOT_TOKEN)
# ---------------------

# URL Regex (yahi rahega)
URL_REGEX = re.compile(
    r'^(?:http|ftp)s?://' 
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' 
    r'localhost|' 
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' 
    r'(?::\d+)?' 
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)

# --- ASYNC HELPER (MUST be used for all BOT calls) ---
def run_sync(coroutine):
    """Safely runs an async coroutine synchronously for Webhook."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coroutine)
# ----------------------------------------------------

# --- MAIN LOGIC MIGRATED FROM handle_url ---

def handle_update(update_data):
    """Processes a single Telegram Update dictionary (Raw JSON)."""
    # Raw JSON data ko parse karna
    message_data = update_data.get('message', {})
    text = message_data.get('text', '').strip()
    chat_id = message_data.get('chat', {}).get('id')
    
    if not chat_id or not text:
        return

    user_url = text.strip()
    local_files_to_clean = []
    
    # 1. Start Command Handling
    if user_url == "/start":
        run_sync(BOT.send_message(chat_id, "Hello! Send me the URL from which you want to extract links, images, and videos."))
        return

    # 2. URL Validation
    if not URL_REGEX.fullmatch(user_url):
        run_sync(BOT.send_message(chat_id, "Please send a valid and complete URL (starting with http/https)."))
        return
        
    status_msg = run_sync(BOT.send_message(chat_id, f"URL received: **{user_url}**\n\nStarting scraping and media download. This may take a moment...", parse_mode='Markdown'))

    try:
        # A) Run Scraper (Synchronous)
        results = run_scraper(user_url)
        
        if results['status'] == 'error':
            run_sync(BOT.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                           text=f"❌ Scraping failed: {results['message']}"))
            return

        # B) Media Album Sending
        media_paths = results['media_paths']
        
        try:
            if media_paths:
                media_group = []
                open_files = [] 
                
                for item_path in media_paths:
                    if isinstance(item_path, str) and (os.path.exists(item_path)):
                        # Local file (Image/Video)
                        file_handle = open(item_path, 'rb')
                        open_files.append(file_handle)
                        
                        # Your original file extension check
                        if item_path.endswith(('.jpg', '.png')):
                            media_group.append(InputMediaPhoto(media=file_handle))
                        elif item_path.endswith(('.mp4', '.mov')):
                            media_group.append(InputMediaVideo(media=file_handle))
                            
                        local_files_to_clean.append(item_path) 
                        
                    elif isinstance(item_path, str) and ('youtube.com' in item_path or 'vimeo.com' in item_path):
                        # Video Link (Send separately)
                        run_sync(BOT.send_message(chat_id, f"🎥 Video Link: {item_path}", disable_web_page_preview=False))
                        
                if media_group:
                    try:
                        # send_media_group is an async operation
                        run_sync(BOT.send_media_group(chat_id=chat_id, media=media_group))
                        logger.info("Media group successfully sent.")
                    finally:
                        for fh in open_files:
                            fh.close()
                            
        except Exception as media_e:
            logger.error(f"Media sending failed but continuing with links: {media_e}")
            run_sync(BOT.send_message(chat_id, "⚠️ Media (Images/Videos) sending failed, but continuing with links."))


        # C) Download Links Sending (This creates the desired card previews)
        download_links = results['download_links']
        
        if download_links:
            run_sync(BOT.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                           text="✅ Links successfully extracted! Sending download links now:"))
            
            for category, links in download_links.items():
                # 1. Category Heading Sending (e.g., DOWNLOAD FOR WINDOWS)
                run_sync(BOT.send_message(chat_id, f"**{category}**", parse_mode='Markdown'))
                
                # 2. Sending each Link in /addlink format (for card preview)
                for i, link_url in enumerate(links):
                    # Link text for card preview (Your original /addlink format)
                    link_message = f"{i+1}. /addlink {link_url}" 
                    run_sync(BOT.send_message(chat_id, link_message, disable_web_page_preview=False)) # Card Preview ON!
        else:
             run_sync(BOT.edit_message_text(chat_id=chat_id, message_id=status_msg.message_id,
                                            text="⚠️ Scraping complete, but no download links were found."))

        # D) User Count (Optional: Display Stats)
        if results['user_count'] and results['user_count'] != 'N/A':
            run_sync(BOT.send_message(chat_id, f"🌐 Website Stats: {results['user_count']}"))
            
    except Exception as e:
        logger.error(f"Main handling error: {e}")
        error_text = f"❌ An unexpected error occurred: {e}"
        run_sync(BOT.send_message(chat_id, error_text))
        
    finally:
        # E) Clean up temporary files
        if local_files_to_clean:
            clean_up_files(local_files_to_clean)
            logger.info("Temporary files successfully cleaned up.")


# --- FLASK APPLICATION SETUP ---

def create_app():
    """Initializes the Flask app for Gunicorn/Webhook."""
    app = Flask(__name__)

    @app.route('/telegram', methods=['POST'])
    def webhook():
        if request.method == "POST":
            update_data = request.get_json()
            handle_update(update_data) # Call the core logic

        # Always return 200 OK instantly to Telegram
        return jsonify({'status': 'ok'}), 200 

    return app
