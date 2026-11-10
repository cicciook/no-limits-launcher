import json
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path.home() / ".no-limits-launcher"
INSTANCES_FILE = DATA_DIR / "instances.json"

class InstanceStore:
    def __init__(self, path: Path = INSTANCES_FILE):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def list_instances(self) -> list[dict]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    def add_instance(self, name: str, minecraft_version: str, loader: str = "vanilla") -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Il nome dell'istanza non può essere vuoto.")
        items = self.list_instances()
        if any(item.get("name", "").casefold() == name.casefold() for item in items):
            raise ValueError("Esiste già un'istanza con questo nome.")
        item = {"id": f"instance-{int(datetime.now(timezone.utc).timestamp() * 1000)}", "name": name, "minecraft_version": minecraft_version.strip(), "loader": loader.lower(), "created_at": datetime.now(timezone.utc).isoformat(), "status": "not_installed"}
        items.append(item)
        self.path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
        return item
