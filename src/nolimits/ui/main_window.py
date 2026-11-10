import os, json, webbrowser
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QInputDialog, QFrame, QStackedWidget, QGridLayout, QScrollArea, QProgressBar)
from nolimits.providers.modrinth import ModrinthProvider
from nolimits.core.instances import InstanceStore
from nolimits.core.modpacks import install_modrinth_project, launch_instance
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

class SearchWorker(QThread):
    completed = Signal(list); failed = Signal(str)
    def __init__(self, query): super().__init__(); self.query=query
    def run(self):
        try: self.completed.emit(ModrinthProvider().search_modpacks(self.query))
        except Exception as exc: self.failed.emit(str(exc))

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
    completed = Signal(dict); failed = Signal(str); progress = Signal(str)
    def __init__(self, project_id, title): super().__init__(); self.project_id=project_id; self.title=title
    def run(self):
        try: self.completed.emit(install_modrinth_project(self.project_id,self.title,self.progress.emit))
        except Exception as exc: self.failed.emit(str(exc))

class LaunchWorker(QThread):
    completed = Signal(); failed = Signal(str)
    def __init__(self, instance, profile): super().__init__(); self.instance=instance; self.profile=profile
    def run(self):
        try: launch_instance(self.instance,self.profile); self.completed.emit()
        except Exception as exc: self.failed.emit(str(exc))

class LoginWorker(QThread):
    completed = Signal(dict); failed = Signal(str); progress = Signal(str)
    def __init__(self, client_id): super().__init__(); self.client_id=client_id
    def run(self):
        try:
            profile=auth.login(self.client_id, self.progress.emit, webbrowser.open)
            self.completed.emit(profile)
        except Exception as exc: self.failed.emit(str(exc))

