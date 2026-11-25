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

    def get_instance(self, instance_id: str) -> dict | None:
        return next((item for item in self.list_instances() if item.get("id") == instance_id), None)

    def name_taken(self, name: str, ignore_id: str | None = None) -> bool:
        wanted = name.strip().casefold()
        return any(item.get("name", "").casefold() == wanted and item.get("id") != ignore_id for item in self.list_instances())

    def duplicate_instance(self, instance_id: str, new_name: str, progress=None) -> dict:
        """Copia istanza e cartella (può essere lenta: da chiamare fuori dal thread dell'interfaccia)."""
        import shutil
        from nolimits.core.runtime import new_instance_dir
        source = self.get_instance(instance_id)
        if source is None:
            raise KeyError(instance_id)
        new_name = new_name.strip()
        if not new_name:
            raise ValueError("Il nome dell'istanza non può essere vuoto.")
        if self.name_taken(new_name):
            raise ValueError("Esiste già un'istanza con questo nome.")
        copy = dict(source)
        copy.pop("import_warnings", None)
        origin = Path(source.get("directory") or "")
        if origin.is_dir():
            target = new_instance_dir(new_name)
            (progress or (lambda *_: None))(10, "Copia dei file dell'istanza…")
            shutil.copytree(origin, target, dirs_exist_ok=True)
            copy["directory"] = str(target)
        copy.update({"id": f"instance-{int(datetime.now(timezone.utc).timestamp() * 1000)}", "name": new_name,
                     "created_at": datetime.now(timezone.utc).isoformat()})
        items = self.list_instances()
        items.append(copy)
        self._write(items)
        return copy

    def update_instance(self, instance_id: str, updated: dict) -> None:
        items = self.list_instances()
        for index, item in enumerate(items):
            if item.get("id") == instance_id:
                items[index] = updated
                self._write(items)
                return
        raise KeyError(instance_id)

    def remove_instance(self, instance_id: str) -> None:
        items = self.list_instances()
        remaining = [item for item in items if item.get("id") != instance_id]
        if len(remaining) == len(items):
            raise KeyError(instance_id)
        self._write(remaining)

    def _write(self, items):
        self.path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_instance(self, name: str, minecraft_version: str, loader: str = "vanilla") -> dict:
        name = name.strip()
        if not name:
            raise ValueError("Il nome dell'istanza non può essere vuoto.")
        items = self.list_instances()
        if any(item.get("name", "").casefold() == name.casefold() for item in items):
            raise ValueError("Esiste già un'istanza con questo nome.")
        item = {"id": f"instance-{int(datetime.now(timezone.utc).timestamp() * 1000)}", "name": name, "minecraft_version": minecraft_version.strip(), "loader": loader.lower(), "created_at": datetime.now(timezone.utc).isoformat(), "status": "not_installed"}
        items.append(item)
        self._write(items)
        return item
