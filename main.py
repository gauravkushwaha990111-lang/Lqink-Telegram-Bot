# /home/gauravwhy/Lqink_bot/main.py (FINAL CODE: Media Grouping Fix)
import logging
import re
import os
import sys
import asyncio 
import tempfile
from telegram import Bot, error, InputMediaPhoto, InputMediaVideo # <-- NEW IMPORTS ADDED
from typing import Final
from flask import Flask, request, jsonify 
import requests 
from urllib.parse import urlparse

# scraper.py से फंक्शन इम्पोर्ट करना
try:
    from scraper import run_scraper, clean_up_files 
except ImportError:
    logger.error("Scraper module not found!")
    def run_scraper(url): return {'status': 'error', 'message': 'Scraper not available'}
    def clean_up_files(file_list): pass

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECURE TOKEN AND KEY LOADING ---
BOT_TOKEN: Final = os.environ.get("BOT_TOKEN") 
if not BOT_TOKEN:
    logger.error("❌ FATAL: BOT_TOKEN environment variable not set!")
    sys.exit(1)
SCRAPER_API_KEY: Final = os.environ.get("SCRAPER_API_KEY") 
BOT = Bot(token=BOT_TOKEN)
# ---------------------

# --- ASYNC HELPER ---
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

# --- FORMATTING FUNCTIONS ---
def format_links(title, link_list):
    if not link_list: return ""
    text = f"\n**{title} ({len(link_list)} Found):**\n"
    for i, (link_text, href) in enumerate(link_list):
        if i >= 10: break
        display_text = link_text[:70].replace('\n', ' ')
        text += f"**{i+1}.** [{display_text}]({href})\n"
    return text

def format_media(title, media_list):
    if not media_list: return ""
    text = f"\n**{title} ({len(media_list)} Found):**\n"
    for i, src in enumerate(media_list):
        if i >= 5 and title != "🎥 VIDEO LINKS (Top 2)": break
        text += f"- [Media Link {i+1}]({src})\n"
    return text

# --- CORE FUNCTIONS: DOWNLOADER ---

