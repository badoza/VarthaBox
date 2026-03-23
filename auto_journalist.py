import os
import requests
import feedparser
from google import genai
import json
import re
import hashlib

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# MASSIVE News Feeds List
FEEDS = {
    "Top News": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "Tech & Startups": "https://timesofindia.indiatimes.com/rssfeeds/66946927.cms",
    "Sports": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
    "Entertainment": "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms",
    "Business": "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms",
    "Science": "https://timesofindia.indiatimes.com/rssfeeds/-2128672765.cms"
}

def extract_image(entry):
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0].get('href', '')
    img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
    if img_match:
        return img_match.group(1)
    return "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80"

def generate_id(url):
    # Creates a unique short ID for deep-linking based on the article URL
    return hashlib.md5(url.encode()).hexdigest()[:8]

def run_news_pipeline():
    print("Fetching expanded VarthaBox news...")
    
    current_db = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            try:
                current_db = json.load(f)
            except:
                current_db = []

    new_articles = []

    # Pull 3 articles from EACH of the 6 categories (18 new articles per run)
    for category, url in FEEDS.items():
        feed = feedparser.parse(url)
        top_entries = feed.entries[:3] 

        for entry in top_entries:
            print(f"Processing {category}: {entry.title}")
            image_url = extract_image(entry)
            article_id = generate_id(entry.link)
            
            # Check if we already have this article to avoid duplicates
            if any(item.get('id') == article_id for item in current_db):
                print("Skipping duplicate.")
                continue
            
            prompt = f"""
            You are a professional journalist for a minimalist news app. 
            Rewrite this raw news data into a tight, engaging, 50-word news summary. 
            Translate the title and the summary perfectly into Kannada, Marathi, and Hindi.
            
            Return ONLY a valid JSON object with this exact structure:
            {{
                "en": {{"title": "English Title", "content": "English Content"}},
                "kn": {{"title": "Kannada Title", "content": "Kannada Content"}},
                "mr": {{"title": "Marathi Title", "content": "Marathi Content"}},
                "hi": {{"title": "Hindi Title", "content": "Hindi Content"}}
            }}
            
            Raw data: {entry.title} - {entry.summary}
            """
            
            try:
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                raw_text = re.sub(r'```json\n?', '', response.text)
                raw_text = re.sub(r'```\n?', '', raw_text)
                translations = json.loads(raw_text.strip())
                
                article = {
                    "id": article_id,
                    "category": category,
                    "image": image_url,
                    "translations": translations,
                    "link": entry.link
                }
                new_articles.append(article)
            except Exception as e:
                print(f"Error generating content: {e}")

    # Combine and save (keep latest 50 articles for endless swiping!)
    updated_db = new_articles + current_db
    updated_db = updated_db[:50] 
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print("Saved 50 articles to news.json locally!")

if __name__ == "__main__":
    run_news_pipeline()
