# /home/gauravwhy/Lqink_bot/scraper.py (Final Code with ScraperAPI)

import requests
from bs4 import BeautifulSoup
import os
import re
import logging
import json

logger = logging.getLogger(__name__)

# Render Environment Variable से API Key लोड करें
SCRAPER_API_KEY = os.environ.get("SCRAPER_API_KEY")

# --- UTILITY FUNCTIONS ---

def fetch_html_via_api(url):
    """ScraperAPI का उपयोग करके HTML content fetch करता है।"""
    if not SCRAPER_API_KEY:
        return None, "Error: SCRAPER_API_KEY not set."
        
    API_URL = "http://api.scraperapi.com/"
    
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': url,
        # Render पर JavaScript-heavy sites के लिए 'render=true' का उपयोग किया जा सकता है,
        # लेकिन हम मुफ्त टियर के लिए इसे बंद रखते हैं।
        # 'render': 'true', 
        'country_code': 'us'
    }

    try:
        # ScraperAPI को कॉल करें
        response = requests.get(API_URL, params=payload, timeout=30)
        response.raise_for_status() # HTTP errors को हैंडल करें
        
        # ScraperAPI सफलतापूर्वक जवाब दे सकता है, लेकिन हो सकता है कि उसने कंटेंट लोड न किया हो
        if response.status_code == 200:
            return response.content, None
        else:
            return None, f"ScraperAPI returned status code: {response.status_code}"

    except requests.exceptions.RequestException as e:
        logger.error(f"API fetch error for {url}: {e}")
        return None, f"Network or API Call Error: {e}"


# --- EXTRACTION FUNCTIONS (BASIC) ---

def extract_links(soup, base_url):
    """Soup object से पहले 5 non-empty links निकालता है।"""
    links = {}
    count = 0
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        text = a_tag.get_text(strip=True)
        
        if href and text and href.startswith('http') and count < 5:
            links[text] = href
            count += 1
            
    return links

def extract_media(soup):
    """Dummy function for media (आप इसे बाद में जोड़ सकते हैं)"""
    return []

# --- MAIN SCRAPER FUNCTION ---

def run_scraper(url):
    """ScraperAPI का उपयोग करके scraping process चलाता है।"""
    
    html_content, error_msg = fetch_html_via_api(url)
    
    if error_msg:
        return {'status': 'error', 'message': error_msg}

    try:
        # HTML को पार्स करें
        soup = BeautifulSoup(html_content, 'html.parser')

        # डेटा निकालें
        extracted_links = extract_links(soup, url)
        # extracted_media = extract_media(soup) # Media abhi skip kiya

        return {
            'status': 'success',
            'links': extracted_links,
            'media': [], # Media abhi empty hai
            'message': 'Data extracted via ScraperAPI.'
        }

    except Exception as e:
        logger.error(f"Scraping/Parsing Error: {e}")
        return {'status': 'error', 'message': f"Parsing failed: {e}"}

def clean_up_files(file_list):
    """Dummy function for cleanup."""
    pass