async def handle_direct_file_download_and_send(chat_id, file_url):
    """Handles direct file download and Telegram upload (Max 20MB)."""
    
    MAX_FILE_SIZE_MB = 20 
    
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            await BOT.send_message(chat_id, f"🎬 Attempting direct download (Max {MAX_FILE_SIZE_MB}MB)...")

            # 1. फ़ाइल को डाउनलोड करें (Streaming)
            path = urlparse(file_url).path
            base_name = os.path.basename(path).split('?')[0] or 'downloaded_file'
            local_filename = os.path.join(temp_dir, base_name)

            # Streaming download with timeout and size check
            with requests.get(file_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                downloaded_size = 0
                
                with open(local_filename, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: 
                            f.write(chunk)
                            downloaded_size += len(chunk)
                            
                            if downloaded_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                                raise Exception(f"File exceeded {MAX_FILE_SIZE_MB}MB limit during download.")
                
            # 2. File ko Telegram par upload karein
            caption = f"✅ Direct Download: {os.path.basename(local_filename)}"
            
            if local_filename.lower().endswith(('.mp4', '.mov', '.avi')):
                with open(local_filename, 'rb') as file_to_upload:
                    await BOT.send_video(chat_id=chat_id, video=file_to_upload, caption=caption, supports_streaming=True)
            elif local_filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                 with open(local_filename, 'rb') as file_to_upload:
                    await BOT.send_photo(chat_id=chat_id, photo=file_to_upload, caption=caption)
            else:
                 with open(local_filename, 'rb') as file_to_upload:
                    await BOT.send_document(chat_id=chat_id, document=file_to_upload, caption=caption)
                    
            await BOT.send_message(chat_id, "✨ File uploaded successfully!")

        except Exception as e:
            logger.error(f"File Download/Upload Error: {e}")
            await BOT.send_message(chat_id, f"❌ File processing error: {e}. Possible Timeout or Link not direct.")


# --- CORE FUNCTIONS: SCRAPER (With Media Group Logic) ---

async def send_media_group(chat_id, images, videos):
    """Sends multiple images and videos as a Telegram Media Group/Album."""
    media = []
    
    # Photos ko InputMediaPhoto ke roop mein jodna (Max 10 items)
    for i, img_url in enumerate(images[:5]): # Sirf pehli 5 photos
        # Photos ko URL se bhejne ke liye InputMediaPhoto ka upyog karen
        media.append(InputMediaPhoto(media=img_url, caption=f"Image {i+1}"))

    # Videos ko InputMediaVideo ke roop mein jodna (Max 10 items)
    for i, vid_url in enumerate(videos[:2]): # Sirf pehle 2 videos
        if len(media) < 10:
             media.append(InputMediaVideo(media=vid_url, caption=f"Video {i+1}"))
        else:
             break

    if media:
        try:
            # Media group bhej dein
            await BOT.send_media_group(chat_id=chat_id, media=media)
            return True
        except Exception as e:
            logger.error(f"Error sending media group: {e}")
            await BOT.send_message(chat_id, f"❌ Media Group Error: Could not send photos/videos. Sending links instead.")
            return False
    return False


def handle_scrape_and_send(chat_id, user_url):
    """Handles scraping for links and media (used by /addlink)."""
    
    scrape_result = run_scraper(user_url)
    
    if scrape_result['status'] == 'success':
        extracted_data = scrape_result['data']
        response_text = f"✅ Extracted Data for: **{user_url}**\n\n"
        
        # Images aur Videos nikalna
        images = extracted_data.get('images', [])
        videos = extracted_data.get('videos', [])
        
        # 1. Media Group bhejen (Photos aur Videos)
        media_sent = run_sync(send_media_group(chat_id, images, videos))
        
        # 2. Download Links bhejen (Text ke roop mein)
        download_text = format_links("⬇️ DOWNLOAD LINKS", extracted_data.get('downloads', []))
        
        # Agar media group nahi bhej paye aur links available hain
        if not media_sent:
             # Agar media group fail ho gaya to images/videos ke links bhi text mein de dein
             image_text = format_media("🖼️ IMAGE LINKS (Top 6)", images)
             video_text = format_media("🎥 VIDEO LINKS (Top 2)", videos)
             response_text += image_text + video_text

        response_text += download_text
             
        if not download_text and not images and not videos:
            response_text += "ℹ️ No specific download or media links found on the page."

    else:
        response_text = f"❌ Scraping Failed: {scrape_result.get('message', 'Unknown Error')}"

    # Response sirf download links ya error ke liye
    run_sync(BOT.send_message(chat_id, response_text, parse_mode='Markdown', disable_web_page_preview=True))


# --- HANDLE UPDATE MAIN LOGIC ---
def handle_update(update_data):
    """Processes a single Telegram Update dictionary."""
    message_data = update_data.get('message', {})
    text = message_data.get('text', '').strip()
    chat_id = message_data.get('chat', {}).get('id')
    
    if not chat_id or not text: return
    
    # Parse command and URL
    parts = text.split(maxsplit=1)
    command = parts[0].lower()
    url = parts[1] if len(parts) > 1 and URL_REGEX.fullmatch(parts[1]) else None
    
    # Default to /download if only URL is sent
    if URL_REGEX.fullmatch(text):
        command = '/download' 
        url = text

    try:
        if command == "/start":
            run_sync(BOT.send_message(chat_id, "Welcome! Send me a direct file URL to download and upload it (Max 20MB). You can also use the /addlink command for scraping links."))
            return

        if not url:
            run_sync(BOT.send_message(chat_id, "Please provide a valid URL after the command."))
            return

        run_sync(BOT.send_message(chat_id, f"🔍 Processing: **{command}** for **{url}**...", parse_mode='Markdown'))
        
        if command == '/download':
            # Direct File Download and Upload Logic (Default Action)
            run_sync(handle_direct_file_download_and_send(chat_id, url))
        
        elif command == '/addlink':
            # Scraping and Link Extraction Logic
            handle_scrape_and_send(chat_id, url)
        
        else:
            run_sync(BOT.send_message(chat_id, "Invalid command. Use `/addlink` or send a direct URL."))

    except Exception as e:
        logger.error(f"Global Update Handler Error: {e}")
        error_text = f"❌ An unexpected error occurred: {e}"
        run_sync(BOT.send_message(chat_id, error_text))

# --- FLASK APPLICATION SETUP ---
def create_app():  
    """Creates the Flask app and webhook route for Gunicorn."""
    app = Flask(__name__)
    @app.route('/telegram', methods=['POST'])
    def webhook():
        if request.method == "POST":
            update_data = request.get_json()
            handle_update(update_data)
        return jsonify({'status': 'ok'}), 200 
    return app
