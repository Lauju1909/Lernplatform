# word_bridge.py – Microsoft Word Live-Integration & Auto-Übersetzung (/üb...)
"""
Ermöglicht das Öffnen von Word-Dokumenten (.docx) und überwacht die Datei live.
Wird im Dokument ein Befehl wie /übd (übersetze auf Deutsch) oder /übe (übersetze auf Englisch)
gefunden und in Word gespeichert (Strg+S), werden alle unvollständigen Vokabelzeilen
automatisch online übersetzt und direkt in die VokabelMeister (vokabeln.json) importiert.

Übersetzungs-API: MyMemory (https://mymemory.translated.net)
  – Kostenlos, offiziell, ToS-konform, kein API-Schlüssel nötig.
  – Limit: 1.000 Wörter/Tag (anonym). Details: https://mymemory.translated.net/doc/usagelimits.php
  – Übersetzung läuft im Hintergrund-Thread – die UI friert nie ein!
"""

from __future__ import annotations

import os
import re
import time
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

from PyQt6.QtCore import Qt, QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QFont, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from backend import VokabelTrainer, STANDARD_SPRACHEN
from import_funktionen import split_line

logger = logging.getLogger(__name__)

# Liste aller aktiven Begleitdialoge, um Garbage-Collection-Abstürze zu verhindern
_active_dialogs: list[WordCompanionDialog] = []

# ── Sprach-Zuordnungen für /üb... Kürzel ──────────────────────────────────────
LANG_MAP: dict[str, tuple[str, str]] = {
    # Deutsch
    "d": ("Deutsch", "de"),
    "de": ("Deutsch", "de"),
    "deutsch": ("Deutsch", "de"),
    # Englisch
    "e": ("Englisch", "en"),
    "en": ("Englisch", "en"),
    "englisch": ("Englisch", "en"),
    # Französisch
    "f": ("Französisch", "fr"),
    "fr": ("Französisch", "fr"),
    "französisch": ("Französisch", "fr"),
    # Spanisch
    "s": ("Spanisch", "es"),
    "es": ("Spanisch", "es"),
    "spanisch": ("Spanisch", "es"),
    # Italienisch
    "i": ("Italienisch", "it"),
    "it": ("Italienisch", "it"),
    "italienisch": ("Italienisch", "it"),
    # Latein
    "l": ("Latein", "la"),
    "la": ("Latein", "la"),
    "latein": ("Latein", "la"),
    # Russisch
    "r": ("Russisch", "ru"),
    "ru": ("Russisch", "ru"),
    "russisch": ("Russisch", "ru"),
    # Japanisch
    "j": ("Japanisch", "ja"),
    "ja": ("Japanisch", "ja"),
    "japanisch": ("Japanisch", "ja"),
    # Chinesisch
    "c": ("Chinesisch", "zh"),
    "ch": ("Chinesisch", "zh"),
    "zh": ("Chinesisch", "zh"),
    "chinesisch": ("Chinesisch", "zh"),
    # Türkisch
    "t": ("Türkisch", "tr"),
    "tr": ("Türkisch", "tr"),
    "türkisch": ("Türkisch", "tr"),
    # Portugiesisch
    "p": ("Portugiesisch", "pt"),
    "pt": ("Portugiesisch", "pt"),
    "portugiesisch": ("Portugiesisch", "pt"),
    # Niederländisch
    "n": ("Niederländisch", "nl"),
    "nl": ("Niederländisch", "nl"),
    "niederländisch": ("Niederländisch", "nl"),
    # Griechisch
    "g": ("Griechisch", "el"),
    "el": ("Griechisch", "el"),
    "griechisch": ("Griechisch", "el"),
    # Polnisch
    "po": ("Polnisch", "pl"),
    "pl": ("Polnisch", "pl"),
    "polnisch": ("Polnisch", "pl"),
    # Arabisch
    "a": ("Arabisch", "ar"),
    "ar": ("Arabisch", "ar"),
    "arabisch": ("Arabisch", "ar"),
}

NAME_TO_ISO: dict[str, str] = {
    "Deutsch": "de",
    "Englisch": "en",
    "Französisch": "fr",
    "Spanisch": "es",
    "Italienisch": "it",
    "Latein": "la",
    "Russisch": "ru",
    "Japanisch": "ja",
    "Chinesisch": "zh",
    "Türkisch": "tr",
    "Portugiesisch": "pt",
    "Niederländisch": "nl",
    "Griechisch": "el",
    "Polnisch": "pl",
    "Arabisch": "ar",
}


