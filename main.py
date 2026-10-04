# main.py – Lernplatform Einstiegspunkt, Hauptfenster & Schüler-Setup
"""
Haupteinstiegspunkt und Hauptfenster der Lernplatform:
1. Schüler-Selbstorganisation:
   - Lose gestartete EXE organisiert sich vollautomatisch selbst (Ordner erstellen,
     kopieren, Standard-JSON anlegen, alte EXE entfernen).
2. Globales Crash-Logging:
   - Fängt alle unerwarteten Fehler ab und schreibt aussagekräftige Logs.
3. MainWindow:
   - Sidebar-Navigation (Abfrage, Kategorien, Vokabelverwaltung)
   - Live-Ordnerüberwachung: Erkennt neu hineingeschobene oder extern geänderte
     Vokabel-JSON-Dateien automatisch und aktualisiert alle Ansichten.
4. Anwendungsstart:
   - Initialisiert Qt-Application, barrierefreies Stylesheet und Hauptfenster.
"""
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
import traceback
from functools import partial
from pathlib import Path

# Projektordner in den Modulsuchpfad aufnehmen
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent))

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import backend
from abfrage import AbfrageView
from backend import VokabelTrainer
from einstellungen import EinstellungenView
from kategorien import KategorienView
from style import STYLE, EnterActivationFilter
from verwaltung import VerwaltungView


# ── Automatisches Selbst-Einrichten für Mitschüler (Standalone-EXE) ───────────
def _write_default_json_files(target_dir: Path) -> None:
    """Erstellt vokabeln.json und kategorien.json im Zielordner aus den Vorlagen."""
    target_vok = target_dir / "vokabeln.json"
    target_kat = target_dir / "kategorien.json"

    # 1. Aus PyInstaller-Bundle (_MEIPASS) kopieren falls vorhanden
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        src_vok = Path(meipass) / "vokabeln.json"
        src_kat = Path(meipass) / "kategorien.json"
        if src_vok.exists() and not target_vok.exists():
            try:
                shutil.copy2(str(src_vok), str(target_vok))
            except Exception:
                pass
        if src_kat.exists() and not target_kat.exists():
            try:
                shutil.copy2(str(src_kat), str(target_kat))
            except Exception:
                pass

    # 2. Aus dem Anwendungs-/Quellordner kopieren falls vorhanden
    src_dir = Path(__file__).resolve().parent
    if not target_vok.exists() and (src_dir / "vokabeln.json").exists():
        try:
            shutil.copy2(str(src_dir / "vokabeln.json"), str(target_vok))
        except Exception:
            pass
    if not target_kat.exists() and (src_dir / "kategorien.json").exists():
        try:
            shutil.copy2(str(src_dir / "kategorien.json"), str(target_kat))
        except Exception:
            pass

    # 3. Fallback: Gültige Standard-Dateien anlegen falls gar nichts gefunden wurde
    if not target_kat.exists():
        target_kat.write_text("{}", encoding="utf-8")
    if not target_vok.exists():
        target_vok.write_text("[]", encoding="utf-8")


