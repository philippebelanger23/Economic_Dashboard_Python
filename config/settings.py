# config/settings.py
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRED_API_KEY = os.getenv("FRED_API_KEY", "a734c74dab0f321bd97ed766dc2c8e4f")
RECESSIONS_FILE = BASE_DIR / "data" / "recessions.json"
RSS_FEED_URLS = {
    "Federal Reserve": "https://www.federalreserve.gov/feeds/press_all.xml",
    "Financial Times": "https://www.ft.com/global-economy?format=rss",
    "Energy Information Administration": "https://www.eia.gov/rss/todayinenergy.xml",
    "CEPR - Discussion Paper": "https://cepr.org/rss/discussion-paper",
    "CEPR - News": "https://cepr.org/rss/news",
    "Wall Street Journal": "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed",
}
    
