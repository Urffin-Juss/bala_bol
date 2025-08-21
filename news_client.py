# news_client.py
import os
import urllib.parse
import feedparser
from typing import List, Dict

class NewsClient:
    def __init__(self):
        self.max_items = int(os.getenv("NEWS_MAX_ITEMS", "5"))
        self.region = os.getenv("NEWS_REGION", "ru")
        self.lang = os.getenv("NEWS_LANG", "ru")
        self.sources = [s.strip() for s in os.getenv("NEWS_SOURCES", "google").split(",") if s.strip()]

    # --- Google News RSS ---
    # топ: https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru
    # поиск: https://news.google.com/rss/search?q=запрос&hl=ru&gl=RU&ceid=RU:ru
    def _google_feed_top(self) -> str:
        ceid = f"{self.region.upper()}:{self.lang}"
        return f"https://news.google.com/rss?hl={self.lang}&gl={self.region.upper()}&ceid={ceid}"

    def _google_feed_search(self, query: str) -> str:
        ceid = f"{self.region.upper()}:{self.lang}"
        q = urllib.parse.quote(query)
        return f"https://news.google.com/rss/search?q={q}&hl={self.lang}&gl={self.region.upper()}&ceid={ceid}"

    # Доп. источники (опционально):
    def _bbc_ru(self) -> str:
        return "https://feeds.bbci.co.uk/russian/rss.xml"
    def _dw_ru(self) -> str:
        return "https://rss.dw.com/rdf/rss-ru-all"

    def _parse(self, url: str) -> List[Dict]:
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[: self.max_items]:
            items.append({
                "title": (e.title or "").strip(),
                "link": (e.link or "").strip(),
                "source": (feed.feed.get("title") or "News").strip()
            })
        return items

    def top(self) -> List[Dict]:
        items: List[Dict] = []
        if "google" in self.sources:
            items += self._parse(self._google_feed_top())
        if "bbc" in self.sources:
            items += self._parse(self._bbc_ru())
        if "dw" in self.sources:
            items += self._parse(self._dw_ru())
        # ограничим общее число
        return items[: self.max_items]

    def search(self, query: str) -> List[Dict]:
        if not query:
            return self.top()
        items: List[Dict] = []
        if "google" in self.sources:
            items += self._parse(self._google_feed_search(query))
        # Можно добавить поиск по другим, если нужно
        return items[: self.max_items]
