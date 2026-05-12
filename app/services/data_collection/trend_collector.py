import logging
import httpx
from typing import List, Dict
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

HEALTH_KEYWORDS = [
    "صحة", "تغذية", "رجيم", "لياقة", "دايت", "فيتامين",
    "نوم", "تمرين", "صحة نفسية", "قلب", "سكر", "ضغط",
    "health tips", "nutrition", "weight loss", "fitness",
    "mental health", "sleep", "diabetes", "heart health",
]


class TrendCollector:
    def __init__(self):
        self.pytrends = TrendReq(hl="ar", tz=360)

    def get_google_trends(self, keywords: List[str] = None) -> List[Dict]:
        keywords = keywords or HEALTH_KEYWORDS[:5]
        trends = []
        try:
            self.pytrends.build_payload(
                keywords[:5],
                cat=0,
                timeframe="now 7-d",
                geo="",
                gprop="youtube",
            )
            related = self.pytrends.related_queries()
            for kw in keywords[:5]:
                if kw in related and related[kw].get("top") is not None:
                    top_df = related[kw]["top"]
                    for _, row in top_df.head(5).iterrows():
                        trends.append({
                            "title": row["query"],
                            "summary": f"ترند على Google Trends مرتبط بـ: {kw}",
                            "trend_score": float(row["value"]) / 100,
                            "source": "google_trends",
                            "keyword": kw,
                        })
        except Exception as e:
            logger.warning(f"Google Trends error: {e}")

        return trends

    def get_reddit_health_trends(self) -> List[Dict]:
        trends = []
        subreddits = ["health", "nutrition", "fitness", "HealthyFood", "loseit"]
        try:
            for sub in subreddits:
                url = f"https://www.reddit.com/r/{sub}/hot.json?limit=10"
                headers = {"User-Agent": "HealthIsFirstBot/1.0"}
                with httpx.Client(timeout=10) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        posts = data.get("data", {}).get("children", [])
                        for post in posts:
                            p = post.get("data", {})
                            score = p.get("score", 0)
                            if score > 100:
                                trends.append({
                                    "title": p.get("title", ""),
                                    "summary": p.get("selftext", "")[:500],
                                    "source_url": f"https://reddit.com{p.get('permalink', '')}",
                                    "trend_score": min(score / 10000, 1.0),
                                    "source": "reddit",
                                    "subreddit": sub,
                                })
        except Exception as e:
            logger.warning(f"Reddit collection error: {e}")
        return trends

    def collect_all_trends(self) -> List[Dict]:
        all_trends = []
        all_trends.extend(self.get_reddit_health_trends())
        try:
            all_trends.extend(self.get_google_trends())
        except Exception as e:
            logger.warning(f"Google trends skipped: {e}")
        logger.info(f"Collected {len(all_trends)} trends total")
        return all_trends
