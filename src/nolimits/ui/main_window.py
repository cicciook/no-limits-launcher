import os, json, webbrowser
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtCore import QByteArray
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QFrame,
    QStackedWidget, QGridLayout, QScrollArea, QProgressBar, QPlainTextEdit, QComboBox
)
from nolimits.providers.modrinth import ModrinthProvider
from nolimits.core.instances import InstanceStore
from nolimits.core.modpacks import install_modrinth_project, launch_instance, search_modrinth_content, install_modrinth_content
from nolimits import auth
from .theme import DARK_STYLE

APP_DIR = Path.home() / ".no-limits-launcher"
CONFIG_FILE = APP_DIR / "config.json"
DEFAULT_MICROSOFT_CLIENT_ID = "2055c8b7-8738-4ee0-a152-bc724edd35c4"

def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try: return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError): return {}

def save_config(data):
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

NAV_ART = {
    "Home": '<path d="M3 11 12 3l9 8v10h-6v-6H9v6H3z"/>',
    "Catalogo": '<rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/>',
    "Le mie istanze": '<rect x="4" y="4" width="16" height="5" rx="1"/><rect x="4" y="11" width="16" height="5" rx="1"/><path d="M4 19h16"/>',
    "Console": '<path d="m5 6 6 6-6 6M13 18h6"/>',
    "Mod": '<path d="M9 4a2 2 0 1 1 4 0v2h3a2 2 0 0 1 2 2v3h2a2 2 0 1 1 0 4h-2v3a2 2 0 0 1-2 2h-3v-2a2 2 0 1 0-4 0v2H6a2 2 0 0 1-2-2v-3h2a2 2 0 1 0 0-4H4V8a2 2 0 0 1 2-2h3z"/>',
    "Shader": '<path d="m12 2 2.7 7.3L22 12l-7.3 2.7L12 22l-2.7-7.3L2 12l7.3-2.7z"/>',
    "Resource Pack": '<path d="M4 5h16v14H4zM8 9h8M8 13h8M8 17h5"/>',
    "Impostazioni": '<circle cx="12" cy="12" r="3"/><path d="m19 13 2-1-2-1-.7-2 1-2-2-2-2 1-2-.7-1-2-1 2-2 .7-2-1-2 2 1 2-.7 2-2 1 2 1 .7 2-1 2 2 2 2-1 2 .7 1 2 1-2 2-.7 2 1 2-2-1-2z"/>',
    "Account": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "Info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>'
}

def make_nav_icon(name):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"><g fill="none" stroke="#6ea4ff" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{NAV_ART[name]}</g></svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class SearchWorker(QThread):
    completed = Signal(list); failed = Signal(str)
    def __init__(self, query): super().__init__(); self.query=query
    def run(self):
        try: self.completed.emit(ModrinthProvider().search_modpacks(self.query))
        except Exception as exc: self.failed.emit(str(exc))

class ContentSearchWorker(QThread):
    completed = Signal(list)
    failed = Signal(str)
    def __init__(self, query, kind, sort="follows"):
        super().__init__()
        self.query, self.kind, self.sort = query, kind, sort
    def run(self):
        try:
            self.completed.emit(search_modrinth_content(self.query, self.kind, sort=self.sort))
        except Exception as exc:
            self.failed.emit(str(exc))

class ContentInstallWorker(QThread):
    completed = Signal(str)
    failed = Signal(str)
    progress = Signal(int, str)
    def __init__(self, instance, project_id, kind):
        super().__init__()
        self.instance, self.project_id, self.kind = instance, project_id, kind
    def run(self):
        try:
            self.completed.emit(install_modrinth_content(self.instance, self.project_id, self.kind, self.progress.emit))
        except Exception as exc:
            self.failed.emit(str(exc))

class CoverWorker(QThread):
    loaded = Signal(object, bytes)
    def __init__(self, item, url):
        super().__init__(); self.item=item; self.url=url
    def run(self):
        try:
            import requests
            response=requests.get(self.url, timeout=15, headers={"User-Agent":"NoLimitsLauncher/0.3.0"})
            response.raise_for_status()
            self.loaded.emit(self.item, response.content)
        except Exception:
            pass

class InstallWorker(QThread):
    completed = Signal(dict); failed = Signal(str); progress = Signal(int, str)
    def __init__(self, project_id, title, icon_url=None): super().__init__(); self.project_id=project_id; self.title=title; self.icon_url=icon_url
    def run(self):
        try: self.completed.emit(install_modrinth_project(self.project_id,self.title,self.progress.emit,self.icon_url))
        except Exception as exc: self.failed.emit(str(exc))

class LaunchWorker(QThread):
    completed = Signal(); failed = Signal(str); output = Signal(str)
    def __init__(self, instance, profile, offline_username=""):
        super().__init__(); self.instance=instance; self.profile=profile; self.offline_username=offline_username
    def run(self):
        try:
            process=launch_instance(self.instance,self.profile,self.offline_username)
            self.output.emit("Minecraft avviato. Output console:")
            if process.stdout:
                for line in process.stdout:
                    self.output.emit(line.rstrip())
            code=process.wait()
            self.output.emit(f"Processo Minecraft terminato (exit code {code}).")
            self.completed.emit()
        except Exception as exc: self.failed.emit(str(exc))

