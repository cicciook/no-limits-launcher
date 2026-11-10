from .base import ModpackProvider

class CurseForgeProvider(ModpackProvider):
    provider_id = "curseforge"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    def search_modpacks(self, query: str, limit: int = 20) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("CurseForge richiede una API key autorizzata. Configurarla nelle impostazioni prima di abilitare il provider.")
        raise NotImplementedError("CurseForge API adapter: planned milestone.")
