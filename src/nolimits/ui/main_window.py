from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem, QTabWidget, QMessageBox, QInputDialog)
from nolimits.providers.modrinth import ModrinthProvider
from nolimits.core.instances import InstanceStore
from .theme import DARK_STYLE

class SearchWorker(QThread):
    completed = Signal(list)
    failed = Signal(str)
    def __init__(self, query: str):
        super().__init__(); self.query = query
    def run(self):
        try: self.completed.emit(ModrinthProvider().search_modpacks(self.query))
        except Exception as exc: self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("No Limits Launcher"); self.resize(1100, 720); self.setMinimumSize(820, 560); self.setStyleSheet(DARK_STYLE)
        self.store = InstanceStore(); self.worker = None
        central = QWidget(); self.setCentralWidget(central); layout = QVBoxLayout(central); layout.setContentsMargins(28,24,28,24); layout.setSpacing(16)
        header = QHBoxLayout(); brand_col = QVBoxLayout(); brand = QLabel("NO LIMITS"); brand.setObjectName("Brand"); subtitle = QLabel("MINECRAFT, WITHOUT LIMITS."); subtitle.setObjectName("Subtitle"); brand_col.addWidget(brand); brand_col.addWidget(subtitle); header.addLayout(brand_col); header.addStretch(); self.status = QLabel("DESKTOP PREVIEW  •  v0.1.0"); self.status.setObjectName("Subtitle"); header.addWidget(self.status); layout.addLayout(header)
        self.tabs = QTabWidget(); layout.addWidget(self.tabs)
        self.catalog_tab = QWidget(); catalog = QVBoxLayout(self.catalog_tab); search_row = QHBoxLayout(); self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Cerca modpack su Modrinth…"); self.search_input.returnPressed.connect(self.search_modpacks); self.search_button = QPushButton("Cerca"); self.search_button.setObjectName("Primary"); self.search_button.clicked.connect(self.search_modpacks); search_row.addWidget(self.search_input,1); search_row.addWidget(self.search_button); catalog.addLayout(search_row); self.results = QListWidget(); self.results.itemDoubleClicked.connect(self.show_pack_details); catalog.addWidget(self.results,1); self.tabs.addTab(self.catalog_tab,"Catalogo")
        self.instances_tab = QWidget(); instances = QVBoxLayout(self.instances_tab); row = QHBoxLayout(); row.addWidget(QLabel("Le tue installazioni indipendenti")); row.addStretch(); add_btn = QPushButton("+ Nuova istanza"); add_btn.setObjectName("Primary"); add_btn.clicked.connect(self.add_instance); row.addWidget(add_btn); instances.addLayout(row); self.instance_list = QListWidget(); instances.addWidget(self.instance_list,1); self.tabs.addTab(self.instances_tab,"Le mie istanze")
        self.about_tab = QWidget(); about = QVBoxLayout(self.about_tab); about.addWidget(QLabel("Un launcher. Tutte le tue versioni.")); about.addWidget(QLabel("Primo prototipo: ricerca Modrinth e registro locale delle istanze attivi. Installazione, CurseForge, login Microsoft e avvio del gioco sono in sviluppo.")); about.addStretch(); self.tabs.addTab(self.about_tab,"Info"); self.refresh_instances()
    def search_modpacks(self):
        query=self.search_input.text().strip(); self.search_button.setEnabled(False); self.search_button.setText("Ricerca…"); self.results.clear(); self.worker=SearchWorker(query); self.worker.completed.connect(self.show_results); self.worker.failed.connect(self.search_failed); self.worker.finished.connect(self.search_finished); self.worker.start()
    def show_results(self,packs):
        if not packs: self.results.addItem("Nessun modpack trovato."); return
        for pack in packs:
            item=QListWidgetItem(f'{pack["title"]}\n{pack["author"]}  •  {pack["downloads"]:,} download\n{pack["description"]}'); item.setData(Qt.ItemDataRole.UserRole,pack); self.results.addItem(item)
    def show_pack_details(self,item):
        pack=item.data(Qt.ItemDataRole.UserRole)
        if pack: QMessageBox.information(self,pack["title"],f'{pack["description"]}\n\nAutore: {pack["author"]}\nID Modrinth: {pack["id"]}\n\nInstallazione del modpack: in sviluppo.')
    def search_failed(self,message): QMessageBox.warning(self,"Ricerca non riuscita",message)
    def search_finished(self): self.search_button.setEnabled(True); self.search_button.setText("Cerca")
    def add_instance(self):
        name,ok=QInputDialog.getText(self,"Nuova istanza","Nome:")
        if not ok:return
        version,ok=QInputDialog.getText(self,"Versione Minecraft","Versione (es. 1.20.1):",text="1.20.1")
        if not ok:return
        loader,ok=QInputDialog.getItem(self,"Mod loader","Seleziona:",["Vanilla","Fabric","Forge","NeoForge","Quilt"],0,False)
        if not ok:return
        try:self.store.add_instance(name,version,loader);self.refresh_instances()
        except ValueError as exc:QMessageBox.warning(self,"Istanza non creata",str(exc))
    def refresh_instances(self):
        self.instance_list.clear()
        for instance in self.store.list_instances():self.instance_list.addItem(f'{instance["name"]}  •  Minecraft {instance["minecraft_version"]}  •  {instance["loader"].title()}  •  {instance["status"]}')