def _ensure_self_contained_folder() -> None:
    """Wenn die kompilierte EXE lose (z. B. auf dem Desktop oder im Download-Ordner)
    ohne vokabeln.json ausgeführt wird, organisiert sie sich automatisch selbst:
    1. Erstellt einen neuen Ordner 'Lernplatform' am aktuellen Ort
    2. Schreibt die 2 JSON-Dateien (vokabeln.json und kategorien.json) dort hinein
    3. Kopiert die EXE in diesen Ordner, löscht die lose Datei und startet die App
    """
    if not getattr(sys, "frozen", False):
        return

    current_exe = Path(sys.executable).resolve()
    current_dir = current_exe.parent

    # Im Entwicklungs- oder Dist-Ordner niemals selbst verschieben
    if current_dir.name.lower() in ("dist", "build") or (current_dir.parent / "main.py").exists():
        return

    # Wenn bereits eine vokabeln.json oder eine andere JSON-Datei vorhanden ist -> sofort normal starten!
    try:
        if any(p.suffix.lower() == ".json" for p in current_dir.iterdir() if p.is_file()):
            return
    except Exception:
        if (current_dir / "vokabeln.json").exists():
            return

    # Wenn der Ordner bereits 'Lernplatform' heißt -> nur JSON-Dateien anlegen
    if current_dir.name.lower() == "lernplatform":
        _write_default_json_files(current_dir)
        return

    # Die EXE liegt lose (z. B. auf dem Desktop eines Mitschülers):
    target_dir = current_dir / "Lernplatform"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_exe = target_dir / current_exe.name

    # 1. JSON-Dateien im Zielordner erstellen
    _write_default_json_files(target_dir)

    # 2. EXE in den neuen Ordner kopieren
    try:
        shutil.copy2(str(current_exe), str(target_exe))
    except Exception:
        return

    # 3. Alte lose EXE löschen und neue EXE im Ordner starten
    clean_cmd = f'ping 127.0.0.1 -n 2 >nul & del /f /q "{current_exe}" & start "" "{target_exe}"'
    try:
        subprocess.Popen(
            ["cmd.exe", "/c", clean_cmd],
            shell=False,
            creationflags=0x00000008,
            close_fds=True,
        )
    except Exception:
        pass

    sys.exit(0)


# ── Globales Exception-Logging ────────────────────────────────────────────────
def _setup_crash_logging() -> None:
    """Leitet alle unbehandelten Exceptions in eine Log-Datei um und zeigt Dialog an."""
    if getattr(sys, "frozen", False):
        log_dir = Path(sys.executable).parent
    else:
        log_dir = Path(__file__).parent
    log_file = log_dir / "lernplatform_crash.log"

    try:
        import faulthandler
        fault_log = open(str(log_dir / "lernplatform_faulthandler.log"), "a", encoding="utf-8")
        faulthandler.enable(file=fault_log)
    except Exception:
        pass

    logging.basicConfig(
        filename=str(log_file),
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8",
    )

    def _excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_tb: object) -> None:
        msg = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))  # type: ignore[arg-type]
        logging.critical("Unbehandelte Exception:\n%s", msg)
        app = QApplication.instance()
        if app is not None:
            dlg = QMessageBox()
            dlg.setWindowTitle("Lernplatform – Unerwarteter Fehler")
            dlg.setIcon(QMessageBox.Icon.Critical)
            dlg.setText(
                "Ein unerwarteter Fehler ist aufgetreten.\n\n"
                f"Details wurden gespeichert in:\n{log_file}\n\n"
                "Die Anwendung wird jetzt beendet."
            )
            dlg.setDetailedText(msg)
            dlg.exec()
        sys.__excepthook__(exc_type, exc_value, exc_tb)  # type: ignore[attr-defined]

    sys.excepthook = _excepthook


