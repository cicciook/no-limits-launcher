"""Import di modpack da file o link, come su Prism Launcher.

Formati riconosciuti dal contenuto dello ZIP (non dall'estensione):
  - Modrinth        .mrpack  (contiene modrinth.index.json)
  - CurseForge      .zip     (contiene manifest.json)
  - Prism/MultiMC   .zip     (contiene instance.cfg e mmc-pack.json)
Sono accettati anche link a una pagina modpack di Modrinth e link diretti a questi file.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
import minecraft_launcher_lib

from nolimits.core.instances import InstanceStore
from nolimits.core.modpacks import API, HEADERS, install_modrinth_project
from nolimits.core.runtime import (
    GAME_DIR, PRISM_LOADER_UIDS, ROOT, install_runtime, loader_from_dependencies,
    new_instance_dir, parse_loader_id, progress_callback, read_mrpack_index,
)

FORMAT_MODRINTH, FORMAT_CURSEFORGE, FORMAT_PRISM = "modrinth", "curseforge", "prism"
FORMAT_LABELS = {FORMAT_MODRINTH: "Modrinth (.mrpack)", FORMAT_CURSEFORGE: "CurseForge (.zip)", FORMAT_PRISM: "Prism / MultiMC (.zip)"}
_MODRINTH_PAGE = re.compile(r"https?://(?:www\.)?modrinth\.com/(?:modpack|project)/([^/?#]+)", re.I)


# ------------------------------------------------------------------ utilità
def scaled(report, base: int, span: int):
    """Mappa un `report` 0-100 sull'intervallo [base, base+span]."""
    return lambda value, message: report(base + int(max(0, min(100, value)) * span / 100), message)


def unique_name(store: InstanceStore, wanted: str) -> str:
    wanted = (wanted or "Modpack").strip() or "Modpack"
    used = {item.get("name", "").casefold() for item in store.list_instances()}
    candidate, number = wanted, 2
    while candidate.casefold() in used:
        candidate = f"{wanted} ({number})"
        number += 1
    return candidate


def extract_prefix(bundle: zipfile.ZipFile, prefix: str, destination: Path, skip_dirs=()) -> int:
    """Estrae le voci sotto `prefix` in `destination`, ignorando percorsi che escono dalla cartella (zip-slip)."""
    destination = destination.resolve()
    count = 0
    for info in bundle.infolist():
        if not info.filename.startswith(prefix) or info.is_dir():
            continue
        relative = info.filename[len(prefix):]
        if not relative or relative.split("/")[0] in skip_dirs:
            continue
        target = (destination / relative).resolve()
        if not target.is_relative_to(destination):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with bundle.open(info) as source, open(target, "wb") as output:
            shutil.copyfileobj(source, output)
        count += 1
    return count


def _filename_from_response(response, url: str) -> str:
    disposition = response.headers.get("content-disposition", "")
    match = re.search(r"filename\*?=(?:UTF-8'')?\"?([^\";]+)", disposition, re.I)
    name = unquote(match.group(1)) if match else unquote(Path(urlparse(url).path).name)
    return re.sub(r"[^\w .()\[\]+-]", "_", Path(name).name) or "import.zip"


def _download(url: str, report) -> Path:
    folder = ROOT / "downloads"
    folder.mkdir(parents=True, exist_ok=True)
    report(0, "Download del file…")
    with requests.get(url, headers=HEADERS, stream=True, timeout=(20, 120)) as response:
        response.raise_for_status()
        destination = folder / _filename_from_response(response, response.url or url)
        total = int(response.headers.get("content-length") or 0)
        received = 0
        with destination.open("wb") as output:
            for chunk in response.iter_content(256 * 1024):
                if chunk:
                    output.write(chunk)
                    received += len(chunk)
                    report(int(received * 100 / total) if total else 50, f"Download… {received // (1024 * 1024)} MB")
    return destination


def detect_format(archive) -> str:
    """Riconosce il tipo di modpack guardando dentro lo ZIP."""
    try:
        bundle = zipfile.ZipFile(archive)
    except zipfile.BadZipFile as exc:
        raise ValueError("Il file non è un archivio ZIP valido.") from exc
    with bundle:
        names = bundle.namelist()
        if "modrinth.index.json" in names:
            return FORMAT_MODRINTH
        if "manifest.json" in names:
            try:
                manifest = json.loads(bundle.read("manifest.json"))
            except ValueError:
                manifest = {}
            if isinstance(manifest, dict) and "minecraft" in manifest and "files" in manifest:
                return FORMAT_CURSEFORGE
        if any(name.endswith("instance.cfg") for name in names) or any(name.endswith("mmc-pack.json") for name in names):
            return FORMAT_PRISM
    raise ValueError("Formato non riconosciuto. Sono supportati .mrpack (Modrinth) e .zip di CurseForge, Prism o MultiMC.")


