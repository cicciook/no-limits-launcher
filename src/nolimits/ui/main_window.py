import os
import json
import webbrowser
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QSize, QByteArray, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtWidgets import QGraphicsOpacityEffect
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
LOGO_PATH = Path("src/nolimits/ui/logo.png")

def load_config():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

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
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24"><g fill="none" stroke="#a855f7" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{NAV_ART[name]}</g></svg>'
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class SkinHeadWorker(QThread):
    loaded = Signal(bytes)
    def __init__(self, username):
        super().__init__()
        self.username = username
    def run(self):
        import requests
        try:
            url = f"https://crafthead.net/helm/{self.username}/32"
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                self.loaded.emit(res.content)
        except Exception:
            pass

class HeroDataWorker(QThread):
    image_loaded = Signal(str, bytes)

    def __init__(self, pack_queries):
        super().__init__()
        self.pack_queries = pack_queries

    @staticmethod
    def _normalise(value):
        return "".join(char.lower() for char in value if char.isalnum())

    def run(self):
        import requests
        provider = ModrinthProvider()
        for key, config in self.pack_queries.items():
            try:
                pack = None
                for slug in config.get("project_slugs", []):
                    project_response = requests.get(
                        f"{provider.API}/project/{slug}",
                        timeout=15,
                        headers={"User-Agent": "NoLimitsLauncher/0.3.0"},
                    )
                    if project_response.status_code == 200:
                        candidate = project_response.json()
                        if candidate.get("project_type") == "modpack" and candidate.get("icon_url"):
                            pack = candidate
                            break

                if not pack:
                    results = provider.search_modpacks(config["query"], limit=100)
                    expected_titles = {
                        self._normalise(config["title"]),
                        *(self._normalise(value) for value in config.get("title_aliases", [])),
                    }
                    expected_slugs = {value.lower().strip() for value in config.get("slug_aliases", [])}
                    pack = next(
                        (
                            item for item in results
                            if self._normalise(item.get("title", "")) in expected_titles
                            or item.get("slug", "").lower().strip() in expected_slugs
                        ),
                        None,
                    )
                if not pack:
                    continue

                image_url = pack.get("icon_url")
                if not image_url:
                    continue

                response = requests.get(
                    image_url,
                    timeout=15,
                    headers={"User-Agent": "NoLimitsLauncher/0.3.0"},
                )
                response.raise_for_status()
                self.image_loaded.emit(key, response.content)
            except Exception:
                continue

class CoverLabel(QLabel):
    def __init__(self, placeholder="", parent=None):
        super().__init__(placeholder, parent)
        self._source_pixmap = None
        self._placeholder = placeholder
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_placeholder(self, text):
        self._placeholder = text
        if self._source_pixmap is None:
            self.setText(text)

    def set_cover_data(self, data):
        pixmap = QPixmap()
        if not pixmap.loadFromData(data) or pixmap.isNull():
            return False
        self._source_pixmap = pixmap
        self.setText("")
        self._render_cover()
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render_cover()

    def _render_cover(self):
        if self._source_pixmap is None or self.width() <= 0 or self.height() <= 0:
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - self.width()) // 2)
        y = max(0, (scaled.height() - self.height()) // 2)
        self.setPixmap(scaled.copy(x, y, self.width(), self.height()))

class SearchWorker(QThread):
    completed = Signal(list)
    failed = Signal(str)
    def __init__(self, query):
        super().__init__()
        self.query = query
    def run(self):
        try:
            self.completed.emit(ModrinthProvider().search_modpacks(self.query))
        except Exception as exc:
            self.failed.emit(str(exc))

class ContentSearchWorker(QThread):
    completed = Signal(list, int)
    failed = Signal(str)
    def __init__(self, query, kind, sort="follows", offset=0):
        super().__init__()
        self.query, self.kind, self.sort, self.offset = query, kind, sort, offset
    def run(self):
        try:
            projects = search_modrinth_content(
                self.query, self.kind, limit=50, sort=self.sort, offset=self.offset
            )
            self.completed.emit(projects, self.offset)
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
    failed = Signal(object, str)
    def __init__(self, item, url):
        super().__init__()
        self.item = item
        self.url = url
    def run(self):
        try:
            import requests
            response = requests.get(
                self.url, timeout=20,
                headers={"User-Agent": "NoLimitsLauncher/0.3.0", "Accept": "image/avif,image/webp,image/png,image/*"}
            )
            response.raise_for_status()
            if not response.content:
                raise RuntimeError("Immagine vuota")
            self.loaded.emit(self.item, response.content)
        except Exception as exc:
            self.failed.emit(self.item, str(exc))

class ContentResultCard(QFrame):
    def __init__(self, list_widget, item):
        super().__init__()
        self.list_widget = list_widget
        self.item = item

    def mousePressEvent(self, event):
        self.list_widget.setCurrentItem(self.item)
        super().mousePressEvent(event)

class InstallWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)
    progress = Signal(int, str)
    def __init__(self, project_id, title, icon_url=None):
        super().__init__()
        self.project_id = project_id
        self.title = title
        self.icon_url = icon_url
    def run(self):
        try:
            self.completed.emit(install_modrinth_project(self.project_id, self.title, self.progress.emit, self.icon_url))
        except Exception as exc:
            self.failed.emit(str(exc))

class LaunchWorker(QThread):
    completed = Signal()
    failed = Signal(str)
    output = Signal(str)
    def __init__(self, instance, profile, offline_username=""):
        super().__init__()
        self.instance = instance
        self.profile = profile
        self.offline_username = offline_username
    def run(self):
        try:
            process = launch_instance(self.instance, self.profile, self.offline_username)
            self.output.emit("Minecraft avviato. Output console:")
            if process.stdout:
                for line in process.stdout:
                    self.output.emit(line.rstrip())
            code = process.wait()
            self.output.emit(f"Processo Minecraft terminato (exit code {code}).")
            self.completed.emit()
        except Exception as exc:
            self.failed.emit(str(exc))

class LoginWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)
    progress = Signal(str)
    def __init__(self, client_id):
        super().__init__()
        self.client_id = client_id
    def run(self):
        try:
            profile = auth.login(self.client_id, self.progress.emit, webbrowser.open)
            self.completed.emit(profile)
        except Exception as exc:
            self.failed.emit(str(exc))

class SessionWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)
    def __init__(self, client_id, token):
        super().__init__()
        self.client_id = client_id
        self.token = token
    def run(self):
        try:
            self.completed.emit(auth.refresh(self.client_id, self.token, lambda _message: None))
        except Exception as exc:
            self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("No Limits Launcher")
        self.resize(1340, 840)
        self.setMinimumSize(1020, 680)
        self.setStyleSheet(DARK_STYLE)
        
        self.store = InstanceStore()
        self.config = load_config()
        self.account = None
        self.search_worker = None
        self.login_worker = None
        self.session_worker = None
        self.install_worker = None
        self.launch_worker = None
        self.skin_worker = None
        self.cover_workers = []
        
        self.hero_index = 0
        self.hero_packs = [
            {"title": "Fabulously Optimized", "desc": "Beautiful graphics, speedy performance and familiar features in a simple package.", "tags": ["Optimization", "Fabric", "Client"], "query": "Fabulously Optimized"},
            {"title": "Zombie Invade 100 Days", "desc": "Same as Forge Labs 100 Days Zombie Apocalypse in new Minecraft.", "tags": ["Combat", "Forge", "Hardcore"], "query": "Zombie Invade 100 Days"},
            {"title": "Cobblemon Official Modpack", "desc": "The official modpack of the Cobblemon mod, for Fabric!", "tags": ["Adventure", "Fabric", "Pokemon"], "query": "Cobblemon Official Modpack"},
            {"title": "COBBLEVERSE", "desc": "Start a true Pokémon adventure in Minecraft with starter kit and unique structures.", "tags": ["Adventure", "Fabric", "Pokemon"], "query": "COBBLEVERSE"},
            {"title": "BattleArmory TACZ", "desc": "Modern firearms with random spawns, CS and Call of Duty style weaponry.", "tags": ["Combat", "Forge", "Guns"], "query": "BattleArmory TACZ"}
        ]
        
        self.root = QWidget()
        self.root.setObjectName("Root")
        self.setCentralWidget(self.root)
        
        self.root.setStyleSheet("""
            QWidget#Root {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0d0a1a, stop:0.5 #150f28, stop:1 #0a0714);
            }
        """)
        
        outer = QVBoxLayout(self.root)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(14)
        
        # BARRA SUPERIORE (Istanze + Navigazione + User Chip + LOGO ESPANSO)
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        top_bar.setContentsMargins(0, 0, 0, 0)
        
        # 1. Selettore Istanze
        self.top_instance_combo = QComboBox()
        self.top_instance_combo.setMinimumWidth(180)
        self.top_instance_combo.setStyleSheet("""
            QComboBox {
                background: rgba(139, 92, 246, 0.15);
                border: 1px solid rgba(168, 85, 247, 0.4);
                border-radius: 8px;
                color: #e9d5ff;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 12px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #18122b;
                border: 1px solid #7e22ce;
                color: #ffffff;
                selection-background-color: #8b5cf6;
            }
        """)
        top_bar.addWidget(QLabel("<b style='color:#c084fc; font-size:12px;'>Instances:</b>"))
        top_bar.addWidget(self.top_instance_combo)
        top_bar.addSpacing(6)

        # 2. Pulsanti Navigazione
        self.nav_bar = QFrame()
        self.nav_bar.setStyleSheet("background: transparent; border: none;")
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(6)
        
        self.nav_buttons = {}
        for label in ["Home", "Catalogo", "Le mie istanze", "Console", "Mod", "Shader", "Resource Pack", "Impostazioni", "Account", "Info"]:
            btn = QPushButton(label)
            btn.setObjectName("Nav")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(168, 85, 247, 0.25);
                    border-radius: 6px;
                    color: #d8b4fe;
                    padding: 6px 12px;
                    font-weight: 700;
                    font-size: 12px;
                }
                QPushButton:checked {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #a855f7);
                    color: #ffffff;
                    border: 1px solid #c084fc;
                }
                QPushButton:hover:!checked {
                    background: rgba(168, 85, 247, 0.2);
                    color: #ffffff;
                }
            """)
            btn.clicked.connect(lambda checked=False, n=label: self.navigate(n))
            nav_layout.addWidget(btn)
            self.nav_buttons[label] = btn
            
        self.nav_buttons["Home"].setChecked(True)
        top_bar.addWidget(self.nav_bar)
        top_bar.addStretch()
        
        # 3. FIX SKIN USER CHIP (Contenitore perfettamente allineato e pulito)
        self.user_chip = QPushButton()
        self.user_chip.setFixedHeight(36)
        self.user_chip.setStyleSheet("""
            QPushButton {
                background: rgba(139, 92, 246, 0.15);
                border: 1px solid rgba(168, 85, 247, 0.35);
                border-radius: 8px;
                color: #ffffff;
                padding: 2px 10px 2px 4px;
            }
            QPushButton:hover { background: rgba(139, 92, 246, 0.3); }
        """)
        self.user_chip.clicked.connect(lambda: self.navigate("Account"))
        
        uc_layout = QHBoxLayout(self.user_chip)
        uc_layout.setContentsMargins(4, 2, 8, 2)
        uc_layout.setSpacing(8)
        
        # Label dedicata alla skin (icona di default se non ancora caricata)
        self.skin_head = QLabel("👤")
        self.skin_head.setFixedSize(28, 28)
        self.skin_head.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.skin_head.setStyleSheet("""
            QLabel {
                border-radius: 6px;
                background: #2e1065;
                color: #c084fc;
                font-size: 15px;
                border: 1px solid rgba(168, 85, 247, 0.4);
            }
        """)
        uc_layout.addWidget(self.skin_head)
        
        uc_info = QVBoxLayout()
        uc_info.setSpacing(0)
        uc_info.setContentsMargins(0, 0, 0, 0)
        
        self.account_label = QLabel("cicciook")
        self.account_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #ffffff; background: transparent; border: none;")
        self.status_label = QLabel("• Online")
        self.status_label.setStyleSheet("font-size: 9px; color: #4ade80; background: transparent; border: none;")
        
        uc_info.addWidget(self.account_label)
        uc_info.addWidget(self.status_label)
        uc_layout.addLayout(uc_info)
        top_bar.addWidget(self.user_chip)
        
        # 4. LOGO UFFICIALE (Sostituisce il testo deformato in alto a destra)
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(170, 48)
        self.logo_label.setScaledContents(True)
        if LOGO_PATH.exists():
            self.logo_label.setPixmap(QPixmap(str(LOGO_PATH)))
        else:
            self.logo_label.setText("Ｎ NO LIMITS\nＬＡＵＮＣＨＥＲ")
            self.logo_label.setStyleSheet("font-size: 12px; font-weight: 900; color: #c084fc; letter-spacing: 1px; background: transparent; border: none;")
        top_bar.addWidget(self.logo_label)
        
        outer.addLayout(top_bar)
        
        # Stacked Widget per le schermate
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        outer.addWidget(self.stack, 1)
        
        self.pages = {}
        for name in ["Home", "Catalogo", "Le mie istanze", "Console", "Mod", "Shader", "Resource Pack", "Impostazioni", "Account", "Info"]:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(0, 0, 0, 0)
            page_layout.setSpacing(14)
            self.pages[name] = page
            self.stack.addWidget(page)
            
        self.build_home()
        self.build_catalog()
        self.build_instances()
        self.build_console()
        self.build_simple_pages()
        self.navigate("Home")
        self.update_account_ui()
        self.restore_session()
        self.load_modrinth_images()

    def panel(self, title=None, subtitle=None):
        frame = QFrame()
        frame.setObjectName("Panel")
        frame.setStyleSheet("""
            QFrame#Panel {
                background: rgba(24, 18, 43, 0.65);
                border: 1px solid rgba(168, 85, 247, 0.25);
                border-radius: 12px;
            }
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        box = QVBoxLayout(frame)
        box.setContentsMargins(18, 16, 18, 16)
        box.setSpacing(8)
        if title:
            t = QLabel(title)
            t.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffffff;")
            box.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("Muted")
            s.setStyleSheet("color: #a78bfa; font-size: 12px;")
            s.setWordWrap(True)
            box.addWidget(s)
        return frame, box

    def page_header(self, page, title, desc):
        box = QVBoxLayout()
        t = QLabel(title)
        t.setObjectName("SectionTitle")
        t.setStyleSheet("font-size: 22px; font-weight: 800; color: #ffffff; border: none; background: transparent;")
        d = QLabel(desc)
        d.setObjectName("Muted")
        d.setStyleSheet("color: #a78bfa; font-size: 13px; border: none; background: transparent;")
        box.addWidget(t)
        box.addWidget(d)
        self.pages[page].layout().addLayout(box)

    def build_home(self):
        p = self.pages["Home"]
        
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)
        
        search_wrap = QFrame()
        search_wrap.setStyleSheet("""
            background: rgba(20, 14, 36, 0.7);
            border: 1px solid rgba(168, 85, 247, 0.3);
            border-radius: 10px;
        """)
        sw_layout = QHBoxLayout(search_wrap)
        sw_layout.setContentsMargins(12, 6, 12, 6)
        
        search_icon = QLabel("🔍")
        search_icon.setStyleSheet("color: #a78bfa; font-size: 13px; border: none; background: transparent;")
        self.home_search_input = QLineEdit()
        self.home_search_input.setPlaceholderText("Cerca modpack su CurseForge e Modrinth...")
        self.home_search_input.setStyleSheet("background: transparent; border: none; color: #ffffff; font-size: 13px;")
        self.home_search_input.returnPressed.connect(self.trigger_home_search)
        
        sw_layout.addWidget(search_icon)
        sw_layout.addWidget(self.home_search_input, 1)
        
        cf_btn = QPushButton("🟠 CurseForge")
        cf_btn.setStyleSheet("background: rgba(255, 125, 50, 0.15); border: 1px solid rgba(255, 125, 50, 0.4); color: #ff7d32; border-radius: 8px; padding: 6px 14px; font-weight: 700;")
        
        mr_btn = QPushButton("🟢 modrinth")
        mr_btn.setStyleSheet("background: rgba(27, 217, 106, 0.15); border: 1px solid rgba(27, 217, 106, 0.4); color: #1bd96a; border-radius: 8px; padding: 6px 14px; font-weight: 700;")
        
        top_bar.addWidget(search_wrap, 1)
        top_bar.addWidget(cf_btn)
        top_bar.addWidget(mr_btn)
        p.layout().addLayout(top_bar)
        
        self.hero_frame = QFrame()
        self.hero_frame.setObjectName("HeroFrame")
        self.hero_frame.setStyleSheet("""
            QFrame#HeroFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(109, 40, 217, 0.4), stop:1 rgba(24, 15, 46, 0.8));
                border: 1px solid rgba(168, 85, 247, 0.4);
                border-radius: 14px;
            }
            QLabel { border: none; background: transparent; }
        """)

        h_layout = QHBoxLayout(self.hero_frame)
        h_layout.setContentsMargins(24, 24, 24, 24)
        h_layout.setSpacing(20)

        self.hero_content = QFrame()
        self.hero_content.setStyleSheet("background: transparent; border: none;")
        content_layout = QHBoxLayout(self.hero_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(24)

        self.hero_cover = CoverLabel("Fabulously Optimized")
        self.hero_cover.setFixedSize(280, 160)
        self.hero_cover.setStyleSheet(
            "font-size: 16px; font-weight: 800; color: #e9d5ff; "
            "background: rgba(15, 10, 30, 0.7); border-radius: 10px; "
            "border: 1px solid rgba(168, 85, 247, 0.3);"
        )
        content_layout.addWidget(self.hero_cover)

        hero_info = QVBoxLayout()
        hero_info.setSpacing(10)

        self.hero_title_lbl = QLabel("Fabulously Optimized")
        self.hero_title_lbl.setStyleSheet("font-size: 26px; font-weight: 900; color: #ffffff;")

        self.hero_desc_lbl = QLabel("Beautiful graphics, speedy performance and familiar features in a simple package.")
        self.hero_desc_lbl.setStyleSheet("color: #ddd6fe; font-size: 13px;")
        self.hero_desc_lbl.setWordWrap(True)

        self.tags_layout = QHBoxLayout()
        self.tags_layout.setSpacing(6)

        download_btn = QPushButton("📥 Scarica")
        download_btn.setStyleSheet(
            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8b5cf6, stop:1 #a855f7); "
            "color: #ffffff; border-radius: 8px; padding: 10px 28px; font-weight: 700; font-size: 13px; border: none;"
        )
        download_btn.clicked.connect(lambda: self.navigate("Catalogo"))

        hero_info.addWidget(self.hero_title_lbl)
        hero_info.addWidget(self.hero_desc_lbl)
        hero_info.addLayout(self.tags_layout)
        hero_info.addSpacing(6)
        hero_info.addWidget(download_btn, 0, Qt.AlignmentFlag.AlignLeft)
        hero_info.addStretch()

        content_layout.addLayout(hero_info, 1)
        h_layout.addWidget(self.hero_content, 1)
        p.layout().addWidget(self.hero_frame)

        self.dots_layout = QHBoxLayout()
        self.dots_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dots_layout.setSpacing(10)
        self.dots = []
        for i in range(len(self.hero_packs)):
            dot = QPushButton()
            dot.setCursor(Qt.CursorShape.PointingHandCursor)
            dot.setFixedSize(10, 10)
            dot.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            dot.clicked.connect(lambda checked=False, index=i: self.go_to_hero(index))
            self.dots_layout.addWidget(dot)
            self.dots.append(dot)
        p.layout().addLayout(self.dots_layout)

        grid_header = QHBoxLayout()
        gh_title = QLabel("★ Modpack in evidenza")
        gh_title.setStyleSheet("font-size: 17px; font-weight: 800; color: #ffffff; border: none; background: transparent;")
        see_all = QPushButton("Vedi tutti →")
        see_all.setStyleSheet("background: transparent; border: none; color: #c084fc; font-weight: 700; font-size: 13px;")
        see_all.clicked.connect(lambda: self.navigate("Catalogo"))
        grid_header.addWidget(gh_title)
        grid_header.addStretch()
        grid_header.addWidget(see_all)
        p.layout().addLayout(grid_header)
        
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)
        
        self.grid_cards = {}
        featured_packs = [
            ("Zombie Invade 100 Days", "1.20.1", "Forge", "Zombie Invade 100 Days"),
            ("Cobblemon Official Modpack", "1.20.1", "Fabric", "Cobblemon Official Modpack"),
            ("COBBLEVERSE", "1.20.1", "Fabric", "COBBLEVERSE"),
            ("BattleArmory TACZ", "1.20.1", "Forge", "BattleArmory TACZ")
        ]
        
        for idx, (p_name, p_ver, p_loader, p_query) in enumerate(featured_packs):
            card = QFrame()
            card.setStyleSheet("""
                QFrame {
                    background: rgba(24, 18, 43, 0.6);
                    border: 1px solid rgba(168, 85, 247, 0.25);
                    border-radius: 12px;
                }
                QLabel {
                    border: none;
                    background: transparent;
                }
            """)
            c_box = QVBoxLayout(card)
            c_box.setContentsMargins(12, 12, 12, 12)
            c_box.setSpacing(8)
            
            c_img = CoverLabel(p_name)
            c_img.setFixedHeight(120)
            c_img.setMinimumWidth(0)
            c_img.setStyleSheet("background: rgba(46, 16, 101, 0.5); border-radius: 8px; font-weight: 800; color: #c084fc; font-size: 13px; border: none;")
            
            c_title = QLabel(p_name)
            c_title.setStyleSheet("font-weight: 700; font-size: 13px; color: #ffffff;")
            
            c_meta = QLabel(f"🌐 {p_ver}   ★ {p_loader}")
            c_meta.setStyleSheet("font-size: 11px; color: #a78bfa; font-weight: 600;")
            
            c_box.addWidget(c_img)
            c_box.addWidget(c_title)
            c_box.addWidget(c_meta)
            
            self.grid_cards[p_query] = c_img
            grid_layout.addWidget(card, 0, idx)
            
        p.layout().addLayout(grid_layout)
        p.layout().addStretch()
        
        self.hero_opacity = QGraphicsOpacityEffect(self.hero_content)
        self.hero_content.setGraphicsEffect(self.hero_opacity)
        self.hero_opacity.setOpacity(1.0)
        self.hero_animation = None
        self.hero_transitioning = False

        self.hero_timer = QTimer(self)
        self.hero_timer.timeout.connect(self.next_hero)
        self.hero_timer.start(5500)

        self.update_hero_ui()

    def update_hero_gradient(self, data):
        pixmap = QPixmap()
        if not pixmap.loadFromData(data) or pixmap.isNull():
            return
        sample = pixmap.scaled(
            1, 1,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        color = sample.toImage().pixelColor(0, 0)
        start = color.darker(160)
        end = color.darker(450)
        self.hero_frame.setStyleSheet(f"""
            QFrame#HeroFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {start.name()}, stop:1 {end.name()});
                border: 1px solid rgba(168, 85, 247, 0.5);
                border-radius: 14px;
            }}
            QLabel {{ border: none; background: transparent; }}
        """)

    def update_hero_ui(self):
        pack = self.hero_packs[self.hero_index]
        self.hero_title_lbl.setText(pack["title"])
        self.hero_desc_lbl.setText(pack["desc"])

        while self.tags_layout.count():
            child = self.tags_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for tag in pack["tags"]:
            tag_label = QLabel(tag)
            tag_label.setStyleSheet(
                "background: rgba(139, 92, 246, 0.25); color: #e9d5ff; "
                "padding: 4px 12px; border-radius: 12px; "
                "font-size: 11px; font-weight: 600;"
            )
            self.tags_layout.addWidget(tag_label)
        self.tags_layout.addStretch()

        for idx, dot in enumerate(self.dots):
            if idx == self.hero_index:
                dot.setFixedSize(11, 11)
                dot.setStyleSheet(
                    "QPushButton { background: #c084fc; border: 2px solid #f3e8ff; border-radius: 5px; }"
                )
            else:
                dot.setFixedSize(8, 8)
                dot.setStyleSheet(
                    "QPushButton { background: rgba(168, 85, 247, 0.3); border: none; border-radius: 4px; } "
                    "QPushButton:hover { background: #c084fc; }"
                )

        self.hero_cover.set_placeholder(pack["title"])
        image_data = getattr(self, "hero_images", {}).get(pack["query"])
        if image_data:
            self.hero_cover.set_cover_data(image_data)
            self.update_hero_gradient(image_data)

    def go_to_hero(self, index):
        if not self.hero_packs or index == self.hero_index or self.hero_transitioning:
            return
        self.hero_transitioning = True
        self.hero_timer.start(5500)

        fade_out = QPropertyAnimation(self.hero_opacity, b"opacity", self)
        fade_out.setDuration(180)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)

        def show_next():
            self.hero_index = index
            self.update_hero_ui()
            fade_in = QPropertyAnimation(self.hero_opacity, b"opacity", self)
            fade_in.setDuration(420)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.hero_animation = fade_in
            fade_in.finished.connect(lambda: setattr(self, "hero_transitioning", False))
            fade_in.start()

        self.hero_animation = fade_out
        fade_out.finished.connect(show_next)
        fade_out.start()

    def next_hero(self):
        self.go_to_hero((self.hero_index + 1) % len(self.hero_packs))

    def prev_hero(self):
        self.go_to_hero((self.hero_index - 1) % len(self.hero_packs))

    def load_modrinth_images(self):
        queries = {
            "Fabulously Optimized": {
                "query": "Fabulously Optimized",
                "title": "Fabulously Optimized",
                "project_slugs": ["fabulously-optimized"],
            },
            "Zombie Invade 100 Days": {
                "query": "Zombie Invade 100 Days",
                "title": "Zombie Invade 100 Days",
                "project_slugs": ["zombie-invade-100-days"],
            },
            "Cobblemon Official Modpack": {
                "query": "Cobblemon Official Modpack",
                "title": "Cobblemon Official Modpack [Fabric]",
                "project_slugs": ["cobblemon-official-modpack"],
            },
            "COBBLEVERSE": {
                "query": "COBBLEVERSE",
                "title": "COBBLEVERSE - Pokemon Adventure",
                "project_slugs": ["cobbleverse"],
            },
            "BattleArmory TACZ": {
                "query": "BattleArmory TACZ",
                "title": "BattleArmory TACZ",
                "project_slugs": ["battlearmory-tacz"],
            },
        }

        self.hero_images = {}
        self.hero_worker = HeroDataWorker(queries)
        self.hero_worker.image_loaded.connect(self.on_hero_image_loaded)
        self.hero_worker.start()

    def on_hero_image_loaded(self, key, data):
        self.hero_images[key] = data
        if key in self.grid_cards:
            self.grid_cards[key].set_cover_data(data)
        if self.hero_packs[self.hero_index]["query"] == key:
            self.hero_cover.set_cover_data(data)
            self.update_hero_gradient(data)

    def trigger_home_search(self):
        query = self.home_search_input.text().strip()
        if query:
            self.search_input.setText(query)
            self.navigate("Catalogo")
            self.search_modpacks()

    def build_catalog(self):
        p = self.pages["Catalogo"]
        self.page_header("Catalogo", "Catalogo modpack", "Cerca modpack su Modrinth. Il connettore CurseForge verrà attivato con API key autorizzata.")
        row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Cerca modpack…")
        self.search_input.returnPressed.connect(self.search_modpacks)
        row.addWidget(self.search_input, 1)
        self.source = QPushButton("Modrinth  ✓")
        self.source.setEnabled(False)
        row.addWidget(self.source)
        self.search_button = QPushButton("Cerca / più popolari")
        self.search_button.setObjectName("Primary")
        self.search_button.clicked.connect(self.search_modpacks)
        row.addWidget(self.search_button)
        p.layout().addLayout(row)
        self.results = QListWidget()
        self.results.setIconSize(QPixmap(112, 72).size())
        self.results.setSpacing(7)
        self.results.itemDoubleClicked.connect(self.show_pack_details)
        p.layout().addWidget(self.results, 1)
        self.install_progress = QProgressBar()
        self.install_progress.setRange(0, 100)
        self.install_progress.setValue(0)
        self.install_progress.setFormat("%p%  •  %v/100")
        p.layout().addWidget(self.install_progress)
        actions = QHBoxLayout()
        self.install_button = QPushButton("Installa modpack selezionato")
        self.install_button.setObjectName("Primary")
        self.install_button.clicked.connect(self.install_selected_pack)
        actions.addWidget(self.install_button)
        self.install_status = QLabel("")
        self.install_status.setObjectName("Muted")
        actions.addWidget(self.install_status, 1)
        p.layout().addLayout(actions)

    def build_console(self):
        p = self.pages["Console"]
        self.page_header("Console", "Console di gioco", "Log in tempo reale dell'installazione e del processo Minecraft.")
        self.console_output = QPlainTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setPlaceholderText("La console mostrerà qui i log di Minecraft…")
        self.console_output.setMaximumBlockCount(5000)
        p.layout().addWidget(self.console_output, 1)
        row = QHBoxLayout()
        clear = QPushButton("Pulisci console")
        clear.clicked.connect(self.console_output.clear)
        row.addWidget(clear)
        row.addStretch()
        p.layout().addLayout(row)

    def log_console(self, message):
        if hasattr(self, "console_output"):
            self.console_output.appendPlainText(str(message))

    def install_progress_update(self, value, message):
        self.install_progress.setValue(max(0, min(100, int(value))))
        self.install_status.setText(message)
        self.log_console(f"[INSTALL {value:3d}%] {message}")

    def build_instances(self):
        p = self.pages["Le mie istanze"]
        self.page_header("Le mie istanze", "Le tue installazioni", "Ogni istanza avrà cartella, versione Minecraft e mod loader indipendenti.")
        row = QHBoxLayout()
        launch = QPushButton("▶ Avvia selezionata")
        launch.setObjectName("Primary")
        launch.clicked.connect(self.launch_selected_instance)
        row.addWidget(launch)
        row.addStretch()
        add = QPushButton("+ Nuova istanza")
        add.setObjectName("Primary")
        add.clicked.connect(self.add_instance)
        row.addWidget(add)
        p.layout().addLayout(row)
        self.instance_list = QListWidget()
        self.instance_list.setIconSize(QSize(128, 76))
        self.instance_list.setSpacing(7)
        p.layout().addWidget(self.instance_list, 1)
        controls = QHBoxLayout()
        rename = QPushButton("Rinomina")
        rename.clicked.connect(self.rename_selected_instance)
        controls.addWidget(rename)
        remove = QPushButton("Elimina")
        remove.clicked.connect(self.delete_selected_instance)
        controls.addWidget(remove)
        p.layout().addLayout(controls)
        self.refresh_instances()

    def build_simple_pages(self):
        for name, desc in [
            ("Mod", "Gestione delle mod per ogni istanza."),
            ("Shader", "Gestisci shader pack e impostazioni grafiche."),
            ("Resource Pack", "Organizza texture e resource pack."),
            ("Impostazioni", "Percorsi Java, memoria RAM, lingua e preferenze."),
            ("Account", "Accedi con il tuo account Microsoft per giocare a Minecraft."),
            ("Info", "No Limits Launcher — un launcher indipendente, in sviluppo.")
        ]:
            self.page_header(name, name, desc)
            if name == "Account":
                card, box = self.panel("Account Microsoft", "Autenticazione ufficiale tramite Device Code Flow.")
                self.login_status = QLabel("Non hai ancora collegato un account.")
                self.login_status.setObjectName("Muted")
                box.addWidget(self.login_status)
                offline, offline_box = self.panel("Modalità offline", "Avvia Minecraft senza account Microsoft usando un nome locale.")
                self.offline_name_input = QLineEdit()
                self.offline_name_input.setPlaceholderText("Nome giocatore (es. Steve)")
                self.offline_name_input.setText(self.config.get("offline_username", ""))
                self.offline_name_input.textChanged.connect(self.save_offline_name)
                offline_box.addWidget(self.offline_name_input)
                p = self.pages[name]
                p.layout().addWidget(offline)
                self.login_button = QPushButton("Accedi con Microsoft")
                self.login_button.setObjectName("Primary")
                self.login_button.clicked.connect(self.start_login)
                box.addWidget(self.login_button, 0, Qt.AlignmentFlag.AlignLeft)
                self.logout_button = QPushButton("Disconnetti account")
                self.logout_button.clicked.connect(self.logout)
                self.logout_button.setVisible(False)
                box.addWidget(self.logout_button, 0, Qt.AlignmentFlag.AlignLeft)
                p.layout().addWidget(card)
                p.layout().addStretch()
            elif name in ("Mod", "Shader", "Resource Pack"):
                kind = {"Mod": "mod", "Shader": "shader", "Resource Pack": "resourcepack"}[name]
                self.build_content_page(name, kind)
            elif name == "Impostazioni":
                card, box = self.panel("Preferenze launcher", "Le impostazioni dell'account Microsoft sono gestite automaticamente.")
                b = QPushButton("Apri account")
                b.clicked.connect(lambda: self.navigate("Account"))
                box.addWidget(b, 0, Qt.AlignmentFlag.AlignLeft)
                self.pages[name].layout().addWidget(card)
                self.pages[name].layout().addStretch()
            else:
                card, box = self.panel("In sviluppo", desc + " Questa sezione è già predisposta nell'interfaccia.")
                self.pages[name].layout().addWidget(card)
                self.pages[name].layout().addStretch()

    def build_content_page(self, page_name, kind):
        page = self.pages[page_name]
        if not hasattr(self, "content_offsets"):
            self.content_offsets, self.content_has_more = {}, {}
            self.content_loading, self.content_seen = {}, {}
            self.content_cover_labels = {}
        self.content_offsets[kind] = 0
        self.content_has_more[kind] = True
        self.content_loading[kind] = False
        self.content_seen[kind] = set()

        intro, intro_box = self.panel(
            "Esplora " + page_name,
            "Catalogo Modrinth aggiornato: seleziona un risultato per installarlo oppure apri la sua pagina ufficiale."
        )
        intro.setObjectName("ContentIntro")
        page.layout().addWidget(intro)

        row = QHBoxLayout()
        row.setSpacing(10)
        selector = QComboBox()
        selector.setMinimumWidth(210)
        selector.setPlaceholderText("Seleziona istanza")
        if not hasattr(self, "content_selectors"):
            self.content_selectors = {}
        self.content_selectors[kind] = selector
        row.addWidget(QLabel("Istanza"))
        row.addWidget(selector)

        query = QLineEdit()
        query.setPlaceholderText("Cerca " + page_name.lower() + " su Modrinth…")
        if not hasattr(self, "content_queries"):
            self.content_queries = {}
        self.content_queries[kind] = query
        query.returnPressed.connect(lambda k=kind: self.search_content(k))
        row.addWidget(query, 1)

        if kind == "mod":
            sort = QComboBox()
            sort.addItem("Popolari", "follows")
            sort.addItem("Più scaricate", "downloads")
            sort.addItem("Aggiornate di recente", "updated")
            sort.setMinimumWidth(175)
            self.mod_sort = sort
            row.addWidget(sort)

        search = QPushButton("Cerca")
        search.setObjectName("Primary")
        search.clicked.connect(lambda checked=False, k=kind: self.search_content(k))
        row.addWidget(search)
        page.layout().addLayout(row)

        results = QListWidget()
        results.setObjectName("ContentResults")
        results.setSpacing(5)
        results.setUniformItemSizes(False)
        if not hasattr(self, "content_lists"):
            self.content_lists = {}
        self.content_lists[kind] = results
        results.verticalScrollBar().valueChanged.connect(
            lambda value, k=kind: self.maybe_load_more_content(k, value)
        )
        page.layout().addWidget(results, 1)

        footer = QHBoxLayout()
        progress = QProgressBar()
        progress.setMaximumWidth(190)
        if not hasattr(self, "content_bars"):
            self.content_bars = {}
        self.content_bars[kind] = progress
        status = QLabel("Modrinth • cerca per iniziare")
        status.setObjectName("Muted")
        if not hasattr(self, "content_labels"):
            self.content_labels = {}
        self.content_labels[kind] = status
        install = QPushButton("Installa selezionato")
        install.setObjectName("Primary")
        install.clicked.connect(lambda checked=False, k=kind: self.install_selected_content(k))
        footer.addWidget(status, 1)
        footer.addWidget(progress)
        footer.addWidget(install)
        page.layout().addLayout(footer)
        self.refresh_content_instances()

    def refresh_content_instances(self):
        for selector in getattr(self, "content_selectors", {}).values():
            current = selector.currentText()
            selector.clear()
            for instance in self.store.list_instances():
                if instance.get("status") == "installed":
                    selector.addItem(instance.get("name", "Istanza"), instance)
            index = selector.findText(current)
            if index >= 0: selector.setCurrentIndex(index)

    def search_content(self, kind):
        self.content_lists[kind].clear()
        self.content_offsets[kind] = 0
        self.content_has_more[kind] = True
        self.content_loading[kind] = False
        self.content_seen[kind] = set()
        self.content_labels[kind].setText("Ricerca su Modrinth…")
        self.load_more_content(kind)

    def maybe_load_more_content(self, kind, value):
        bar = self.content_lists[kind].verticalScrollBar()
        if bar.maximum() > 0 and value >= bar.maximum() - 160:
            self.load_more_content(kind)

    def load_more_content(self, kind):
        if self.content_loading.get(kind, False) or not self.content_has_more.get(kind, True):
            return
        self.content_loading[kind] = True
        sort = self.mod_sort.currentData() if kind == "mod" and hasattr(self, "mod_sort") else "downloads"
        worker = ContentSearchWorker(
            self.content_queries[kind].text().strip(), kind, sort,
            offset=self.content_offsets.get(kind, 0)
        )
        if not hasattr(self, "content_workers"): self.content_workers = []
        self.content_workers.append(worker)
        worker.completed.connect(lambda projects, offset, k=kind: self.show_content_results(k, projects, offset))
        worker.failed.connect(lambda message, k=kind: self.content_search_failed(k, message))
        worker.finished.connect(lambda w=worker: self.content_workers.remove(w) if w in self.content_workers else None)
        worker.start()

    def content_search_failed(self, kind, message):
        self.content_loading[kind] = False
        self.content_labels[kind].setText("Errore di ricerca: " + message)

    def show_content_results(self, kind, projects, offset):
        seen = self.content_seen[kind]
        added = 0
        for project in projects:
            project_id = project.get("id")
            if not project_id or project_id in seen:
                continue
            seen.add(project_id)

            title = QLabel(project.get("title", "Contenuto senza nome"))
            title.setObjectName("ContentTitle")
            downloads = QLabel("{:,} download".format(project.get("downloads", 0)))
            downloads.setObjectName("ContentDescription")

            details = QVBoxLayout()
            details.setSpacing(5)
            details.addWidget(title)
            details.addWidget(downloads)
            description = (project.get("description") or "").strip()
            if description:
                if len(description) > 125:
                    description = description[:122] + "…"
                summary = QLabel(description)
                summary.setObjectName("ContentDescription")
                summary.setWordWrap(False)
                details.addWidget(summary)

            author = QLabel("CREATORE " + project.get("author", "Autore sconosciuto"))
            author.setObjectName("ContentAuthor")
            versions = project.get("versions") or []
            version_text = " • ".join(versions[:3]) if versions else "Versioni varie"
            if len(versions) > 3:
                version_text += " • +{}".format(len(versions) - 3)
            version = QLabel(version_text)
            version.setObjectName("ContentVersion")
            author.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            version.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            open_page = QPushButton("Apri pagina ↗")
            open_page.setObjectName("SecondaryAction")
            project_url = project.get("project_url", "")
            open_page.clicked.connect(
                lambda checked=False, url=project_url: webbrowser.open(url) if url else None
            )
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, project)
            item.setSizeHint(QSize(0, 112))
            self.content_lists[kind].addItem(item)

            card = ContentResultCard(self.content_lists[kind], item)
            card.setObjectName("ContentResultCard")
            for label in (title, downloads, author, version):
                label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            if description:
                summary.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout = QHBoxLayout(card)
            layout.setContentsMargins(12, 9, 12, 9)
            layout.setSpacing(13)

            cover = QLabel("MODRINTH")
            cover.setObjectName("ContentCover")
            cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cover.setFixedSize(76, 76)
            cover.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            layout.addWidget(cover)
            layout.addLayout(details, 1)
            side = QVBoxLayout()
            side.setSpacing(5)
            side.addWidget(author)
            side.addWidget(version)
            side.addStretch(1)
            side.addWidget(open_page, 0, Qt.AlignmentFlag.AlignRight)
            layout.addLayout(side)
            self.content_lists[kind].setItemWidget(item, card)

            if project.get("icon_url"):
                worker = CoverWorker(cover, project["icon_url"])
                worker.loaded.connect(self.set_content_cover)
                worker.failed.connect(self.content_cover_failed)
                if not hasattr(self, "cover_workers"):
                    self.cover_workers = []
                self.cover_workers.append(worker)
                worker.finished.connect(
                    lambda w=worker: self.cover_workers.remove(w) if w in self.cover_workers else None
                )
                worker.start()
            else:
                cover.setText("NO COVER")
            added += 1

        self.content_offsets[kind] = offset + len(projects)
        self.content_has_more[kind] = len(projects) == 50
        self.content_loading[kind] = False
        count = self.content_lists[kind].count()
        suffix = " • scorri per caricarne altri" if self.content_has_more[kind] else ""
        self.content_labels[kind].setText("{} risultati{}".format(count, suffix))
        bar = self.content_lists[kind].verticalScrollBar()
        if self.content_has_more[kind] and (added == 0 or bar.maximum() <= 0):
            self.load_more_content(kind)

    def set_content_cover(self, label, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            label.setPixmap(
                pixmap.scaled(
                    label.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            label.setText("")

    def content_cover_failed(self, label, message):
        label.setText("COVER")
        label.setToolTip("Copertina non disponibile: " + message)

    def install_selected_content(self, kind):
        item = self.content_lists[kind].currentItem()
        project = item.data(Qt.ItemDataRole.UserRole) if item else None
        instance = self.top_instance_combo.currentData()
        if not project or not instance:
            QMessageBox.information(self, "Selezione necessaria", "Scegli un contenuto e un'istanza installata.")
            return
        worker = ContentInstallWorker(instance, project["id"], kind)
        if not hasattr(self, "content_install_workers"): self.content_install_workers = []
        self.content_install_workers.append(worker)
        worker.progress.connect(lambda value, msg, k=kind: (self.content_bars[k].setValue(value), self.content_labels[k].setText(msg), self.log_console(msg)))
        worker.completed.connect(lambda path, k=kind: self.content_labels[k].setText("Installato: " + Path(path).name))
        worker.failed.connect(lambda msg, k=kind: (self.content_labels[k].setText("Errore installazione"), QMessageBox.warning(self, "Installazione", msg)))
        worker.finished.connect(lambda w=worker: self.content_install_workers.remove(w) if w in self.content_install_workers else None)
        worker.start()

    def navigate(self, name):
        self.stack.setCurrentWidget(self.pages[name])
        for label, button in self.nav_buttons.items():
            button.setChecked(label == name)
            
        if name == "Le mie istanze": self.refresh_instances()
        if name in ("Mod", "Shader", "Resource Pack"): self.refresh_content_instances()
        if name == "Catalogo" and self.results.count() == 0: self.search_modpacks()

    def search_modpacks(self):
        query = self.search_input.text().strip()
        self.search_button.setEnabled(False)
        self.search_button.setText("Ricerca…")
        self.results.clear()
        self.search_worker = SearchWorker(query)
        self.search_worker.completed.connect(self.show_results)
        self.search_worker.failed.connect(self.search_failed)
        self.search_worker.finished.connect(self.search_finished)
        self.search_worker.start()

    def show_results(self, packs):
        if not packs:
            self.results.addItem("Nessun modpack trovato. Prova un altro nome.")
            return
        for pack in packs:
            description = (pack.get("description") or "").strip()
            if len(description) > 180: description = description[:177] + "..."
            item = QListWidgetItem(
                f'{pack.get("title","Modpack")}\n'
                f'{pack.get("author","Unknown")} • {pack.get("downloads",0):,} download\n'
                f'{description}'
            )
            item.setData(Qt.ItemDataRole.UserRole, pack)
            item.setSizeHint(QSize(0, 88))
            self.results.addItem(item)
            cover = pack.get("icon_url")
            if cover:
                worker = CoverWorker(item, cover)
                worker.loaded.connect(self.set_pack_cover)
                worker.finished.connect(lambda w=worker: self.cover_workers.remove(w) if w in self.cover_workers else None)
                self.cover_workers.append(worker)
                worker.start()

    def set_pack_cover(self, item, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            item.setIcon(QIcon(pixmap.scaled(112, 72, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)))

    def install_selected_pack(self):
        item = self.results.currentItem()
        pack = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not pack:
            QMessageBox.information(self, 'Seleziona un modpack', 'Seleziona prima un risultato Modrinth.')
            return
        self.install_button.setEnabled(False)
        self.install_progress.setValue(0)
        self.install_status.setText('Preparazione installazione…')
        self.install_worker = InstallWorker(pack['id'], pack['title'], pack.get('icon_url'))
        self.install_worker.progress.connect(self.install_progress_update)
        self.install_worker.completed.connect(self.install_success)
        self.install_worker.failed.connect(self.install_failed)
        self.install_worker.finished.connect(lambda: self.install_button.setEnabled(True))
        self.install_worker.start()

    def install_success(self, instance):
        self.install_progress.setValue(100)
        self.install_status.setText(f'{instance["name"]} installato.')
        self.refresh_instances()
        QMessageBox.information(self, 'Installazione completata', f'{instance["name"]} è stato installato. Vai in Le mie istanze per avviarlo.')

    def install_failed(self, message):
        self.install_status.setText('Installazione non riuscita.')
        self.log_console(f"[ERRORE INSTALLAZIONE] {message}")
        QMessageBox.warning(self, 'Installazione modpack', message)

    def launch_selected_instance(self):
        row = self.instance_list.currentRow()
        instances = self.store.list_instances()
        if row < 0 or row >= len(instances):
            QMessageBox.information(self, 'Seleziona un\'istanza', 'Seleziona prima un\'istanza installata.')
            return
        instance = instances[row]
        if instance.get('status') != 'installed':
            QMessageBox.information(self, 'Non installata', 'Questa istanza non è ancora installabile.')
            return
        offline_name = self.offline_name_input.text().strip() if hasattr(self, "offline_name_input") else ""
        if not self.account and not offline_name:
            QMessageBox.warning(self, "Nome giocatore mancante", "Scegli un nome offline nella pagina Account, oppure accedi con Microsoft.")
            self.navigate("Account")
            return
        self.launch_worker = LaunchWorker(instance, self.account, offline_name)
        self.launch_worker.output.connect(self.log_console)
        self.launch_worker.failed.connect(lambda message: (self.log_console("[ERRORE] " + message), QMessageBox.warning(self, "Avvio Minecraft", message)))
        self.navigate("Console")
        self.launch_worker.start()

    def show_pack_details(self, item):
        pack = item.data(Qt.ItemDataRole.UserRole)
        if pack:
            QMessageBox.information(self, pack["title"], f'{pack.get("description","")}\n\nAutore: {pack.get("author","Unknown")}\nDownload: {pack.get("downloads",0):,}\nID Modrinth: {pack.get("id","")}\n\nUsa il pulsante Installa per creare una nuova istanza separata.')

    def search_failed(self, message): QMessageBox.warning(self, "Ricerca non riuscita", message)
    def search_finished(self): self.search_button.setEnabled(True); self.search_button.setText("Cerca")

    def add_instance(self):
        name, ok = QInputDialog.getText(self, "Nuova istanza", "Nome:")
        if not ok: return
        version, ok = QInputDialog.getText(self, "Versione Minecraft", "Versione (es. 1.20.1):", text="1.20.1")
        if not ok: return
        loader, ok = QInputDialog.getItem(self, "Mod loader", "Seleziona:", ["Vanilla", "Fabric", "Forge", "NeoForge", "Quilt"], 0, False)
        if not ok: return
        try:
            self.store.add_instance(name, version, loader)
            self.refresh_instances()
        except ValueError as exc:
            QMessageBox.warning(self, "Istanza non creata", str(exc))

    def refresh_instances(self):
        if not hasattr(self, "instance_list"): return
        self.instance_list.clear()
        self.top_instance_combo.clear()
        
        for instance in self.store.list_instances():
            status_desc = f'{instance["name"]} • Minecraft {instance["minecraft_version"]} • {instance["loader"].title()} • {instance["status"]}'
            item = QListWidgetItem(status_desc)
            item.setData(Qt.ItemDataRole.UserRole, instance)
            item.setSizeHint(QSize(0, 90))
            self.instance_list.addItem(item)
            
            if instance.get("status") == "installed":
                self.top_instance_combo.addItem(instance.get("name", "Istanza"), instance)

            if instance.get("icon_url"):
                worker = CoverWorker(item, instance["icon_url"])
                worker.loaded.connect(self.set_pack_cover)
                self.cover_workers.append(worker)
                worker.finished.connect(lambda w=worker: self.cover_workers.remove(w) if w in self.cover_workers else None)
                worker.start()
                
        self.refresh_content_instances()

    def rename_selected_instance(self):
        item = self.instance_list.currentItem()
        instance = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not instance: return
        name, ok = QInputDialog.getText(self, "Rinomina istanza", "Nuovo nome:", text=instance.get("name", ""))
        if ok and name.strip():
            instance["name"] = name.strip()
            try:
                self.store.update_instance(instance["id"], instance)
                self.refresh_instances()
            except Exception as exc:
                QMessageBox.warning(self, "Istanza", str(exc))

    def delete_selected_instance(self):
        item = self.instance_list.currentItem()
        instance = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not instance: return
        answer = QMessageBox.question(self, "Elimina istanza", "Eliminare l'istanza selezionata e tutti i suoi file?")
        if answer != QMessageBox.StandardButton.Yes: return
        try:
            import shutil
            folder = Path(instance.get("directory", ""))
            if folder.is_dir(): shutil.rmtree(folder)
            self.store.remove_instance(instance["id"])
            self.refresh_instances()
        except Exception as exc:
            QMessageBox.warning(self, "Istanza", str(exc))

    def save_offline_name(self, value):
        val = value.strip()
        self.config["offline_username"] = val
        save_config(self.config)
        if hasattr(self, "account_label") and not self.account:
            self.account_label.setText(val if val else "cicciook")
            self.load_skin_head(val if val else "cicciook")

    def save_client_id(self):
        value = self.client_id_input.text().strip()
        if not value:
            QMessageBox.warning(self, "Client ID mancante", "Inserisci il Client ID pubblico dell'app Microsoft.")
            return
        self.config["microsoft_client_id"] = value
        save_config(self.config)
        QMessageBox.information(self, "Configurazione salvata", "Client ID salvato localmente.")

    def start_login(self):
        client_id = self.config.get("microsoft_client_id") or os.getenv("NO_LIMITS_MSA_CLIENT_ID") or DEFAULT_MICROSOFT_CLIENT_ID
        if not client_id:
            QMessageBox.warning(self, "Login non configurato", "Accesso Microsoft non configurato in questa build.")
            return
        self.config["microsoft_client_id"] = client_id
        save_config(self.config)
        self.login_button.setEnabled(False)
        self.login_button.setText("Attendo Microsoft…")
        self.login_status.setText("Apro la pagina di accesso Microsoft…")
        self.login_worker = LoginWorker(client_id)
        self.login_worker.progress.connect(self.login_status.setText)
        self.login_worker.completed.connect(self.login_success)
        self.login_worker.failed.connect(self.login_failed)
        self.login_worker.finished.connect(self.login_finished)
        self.login_worker.start()

    def login_success(self, profile):
        self.account = profile
        self.login_status.setText(f'Connesso come {profile.get("name","Minecraft player")}')
        self.update_account_ui()
        QMessageBox.information(self, "Accesso completato", f'Benvenuto, {profile.get("name","Minecraft player")}!')

    def login_failed(self, message):
        self.login_status.setText("Accesso non completato.")
        QMessageBox.warning(self, "Login Microsoft", message)

    def login_finished(self):
        self.login_button.setEnabled(True)
        self.login_button.setText("Account collegato" if self.account else "Accedi con Microsoft")

    def restore_session(self):
        client_id = self.config.get("microsoft_client_id") or os.getenv("NO_LIMITS_MSA_CLIENT_ID") or DEFAULT_MICROSOFT_CLIENT_ID
        if not client_id: return
        token = auth.saved_token(client_id)
        if not token: return
        self.login_status.setText("Ripristino sessione Microsoft…")
        self.session_worker = SessionWorker(client_id, token)
        self.session_worker.completed.connect(self.session_restored)
        self.session_worker.failed.connect(lambda _message: self.login_status.setText("Sessione scaduta: accedi di nuovo."))
        self.session_worker.start()

    def session_restored(self, profile):
        self.account = profile
        self.login_status.setText(f'Connesso come {profile.get("name","Minecraft player")}')
        self.update_account_ui()

    def logout(self):
        client_id = self.config.get("microsoft_client_id") or os.getenv("NO_LIMITS_MSA_CLIENT_ID", "")
        try: auth.forget(client_id)
        except Exception as exc: QMessageBox.warning(self, "Logout", str(exc)); return
        self.account = None
        self.login_status.setText("Account disconnesso.")
        self.update_account_ui()

    def load_skin_head(self, username):
        if not username: return
        self.skin_worker = SkinHeadWorker(username)
        self.skin_worker.loaded.connect(self.set_skin_head)
        self.skin_worker.start()

    def set_skin_head(self, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.skin_head.setPixmap(pixmap.scaled(28, 28, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            self.skin_head.setText("")

    def update_account_ui(self):
        if self.account:
            username = self.account.get("name", "cicciook")
            self.account_label.setText(username)
            self.status_label.setText("• Online")
            self.load_skin_head(username)
            if hasattr(self, "logout_button"): self.logout_button.setVisible(True)
            if hasattr(self, "login_button"): self.login_button.setText("Account collegato")
        else:
            name = self.config.get("offline_username", "cicciook")
            self.account_label.setText(name)
            self.status_label.setText("• Offline")
            self.load_skin_head(name)
            if hasattr(self, "logout_button"): self.logout_button.setVisible(False)
            if hasattr(self, "login_button"): self.login_button.setText("Accedi con Microsoft")
