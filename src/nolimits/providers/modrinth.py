import requests
from .base import ModpackProvider


class ModrinthProvider(ModpackProvider):
    provider_id = "modrinth"
    API = "https://api.modrinth.com/v2"
    HEADERS = {"User-Agent": "NoLimitsLauncher/0.3.0 (desktop)"}

    def search_modpacks(self, query: str = "", limit: int = 100) -> list[dict]:
        # A catalog opened without a query should show popular packs, not an empty search.
        params = {
            "query": query.strip(),
            "limit": max(1, min(limit, 100)),
            "offset": 0,
            "facets": '[["project_type:modpack"]]',
            "index": "downloads" if not query.strip() else "relevance",
        }
        response = requests.get(
            f"{self.API}/search", params=params, headers=self.HEADERS, timeout=30
        )
        response.raise_for_status()
        payload = response.json()
        packs = []
        for hit in payload.get("hits", []):
            packs.append({
                "id": hit.get("project_id"),
                "title": hit.get("title", "Untitled"),
                "description": hit.get("description", ""),
                "author": hit.get("author", "Unknown"),
                "downloads": hit.get("downloads", 0),
                "icon_url": hit.get("icon_url"),
                "source": self.provider_id,
                "slug": hit.get("slug", ""),
                "categories": hit.get("categories", []),
                "versions": hit.get("versions", []),
                "date_modified": hit.get("date_modified", ""),
                "project_url": f"https://modrinth.com/modpack/{hit.get('slug', '')}",
            })
        return packs