# ── Hauptfenster mit Sidebar & Live-Ordnerüberwachung ─────────────────────────
class MainWindow(QMainWindow):
    """Hauptanwendungsfenster der Lernplatform."""

    def __init__(self, trainer: VokabelTrainer) -> None:
        super().__init__()
        self._trainer = trainer
        self.setWindowTitle("Lernplatform")
        self.setMinimumSize(960, 600)
        self.setAccessibleName(" Lernplatform Hauptfenster")
        self._build_ui()
        self._init_folder_watcher()
        self._navigate(1)  # Startet auf Kategorien

    def _init_folder_watcher(self) -> None:
        """Überwacht das Verzeichnis im Hintergrund auf neue oder geänderte JSON-Dateien."""
        self._last_data_mtime = backend.DATA_FILE.stat().st_mtime if backend.DATA_FILE.exists() else 0.0
        self._last_data_size = backend.DATA_FILE.stat().st_size if backend.DATA_FILE.exists() else 0
        self._known_json_state = self._get_folder_json_state()

        self._folder_timer = QTimer(self)
        self._folder_timer.setInterval(3000)  # Alle 3 Sekunden prüfen
        self._folder_timer.timeout.connect(self._check_folder_changes)
        self._folder_timer.start()

    def _get_folder_json_state(self) -> dict[Path, tuple[float, int]]:
        """Ermittelt Pfad, Zeitstempel und Größe aller sekundären JSON-Dateien im Anwendungsordner."""
        state: dict[Path, tuple[float, int]] = {}
        dirs = [backend.APP_DIR]
        exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
        if exe_dir not in dirs:
            dirs.append(exe_dir)

        for d in dirs:
            if not d.exists():
                continue
            for p in d.glob("*.json"):
                if p.name.lower() in (
                    "vokabeln.json", "kategorien.json", "kategorien.json.tmp",
                    "vokabeln.json.tmp", "einstellungen.json", "einstellungen.json.tmp"
                ):
                    continue
                try:
                    st = p.stat()
                    state[p] = (st.st_mtime, st.st_size)
                except Exception:
                    pass
        return state

    def _show_status(self, text: str, timeout: int = 0) -> None:
        """Zeigt eine Statusmeldung nur an, wenn die Statusleiste verfügbar ist."""
        status_bar = self.statusBar()
        if status_bar is not None:
            status_bar.showMessage(text, timeout)

    def _check_folder_changes(self) -> None:
        """Erkennt automatisch, wenn eine vorhandene Vokabel-JSON in den Ordner geschoben oder aktualisiert wird."""
        # Wenn aktuell ein modaler Dialog (z. B. Hinzufügen, Löschen, Bearbeiten) geöffnet ist: nicht stören!
        if QApplication.activeModalWidget() is not None:
            return

        # 1. Hauptdatei (vokabeln.json) prüfen
        data_exists = backend.DATA_FILE.exists()
        cur_mtime = backend.DATA_FILE.stat().st_mtime if data_exists else 0.0
        cur_size = backend.DATA_FILE.stat().st_size if data_exists else 0

        # Wenn die Anwendung gerade selbst gespeichert hat (innerhalb der letzten 3,5 Sekunden):
        # Es handelt sich um ein internes Speichern – kein externes Neuladen nötig!
        if getattr(backend, "LAST_SAVED_TIME", 0.0) > 0 and (time.time() - backend.LAST_SAVED_TIME) < 3.5:
            self._last_data_mtime = cur_mtime
            self._last_data_size = cur_size
            return

        if cur_mtime != self._last_data_mtime or cur_size != self._last_data_size:
            self._last_data_mtime = cur_mtime
            self._last_data_size = cur_size
            if abs(cur_mtime - backend.LAST_SAVED_MTIME) > 1.0:
                count = self._trainer.reload_vokabeln()
                self._refresh_all_views()
                if count > 0:
                    self._show_status(
                        f"✓ Vokabeldatei aktualisiert: {count} Vokabeln geladen.", 6000
                    )
                return

        # 2. Prüfen, ob eine neue oder andere JSON-Datei in den Ordner geschoben wurde
        current_state = self._get_folder_json_state()
        new_or_modified: list[Path] = []
        for p, (mtime, size) in current_state.items():
            if p == backend.DATA_FILE:
                continue
            prev = self._known_json_state.get(p)
            if prev is None or prev != (mtime, size):
                new_or_modified.append(p)
        self._known_json_state = current_state

        for p in new_or_modified:
            new_voks = backend._parse_vokabel_file(p)
            if not new_voks:
                continue

            # Wenn bisher 0 Vokabeln vorhanden -> direkt komplett übernehmen
            if len(self._trainer.vokabeln) == 0:
                self._trainer.vokabeln = new_voks
                self._trainer.save()
                self._last_data_mtime = backend.DATA_FILE.stat().st_mtime if backend.DATA_FILE.exists() else 0.0
                self._last_data_size = backend.DATA_FILE.stat().st_size if backend.DATA_FILE.exists() else 0
                self._refresh_all_views()
                self._show_status(
                    f"✓ {len(new_voks)} Vokabeln aus \u201e{p.name}\u201c automatisch erkannt und aktiviert!", 8000
                )
                break
            else:
                # Bestehenden Pool ergänzen (Duplikate überspringen)
                added = 0
                for v in new_voks:
                    if not self._trainer.is_duplicate(v.front, v.kategorie, v.lang_front):
                        self._trainer.vokabeln.append(v)
                        added += 1
                if added > 0:
                    self._trainer.save()
                    self._last_data_mtime = backend.DATA_FILE.stat().st_mtime if backend.DATA_FILE.exists() else 0.0
                    self._last_data_size = backend.DATA_FILE.stat().st_size if backend.DATA_FILE.exists() else 0
                    self._refresh_all_views()
                    self._show_status(
                        f"✓ {added} neue Vokabeln aus \u201e{p.name}\u201c automatisch importiert!", 8000
                    )
                    break

    def _refresh_all_views(self) -> None:
        """Aktualisiert die aktuell sichtbare Ansicht (versteckte Views aktualisieren sich beim Wechseln)."""
        current_view = self._stack.currentWidget()
        refresh = getattr(current_view, "refresh", None)
        if callable(refresh):
            try:
                refresh()
            except Exception:
                pass

    def _build_ui(self) -> None:
        """Baut das Layout aus Seitenleiste und gestapelten Inhaltsbereichen auf."""
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(210)
        sidebar.setAccessibleName(" Navigation")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(12, 20, 12, 20)
        sb_layout.setSpacing(4)

        app_title = QLabel("Lernplatform")
        app_title.setObjectName("appTitle")
        app_title.setAccessibleName(" Lernplatform")
        sb_layout.addWidget(app_title)

        nav_items = [
            ("▶  Abfrage",           " Abfrage"),
            ("📂  Kategorien",        " Kategorien"),
            ("📋  Vokabelverwaltung", " Vokabelverwaltung"),
            ("⚙  Einstellungen",     " Einstellungen"),
        ]
        self._nav_btns: list[QPushButton] = []
        for label, accessible in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("navBtn")
            btn.setAccessibleName(accessible)
            idx = len(self._nav_btns)
            btn.clicked.connect(partial(self._navigate, idx))
            sb_layout.addWidget(btn)
            self._nav_btns.append(btn)

        sb_layout.addStretch()
        root_layout.addWidget(sidebar)

        # Trennlinie
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setStyleSheet("color: #1e2130;")
        root_layout.addWidget(line)

        # Content-Bereich
        self._stack = QStackedWidget()
        self._stack.setAccessibleName(" Inhaltsbereich")

        self._abfrage_view = AbfrageView(self._trainer)
        self._stack.addWidget(self._abfrage_view)        # Index 0

        self._kategorien_view = KategorienView(
            self._trainer, on_start=self._start_kategorie
        )
        self._stack.addWidget(self._kategorien_view)     # Index 1

        self._verwaltung_view = VerwaltungView(self._trainer)
        self._stack.addWidget(self._verwaltung_view)     # Index 2

        self._einstellungen_view = EinstellungenView(
            self._trainer, on_settings_changed=self._on_settings_changed
        )
        self._stack.addWidget(self._einstellungen_view)  # Index 3

        self._views: list[QWidget] = [
            self._abfrage_view,
            self._kategorien_view,
            self._verwaltung_view,
            self._einstellungen_view,
        ]

        root_layout.addWidget(self._stack, stretch=1)

        # Easter Egg Shortcut (Strg + Shift + E)
        self._shortcut_easteregg = QShortcut(QKeySequence("Ctrl+Shift+E"), self)
        self._shortcut_easteregg.activated.connect(self._show_easter_egg_dialog)

    def _show_easter_egg_dialog(self) -> None:
        """Zeigt das geheime Entwickler-Easter-Egg-Fenster."""
        dlg = QMessageBox(self)
        dlg.setWindowTitle("🎉 Geheimes Entwickler-Easter-Egg!")
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setText(
            "🌟 HERZLICHEN GLÜCKWUNSCH! 🌟\n\n"
            "Du hast das geheime Entwickler-Easter-Egg der Lernplatform entdeckt!\n\n"
            "Wer sich Anleitungen so aufmerksam und gründlich durchliest, beweist echte Meister-Disziplin.\n"
            "Viel Erfolg beim Lernen – du bist auf dem besten Weg zur Bestnote! 🚀"
        )
        dlg.setAccessibleName(" Geheimes Entwickler Easter Egg entdeckt. Herzlichen Glückwunsch!")
        btn = dlg.addButton("Meisterhaft! Weiterlernen 🎓", QMessageBox.ButtonRole.AcceptRole)
        btn.setAutoDefault(False)
        btn.setDefault(False)
        dlg.exec()

    def _on_settings_changed(self) -> None:
        """Wird aufgerufen, wenn Einstellungen (z. B. Abfragerichtung) geändert wurden."""
        self._abfrage_view.refresh()

    def _navigate(self, index: int) -> None:
        """Schaltet die aktive Ansicht um und aktualisiert den aktiven Sidebar-Button."""
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", "true" if i == index else "false")
            style = btn.style()
            if style is not None:
                style.unpolish(btn)
                style.polish(btn)
        if 0 <= index < len(self._views):
            view = self._views[index]
            refresh = getattr(view, "refresh", None)
            if callable(refresh):
                refresh()

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is not None and self._stack.currentIndex() == 0:
            self._abfrage_view.keyPressEvent(a0)
            if a0.isAccepted():
                return
        super().keyPressEvent(a0)

    def _start_kategorie(self, kategorie: list[str] | set[str] | str | None) -> None:
        """Kategorie(n) setzen und direkt zur Abfrage wechseln."""
        self._abfrage_view.set_kategorien(kategorie)
        self._navigate(0)


