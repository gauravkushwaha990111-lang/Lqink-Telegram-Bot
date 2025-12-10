# /home/gauravwhy/Lqink_bot/scraper.py (FINAL ADVANCED EXTRACTION)

import requests
from bs4 import BeautifulSoup
import os
import re
import logging
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)

SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

# --- UTILITY FUNCTIONS ---
def fetch_html_via_api(url):
    # ... (ScraperAPI call logic yahi rahega) ...
    if not SCRAPER_API_KEY: return None, "Error: SCRAPER_API_KEY not set. Check Render Variables."
    API_URL = "http://api.scraperapi.com/"
    payload = {'api_key': SCRAPER_API_KEY, 'url': url, 'country_code': 'us'}

    try:
        response = requests.get(API_URL, params=payload, timeout=45)
        response.raise_for_status() 
        if response.status_code == 200:
            return response.content, None
        else:
            return None, f"ScraperAPI returned status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        logger.error(f"API fetch error for {url}: {e}")
        return None, f"Network or API Call Error: {e}"

# --- ADVANCED EXTRACTION FUNCTIONS ---
def extract_advanced_data(soup, base_url):
    images = set()
    videos = set()
    downloads = set()
    general_links = set()

    download_extensions = ['.mp4', '.avi', '.zip', '.rar', '.pdf', '.exe', '.apk', '.iso', '.mp3', '.torrent', '.dmg']
    
    # 1. Images (<img> tags)
    for img in soup.find_all('img', src=True):
        src = urljoin(base_url, img['src'])
        if src.startswith('http'): images.add(src)
            
    # 2. Videos (<video> tags)
    for video in soup.find_all('video', src=True):
        src = urljoin(base_url, video['src'])
        if src.startswith('http'): videos.add(src)
    
    # 3. Downloadable Files (Links)
    for a_tag in soup.find_all('a', href=True):
        href = urljoin(base_url, a_tag['href'])
        text = a_tag.get_text(strip=True) or os.path.basename(urlparse(href).path)

        if not href.startswith('http'): continue
            
        is_download = False
        
        if any(href.lower().endswith(ext) for ext in download_extensions):
             is_download = True
        
        # Check by link text
        if re.search(r'download|install|apk|zip|video|file|gofile\.io', text.lower()) and not is_download:
             is_download = True
        
        if href in images or href in videos: continue

        if is_download:
            downloads.add((text, href))
        else:
            general_links.add((text, href))

    return {
        'images': list(images)[:6],
        'videos': list(videos)[:2],
        'downloads': list(downloads),
        'general': list(general_links)[:10]
    }

# --- MAIN SCRAPER FUNCTION ---
def run_scraper(url):
    html_content, error_msg = fetch_html_via_api(url)
    if error_msg: return {'status': 'error', 'message': error_msg}

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        extracted_data = extract_advanced_data(soup, url)

        return {'status': 'success', 'data': extracted_data, 'message': 'Data extracted via ScraperAPI.'}

    except Exception as e:
        logger.error(f"Scraping/Parsing Error: {e}")
        return {'status': 'error', 'message': f"Parsing failed: {e}"}

def clean_up_files(file_list):
    pass
