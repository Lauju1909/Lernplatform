# frontend.py – VokabelMeister Frontend (PyQt6 UI, Barrierefreiheit, Views, Styling)
from __future__ import annotations

import random
import time
from functools import partial
from pathlib import Path
from typing import Callable
import dialogs
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFrame,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QComboBox, QDialog, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QKeyEvent, QFocusEvent
from backend import Vokabel, VokabelTrainer, import_datei, check_answer

# ── Stylesheet ─────────────────────────────────────────────────────────────────
STYLE = """
QWidget { background-color: #0f1117; color: #e8eaf0; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
QWidget#sidebar { background-color: #13151f; border-right: 1px solid #1e2130; }
QPushButton#navBtn { background-color: transparent; color: #8b90a8; border: none; border-radius: 10px; padding: 12px 16px; text-align: left; font-size: 14px; }
QPushButton#navBtn:hover { background-color: #1e2130; color: #e8eaf0; }
QPushButton#navBtn[active="true"] { background-color: #1e2444; color: #7986e0; font-weight: 600; }
QFrame#abfrageCard { background-color: #141724; border: 1px solid #23273c; border-radius: 16px; }
QLabel#questionLabel { color: #ffffff; font-size: 30px; font-weight: 700; line-height: 1.45; }
QLabel#feedbackLabel { font-size: 24px; font-weight: 700; min-height: 42px; }
QLabel#motivLabel { font-size: 18px; font-weight: 600; }
QLabel#statsLabel { color: #8b90a8; font-size: 16px; font-weight: 600; }
QLabel#catBadge { color: #7986e0; font-size: 16px; font-weight: 700; letter-spacing: 0.5px; }
QLabel#enterHint { color: #9aa0bc; font-size: 20px; font-weight: 600; }
QFrame#katCard { background-color: #1a1d27; border: 1px solid #232639; border-radius: 14px; }
QFrame#katCard:hover { border: 1px solid #5c6bc0; }
QLabel#katIcon { font-size: 32px; }
QLabel#katName { color: #ffffff; font-size: 16px; font-weight: 700; }
QLabel#katDesc { color: #8b90a8; font-size: 12px; }
QLabel#katCount { color: #7986e0; font-size: 12px; font-weight: 600; }
QPushButton#katBtn { background-color: #1e2444; color: #7986e0; border: 1px solid #2e3360; border-radius: 10px; padding: 10px 20px; font-size: 13px; font-weight: 600; }
QPushButton#katBtn:hover { background-color: #252d5a; color: #8b96e0; }
QPushButton#katBtn:focus { border: 2px solid #5c6bc0; }
QLineEdit { background-color: #1e2130; color: #ffffff; border: 2px solid #2e3148; border-radius: 10px; padding: 14px 18px; font-size: 20px; selection-background-color: #5c6bc0; }
QLineEdit:focus { border: 2px solid #5c6bc0; }
QPushButton#primaryBtn { background-color: #5c6bc0; color: #ffffff; border: none; border-radius: 10px; padding: 13px 32px; font-size: 14px; font-weight: 600; }
QPushButton#primaryBtn:hover { background-color: #6979d4; }
QPushButton#primaryBtn:pressed { background-color: #4a59b0; }
QPushButton#primaryBtn:focus { border: 3px solid #8b96e0; }
QPushButton#primaryBtn:disabled { background-color: #2e3148; color: #4a4f6a; }
QPushButton#secondaryBtn { background-color: transparent; color: #8b90a8; border: 1px solid #2e3148; border-radius: 10px; padding: 10px 20px; font-size: 14px; }
QPushButton#secondaryBtn:hover { background-color: #1e2130; color: #e8eaf0; }
QPushButton#secondaryBtn:focus { border: 1px solid #5c6bc0; color: #e8eaf0; }
QPushButton#dangerBtn { background-color: transparent; color: #e05c5c; border: 1px solid #5a2020; border-radius: 10px; padding: 10px 20px; font-size: 14px; }
QPushButton#dangerBtn:hover { background-color: #2a1515; }
QListWidget { background-color: #13151f; border: 1px solid #1e2130; border-radius: 10px; padding: 4px; color: #e8eaf0; font-size: 13px; }
QListWidget::item { padding: 10px 12px; border-radius: 8px; }
QListWidget::item:selected { background-color: #1e2444; color: #7986e0; }
QListWidget::item:hover { background-color: #1e2130; }
QComboBox { background-color: #1e2130; color: #e8eaf0; border: 2px solid #2e3148; border-radius: 10px; padding: 10px 14px; font-size: 14px; }
QComboBox:focus { border: 2px solid #5c6bc0; }
QComboBox::drop-down { border: none; padding-right: 10px; }
QComboBox QAbstractItemView { background-color: #1a1d27; color: #e8eaf0; border: 1px solid #2e3148; selection-background-color: #2e3360; padding: 4px; }
QLabel#sectionLabel { color: #8b90a8; font-size: 11px; font-weight: 700; letter-spacing: 1.2px; }
QCheckBox { color: #8b90a8; font-size: 13px; spacing: 8px; }
QCheckBox:checked { color: #7986e0; font-weight: 600; }
QDialog { background-color: #0f1117; }
QMessageBox { background-color: #0f1117; }
"""


