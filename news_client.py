# news_client.py
import os
import logging
import urllib.parse
from typing import List, Dict
from requests.adapters import HTTPAdapter
import requests
import feedparser
from urllib.parse import quote
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)


DEFAULT_MAX_ITEMS = 5

YANDEX_FEEDS = {
    "главные": "https://news.yandex.ru/index.rss",
    "спорт": "https://news.yandex.ru/sport.rss",
    "политика": "https://news.yandex.ru/politics.rss",
    "экономика": "https://news.yandex.ru/business.rss",
    "технологии": "https://news.yandex.ru/computers.rss",
    "культура": "https://news.yandex.ru/culture.rss",
    "наука": "https://news.yandex.ru/science.rss",
}
UA = "Mozilla/5.0"


class NewsClient:
    def __init__(self):
        self.max_items = int(os.getenv("NEWS_MAX_ITEMS", str(DEFAULT_MAX_ITEMS)))

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

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
                source = (feed.feed.get("title") if isinstance(feed.feed, dict) else None) or "Новости"
                items.append({"title": title, "link": link, "source": source})
            return items
        except Exception as ex:
            log.warning(f"[news] parse failed for {url}: {ex}")
            return []

    # -------- Яндекс --------
    def yandex_top(self) -> List[Dict]:
        return self._parse(YANDEX_FEEDS["главные"])

    def yandex_category(self, cat: str) -> List[Dict]:
        url = YANDEX_FEEDS.get(cat.lower())
        if not url:
            return []
        return self._parse(url)

    # -------- Google/Bing --------
    def google_search(self, query: str) -> List[Dict]:
        url = f"https://news.google.com/rss/search?q={quote(query)}&hl=ru&gl=RU&ceid=RU:ru"
        return self._parse(url)

    def bing_search(self, query: str) -> List[Dict]:
        url = f"https://www.bing.com/news/search?q={quote(query)}&format=rss"
        return self._parse(url)

    # -------- Публичный интерфейс --------
    def top(self) -> List[Dict]:
        return self.yandex_top()

    def category(self, cat: str) -> List[Dict]:
        return self.yandex_category(cat)

    def search(self, query: str) -> List[Dict]:
        items = self.google_search(query)
        if not items:
            items = self.bing_search(query)
        return items



