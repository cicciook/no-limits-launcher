DARK_STYLE = r"""
* { font-family: "Segoe UI", "Arial", sans-serif; }
QMainWindow, QWidget#Root { background: #090d18; color: #eaf0ff; }
QWidget#Sidebar { background: #080d1b; border-right: 1px solid #27365e; }
QLabel { color: #eaf0ff; }
QLabel#Brand { font-size: 25px; font-weight: 1000; letter-spacing: 2px; color:#f3f5ff; }
QLabel#BrandAccent { color: #438cff; font-size: 11px; font-weight: 700; letter-spacing: 4px; }
QLabel#Muted { color: #8394b8; }
QLabel#SectionTitle { font-size: 21px; font-weight: 800; }
QLabel#HeroTitle { font-size: 28px; font-weight: 900; }
QLabel#HeroSub { color: #d3ddf7; font-size: 13px; }
QPushButton { color: #eaf0ff; background: #17233b; border: 1px solid #2a3c60; border-radius: 9px; padding: 10px 13px; }
QPushButton:hover { background: #22365b; border-color: #4d83ff; }
QPushButton#Primary { background: #2868ed; border: 1px solid #4b8aff; font-weight: 800; }
QPushButton#Primary:hover { background: #4380ff; }
QPushButton#Nav { text-align: left; padding: 13px 14px; border: 0; border-radius:11px; background: transparent; color: #aebcda; font-size:13px; font-weight:650; }
QPushButton#Nav:hover { background: #172746; color: white; }
QPushButton#Nav[active="true"] { background: #192b58; color: white; border-left: 3px solid #9b8cff; }
QLineEdit, QComboBox, QListWidget, QPlainTextEdit { background: #101a2d; color: #eaf0ff; border: 1px solid #293c60; border-radius: 9px; padding: 11px; }
QListWidget::item { padding: 13px; border-bottom: 1px solid #22304b; border-radius: 8px; margin: 3px; }
QListWidget::item:selected { background: #1b3565; }
QFrame#Panel { background: #111b2e; border: 1px solid #233657; border-radius: 15px; }
QFrame#Hero { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #111d3d,stop:.55 #172b59,stop:1 #271b4c); border: 1px solid #4654a4; border-radius: 20px; }
QFrame#PackCard { background: #121e33; border: 1px solid #2a3c5e; border-radius: 12px; }
QTabWidget::pane { border: 0; }
QScrollArea { border: 0; background: transparent; }
QPlainTextEdit { background: #070b13; color: #9fe8bd; border: 1px solid #263957; border-radius: 12px; padding: 12px; font-family: Consolas, monospace; font-size: 12px; }
QProgressBar { background: #0b1425; color: #eaf0ff; border: 1px solid #2a416a; border-radius: 7px; min-height: 17px; text-align: center; font-weight: 700; }
QProgressBar::chunk { background: #3478ff; border-radius: 6px; }
QPushButton:disabled { color: #64738f; background: #111a2b; border-color: #202e47; }
QToolTip { background: #17233b; color: #f1f5ff; border: 1px solid #4b78c8; padding: 5px; }

QFrame#ContentIntro { background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #14264a,stop:1 #17203a); border: 1px solid #344c7b; border-radius: 14px; }
QListWidget#ContentResults { background: transparent; border: 0; padding: 2px; }
QFrame#ContentResultCard { background: #111d32; border: 1px solid #2a3d60; border-radius: 13px; }
QFrame#ContentResultCard:hover { background: #172846; border: 1px solid #4a73b8; }
QLabel#ContentCover { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #263c67,stop:1 #17223b); border: 1px solid #405985; border-radius: 10px; color: #9fb6df; font-size: 9px; font-weight: 800; }
QLabel#ContentTitle { color: #f2f6ff; font-size: 14px; font-weight: 800; background: transparent; }
QLabel#ContentDescription { color: #8fa2c4; font-size: 11px; background: transparent; }
QLabel#ContentAuthor { color: #d6e1f6; font-size: 11px; font-weight: 700; background: transparent; }
QLabel#ContentVersion { color: #7fa6ed; font-size: 10px; background: transparent; }
QPushButton#SecondaryAction { background: #1a2b49; border: 1px solid #39547e; color: #bcd2f5; padding: 7px 10px; border-radius: 8px; font-size: 11px; }
QPushButton#SecondaryAction:hover { background: #25416d; border-color: #6395ec; color: white; }

"""