import os
import requests
from typing import Optional, Dict, Any, List



CITY_MAP = {
    "москва": "Moscow",
    "санкт-петербург": "Saint Petersburg",
    "питер": "Saint Petersburg",
    "нижний новгород": "Nizhny Novgorod",
    "екатеринбург": "Ekaterinburg",
    "новосибирск": "Novosibirsk",
    "казань": "Kazan",
    "самара": "Samara",
    "волгоград": "Volgograd",
    "ростов-на-дону": "Rostov-on-Don",
}
"""
class MeteoRFError(Exception):
    pass

class MeteoRFClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or os.getenv("METEORF_API_BASE") or "http://api-core.meteorf.ru").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: Dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        r = self.session.get(url, params=params or {}, timeout=12)
        r.raise_for_status()
        return r.json()

    # --- поиск станций по подстроке имени ---
    def search_stations(self, city: str) -> list[dict]:
        """
        Поиск станций через /api/v1/station/by/name/contains и .../starts.
        Возвращает список словарей: {"code", "name", "locale_name", "lat", "lon"}.
        """
        city = (city or "").strip()
        if not city:
            return []

        # простая мапа кириллицы → латиницы (можно дополнять)
        CITY_MAP = {
            "москва": "Moscow",
            "санкт-петербург": "Saint Petersburg",
            "питер": "Saint Petersburg",
            "нижний новгород": "Nizhny Novgorod",
            "екатеринбург": "Ekaterinburg",
            "новосибирск": "Novosibirsk",
            "казань": "Kazan",
            "самара": "Samara",
            "волгоград": "Volgograd",
            "ростов-на-дону": "Rostov-on-Don",
        }

        # варианты запроса, которые попробуем по очереди
        variants = []
        # 1) как ввели
        variants.append(city)
        # 2) Capitalize + Title (часто помогает)
        variants.append(city.capitalize())
        variants.append(city.title())
        # 3) маппинг рус -> eng (если есть)
        mapped = CITY_MAP.get(city.lower())
        if mapped:
            variants.append(mapped)

        def _normalize(resp):
            if not isinstance(resp, list):
                return []
            out = []
            for it in resp:
                if not isinstance(it, dict):
                    continue
                code = it.get("code")
                if not code:
                    continue
                out.append({
                    "code": str(code),
                    "name": it.get("name"),
                    "locale_name": it.get("locale_name") or it.get("locale_name_p"),
                    "lat": it.get("latitude"),
                    "lon": it.get("longitude"),
                })
            return out

        # перебор эндпоинтов и вариантов написания
        tried = set()
        for q in variants:
            if not q or q in tried:
                continue
            tried.add(q)
            for path in ("/api/v1/station/by/name/contains", "/api/v1/station/by/name/starts"):
                try:
                    self.session.headers.update({"Accept": "application/json"})
                    data = self._get(path, {"name": q})
                    stations = _normalize(data)
                    logger = globals().get("logger")  # если logger есть в модуле handlers
                    if logger:
                        logger.debug(f"[MeteoRF] station search: {path}?name={q} -> {len(stations)}")
                    if stations:
                        return stations
                except Exception:
                    # пробуем следующий вариант
                    continue

        return []

    # --- прогноз на дни по коду станции ---
    def forecast_daily(self, code: str) -> Dict[str, Any]:
        """
        GET /api/v1/forecast/daily/{code}
        Возвращает прогноз на несколько дней. Формат уточняется по Swagger, поэтому отдаём raw.
        """
        return self._get(f"/api/v1/forecast/daily/{code}")

    # (опционально)
    def forecast_weekly(self, code: str) -> Dict[str, Any]:
        return self._get(f"/api/v1/forecast/weekly/{code}")

    def search_stations(self, name: str) -> List[Dict[str, Any]]:
        data = self._get("/api/v1/station/by/name/contains", {"name": name})
        if not isinstance(data, list):
            return []
        return [{
            "name": it.get("name"),
            "locale_name": it.get("locale_name") or it.get("locale_name_p"),
            "code": str(it.get("code")),
            "lat": it.get("latitude"),
            "lon": it.get("longitude")
        } for it in data if it.get("code")]
                                                """