# ── Kostenlose & ToS-konforme Übersetzung via MyMemory API ────────────────────
class OnlineTranslator:
    """Übersetzt Wörter über die offizielle, kostenlose MyMemory API.

    MyMemory (https://mymemory.translated.net) ist ein professioneller Dienst:
    - Kein API-Schlüssel nötig (anonym bis 1.000 Wörter/Tag)
    - ToS-konform und für kommerzielle und nicht-kommerzielle Nutzung erlaubt
    - Nutzungsbedingungen: https://mymemory.translated.net/doc/usagelimits.php

    HINWEIS: Die Übersetzung wird immer im Hintergrund-Thread ausgeführt
    (_DocProcessWorker), sodass die UI niemals einfriert.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, str], str] = {}

    def translate(self, text: str, source_iso: str = "auto", target_iso: str = "de") -> str:
        """Übersetzt einen Text via MyMemory.
        Gibt den Originaltext zurück, wenn die Übersetzung fehlschlägt.
        """
        text = text.strip()
        if not text:
            return ""

        # Cache: Gleiche Wörter nicht doppelt übersetzen
        cache_key = (text.lower(), source_iso.lower(), target_iso.lower())
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # MyMemory unterstützt kein "auto" – Fallback auf Englisch
            src = source_iso if source_iso not in ("auto", "") else "en"
            url = (
                "https://api.mymemory.translated.net/get"
                f"?q={urllib.parse.quote(text)}"
                f"&langpair={urllib.parse.quote(src)}|{urllib.parse.quote(target_iso)}"
            )
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "VokabelMeister/2.5 (educational vocabulary trainer)"},
            )
            with urllib.request.urlopen(req, timeout=8) as response:
                raw = response.read().decode("utf-8")

            data = json.loads(raw)
            if data.get("responseStatus") == 200:
                result = str(data["responseData"]["translatedText"]).strip()
                # MyMemory gibt manchmal den Originaltext zurück → erkennen und ignorieren
                if result and result.upper() != text.upper():
                    self._cache[cache_key] = result
                    return result
        except Exception as exc:
            logger.warning("MyMemory-Übersetzung für '%s' fehlgeschlagen: %s", text, exc)

        return text  # Fallback: Originaltext zurückgeben


_translator = OnlineTranslator()


# ── Robuste Word-Dokument-Verarbeitung mit Retry ──────────────────────────────
def _read_docx_lines_safe(docx_path: Path, max_attempts: int = 4) -> list[str]:
    """Liest Word-Dokument sicher aus. Führt bei Schreib-Sperren von Word kurze Retries durch."""
    try:
        from docx import Document  # type: ignore[import-untyped]
    except ImportError:
        raise RuntimeError("Das Paket 'python-docx' ist für Word-Dateien erforderlich.")

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            doc = Document(str(docx_path))
            lines: list[str] = []

            for para in doc.paragraphs:
                t = para.text.strip()
                if t:
                    lines.append(t)

            for table in doc.tables:
                for row in table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if len(cells) >= 2 and (cells[0] or cells[1]):
                        if cells[0] and cells[1]:
                            lines.append(f"{cells[0]} - {cells[1]}")
                        elif cells[0]:
                            lines.append(cells[0])
                        elif cells[1]:
                            lines.append(cells[1])

            return lines
        except Exception as exc:
            last_exc = exc
            time.sleep(0.3)

    if last_exc:
        raise last_exc
    return []


def parse_and_translate_docx(
    docx_path: Path,
    default_lang_front: str = "Englisch",
    default_lang_back: str = "Deutsch",
) -> tuple[list[tuple[str, str, str, str]], str | None]:
    """Liest ein Word-Dokument aus, erkennt /üb... Befehle und übersetzt neue Wörter.

    HINWEIS: Diese Funktion führt Netzwerkanfragen durch und muss immer in einem
    Hintergrund-Thread aufgerufen werden (nicht im Qt-Haupt-Thread).
    """
    lines = _read_docx_lines_safe(docx_path)

    # Befehlsmuster: Erkennt /übd, /ubd, /übe, /ube, /üb deutsch, /ub englisch etc.
    cmd_pattern = re.compile(r"/(?:üb|ub)\s*([a-zA-ZäöüÄÖÜ]+)?", re.IGNORECASE)

    target_lang_name: str | None = None
    target_lang_iso: str = "de"
    detected_cmd: str | None = None

    filtered_lines: list[str] = []
    for line in lines:
        cleaned = line.strip()
        match = cmd_pattern.search(cleaned)
        if match:
            raw_suffix = (match.group(1) or "").strip().lower()
            detected_cmd = match.group(0).strip()
            if raw_suffix in LANG_MAP:
                target_lang_name, target_lang_iso = LANG_MAP[raw_suffix]
            else:
                target_lang_name, target_lang_iso = (
                    default_lang_back,
                    NAME_TO_ISO.get(default_lang_back, "de"),
                )

            line_without_cmd = cmd_pattern.sub("", cleaned).strip()
            if line_without_cmd:
                filtered_lines.append(line_without_cmd)
        else:
            filtered_lines.append(cleaned)

    paare: list[tuple[str, str, str, str]] = []

    for line in filtered_lines:
        if line.startswith("#") or line.lower() in ("vorderseite", "wort", "begriff", "fragen"):
            continue

        # Hat die Zeile bereits einen gültigen Trenner ('apple - Apfel')?
        split_res = split_line(line)
        if split_res is not None:
            f, b = split_res
            paare.append((f, b, default_lang_front, default_lang_back))
            continue

        # Zeile ist ein Einzelwort ohne Übersetzung → via MyMemory übersetzen
        if target_lang_name is not None:
            if target_lang_name == "Deutsch":
                src_lang = default_lang_front if default_lang_front != "Deutsch" else "Englisch"
            else:
                src_lang = "Deutsch"

            source_iso = NAME_TO_ISO.get(src_lang, "en")
            translation = _translator.translate(line, source_iso=source_iso, target_iso=target_lang_iso)
            paare.append((line, translation or line, src_lang, target_lang_name))

    cmd_desc = f"{detected_cmd} (-> {target_lang_name})" if detected_cmd and target_lang_name else None
    return paare, cmd_desc


# ── Hintergrund-Worker für die Dokument-Verarbeitung (kein UI-Freeze!) ────────
class _DocProcessWorker(QThread):
    """Liest und übersetzt ein Word-Dokument vollständig im Hintergrund-Thread.

    Dadurch friert der Qt-Haupt-Thread (und die gesamte UI) nie ein – auch dann
    nicht, wenn die Netzwerkverbindung langsam ist oder kurz ausfällt.
    """

    # Signal: (paare: list[tuple], cmd_desc: str | None)
    finished = pyqtSignal(list, object)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        path: Path,
        lang_front: str,
        lang_back: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._lang_front = lang_front
        self._lang_back = lang_back

    def run(self) -> None:
        """Wird im Hintergrund-Thread ausgeführt – niemals direkt aufrufen."""
        try:
            paare, cmd_desc = parse_and_translate_docx(
                self._path,
                default_lang_front=self._lang_front,
                default_lang_back=self._lang_back,
            )
            self.finished.emit(paare, cmd_desc)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


# ── Begleit-Dialog: Word-Integration & Live-Überwachung ───────────────────────
class WordCompanionDialog(QDialog):
    """Begleitfenster, das aktiv bleibt, während Microsoft Word geöffnet ist.
    Überwacht die Datei auf Änderungen (Strg+S) und führt /üb... Übersetzungen automatisch aus.
    Die gesamte Übersetzung läuft im Hintergrund – die UI bleibt immer reaktionsfähig.
    """

    vocabularies_imported = pyqtSignal(int)

    def __init__(
        self,
        docx_path: Path,
        trainer: VokabelTrainer,
        kategorie: str = "Sprache",
        lang_front: str = "Englisch",
        lang_back: str = "Deutsch",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._path = docx_path.resolve()
        self._trainer = trainer
        self._kategorie = kategorie
        self._lang_front = lang_front
        self._lang_back = lang_back
        self._last_translated_pairs: list[tuple[str, str]] = []
        self._worker: _DocProcessWorker | None = None  # Aktueller Hintergrund-Worker

        # Referenz halten, um Garbage Collection zu verhindern
        _active_dialogs.append(self)

        self._last_mtime: float = 0.0
        try:
            if self._path.exists():
                self._last_mtime = self._path.stat().st_mtime
        except Exception:
            pass

        self._init_ui()

        # Timer für die Datei-Überwachung (alle 1,2 Sekunden)
        self._watch_timer = QTimer(self)
        self._watch_timer.setInterval(1200)
        self._watch_timer.timeout.connect(self._check_file_modified)
        self._watch_timer.start()

    def _init_ui(self) -> None:
        self.setWindowTitle(f"Word-Live-Begleiter – {self._path.name}")
        self.setMinimumWidth(580)
        self.setMinimumHeight(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(22, 22, 22, 22)

        # 1. Kopfbereich mit Status
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "background: #1e2433; border: 1px solid #2e3a52; border-radius: 8px; padding: 10px;"
        )
        h_layout = QVBoxLayout(header_frame)
        h_layout.setSpacing(4)

        self._status_lbl = QLabel("🟢  Word-Überwachung aktiv")
        self._status_lbl.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self._status_lbl.setStyleSheet("color: #4ade80;")

        file_lbl = QLabel(
            f"📄 Datei: <b>{self._path.name}</b><br>"
            f"<span style='color: #8892b0; font-size: 11px;'>{self._path}</span>"
        )
        file_lbl.setWordWrap(True)

        h_layout.addWidget(self._status_lbl)
        h_layout.addWidget(file_lbl)
        layout.addWidget(header_frame)

        # 2. Kurzanleitung / Spickzettel
        info_box = QFrame()
        info_box.setStyleSheet("background: #181d28; border-radius: 6px; padding: 10px;")
        info_layout = QVBoxLayout(info_box)
        info_layout.setSpacing(6)

        info_title = QLabel("💡 SO FUNKTIONIERT ES IN MICROSOFT WORD:")
        info_title.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        info_title.setStyleSheet("color: #7986e0;")

        info_text = QLabel(
            "1. Schreibe deine Wörter in Word (z. B. <i>Monday</i>, <i>Tuesday</i> ...)<br>"
            "2. Schreibe am Ende z. B. <b>/übd</b> (für Deutsch) oder <b>/übe</b> (für Englisch)<br>"
            "3. Drücke in Word <b>Strg + S</b> (Speichern) – die Wörter werden automatisch "
            "übersetzt und direkt in die VokabelMeister importiert!"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #ccd6f6; font-size: 12px; line-height: 1.4;")

        info_layout.addWidget(info_title)
        info_layout.addWidget(info_text)
        layout.addWidget(info_box)

        # 3. Live-Protokoll
        log_lbl = QLabel("VERLAUF DER AUTO-ÜBERSETZUNG & IMPORTE:")
        log_lbl.setObjectName("sectionLabel")
        layout.addWidget(log_lbl)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet(
            "background: #0f131a; color: #a8b2d1; border: 1px solid #232b3e; "
            "border-radius: 6px; font-family: Consolas, monospace; font-size: 12px;"
        )
        self._log_edit.setPlaceholderText(
            "Noch keine automatischen Importe. Schreibe in Word und drücke Strg+S..."
        )
        layout.addWidget(self._log_edit)

        # 4. Aktions-Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._btn_reopen = QPushButton("📝  In Word öffnen")
        self._btn_reopen.setObjectName("secondaryBtn")
        self._btn_reopen.clicked.connect(self._open_in_word)

        self._btn_manual = QPushButton("⚡  Jetzt manuell prüfen")
        self._btn_manual.setObjectName("primaryBtn")
        self._btn_manual.clicked.connect(self._process_document_now)

        self._btn_copy = QPushButton("📋  In Zwischenablage kopieren")
        self._btn_copy.setObjectName("secondaryBtn")
        self._btn_copy.clicked.connect(self._copy_to_clipboard)

        self._btn_close = QPushButton("Schließen")
        self._btn_close.setObjectName("secondaryBtn")
        self._btn_close.clicked.connect(self.close)

        btn_layout.addWidget(self._btn_reopen)
        btn_layout.addWidget(self._btn_manual)
        btn_layout.addWidget(self._btn_copy)
        btn_layout.addStretch()
        btn_layout.addWidget(self._btn_close)
        layout.addLayout(btn_layout)

    def closeEvent(self, event: QCloseEvent | None) -> None:
        """Stoppt Timer und Worker-Thread sauber beim Schließen."""
        self._watch_timer.stop()
        if self._worker is not None and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)  # Maximal 2 Sekunden warten
        if self in _active_dialogs:
            _active_dialogs.remove(self)
        if event is not None:
            super().closeEvent(event)

    def reject(self) -> None:
        self.close()

    def _open_in_word(self) -> None:
        """Öffnet das Dokument erneut in Microsoft Word."""
        try:
            os.startfile(str(self._path))
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Word konnte nicht gestartet werden:\n{exc}")

    def _copy_to_clipboard(self) -> None:
        """Kopiert die zuletzt übersetzten Vokabeln im Format 'Wort - Übersetzung' in die Zwischenablage."""
        if not self._last_translated_pairs:
            QMessageBox.information(
                self,
                "Hinweis",
                "Es wurden noch keine Vokabeln übersetzt.\n"
                "Schreibe Wörter in Word und nutze /übd zum Übersetzen.",
            )
            return

        text = "\n".join(f"{f} - {b}" for f, b in self._last_translated_pairs)
        clipboard = QGuiApplication.clipboard()
        if clipboard:
            clipboard.setText(text)
            self._log_edit.append(
                "📋 Übersetzte Vokabeln in die Zwischenablage kopiert! "
                "(Du kannst sie in Word mit Strg+V einfügen)"
            )

    def _check_file_modified(self) -> None:
        """Prüft, ob die .docx-Datei auf der Festplatte geändert wurde (durch Strg+S in Word)."""
        if not self._path.exists():
            return
        try:
            current_mtime = self._path.stat().st_mtime
            if current_mtime > self._last_mtime:
                # 400ms warten, damit Word die Datei vollständig schreiben kann
                QTimer.singleShot(400, self._process_document_now)
        except Exception:
            pass

    def _process_document_now(self) -> None:
        """Startet die Hintergrundverarbeitung der Word-Datei.

        Läuft in einem _DocProcessWorker-QThread – die UI friert nicht ein,
        auch wenn die Übersetzung mehrere Sekunden dauert.
        """
        if not self._path.exists():
            return
        # Wenn bereits ein Worker läuft, nicht neu starten (verhindert Duplikate)
        if self._worker is not None and self._worker.isRunning():
            return

        # Mtime sofort aktualisieren, damit _check_file_modified nicht erneut feuert
        try:
            self._last_mtime = self._path.stat().st_mtime
        except Exception:
            pass

        self._status_lbl.setText("⏳  Übersetze …")
        self._status_lbl.setStyleSheet("color: #f0c040;")

        self._worker = _DocProcessWorker(
            self._path, self._lang_front, self._lang_back, parent=self
        )
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.error_occurred.connect(self._on_worker_error)
        self._worker.start()

    def _on_worker_finished(self, paare: list, cmd_desc: object) -> None:
        """Wird im Haupt-Thread aufgerufen, wenn der Worker fertig ist."""
        if not paare:
            self._status_lbl.setText("🟢  Word-Überwachung aktiv")
            self._status_lbl.setStyleSheet("color: #4ade80;")
            return

        neu_count = 0
        dup_count = 0
        sample_words: list[str] = []
        translated_pairs: list[tuple[str, str]] = []

        for f, b, lf, lb in paare:
            translated_pairs.append((f, b))
            res = self._trainer.add_vokabel(
                front=f,
                back=b,
                kategorie=self._kategorie,
                lang_front=lf,
                lang_back=lb,
            )
            if res is not None:
                neu_count += 1
                if len(sample_words) < 5:
                    sample_words.append(f"{f} -> {b}")
            else:
                dup_count += 1

        self._last_translated_pairs = translated_pairs

        if neu_count > 0:
            cmd_info = f" [Befehl: {cmd_desc}]" if cmd_desc else ""
            msg = f"✔ {neu_count} neue Vokabel(n) importiert!{cmd_info}"
            if sample_words:
                msg += f"\n   {', '.join(sample_words)}"
            if dup_count > 0:
                msg += f" ({dup_count} Duplikate übersprungen)"
            self._log_edit.append(msg)
            self._status_lbl.setText(f"✔  Zuletzt importiert: {neu_count} Vokabel(n)")
            self._status_lbl.setStyleSheet("color: #38bdf8;")
            self.vocabularies_imported.emit(neu_count)
        elif dup_count > 0 and cmd_desc:
            self._log_edit.append(
                f"ℹ Alle {dup_count} Vokabeln aus der Datei waren bereits vorhanden."
            )
            self._status_lbl.setText("🟢  Word-Überwachung aktiv")
            self._status_lbl.setStyleSheet("color: #4ade80;")
        else:
            self._status_lbl.setText("🟢  Word-Überwachung aktiv")
            self._status_lbl.setStyleSheet("color: #4ade80;")

    def _on_worker_error(self, error_msg: str) -> None:
        """Wird aufgerufen, wenn der Worker-Thread einen Fehler meldet."""
        self._log_edit.append(
            f"⚠ Datei wird noch von Word gespeichert, versuche gleich erneut: {error_msg}"
        )
        self._status_lbl.setText("🟢  Word-Überwachung aktiv")
        self._status_lbl.setStyleSheet("color: #4ade80;")


# ── Hilfsfunktion: Vorlage erstellen oder Vorhandenes öffnen ──────────────────
def open_word_integration(
    trainer: VokabelTrainer,
    kategorie: str = "Sprache",
    lang_front: str = "Englisch",
    lang_back: str = "Deutsch",
    parent: QWidget | None = None,
) -> WordCompanionDialog | None:
    """Bietet an, ein neues Word-Dokument zu erstellen oder ein bestehendes zu öffnen."""
    box = QMessageBox(parent)
    box.setWindowTitle("Microsoft Word öffnen")
    box.setText("Möchtest du ein vorhandenes Dokument auswählen oder ein neues erstellen?")
    btn_new = box.addButton("➕  Neues Dokument erstellen", QMessageBox.ButtonRole.ActionRole)
    btn_existing = box.addButton("📂  Vorhandenes Dokument öffnen", QMessageBox.ButtonRole.ActionRole)
    btn_cancel = box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(btn_existing)
    box.exec()

    clicked_btn = box.clickedButton()
    if clicked_btn == btn_cancel or clicked_btn is None:
        return None

    docx_file: Path | None = None

    if clicked_btn == btn_new:
        save_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Neues Word-Dokument speichern unter",
            str(Path.home() / "Desktop" / "Vokabelliste.docx"),
            "Word-Dokumente (*.docx)",
        )
        if not save_path:
            return None
        docx_file = Path(save_path)
        if docx_file.suffix.lower() != ".docx":
            docx_file = docx_file.with_suffix(".docx")

        try:
            from docx import Document  # type: ignore[import-untyped]
            doc = Document()
            doc.add_heading("Meine Vokabelliste", level=1)
            doc.add_paragraph(
                "Schreibe hier deine Wörter zeilenweise auf.\n"
                "Schreibe am Ende /übd (für Deutsch) oder /übe (für Englisch) und drücke Strg+S!\n"
            )
            doc.add_paragraph("apple")
            doc.add_paragraph("banana")
            doc.add_paragraph("/übd")
            doc.save(str(docx_file))
        except Exception as exc:
            if parent:
                QMessageBox.critical(parent, "Fehler", f"Konnte Vorlage nicht erstellen:\n{exc}")
            return None
    else:
        start_dir = str(Path.home() / "Desktop")
        selected_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Word-Dokument (.docx) auswählen",
            start_dir,
            "Word-Dokumente (*.docx)",
        )
        if not selected_path:
            return None
        docx_file = Path(selected_path)

    # In Microsoft Word öffnen
    try:
        os.startfile(str(docx_file))
    except Exception as exc:
        if parent:
            QMessageBox.critical(parent, "Fehler", f"Microsoft Word konnte nicht gestartet werden:\n{exc}")
        return None

    # Begleitdialog erstellen und anzeigen
    dlg = WordCompanionDialog(
        docx_path=docx_file,
        trainer=trainer,
        kategorie=kategorie,
        lang_front=lang_front,
        lang_back=lang_back,
        parent=parent,
    )
    dlg.show()
    return dlg
