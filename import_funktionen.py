# import_funktionen.py – Datei-Import (Word .docx & Textdatei .txt) & Import-Dialog
"""
Dieses Modul verwaltet den vollständigen Import-Workflow für Vokabeln:
1. Zeilen-Parser (split_line):
   - Erkennt Pipe (|), Tabulator (\t), Gedankenstriche (–, —) und Leerzeichen-Minus (' - ')
   - Komma (,) und Semikolon (;) werden als Synonyme innerhalb einer Sprache bewahrt
2. Dateileser (parse_datei):
   - .docx: Liest Word-Tabellen (mind. 2 Spalten) und Freitext-Absätze
   - .txt: Liest Zeilen mit automatischem Encoding-Fallback (UTF-8, Windows-1252)
3. ImportDialog:
   - Auswahl von Zielkategorie und Sprachen
   - Direktimport oder Start der Microsoft Word Live-Überwachung
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Tuple

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from backend import KATEGORIEN, STANDARD_SPRACHEN, VokabelTrainer
from kategorien import _flag_icon


# ── Trenner-Erkennung für Vokabelpaare ─────────────────────────────────────────
def split_line(line: str) -> tuple[str, str] | None:
    """Zeile in (Vorderseite, Rückseite) aufteilen.

    Unterstützte Trenner (in Prioritätsreihenfolge):
      1. | (Pipe)         – empfohlen, eindeutig
      2. Tab              – für TSV/Excel-Exporte
      3. – / — (Word)     – En-Dash und Em-Dash aus Word
      4. ' - '            – Standard-Trenner (Leerzeichen-Minus-Leerzeichen)
      5. '-'              – nacktes Minus (letzter Ausweg, ab ≥3+2 Zeichen)

    Semikolon (;) und Komma (,) sind KEINE Trenner zwischen den Sprachen,
    sondern trennen mehrere Bedeutungen/Synonyme innerhalb einer Sprache.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None

    # 1. Pipe (eindeutig)
    if "|" in line:
        a, b = line.split("|", 1)
        a, b = a.strip(), b.strip()
        if a and b:
            return a, b

    # 2. Tab (TSV / Spaltenexport) – bereinigt führendes Minus
    if "\t" in line:
        a, b = line.split("\t", 1)
        a, b = a.strip(), b.strip()
        for prefix in ["\u2013 ", "\u2014 ", "- "]:
            if b.startswith(prefix):
                b = b[len(prefix):].strip()
                break
        if a and b:
            return a, b

    # 3. Gedankenstriche aus Word (En-Dash –, Em-Dash —)
    for sep in ["\u2013", "\u2014"]:
        if sep in line:
            a, b = line.split(sep, 1)
            a, b = a.strip(), b.strip()
            if a and b:
                return a, b

    # 4. Normales Minus mit Leerzeichen ' - ' (Standard-Trenner)
    if " - " in line:
        a, b = line.split(" - ", 1)
        a, b = a.strip(), b.strip()
        if a and b:
            return a, b

    # 5. Nacktes Minus '-' (Mindestlänge verhindert Trennung bei 'anti-virus' etc.)
    if "-" in line:
        a, b = line.split("-", 1)
        a, b = a.strip(), b.strip()
        if len(a) >= 3 and len(b) >= 2:
            return a, b

    return None


# Maximale Dateigröße für Import: 25 MB
_MAX_IMPORT_FILE_SIZE = 25 * 1024 * 1024
# Maximale Anzahl importierbarer Vokabelpaare pro Datei
_MAX_IMPORT_PAIRS = 10_000


