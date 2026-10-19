import os
import re
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from supabase import create_client
from transformers import pipeline

# =============================
# CONFIG
# =============================

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

RSS_SOURCES = {
    # General news
    "BBC Arabic": "https://feeds.bbci.co.uk/arabic/rss.xml",
    "France24 Arabic": "https://www.france24.com/ar/rss",
    "RT Arabic": "https://arabic.rt.com/rss/",
    "Alsharq (Qatar)": "https://al-sharq.com/rss/latestNews",

    # Egypt
    "Al-Masry Al-Youm": "https://almasryalyoum.com/rss/rssfeed",
    "Masrawy": "https://www.masrawy.com/rss",

    # Jordan / Lebanon
    "Al Jadeed TV": "https://www.aljadeed.tv/rss",
    "SarayNews": "https://www.sarayanews.com/rss.php",

    # Yemen
    "Yemenat News": "https://yemenat.net/feed",
    "Yemen Voice": "https://ye-voice.com/rss.php?cat=5",
    "Yemen Saeed": "https://yemen-saeed.com/rss.php?cat=1",

    # Saudi Arabia
    "Okaz": "https://www.okaz.com.sa/rss",
    "Al Madina": "https://al-madina.com/rssFeed/193",
    "Al Bilad": "https://albiladdaily.com/feed",
    "Arab News": "https://www.arabnews.com/rss",

    # Sports
    "Kooora": "https://www.kooora.com/rss",
    "FilGoal": "https://www.filgoal.com/rss",
    "YallaKora": "https://www.yallakora.com/rss",
    "beIN Sports Arabic": "https://www.beinsports.com/ar/rss",
}

ALLOWED_CATEGORIES = {
    "politics": 1,
    "sports": 2,
    "technology": 3,
    "health": 4,
    "economy": 5,
    "culture": 6,
}

# The model outputs: Culture, Finance, Medical, Politics, Religion, Sports.
# Religion is mapped to culture because there is currently no religion category
# in ALLOWED_CATEGORIES.
CATEGORY_MAPPING = {
    "tech": "technology",
    "technology": "technology",
    "finance": "economy",
    "economics": "economy",
    "economy": "economy",
    "politics": "politics",
    "sports": "sports",
    "health": "health",
    "culture": "culture",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (NabaAI Bot)"
}

MAX_CHARS = 2000

# =============================
# INIT
# =============================

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Load the Hugging Face model directly. This replaces the old /api/predict call.
classifier = pipeline(
    "text-classification",
    model="zico2m/arabic-news-topic-classifier",
    tokenizer="zico2m/arabic-news-topic-classifier",
)

# =============================
# HELPERS
# =============================

def now_utc():
    return datetime.now(timezone.utc).isoformat()


def clean_text(text: str) -> str:
    text = re.sub(r"\\s+", " ", text)
    return text.strip()


def classify(text: str) -> str:
    """Classify an article using the downloaded Hugging Face model."""
    try:
        short_text = text[:MAX_CHARS]
        result = classifier(short_text, truncation=True)[0]

        label = str(result.get("label", "unknown")).lower().strip()
        score = result.get("score")

        if score is not None:
            print(f"Prediction: {label} | Confidence: {score:.4f}")
        else:
            print(f"Prediction: {label}")

        return label

    except Exception as e:
        print("WARNING: Classification failed:", e)
        return "unknown"


def already_exists(title: str) -> bool:
    res = (
        supabase.table("news")
        .select("id")
        .eq("title", title)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def get_or_create_source(name: str) -> int:
    res = (
        supabase.table("sources")
        .select("id")
        .eq("name", name)
        .limit(1)
        .execute()
    )

    if res.data:
        return res.data[0]["id"]

    ins = supabase.table("sources").insert({
        "name": name,
        "source_type_id": 1,
    }).execute()

    return ins.data[0]["id"]

# =============================
# ARTICLE SCRAPER
# =============================

def fetch_full_article(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        paragraphs = soup.find_all("p")
        content = " ".join(p.get_text(" ", strip=True) for p in paragraphs)
        content = clean_text(content)

        img = soup.find("meta", property="og:image")
        image_url = img.get("content") if img else None

        return content, image_url

    except Exception as e:
        print("WARNING: Article fetch failed:", e)
        return None, None

# =============================
# MAIN
# =============================

def main():
    added = 0

    for source_name, rss_url in RSS_SOURCES.items():
        print(f"\\nFetching from {source_name}")

        try:
            feed = feedparser.parse(rss_url)
            source_id = get_or_create_source(source_name)
        except Exception as e:
            print(f"WARNING: Could not prepare source {source_name}: {e}")
            continue

        for item in feed.entries[:15]:
            title = item.get("title")
            link = item.get("link")

            if not title or not link:
                continue

            try:
                if already_exists(title):
                    continue

                content, image_url = fetch_full_article(link)
                if not content or len(content) < 300:
                    continue

                predicted_raw = classify(content)
                mapped_category = CATEGORY_MAPPING.get(predicted_raw)
                status = "pending"
                category_id = None

                if mapped_category and mapped_category in ALLOWED_CATEGORIES:
                    category_id = ALLOWED_CATEGORIES[mapped_category]
                    status = "published"

                supabase.table("news").insert({
                    "title": title,
                    "content": content,
                    "primary_image": image_url,
                    "category_id": category_id,
                    "source_id": source_id,
                    "status": status,
                    "is_external": True,
                    "published_at": now_utc(),
                }).execute()

                added += 1
                print(f"Added ({status}): {title}")

            except Exception as e:
                print(f"WARNING: Failed processing article '{title}': {e}")
                continue

    print(f"\\nDONE. Total added: {added}")

# =============================
# RUN
# =============================

if __name__ == "__main__":
    mainn()
