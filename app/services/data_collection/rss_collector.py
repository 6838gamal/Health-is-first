import feedparser
import hashlib
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

HEALTH_RSS_FEEDS = [
    {"name": "WHO News", "url": "https://www.who.int/rss-feeds/news-english.xml", "reliability": 9.5},
    {"name": "Medical News Today", "url": "https://www.medicalnewstoday.com/rss", "reliability": 8.0},
    {"name": "Healthline", "url": "https://www.healthline.com/rss/health-news", "reliability": 8.0},
    {"name": "WebMD", "url": "https://rssfeeds.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC", "reliability": 8.5},
    {"name": "Harvard Health", "url": "https://www.health.harvard.edu/blog/feed", "reliability": 9.0},
    {"name": "NIH News", "url": "https://www.nih.gov/news-events/news-releases/feed.xml", "reliability": 9.5},
]


class RSSCollector:
    def __init__(self):
        self.seen_hashes: set = set()

    def _hash_title(self, title: str) -> str:
        return hashlib.md5(title.lower().strip().encode()).hexdigest()

    def fetch_feed(self, feed_url: str, max_items: int = 20) -> List[Dict]:
        try:
            feed = feedparser.parse(feed_url)
            items = []
            for entry in feed.entries[:max_items]:
                title = entry.get("title", "").strip()
                if not title:
                    continue
                h = self._hash_title(title)
                if h in self.seen_hashes:
                    continue
                self.seen_hashes.add(h)

                published = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6]).isoformat()
                    except Exception:
                        pass

                items.append({
                    "title": title,
                    "summary": entry.get("summary", "")[:1000],
                    "url": entry.get("link", ""),
                    "published_at": published,
                    "source_name": feed.feed.get("title", "Unknown"),
                })
            logger.info(f"Fetched {len(items)} items from {feed_url}")
            return items
        except Exception as e:
            logger.error(f"Error fetching RSS {feed_url}: {e}")
            return []

    def fetch_all_feeds(self) -> List[Dict]:
        all_items = []
        for feed_info in HEALTH_RSS_FEEDS:
            items = self.fetch_feed(feed_info["url"])
            for item in items:
                item["reliability_score"] = feed_info["reliability"]
                item["feed_name"] = feed_info["name"]
            all_items.extend(items)
        logger.info(f"Total RSS items collected: {len(all_items)}")
        return all_items