def parse_datei(path: Path) -> list[tuple[str, str]]:
    """Liest Vokabelpaare aus einer Word- oder Textdatei.
    Begrenzt auf 25 MB und maximal 10.000 Paare, um DoS durch überdimensionierte Dateien zu verhindern.
    """
    paare: list[tuple[str, str]] = []

    # Dateigröße prüfen, bevor wir die Datei öffnen
    try:
        file_size = path.stat().st_size
    except Exception:
        return paare
    if file_size > _MAX_IMPORT_FILE_SIZE:
        raise RuntimeError(
            f"Die Datei ist zu groß ({file_size // (1024*1024)} MB). "
            f"Maximal {_MAX_IMPORT_FILE_SIZE // (1024*1024)} MB sind erlaubt."
        )

    if path.suffix.lower() == ".docx":
        try:
            from docx import Document  # type: ignore[import-untyped]
        except ImportError:
            raise RuntimeError(
                "Das Paket 'python-docx' ist nicht installiert.\n"
                "Word-Dateien (.docx) können ohne dieses Paket nicht gelesen werden."
            )
        doc = Document(str(path))
        # 1. Tabellen mit mindestens 2 Spalten
        for table in doc.tables:
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells]
                if len(cells) >= 2 and cells[0] and cells[1]:
                    if cells[0].lower() in ["vorderseite", "wort", "frage", "begriff"]:
                        continue
                    paare.append((cells[0], cells[1]))
        # 2. Falls keine Tabellen vorhanden sind, Absätze durchsuchen
        if not paare:
            for para in doc.paragraphs:
                result = split_line(para.text)
                if result:
                    paare.append(result)
    else:
        # Textdatei: UTF-8 mit Fallback auf Windows-1252
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp1252", errors="replace")
        for line in text.splitlines():
            result = split_line(line)
            if result:
                paare.append(result)
    # Paare auf Maximum begrenzen
    return paare[:_MAX_IMPORT_PAIRS]


def import_datei(
    trainer: VokabelTrainer,
    path: Path,
    kategorie: str,
    lang_front: str = "Englisch",
    lang_back: str = "Deutsch",
) -> tuple[int, int]:
    """Importiert eine Datei in den Trainer. Gibt (anzahl_neu, anzahl_duplikate) zurück."""
    paare = parse_datei(path)
    neu_count = 0
    dup_count = 0
    for front, back in paare:
        res = trainer.add_vokabel(front, back, kategorie, lang_front, lang_back)
        if res is not None:
            neu_count += 1
        else:
            dup_count += 1
    return neu_count, dup_count


