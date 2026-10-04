# verwaltung.py – Vokabelverwaltung, Tabellenansicht & Vokabel-Dialoge
"""
Dieses Modul bündelt das gesamte Vokabelverwaltungs-Feature der VokabelMeister:
1. AddVokabelDialog:
   - Erstellen neuer Vokabeln mit Kategorieauswahl, Richtungswarnung und Flaggen
2. DeleteDialog:
   - Barrierefreies Löschfenster mit Kontrollkästchen, Suchfilter, Mehrfachauswahl und Undo
3. VerwaltungView:
   - Barrierefreie Datentabelle (5 Spalten: #, Vokabel, Score, Abgefragt, Richtig)
   - Vollständige Tastaturbedienung (Pfeiltasten, Tab/Backtab, Entf)
   - Schnellsuche (Strg+F), Kategorie-Filter und Rückgängig-Funktion (Strg+Z)
   - Anbindung an Datei-Import (Text/Word)
"""
from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QSize, QTimer, QStringListModel
from PyQt6.QtGui import (
    QColor,
    QFocusEvent,
    QFont,
    QKeyEvent,
    QKeySequence,
    QShortcut,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend import KATEGORIEN, STANDARD_SPRACHEN, Vokabel, VokabelTrainer
from import_funktionen import ImportDialog, import_datei
from kategorien import _flag_icon
from style import NavigableTableWidget, _sort_vokabel_key

logger = logging.getLogger(__name__)


# ── Dialog: Vokabel hinzufügen ────────────────────────────────────────────────
class AddVokabelDialog(QDialog):
    """Dialog zum Hinzufügen einer einzelnen Vokabel mit Sprachrichtungswarnung."""
    def __init__(
        self,
        parent: QWidget | None = None,
        trainer: VokabelTrainer | None = None,
        lang_f: str = "Englisch",
        lang_b: str = "Deutsch",
        canonical_lf: str = "",
        canonical_lb: str = "",
        initial_kat: str | None = None,
    ) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._canonical_lf, self._canonical_lb = canonical_lf, canonical_lb
        self.setWindowTitle("Vokabel hinzufügen")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl_kat = QLabel("1. KATEGORIE WÄHLEN")
        lbl_kat.setObjectName("sectionLabel")
        self._kat_combo = QComboBox()
        kats = self._trainer.get_kategorien() if self._trainer else KATEGORIEN
        for k, info in kats.items():
            self._kat_combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
        if initial_kat and initial_kat in kats:
            for idx in range(self._kat_combo.count()):
                if self._kat_combo.itemData(idx) == initial_kat:
                    self._kat_combo.setCurrentIndex(idx)
                    break
        self._kat_combo.setAccessibleName(" Kategorie auswählen")
        self._kat_combo.currentIndexChanged.connect(self._on_kat_changed)
        lbl_kat.setBuddy(self._kat_combo)

        self._lang_container = QWidget()
        lang_layout = QHBoxLayout(self._lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(10)

        col_left = QVBoxLayout()
        lbl_lang_f = QLabel("SPRACHE LINKS")
        lbl_lang_f.setObjectName("sectionLabel")
        self._lang_f_combo = QComboBox()
        self._lang_f_combo.setEditable(True)
        self._lang_f_combo.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_f_combo.addItem(_flag_icon(s), s)
        self._lang_f_combo.setCurrentText(lang_f)
        self._lang_f_combo.setAccessibleName(" Sprache der Vorderseite")
        self._lang_f_combo.currentTextChanged.connect(self._on_lang_f_changed)
        lbl_lang_f.setBuddy(self._lang_f_combo)
        col_left.addWidget(lbl_lang_f)
        col_left.addWidget(self._lang_f_combo)

        arrow_lbl = QLabel("→")
        arrow_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        arrow_lbl.setStyleSheet("color: #7986e0; padding-top: 18px;")

        col_right = QVBoxLayout()
        lbl_lang_b = QLabel("SPRACHE RECHTS")
        lbl_lang_b.setObjectName("sectionLabel")
        self._lang_b_combo = QComboBox()
        self._lang_b_combo.setEditable(True)
        self._lang_b_combo.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_b_combo.addItem(_flag_icon(s), s)
        self._lang_b_combo.setCurrentText(lang_b)
        self._lang_b_combo.setAccessibleName(" Sprache der Rückseite")
        self._lang_b_combo.currentTextChanged.connect(self._on_lang_b_changed)
        lbl_lang_b.setBuddy(self._lang_b_combo)
        col_right.addWidget(lbl_lang_b)
        col_right.addWidget(self._lang_b_combo)

        lang_layout.addLayout(col_left)
        lang_layout.addWidget(arrow_lbl)
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

        self._lbl_front = QLabel("VORDERSEITE")
        self._lbl_front.setObjectName("sectionLabel")
        self._front = QLineEdit()
        self._front.setMaxLength(2000)  # Max 2000 Zeichen
        self._lbl_front.setBuddy(self._front)

        self._lbl_back = QLabel("RÜCKSEITE")
        self._lbl_back.setObjectName("sectionLabel")
        self._back = QLineEdit()
        self._back.setMaxLength(2000)  # Max 2000 Zeichen
        self._lbl_back.setBuddy(self._back)

        self._front.returnPressed.connect(self._back.setFocus)
        self._back.returnPressed.connect(self._on_save)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        save = btns.button(QDialogButtonBox.StandardButton.Save)
        cancel = btns.button(QDialogButtonBox.StandardButton.Cancel)
        if save:
            save.setText("💾  Speichern")
            save.setObjectName("primaryBtn")
            save.setAutoDefault(False)
            save.setDefault(False)
        if cancel:
            cancel.setObjectName("secondaryBtn")
            cancel.setAutoDefault(False)
            cancel.setDefault(False)

        for w in [lbl_kat, self._kat_combo, self._lang_container, self._warn_widget, self._lbl_front, self._front, self._lbl_back, self._back, btns]:
            layout.addWidget(w)

        self._on_kat_changed()
        self._kat_combo.setFocus()

    def _on_lang_f_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_b_combo.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_b_combo.blockSignals(True)
                    self._lang_b_combo.setCurrentText(s)
                    self._lang_b_combo.blockSignals(False)
                    break
        self._on_kat_changed()
        self._check_direction()

    def _on_lang_b_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_f_combo.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_f_combo.blockSignals(True)
                    self._lang_f_combo.setCurrentText(s)
                    self._lang_f_combo.blockSignals(False)
                    break
        self._on_kat_changed()
        self._check_direction()

    def _check_direction(self) -> None:
        if self._kat_combo.currentData() != "Sprache" or not self._canonical_lf or not self._canonical_lb:
            self._warn_widget.hide()
            return
        lf = self._lang_f_combo.currentText().strip().lower()
        lb = self._lang_b_combo.currentText().strip().lower()
        clf = self._canonical_lf.strip().lower()
        clb = self._canonical_lb.strip().lower()
        if lf == clb and lb == clf and clf != clb:
            self._warn_lbl.setText(
                f"⚠  Du hast bereits Vokabeln in der Richtung <b>{self._canonical_lf} → {self._canonical_lb}</b>. Die gewählte Richtung ist umgekehrt — das kann verwirren."
            )
            self._btn_empfehlung.setText(f"✔  Empfehlung: {self._canonical_lf} → {self._canonical_lb}")
            self._warn_widget.show()
        else:
            self._warn_widget.hide()

    def _empfehlung_uebernehmen(self) -> None:
        if self._canonical_lf and self._canonical_lb:
            self._lang_f_combo.blockSignals(True)
            self._lang_b_combo.blockSignals(True)
            self._lang_f_combo.setCurrentText(self._canonical_lf)
            self._lang_b_combo.setCurrentText(self._canonical_lb)
            self._lang_f_combo.blockSignals(False)
            self._lang_b_combo.blockSignals(False)
            self._warn_widget.hide()
            self._on_kat_changed()

    def _on_kat_changed(self) -> None:
        kat = self._kat_combo.currentData()
        is_sprache = kat == "Sprache"
        self._lang_container.setVisible(is_sprache)
        if not is_sprache:
            self._warn_widget.hide()
        kat_info = self._trainer.get_kategorie_info(kat) if self._trainer else KATEGORIEN.get(kat, {})
        if is_sprache:
            lf = self._lang_f_combo.currentText().strip() or "Fremdsprache"
            lb = self._lang_b_combo.currentText().strip() or "Zielsprache"
            self._lbl_front.setText(lf.upper())
            self._front.setAccessibleName(f" Vokabel auf {lf}")
            self._lbl_back.setText(lb.upper())
            self._back.setAccessibleName(f" Vokabel auf {lb}")
        else:
            lbl_f = kat_info.get("lbl_front", "Vorderseite")
            lbl_b = kat_info.get("lbl_back", "Rückseite")
            self._lbl_front.setText(lbl_f.upper())
            self._front.setAccessibleName(f" {lbl_f} eingeben")
            self._lbl_back.setText(lbl_b.upper())
            self._back.setAccessibleName(f" {lbl_b} eingeben")

    def _on_save(self) -> None:
        if not self._front.text().strip() or not self._back.text().strip():
            QMessageBox.warning(self, "Unvollständig", "Bitte trage sowohl die Vorderseite als auch die Rückseite ein.")
            return
        self.accept()

    def get_values(self) -> tuple[str, str, str, str, str]:
        kat = self._kat_combo.currentData() or "Sprache"
        lf = self._lang_f_combo.currentText().strip() if kat == "Sprache" else ""
        lb = self._lang_b_combo.currentText().strip() if kat == "Sprache" else ""
        return (self._front.text().strip(), self._back.text().strip(), kat, lf or "Englisch", lb or "Deutsch")


# ── Dialog: Vokabel bearbeiten ────────────────────────────────────────────────
class EditVokabelDialog(QDialog):
    """Dialog zum Bearbeiten einer bestehenden Vokabel mit Barrierefreiheitsunterstützung."""
    def __init__(
        self,
        vokabel: Vokabel,
        parent: QWidget | None = None,
        trainer: VokabelTrainer | None = None,
    ) -> None:
        super().__init__(parent)
        self._vokabel = vokabel
        self._trainer = trainer
        self.setWindowTitle("Vokabel bearbeiten")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        lbl_kat = QLabel("KATEGORIE")
        lbl_kat.setObjectName("sectionLabel")
        self._kat_combo = QComboBox()
        kats = self._trainer.get_kategorien() if self._trainer else KATEGORIEN
        selected_idx = 0
        for idx, (k, info) in enumerate(kats.items()):
            self._kat_combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
            if k == self._vokabel.kategorie:
                selected_idx = idx
        self._kat_combo.setCurrentIndex(selected_idx)
        self._kat_combo.setAccessibleName(" Kategorie auswählen")
        self._kat_combo.currentIndexChanged.connect(self._on_kat_changed)
        lbl_kat.setBuddy(self._kat_combo)

        self._lang_container = QWidget()
        lang_layout = QHBoxLayout(self._lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(10)

        col_left = QVBoxLayout()
        lbl_lang_f = QLabel("SPRACHE LINKS")
        lbl_lang_f.setObjectName("sectionLabel")
        self._lang_f_combo = QComboBox()
        self._lang_f_combo.setEditable(True)
        self._lang_f_combo.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_f_combo.addItem(_flag_icon(s), s)
        self._lang_f_combo.setCurrentText(self._vokabel.lang_front or "Englisch")
        self._lang_f_combo.setAccessibleName(" Sprache der Vorderseite")
        lbl_lang_f.setBuddy(self._lang_f_combo)
        col_left.addWidget(lbl_lang_f)
        col_left.addWidget(self._lang_f_combo)

        arrow_lbl = QLabel("→")
        arrow_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        arrow_lbl.setStyleSheet("color: #7986e0; padding-top: 18px;")

        col_right = QVBoxLayout()
        lbl_lang_b = QLabel("SPRACHE RECHTS")
        lbl_lang_b.setObjectName("sectionLabel")
        self._lang_b_combo = QComboBox()
        self._lang_b_combo.setEditable(True)
        self._lang_b_combo.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_b_combo.addItem(_flag_icon(s), s)
        self._lang_b_combo.setCurrentText(self._vokabel.lang_back or "Deutsch")
        self._lang_b_combo.setAccessibleName(" Sprache der Rückseite")
        lbl_lang_b.setBuddy(self._lang_b_combo)
        col_right.addWidget(lbl_lang_b)
        col_right.addWidget(self._lang_b_combo)

        lang_layout.addLayout(col_left)
        lang_layout.addWidget(arrow_lbl)
        lang_layout.addLayout(col_right)

        self._lbl_front = QLabel("VORDERSEITE")
        self._lbl_front.setObjectName("sectionLabel")
        self._front = QLineEdit()
        self._front.setMaxLength(2000)  # Max 2000 Zeichen
        self._front.setText(self._vokabel.front)
        self._lbl_front.setBuddy(self._front)

        self._lbl_back = QLabel("RÜCKSEITE")
        self._lbl_back.setObjectName("sectionLabel")
        self._back = QLineEdit()
        self._back.setMaxLength(2000)  # Max 2000 Zeichen
        self._back.setText(self._vokabel.back)
        self._lbl_back.setBuddy(self._back)

        self._front.returnPressed.connect(self._back.setFocus)
        self._back.returnPressed.connect(self._on_save)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        save = btns.button(QDialogButtonBox.StandardButton.Save)
        cancel = btns.button(QDialogButtonBox.StandardButton.Cancel)
        if save:
            save.setText("💾  Speichern")
            save.setObjectName("primaryBtn")
            save.setAutoDefault(False)
            save.setDefault(False)
        if cancel:
            cancel.setObjectName("secondaryBtn")
            cancel.setAutoDefault(False)
            cancel.setDefault(False)

        for w in [lbl_kat, self._kat_combo, self._lang_container, self._lbl_front, self._front, self._lbl_back, self._back, btns]:
            layout.addWidget(w)

        self._on_kat_changed()
        self._front.setFocus()
        self._front.selectAll()

    def _on_kat_changed(self) -> None:
        kat = self._kat_combo.currentData()
        is_sprache = kat == "Sprache"
        self._lang_container.setVisible(is_sprache)
        kat_info = self._trainer.get_kategorie_info(kat) if self._trainer else KATEGORIEN.get(kat, {})
        if is_sprache:
            lf = self._lang_f_combo.currentText().strip() or "Fremdsprache"
            lb = self._lang_b_combo.currentText().strip() or "Zielsprache"
            self._lbl_front.setText(lf.upper())
            self._front.setAccessibleName(f" Vokabel auf {lf}")
            self._lbl_back.setText(lb.upper())
            self._back.setAccessibleName(f" Vokabel auf {lb}")
        else:
            lbl_f = kat_info.get("lbl_front", "Vorderseite")
            lbl_b = kat_info.get("lbl_back", "Rückseite")
            self._lbl_front.setText(lbl_f.upper())
            self._front.setAccessibleName(f" {lbl_f} bearbeiten")
            self._lbl_back.setText(lbl_b.upper())
            self._back.setAccessibleName(f" {lbl_b} bearbeiten")

    def _on_save(self) -> None:
        front = self._front.text().strip()
        back = self._back.text().strip()
        if not front or not back:
            QMessageBox.warning(self, "Unvollständig", "Bitte trage sowohl die Vorderseite als auch die Rückseite ein.")
            return
        kat = self._kat_combo.currentData() or "Sprache"
        lf = self._lang_f_combo.currentText().strip() if kat == "Sprache" else ""
        lb = self._lang_b_combo.currentText().strip() if kat == "Sprache" else ""

        self._vokabel.front = front
        self._vokabel.back = back
        self._vokabel.kategorie = kat
        self._vokabel.lang_front = lf or "Englisch"
        self._vokabel.lang_back = lb or "Deutsch"
        if self._trainer:
            self._trainer.save()
        self.accept()


# ── Dialog: Vokabeln löschen ──────────────────────────────────────────────────
class DeleteDialog(QDialog):
    """Aufploppendes Dialogfenster zum gezielten Löschen von Vokabeln mit Checkboxen."""
    def __init__(self, trainer: VokabelTrainer, initial_kategorie: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self.setWindowTitle("Vokabeln löschen")
        self.setMinimumSize(540, 500)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Vokabeln zum Löschen auswählen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setAccessibleName(" Vokabeln löschen – Fenster")
        hint = QLabel("Setze bei den Vokabeln ein Häkchen (mit Enter, Leertaste oder Klick), die du löschen möchtest.")
        hint.setObjectName("statsLabel")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_lbl = QLabel("KATEGORIE")
        filter_lbl.setObjectName("sectionLabel")
        self._filter_combo = QComboBox()
        self._filter_combo.addItem("Alle", userData=None)
        for k, info in self._trainer.get_kategorien().items():
            self._filter_combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
        self._filter_combo.setAccessibleName(" Kategorie filtern")
        self._filter_combo.currentIndexChanged.connect(self._load_list)
        filter_lbl.setBuddy(self._filter_combo)
        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self._filter_combo)

        filter_row.addSpacing(12)
        search_lbl = QLabel("SUCHE")
        search_lbl.setObjectName("sectionLabel")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Vokabel suchen …")
        self._search_input.setAccessibleName(" Vokabeln im Löschfenster durchsuchen mit Suchvorschlägen")
        self._search_input.setClearButtonEnabled(True)

        self._completer_model = QStringListModel(self)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(8)

        popup = self._completer.popup()
        if popup is not None:
            popup.setObjectName("completerPopupDel")
            popup.setStyleSheet("""
                QListView#completerPopupDel {
                    background-color: #161922;
                    color: #e8eaf0;
                    border: 1px solid #7986e0;
                    border-radius: 6px;
                    padding: 4px;
                    outline: none;
                    font-size: 13px;
                }
                QListView#completerPopupDel::item {
                    padding: 6px 12px;
                    border-radius: 4px;
                    color: #e8eaf0;
                }
                QListView#completerPopupDel::item:selected {
                    background-color: #2e3460;
                    color: #ffffff;
                    font-weight: bold;
                }
                QListView#completerPopupDel::item:hover {
                    background-color: #1e2235;
                }
            """)
            popup.setAccessibleName(" Suchvorschläge")

        self._search_input.setCompleter(self._completer)
        self._completer.activated.connect(self._on_suggestion_activated)
        self._search_input.returnPressed.connect(self._on_search_return_pressed)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(100)
        self._search_timer.timeout.connect(self._load_list)
        self._search_input.textChanged.connect(lambda: self._search_timer.start())

        search_lbl.setBuddy(self._search_input)
        filter_row.addWidget(search_lbl)
        filter_row.addWidget(self._search_input, stretch=1)
        layout.addLayout(filter_row)

        select_row = QHBoxLayout()
        btn_desel_all = QPushButton("☐  Alle abwählen")
        btn_desel_all.setObjectName("secondaryBtn")
        btn_desel_all.setAccessibleName(" Alle Häkchen entfernen")
        btn_desel_all.clicked.connect(self._deselect_all)
        select_row.addWidget(btn_desel_all)
        select_row.addStretch()
        layout.addLayout(select_row)

        self._list = QListWidget()
        self._list.setAccessibleName(" Vokabelliste mit Kontrollkästchen zum Löschen")
        self._list.itemChanged.connect(self._update_delete_button_text)
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._btn_delete_selected = QPushButton("🗑  Markierte löschen")
        self._btn_delete_selected.setObjectName("dangerBtn")
        self._btn_delete_selected.setAccessibleName(" Markierte Vokabeln löschen")
        self._btn_delete_selected.clicked.connect(self._delete_selected)

        btn_delete_all = QPushButton("⚠️  Alle löschen")
        btn_delete_all.setObjectName("dangerBtn")
        btn_delete_all.setAccessibleName(" Alle Vokabeln dieser Kategorie löschen")
        btn_delete_all.clicked.connect(self._delete_all)

        self._btn_undo = QPushButton("↩  Rückgängig")
        self._btn_undo.setObjectName("secondaryBtn")
        self._btn_undo.setAccessibleName(" Zuletzt gelöschte Vokabeln wiederherstellen")
        self._btn_undo.clicked.connect(self._undo)
        self._btn_undo.setEnabled(self._trainer.can_undo())

        btn_close = QPushButton("Fertig / Schließen")
        btn_close.setObjectName("primaryBtn")
        btn_close.setAccessibleName(" Lösch-Fenster schließen")
        btn_close.clicked.connect(self.accept)

        for b in (self._btn_delete_selected, btn_delete_all, self._btn_undo, btn_close, btn_desel_all):
            b.setAutoDefault(False)
            b.setDefault(False)

        btn_row.addWidget(self._btn_delete_selected)
        btn_row.addWidget(btn_delete_all)
        btn_row.addWidget(self._btn_undo)
        btn_row.addStretch()
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        if initial_kategorie:
            for idx in range(self._filter_combo.count()):
                if self._filter_combo.itemData(idx) == initial_kategorie:
                    self._filter_combo.setCurrentIndex(idx)
                    break
        self._update_completer_words()
        self._load_list()

    def _update_completer_words(self) -> None:
        """Aktualisiert die Suchvorschläge für das Löschfenster."""
        kat: str | None = self._filter_combo.currentData()
        pool = self._trainer.get_pool(kat)
        suggestions: list[str] = []
        seen: set[str] = set()
        for v in pool:
            pair = f"{v.front}  →  {v.back}"
            if pair not in seen:
                seen.add(pair)
                suggestions.append(pair)
            if v.front and v.front not in seen:
                seen.add(v.front)
                suggestions.append(v.front)
            if v.back and v.back not in seen:
                seen.add(v.back)
                suggestions.append(v.back)
        self._completer_model.setStringList(sorted(suggestions, key=lambda s: s.lower()))

    def _on_suggestion_activated(self, text: str) -> None:
        self._search_timer.stop()
        self._search_input.setText(text)
        self._load_list()
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
            self._list.setFocus()

    def _on_search_return_pressed(self) -> None:
        self._search_timer.stop()
        self._load_list()
        if self._list.count() > 0:
            self._list.setCurrentRow(0)
            self._list.setFocus()

    def _load_list(self) -> None:
        self._list.setUpdatesEnabled(False)
        self._list.blockSignals(True)
        try:
            kat: str | None = self._filter_combo.currentData()
            pool = self._trainer.get_pool(kat)
            query = self._search_input.text().strip().lower()
            if query:
                clean_q = query.replace("→", "-").replace("->", "-")
                if " - " in clean_q:
                    parts = [p.strip() for p in clean_q.split(" - ", 1) if p.strip()]
                    if len(parts) == 2:
                        p1, p2 = parts[0], parts[1]
                        pool = [
                            v for v in pool
                            if (p1 in v.front.lower() and p2 in v.back.lower())
                            or (p2 in v.front.lower() and p1 in v.back.lower())
                        ]
                    else:
                        pool = [
                            v for v in pool
                            if any(p in v.front.lower() or p in v.back.lower() for p in parts)
                        ]
                else:
                    pool = [
                        v for v in pool
                        if query in v.front.lower()
                        or query in v.back.lower()
                        or query in v.kategorie.lower()
                        or query in v.lang_front.lower()
                        or query in v.lang_back.lower()
                    ]
            self._list.clear()
            for vok in pool:
                icon = KATEGORIEN.get(vok.kategorie, {}).get("icon", "")
                lang_tag = f" [{vok.lang_front} → {vok.lang_back}]" if vok.kategorie == "Sprache" and vok.lang_front else ""
                text = f"{icon}{lang_tag}  {vok.front}  →  {vok.back}"
                if vok.attempts > 0:
                    text += f"  [{vok.score:.0f}%]"
                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, vok)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                self._list.addItem(item)
        finally:
            self._list.blockSignals(False)
            self._list.setUpdatesEnabled(True)
        self._update_delete_button_text()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None:
                item.setCheckState(Qt.CheckState.Unchecked)
        self._list.blockSignals(False)
        self._update_delete_button_text()

    def _get_checked_vokabeln(self) -> list[Vokabel]:
        checked: list[Vokabel] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                checked.append(item.data(Qt.ItemDataRole.UserRole))
        return checked

    def _update_delete_button_text(self) -> None:
        count = len(self._get_checked_vokabeln())
        if count > 0:
            self._btn_delete_selected.setText(f"🗑  {count} markierte löschen")
            self._btn_delete_selected.setEnabled(True)
        else:
            self._btn_delete_selected.setText("🗑  Markierte löschen")
            self._btn_delete_selected.setEnabled(False)
        self._btn_undo.setEnabled(self._trainer.can_undo())

    def _undo(self) -> None:
        count = self._trainer.undo_last_delete()
        if count > 0:
            self._load_list()
            QMessageBox.information(
                self, "Rückgängig gemacht",
                f"✔ {count} Vokabel{'n wurden' if count != 1 else ' wurde'} erfolgreich wiederhergestellt.",
            )
        self._update_delete_button_text()

    def _delete_selected(self) -> None:
        checked = self._get_checked_vokabeln()
        if not checked:
            return
        confirm = QMessageBox.question(
            self, "Ausgewählte löschen", f"Möchtest du die {len(checked)} markierte(n) Vokabel(n) wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_vokabeln(checked)
            self._load_list()

    def _delete_all(self) -> None:
        kat: str | None = self._filter_combo.currentData()
        pool = self._trainer.get_pool(kat)
        if not pool:
            QMessageBox.information(self, "Hinweis", "Keine Vokabeln vorhanden.")
            return
        kat_text = f"in Kategorie \u201e{kat}\u201c" if kat else "in allen Kategorien"
        confirm = QMessageBox.question(
            self, "Alle löschen", f"Möchtest du wirklich ALLE {len(pool)} Vokabeln {kat_text} unwiderruflich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_all(kat)
            self._load_list()


# ── Vokabelverwaltung-View (Hauptansicht) ─────────────────────────────────────
class VerwaltungView(QWidget):
    """Zentrale Tabellenverwaltung für Vokabeln mit Tastaturnavigation,
    Schnellsuche (Strg+F), Undo (Strg+Z) und Datei-Import.
    """
    def __init__(self, trainer: VokabelTrainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._last_lang_f = "Englisch"
        self._last_lang_b = "Deutsch"
        self._current_vokabeln: list[Vokabel] = []
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(16)

        title = QLabel("Vokabelverwaltung")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAccessibleName(" Vokabelverwaltung")
        root.addWidget(title)

        # Filter- und Suchzeile
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_lbl = QLabel("KATEGORIE")
        filter_lbl.setObjectName("sectionLabel")
        self._filter_combo = QComboBox()
        self._filter_combo.setAccessibleName(" Kategorie filtern")
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        filter_lbl.setBuddy(self._filter_combo)
        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self._filter_combo)

        filter_row.addSpacing(10)

        search_lbl = QLabel("SUCHE")
        search_lbl.setObjectName("sectionLabel")
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Vokabel oder Übersetzung suchen … (Strg+F)")
        self._search_input.setAccessibleName(" Vokabeln suchen mit automatischen Suchvorschlägen. Mit Tastenkombination Strg plus F erreichbar.")
        self._search_input.setClearButtonEnabled(True)

        # Autovervollständigung / Suchvorschläge mit QCompleter
        self._completer_model = QStringListModel(self)
        self._completer = QCompleter(self._completer_model, self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setMaxVisibleItems(8)

        popup = self._completer.popup()
        if popup is not None:
            popup.setObjectName("completerPopup")
            popup.setStyleSheet("""
                QListView#completerPopup {
                    background-color: #161922;
                    color: #e8eaf0;
                    border: 1px solid #7986e0;
                    border-radius: 6px;
                    padding: 4px;
                    outline: none;
                    font-size: 13px;
                }
                QListView#completerPopup::item {
                    padding: 6px 12px;
                    border-radius: 4px;
                    color: #e8eaf0;
                }
                QListView#completerPopup::item:selected {
                    background-color: #2e3460;
                    color: #ffffff;
                    font-weight: bold;
                }
                QListView#completerPopup::item:hover {
                    background-color: #1e2235;
                }
            """)
            popup.setAccessibleName(" Suchvorschläge")

        self._search_input.setCompleter(self._completer)
        self._completer.activated.connect(self._on_suggestion_activated)
        self._search_input.returnPressed.connect(self._on_search_return_pressed)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self._load_list)
        self._search_input.textChanged.connect(lambda: self._search_timer.start())

        search_lbl.setBuddy(self._search_input)
        filter_row.addWidget(search_lbl)
        filter_row.addWidget(self._search_input, stretch=1)

        self._count_lbl = QLabel("")
        self._count_lbl.setObjectName("statsLabel")
        self._count_lbl.setAccessibleName(" Trefferanzahl")
        filter_row.addWidget(self._count_lbl)

        root.addLayout(filter_row)
        self._update_filter_combo()

        # Statistik-Tabelle (5 Spalten)
        self._table = NavigableTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["#", "Vokabel", "Score", "Abgefragt", "Richtig"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.delete_pressed.connect(self._delete_selected_from_table)
        self._table.row_activated.connect(self._edit_selected_from_table)
        vertical_header = self._table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
        self._table.setShowGrid(False)
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(0, 50)
            self._table.setColumnWidth(2, 85)
            self._table.setColumnWidth(3, 95)
            self._table.setColumnWidth(4, 85)
        self._table.setStyleSheet("""
            QTableWidget { background: #161922; alternate-background-color: #1c2030; border: 1px solid #2a2d3e; border-radius: 6px; gridline-color: transparent; outline: none; }
            QTableWidget:focus { border: 1px solid #7986e0; }
            QTableWidget::item { padding: 6px 10px; color: #e8eaf0; }
            QTableWidget::item:selected { background: #2e3460; color: #ffffff; }
            QHeaderView::section { background: #1e2235; color: #9095b0; font-size: 11px; font-weight: bold; letter-spacing: 1px; padding: 6px 10px; border: none; border-bottom: 1px solid #2a2d3e; }
        """)
        self._table.setAccessibleName(" Vokabel-Tabelle")
        root.addWidget(self._table, stretch=1)

        # Aktions-Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        add_btn = QPushButton("＋  Hinzufügen")
        add_btn.setObjectName("primaryBtn")
        add_btn.setAccessibleName(" Hinzufügen")
        add_btn.clicked.connect(self._hinzufuegen)

        edit_btn = QPushButton("✏  Bearbeiten")
        edit_btn.setObjectName("secondaryBtn")
        edit_btn.setAccessibleName(" Ausgewählte Vokabel bearbeiten")
        edit_btn.clicked.connect(self._edit_selected_from_table)

        del_btn = QPushButton("🗑  Löschen …")
        del_btn.setObjectName("dangerBtn")
        del_btn.setAccessibleName(" Löschen")
        del_btn.clicked.connect(self._loeschen)

        self._undo_btn = QPushButton("↩  Rückgängig")
        self._undo_btn.setObjectName("secondaryBtn")
        self._undo_btn.setAccessibleName(" Zuletzt gelöschte Vokabeln wiederherstellen. Tastenkombination Strg plus Z.")
        self._undo_btn.clicked.connect(self._undo)
        self._undo_btn.setEnabled(self._trainer.can_undo())

        import_btn = QPushButton("📂  Datei importieren")
        import_btn.setObjectName("secondaryBtn")
        import_btn.setAccessibleName(" Importieren")
        import_btn.clicked.connect(self._importieren)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(del_btn)
        btn_row.addWidget(self._undo_btn)
        btn_row.addStretch()
        btn_row.addWidget(import_btn)
        root.addLayout(btn_row)

        # Shortcuts
        self._shortcut_find = QShortcut(QKeySequence("Ctrl+F"), self)
        self._shortcut_find.activated.connect(self._focus_search)

        self._shortcut_undo = QShortcut(QKeySequence("Ctrl+Z"), self)
        self._shortcut_undo.activated.connect(self._undo)

        self.refresh()

    def _focus_search(self) -> None:
        self._search_input.setFocus()
        self._search_input.selectAll()

    def _update_undo_btn(self) -> None:
        self._undo_btn.setEnabled(self._trainer.can_undo())

    def _undo(self) -> None:
        try:
            count = self._trainer.undo_last_delete()
            if count > 0:
                self._load_list()
                self._update_undo_btn()
                QMessageBox.information(
                    self,
                    "Rückgängig gemacht",
                    f"✔ {count} Vokabel{'n wurden' if count != 1 else ' wurde'} erfolgreich wiederhergestellt.",
                )
            else:
                QMessageBox.information(
                    self,
                    "Hinweis",
                    "Es gibt keine gelöschten Vokabeln zum Wiederherstellen.",
                )
        except Exception as exc:
            logger.error("Fehler beim Rückgängigmachen: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Fehler", f"Fehler beim Rückgängigmachen:\n{exc}")

    def _delete_selected_from_table(self) -> None:
        row = self._table.currentRow()
        if row < 0 or row >= len(self._current_vokabeln):
            return
        vok = self._current_vokabeln[row]
        confirm = QMessageBox.question(
            self,
            "Vokabel löschen",
            f"Möchtest du diese Vokabel wirklich löschen?\n\n\u201e{vok.front}  \u2192  {vok.back}\u201c\n\n(Kann mit \u201eRückgängig\u201c oder Strg+Z wiederhergestellt werden)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_vokabel(vok)
            self._load_list()
            self._update_undo_btn()

    def _update_filter_combo(self) -> None:
        cur_data = self._filter_combo.currentData()
        self._filter_combo.blockSignals(True)
        self._filter_combo.clear()
        self._filter_combo.addItem("🗂  Alle", userData=None)
        for k, info in self._trainer.get_kategorien().items():
            self._filter_combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
        idx_to_select = 0
        for idx in range(self._filter_combo.count()):
            if self._filter_combo.itemData(idx) == cur_data:
                idx_to_select = idx
                break
        self._filter_combo.setCurrentIndex(idx_to_select)
        self._filter_combo.blockSignals(False)

    def _on_filter_changed(self) -> None:
        """Wird aufgerufen, wenn eine andere Kategorie im Filter gewählt wird."""
        self._update_search_completer()
        self._load_list()

    def refresh(self) -> None:
        self._update_filter_combo()
        self._update_search_completer()
        self._load_list()
        self._update_undo_btn()

    def _update_search_completer(self) -> None:
        """Aktualisiert die Suchvorschläge für das Hauptsuchfeld."""
        kat: str | None = self._filter_combo.currentData()
        pool = self._trainer.get_pool(kat)
        suggestions: list[str] = []
        seen: set[str] = set()
        for v in pool:
            pair = f"{v.front}  →  {v.back}"
            if pair not in seen:
                seen.add(pair)
                suggestions.append(pair)
            if v.front and v.front not in seen:
                seen.add(v.front)
                suggestions.append(v.front)
            if len(suggestions) >= 300:
                break
        self._completer_model.setStringList(suggestions)

    def _on_suggestion_activated(self, text: str) -> None:
        """Wird aufgerufen, wenn der Benutzer einen Suchvorschlag auswählt (per Klick oder Enter)."""
        self._search_timer.stop()
        self._search_input.setText(text)
        self._load_list()
        if self._table.rowCount() > 0:
            self._table.setCurrentCell(0, 1)
            self._table.setFocus()

    def _on_search_return_pressed(self) -> None:
        """Wird bei Enter im Suchfeld aufgerufen: Springt direkt in die Tabelle auf den ersten Treffer."""
        self._search_timer.stop()
        self._load_list()
        if self._table.rowCount() > 0:
            self._table.setCurrentCell(0, 1)
            self._table.setFocus()

    def _load_list(self) -> None:
        self._table.setUpdatesEnabled(False)
        self._table.blockSignals(True)
        try:
            kat: str | None = self._filter_combo.currentData()
            vokabeln: list[Vokabel] = self._trainer.get_pool(kat)
            total_pool_count = len(vokabeln)

            query = self._search_input.text().strip().lower()
            if query:
                clean_q = query.replace("→", "-").replace("->", "-")
                if " - " in clean_q:
                    parts = [p.strip() for p in clean_q.split(" - ", 1) if p.strip()]
                    if len(parts) == 2:
                        p1, p2 = parts[0], parts[1]
                        vokabeln = [
                            v for v in vokabeln
                            if (p1 in v.front.lower() and p2 in v.back.lower())
                            or (p2 in v.front.lower() and p1 in v.back.lower())
                        ]
                    else:
                        vokabeln = [
                            v for v in vokabeln
                            if any(p in v.front.lower() or p in v.back.lower() for p in parts)
                        ]
                else:
                    vokabeln = [
                        v for v in vokabeln
                        if query in v.front.lower()
                        or query in v.back.lower()
                        or query in v.kategorie.lower()
                        or query in v.lang_front.lower()
                        or query in v.lang_back.lower()
                    ]

            vokabeln_sorted = sorted(vokabeln, key=_sort_vokabel_key)
            self._current_vokabeln = vokabeln_sorted
            self._table.clearContents()
            self._table.setRowCount(len(vokabeln_sorted))

            if query:
                match_txt = f"{len(vokabeln_sorted)} von {total_pool_count} Vokabeln"
                self._count_lbl.setText(match_txt)
                self._count_lbl.setAccessibleName(f" {len(vokabeln_sorted)} von {total_pool_count} Vokabeln gefunden")
            else:
                total_txt = f"{total_pool_count} Vokabel{'n' if total_pool_count != 1 else ''}"
                self._count_lbl.setText(total_txt)
                self._count_lbl.setAccessibleName(f" {total_pool_count} Vokabeln in dieser Auswahl")

            self._update_undo_btn()

            for row, vok in enumerate(vokabeln_sorted):
                kat_info = self._trainer.get_kategorie_info(vok.kategorie)
                icon_str = kat_info.get("icon", "")
                lang_tag = f" [{vok.lang_front} → {vok.lang_back}]" if vok.kategorie == "Sprache" and vok.lang_front else ""
                vokabel_text = f"{icon_str}{lang_tag}  {vok.front}  →  {vok.back}"
                score_text = f"{vok.score:.0f} %"
                abgef_text = f"{vok.attempts}×"
                richtig_text = f"{vok.correct}×"

                items = [
                    QTableWidgetItem(str(row + 1)),
                    QTableWidgetItem(vokabel_text),
                    QTableWidgetItem(score_text),
                    QTableWidgetItem(abgef_text),
                    QTableWidgetItem(richtig_text),
                ]

                # AccessibleTextRole für Braillezeilen
                items[0].setData(Qt.ItemDataRole.AccessibleTextRole, f" {row + 1}")
                items[1].setData(Qt.ItemDataRole.AccessibleTextRole, f" {vok.front} = {vok.back}")
                items[2].setData(Qt.ItemDataRole.AccessibleTextRole, f" {vok.score:.0f}%")
                items[3].setData(Qt.ItemDataRole.AccessibleTextRole, f" {vok.attempts}x")
                items[4].setData(Qt.ItemDataRole.AccessibleTextRole, f" {vok.correct}x")

                if vok.attempts == 0:
                    items[2].setForeground(QColor("#555c75"))
                elif vok.score <= 50:
                    items[2].setForeground(QColor("#ff6b6b"))
                elif vok.score <= 75:
                    items[2].setForeground(QColor("#f0c040"))
                else:
                    items[2].setForeground(QColor("#69db7c"))

                for col, item in enumerate(items):
                    if col in (0, 2, 3, 4):
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self._table.setItem(row, col, item)
        finally:
            self._table.blockSignals(False)
            self._table.setUpdatesEnabled(True)

    def _edit_selected_from_table(self, row: int | None = None) -> None:
        """Öffnet den Bearbeiten-Dialog für die aktuell ausgewählte Vokabel."""
        if row is None or not isinstance(row, int) or row < 0:
            row = self._table.currentRow()
        if row < 0 or row >= len(self._current_vokabeln):
            return
        vok = self._current_vokabeln[row]
        dlg = EditVokabelDialog(vok, parent=self, trainer=self._trainer)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_list()

    def _hinzufuegen(self) -> None:
        try:
            canonical_lf, canonical_lb = self._trainer.get_most_used_lang_pair()
            dlg = AddVokabelDialog(
                self,
                trainer=self._trainer,
                lang_f=self._last_lang_f,
                lang_b=self._last_lang_b,
                canonical_lf=canonical_lf,
                canonical_lb=canonical_lb,
                initial_kat=self._filter_combo.currentData(),
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                front, back, kat, lf, lb = dlg.get_values()
                if front and back:
                    vok = self._trainer.add_vokabel(front, back, kat, lf, lb)
                    if vok is None:
                        sprache_hinweis = f" ({lf})" if kat == "Sprache" else ""
                        QMessageBox.warning(
                            self, "Duplikat",
                            f"Die Vokabel \u201e{front}\u201c existiert bereits in der Kategorie \u201e{kat}\u201c{sprache_hinweis} und wurde nicht doppelt angelegt.",
                        )
                    else:
                        if kat == "Sprache" and lf and lb:
                            self._last_lang_f = lf
                            self._last_lang_b = lb
                        self._update_search_completer()
                        self._load_list()
        except Exception as exc:
            logger.error("Fehler beim Hinzufügen: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Fehler", f"Vokabel konnte nicht gespeichert werden:\n{exc}")

    def _loeschen(self) -> None:
        try:
            kat: str | None = self._filter_combo.currentData()
            dlg = DeleteDialog(self._trainer, initial_kategorie=kat, parent=self)
            dlg.exec()
            self._update_search_completer()
            self._load_list()
        except Exception as exc:
            logger.error("Fehler beim Löschen: %s", exc, exc_info=True)
            QMessageBox.critical(self, "Fehler", f"Beim Löschen ist ein Fehler aufgetreten:\n{exc}")

    def _importieren(self) -> None:
        canonical_lf, canonical_lb = self._trainer.get_most_used_lang_pair()
        dlg = ImportDialog(
            self,
            trainer=self._trainer,
            lang_f=self._last_lang_f,
            lang_b=self._last_lang_b,
            canonical_lf=canonical_lf,
            canonical_lb=canonical_lb,
        )
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        ziel_kat, lang_f, lang_b = dlg.get_data()
        if ziel_kat == "Sprache" and lang_f and lang_b:
            self._last_lang_f = lang_f
            self._last_lang_b = lang_b

        start_dir = str(Path.home() / "Desktop")
        path, _ = QFileDialog.getOpenFileName(
            self, "Datei importieren", start_dir,
            "Dateien (*.docx *.txt);;Word (*.docx);;Text (*.txt)",
        )
        if not path:
            return

        try:
            neu, duplikate = import_datei(self._trainer, Path(path), ziel_kat, lang_f, lang_b)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Datei konnte nicht gelesen werden:\n{exc}")
            return

        self._update_search_completer()
        self._load_list()
        if neu == 0 and duplikate == 0:
            QMessageBox.warning(
                self, "Import fehlgeschlagen",
                "Keine gültigen Vokabelpaare gefunden.\n\n"
                "Format: Vorderseite | Rückseite  oder  Vorderseite - Rückseite",
            )
        else:
            lang_info = f" ({lang_f} → {lang_b})" if ziel_kat == "Sprache" else ""
            msg = f"{neu} neue Vokabel(n) als \u201e{ziel_kat}\u201c{lang_info} importiert."
            if duplikate > 0:
                msg += f"\n({duplikate} doppelte Vokabeln wurden automatisch übersprungen)"
            QMessageBox.information(self, "Import erfolgreich", msg)
