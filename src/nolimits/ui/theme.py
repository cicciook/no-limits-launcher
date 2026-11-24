"""Tema grafico di No Limits Launcher.

Tutta l'estetica vive qui: la palette è definita una volta sola e il foglio di
stile Qt viene generato a partire dai token, così main_window.py non ha più
bisogno di stili inline (tranne pochi casi dinamici, come il gradiente dell'hero).
"""
from pathlib import Path

# ---------------------------------------------------------------- palette
BG_0 = "#07050f"
BG_1 = "#0d0a1b"
BG_2 = "#140f28"
SURFACE = "rgba(255, 255, 255, 0.035)"
SURFACE_HOVER = "rgba(139, 92, 246, 0.12)"
BORDER = "rgba(255, 255, 255, 0.07)"
BORDER_ACCENT = "rgba(167, 139, 250, 0.35)"

TEXT = "#f4f0ff"
TEXT_MUTED = "#9d94c4"
TEXT_SUBTLE = "#6c6490"

VIOLET = "#8b5cf6"
VIOLET_DEEP = "#7c3aed"
PURPLE = "#a855f7"
SKY = "#38bdf8"
GREEN = "#4ade80"
AMBER = "#fbbf24"

GRAD_PRIMARY = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {VIOLET_DEEP}, stop:1 {PURPLE})"
GRAD_PRIMARY_HOVER = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {VIOLET}, stop:1 #c084fc)"
GRAD_PLAY = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {VIOLET_DEEP}, stop:1 {SKY})"
GRAD_PLAY_HOVER = f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {VIOLET}, stop:1 #7dd3fc)"

APP_DIR = Path.home() / ".no-limits-launcher"


def _chevron_url() -> str:
    """Scrive (una volta) la freccia dei combo box e ne restituisce l'url per QSS."""
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 12">'
        '<path d="M2.5 4.5 6 8l3.5-3.5" fill="none" stroke="#b9a7ff" stroke-width="1.6" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )
    try:
        target = APP_DIR / "assets" / "chevron.svg"
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_text(encoding="utf-8") != svg:
            target.write_text(svg, encoding="utf-8")
        return target.as_posix()
    except OSError:
        return ""


