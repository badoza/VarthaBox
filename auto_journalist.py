import os
import requests
import feedparser
from google import genai
import json
import re

# Setup API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 1. Hyper-Local Political Search Queries (Uses Google News RSS Search)
# We structure the query to find major politicians and the Jarkiholi family in Belagavi.
SEARCH_FEEDS = {
    # Searches specifically for Ramesh, Satish, and Balachandra in Belagavi district politics
    "Jarkiholi Family": "https://news.google.com/rss/search?q=Ramesh+Satish+Balachandra+Jarkiholi+Family+Belagavi+politics&hl=en-IN&gl=IN&ceid=IN:en",
    # Searches specifically for Lakshmi Hebbalkar in Belagavi district politics
    "Lakshmi Hebbalkar": "https://news.google.com/rss/search?q=Lakshmi+Hebbalkar+Belagavi+politics&hl=en-IN&gl=IN&ceid=IN:en",
    # General top political and district news from Belagavi
    "Belagavi District Politics": "https://news.google.com/rss/search?q=Belagavi+district+politics+RDC+latest+news&hl=en-IN&gl=IN&ceid=IN:en"
}

def extract_image(entry):
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0].get('href', '')
    img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
    if img_match:
        return img_match.group(1)
    return "https://images.unsplash.com/photo-1495020689067-958852a7765e?w=800&q=80" # Fallback image

def run_news_pipeline():
    print("Fetching Belagavi-specific news data...")
    
    current_db = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            try:
                current_db = json.load(f)
            except:
                current_db = []

    new_articles = []

    # Pull 5 articles from EACH of the 3 specialized search categories (15 articles total per run)
    for category, url in SEARCH_FEEDS.items():
        feed = feedparser.parse(url)
        top_entries = feed.entries[:5] 

        for entry in top_entries:
            print(f"Processing {category}: {entry.title}")
            image_url = extract_image(entry)
            
            # The prompt is simplified to ensure it fits within free tier limits while translating.
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
                response = model.generate_content(prompt)
                raw_text = response.text
                
                # Clean up JSON formatting
                raw_text = re.sub(r'```json\n?', '', raw_text)
                raw_text = re.sub(r'```\n?', '', raw_text)
                
                translations = json.loads(raw_text.strip())
                
                article = {
                    "translations": translations,
                    "image": image_url,
                    "link": entry.link
                }
                new_articles.append(article)
                print(f"Successfully processed {category}!")
            except Exception as e:
                print(f"Error generating content: {e}")

    # Combine and save (keep latest 60 articles for endless swiping)
    updated_db = new_articles + current_db
    updated_db = updated_db[:60] 
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print(f"Saved {len(updated_db)} articles to news.json locally!")

if __name__ == "__main__":
    run_news_pipeline()
