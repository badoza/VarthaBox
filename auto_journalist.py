import os
import requests
import feedparser
import google.generativeai as genai
import json
import re

# 1. Setup API and News Source
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# Using Times of India Hubballi/Belagavi region RSS feed as a starting point
RSS_FEED_URL = "https://timesofindia.indiatimes.com/rssfeeds/-2128833038.cms" 

genai.configure(api_key=GEMINI_API_KEY)
# Using the free and fast Flash model
model = genai.GenerativeModel('gemini-1.5-flash')

def run_news_pipeline():
    print("Fetching raw news...")
    feed = feedparser.parse(RSS_FEED_URL)
    top_entries = feed.entries[:3] # Get top 3 news items
    
    # Load existing news if it exists
    current_db = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            try:
                current_db = json.load(f)
            except:
                current_db = []

    new_articles = []

    for entry in top_entries:
        print(f"Processing: {entry.title}")
        
        # The Master Prompt for Multi-Language Generation
        prompt = f"""
        You are a professional journalist. Rewrite this raw news data into a short, engaging 2-paragraph news article.
        Then, translate the title and the article perfectly into Kannada, Marathi, and Hindi.
        
        You MUST return ONLY a valid JSON object with this exact structure, do not add markdown formatting or backticks:
        {{
            "en": {{"title": "English Title", "content": "English Content"}},
            "kn": {{"title": "Kannada Title", "content": "Kannada Content"}},
            "mr": {{"title": "Marathi Title", "content": "Marathi Content"}},
            "hi": {{"title": "Hindi Title", "content": "Hindi Content"}}
        }}
        
        Raw data: {entry.title} - {entry.summary}
        """
        
        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            
            # Clean up the response to ensure it's pure JSON
            raw_text = re.sub(r'```json\n?', '', raw_text)
            raw_text = re.sub(r'```\n?', '', raw_text)
            
            translations = json.loads(raw_text.strip())
            
            article = {
                "translations": translations,
                "link": entry.link
            }
            new_articles.append(article)
            print("Successfully processed and translated!")
        except Exception as e:
            print(f"Error generating content: {e}")

    # Combine and save (keeping only the latest 15 articles to keep the site fast)
    updated_db = new_articles + current_db
    updated_db = updated_db[:15] 
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print("Saved to news.json locally!")

if __name__ == "__main__":
    run_news_pipeline()
