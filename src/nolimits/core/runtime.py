"""Installazione di Minecraft e dei mod loader, condivisa da import, creazione e modifica delle istanze."""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import minecraft_launcher_lib

ROOT = Path.home() / ".no-limits-launcher"
GAME_DIR = ROOT / "game"
INSTANCES_DIR = ROOT / "instances"
LOADERS = ("vanilla", "fabric", "forge", "neoforge", "quilt")

# chiave in modrinth.index.json -> loader
_MRPACK_LOADER_KEYS = (
    ("fabric-loader", "fabric"), ("fabric", "fabric"),
    ("quilt-loader", "quilt"), ("quilt", "quilt"),
    ("neoforge", "neoforge"), ("forge", "forge"),
)
# uid dei componenti in mmc-pack.json (Prism / MultiMC) -> loader
PRISM_LOADER_UIDS = {
    "net.fabricmc.fabric-loader": "fabric",
    "org.quiltmc.quilt-loader": "quilt",
    "net.minecraftforge": "forge",
    "net.neoforged": "neoforge",
}


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9 _.-]", "", str(value)).strip(" .")
    return value[:48] or "Modpack"


def dir_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", safe_name(name))


def new_instance_dir(name: str) -> Path:
    """Crea e restituisce una cartella istanza libera (aggiunge -2, -3… se il nome è già usato)."""
    base = INSTANCES_DIR / dir_name(name)
    candidate, number = base, 2
    while candidate.exists():
        candidate = Path(f"{base}-{number}")
        number += 1
    candidate.mkdir(parents=True)
    return candidate


def read_mrpack_index(archive) -> dict:
    with zipfile.ZipFile(archive) as bundle:
        return json.loads(bundle.read("modrinth.index.json"))


def loader_from_dependencies(dependencies: dict) -> tuple[str, str]:
    """Da `dependencies` di un .mrpack restituisce (loader, versione del loader)."""
    for key, loader in _MRPACK_LOADER_KEYS:
        if dependencies.get(key):
            return loader, str(dependencies[key])
    return "vanilla", ""


def parse_loader_id(value: str) -> tuple[str, str]:
    """'forge-47.2.0' (formato CurseForge) -> ('forge', '47.2.0')."""
    loader, _, version = str(value).partition("-")
    loader = loader.lower()
    return (loader, version) if loader in LOADERS else ("vanilla", "")


def progress_callback(report, base: int, span: int, text: str) -> dict:
    """Adatta il `callback` di minecraft-launcher-lib a `report(percentuale, messaggio)` su un intervallo."""
    state = {"max": 1, "text": text}

    def set_status(message):
        state["text"] = str(message)
        report(base, state["text"])

    def set_max(value):
        state["max"] = max(1, int(value))

    def set_progress(value):
        done = max(0, min(state["max"], int(value)))
        report(base + int(span * done / state["max"]), state["text"])

    return {"setStatus": set_status, "setMax": set_max, "setProgress": set_progress}


def install_runtime(minecraft_version: str, loader: str = "vanilla", loader_version: str | None = None, progress=None) -> str:
    """Scarica Minecraft (e il mod loader) in GAME_DIR e restituisce l'id della versione da avviare."""
    report = progress or (lambda _value, _message: None)
    loader = (loader or "vanilla").lower()
    if loader not in LOADERS:
        raise ValueError(f"Mod loader non supportato: {loader}")
    minecraft_version = str(minecraft_version).strip()
    if not minecraft_version:
        raise ValueError("Indica la versione di Minecraft.")
    GAME_DIR.mkdir(parents=True, exist_ok=True)

    if loader == "vanilla":
        minecraft_launcher_lib.install.install_minecraft_version(
            minecraft_version, str(GAME_DIR),
            callback=progress_callback(report, 0, 100, f"Download di Minecraft {minecraft_version}…"),
        )
        return minecraft_version

    mod_loader = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
    if not mod_loader.is_minecraft_version_supported(minecraft_version):
        raise RuntimeError(f"{mod_loader.get_name()} non supporta Minecraft {minecraft_version}.")
    # install() scarica anche Minecraft se manca e restituisce l'id della versione da avviare
    installed = mod_loader.install(
        minecraft_version, str(GAME_DIR),
        loader_version=(loader_version or None),
        callback=progress_callback(report, 0, 100, f"Installazione di {mod_loader.get_name()}…"),
    )
    if not installed:
        installed = mod_loader.get_installed_version(
            minecraft_version, loader_version or mod_loader.get_latest_loader_version(minecraft_version)
        )
    return str(installed)


def install_instance(instance: dict, progress=None) -> dict:
    """Prepara cartella, Minecraft e loader di un'istanza; restituisce il dict aggiornato (status=installed).

    Non scrive su instances.json: lo fa chi chiama, dal thread dell'interfaccia.
    """
    result = dict(instance)
    directory = Path(result.get("directory") or "")
    if not str(directory) or str(directory) == ".":
        directory = new_instance_dir(result.get("name", "Istanza"))
    directory.mkdir(parents=True, exist_ok=True)
    result["launch_version"] = install_runtime(
        result.get("minecraft_version", ""), result.get("loader", "vanilla"), result.get("loader_version") or None, progress
    )
    result["directory"] = str(directory)
    result["status"] = "installed"
    (progress or (lambda *_: None))(100, "Istanza pronta.")
    return result