# ── Dialog: Import-Kategorie & Sprachen wählen ────────────────────────────────
class ImportDialog(QDialog):
    """Dialog zur Auswahl von Zielkategorie und Sprachpaar vor dem Import."""
    def __init__(
        self,
        parent: QWidget | None = None,
        trainer: VokabelTrainer | None = None,
        lang_f: str = "Englisch",
        lang_b: str = "Deutsch",
        canonical_lf: str = "",
        canonical_lb: str = "",
    ) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._canonical_lf, self._canonical_lb = canonical_lf, canonical_lb
        self.setWindowTitle("Importieren – Kategorie & Sprachen")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl = QLabel("1. ZIELKATEGORIE WÄHLEN")
        lbl.setObjectName("sectionLabel")
        self._combo = QComboBox()
        kats = self._trainer.get_kategorien() if self._trainer else KATEGORIEN
        for k, info in kats.items():
            self._combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
        self._combo.setAccessibleName(" Zielkategorie für den Import auswählen")
        self._combo.currentIndexChanged.connect(self._on_kat_changed)
        lbl.setBuddy(self._combo)

        self._lang_container = QWidget()
        lang_layout = QHBoxLayout(self._lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(10)

        col_left = QVBoxLayout()
        lbl_lf = QLabel("SPRACHE LINKS")
        lbl_lf.setObjectName("sectionLabel")
        self._lang_f = QComboBox()
        self._lang_f.setEditable(True)
        self._lang_f.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_f.addItem(_flag_icon(s), s)
        self._lang_f.setCurrentText(lang_f)
        self._lang_f.setAccessibleName(" Sprache der linken Spalte")
        self._lang_f.currentTextChanged.connect(self._on_lang_f_changed)
        col_left.addWidget(lbl_lf)
        col_left.addWidget(self._lang_f)

        arrow = QLabel("→")
        arrow.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        arrow.setStyleSheet("color: #7986e0; padding-top: 18px;")

        col_right = QVBoxLayout()
        lbl_lb = QLabel("SPRACHE RECHTS")
        lbl_lb.setObjectName("sectionLabel")
        self._lang_b = QComboBox()
        self._lang_b.setEditable(True)
        self._lang_b.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_b.addItem(_flag_icon(s), s)
        self._lang_b.setCurrentText(lang_b)
        self._lang_b.setAccessibleName(" Sprache der rechten Spalte")
        self._lang_b.currentTextChanged.connect(self._on_lang_b_changed)
        col_right.addWidget(lbl_lb)
        col_right.addWidget(self._lang_b)

        lang_layout.addLayout(col_left)
        lang_layout.addWidget(arrow)
        lang_layout.addLayout(col_right)

        self._warn_widget = QWidget()
        self._warn_widget.setObjectName("warnBox")
        self._warn_widget.setStyleSheet("#warnBox { background: #3d2f00; border: 1px solid #f0a500; border-radius: 6px; padding: 2px; }")
        warn_layout = QVBoxLayout(self._warn_widget)
        warn_layout.setContentsMargins(12, 8, 12, 8)
        warn_layout.setSpacing(8)
        self._warn_lbl = QLabel()
        self._warn_lbl.setWordWrap(True)
        self._warn_lbl.setStyleSheet("color: #f0c040; font-size: 12px;")
        self._warn_lbl.setAccessibleName(" Richtungshinweis")
        warn_layout.addWidget(self._warn_lbl)

        warn_btn_row = QHBoxLayout()
        warn_btn_row.setSpacing(8)
        self._btn_empfehlung = QPushButton()
        self._btn_empfehlung.setObjectName("primaryBtn")
        self._btn_empfehlung.setAutoDefault(False)
        self._btn_empfehlung.setDefault(False)
        self._btn_empfehlung.clicked.connect(self._empfehlung_uebernehmen)
        self._btn_weiter = QPushButton("Trotzdem so behalten")
        self._btn_weiter.setObjectName("secondaryBtn")
        self._btn_weiter.setAutoDefault(False)
        self._btn_weiter.setDefault(False)
        self._btn_weiter.clicked.connect(self._warn_widget.hide)
        warn_btn_row.addWidget(self._btn_empfehlung)
        warn_btn_row.addWidget(self._btn_weiter)
        warn_layout.addLayout(warn_btn_row)
        self._warn_widget.hide()

        self._hint = QLabel("")
        self._hint.setObjectName("statsLabel")
        self._hint.setWordWrap(True)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_open_word = QPushButton("📝  Datei öffnen")
        self._btn_open_word.setObjectName("secondaryBtn")
        self._btn_open_word.setAccessibleName("Word-Dokument öffnen und live überwachen")
        self._btn_open_word.setAutoDefault(False)
        self._btn_open_word.setDefault(False)
        self._btn_open_word.clicked.connect(self._on_open_word_clicked)

        self._btn_cancel = QPushButton("Abbrechen")
        self._btn_cancel.setObjectName("secondaryBtn")
        self._btn_cancel.setAutoDefault(False)
        self._btn_cancel.setDefault(False)
        self._btn_cancel.clicked.connect(self.reject)

        self._btn_import = QPushButton("📥  Datei importieren")
        self._btn_import.setObjectName("primaryBtn")
        self._btn_import.setAccessibleName("Datei auswählen und direkt importieren")
        self._btn_import.setAutoDefault(False)
        self._btn_import.setDefault(False)
        self._btn_import.clicked.connect(self.accept)

        btn_row.addWidget(self._btn_open_word)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_cancel)
        btn_row.addWidget(self._btn_import)

        for w in [lbl, self._combo, self._lang_container, self._warn_widget, self._hint]:
            layout.addWidget(w)
        layout.addLayout(btn_row)
        self._on_kat_changed()
        self._combo.setFocus()

    def _on_open_word_clicked(self) -> None:
        """Öffnet Microsoft Word und startet die Live-Überwachung."""
        try:
            from word_bridge import open_word_integration
            kat, lf, lb = self.get_data()
            parent_w = self.parentWidget()
            if self._trainer:
                companion = open_word_integration(self._trainer, kat, lf, lb, parent=parent_w)
                if companion:
                    self.reject()
                    if parent_w is not None:
                        load_list = getattr(parent_w, "_load_list", None)
                        if callable(load_list):
                            companion.vocabularies_imported.connect(lambda _count, _load_list=load_list: _load_list())
        except Exception:
            pass

    def _on_lang_f_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_b.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_b.blockSignals(True)
                    self._lang_b.setCurrentText(s)
                    self._lang_b.blockSignals(False)
                    break
        self._check_direction()
        self._on_kat_changed()

    def _on_lang_b_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_f.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_f.blockSignals(True)
                    self._lang_f.setCurrentText(s)
                    self._lang_f.blockSignals(False)
                    break
        self._check_direction()
        self._on_kat_changed()

    def _check_direction(self) -> None:
        if self._combo.currentData() != "Sprache" or not self._canonical_lf or not self._canonical_lb:
            self._warn_widget.hide()
            return
        lf, lb = self._lang_f.currentText().strip().lower(), self._lang_b.currentText().strip().lower()
        clf, clb = self._canonical_lf.strip().lower(), self._canonical_lb.strip().lower()
        if lf == clb and lb == clf and clf != clb:
            self._warn_lbl.setText(
                f"⚠ Du hast bereits Vokabeln in der Richtung <b>{self._canonical_lf} → {self._canonical_lb}</b>.<br>Die gewählte Richtung ist umgekehrt."
            )
            self._btn_empfehlung.setText(f"✔  Empfehlung: {self._canonical_lf} → {self._canonical_lb}")
            self._warn_widget.show()
        else:
            self._warn_widget.hide()

    def _empfehlung_uebernehmen(self) -> None:
        if self._canonical_lf and self._canonical_lb:
            self._lang_f.blockSignals(True)
            self._lang_b.blockSignals(True)
            self._lang_f.setCurrentText(self._canonical_lf)
            self._lang_b.setCurrentText(self._canonical_lb)
            self._lang_f.blockSignals(False)
            self._lang_b.blockSignals(False)
            self._warn_widget.hide()
            self._on_kat_changed()

    def _on_kat_changed(self) -> None:
        kat = self._combo.currentData()
        is_sprache = kat == "Sprache"
        self._lang_container.setVisible(is_sprache)
        kat_info = self._trainer.get_kategorie_info(kat) if self._trainer else KATEGORIEN.get(kat, {})
        if is_sprache:
            self._check_direction()
            lf = self._lang_f.currentText().strip() or "Fremdsprache"
            lb = self._lang_b.currentText().strip() or "Deutsch"
            self._hint.setText(
                f"Format pro Zeile (Textdatei) oder Tabellenspalten (Word/Excel):\n"
                f"  [{lf}-Wort] - [{lb}-Übersetzung]\n\n"
                f"Komma (,) für mehrere Bedeutungen, z. B.:\n"
                f"  to run - laufen, rennen, fahren\n"
                f"  fast, quick - schnell\n\n"
                f"Weitere Trenner: | (Pipe) oder Tab"
            )
        else:
            self._warn_widget.hide()
            lbl_f = kat_info.get("lbl_front", "Vorderseite")
            lbl_b = kat_info.get("lbl_back", "Rückseite")
            self._hint.setText(
                f"Format pro Zeile (Textdatei) oder Tabellenspalten (Word/Excel):\n"
                f"  [{lbl_f}] - [{lbl_b}]\n\n"
                f"Komma (,) für mehrere Bedeutungen. Weitere Trenner: | (Pipe) oder Tab"
            )

    def get_data(self) -> tuple[str, str, str]:
        kat = self._combo.currentData() or "Sprache"
        lf = self._lang_f.currentText().strip() if kat == "Sprache" else ""
        lb = self._lang_b.currentText().strip() if kat == "Sprache" else ""
        return kat, lf or "Englisch", lb or "Deutsch"
