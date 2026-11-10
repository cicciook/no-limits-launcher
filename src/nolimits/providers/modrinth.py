import requests
from .base import ModpackProvider

class ModrinthProvider(ModpackProvider):
    provider_id = "modrinth"
    API = "https://api.modrinth.com/v2"

    def search_modpacks(self, query: str, limit: int = 20) -> list[dict]:
        params = {"query": query, "limit": max(1, min(limit, 100)), "facets": '[["project_type:modpack"]]', "index": "relevance"}
        response = requests.get(f"{self.API}/search", params=params, headers={"User-Agent": "NoLimitsLauncher/0.1.0 (desktop prototype)"}, timeout=20)
        response.raise_for_status()
        payload = response.json()
        return [{"id": hit.get("project_id"), "title": hit.get("title", "Untitled"), "description": hit.get("description", ""), "author": hit.get("author", "Unknown"), "downloads": hit.get("downloads", 0), "icon_url": hit.get("icon_url"), "source": self.provider_id, "slug": hit.get("slug", "")} for hit in payload.get("hits", [])]