def _register(name, minecraft_version, loader, loader_version, directory, launch_version, source, extra=None) -> dict:
    store = InstanceStore()
    item = store.add_instance(unique_name(store, name), minecraft_version or "sconosciuta", loader)
    item.update({
        "directory": str(directory), "launch_version": launch_version,
        "loader_version": loader_version or "", "source": source, "status": "installed",
    })
    if extra:
        item.update(extra)
    store.update_instance(item["id"], item)
    return item


# --------------------------------------------------------------- entry point
def import_modpack(source, name: str | None = None, progress=None, curseforge_api_key: str | None = None) -> dict:
    """Importa un modpack da percorso locale o URL e restituisce la nuova istanza."""
    report = progress or (lambda _value, _message: None)
    source = str(source).strip().strip("\"'")
    if not source:
        raise ValueError("Indica un file o un link da importare.")
    name = (name or "").strip() or None

    if re.match(r"https?://", source, re.I):
        page = _MODRINTH_PAGE.match(source)
        if page:
            return _import_modrinth_page(page.group(1), name, report)
        if "curseforge.com" in urlparse(source).netloc.lower():
            raise RuntimeError("Dalle pagine di CurseForge non si può scaricare in automatico: scarica il file .zip dal sito e importalo da file.")
        archive = _download(source, scaled(report, 0, 30))
        report = scaled(report, 30, 70)
    else:
        archive = Path(source).expanduser()
        if not archive.is_file():
            raise FileNotFoundError(f"File non trovato: {archive}")

    kind = detect_format(archive)
    if kind == FORMAT_MODRINTH:
        return _import_mrpack(archive, name, report)
    if kind == FORMAT_CURSEFORGE:
        return _import_curseforge(archive, name, report, curseforge_api_key or os.environ.get("NOLIMITS_CURSEFORGE_API_KEY"))
    return _import_prism(archive, name, report)


def _import_modrinth_page(slug: str, name, report) -> dict:
    response = requests.get(f"{API}/project/{slug}", headers=HEADERS, timeout=30)
    if response.status_code == 404:
        raise RuntimeError("Progetto Modrinth non trovato.")
    response.raise_for_status()
    info = response.json()
    if info.get("project_type") != "modpack":
        raise RuntimeError(f"«{info.get('title', slug)}» non è un modpack (è di tipo {info.get('project_type')}).")
    return install_modrinth_project(info["id"], name or info.get("title", slug), report, info.get("icon_url"))


# ---------------------------------------------------------------- Modrinth
def _import_mrpack(archive: Path, name, report) -> dict:
    index = read_mrpack_index(archive)
    dependencies = index.get("dependencies", {})
    loader, loader_version = loader_from_dependencies(dependencies)
    store = InstanceStore()
    name = unique_name(store, name or index.get("name") or archive.stem)
    instance_dir = new_instance_dir(name)
    try:
        report(2, "Lettura del modpack…")
        minecraft_launcher_lib.mrpack.install_mrpack(
            str(archive), str(GAME_DIR), modpack_directory=str(instance_dir),
            callback=progress_callback(report, 2, 96, "Installazione mod e loader…"),
        )
        launch_version = minecraft_launcher_lib.mrpack.get_mrpack_launch_version(str(archive))
    except Exception:
        shutil.rmtree(instance_dir, ignore_errors=True)
        raise
    report(100, "Importazione completata.")
    return _register(name, dependencies.get("minecraft"), loader, loader_version, instance_dir, launch_version, "import-mrpack",
                     {"notes": index.get("summary", "") or ""})


# -------------------------------------------------------------- CurseForge
def _curseforge_fetch(project_id: int, file_id: int, mods_dir: Path, api_key: str | None) -> Path:
    filename = None
    if api_key:
        meta = requests.get(f"https://api.curseforge.com/v1/mods/{project_id}/files/{file_id}",
                            headers={"x-api-key": api_key, "Accept": "application/json"}, timeout=30)
        meta.raise_for_status()
        data = meta.json()["data"]
        filename = data["fileName"]
        url = data.get("downloadUrl") or f"https://edge.forgecdn.net/files/{file_id // 1000}/{file_id % 1000}/{filename}"
    else:
        url = f"https://www.curseforge.com/api/v1/mods/{project_id}/files/{file_id}/download"
    with requests.get(url, headers=HEADERS, stream=True, timeout=(20, 120), allow_redirects=True) as response:
        response.raise_for_status()
        filename = filename or _filename_from_response(response, response.url or url)
        folder = mods_dir if filename.lower().endswith(".jar") else mods_dir.parent / "resourcepacks"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / filename
        with target.open("wb") as output:
            for chunk in response.iter_content(256 * 1024):
                if chunk:
                    output.write(chunk)
    return target


