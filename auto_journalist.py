import os
import requests
import feedparser
from google import genai
import json
import re
import hashlib
import time

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Direct publisher RSS feeds to prevent GitHub from being blocked
SEARCH_FEEDS = {
    "Karnataka Local": "https://timesofindia.indiatimes.com/rssfeeds/46088681.cms",
    "National": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "World": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "Sports": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
    "Entertainment": "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms",
    "Tech & Startups": "https://timesofindia.indiatimes.com/rssfeeds/66946927.cms"
}

def extract_real_image(url, entry):
    # 1. Check official RSS enclosures
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0].get('href', '')
    
    # 2. Check hidden summary tags
    img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
    if img_match:
        return img_match.group(1)
        
    # 3. Scrape the live website for the high-res meta image
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        match = re.search(r'<meta\s+(?:property|name)="og:image"\s+content="([^"]+)"', response.text)
        if match:
            return match.group(1)
    except Exception:
        pass
        
    # 4. Premium Fallback
    return "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80"

def generate_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:8]

def run_news_pipeline():
    print("Fetching reliable multi-source news...")
    
    current_db = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            try:
                current_db = json.load(f)
            except:
                current_db = []

    new_articles = []

    for category, url in SEARCH_FEEDS.items():
        feed = feedparser.parse(url)
        top_entries = feed.entries[:10] 

        for entry in top_entries:
            print(f"Processing {category}: {entry.title}")
            article_id = generate_id(entry.link)
            
            if any(item.get('id') == article_id for item in current_db):
                continue
                
            image_url = extract_real_image(entry.link, entry)
            
            prompt = f"""
            Rewrite this raw news into a tight, engaging, 60-word summary for an app.
            Translate the title and summary perfectly into Kannada, Marathi, and Hindi.
            Return ONLY a valid JSON object without any backticks or markdown:
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
                    "translations": translations,
                    "image": image_url,
                    "link": entry.link
                }
                new_articles.append(article)
                print(f"Successfully processed {category}!")
                time.sleep(4) # Prevent rate limits
                
            except Exception as e:
                print(f"Skipped article due to error.")
                time.sleep(4)

    updated_db = new_articles + current_db
    updated_db = updated_db[:80] # Keep 80 articles for endless swiping
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print(f"Saved {len(updated_db)} articles to news.json!")

if __name__ == "__main__":
    run_news_pipeline()