# ── CLI-Argumente ─────────────────────────────────────────────────────────────
def _parse_arguments() -> argparse.Namespace:
    """Parst optionale Startargumente für Debugging."""
    parser = argparse.ArgumentParser(
        prog="Lernplatform",
        description="Barrierefreier, intelligenter Vokabel- und Begriffstrainer",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 2.5",
        help="Programmversion anzeigen und beenden",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Ausführliche Konsolenausgabe für Debugging aktivieren",
    )
    return parser.parse_args()


# ── Haupteinstiegspunkt ───────────────────────────────────────────────────────
def main() -> None:
    """Initialisiert und startet die Anwendung."""
    # 1. Schüler-Setup: Lose EXE automatisch in Ordner einbetten
    _ensure_self_contained_folder()

    # 2. Crash-Logging aktivieren
    _setup_crash_logging()

    # 3. CLI-Optionen prüfen
    try:
        args = _parse_arguments()
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
    except SystemExit:
        return
    except Exception:
        pass

    # 4. QApplication zuerst starten (muss vor allem anderen Qt-Code sein)
    app = QApplication(sys.argv)
    app.setApplicationName("Lernplatform")
    app.setOrganizationName("Lernplatform")
    app.setStyleSheet(STYLE)

    # 5. Trainer initialisieren (erst nach QApplication!)
    trainer = VokabelTrainer()

    # Globaler Enter-Aktivierungsfilter für Tastaturbedienung
    enter_filter = EnterActivationFilter(app)
    app.installEventFilter(enter_filter)

    window = MainWindow(trainer)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
