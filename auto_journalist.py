import os
import requests
import feedparser
from google import genai
import json
import re

# Setup API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

# Multiple News Categories
FEEDS = {
    "India": "https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms",
    "World": "https://timesofindia.indiatimes.com/rssfeeds/296589292.cms",
    "Sports": "https://timesofindia.indiatimes.com/rssfeeds/4719148.cms",
    "Cinema": "https://timesofindia.indiatimes.com/rssfeeds/1081479906.cms"
}

def extract_image(entry):
    # Try to find an image in the enclosure or description
    if 'enclosures' in entry and len(entry.enclosures) > 0:
        return entry.enclosures[0].get('href', '')
    
    # Fallback: search for an img tag in the summary
    img_match = re.search(r'<img[^>]+src="([^">]+)"', entry.summary)
    if img_match:
        return img_match.group(1)
        
    return "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800&q=80" # High-quality fallback image

def run_news_pipeline():
    print("Fetching VarthaBox news...")
    
    current_db = []
    if os.path.exists("news.json"):
        with open("news.json", "r", encoding="utf-8") as f:
            try:
                current_db = json.load(f)
            except:
                current_db = []

    new_articles = []

    # Pull 2 top articles from EACH category (8 total per run)
    for category, url in FEEDS.items():
        feed = feedparser.parse(url)
        top_entries = feed.entries[:2] 

        for entry in top_entries:
            print(f"Processing {category}: {entry.title}")
            image_url = extract_image(entry)
            
            prompt = f"""
            You are a professional journalist for an app like Inshorts. 
            Rewrite this raw news data into a tight, engaging, 60-word news summary. It must be short and punchy.
            Then, translate the title and the summary perfectly into Kannada, Marathi, and Hindi.
            
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
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                raw_text = response.text
                
                # Clean up JSON formatting if the AI adds Markdown backticks
                raw_text = re.sub(r'```json\n?', '', raw_text)
                raw_text = re.sub(r'```\n?', '', raw_text)
                
                translations = json.loads(raw_text.strip())
                
                article = {
                    "category": category,
                    "image": image_url,
                    "translations": translations,
                    "link": entry.link
                }
                new_articles.append(article)
                print(f"Successfully processed {category}!")
            except Exception as e:
                print(f"Error generating content: {e}")

    # Combine and save (keep latest 30 articles for swiping)
    updated_db = new_articles + current_db
    updated_db = updated_db[:30] 
    
    with open("news.json", "w", encoding='utf-8') as f:
        json.dump(updated_db, f, ensure_ascii=False, indent=4)
        
    print("Saved to news.json locally!")

if __name__ == "__main__":
    run_news_pipeline()
