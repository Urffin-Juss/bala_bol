# meteorf_client.py
import os
import requests
from typing import Optional, Dict, Any, List

class MeteoRFError(Exception):
    pass

class MeteoRFClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = (base_url or os.getenv("METEORF_API_BASE") or "http://api-core.meteorf.ru").rstrip("/")
        self.api_key = api_key or os.getenv("METEORF_API_KEY")

        self.session = requests.Session()
        if self.api_key:
            self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self.session.headers.update({"Accept": "application/json"})

    def _get(self, path: str, params: Dict[str, Any]) -> Any:
        url = f"{self.base_url}{path}"
        r = self.session.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def search_settlement(self, name: str) -> List[Dict[str, Any]]:
        """
        ⚠️ Подставь реальный путь из swagger! (пример: /api/settlements/search)
        """
        data = self._get("/api/settlements/search", {"name": name})
        return [
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "region": item.get("region")
            }
            for item in data
        ]

    def get_forecast(self, settlement_id: Any) -> Dict[str, Any]:
        """
        ⚠️ Подставь реальный путь из swagger! (пример: /api/forecast/settlement/{id})
        """
        raw = self._get(f"/api/forecast/settlement/{settlement_id}", {"hours": 24, "days": 3})
        return raw
