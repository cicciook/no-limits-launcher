from __future__ import annotations

import re
import hashlib
import subprocess
import uuid
import os
from pathlib import Path

import requests
import minecraft_launcher_lib

from nolimits.core.instances import InstanceStore

API = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "NoLimitsLauncher/0.3.0 (desktop)"}
ROOT = Path.home() / ".no-limits-launcher"
GAME_DIR = ROOT / "game"
INSTANCES_DIR = ROOT / "instances"


def _safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9 _.-]", "", value).strip(" .")
    return value[:48] or "Modpack"


def install_modrinth_project(project_id: str, display_name: str, progress=None, icon_url: str | None = None) -> dict:
    report = progress or (lambda _value, _message: None)
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
    report(0, "Download del modpack…")
    with requests.get(pack_file["url"], headers=HEADERS, stream=True, timeout=(20, 120)) as download:
        download.raise_for_status()
        total = int(download.headers.get("content-length") or 0)
        received = 0
        with archive.open("wb") as out:
            for chunk in download.iter_content(1024 * 256):
                if chunk:
                    out.write(chunk)
                    received += len(chunk)
                    percent = int(received * 70 / total) if total else 0
                    report(min(70, percent), f"Download modpack… {received // (1024 * 1024)} MB")
    report(72, "Estrazione mod, configurazioni e loader…")
    info = minecraft_launcher_lib.mrpack.get_mrpack_information(str(archive))
    install_state = {"progress": 0, "maximum": 100}
    def set_status(message):
        report(72 + int(install_state["progress"] * 0.27), str(message))
    def set_max(value):
        install_state["maximum"] = max(1, int(value))
    def set_progress(value):
        install_state["progress"] = max(0, min(install_state["maximum"], int(value)))
        set_status("Installazione mod e loader…")
    minecraft_launcher_lib.mrpack.install_mrpack(
        str(archive), str(GAME_DIR), modpack_directory=str(instance_dir),
        callback={"setStatus": set_status, "setProgress": set_progress, "setMax": set_max},
    )
    launch_version = minecraft_launcher_lib.mrpack.get_mrpack_launch_version(str(archive))
    dependencies = info.get("dependencies", {})
    pack_loader = next((loader for key, loader in (("fabric", "fabric"), ("forge", "forge"), ("neoforge", "neoforge"), ("quilt", "quilt")) if dependencies.get(key)), "vanilla")
    item = store.add_instance(name, info.get("minecraftVersion", "sconosciuta"), pack_loader)
    item.update({"directory": str(instance_dir), "archive": str(archive), "launch_version": launch_version, "source": "modrinth", "project_id": project_id, "project_version_id": selected["id"], "icon_url": icon_url, "status": "installed"})
    store.update_instance(item["id"], item)
    report(100, "Installazione completata.")
    return item


def launch_instance(instance: dict, profile: dict | None = None, offline_username: str | None = None) -> subprocess.Popen:
    if profile and profile.get("access_token"):
        username = profile["name"]
        player_uuid = profile["id"]
        token = profile["access_token"]
        user_type = "msa"
    else:
        username = (offline_username or "").strip()
        if not username or len(username) > 16 or not re.fullmatch(r"[A-Za-z0-9_]+", username):
            raise RuntimeError("Inserisci un nome offline valido (1–16 caratteri: lettere, numeri e _).")
        player_uuid = str(uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + username).encode("utf-8")).digest(), version=3))
        token = ""
        user_type = "legacy"
    game_dir = Path(instance.get("directory", ""))
    if not game_dir.is_dir():
        raise RuntimeError("Cartella dell'istanza non trovata. Reinstalla il modpack.")
    version = instance.get("launch_version") or instance.get("minecraft_version")
    minecraft_launcher_lib.install.install_minecraft_version(version, str(GAME_DIR))
    options = {"username": username, "uuid": player_uuid, "token": token, "userType": user_type, "userProperties": "{}", "gameDirectory": str(game_dir), "launcherName": "No Limits Launcher", "launcherVersion": "0.3.0"}
    command = minecraft_launcher_lib.command.get_minecraft_command(version, str(GAME_DIR), options)
    kwargs = {"cwd": str(game_dir), "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True, "bufsize": 1, "errors": "replace"}
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        kwargs["stdin"] = subprocess.DEVNULL
    return subprocess.Popen(command, **kwargs)


def search_modrinth_content(query: str, content_type: str, limit: int = 60) -> list[dict]:
    if content_type not in ("mod", "shader"):
        raise ValueError("Tipo di contenuto non supportato.")
    params = {
        "query": query.strip(),
        "limit": max(1, min(limit, 100)),
        "index": "downloads" if not query.strip() else "relevance",
        "facets": __import__("json").dumps([[f"project_type:{content_type}"]]),
    }
    response = requests.get(f"{API}/search", params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return [{
        "id": hit.get("project_id"), "title": hit.get("title", "Senza nome"),
        "description": hit.get("description", ""), "author": hit.get("author", "Unknown"),
        "downloads": hit.get("downloads", 0), "icon_url": hit.get("icon_url"),
        "slug": hit.get("slug", ""), "project_type": content_type,
    } for hit in response.json().get("hits", [])]


def install_modrinth_content(instance: dict, project_id: str, content_type: str, progress=None) -> str:
    """Install one compatible Modrinth mod or shader into an existing instance."""
    import json
    from urllib.parse import urlparse
    report = progress or (lambda _value, _message: None)
    if content_type not in ("mod", "shader"):
        raise ValueError("Tipo di contenuto non supportato.")
    game_dir = Path(instance.get("directory", ""))
    if not game_dir.is_dir():
        raise RuntimeError("La cartella dell'istanza non esiste.")
    version = str(instance.get("minecraft_version", ""))
    loader = str(instance.get("loader", "vanilla")).lower()
    loaders = [loader] if loader in ("fabric", "forge", "neoforge", "quilt") else []
    params = {"game_versions": json.dumps([version])}
    if loaders and content_type == "mod":
        params["loaders"] = json.dumps(loaders)
    response = requests.get(f"{API}/project/{project_id}/version", params=params, headers=HEADERS, timeout=30)
    response.raise_for_status()
    versions = response.json()
    if not versions:
        raise RuntimeError("Nessuna versione compatibile con questa istanza. Controlla Minecraft e mod loader.")
    selected = versions[0]
    file_info = next((f for f in selected.get("files", []) if f.get("primary")), None) or (selected.get("files") or [None])[0]
    if not file_info or not file_info.get("url"):
        raise RuntimeError("Modrinth non ha fornito un file scaricabile.")
    folder = game_dir / ("mods" if content_type == "mod" else "shaderpacks")
    folder.mkdir(parents=True, exist_ok=True)
    filename = Path(urlparse(file_info["url"]).path).name or file_info.get("filename") or f"{project_id}.jar"
    destination = folder / filename
    report(5, f"Download {filename}…")
    with requests.get(file_info["url"], headers=HEADERS, stream=True, timeout=(20, 120)) as download:
        download.raise_for_status()
        total = int(download.headers.get("content-length") or 0)
        received = 0
        with destination.open("wb") as output:
            for chunk in download.iter_content(256 * 1024):
                if chunk:
                    output.write(chunk)
                    received += len(chunk)
                    report(min(99, 5 + int(received * 94 / total)) if total else 50, f"Download {filename}…")
    report(100, f"{filename} installato.")
    return str(destination)
