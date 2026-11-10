DARK_STYLE = r"""
* { font-family: "Segoe UI", "Arial", sans-serif; }
QMainWindow, QWidget#Root { background: #090d18; color: #eaf0ff; }
QWidget#Sidebar { background: #0d1425; border-right: 1px solid #1c2b4a; }
QLabel { color: #eaf0ff; }
QLabel#Brand { font-size: 24px; font-weight: 900; letter-spacing: 2px; }
QLabel#BrandAccent { color: #438cff; font-size: 11px; font-weight: 700; letter-spacing: 4px; }
QLabel#Muted { color: #8394b8; }
QLabel#SectionTitle { font-size: 21px; font-weight: 800; }
QLabel#HeroTitle { font-size: 28px; font-weight: 900; }
QLabel#HeroSub { color: #d3ddf7; font-size: 13px; }
QPushButton { color: #eaf0ff; background: #17233b; border: 1px solid #2a3c60; border-radius: 9px; padding: 10px 13px; }
QPushButton:hover { background: #22365b; border-color: #4d83ff; }
QPushButton#Primary { background: #2868ed; border: 1px solid #4b8aff; font-weight: 800; }
QPushButton#Primary:hover { background: #4380ff; }
QPushButton#Nav { text-align: left; padding: 12px 14px; border: 0; background: transparent; color: #aebcda; }
QPushButton#Nav:hover { background: #172746; color: white; }
QPushButton#Nav[active="true"] { background: #17336b; color: white; border-left: 3px solid #438cff; }
QLineEdit, QComboBox, QListWidget { background: #101a2d; color: #eaf0ff; border: 1px solid #293c60; border-radius: 9px; padding: 11px; }
QListWidget::item { padding: 13px; border-bottom: 1px solid #22304b; }
QListWidget::item:selected { background: #1b3565; }
QFrame#Panel { background: #111b2e; border: 1px solid #233657; border-radius: 15px; }
QFrame#Hero { background: #101f42; border: 1px solid #2853a1; border-radius: 18px; }
QFrame#PackCard { background: #121e33; border: 1px solid #2a3c5e; border-radius: 12px; }
QTabWidget::pane { border: 0; }
QScrollArea { border: 0; background: transparent; }
"""