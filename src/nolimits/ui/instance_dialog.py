"""Finestra «Modifica istanza» (stile Prism): generale, versione, Java e memoria, mod, resource pack, shader, note."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from nolimits.core.runtime import LOADERS
from nolimits.ui.main_window import PackIcon

DATA_DIR = Path.home() / ".no-limits-launcher"
COMMON_VERSIONS = [
    "1.21.4", "1.21.1", "1.20.6", "1.20.4", "1.20.1", "1.19.4", "1.19.2",
    "1.18.2", "1.17.1", "1.16.5", "1.12.2", "1.8.9",
]


def format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{max(1, size // 1024)} KB"


def open_folder(path: Path, parent: QWidget) -> None:
    if path.is_dir():
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    else:
        QMessageBox.information(parent, "Cartella non trovata", "La cartella non esiste ancora: l'istanza non è stata installata.")


class ContentFilesTab(QWidget):
    """Elenco dei file di una cartella (mods, resourcepacks, shaderpacks) con attiva/disattiva, aggiungi e rimuovi.

    Disattivare un file aggiunge il suffisso `.disabled`, come fa Prism: il gioco lo ignora ma il file resta.
    """

    def __init__(self, instance_dir: str, folder: str, extensions: tuple, add_filter: str, parent=None):
        super().__init__(parent)
        self.folder = Path(instance_dir) / folder if instance_dir else None
        self.extensions = extensions
        self.add_filter = add_filter
        self._loading = False
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)
        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        layout.addWidget(self.summary)

        self.list = QListWidget()
        self.list.setObjectName("FileList")
        self.list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.list.itemChanged.connect(self._toggle)
        layout.addWidget(self.list, 1)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        add = QPushButton("Aggiungi file…")
        add.clicked.connect(self.add_files)
        remove = QPushButton("Rimuovi selezionati")
        remove.clicked.connect(self.remove_selected)
        open_btn = QPushButton("Apri cartella")
        open_btn.clicked.connect(lambda: open_folder(self.folder, self) if self.folder else None)
        for button in (add, remove, open_btn):
            buttons.addWidget(button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        self.reload()

    def _files(self) -> list[Path]:
        if not self.folder or not self.folder.is_dir():
            return []
        found = [p for p in self.folder.iterdir()
                 if p.is_file() and not p.name.startswith(".")
                 and p.name.lower().removesuffix(".disabled").endswith(self.extensions)]
        return sorted(found, key=lambda p: p.name.lower())

    def reload(self) -> None:
        self._loading = True
        self.list.clear()
        files = self._files()
        for path in files:
            enabled = not path.name.endswith(".disabled")
            item = QListWidgetItem(f"{path.name.removesuffix('.disabled')}     ·     {format_size(path.stat().st_size)}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked)
            self.list.addItem(item)
        self._loading = False
        if not self.folder or not self.folder.is_dir():
            self.summary.setText("L'istanza non ha ancora una cartella: installala per gestire questi file.")
        else:
            active = sum(1 for p in files if not p.name.endswith(".disabled"))
            self.summary.setText(f"{len(files)} file ({active} attivi). Togli la spunta per disattivarne uno senza eliminarlo.")

    def _toggle(self, item: QListWidgetItem) -> None:
        if self._loading:
            return
        path = Path(item.data(Qt.ItemDataRole.UserRole))
        enable = item.checkState() == Qt.CheckState.Checked
        clean = path.name.removesuffix(".disabled")
        target = path.with_name(clean if enable else clean + ".disabled")
        if target == path:
            return
        try:
            path.rename(target)
        except OSError as exc:
            QMessageBox.warning(self, "File", f"Impossibile rinominare il file: {exc}")
        # ricarico nel ciclo successivo: l'elemento che sta emettendo il segnale non va distrutto qui dentro
        QTimer.singleShot(0, self.reload)

    def _copy_in(self, sources: list[str]) -> None:
        if not self.folder:
            QMessageBox.information(self, "Istanza non installata", "Installa prima l'istanza per aggiungere file.")
            return
        self.folder.mkdir(parents=True, exist_ok=True)
        skipped = []
        for source in sources:
            origin = Path(source)
            if not origin.name.lower().endswith(self.extensions):
                skipped.append(f"{origin.name} (tipo non valido)")
                continue
            target = self.folder / origin.name
            if target.exists() or target.with_name(origin.name + ".disabled").exists():
                skipped.append(f"{origin.name} (esiste già)")
                continue
            try:
                shutil.copy2(origin, target)
            except OSError as exc:
                skipped.append(f"{origin.name} ({exc})")
        self.reload()
        if skipped:
            QMessageBox.information(self, "File non aggiunti", "\n".join(skipped))

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Aggiungi file", "", self.add_filter)
        if files:
            self._copy_in(files)

    def remove_selected(self) -> None:
        items = self.list.selectedItems()
        if not items:
            return
        if QMessageBox.question(self, "Rimuovi file", f"Eliminare definitivamente {len(items)} file?") != QMessageBox.StandardButton.Yes:
            return
        for item in items:
            try:
                Path(item.data(Qt.ItemDataRole.UserRole)).unlink()
            except OSError as exc:
                QMessageBox.warning(self, "File", str(exc))
        self.reload()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        self._copy_in([url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()])
        event.acceptProposedAction()


class InstanceEditDialog(QDialog):
    def __init__(self, parent, instance: dict, other_names: list[str]):
        super().__init__(parent)
        self.instance = instance
        self.other_names = {name.casefold() for name in other_names}
        self.icon_path = instance.get("icon_path") or ""
        name = instance.get("name", "Istanza")
        directory = instance.get("directory") or ""

        self.setObjectName("InstanceDialog")
        self.setWindowTitle(f"Modifica istanza · {name}")
        self.resize(800, 620)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(14)
        self.header_icon = PackIcon(56, 16, 0, name)
        header.addWidget(self.header_icon)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        title = QLabel(name)
        title.setObjectName("BlockTitle")
        meta = QLabel(f"Minecraft {instance.get('minecraft_version', '?')}  •  {str(instance.get('loader', 'vanilla')).title()}")
        meta.setObjectName("Muted")
        titles.addWidget(title)
        titles.addWidget(meta)
        header.addLayout(titles, 1)
        root.addLayout(header)
        self._load_icon_preview()

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general(directory), "Generale")
        self.tabs.addTab(self._build_version(), "Versione")
        self.tabs.addTab(self._build_java(), "Java e memoria")
        self.tabs.addTab(ContentFilesTab(directory, "mods", (".jar",), "Mod (*.jar)"), "Mod")
        self.tabs.addTab(ContentFilesTab(directory, "resourcepacks", (".zip",), "Resource pack (*.zip)"), "Resource pack")
        self.tabs.addTab(ContentFilesTab(directory, "shaderpacks", (".zip",), "Shader (*.zip)"), "Shader")
        self.tabs.addTab(self._build_notes(), "Note")
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        folder_btn = QPushButton("Apri cartella")
        folder_btn.clicked.connect(lambda: open_folder(Path(directory), self))
        cancel = QPushButton("Annulla")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Salva modifiche")
        save.setObjectName("Primary")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        footer.addWidget(folder_btn)
        footer.addStretch(1)
        footer.addWidget(cancel)
        footer.addWidget(save)
        root.addLayout(footer)

    # ------------------------------------------------------------------ tab
    def _form(self) -> tuple[QWidget, QFormLayout]:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(18, 18, 18, 14)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(14)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        return page, form

    def _build_general(self, directory: str) -> QWidget:
        page, form = self._form()
        self.name_edit = QLineEdit(self.instance.get("name", ""))
        form.addRow("Nome", self.name_edit)

        icon_row = QHBoxLayout()
        icon_row.setSpacing(8)
        choose = QPushButton("Scegli immagine…")
        choose.clicked.connect(self.choose_icon)
        clear = QPushButton("Rimuovi")
        clear.clicked.connect(self.clear_icon)
        icon_row.addWidget(choose)
        icon_row.addWidget(clear)
        icon_row.addStretch(1)
        form.addRow("Icona", icon_row)

        folder_edit = QLineEdit(directory or "—")
        folder_edit.setReadOnly(True)
        form.addRow("Cartella", folder_edit)

        source = {"modrinth": "Modrinth", "import-mrpack": "Importata (.mrpack)", "import-curseforge": "Importata (CurseForge)",
                  "import-prism": "Importata (Prism / MultiMC)"}.get(self.instance.get("source", ""), "Creata nel launcher")
        origin = QLabel(source)
        origin.setObjectName("Muted")
        form.addRow("Origine", origin)

        warnings = self.instance.get("import_warnings") or []
        if warnings:
            box = QPlainTextEdit("\n".join(warnings))
            box.setObjectName("NotesEdit")
            box.setReadOnly(True)
            box.setMaximumHeight(120)
            label = QLabel(f"{len(warnings)} mod non scaricate\nall'importazione")
            label.setObjectName("Muted")
            form.addRow(label, box)
        return page

    def _build_version(self) -> QWidget:
        page, form = self._form()
        self.mc_combo = QComboBox()
        self.mc_combo.setEditable(True)
        current = str(self.instance.get("minecraft_version", ""))
        versions = COMMON_VERSIONS if current in COMMON_VERSIONS or not current else [current] + COMMON_VERSIONS
        self.mc_combo.addItems(versions)
        self.mc_combo.setCurrentText(current)
        form.addRow("Minecraft", self.mc_combo)

        self.loader_combo = QComboBox()
        self.loader_combo.addItems([loader.title() for loader in LOADERS])
        loader = str(self.instance.get("loader", "vanilla")).lower()
        self.loader_combo.setCurrentIndex(LOADERS.index(loader) if loader in LOADERS else 0)
        form.addRow("Mod loader", self.loader_combo)

        self.loader_version_edit = QLineEdit(str(self.instance.get("loader_version") or ""))
        self.loader_version_edit.setPlaceholderText("Ultima disponibile (lascia vuoto)")
        form.addRow("Versione loader", self.loader_version_edit)

        hint = QLabel("Cambiando versione di Minecraft o mod loader, al salvataggio verrà scaricata la nuova versione. "
                      "Le mod già presenti nella cartella non vengono toccate e potrebbero non essere compatibili: "
                      "controlla la scheda Mod dopo il cambio.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        form.addRow(hint)
        return page

    def _spin(self, value: int, maximum: int, step: int, suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(0, maximum)
        spin.setSingleStep(step)
        spin.setSpecialValueText("Automatico")
        spin.setSuffix(suffix)
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setValue(int(value or 0))
        return spin

    def _build_java(self) -> QWidget:
        page, form = self._form()
        self.min_mem = self._spin(self.instance.get("memory_min", 0), 131072, 256, " MB")
        self.max_mem = self._spin(self.instance.get("memory_max", 0), 131072, 256, " MB")
        form.addRow("Memoria minima", self.min_mem)
        form.addRow("Memoria massima", self.max_mem)

        java_row = QHBoxLayout()
        java_row.setSpacing(8)
        self.java_edit = QLineEdit(str(self.instance.get("java_path") or ""))
        self.java_edit.setPlaceholderText("Automatico (usa il Java scelto dal gioco)")
        browse = QPushButton("Sfoglia…")
        browse.clicked.connect(self.choose_java)
        java_row.addWidget(self.java_edit, 1)
        java_row.addWidget(browse)
        form.addRow("Eseguibile Java", java_row)

        self.args_edit = QLineEdit(str(self.instance.get("jvm_args") or ""))
        self.args_edit.setPlaceholderText("Es. -XX:+UseG1GC -Dfoo=bar")
        form.addRow("Argomenti JVM", self.args_edit)

        self.width_spin = self._spin(self.instance.get("resolution_width", 0), 10000, 10, " px")
        self.height_spin = self._spin(self.instance.get("resolution_height", 0), 10000, 10, " px")
        form.addRow("Larghezza finestra", self.width_spin)
        form.addRow("Altezza finestra", self.height_spin)

        hint = QLabel("«Automatico» lascia decidere al gioco. Imposta larghezza e altezza insieme per forzare la risoluzione.")
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        form.addRow(hint)
        return page

    def _build_notes(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 12)
        self.notes_edit = QPlainTextEdit(str(self.instance.get("notes") or ""))
        self.notes_edit.setObjectName("NotesEdit")
        self.notes_edit.setPlaceholderText("Appunti su questa istanza: mod da aggiornare, server, trucchi…")
        layout.addWidget(self.notes_edit)
        return page

    # --------------------------------------------------------------- azioni
    def _load_icon_preview(self) -> None:
        if self.icon_path:
            try:
                if self.header_icon.set_cover_data(Path(self.icon_path).read_bytes()):
                    return
            except OSError:
                pass
        if self.instance.get("icon_url") and not self.icon_path:
            return  # resta il segnaposto: l'icona online si vede nella lista
        self.header_icon.set_placeholder(self.instance.get("name", ""))

    def choose_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Scegli un'icona", "", "Immagini (*.png *.jpg *.jpeg *.webp *.bmp)")
        if not path:
            return
        if QPixmap(path).isNull():
            QMessageBox.warning(self, "Icona", "Il file scelto non è un'immagine valida.")
            return
        folder = DATA_DIR / "icons"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{self.instance.get('id', 'instance')}{Path(path).suffix.lower()}"
        try:
            shutil.copy2(path, target)
        except OSError as exc:
            QMessageBox.warning(self, "Icona", str(exc))
            return
        self.icon_path = str(target)
        self._load_icon_preview()

    def clear_icon(self) -> None:
        self.icon_path = ""
        self.header_icon.set_placeholder(self.instance.get("name", ""))

    def choose_java(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Scegli l'eseguibile Java", "", "Java (java.exe javaw.exe java);;Tutti i file (*)")
        if path:
            self.java_edit.setText(path)

    def accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Nome mancante", "Il nome dell'istanza non può essere vuoto.")
            self.tabs.setCurrentIndex(0)
            return
        if name.casefold() in self.other_names:
            QMessageBox.warning(self, "Nome già usato", "Esiste già un'istanza con questo nome.")
            self.tabs.setCurrentIndex(0)
            return
        if not self.mc_combo.currentText().strip():
            QMessageBox.warning(self, "Versione mancante", "Indica la versione di Minecraft.")
            self.tabs.setCurrentIndex(1)
            return
        low, high = self.min_mem.value(), self.max_mem.value()
        if low and high and low > high:
            QMessageBox.warning(self, "Memoria", "La memoria minima non può superare la massima.")
            self.tabs.setCurrentIndex(2)
            return
        super().accept()

    def values(self) -> dict:
        return {
            "name": self.name_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
            "icon_path": self.icon_path,
            "minecraft_version": self.mc_combo.currentText().strip(),
            "loader": LOADERS[self.loader_combo.currentIndex()],
            "loader_version": self.loader_version_edit.text().strip(),
            "memory_min": self.min_mem.value(),
            "memory_max": self.max_mem.value(),
            "java_path": self.java_edit.text().strip(),
            "jvm_args": self.args_edit.text().strip(),
            "resolution_width": self.width_spin.value(),
            "resolution_height": self.height_spin.value(),
        }

    def runtime_changed(self) -> bool:
        new, old = self.values(), self.instance
        return (
            new["minecraft_version"] != str(old.get("minecraft_version", ""))
            or new["loader"] != str(old.get("loader", "vanilla")).lower()
            or new["loader_version"] != str(old.get("loader_version") or "")
        )
