from __future__ import annotations

import re
import subprocess
from pathlib import Path

import requests
import minecraft_launcher_lib

from nolimits.core.instances import InstanceStore

API = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "NoLimitsLauncher/0.2.0 (desktop)"}
ROOT = Path.home() / ".no-limits-launcher"
GAME_DIR = ROOT / "game"
INSTANCES_DIR = ROOT / "instances"


def _safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9 _.-]", "", value).strip(" .")
    return value[:48] or "Modpack"


def install_modrinth_project(project_id: str, display_name: str, progress=None) -> dict:
    report = progress or (lambda _message: None)
    response = requests.get(f"{API}/project/{project_id}/version", headers=HEADERS, timeout=30)
    response.raise_for_status()
    versions = response.json()
    selected = next((v for v in versions if any(f.get("primary") and f.get("filename", "").endswith(".mrpack") for f in v.get("files", []))), None)
    if selected is None:
        selected = next((v for v in versions if any(f.get("filename", "").endswith(".mrpack") for f in v.get("files", []))), None)
    if selected is None:
        raise RuntimeError("Questo progetto non pubblica un file .mrpack installabile.")
    pack_file = next((f for f in selected["files"] if f.get("filename", "").endswith(".mrpack") and f.get("primary")), None)
    if pack_file is None:
        pack_file = next(f for f in selected["files"] if f.get("filename", "").endswith(".mrpack"))
    name = _safe_name(display_name)
    store = InstanceStore()
    used = {x.get("name", "").casefold() for x in store.list_instances()}
    if name.casefold() in used:
        name = _safe_name(f"{name} {selected.get('version_number', '')}")
    instance_dir = INSTANCES_DIR / re.sub(r"[^a-zA-Z0-9_.-]", "_", name)
    instance_dir.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "downloads" / f"{project_id}-{selected['id']}.mrpack"
    archive.parent.mkdir(parents=True, exist_ok=True)
    report("Download del modpack…")
    with requests.get(pack_file["url"], headers=HEADERS, stream=True, timeout=(20, 120)) as download:
        download.raise_for_status()
        with archive.open("wb") as out:
            for chunk in download.iter_content(1024 * 256):
                if chunk:
                    out.write(chunk)
    report("Installazione mod, configurazioni e loader…")
    info = minecraft_launcher_lib.mrpack.get_mrpack_information(str(archive))
    minecraft_launcher_lib.mrpack.install_mrpack(str(archive), str(GAME_DIR), modpack_directory=str(instance_dir), callback={"setStatus": report})
    launch_version = minecraft_launcher_lib.mrpack.get_mrpack_launch_version(str(archive))
    item = store.add_instance(name, info.get("minecraftVersion", "sconosciuta"), "modpack")
    item.update({"directory": str(instance_dir), "archive": str(archive), "launch_version": launch_version, "source": "modrinth", "project_id": project_id, "project_version_id": selected["id"], "status": "installed"})
    store.update_instance(item["id"], item)
    report("Installazione completata.")
    return item


def launch_instance(instance: dict, profile: dict) -> subprocess.Popen:
    if not profile or not profile.get("access_token"):
        raise RuntimeError("Accedi prima con un account Microsoft che possiede Minecraft Java Edition.")
    game_dir = Path(instance.get("directory", ""))
    if not game_dir.is_dir():
        raise RuntimeError("Cartella dell'istanza non trovata. Reinstalla il modpack.")
    version = instance.get("launch_version") or instance.get("minecraft_version")
    minecraft_launcher_lib.install.install_minecraft_version(version, str(GAME_DIR))
    options = {"username": profile["name"], "uuid": profile["id"], "token": profile["access_token"], "gameDirectory": str(game_dir), "launcherName": "No Limits Launcher", "launcherVersion": "0.2.0"}
    command = minecraft_launcher_lib.command.get_minecraft_command(version, str(GAME_DIR), options)
    return subprocess.Popen(command, cwd=str(game_dir))
