# CODE D: /home/gauravwhy/Lqink_bot/scraper.py (Final Proxy Fix)

import requests
from bs4 import BeautifulSoup
import os
import tempfile
import re
import logging

logger = logging.getLogger(__name__)

# --- UTILITY FUNCTIONS ---

def fetch_html(url):
    """Diye gaye URL se HTML content fetch karta hai. Mazboot User-Agent aur Proxy Fix ka upyog."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/', 
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        session = requests.Session()
        
        # ⚠️ FINAL PROXY FIX: Proxies ko explicitly None par set karein, taki PythonAnywhere proxy ko ignore kiya ja sake.
        session.proxies = {'http': None, 'https': None}

        response = session.get(url, headers=headers, timeout=15)
        
        response.raise_for_status() 
        return response.content
    except requests.exceptions.RequestException as e:
        # Error message ko log karna (aapko yahi error log me dikhega)
        logger.error(f"HTML fetch error for {url}: {e}")
        return None

def download_file(url, file_type):
    """File ko temporary directory mein download karta hai. Timeout badhaya gaya (30s)."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Referer': 'https://www.google.com/' 
        }
        
        session = requests.Session()
        # ⚠️ PROXY FIX: Download ke samay bhi proxy ko None par set karein
        session.proxies = {'http': None, 'https': None} 
        
        response = session.get(url, headers=headers, stream=True, timeout=30) 
        response.raise_for_status()

        temp_dir = tempfile.gettempdir()
        file_extension = '.jpg' if file_type == 'image' else '.mp4' 
        
        temp_file_path = os.path.join(temp_dir, os.urandom(12).hex() + file_extension)

        with open(temp_file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return temp_file_path
    except requests.exceptions.RequestException as e:
        logger.error(f"File download error for {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        return None

def clean_up_files(file_list):
    """Temporary files ko delete karta hai (Storage bachaane ke liye)."""
    for file_path in file_list:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError as e:
            logger.error(f"Error cleaning up {file_path}: {e}")

# --- SCRAPING LOGIC FUNCTIONS ---

def extract_media(soup):
    """HTML se top 7 images aur top 2 video links/files nikalta hai."""
    media_paths = []
    img_tags = soup.find_all('img')
    img_count = 0
    
    for img in img_tags:
        if img_count >= 7: 
            break
        src = img.get('src')
        
        if src and src.startswith(('http', 'https')) and ('logo' not in src.lower() and 'icon' not in src.lower()):
            
            try: 
                # Ab hum sirf URL collect kar rahe hain
                media_paths.append(src) 
                img_count += 1
                
            except Exception as e:
                logger.warning(f"Skipping failed image processing: {src}. Error: {e}")
                continue 

    # Videos nikalna
    video_count = 0
    video_elements = soup.find_all(['iframe', 'video'])
    for element in video_elements:
        if video_count >= 2:
            break
        
        if element.name == 'iframe':
            src = element.get('src')
            if src and ('youtube.com/embed' in src or 'player.vimeo.com' in src):
                media_paths.append(src) 
                video_count += 1
        
    return media_paths

def extract_links(soup):
    """HTML se headings ke neeche ke download links nikalta hai."""
    download_links = {}
    current_category = None
    
    all_elements = soup.find('body').find_all(['h2', 'h3', 'a'], limit=200) 

    for element in all_elements:
        text = element.get_text(strip=True)
        
        # Category ki pehchaan
        if element.name in ['h2', 'h3'] and 'DOWNLOAD FOR' in text.upper():
            current_category = text.strip()
            download_links[current_category] = []
        
        # Download link ki pehchaan
        elif current_category and element.name == 'a':
            href = element.get('href')
            button_text = element.get_text(strip=True)
            
            if href and href.startswith('http') and ('download' in button_text.lower() or any(ext in href.lower() for ext in ['.exe', '.apk', '.zip', '.iso', '.dmg'])):
                if href not in download_links[current_category]:
                    download_links[current_category].append(href)
    
    return download_links

def extract_user_count(soup):
    """HTML se 'monthly users' ki sankhya nikalta hai."""
    try:
        text_data = soup.get_text()
        match = re.search(r'([\d,]+)\s+monthly users', text_data, re.IGNORECASE)
        
        if match:
            return f"{match.group(1)} monthly users"
        
        return "N/A"
    
    except Exception as e:
        logger.error(f"User count extraction error: {e}")
        return "N/A"

# --- MAIN SCRAPER FUNCTION ---

def run_scraper(url):
    """Pura scraping process chalaata hai aur results return karta hai."""
    logger.info(f"Scraping started for: {url}")
    html_content = fetch_html(url)
    if not html_content:
        # Returning a clear error status
        return {'status': 'error', 'message': 'Failed to fetch website content.'}

    soup = BeautifulSoup(html_content, 'html.parser')
    
    results = {
        'status': 'success',
        'media_paths': [],      
        'download_links': {},   
        'user_count': 'N/A'     
    }

    # Data extraction
    results['media_paths'] = extract_media(soup)
    results['download_links'] = extract_links(soup)
    results['user_count'] = extract_user_count(soup)
    
    logger.info("Scraping finished.")
    return results

if __name__ == '__main__':
    pass