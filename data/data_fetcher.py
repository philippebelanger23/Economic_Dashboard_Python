# data/data_fetcher.py
import pandas as pd
from fredapi import Fred
from tenacity import retry, stop_after_attempt, wait_fixed
import feedparser
from config.settings import FRED_API_KEY, BASE_DIR, RSS_FEED_URLS
from datetime import datetime
import json
import time
import os

print("FRED_API_KEY:", FRED_API_KEY)

fred = Fred(api_key=FRED_API_KEY)
CACHE_FILE = BASE_DIR / "data" / "fred_cache.pkl"
CACHE_METADATA_FILE = BASE_DIR / "data" / "fred_cache_metadata.json"
RELEASE_DATES_CACHE = BASE_DIR / "data" / "release_dates_cache.json"


@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def fetch_series(series):
    print(f"Attempting to fetch series {series}...")
    series_data = fred.get_series(series)
    print(f"Successfully fetched {series} with {len(series_data)} data points")
    return series_data


def fetch_fred_data(force_refresh=False):
    # Load existing cache and metadata if available
    cached_data = {}
    cached_indicators = set()

    if CACHE_FILE.exists() and not force_refresh:
        print("Loading cached data from", CACHE_FILE)
        cached_data = pd.read_pickle(CACHE_FILE)

        # Load metadata (list of indicators in the cache)
        if os.path.exists(CACHE_METADATA_FILE):
            with open(CACHE_METADATA_FILE, "r") as f:
                cached_indicators = set(json.load(f))
            print(f"Cached indicators: {cached_indicators}")
        else:
            # If metadata doesn't exist, assume all columns in cached_data are indicators
            cached_indicators = set(cached_data.columns)
            with open(CACHE_METADATA_FILE, "w") as f:
                json.dump(list(cached_indicators), f)

    from data.mappings import INDICATORS

    new_data = {}
    indicators_to_fetch = set()

    # Identify indicators that need to be fetched (not in cache or force_refresh=True)
    for key, info in INDICATORS.items():
        if force_refresh or key not in cached_indicators:
            indicators_to_fetch.add(key)

    if not indicators_to_fetch:
        print("All indicators already in cache, no fetching required")
    else:
        print(
            f"Fetching {len(indicators_to_fetch)} new or updated indicators: {indicators_to_fetch}"
        )
        for key in indicators_to_fetch:
            info = INDICATORS[key]
            try:
                print(f"Fetching data for {key} ({info['id']})...")
                series_data = fetch_series(info["id"])
                if series_data.empty:
                    print(f"❌ No data returned for {key} ({info['id']})")
                else:
                    new_data[key] = series_data
                time.sleep(1)  # 1-second delay to avoid rate-limiting
            except Exception as e:
                print(f"❌ Error fetching {key} ({info['id']}): {str(e)}")

    # Combine cached data with newly fetched data
    if new_data:
        new_df = pd.DataFrame(new_data)
        if not new_df.empty:
            new_df.index = pd.to_datetime(new_df.index)
            # Align indices with cached_data if it exists
            if not cached_data.empty:
                date_range = pd.date_range(
                    start=min(cached_data.index.min(), new_df.index.min()),
                    end=max(cached_data.index.max(), new_df.index.max()),
                    freq="D",
                )
                cached_data = cached_data.reindex(date_range)
                new_df = new_df.reindex(date_range)
                df = pd.concat([cached_data, new_df], axis=1)
            else:
                date_range = pd.date_range(
                    start=new_df.index.min(), end=new_df.index.max(), freq="D"
                )
                new_df = new_df.reindex(date_range)
                df = new_df
        else:
            df = cached_data
    else:
        df = cached_data

    if df.empty:
        print("❌ DataFrame is empty after combining cached and new data")
    else:
        print(f"DataFrame created with columns: {df.columns.tolist()}")
        # Save the updated cache and metadata
        df.to_pickle(CACHE_FILE)
        with open(CACHE_METADATA_FILE, "w") as f:
            json.dump(list(df.columns), f)

    return df


def fetch_rss_feed(url, num_articles=5):
    """
    Fetch and return the latest RSS feed articles from the specified URL.

    Parameters:
        url (str): The URL of the RSS feed.
        num_articles (int): Number of articles to return (default: 5)

    Returns:
        list: A list of dictionaries, each containing the title, link, publication date, and summary.
        Returns an empty list if the fetch fails.
    """
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            print(f"❌ Error parsing RSS feed from {url}: {feed.bozo_exception}")
            return []

        articles = []
        for entry in feed.entries[:num_articles]:
            pub_date = entry.get("published", "") or entry.get("updated", "Unknown")
            if pub_date and pub_date != "Unknown":
                try:
                    pub_date = datetime.strptime(
                        pub_date, "%a, %d %b %Y %H:%M:%S %Z"
                    ).strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pub_date = "Unknown"

            summary = entry.get("summary", "")

            articles.append(
                {
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", "#"),
                    "pub_date": pub_date,
                    "summary": (
                        summary[:200] + "..."
                        if summary and len(summary) > 200
                        else summary
                    ),
                }
            )
        return articles

    except Exception as e:
        print(f"❌ Error fetching RSS feed from {url}: {e}")
        return []


def fetch_next_release_date(series_id):
    try:
        release_info = fred.get_series_release(series_id)
        release_id = release_info["id"]
        today = datetime.today().strftime("%Y-%m-%d")
        future_dates = fred.get_release_dates(
            release_id=release_id,
            include_release_dates_with_no_data=False,
            realtime_start=today,
            limit=1,
            sort_order="asc",
        )
        if future_dates and len(future_dates) > 0:
            next_date = future_dates[0]["date"]
            return next_date
        past_dates = fred.get_release_dates(
            release_id=release_id,
            include_release_dates_with_no_data=False,
            realtime_end=today,
            limit=1,
            sort_order="desc",
        )
        if past_dates and len(past_dates) > 0:
            last_date = past_dates[0]["date"]
            return f"Last Release: {last_date} (Next TBD)"
        return "Unknown"
    except Exception as e:
        print(f"❌ Error fetching release date for {series_id}: {e}")
        return "Unknown"


def get_all_next_release_dates(force_refresh=False):
    if RELEASE_DATES_CACHE.exists() and not force_refresh:
        with open(RELEASE_DATES_CACHE, "r") as f:
            return json.load(f)

    from data.mappings import INDICATORS

    release_dates = {}
    for key, info in INDICATORS.items():
        series_id = info["id"]
        print(f"Fetching next release date for {key} ({series_id})...")
        next_date = fetch_next_release_date(series_id)
        release_dates[series_id] = next_date

    with open(RELEASE_DATES_CACHE, "w") as f:
        json.dump(release_dates, f)

    return release_dates


if __name__ == "__main__":
    df = fetch_fred_data()
    print("✅ Data fetched. Available columns:", df.columns)
    print("Data available from:", df.index.min(), "to", df.index.max())
