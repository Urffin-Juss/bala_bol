# news_client.py
import os
import logging
import urllib.parse
from typing import List, Dict

import requests
import feedparser

log = logging.getLogger(__name__)

DEFAULT_MAX_ITEMS = 5
DEFAULT_REGION = "ru"
DEFAULT_LANG = "ru"
DEFAULT_SOURCES = "google"  # csv: google,bbc,dw

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"


class NewsClient:
    def __init__(self):
        self.max_items = int(os.getenv("NEWS_MAX_ITEMS", str(DEFAULT_MAX_ITEMS)))
        self.region = os.getenv("NEWS_REGION", DEFAULT_REGION)
        self.lang = os.getenv("NEWS_LANG", DEFAULT_LANG)
        self.sources = [s.strip() for s in os.getenv("NEWS_SOURCES", DEFAULT_SOURCES).split(",") if s.strip()]

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept": "text/xml,application/rss+xml,application/xml;q=0.9,*/*;q=0.8"})

    # ---------- Google News ----------
    # топ:    https://news.google.com/rss?hl=ru&gl=RU&ceid=RU:ru
    # поиск:  https://news.google.com/rss/search?q=запрос&hl=ru&gl=RU&ceid=RU:ru
    def _google_feed_top(self) -> str:
        ceid = f"{self.region.upper()}:{self.lang}"
        return f"https://news.google.com/rss?hl={self.lang}&gl={self.region.upper()}&ceid={ceid}"

    def _google_feed_search(self, query: str) -> str:
        ceid = f"{self.region.upper()}:{self.lang}"
        q = urllib.parse.quote(query)
        return f"https://news.google.com/rss/search?q={q}&hl={self.lang}&gl={self.region.upper()}&ceid={ceid}"

    # ---------- Дополнительные ленты (по желанию) ----------
    def _bbc_ru(self) -> str:
        return "https://feeds.bbci.co.uk/russian/rss.xml"

    def _dw_ru(self) -> str:
        return "https://rss.dw.com/rdf/rss-ru-all"

    # ---------- Универсальный парсер ----------
    def _parse(self, url: str) -> List[Dict]:
        try:
            r = self.session.get(url, timeout=12)
            r.raise_for_status()
            feed = feedparser.parse(r.text)
            items = []
            for e in feed.entries[: self.max_items]:
                title = (getattr(e, "title", "") or "").strip()
                link = (getattr(e, "link", "") or "").strip()
                if not title or not link:
                    continue
                source = (feed.feed.get("title") if isinstance(feed.feed, dict) else None) or "News"
                items.append({"title": title, "link": link, "source": source})
            log.debug(f"[news] parsed {len(items)} items from {url}")
            return items
        except Exception as ex:
            log.warning(f"[news] parse failed for {url}: {ex}")
            return []

    # ---------- Публичные методы ----------
    def top(self) -> List[Dict]:
        items: List[Dict] = []
        if "google" in self.sources:
            items += self._parse(self._google_feed_top())
        if "bbc" in self.sources:
            items += self._parse(self._bbc_ru())
        if "dw" in self.sources:
            items += self._parse(self._dw_ru())
        # оставим не больше заданного лимита
        return items[: self.max_items] if items else []

    def search(self, query: str) -> List[Dict]:
        query = (query or "").strip()
        if not query:
            return self.top()
        items: List[Dict] = []
        if "google" in self.sources:
            items += self._parse(self._google_feed_search(query))
        return items[: self.max_items] if items else []
