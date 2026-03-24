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

# Expanded Categories (Local, National, World, Sports, Film)
SEARCH_FEEDS = {
    "Belagavi Local": "https://news.google.com/rss/search?q=Belagavi+Jarkiholi+Hebbalkar+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "National": "https://news.google.com/rss/search?q=India+Top+News+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "World": "https://news.google.com/rss/search?q=World+News+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "Sports": "https://news.google.com/rss/search?q=Cricket+Sports+India+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "Entertainment": "https://news.google.com/rss/search?q=Bollywood+Tollywood+Cinema+when:24h&hl=en-IN&gl=IN&ceid=IN:en"
}

def extract_real_image(url):
    """Visits the actual news site to scrape the high-res image"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=5)
        # Look for the OpenGraph image tag used by all major news sites
        match = re.search(r'<meta\s+(?:property|name)="og:image"\s+content="([^"]+)"', response.text)
        if match:
            return match.group(1)
    except Exception:
        pass
    # Premium dark fallback image
    return "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80"

def generate_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:8]

def run_news_pipeline():
    print("Fetching expanded real-time news...")
    
    current_db = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            try:
                current_db = json.load(f)
            except:
                current_db = []

    new_articles = []

    # Pull 12 articles per category to ensure we get a massive list
    for category, url in SEARCH_FEEDS.items():
        feed = feedparser.parse(url)
        top_entries = feed.entries[:12] 

        for entry in top_entries:
            print(f"Processing {category}: {entry.title}")
            article_id = generate_id(entry.link)
            
            # Skip duplicates
            if any(item.get('id') == article_id for item in current_db):
                continue
                
            # Grab the real image from the website
            image_url = extract_real_image(entry.link)
            
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
                time.sleep(4) # Respect API limits so it doesn't crash
                
            except Exception as e:
                print(f"Skipped due to API/formatting error.")
                time.sleep(4)

    # Save up to 80 articles for an endless scroll experience
    updated_db = new_articles + current_db
    updated_db = updated_db[:80] 
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print(f"Saved {len(updated_db)} fresh articles!")

if __name__ == "__main__":
    run_news_pipeline()