def build_style() -> str:
    chevron = _chevron_url()
    arrow_rule = f"image: url({chevron});" if chevron else ""

    return f"""
* {{
    font-family: "Segoe UI", "Inter", "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    outline: none;
}}

QMainWindow {{ background: {BG_0}; }}
QWidget#Root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {BG_1}, stop:0.5 {BG_2}, stop:1 {BG_0});
}}
QLabel {{ color: {TEXT}; background: transparent; border: none; }}
QLabel#Muted {{ color: {TEXT_MUTED}; }}
QDialog, QMessageBox, QInputDialog {{ background: {BG_2}; }}

/* ------------------------------------------------------------ sidebar */
QFrame#Sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(24, 17, 48, 0.96), stop:1 rgba(12, 9, 26, 0.96));
    border: 1px solid {BORDER_ACCENT};
    border-radius: 20px;
}}
QLabel#SectionCap {{
    color: {TEXT_SUBTLE};
    font-size: 10px;
    font-weight: 700;
    padding: 10px 6px 2px 6px;
}}
QFrame#SidebarDivider {{ background: {BORDER}; border: none; max-height: 1px; min-height: 1px; }}

QPushButton#Nav {{
    text-align: left;
    padding: 10px 14px;
    border: 1px solid transparent;
    border-radius: 12px;
    background: transparent;
    color: {TEXT_MUTED};
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#Nav:hover {{ background: {SURFACE_HOVER}; color: {TEXT}; }}
QPushButton#Nav:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(139, 92, 246, 0.42), stop:1 rgba(139, 92, 246, 0.06));
    border: 1px solid rgba(167, 139, 250, 0.35);
    color: #ffffff;
    font-weight: 700;
}}

QFrame#PlayerChip {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 14px;
}}
QLabel#PlayerName {{ font-size: 13px; font-weight: 700; color: {TEXT}; }}
QLabel#StatusLabel {{ font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; }}
QLabel#StatusLabel[online="true"] {{ color: {GREEN}; }}
QLabel#StatusLabel[online="false"] {{ color: {AMBER}; }}
QLabel#SkinHead {{
    background: rgba(139, 92, 246, 0.25);
    border: 1px solid {BORDER_ACCENT};
    border-radius: 10px;
    color: #c4b5fd;
    font-size: 16px;
}}
QLabel#VersionTag {{ color: {TEXT_SUBTLE}; font-size: 10px; padding-left: 4px; }}

/* -------------------------------------------------------- right panel */
QFrame#RightPanel {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(24, 17, 48, 0.85), stop:1 rgba(12, 9, 26, 0.85));
    border: 1px solid {BORDER_ACCENT};
    border-radius: 20px;
}}
QPushButton#ChipCurse {{
    background: rgba(255, 125, 50, 0.12); border: 1px solid rgba(255, 125, 50, 0.40);
    color: #ff9a5c; border-radius: 10px; padding: 6px 10px; font-size: 11px; font-weight: 700;
}}
QPushButton#ChipCurse:hover {{ background: rgba(255, 125, 50, 0.24); }}
QPushButton#ChipModrinth {{
    background: rgba(27, 217, 106, 0.12); border: 1px solid rgba(27, 217, 106, 0.40);
    color: #34e58a; border-radius: 10px; padding: 6px 10px; font-size: 11px; font-weight: 700;
}}
QPushButton#ChipModrinth:hover {{ background: rgba(27, 217, 106, 0.24); }}
QPushButton#ServerButton {{
    text-align: left; padding: 10px 14px; border-radius: 12px;
    background: {SURFACE}; border: 1px solid {BORDER}; color: {TEXT}; font-weight: 700;
}}
QPushButton#ServerButton:hover {{ background: {SURFACE_HOVER}; border-color: {VIOLET}; }}
QListWidget#FriendsList {{ background: transparent; border: none; }}
QListWidget#FriendsList::item {{ color: {TEXT_SUBTLE}; padding: 8px 6px; }}

/* ------------------------------------------------------------ play bar */
QFrame#PlayBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(30, 20, 60, 0.90), stop:1 rgba(16, 12, 36, 0.90));
    border: 1px solid {BORDER_ACCENT};
    border-radius: 18px;
}}
QLabel#PlayBarCap {{ color: {TEXT_SUBTLE}; font-size: 10px; font-weight: 700; }}
QPushButton#PlayButton {{
    background: {GRAD_PLAY};
    color: #ffffff;
    border: 1px solid rgba(255, 255, 255, 0.22);
    border-radius: 14px;
    padding: 13px 34px;
    font-size: 15px;
    font-weight: 800;
}}
QPushButton#PlayButton:hover {{ background: {GRAD_PLAY_HOVER}; }}
QPushButton#PlayButton:pressed {{ background: {VIOLET_DEEP}; }}
QFrame#AdBanner {{
    background: rgba(255, 255, 255, 0.02);
    border: 1px dashed rgba(167, 139, 250, 0.28);
    border-radius: 12px;
}}
QLabel#AdLabel {{ color: rgba(255, 255, 255, 0.30); font-size: 11px; font-weight: 700; }}

/* ------------------------------------------------------------ headings */
QLabel#GreetingTitle {{ font-size: 26px; font-weight: 800; color: #ffffff; }}
QLabel#PageTitle {{ font-size: 24px; font-weight: 800; color: #ffffff; }}
QLabel#PageSubtitle {{ font-size: 13px; color: {TEXT_MUTED}; }}
QLabel#PanelTitle {{ font-size: 15px; font-weight: 700; color: #ffffff; }}
QLabel#BlockTitle {{ font-size: 16px; font-weight: 800; color: #ffffff; }}

/* -------------------------------------------------------------- inputs */
QLineEdit {{
    background: rgba(255, 255, 255, 0.045);
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 10px 14px;
    selection-background-color: {VIOLET_DEEP};
}}
QLineEdit:hover {{ border-color: rgba(167, 139, 250, 0.30); }}
QLineEdit:focus {{ border: 1px solid {VIOLET}; background: rgba(139, 92, 246, 0.08); }}
QLineEdit#SearchInput {{
    padding: 13px 18px;
    font-size: 14px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid {BORDER_ACCENT};
}}

QComboBox {{
    background: rgba(255, 255, 255, 0.045);
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 9px 14px;
    font-weight: 600;
}}
QComboBox:hover {{ border-color: rgba(167, 139, 250, 0.45); }}
QComboBox::drop-down {{ border: none; width: 30px; }}
QComboBox::down-arrow {{ {arrow_rule} width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: #18122e;
    color: {TEXT};
    border: 1px solid rgba(167, 139, 250, 0.40);
    border-radius: 10px;
    padding: 4px;
    selection-background-color: {VIOLET_DEEP};
    outline: 0;
}}

/* ------------------------------------------------------------- buttons */
QPushButton {{
    color: {TEXT};
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 12px;
    padding: 9px 18px;
    font-weight: 600;
}}
QPushButton:hover {{ background: rgba(139, 92, 246, 0.22); border-color: {VIOLET}; }}
QPushButton:pressed {{ background: rgba(139, 92, 246, 0.35); }}
QPushButton:disabled {{ color: {TEXT_SUBTLE}; background: rgba(255, 255, 255, 0.025); border-color: rgba(255, 255, 255, 0.05); }}

QPushButton#Primary {{
    background: {GRAD_PRIMARY};
    border: 1px solid rgba(255, 255, 255, 0.20);
    color: #ffffff;
    font-weight: 800;
}}
QPushButton#Primary:hover {{ background: {GRAD_PRIMARY_HOVER}; }}
QPushButton#Primary:pressed {{ background: {VIOLET_DEEP}; }}
QPushButton#Primary:disabled {{ background: rgba(139, 92, 246, 0.18); color: rgba(255, 255, 255, 0.45); border-color: transparent; }}

QPushButton#SecondaryAction {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid {BORDER};
    color: #cdbfff;
    padding: 6px 12px;
    border-radius: 9px;
    font-size: 11px;
}}
QPushButton#SecondaryAction:hover {{ background: rgba(139, 92, 246, 0.25); border-color: {VIOLET}; color: #ffffff; }}
QPushButton#LinkButton {{
    background: transparent; border: none; color: #c4b5fd; font-weight: 700; padding: 4px 8px;
}}
QPushButton#LinkButton:hover {{ color: #ffffff; background: transparent; }}

/* --------------------------------------------------------------- cards */
QFrame#Panel, QFrame#ContentIntro {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QFrame#ContentIntro {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(139, 92, 246, 0.20), stop:1 rgba(56, 189, 248, 0.07));
    border: 1px solid {BORDER_ACCENT};
}}

QFrame#HeroFrame {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #2a1763, stop:1 #0e0a22);
    border: 1px solid {BORDER_ACCENT};
    border-radius: 26px;
}}
QFrame#HeroContent {{ background: transparent; border: none; }}
QLabel#HeroTitle {{ font-size: 28px; font-weight: 900; color: #ffffff; }}
QLabel#HeroDesc {{ font-size: 13px; color: #ddd6fe; }}
QLabel#Tag {{
    background: rgba(255, 255, 255, 0.10);
    color: #efe9ff;
    padding: 4px 12px;
    border-radius: 11px;
    font-size: 11px;
    font-weight: 700;
}}

QFrame#FeatureCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 22px;
}}
QFrame#FeatureCard:hover {{ background: {SURFACE_HOVER}; border: 1px solid {VIOLET}; }}
QLabel#FeatureTitle {{ font-size: 13px; font-weight: 800; color: #ffffff; }}
QLabel#FeatureMeta {{ font-size: 11px; color: #e4dcff; font-weight: 700; background: rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 3px 12px; }}

QFrame#ResultCard {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 20px;
}}
QFrame#ResultCard:hover {{ background: {SURFACE_HOVER}; border: 1px solid rgba(167, 139, 250, 0.55); }}
QFrame#ResultCard[selected="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(139, 92, 246, 0.30), stop:1 rgba(139, 92, 246, 0.08));
    border: 1px solid {VIOLET};
}}
QWidget#ScrollBody {{ background: transparent; }}
QLabel#ContentTitle {{ color: #ffffff; font-size: 14px; font-weight: 800; }}
QLabel#ContentDescription {{ color: {TEXT_MUTED}; font-size: 12px; }}
QLabel#ContentAuthor {{ color: #d8ccff; font-size: 11px; font-weight: 700; }}
QLabel#ContentVersion {{ color: {SKY}; font-size: 11px; font-weight: 600; }}
QLabel#BadgeOk {{
    background: rgba(74, 222, 128, 0.14); color: {GREEN}; border: 1px solid rgba(74, 222, 128, 0.35);
    border-radius: 9px; padding: 2px 10px; font-size: 10px; font-weight: 800;
}}
QLabel#BadgeWarn {{
    background: rgba(251, 191, 36, 0.14); color: {AMBER}; border: 1px solid rgba(251, 191, 36, 0.35);
    border-radius: 9px; padding: 2px 10px; font-size: 10px; font-weight: 800;
}}

/* --------------------------------------------------------------- lists */
QListWidget {{
    background: transparent;
    border: none;
    padding: 2px;
    color: {TEXT};
}}
QListWidget::item {{
    background: transparent;
    border: none;
    padding: 0px;
    margin: 0px;
}}
QListWidget::item:selected, QListWidget::item:hover {{ background: transparent; }}

/* ---------------------------------------------------------------- tabs */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.02);
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 9px 20px;
    margin-right: 4px;
    font-weight: 700;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}}
QTabBar::tab:hover {{ color: #ffffff; background: rgba(255, 255, 255, 0.04); }}
QTabBar::tab:selected {{ color: #ffffff; background: rgba(139, 92, 246, 0.30); }}

/* ------------------------------------------------------------- console */
QPlainTextEdit {{
    background: #06040d;
    color: #a7f3c8;
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 14px;
    font-family: "JetBrains Mono", "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace;
    font-size: 12px;
    selection-background-color: {VIOLET_DEEP};
}}

/* ------------------------------------------------------------ progress */
QProgressBar {{
    background: rgba(255, 255, 255, 0.05);
    color: #ffffff;
    border: 1px solid {BORDER};
    border-radius: 9px;
    min-height: 18px;
    text-align: center;
    font-size: 11px;
    font-weight: 700;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {VIOLET_DEEP}, stop:1 {SKY});
    border-radius: 8px;
}}

/* ----------------------------------------------------------- scrollbar */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: rgba(167, 139, 250, 0.28); border-radius: 4px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(167, 139, 250, 0.55); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: rgba(167, 139, 250, 0.28); border-radius: 4px; min-width: 36px; }}
QScrollBar::handle:horizontal:hover {{ background: rgba(167, 139, 250, 0.55); }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; background: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

QToolTip {{
    background: #1b1436; color: {TEXT}; border: 1px solid rgba(167, 139, 250, 0.5);
    border-radius: 6px; padding: 6px 8px;
}}
"""


DARK_STYLE = build_style()