class SessionWorker(QThread):
    completed = Signal(dict); failed = Signal(str)
    def __init__(self, client_id, token): super().__init__(); self.client_id=client_id; self.token=token
    def run(self):
        try: self.completed.emit(auth.refresh(self.client_id,self.token,lambda _message: None))
        except Exception as exc: self.failed.emit(str(exc))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("No Limits Launcher"); self.resize(1320, 820); self.setMinimumSize(980, 650); self.setStyleSheet(DARK_STYLE)
        self.store=InstanceStore(); self.config=load_config(); self.account=None; self.search_worker=None; self.login_worker=None; self.session_worker=None; self.install_worker=None; self.launch_worker=None; self.cover_workers=[]
        self.root=QWidget(); self.root.setObjectName("Root"); self.setCentralWidget(self.root)
        outer=QHBoxLayout(self.root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        self.sidebar=QFrame(); self.sidebar.setObjectName("Sidebar"); self.sidebar.setFixedWidth(218); side=QVBoxLayout(self.sidebar); side.setContentsMargins(15,24,15,18); side.setSpacing(8)
        brand=QLabel("Ｎ  NO LIMITS"); brand.setObjectName("Brand"); side.addWidget(brand)
        sub=QLabel("M I N E C R A F T   L A U N C H E R"); sub.setObjectName("BrandAccent"); side.addWidget(sub); side.addSpacing(24)
        self.nav_buttons={}; self.stack=QStackedWidget()
        for label,icon in [("Home","⌂"),("Catalogo","▦"),("Le mie istanze","▤"),("Mod","✥"),("Shader","◇"),("Resource Pack","▣"),("Impostazioni","⚙"),("Account","♙"),("Info","ⓘ")]:
            btn=QPushButton(f"{icon}   {label}"); btn.setObjectName("Nav"); btn.setProperty("active",label=="Home"); btn.clicked.connect(lambda checked=False,n=label:self.navigate(n)); side.addWidget(btn); self.nav_buttons[label]=btn
        side.addStretch()
        self.account_label=QLabel("●  Account non collegato"); self.account_label.setObjectName("Muted"); side.addWidget(self.account_label)
        outer.addWidget(self.sidebar); outer.addWidget(self.stack,1)
        self.pages={}
        for name in ["Home","Catalogo","Le mie istanze","Mod","Shader","Resource Pack","Impostazioni","Account","Info"]:
            page=QWidget(); page_layout=QVBoxLayout(page); page_layout.setContentsMargins(28,24,28,24); page_layout.setSpacing(16); self.pages[name]=page; self.stack.addWidget(page)
        self.build_home(); self.build_catalog(); self.build_instances(); self.build_simple_pages(); self.navigate("Home")
        self.update_account_ui(); self.restore_session()

    def panel(self, title=None, subtitle=None):
        frame=QFrame(); frame.setObjectName("Panel"); box=QVBoxLayout(frame); box.setContentsMargins(18,16,18,16); box.setSpacing(9)
        if title:
            t=QLabel(title); t.setStyleSheet("font-size:16px;font-weight:800;"); box.addWidget(t)
        if subtitle:
            s=QLabel(subtitle); s.setObjectName("Muted"); s.setWordWrap(True); box.addWidget(s)
        return frame,box

    def page_header(self,page,title,desc):
        box=QVBoxLayout(); t=QLabel(title); t.setObjectName("SectionTitle"); d=QLabel(desc); d.setObjectName("Muted"); box.addWidget(t); box.addWidget(d); self.pages[page].layout().addLayout(box)

    def build_home(self):
        p=self.pages["Home"]; self.page_header("Home","Benvenuto in No Limits","Minecraft, senza limiti. Tutte le tue versioni, in un unico launcher.")
        hero=QFrame(); hero.setObjectName("Hero"); h=QHBoxLayout(hero); h.setContentsMargins(26,24,26,24)
        left=QVBoxLayout(); eyebrow=QLabel("MODPACK IN EVIDENZA  •  MODRINTH"); eyebrow.setObjectName("BrandAccent"); left.addWidget(eyebrow)
        title=QLabel("La tua prossima\navventura ti aspetta."); title.setObjectName("HeroTitle"); left.addWidget(title)
        desc=QLabel("Scopri modpack, crea istanze separate e gioca con il tuo setup preferito."); desc.setObjectName("HeroSub"); desc.setWordWrap(True); left.addWidget(desc)
        go=QPushButton("Esplora il catalogo  →"); go.setObjectName("Primary"); go.clicked.connect(lambda:self.navigate("Catalogo")); left.addWidget(go,0,Qt.AlignmentFlag.AlignLeft); h.addLayout(left,2)
        art=QVBoxLayout(); glyph=QLabel("✦  ⛏  ◈"); glyph.setAlignment(Qt.AlignmentFlag.AlignCenter); glyph.setStyleSheet("font-size:54px;color:#6ea4ff;font-weight:900;"); art.addWidget(glyph); art.addWidget(QLabel("NO LIMITS  /  YOUR WORLD"),0,Qt.AlignmentFlag.AlignCenter); h.addLayout(art,1); p.layout().addWidget(hero)
        row=QHBoxLayout()
        for title,desc,action in [("Catalogo modpack","Cerca su Modrinth e CurseForge","Catalogo"),("Multi-versione","Istanze Minecraft indipendenti","Le mie istanze"),("Account Microsoft","Collega il tuo profilo Minecraft","Account")]:
            card,box=self.panel(title,desc); b=QPushButton("Apri →"); b.clicked.connect(lambda checked=False,n=action:self.navigate(n)); box.addWidget(b); row.addWidget(card)
        p.layout().addLayout(row)
        heading=QLabel("Accesso rapido"); heading.setObjectName("SectionTitle"); p.layout().addWidget(heading)
        quick=QHBoxLayout()
        for name,detail in [("Forge / NeoForge","Mod loader"),("Fabric / Quilt","Mod loader"),("Shader e resource pack","Personalizzazione")]:
            card,box=self.panel(name,detail); quick.addWidget(card)
        p.layout().addLayout(quick); p.layout().addStretch()

    def build_catalog(self):
        p=self.pages["Catalogo"]; self.page_header("Catalogo","Catalogo modpack","Cerca modpack su Modrinth. Il connettore CurseForge verrà attivato con API key autorizzata.")
        row=QHBoxLayout(); self.search_input=QLineEdit(); self.search_input.setPlaceholderText("Cerca modpack…"); self.search_input.returnPressed.connect(self.search_modpacks); row.addWidget(self.search_input,1)
        self.source=QPushButton("Modrinth  ✓"); self.source.setEnabled(False); row.addWidget(self.source)
        self.search_button=QPushButton("Cerca / più popolari"); self.search_button.setObjectName("Primary"); self.search_button.clicked.connect(self.search_modpacks); row.addWidget(self.search_button); p.layout().addLayout(row)
        self.results=QListWidget(); self.results.setIconSize(QPixmap(112,72).size()); self.results.setSpacing(7); self.results.itemDoubleClicked.connect(self.show_pack_details); p.layout().addWidget(self.results,1)
        actions=QHBoxLayout(); self.install_button=QPushButton("Installa modpack selezionato"); self.install_button.setObjectName("Primary"); self.install_button.clicked.connect(self.install_selected_pack); actions.addWidget(self.install_button); self.install_status=QLabel(""); self.install_status.setObjectName("Muted"); actions.addWidget(self.install_status,1); p.layout().addLayout(actions)
        note=QLabel("Seleziona un risultato e premi Installa: il launcher scarica il pacchetto .mrpack e prepara un'istanza isolata."); note.setObjectName("Muted"); p.layout().addWidget(note)

    def build_instances(self):
        p=self.pages["Le mie istanze"]; self.page_header("Le mie istanze","Le tue installazioni","Ogni istanza avrà cartella, versione Minecraft e mod loader indipendenti.")
        row=QHBoxLayout(); launch=QPushButton("▶ Avvia selezionata"); launch.setObjectName("Primary"); launch.clicked.connect(self.launch_selected_instance); row.addWidget(launch); row.addStretch(); add=QPushButton("+ Nuova istanza"); add.setObjectName("Primary"); add.clicked.connect(self.add_instance); row.addWidget(add); p.layout().addLayout(row)
        self.instance_list=QListWidget(); p.layout().addWidget(self.instance_list,1); self.refresh_instances()

    def build_simple_pages(self):
        for name,desc in [("Mod","Gestione delle mod per ogni istanza."),("Shader","Gestisci shader pack e impostazioni grafiche."),("Resource Pack","Organizza texture e resource pack."),("Impostazioni","Percorsi Java, memoria RAM, lingua e preferenze."),("Account","Accedi con il tuo account Microsoft per giocare a Minecraft."),("Info","No Limits Launcher — un launcher indipendente, in sviluppo.")]:
            self.page_header(name,name,desc)
            if name=="Account":
                card,box=self.panel("Account Microsoft","Autenticazione ufficiale tramite Device Code Flow. Non chiediamo né memorizziamo la password Microsoft.")
                self.login_status=QLabel("Non hai ancora collegato un account."); self.login_status.setObjectName("Muted"); box.addWidget(self.login_status)
                self.client_id_input=QLineEdit(); self.client_id_input.setPlaceholderText("Microsoft Application (Client) ID"); self.client_id_input.setText(self.config.get("microsoft_client_id",os.getenv("NO_LIMITS_MSA_CLIENT_ID",DEFAULT_MICROSOFT_CLIENT_ID))); box.addWidget(self.client_id_input)
                save=QPushButton("Salva Client ID"); save.clicked.connect(self.save_client_id); box.addWidget(save,0,Qt.AlignmentFlag.AlignLeft)
                self.login_button=QPushButton("Accedi con Microsoft"); self.login_button.setObjectName("Primary"); self.login_button.clicked.connect(self.start_login); box.addWidget(self.login_button,0,Qt.AlignmentFlag.AlignLeft)
                self.logout_button=QPushButton("Disconnetti account"); self.logout_button.clicked.connect(self.logout); self.logout_button.setVisible(False); box.addWidget(self.logout_button,0,Qt.AlignmentFlag.AlignLeft)
                p=self.pages[name]; p.layout().addWidget(card); p.layout().addStretch()
            elif name=="Impostazioni":
                card,box=self.panel("Configurazione Microsoft","Inserisci il Client ID pubblico dell'app registrata in Microsoft Entra. Non inserire un client secret.")
                b=QPushButton("Configura account Microsoft"); b.clicked.connect(lambda:self.navigate("Account")); box.addWidget(b,0,Qt.AlignmentFlag.AlignLeft); self.pages[name].layout().addWidget(card); self.pages[name].layout().addStretch()
            else:
                card,box=self.panel("In sviluppo",desc+" Questa sezione è già predisposta nell'interfaccia; la gestione completa arriverà nei prossimi aggiornamenti.")
                self.pages[name].layout().addWidget(card); self.pages[name].layout().addStretch()

    def navigate(self,name):
        self.stack.setCurrentWidget(self.pages[name])
        for label,button in self.nav_buttons.items(): button.setProperty("active",label==name); button.style().unpolish(button); button.style().polish(button)
        if name=="Le mie istanze": self.refresh_instances()
        if name=="Catalogo" and self.results.count()==0: self.search_modpacks()

    def search_modpacks(self):
        query=self.search_input.text().strip()
        self.search_button.setEnabled(False); self.search_button.setText("Ricerca…"); self.results.clear()
        self.search_worker=SearchWorker(query); self.search_worker.completed.connect(self.show_results); self.search_worker.failed.connect(self.search_failed); self.search_worker.finished.connect(self.search_finished); self.search_worker.start()

    def show_results(self,packs):
        if not packs:
            self.results.addItem("Nessun modpack trovato. Prova un altro nome.")
            return
        for pack in packs:
            description=(pack.get("description") or "").strip()
            if len(description)>180: description=description[:177]+"..."
            item=QListWidgetItem(
                f'{pack.get("title","Modpack")}\n'
                f'{pack.get("author","Unknown")}  •  {pack.get("downloads",0):,} download\n'
                f'{description}'
            )
            item.setData(Qt.ItemDataRole.UserRole,pack)
            item.setSizeHint(QSize(0,88))
            self.results.addItem(item)
            cover=pack.get("icon_url")
            if cover:
                worker=CoverWorker(item,cover)
                worker.loaded.connect(self.set_pack_cover)
                worker.finished.connect(lambda w=worker: self.cover_workers.remove(w) if w in self.cover_workers else None)
                self.cover_workers.append(worker)
                worker.start()

    def set_pack_cover(self,item,data):
        pixmap=QPixmap()
        if pixmap.loadFromData(data):
            item.setIcon(QIcon(pixmap.scaled(112,72,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation)))

    def install_selected_pack(self):
        item=self.results.currentItem()
        pack=item.data(Qt.ItemDataRole.UserRole) if item else None
        if not pack: QMessageBox.information(self,'Seleziona un modpack','Seleziona prima un risultato Modrinth.'); return
        self.install_button.setEnabled(False); self.install_status.setText('Preparazione installazione…')
        self.install_worker=InstallWorker(pack['id'],pack['title'])
        self.install_worker.progress.connect(self.install_status.setText)
        self.install_worker.completed.connect(self.install_success)
        self.install_worker.failed.connect(self.install_failed)
        self.install_worker.finished.connect(lambda:self.install_button.setEnabled(True))
        self.install_worker.start()

    def install_success(self,instance):
        self.install_status.setText(f'{instance["name"]} installato.')
        self.refresh_instances()
        QMessageBox.information(self,'Installazione completata',f'{instance["name"]} è stato installato. Vai in Le mie istanze per avviarlo.')

    def install_failed(self,message):
        self.install_status.setText('Installazione non riuscita.')
        QMessageBox.warning(self,'Installazione modpack',message)

    def launch_selected_instance(self):
        row=self.instance_list.currentRow(); instances=self.store.list_instances()
        if row<0 or row>=len(instances): QMessageBox.information(self,'Seleziona un\'istanza','Seleziona prima un\'istanza installata.'); return
        instance=instances[row]
        if instance.get('status')!='installed': QMessageBox.information(self,'Non installata','Questa istanza non è ancora installabile.'); return
        if not self.account: QMessageBox.warning(self,'Login richiesto','Accedi con Microsoft prima di avviare Minecraft.'); self.navigate('Account'); return
        self.launch_worker=LaunchWorker(instance,self.account)
        self.launch_worker.failed.connect(lambda message:QMessageBox.warning(self,'Avvio Minecraft',message))
        self.launch_worker.start()

    def show_pack_details(self,item):
        pack=item.data(Qt.ItemDataRole.UserRole)
        if pack: QMessageBox.information(self,pack["title"],f'{pack.get("description","")}\n\nAutore: {pack.get("author","Unknown")}\nDownload: {pack.get("downloads",0):,}\nID Modrinth: {pack.get("id","")}\n\nUsa il pulsante Installa per creare un'istanza separata.')

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
        if not hasattr(self,"instance_list"): return
        self.instance_list.clear()
        for instance in self.store.list_instances():
            self.instance_list.addItem(f'{instance["name"]}  •  Minecraft {instance["minecraft_version"]}  •  {instance["loader"].title()}  •  {instance["status"]}')

    def save_client_id(self):
        value=self.client_id_input.text().strip()
        if not value: QMessageBox.warning(self,"Client ID mancante","Inserisci il Client ID pubblico dell'app Microsoft."); return
        self.config["microsoft_client_id"]=value; save_config(self.config)
        QMessageBox.information(self,"Configurazione salvata","Client ID salvato localmente.")

    def start_login(self):
        client_id=self.client_id_input.text().strip() or os.getenv("NO_LIMITS_MSA_CLIENT_ID","")
        if not client_id: QMessageBox.warning(self,"Login non configurato","Inserisci il Client ID Microsoft nella pagina Account e salvalo."); return
        self.config["microsoft_client_id"]=client_id; save_config(self.config)
        self.login_button.setEnabled(False); self.login_button.setText("Attendo Microsoft…"); self.login_status.setText("Apro la pagina di accesso Microsoft…")
        self.login_worker=LoginWorker(client_id); self.login_worker.progress.connect(self.login_status.setText); self.login_worker.completed.connect(self.login_success); self.login_worker.failed.connect(self.login_failed); self.login_worker.finished.connect(self.login_finished); self.login_worker.start()

    def login_success(self,profile):
        self.account=profile; self.login_status.setText(f'Connesso come {profile.get("name","Minecraft player")}'); self.update_account_ui()
        QMessageBox.information(self,"Accesso completato",f'Benvenuto, {profile.get("name","Minecraft player")}!')

    def login_failed(self,message):
        self.login_status.setText("Accesso non completato."); QMessageBox.warning(self,"Login Microsoft",message)

    def login_finished(self): self.login_button.setEnabled(True); self.login_button.setText("Account collegato" if self.account else "Accedi con Microsoft")


    def restore_session(self):
        client_id=self.config.get("microsoft_client_id") or os.getenv("NO_LIMITS_MSA_CLIENT_ID") or DEFAULT_MICROSOFT_CLIENT_ID
        if not client_id: return
        token=auth.saved_token(client_id)
        if not token: return
        self.login_status.setText("Ripristino sessione Microsoft…")
        self.session_worker=SessionWorker(client_id,token)
        self.session_worker.completed.connect(self.session_restored)
        self.session_worker.failed.connect(lambda _message:self.login_status.setText("Sessione scaduta: accedi di nuovo."))
        self.session_worker.start()

    def session_restored(self,profile):
        self.account=profile
        self.login_status.setText(f'Connesso come {profile.get("name","Minecraft player")}')
        self.update_account_ui()

    def logout(self):
        client_id=self.config.get("microsoft_client_id") or os.getenv("NO_LIMITS_MSA_CLIENT_ID","")
        try: auth.forget(client_id)
        except Exception as exc: QMessageBox.warning(self,"Logout",str(exc)); return
        self.account=None
        self.login_status.setText("Account disconnesso.")
        self.update_account_ui()

    def update_account_ui(self):
        if self.account:
            self.account_label.setText(f'●  {self.account.get("name","Online")}')
            if hasattr(self,"logout_button"): self.logout_button.setVisible(True)
            if hasattr(self,"login_button"): self.login_button.setText("Account collegato")
        else:
            self.account_label.setText("●  Account non collegato")
            if hasattr(self,"logout_button"): self.logout_button.setVisible(False)
            if hasattr(self,"login_button"): self.login_button.setText("Accedi con Microsoft")
