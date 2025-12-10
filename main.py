# /home/gauravwhy/Lqink_bot/main.py

# ... (बाकी imports, BOT_TOKEN loading आदि वही रहेगा) ...

def handle_update(update_data):
    # ... (chat_id, text, /start handling code वही रहेगा) ...

    try:
        # ... (URL regex check code वही रहेगा) ...

        user_url = text
        
        # ⚠️ SCRAPING BYPASS हटाएँ, और रन_स्क्रैपर को कॉल करें
        run_sync(BOT.send_message(chat_id, f"🔍 Searching for content on: **{user_url}**...", parse_mode='Markdown'))

        # 1. Scraper को चलाएं
        scrape_result = run_scraper(user_url)
        
        # 2. रिजल्ट के आधार पर जवाब दें
        if scrape_result['status'] == 'success':
            response_text = f"✅ Content found for: **{user_url}**\n\n"
            
            # Links जोड़ें
            if scrape_result.get('links'):
                response_text += "\n**🔗 Extracted Links:**\n"
                for text, href in scrape_result['links'].items():
                    response_text += f"- [{text}]({href})\n"
            
            # Media/Video Files (अगर आपने scraper.py में जोड़ा है)
            if scrape_result.get('media'):
                 response_text += "\n**🖼️ Media Found:**\n"
                 # ... (media handling logic) ...
            
            # Fallback अगर कोई लिंक नहीं मिला
            if not scrape_result.get('links') and not scrape_result.get('media'):
                response_text += "ℹ️ No specific links or media found, but the page loaded successfully."


        else:
            # अगर scraping विफल होता है (API या नेटवर्क एरर)
            response_text = f"❌ Scraping Failed: {scrape_result.get('message', 'Unknown Error')}"

        run_sync(BOT.send_message(chat_id, response_text, parse_mode='Markdown'))

    except Exception as e:
        logger.error(f"Main handling error: {e}")
        error_text = f"❌ An unexpected error occurred during processing: {e}"
        run_sync(BOT.send_message(chat_id, error_text))
