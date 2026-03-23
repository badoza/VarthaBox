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

# 1. 24-HOUR REAL-TIME SEARCH QUERIES
# Notice the "when:24h" added to every link. This forces Google to ONLY return news from today!
SEARCH_FEEDS = {
    "Belagavi Politics": "https://news.google.com/rss/search?q=Belagavi+politics+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "Jarkiholi & Hebbalkar": "https://news.google.com/rss/search?q=Jarkiholi+OR+Hebbalkar+Belagavi+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "Karnataka Updates": "https://news.google.com/rss/search?q=Karnataka+News+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "National News": "https://news.google.com/rss/search?q=India+Top+News+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "Tech & Startups": "https://news.google.com/rss/search?q=Technology+Startups+India+when:24h&hl=en-IN&gl=IN&ceid=IN:en",
    "Sports": "https://news.google.com/rss/search?q=Sports+Cricket+India+when:24h&hl=en-IN&gl=IN&ceid=IN:en"
}

def extract_image(entry):
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0].get('href', '')
    img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
    if img_match:
        return img_match.group(1)
    return "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80"

def generate_id(url):
    return hashlib.md5(url.encode()).hexdigest()[:8]

def run_news_pipeline():
    print("Fetching strictly 24-hour real-time news...")
    
    current_db = []
    # Note: We wipe the database and start fresh every time so old news doesn't pile up!
    
    new_articles = []

    # Pull up to 10 articles from EACH of the 6 categories (Aiming for 60 fresh articles)
    for category, url in SEARCH_FEEDS.items():
        feed = feedparser.parse(url)
        top_entries = feed.entries[:10] 

        for entry in top_entries:
            print(f"Processing {category}: {entry.title}")
            image_url = extract_image(entry)
            article_id = generate_id(entry.link)
            
            # Skip if we already processed this exact article in this run
            if any(item.get('id') == article_id for item in new_articles):
                continue
            
            prompt = f"""
            You are a professional journalist for an app like Inshorts. 
            Rewrite this raw news data into a tight, engaging, 60-word news summary. It must be short and punchy.
            Then, translate the title and the summary perfectly into Kannada, Marathi, and Hindi.
            
            Return ONLY a valid JSON object with this exact structure, do not add markdown formatting or backticks:
            {{
                "en": {{"title": "English Title", "content": "English Content"}},
                "kn": {{"title": "Kannada Title", "content": "Kannada Content"}},
                "mr": {{"title": "Marathi Title", "content": "Marathi Content"}},
                "hi": {{"title": "Hindi Title", "content": "Hindi Content"}}
            }}
            
            Raw data: {entry.title} - {entry.summary}
            """
            
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                raw_text = response.text
                
                raw_text = re.sub(r'```json\n?', '', raw_text)
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
                
                # CRITICAL: Sleep for 4 seconds to avoid hitting the free Gemini Rate Limit
                time.sleep(4) 
                
            except Exception as e:
                print(f"Error generating content (likely skipped due to rate limit): {e}")
                time.sleep(5) # Wait longer if it hits an error

    # Save up to the latest 75 articles found
    updated_db = new_articles[:75] 
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print(f"Saved {len(updated_db)} fresh 24H articles to news.json locally!")

if __name__ == "__main__":
    run_news_pipeline()