def _motivation(score: float) -> tuple[str, str]:
    if score < 20: return "Kopf hoch – du schaffst das! 💪", "#e05c5c"
    if score < 40: return "Nicht aufgeben, weiter üben! 📖", "#f0a500"
    if score < 60: return "Du wirst besser, bleib dran! 🙂", "#f0a500"
    if score < 80: return "Gut gemacht, weiter so! 👍", "#4caf7d"
    if score < 95: return "Super – fast perfekt! ⭐", "#4caf7d"
    return "Ausgezeichnet – mach weiter so! 🏆", "#7986e0"

def _sort_vokabel_key(v: Vokabel) -> tuple[float, int]:
    """Sortierschlüssel für Vokabeln: bester Score zuerst, bei gleichem Score nach Abfragen."""
    return (-v.score, v.attempts if v.score == 0 else -v.attempts)

# ── Barrierefreies Eingabefeld (liest stets die aktuelle Frage bzw. Rückmeldung vor)
class AccessibleQuestionInput(QLineEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_speech: str = ""
        self.setPlaceholderText("Antwort eingeben …")

    def set_question(self, question: str) -> None:
        self._current_speech = question.strip()
        self.setAccessibleName(f" {self._current_speech}")

    def set_feedback_speech(self, speech: str) -> None:
        self._current_speech = speech.strip()
        self.setAccessibleName(f" {self._current_speech}")

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            super().keyPressEvent(a0)
            return
        if a0.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            a0.accept()
            self.returnPressed.emit()
            return
        super().keyPressEvent(a0)


# ══════════════════════════════════════════════════════════════════════════════
# Abfrage-View (Karten-Layout, direkte Enter-Bedienung, ohne Fortschrittsbalken)
# ══════════════════════════════════════════════════════════════════════════════
class AbfrageView(QWidget):
    def __init__(self, trainer: VokabelTrainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._aktuelle: Vokabel | None = None
        self._kategorien: list[str] | None = None
        self._wiederholen: bool = False
        self._consecutive_card_count: int = 0
        self._last_card: Vokabel | None = None
        self._reverse: bool = False
        self._consecutive_dir_count: int = 0
        self._expected: str = ""
        self._session_total = 0
        self._session_richtig = 0
        self._waiting_for_next: bool = False
        self._last_eval_time: float = 0.0
        self._advance_timer = QTimer(self)
        self._advance_timer.setSingleShot(True)
        self._advance_timer.timeout.connect(self._lade_karte)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 22, 32, 22)
        root.setSpacing(14)

        # 1. Header-Zeile (Kategorie-Badge links, Statistik rechts)
        header_row = QHBoxLayout()
        self._cat_badge = QLabel("")
        self._cat_badge.setObjectName("catBadge")
        self._cat_badge.setAccessibleName(" Aktive Kategorie")
        header_row.addWidget(self._cat_badge)

        header_row.addStretch()

        self._stats_lbl = QLabel("0 richtig  |  0 falsch")
        self._stats_lbl.setObjectName("statsLabel")
        self._stats_lbl.setAccessibleName(" Statistik: 0 richtig, 0 falsch")
        header_row.addWidget(self._stats_lbl)
        root.addLayout(header_row)

        # 2. Haupt-Karten-Container (füllt den Raum harmonisch aus)
        self._card_frame = QFrame()
        self._card_frame.setObjectName("abfrageCard")
        card_layout = QVBoxLayout(self._card_frame)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(0)

        # Vollständig integrierte Frage im natürlichen Satzbau
        self._question_lbl = QLabel("")
        self._question_lbl.setObjectName("questionLabel")
        self._question_lbl.setWordWrap(True)
        self._question_lbl.setAccessibleName(" ")
        card_layout.addWidget(self._question_lbl)
        card_layout.addSpacing(32)

        # Eingabefeld – breiter, größere Schrift, liest bei Fokuswechsel stets aktuellen Inhalt vor
        self._input = AccessibleQuestionInput()
        self._input.returnPressed.connect(self._aktion)
        card_layout.addWidget(self._input)
        card_layout.addSpacing(50)

        # Tastatur-Hinweis (50px direkt unter dem Eingabefeld)
        self._hint_lbl = QLabel("💡 Drücke Enter zum Bestätigen und Weitergehen")
        self._hint_lbl.setObjectName("enterHint")
        self._hint_lbl.setAccessibleName(" ")
        card_layout.addWidget(self._hint_lbl)
        card_layout.addSpacing(22)

        # Feedback-Label (erscheint visuell nach Auswertung)
        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setObjectName("feedbackLabel")
        self._feedback_lbl.setWordWrap(True)
        self._feedback_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._feedback_lbl.setAccessibleName(" ")
        self._feedback_lbl.hide()
        card_layout.addWidget(self._feedback_lbl)
        card_layout.addSpacing(14)

        # Motivationsspruch (visuell)
        self._motiv_lbl = QLabel("")
        self._motiv_lbl.setObjectName("motivLabel")
        self._motiv_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._motiv_lbl.setAccessibleName(" ")
        self._motiv_lbl.hide()
        card_layout.addWidget(self._motiv_lbl)

        card_layout.addStretch(1)

        root.addWidget(self._card_frame, stretch=1)

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if a0 is None:
            super().keyPressEvent(a0)
            return
        if not self._trainer.get_pool(self._kategorien):
            super().keyPressEvent(a0)
            return
        if a0.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._waiting_for_next and (time.time() - self._last_eval_time > 0.3):
                self._advance_timer.stop()
                self._lade_karte()
                a0.accept()
                return
            elif not self._waiting_for_next:
                self._input.setFocus()
                a0.accept()
                return
        elif not self._waiting_for_next and not self._input.hasFocus():
            self._input.setFocus()
        super().keyPressEvent(a0)

    def set_kategorien(self, kategorien: list[str] | set[str] | str | None) -> None:
        self._advance_timer.stop()
        self._waiting_for_next = False
        if isinstance(kategorien, str): self._kategorien = [kategorien]
        elif isinstance(kategorien, (list, set)): self._kategorien = list(kategorien)
        else: self._kategorien = None
        self._aktuelle = None
        self._wiederholen = False
        self._consecutive_card_count = 0
        self._last_card = None
        self._reverse = False
        self._consecutive_dir_count = 0
        self._expected = ""
        self._session_total = 0
        self._session_richtig = 0
        self._stats_lbl.setText("0 richtig  |  0 falsch")
        self._stats_lbl.setAccessibleName(" Statistik: 0 richtig, 0 falsch")

        def get_info(name: str) -> dict[str, str]:
            resolver = getattr(self._trainer, "get_kategorie_info", None)
            if callable(resolver):
                info = resolver(name)
                if isinstance(info, dict):
                    return info
            return {
                "icon": "🏷️",
                "beschreibung": "",
                "frage_front": "Was bedeutet:",
                "frage_back": "Welcher Begriff beschreibt folgendes:",
                "lbl_front": "Vorderseite",
                "lbl_back": "Rückseite",
            }

        if self._kategorien and len(self._kategorien) == 1:
            kat = self._kategorien[0]
            info = get_info(kat)
            self._cat_badge.setText(f"{info.get('icon', '🏷️')}  {kat}  –  {info.get('beschreibung', '')}")
            self._cat_badge.setAccessibleName(f" Aktive Kategorie: {kat}")
        elif self._kategorien and len(self._kategorien) > 1:
            icons_str = "  ".join(get_info(k).get("icon", "🏷️") + " " + k for k in self._kategorien)
            self._cat_badge.setText(f"🗂  {len(self._kategorien)} Kategorien: {icons_str}")
            self._cat_badge.setAccessibleName(f" {len(self._kategorien)} Kategorien aktiv: {', '.join(self._kategorien)}")
        else:
            self._cat_badge.setText("Alle Kategorien")
            self._cat_badge.setAccessibleName(" Alle Kategorien aktiv")

    def set_kategorie(self, kategorie: str | None) -> None:
        self.set_kategorien(kategorie)

    def refresh(self) -> None:
        pool = self._trainer.get_pool(self._kategorien)
        if not pool:
            msg = "Keine Vokabeln vorhanden. Bitte zuerst im Bereich Vokabelverwaltung Vokabeln hinzufügen."
            self._question_lbl.setText("📭  Keine Vokabeln vorhanden")
            self._question_lbl.setAccessibleName(f" {msg}")
            self._question_lbl.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._question_lbl.setFocus()
            self._input.setEnabled(False)
            self._input.clear()
            self._feedback_lbl.hide()
            self._motiv_lbl.hide()
            self._hint_lbl.hide()
            return
        self._question_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._question_lbl.setAccessibleName(" ")
        self._input.setEnabled(True)
        self._hint_lbl.show()
        if self._aktuelle is None:
            self._lade_karte()

    def _build_integrated_question(self, vok: Vokabel, reverse: bool, kat_info: dict[str, str]) -> str:
        if vok.kategorie == "Sprache":
            lf = vok.lang_front.strip() or "Englisch"
            lb = vok.lang_back.strip() or "Deutsch"
            if reverse:
                return f"Wie lautet die Übersetzung von „{vok.back}“ auf {lf}?"
            return f"Wie lautet die Übersetzung von „{vok.front}“ auf {lb}?"

        if vok.kategorie == "Befehle":
            if reverse:
                return f"Welches Tastenkürzel bewirkt: „{vok.back}“?"
            return f"Was macht das Tastenkürzel „{vok.front}“?"

        if vok.kategorie == "Fachwörter":
            if reverse:
                return f"Welcher Begriff beschreibt: „{vok.back}“?"
            return f"Was bedeutet der Fachbegriff „{vok.front}“?"

        if vok.kategorie == "Formeln":
            if reverse:
                return f"Wie lautet die Formel für: „{vok.back}“?"
            return f"Was bedeutet die Formel „{vok.front}“?"

        if reverse:
            raw_q = kat_info.get("frage_back", "Welcher Begriff beschreibt:").strip().rstrip(":?")
            return f"{raw_q}: „{vok.back}“?"
        raw_q = kat_info.get("frage_front", "Was bedeutet:").strip().rstrip(":?")
        return f"{raw_q} „{vok.front}“?"

    def _lade_karte(self) -> None:
        self._advance_timer.stop()
        self._waiting_for_next = False

        if not self._wiederholen:
            exclude = self._last_card if self._consecutive_card_count >= 2 else None
            try:
                self._aktuelle = self._trainer.get_next_card(self._kategorien, exclude=exclude)
            except ValueError:
                self._aktuelle = None
                self.refresh()
                return

            if self._aktuelle is self._last_card:
                self._consecutive_card_count += 1
            else:
                self._consecutive_card_count = 1
                self._last_card = self._aktuelle

            if self._consecutive_dir_count >= 5:
                neue_richtung = not self._reverse
            else:
                neue_richtung = random.choice([False, True])

            if neue_richtung == self._reverse:
                self._consecutive_dir_count += 1
            else:
                self._reverse = neue_richtung
                self._consecutive_dir_count = 1

        self._wiederholen = False
        vok = self._aktuelle
        if vok is None:
            self.refresh()
            return

        kat_info = self._trainer.get_kategorie_info(vok.kategorie)
        self._expected = vok.front if self._reverse else vok.back
        full_question = self._build_integrated_question(vok, self._reverse, kat_info)

        self._question_lbl.setText(full_question)
        self._question_lbl.setAccessibleName(" ")

        self._input.setReadOnly(False)
        self._input.clear()
        self._input.setEnabled(True)
        self._input.set_question(full_question)
        self._feedback_lbl.setText("")
        self._feedback_lbl.setAccessibleName(" ")
        self._feedback_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._feedback_lbl.hide()
        self._motiv_lbl.setText("")
        self._motiv_lbl.setAccessibleName(" ")
        self._motiv_lbl.hide()
        self._hint_lbl.show()
        self._input.setFocus()

    def _aktion(self) -> None:
        if self._waiting_for_next:
            if time.time() - self._last_eval_time > 0.3:
                self._advance_timer.stop()
                self._lade_karte()
        else:
            self._auswerten()

    def _auswerten(self) -> None:
        text = self._input.text().strip()
        if not text:
            self._set_feedback("⚠  Bitte eine Antwort eingeben.", "#f0a500", "Bitte eine Antwort eingeben.")
            return
        vok = self._aktuelle
        if vok is None:
            return

        richtig, is_fuzzy = check_answer(text, self._expected)
        self._trainer.record_result(vok, richtig)
        self._session_total += 1
        if richtig:
            self._session_richtig += 1
        self._update_stats()

        self._last_eval_time = time.time()
        self._waiting_for_next = True
        self._input.setReadOnly(True)

        spruch, farbe = _motivation(vok.score)
        self._motiv_lbl.setText(spruch)
        self._motiv_lbl.setStyleSheet(f"color: {farbe}; font-size: 18px; font-weight: 600;")
        self._motiv_lbl.show()

        if richtig:
            vis_text = f"✓  Richtig! (Volle Lösung: {self._expected})" if is_fuzzy else "✓  Richtig!"
            audio_text = f"Richtig. {spruch}"
            self._set_feedback(vis_text, "#4caf7d", audio_text)
            total_wait_ms = 6000
            self._wiederholen = False
        else:
            buchstabiert = " - ".join(list(self._expected))
            vis_text = f"✗  Falsch.  Richtig: {self._expected}"
            audio_text = f"Falsch. {self._expected}. {buchstabiert}. {spruch}"
            self._set_feedback(vis_text, "#e05c5c", audio_text)
            buchstabier_zeit_ms = max(2500, len(self._expected) * 500)
            total_wait_ms = buchstabier_zeit_ms + 6000
            self._wiederholen = True

        self._advance_timer.start(total_wait_ms)

    def _update_stats(self) -> None:
        falsch = self._session_total - self._session_richtig
        self._stats_lbl.setText(f"{self._session_richtig} richtig  |  {falsch} falsch")
        self._stats_lbl.setAccessibleName(
            f" Statistik: {self._session_richtig} richtig, {falsch} falsch"
        )

    def _set_feedback(self, text: str, farbe: str, audio_text: str | None = None) -> None:
        self._feedback_lbl.setText(text)
        self._feedback_lbl.setStyleSheet(f"color: {farbe}; font-size: 24px; font-weight: 700;")
        speech = audio_text if audio_text is not None else text
        self._feedback_lbl.setAccessibleName(f" {speech}")
        self._feedback_lbl.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._feedback_lbl.show()
        self._motiv_lbl.setAccessibleName(" ")
        self._feedback_lbl.setFocus()


# ══════════════════════════════════════════════════════════════════════════════
# Kategorien-View (Karten-Liste & Eigene Kategorien)
# ══════════════════════════════════════════════════════════════════════════════
class KategorienView(QWidget):
    def __init__(
        self,
        trainer: VokabelTrainer,
        on_start: Callable[[str | list[str] | set[str] | None], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._on_start = on_start
        self._count_labels: dict[str, QLabel] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(36, 28, 36, 28)
        root.setSpacing(14)

        # Header Zeile
        title_box = QVBoxLayout()
        title = QLabel("Kategorien")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAccessibleName(" Kategorien")
        sub = QLabel("Wähle eine Kategorie um die Abfrage zu starten oder erstelle neue Kategorien.")
        sub.setObjectName("statsLabel")
        sub.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(sub)
        root.addLayout(title_box)

        # Scrollbereich für Kachelkarten
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._cards_container = QWidget()
        self._cards_layout = QGridLayout(self._cards_container)
        self._cards_layout.setSpacing(14)
        self._cards_layout.setContentsMargins(0, 4, 0, 4)
        scroll.setWidget(self._cards_container)
        root.addWidget(scroll, stretch=1)

        # Button alle Kategorien lernen / auswählen (links) & Kategorie entfernen (rechts)
        action_row = QHBoxLayout()
        alle_btn = QPushButton("🗂  Alle Kategorien / Auswählen …")
        alle_btn.setObjectName("primaryBtn")
        alle_btn.setAccessibleName(" Kategorien zum Lernen auswählen")
        alle_btn.clicked.connect(self._auswahl_dialog)
        action_row.addWidget(alle_btn)

        action_row.addStretch()

        del_kat_btn = QPushButton("🗑  Kategorie entfernen …")
        del_kat_btn.setObjectName("dangerBtn")
        del_kat_btn.setAccessibleName(" Kategorie entfernen")
        del_kat_btn.clicked.connect(self._delete_kategorie_dialog)
        action_row.addWidget(del_kat_btn)

        root.addLayout(action_row)

        self._rebuild_cards()

    def _rebuild_cards(self) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()
        self._count_labels.clear()

        kats = self._trainer.get_kategorien()
        row, col = 0, 0
        cols_count = 2
        for kat_name, info in kats.items():
            card = self._make_card(kat_name, info)
            self._cards_layout.addWidget(card, row, col)
            col += 1
            if col >= cols_count:
                col = 0
                row += 1

        # Karte "Kategorie hinzufügen" im selben Format als letztes Element
        add_card = self._make_add_card()
        self._cards_layout.addWidget(add_card, row, col)

    def _make_card(self, kat_name: str, info: dict[str, str]) -> QFrame:
        frame = QFrame()
        frame.setObjectName("katCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        icon_lbl = QLabel(info.get("icon", "🏷️"))
        icon_lbl.setObjectName("katIcon")
        icon_lbl.setAccessibleName("")

        name_lbl = QLabel(kat_name)
        name_lbl.setObjectName("katName")
        name_lbl.setAccessibleName(f" Kategorie: {kat_name}")

        desc_lbl = QLabel(info.get("beschreibung", ""))
        desc_lbl.setObjectName("katDesc")
        desc_lbl.setWordWrap(True)

        count_lbl = QLabel("0 Vokabeln")
        count_lbl.setObjectName("katCount")
        self._count_labels[kat_name] = count_lbl

        start_btn = QPushButton(f"▶  {kat_name} lernen")
        start_btn.setObjectName("katBtn")
        start_btn.setAccessibleName(f" {kat_name} lernen")
        start_btn.clicked.connect(partial(self._on_start, kat_name))

        for w in [icon_lbl, name_lbl, desc_lbl, count_lbl]:
            layout.addWidget(w)
        layout.addSpacing(4)
        layout.addWidget(start_btn)
        return frame

    def _make_add_card(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("katCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        icon_lbl = QLabel("➕")
        icon_lbl.setObjectName("katIcon")
        icon_lbl.setAccessibleName("")

        name_lbl = QLabel("Kategorie hinzufügen")
        name_lbl.setObjectName("katName")
        name_lbl.setAccessibleName(" Kategorie hinzufügen")

        desc_lbl = QLabel("Eigene Lernkategorie mit individuellen Abfrage-Feldern erstellen.")
        desc_lbl.setObjectName("katDesc")
        desc_lbl.setWordWrap(True)

        count_lbl = QLabel("Benutzerdefiniert")
        count_lbl.setObjectName("katCount")

        add_btn = QPushButton("＋  Kategorie anlegen")
        add_btn.setObjectName("katBtn")
        add_btn.setAccessibleName(" Neue Kategorie anlegen")
        add_btn.clicked.connect(self._add_kategorie)

        for w in [icon_lbl, name_lbl, desc_lbl, count_lbl]:
            layout.addWidget(w)
        layout.addSpacing(4)
        layout.addWidget(add_btn)
        return frame

    def _auswahl_dialog(self) -> None:
        dlg = dialogs.SelectKategorienDialog(self._trainer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected_kategorien()
            if selected:
                all_kats = list(self._trainer.get_kategorien().keys())
                self._on_start(None if len(selected) == len(all_kats) else selected)

    def _add_kategorie(self) -> None:
        dlg = dialogs.AddKategorieDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if self._trainer.add_kategorie(d["name"], d["icon"], d["beschreibung"], d["frage_front"], d["frage_back"], d["lbl_front"], d["lbl_back"]):
                self._rebuild_cards()
                self.refresh()
            else:
                QMessageBox.warning(self, "Kategorie existiert bereits", f"Die Kategorie \u201e{d['name']}\u201c existiert bereits.")

    def _delete_kategorie_dialog(self) -> None:
        dlg = dialogs.DeleteKategorieDialog(self._trainer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._rebuild_cards()
            self.refresh()

    def refresh(self) -> None:
        kats = self._trainer.get_kategorien()
        if len(kats) != len(self._count_labels):
            self._rebuild_cards()
        for kat_name, lbl in self._count_labels.items():
            n = len(self._trainer.get_pool(kat_name))
            lbl.setText(f"{n} Vokabel{'n' if n != 1 else ''}")
            lbl.setAccessibleName(f" {n} Vokabeln in dieser Kategorie")


# ── Barrierefreie & tastaturnavigierbare Tabelle ──────────────────────────────
class NavigableTableWidget(QTableWidget):
    """
    Tabelle, die sich vollständig mit den Pfeiltasten bedienen lässt
    und mit Tab / Umschalt+Tab sauber zum nächsten/vorherigen Element verlassen wird.
    """
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setTabKeyNavigation(False)

    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        if e is None:
            return
        if e.key() == Qt.Key.Key_Tab:
            self.focusNextChild()
            e.accept()
            return
        if e.key() == Qt.Key.Key_Backtab:
            self.focusPreviousChild()
            e.accept()
            return
        super().keyPressEvent(e)

    def focusInEvent(self, e: QFocusEvent | None) -> None:
        super().focusInEvent(e)
        if self.rowCount() > 0 and self.currentRow() < 0:
            self.setCurrentCell(0, 1)


# ══════════════════════════════════════════════════════════════════════════════
# Vokabelverwaltung-View (Hauptansicht)
# ══════════════════════════════════════════════════════════════════════════════
class VerwaltungView(QWidget):
    def __init__(self, trainer: VokabelTrainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._last_lang_f = "Englisch"
        self._last_lang_b = "Deutsch"
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 32, 32, 32)
        root.setSpacing(16)

        title = QLabel("Vokabelverwaltung")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAccessibleName(" Vokabelverwaltung")
        root.addWidget(title)

        # ── Filter-Zeile ──────────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_lbl = QLabel("KATEGORIE")
        filter_lbl.setObjectName("sectionLabel")
        self._filter_combo = QComboBox()
        self._filter_combo.setAccessibleName(" Kategorie filtern")
        self._filter_combo.currentIndexChanged.connect(self._load_list)
        filter_lbl.setBuddy(self._filter_combo)
        filter_row.addWidget(filter_lbl)
        filter_row.addWidget(self._filter_combo)
        filter_row.addStretch()
        root.addLayout(filter_row)
        self._update_filter_combo()

        # ── Statistik-Tabelle (5 Spalten) ─────────────────────────────────────
        self._table = NavigableTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["#", "Vokabel", "Score", "Abgefragt", "Richtig"])
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        vertical_header = self._table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
        self._table.setShowGrid(False)
        hdr = self._table.horizontalHeader()
        if hdr is not None:
            hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setStyleSheet("""
            QTableWidget { background: #161922; alternate-background-color: #1c2030; border: 1px solid #2a2d3e; border-radius: 6px; gridline-color: transparent; outline: none; }
            QTableWidget:focus { border: 1px solid #7986e0; }
            QTableWidget::item { padding: 6px 10px; color: #e8eaf0; }
            QTableWidget::item:selected { background: #2e3460; color: #ffffff; }
            QHeaderView::section { background: #1e2235; color: #9095b0; font-size: 11px; font-weight: bold; letter-spacing: 1px; padding: 6px 10px; border: none; border-bottom: 1px solid #2a2d3e; }
        """)
        self._table.setAccessibleName(" Vokabel-Tabelle")
        root.addWidget(self._table, stretch=1)

        # ── Aktions-Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        add_btn = QPushButton("＋  Hinzufügen")
        add_btn.setObjectName("primaryBtn")
        add_btn.setAccessibleName(" Hinzufügen")
        add_btn.clicked.connect(self._hinzufuegen)

        del_btn = QPushButton("🗑  Löschen …")
        del_btn.setObjectName("dangerBtn")
        del_btn.setAccessibleName(" Löschen")
        del_btn.clicked.connect(self._loeschen)

        import_btn = QPushButton("📂  Datei importieren")
        import_btn.setObjectName("secondaryBtn")
        import_btn.setAccessibleName(" Importieren")
        import_btn.clicked.connect(self._importieren)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btn_row.addWidget(import_btn)
        root.addLayout(btn_row)

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

    def refresh(self) -> None:
        self._update_filter_combo()
        self._load_list()

    def _load_list(self) -> None:
        kat: str | None = self._filter_combo.currentData()
        vokabeln: list[Vokabel] = self._trainer.get_pool(kat)
        vokabeln_sorted = sorted(vokabeln, key=_sort_vokabel_key)
        self._table.setRowCount(len(vokabeln_sorted))

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

            # ── Saubere Braillezeilen-Ausgabe (AccessibleTextRole ohne Emojis & Ballast) ──
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
                item.setData(Qt.ItemDataRole.UserRole, vok)
                if col in (0, 2, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)

    def _hinzufuegen(self) -> None:
        canonical_lf, canonical_lb = self._trainer.get_most_used_lang_pair()
        dlg = dialogs.AddVokabelDialog(
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
                    self._load_list()

    def _loeschen(self) -> None:
        kat: str | None = self._filter_combo.currentData()
        dlg = dialogs.DeleteDialog(self._trainer, initial_kategorie=kat, parent=self)
        dlg.exec()
        self._load_list()

    def _importieren(self) -> None:
        canonical_lf, canonical_lb = self._trainer.get_most_used_lang_pair()
        dlg = dialogs.ImportDialog(
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
            self, "Datei öffnen", start_dir,
            "Dateien (*.docx *.txt);;Word (*.docx);;Text (*.txt)",
        )
        if not path:
            return

        try:
            neu, duplikate = import_datei(self._trainer, Path(path), ziel_kat, lang_f, lang_b)
        except Exception as exc:
            QMessageBox.critical(self, "Fehler", f"Datei konnte nicht gelesen werden:\n{exc}")
            return

        self._load_list()
        if neu == 0 and duplikate == 0:
            QMessageBox.warning(
                self, "Import fehlgeschlagen",
                "Keine gültigen Vokabelpaare gefunden.\n\n"
                "Format: Vorderseite | Rückseite  oder  Vorderseite - Rückseite",
            )
        else:
            lang_info = f" ({lang_f} → {lang_b})" if ziel_kat == "Sprache" else ""
            msg = f"{neu} neue Vokabel(n) als „{ziel_kat}“{lang_info} importiert."
            if duplikate > 0:
                msg += f"\n({duplikate} doppelte Vokabeln wurden automatisch übersprungen)"
            QMessageBox.information(self, "Import erfolgreich", msg)


# ══════════════════════════════════════════════════════════════════════════════
# Hauptfenster
# ══════════════════════════════════════════════════════════════════════════════
class MainWindow(QMainWindow):
    def __init__(self, trainer: VokabelTrainer) -> None:
        super().__init__()
        self._trainer = trainer
        self.setWindowTitle("VokabelMeister")
        self.setMinimumSize(960, 600)
        self.setAccessibleName(" VokabelMeister Hauptfenster")
        self._build_ui()
        self._navigate(1)  # Startet auf Kategorien

    def _build_ui(self) -> None:
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

        app_title = QLabel("VokabelMeister")
        app_title.setObjectName("appTitle")
        app_title.setAccessibleName(" VokabelMeister")
        sb_layout.addWidget(app_title)

        nav_items = [
            ("▶  Abfrage",           " Abfrage"),
            ("📂  Kategorien",        " Kategorien"),
            ("📋  Vokabelverwaltung", " Vokabelverwaltung"),
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

        self._views: list[QWidget] = [
            self._abfrage_view,
            self._kategorien_view,
            self._verwaltung_view,
        ]

        root_layout.addWidget(self._stack, stretch=1)

    def _navigate(self, index: int) -> None:
        # Bei Wechsel zur Abfrage-Ansicht: Vokabeln neu laden damit Änderungen sofort sichtbar sind
        if index == 0:
            from backend import load_vokabeln
            self._trainer.vokabeln = load_vokabeln()
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
        # Kategorie(n) setzen und direkt zur Abfrage wechseln
        self._abfrage_view.set_kategorien(kategorie)
        self._navigate(0)
