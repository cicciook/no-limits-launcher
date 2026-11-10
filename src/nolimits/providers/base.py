from abc import ABC, abstractmethod

class ModpackProvider(ABC):
    provider_id: str

    @abstractmethod
    def search_modpacks(self, query: str, limit: int = 20) -> list[dict]:
        raise NotImplementedError