def _import_curseforge(archive: Path, name, report, api_key) -> dict:
    with zipfile.ZipFile(archive) as bundle:
        manifest = json.loads(bundle.read("manifest.json"))
        minecraft = manifest.get("minecraft", {})
        minecraft_version = minecraft.get("version", "")
        loaders = minecraft.get("modLoaders", [])
        primary = next((entry for entry in loaders if entry.get("primary")), loaders[0] if loaders else None)
        loader, loader_version = parse_loader_id(primary.get("id", "")) if primary else ("vanilla", "")
        store = InstanceStore()
        name = unique_name(store, name or manifest.get("name") or archive.stem)
        instance_dir = new_instance_dir(name)
        files = manifest.get("files", [])
        warnings: list[str] = []
        try:
            report(2, "Estrazione delle configurazioni…")
            extract_prefix(bundle, manifest.get("overrides", "overrides").rstrip("/") + "/", instance_dir)
            report(5, "Installazione di Minecraft e del loader…")
            launch_version = install_runtime(minecraft_version, loader, loader_version, scaled(report, 5, 35))

            mods_dir = instance_dir / "mods"
            mods_dir.mkdir(parents=True, exist_ok=True)
            done = 0

            def fetch(entry):
                try:
                    _curseforge_fetch(entry["projectID"], entry["fileID"], mods_dir, api_key)
                    return None
                except Exception as exc:  # una mod mancante non deve far fallire tutto l'import
                    return f"progetto {entry.get('projectID')} file {entry.get('fileID')}: {exc}"

            with ThreadPoolExecutor(max_workers=6) as pool:
                for problem in pool.map(fetch, files):
                    done += 1
                    if problem:
                        warnings.append(problem)
                    report(40 + int(58 * done / max(1, len(files))), f"Download mod… {done}/{len(files)}")
        except Exception:
            shutil.rmtree(instance_dir, ignore_errors=True)
            raise
    report(100, "Importazione completata.")
    extra = {"notes": manifest.get("author", "") and f"Autore: {manifest['author']}", "import_warnings": warnings}
    return _register(name, minecraft_version, loader, loader_version, instance_dir, launch_version, "import-curseforge", extra)


# ------------------------------------------------------------ Prism/MultiMC
def parse_instance_cfg(text: str) -> dict:
    values = {}
    for line in text.splitlines():
        key, separator, value = line.partition("=")
        if separator and not line.lstrip().startswith(("#", "[")):
            values[key.strip()] = value.strip()
    return values


def _import_prism(archive: Path, name, report) -> dict:
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        cfg_entry = min((n for n in names if n.endswith("instance.cfg")), key=len, default=None)
        pack_entry = min((n for n in names if n.endswith("mmc-pack.json")), key=len, default=None)
        root = (cfg_entry or pack_entry)[: -len("instance.cfg" if cfg_entry else "mmc-pack.json")]
        cfg = parse_instance_cfg(bundle.read(cfg_entry).decode("utf-8", "replace")) if cfg_entry else {}
        components = json.loads(bundle.read(pack_entry)).get("components", []) if pack_entry else []

        minecraft_version, loader, loader_version = cfg.get("IntendedVersion", ""), "vanilla", ""
        for component in components:
            uid = component.get("uid", "")
            version = component.get("version") or component.get("cachedVersion") or ""
            if uid == "net.minecraft":
                minecraft_version = version or minecraft_version
            elif uid in PRISM_LOADER_UIDS:
                loader, loader_version = PRISM_LOADER_UIDS[uid], version

        game_prefix = next((root + folder + "/" for folder in (".minecraft", "minecraft") if any(n.startswith(root + folder + "/") for n in names)), None)
        store = InstanceStore()
        name = unique_name(store, name or cfg.get("name") or archive.stem)
        instance_dir = new_instance_dir(name)
        try:
            report(3, "Estrazione dell'istanza…")
            if game_prefix:
                extract_prefix(bundle, game_prefix, instance_dir)
            report(10, "Installazione di Minecraft e del loader…")
            launch_version = install_runtime(minecraft_version, loader, loader_version, scaled(report, 10, 88))
        except Exception:
            shutil.rmtree(instance_dir, ignore_errors=True)
            raise

    extra = {"notes": cfg.get("notes", "")}
    if cfg.get("OverrideMemory", "").lower() == "true":
        for key, field in (("MinMemAlloc", "memory_min"), ("MaxMemAlloc", "memory_max")):
            if cfg.get(key, "").isdigit():
                extra[field] = int(cfg[key])
    if cfg.get("OverrideJavaArgs", "").lower() == "true" and cfg.get("JvmArgs"):
        extra["jvm_args"] = cfg["JvmArgs"]
    if cfg.get("OverrideJavaLocation", "").lower() == "true" and cfg.get("JavaPath"):
        extra["java_path"] = cfg["JavaPath"]
    report(100, "Importazione completata.")
    return _register(name, minecraft_version, loader, loader_version, instance_dir, launch_version, "import-prism", extra)
