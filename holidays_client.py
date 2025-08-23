# holidays_client.py
import os
import logging
from datetime import datetime, timedelta, date
from typing import List, Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

DEFAULT_COUNTRY = "RU"   # ISO-3166-1 alpha-2
UA = "Mozilla/5.0"

# Дополнительные «знаковые» даты (если вдруг не придут из API)
EXTRA_OBSERVANCES = {
    # month-day : [titles]
    "01-25": ["Татьянин день (День студента)"],
    "02-23": ["День защитника Отечества"],
    "03-08": ["Международный женский день"],
    "04-12": ["День космонавтики"],
    "05-01": ["Праздник Весны и Труда"],
    "05-09": ["День Победы"],
    "06-12": ["День России"],
    "11-04": ["День народного единства"],
    # Новый год и Рождество обычно придут из API, но подстрахуемся
    "01-01": ["Новый год"],
    "01-07": ["Рождество Христово (РПЦ)"],
}

def programmers_day_titles(d: date) -> Optional[List[str]]:
    # 256-й день года (13 сентября, в високосный — 12 сентября)
    year_start = date(d.year, 1, 1)
    day_256 = year_start + timedelta(days=255)
    if d == day_256:
        return ["День программиста"]
    return None


class HolidaysClient:
    def __init__(self, country: Optional[str] = None):
        self.country = (country or os.getenv("HOLIDAYS_COUNTRY", DEFAULT_COUNTRY)).upper()
        self.timeout = int(os.getenv("HOLIDAYS_TIMEOUT", "12"))
        self.retries = int(os.getenv("HOLIDAYS_RETRIES", "2"))

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA, "Accept": "application/json"})
        retry = Retry(total=self.retries, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

        self.cache: Dict[int, List[Dict]] = {}  # year -> list of holidays

    def _fetch_year(self, year: int) -> List[Dict]:
        if year in self.cache:
            return self.cache[year]
        url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/{self.country}"
        try:
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            data = r.json()
            if isinstance(data, list):
                self.cache[year] = data
                return data
        except Exception as ex:
            log.warning(f"[holidays] fetch failed for {year}/{self.country}: {ex}")
        self.cache[year] = []
        return []

    def on_date(self, d: date) -> List[str]:
        items = []
        year_holidays = self._fetch_year(d.year)
        # Nager.Date возвращает isoDate "YYYY-MM-DD"
        for h in year_holidays:
            if h.get("date") == d.isoformat():
                name = h.get("localName") or h.get("name")
                if name:
                    items.append(name)

        # Дополнительные общеизвестные даты
        key = d.strftime("%m-%d")
        items.extend(EXTRA_OBSERVANCES.get(key, []))
        pd = programmers_day_titles(d)
        if pd:
            items.extend(pd)

        # Уникализируем и отсортируем по длине (краткие вперёд)
        uniq = []
        seen = set()
        for t in items:
            if t not in seen:
                uniq.append(t); seen.add(t)
        return sorted(uniq, key=len)

    def today(self, tz_offset_hours: int = 0) -> List[str]:
        now = datetime.utcnow() + timedelta(hours=tz_offset_hours)
        return self.on_date(now.date())

    def relative(self, days: int, tz_offset_hours: int = 0) -> List[str]:
        now = datetime.utcnow() + timedelta(hours=tz_offset_hours)
        return self.on_date((now + timedelta(days=days)).date())
