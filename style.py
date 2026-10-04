# style.py – Lernplatform Stylesheet, UI-Hilfsfunktionen und barrierefreie Basis-Widgets
"""
Dieses Modul definiert das Designsystem der Lernplatform (Dark Theme mit
hohem Kontrast gemäß WCAG AA), berechnet visuelle und auditive Feedback-
Farbwerte für Screenreader und Braillezeilen und stellt barrierefreie
Qt-Eingabeelemente bereit.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFocusEvent, QFont, QKeyEvent
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QCheckBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QToolButton,
    QWidget,
)

if TYPE_CHECKING:
    from backend import Vokabel


# ── Globales QSS Stylesheet (Modernes Dark Theme, hohe Lesbarkeit) ───────────
STYLE = """
QWidget {
    background-color: #0f1117;
    color: #e8eaf0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}
QWidget#sidebar {
    background-color: #13151f;
    border-right: 1px solid #1e2130;
}
QLabel#appTitle {
    color: #ffffff;
    font-size: 20px;
    font-weight: 700;
    padding: 4px 6px 12px 6px;
    letter-spacing: 0.5px;
}
QPushButton#navBtn {
    background-color: transparent;
    color: #8b90a8;
    border: none;
    border-radius: 10px;
    padding: 12px 16px;
    text-align: left;
    font-size: 14px;
}
QPushButton#navBtn:hover {
    background-color: #1e2130;
    color: #e8eaf0;
}
QPushButton#navBtn[active="true"] {
    background-color: #1e2444;
    color: #7986e0;
    font-weight: 600;
}
QFrame#abfrageCard {
    background-color: #141724;
    border: 1px solid #23273c;
    border-radius: 16px;
}
QLabel#questionLabel {
    color: #ffffff;
    font-size: 30px;
    font-weight: 700;
    line-height: 1.45;
}
QLabel#feedbackLabel {
    font-size: 24px;
    font-weight: 700;
    min-height: 42px;
}
QLabel#motivLabel {
    font-size: 18px;
    font-weight: 600;
}
QLabel#statsLabel {
    color: #8b90a8;
    font-size: 16px;
    font-weight: 600;
}
QLabel#catBadge {
    color: #7986e0;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.5px;
}
QLabel#enterHint {
    color: #9aa0bc;
    font-size: 20px;
    font-weight: 600;
}
QFrame#katCard {
    background-color: #1a1d27;
    border: 1px solid #232639;
    border-radius: 14px;
}
QFrame#katCard:hover {
    border: 1px solid #5c6bc0;
}
QLabel#katIcon {
    font-size: 32px;
}
QLabel#katName {
    color: #ffffff;
    font-size: 16px;
    font-weight: 700;
}
QLabel#katDesc {
    color: #8b90a8;
    font-size: 12px;
}
QLabel#katCount {
    color: #7986e0;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#katBtn {
    background-color: #1e2444;
    color: #7986e0;
    border: 1px solid #2e3360;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#katBtn:hover {
    background-color: #252d5a;
    color: #8b96e0;
}
QPushButton#katBtn:focus {
    border: 2px solid #5c6bc0;
}
QLineEdit {
    background-color: #1e2130;
    color: #ffffff;
    border: 2px solid #2e3148;
    border-radius: 10px;
    padding: 14px 18px;
    font-size: 20px;
    selection-background-color: #5c6bc0;
}
QLineEdit:focus {
    border: 2px solid #5c6bc0;
}
QPushButton#primaryBtn {
    background-color: #5c6bc0;
    color: #ffffff;
    border: none;
    border-radius: 10px;
    padding: 13px 32px;
    font-size: 14px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #6979d4;
}
QPushButton#primaryBtn:pressed {
    background-color: #4a59b0;
}
QPushButton#primaryBtn:focus {
    border: 3px solid #8b96e0;
}
QPushButton#primaryBtn:disabled {
    background-color: #2e3148;
    color: #4a4f6a;
}
QPushButton#secondaryBtn {
    background-color: transparent;
    color: #8b90a8;
    border: 1px solid #2e3148;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 14px;
}
QPushButton#secondaryBtn:hover {
    background-color: #1e2130;
    color: #e8eaf0;
}
QPushButton#secondaryBtn:focus {
    border: 1px solid #5c6bc0;
    color: #e8eaf0;
}
QPushButton#dangerBtn {
    background-color: transparent;
    color: #e05c5c;
    border: 1px solid #5a2020;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 14px;
}
QPushButton#dangerBtn:hover {
    background-color: #2a1515;
}
QListWidget {
    background-color: #13151f;
    border: 1px solid #1e2130;
    border-radius: 10px;
    padding: 4px;
    color: #e8eaf0;
    font-size: 13px;
}
QListWidget::item {
    padding: 10px 12px;
    border-radius: 8px;
}
QListWidget::item:selected {
    background-color: #1e2444;
    color: #7986e0;
}
QListWidget::item:hover {
    background-color: #1e2130;
}
QComboBox {
    background-color: #1e2130;
    color: #e8eaf0;
    border: 2px solid #2e3148;
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 14px;
}
QComboBox:focus {
    border: 2px solid #5c6bc0;
}
QComboBox::drop-down {
    border: none;
    padding-right: 10px;
}
QComboBox QAbstractItemView {
    background-color: #1a1d27;
    color: #e8eaf0;
    border: 1px solid #2e3148;
    selection-background-color: #2e3360;
    padding: 4px;
}
QSpinBox {
    background-color: #1e2130;
    color: #e8eaf0;
    border: 2px solid #2e3148;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 14px;
}
QSpinBox:focus {
    border: 2px solid #7986e0;
}
QSpinBox::up-button, QSpinBox::down-button {
    background-color: #262a3d;
    border: none;
    border-radius: 4px;
    width: 24px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #3b4260;
}
QLabel#sectionLabel {
    color: #8b90a8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1.2px;
}
QCheckBox {
    color: #8b90a8;
    font-size: 13px;
    spacing: 8px;
}
QCheckBox:checked {
    color: #7986e0;
    font-weight: 600;
}
QDialog {
    background-color: #0f1117;
}
QMessageBox {
    background-color: #0f1117;
}
QScrollBar:vertical {
    background: #1a1d27;
    width: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #3e4260;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #5c6bc0;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #1a1d27;
    height: 8px;
    border-radius: 4px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #3e4260;
    border-radius: 4px;
    min-width: 20px;
}
QScrollBar::handle:horizontal:hover {
    background: #5c6bc0;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


# ── Motivations- und Bewertungshilfen ──────────────────────────────────────────
def _motivation(score: float) -> tuple[str, str]:
    """Liefert einen aufmunternden Spruch und die passende Hex-Farbe zum Score."""
    if score < 20:
        return "Kopf hoch – du schaffst das! 💪", "#e05c5c"
    if score < 40:
        return "Nicht aufgeben, weiter üben! 📖", "#f0a500"
    if score < 60:
        return "Du wirst besser, bleib dran! 🙂", "#f0a500"
    if score < 80:
        return "Gut gemacht, weiter so! 👍", "#4caf7d"
    if score < 95:
        return "Super – fast perfekt! ⭐", "#4caf7d"
    return "Ausgezeichnet – mach weiter so! 🏆", "#7986e0"


def get_score_color(score: float, attempts: int = 1) -> QColor:
    """Gibt eine semantische QColor passend zum Lernfortschritt zurück."""
    if attempts == 0:
        return QColor("#555c75")  # Noch unberührt / grau
    if score <= 50:
        return QColor("#ff6b6b")  # Rot / Übungsbedarf
    if score <= 75:
        return QColor("#f0c040")  # Gelb / Solide
    return QColor("#69db7c")      # Grün / Gemeistert


def _sort_vokabel_key(v: Vokabel) -> tuple[float, int]:
    """Sortierschlüssel für Vokabeln: bester Score zuerst, bei gleichem Score nach Abfragen."""
    return (-v.score, v.attempts if v.score == 0 else -v.attempts)


# ── Barrierefreies Eingabefeld (Screenreader-synchronisiert) ───────────────────
class AccessibleQuestionInput(QLineEdit):
    """
    Eingabefeld, das bei Fokus stets den Text der aktuellen Frage
    oder der letzten Auswertung im Barrierefreiheitsbaum bereitstellt.
    """
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._current_speech: str = ""
        self.setPlaceholderText("Antwort eingeben …")
        self.setMaxLength(2000)  # Begrenzt auf 2000 Zeichen – verhindert O(n²) Levenshtein-DoS

    def set_question(self, question: str) -> None:
        """Setzt die Frage und aktualisiert den Barrierefreiheitsnamen."""
        self._current_speech = question.strip()
        self.setAccessibleName(f" {self._current_speech}")

    def set_feedback_speech(self, speech: str) -> None:
        """Setzt Feedback-Sprachausgabe für Screenreader."""
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


# ── Barrierefreie & tastaturnavigierbare Tabelle ──────────────────────────────
class NavigableTableWidget(QTableWidget):
    """
    Tabelle, die sich vollständig mit den Pfeiltasten bedienen lässt
    und mit Tab / Umschalt+Tab sauber zum nächsten/vorherigen Element verlassen wird.
    Unterstützt Öffnen/Aktivieren mit Enter oder Doppelklick und Löschen mit Entf.
    """
    delete_pressed = pyqtSignal()
    row_activated = pyqtSignal(int)

    def __init__(self, rows: int = 0, columns: int = 0, parent: QWidget | None = None) -> None:
        super().__init__(rows, columns, parent)
        self.setTabKeyNavigation(False)
        self.cellDoubleClicked.connect(self._on_cell_double_clicked)

    def _on_cell_double_clicked(self, row: int, col: int) -> None:
        if row >= 0:
            self.row_activated.emit(row)

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
        if e.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
            e.accept()
            return
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            row = self.currentRow()
            if row >= 0:
                self.row_activated.emit(row)
                e.accept()
                return
        super().keyPressEvent(e)

    def focusInEvent(self, e: QFocusEvent | None) -> None:
        super().focusInEvent(e)
        if e is None:
            return
        if self.rowCount() > 0 and self.currentRow() < 0:
            if self.item(0, 1) is not None:
                self.blockSignals(True)
                self.setCurrentCell(0, 1)
                self.blockSignals(False)


# ── Globaler Event-Filter für standardmäßige Enter-Aktivierung ────────────────
class EnterActivationFilter(QObject):
    """Globaler Event-Filter für die gesamte Anwendung:
    Ermöglicht das gewohnte Aktivieren mit der Enter-Taste (Return & Nummernblock-Enter)
    für alle fokussierten Buttons, Checkboxen und ListWidget-Kontrollkästchen,
    anstatt dass man wie in Standard-Qt zwingend die Leertaste drücken muss.
    """
    def eventFilter(self, watched: QObject | None, event: QEvent | None) -> bool:
        if event is not None and event.type() == QEvent.Type.KeyPress:
            if isinstance(event, QKeyEvent) and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                target = watched if isinstance(watched, QWidget) else QApplication.focusWidget()
                if target is None:
                    return super().eventFilter(watched, event)

                # 1. Fokussierter Button oder Checkbox (QPushButton, QCheckBox, QRadioButton, QToolButton)
                if isinstance(target, QAbstractButton):
                    if target.isEnabled() and target.isVisible():
                        target.click()
                        return True

                # 2. QListWidget mit Checkboxen (z. B. im Lösch- oder Auswahldialog)
                list_candidate = target
                if isinstance(list_candidate, QWidget) and not isinstance(list_candidate, QListWidget):
                    if isinstance(list_candidate.parent(), QListWidget):
                        list_candidate = list_candidate.parent()

                if isinstance(list_candidate, QListWidget):
                    item = list_candidate.currentItem()
                    if item is not None and bool(item.flags() & Qt.ItemFlag.ItemIsUserCheckable):
                        new_state = (
                            Qt.CheckState.Unchecked
                            if item.checkState() == Qt.CheckState.Checked
                            else Qt.CheckState.Checked
                        )
                        item.setCheckState(new_state)
                        return True  # Verhindert ungewolltes Schließen des Dialogs!

        return super().eventFilter(watched, event)


__all__ = [
    "STYLE",
    "_motivation",
    "get_score_color",
    "_sort_vokabel_key",
    "AccessibleQuestionInput",
    "NavigableTableWidget",
    "EnterActivationFilter",
]
