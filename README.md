**Automated Arabic News Aggregator & Classifier**
This repository contains an automated backend pipeline designed to aggregate, process, classify, and store Arabic news articles from multiple prominent RSS feeds across the Arab world. The system integrates real-time web scraping with an AI-powered Natural Language Processing (NLP) classification API built on top of the MARBERT model, storing the enriched and structured data directly into a Supabase database.

**Key Features**
**Multi-Source RSS Aggregation:** Automatically fetches latest news entries from a wide range of trusted Arabic news sources, covering general politics, regional news (Egypt, Jordan, Lebanon, Yemen, Saudi Arabia), and sports.

**Automated Web Scraping & Cleaning:** Uses BeautifulSoup and custom cleaning functions to extract full article content and OpenGraph images while filtering out short or low-quality articles.

**AI-Powered Text Classification:** Sends extracted article texts to a custom-hosted Hugging Face API endpoint powered by MARBERT to automatically categorize articles (politics, sports, technology, health, economy, culture).

**Database Management & Deduplication:** Checks for existing articles to prevent duplicates and seamlessly manages relational records for sources and categories using Supabase.

**Smart Status Assignment:** Automatically publishes classified articles matching allowed categories while setting unclassified or out-of-scope articles to a pending status.

Tech Stack**

**Language:** Python

**Database & Backend:** Supabase (PostgreSQL)

**Libraries & Frameworks:**
- feedparser (RSS parsing)
- requests (API communication)
- BeautifulSoup4 (Web scraping)
- supabase-py (Database client)

**AI / ML Integration:** Hugging Face API (MARBERT model for Arabic text classification)
