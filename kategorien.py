# kategorien.py – Kategorien-Verwaltung, Kachelkarten & Kategorie-Dialoge
"""
Dieses Modul bündelt das gesamte Kategorien-Feature der VokabelMeister:
1. Vektor-Flaggen-Icon-Generator:
   - Detailgetreue Flaggen-Icons für Sprachen im Dropdown (Deutsch, Englisch, Französisch, etc.)
2. Kategorie-Dialoge:
   - SelectKategorienDialog: Mehrfachauswahl von Kategorien zum gemeinsamen Lernen
   - AddKategorieDialog: Erstellen neuer benutzerdefinierter Lernkategorien mit eigenen Fragetexten
   - DeleteKategorieDialog: Sicheres Löschen von Kategorien mit Kaskadenschutz
3. KategorienView:
   - Übersichtliche Kachelkarten aller Kategorien mit Vokabelzählern
   - Schnellauswahl zum Starten des Abfragemodus
"""
from __future__ import annotations

from functools import lru_cache, partial
from typing import Callable

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from backend import KATEGORIEN, STANDARD_SPRACHEN, VokabelTrainer


# ── Flaggen-Icon-Generator ────────────────────────────────────────────────────
@lru_cache(maxsize=None)
def _flag_icon(lang: str, size: int = 20) -> QIcon:
    """Erstellt ein präzises Vektor-Flaggen-Icon für Dropdown-Menüs (gecacht)."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    clip = QPainterPath()
    clip.addRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 3, 3)
    p.setClipPath(clip)
    w, h = size, size

    stripes_h = {
        "Deutsch": ["#1a1a1a", "#dd0000", "#ffce00"],
        "Polnisch": ["#ffffff", "#dc143c"],
        "Russisch": ["#ffffff", "#0039a6", "#d52b1e"],
        "Niederländisch": ["#ae1c28", "#ffffff", "#21468b"],
    }
    stripes_v = {
        "Französisch": ["#002395", "#ffffff", "#ed2939"],
        "Italienisch": ["#009246", "#ffffff", "#ce2b37"],
    }

    if lang in stripes_h:
        cols = stripes_h[lang]
        sh = h / len(cols)
        for i, c in enumerate(cols):
            p.fillRect(QRectF(0, i * sh, w, sh + (1 if i == len(cols) - 1 else 0)), QColor(c))
    elif lang in stripes_v:
        cols = stripes_v[lang]
        sw = w / len(cols)
        for i, c in enumerate(cols):
            p.fillRect(QRectF(i * sw, 0, sw + (1 if i == len(cols) - 1 else 0), h), QColor(c))
    elif lang == "Englisch":
        p.fillRect(0, 0, w, h, QColor("#012169"))
        p.setPen(QPen(QColor("#ffffff"), max(2.5, w * 0.2)))
        p.drawLine(0, 0, w, h)
        p.drawLine(0, h, w, 0)
        p.setPen(QPen(QColor("#c8102e"), max(1.2, w * 0.1)))
        p.drawLine(0, 0, w, h)
        p.drawLine(0, h, w, 0)
        p.setPen(QPen(QColor("#ffffff"), max(3.5, w * 0.3)))
        p.drawLine(int(w / 2), 0, int(w / 2), h)
        p.drawLine(0, int(h / 2), w, int(h / 2))
        p.setPen(QPen(QColor("#c8102e"), max(2.0, w * 0.18)))
        p.drawLine(int(w / 2), 0, int(w / 2), h)
        p.drawLine(0, int(h / 2), w, int(h / 2))
    elif lang == "Spanisch":
        p.fillRect(0, 0, w, h // 4, QColor("#aa151b"))
        p.fillRect(0, h // 4, w, h // 2, QColor("#f1bf00"))
        p.fillRect(0, 3 * (h // 4), w, h - 3 * (h // 4), QColor("#aa151b"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#aa151b"))
        p.drawRoundedRect(QRectF(w * 0.22, h * 0.38, w * 0.14, h * 0.24), 1, 1)
    elif lang == "Japanisch":
        p.fillRect(0, 0, w, h, QColor("#ffffff"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#bc002d"))
        r = w * 0.28
        p.drawEllipse(QPointF(w / 2, h / 2), r, r)
    elif lang == "Chinesisch":
        p.fillRect(0, 0, w, h, QColor("#de2910"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffde00"))
        p.drawEllipse(QPointF(w * 0.3, h * 0.35), w * 0.16, w * 0.16)
        for pt, r in [((0.55, 0.2), 0.06), ((0.65, 0.32), 0.06), ((0.65, 0.48), 0.06), ((0.55, 0.6), 0.06)]:
            p.drawEllipse(QPointF(w * pt[0], h * pt[1]), w * r, w * r)
    elif lang == "Türkisch":
        p.fillRect(0, 0, w, h, QColor("#e30a17"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(w * 0.42, h * 0.5), w * 0.24, w * 0.24)
        p.setBrush(QColor("#e30a17"))
        p.drawEllipse(QPointF(w * 0.48, h * 0.5), w * 0.19, w * 0.19)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(w * 0.66, h * 0.5), w * 0.07, w * 0.07)
    elif lang == "Portugiesisch":
        p.fillRect(0, 0, int(w * 0.4), h, QColor("#006600"))
        p.fillRect(int(w * 0.4), 0, w - int(w * 0.4), h, QColor("#ff0000"))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffcc00"))
        p.drawEllipse(QPointF(w * 0.4, h * 0.5), w * 0.15, w * 0.15)
        p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(w * 0.4, h * 0.5), w * 0.08, w * 0.08)
    elif lang == "Griechisch":
        p.fillRect(0, 0, w, h, QColor("#0d5eaf"))
        sh = h / 9
        for i in range(1, 9, 2):
            p.fillRect(QRectF(0, i * sh, w, sh), QColor("#ffffff"))
        p.fillRect(QRectF(0, 0, w * 0.48, h * 0.52), QColor("#0d5eaf"))
        p.setPen(QPen(QColor("#ffffff"), max(1.5, w * 0.1)))
        p.drawLine(QPointF(w * 0.24, 0), QPointF(w * 0.24, h * 0.52))
        p.drawLine(QPointF(0, h * 0.26), QPointF(w * 0.48, h * 0.26))
    elif lang == "Arabisch":
        p.fillRect(0, 0, w, h, QColor("#006c35"))
        p.setPen(QPen(QColor("#ffffff"), 1.5))
        p.drawLine(QPointF(w * 0.2, h * 0.65), QPointF(w * 0.8, h * 0.65))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(QRectF(w * 0.25, h * 0.35, w * 0.5, h * 0.18), 2, 2)
    elif lang == "Latein":
        p.fillRect(0, 0, w, h, QColor("#800020"))
        p.setPen(QPen(QColor("#ffc72c"), 1.2))
        p.drawRect(QRectF(w * 0.15, h * 0.15, w * 0.7, h * 0.7))
        p.setBrush(QColor("#ffc72c"))
        p.drawEllipse(QPointF(w * 0.5, h * 0.5), w * 0.12, w * 0.12)
    else:
        p.fillRect(0, 0, w, h, QColor("#3a3d52"))

    p.setClipping(False)
    p.setPen(QPen(QColor("#3e435e"), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 3, 3)
    p.end()
    return QIcon(pix)


# ── Dialog: Kategorien zum Lernen auswählen ──────────────────────────────────
class SelectKategorienDialog(QDialog):
    """Dialog zum Auswählen mehrerer Kategorien für das gemeinsame Lernen."""
    def __init__(self, trainer: VokabelTrainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self.setWindowTitle("Kategorien zum Lernen auswählen")
        self.setMinimumSize(480, 440)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Kategorien zum Lernen auswählen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setAccessibleName(" Kategorien zum Lernen auswählen – Fenster")
        hint = QLabel("Setze bei den Kategorien ein Häkchen (mit Enter, Leertaste oder Klick), die du zusammen abfragen möchtest.")
        hint.setObjectName("statsLabel")
        hint.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(hint)

        btn_row_sel = QHBoxLayout()
        btn_all = QPushButton("☑  Alle auswählen")
        btn_all.setObjectName("secondaryBtn")
        btn_all.setAccessibleName(" Alle Kategorien auswählen")
        btn_all.clicked.connect(self._select_all)
        btn_none = QPushButton("☐  Alle abwählen")
        btn_none.setObjectName("secondaryBtn")
        btn_none.setAccessibleName(" Alle Häkchen entfernen")
        btn_none.clicked.connect(self._deselect_all)
        btn_row_sel.addWidget(btn_all)
        btn_row_sel.addWidget(btn_none)
        btn_row_sel.addStretch()
        layout.addLayout(btn_row_sel)

        self._list = QListWidget()
        self._list.setAccessibleName(" Kategorieliste mit Kontrollkästchen")
        self._list.itemChanged.connect(self._update_start_btn)
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._btn_start = QPushButton("▶  Ausgewählte lernen")
        self._btn_start.setObjectName("primaryBtn")
        self._btn_start.setAccessibleName(" Lernen mit ausgewählten Kategorien starten")
        self._btn_start.clicked.connect(self.accept)
        btn_cancel = QPushButton("Abbrechen")
        btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.setAccessibleName(" Abbrechen")
        btn_cancel.clicked.connect(self.reject)

        for b in (self._btn_start, btn_cancel, btn_all, btn_none):
            b.setAutoDefault(False)
            b.setDefault(False)

        btn_row.addWidget(self._btn_start)
        btn_row.addStretch()
        btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self._load_list()

    def _load_list(self) -> None:
        self._list.setUpdatesEnabled(False)
        self._list.blockSignals(True)
        try:
            self._list.clear()
            for kat_name, info in self._trainer.get_kategorien().items():
                icon = info.get("icon", "🏷️")
                pool_len = len(self._trainer.get_pool(kat_name))
                item = QListWidgetItem(f"{icon}  {kat_name}  ({pool_len} Vokabel{'n' if pool_len != 1 else ''})")
                item.setData(Qt.ItemDataRole.UserRole, kat_name)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
                self._list.addItem(item)
        finally:
            self._list.blockSignals(False)
            self._list.setUpdatesEnabled(True)
        self._update_start_btn()

    def _select_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None:
                item.setCheckState(Qt.CheckState.Checked)
        self._list.blockSignals(False)
        self._update_start_btn()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None:
                item.setCheckState(Qt.CheckState.Unchecked)
        self._list.blockSignals(False)
        self._update_start_btn()

    def _update_start_btn(self) -> None:
        checked = self.get_selected_kategorien()
        total = self._list.count()
        if len(checked) == 0:
            self._btn_start.setText("▶  Bitte Kategorie wählen")
            self._btn_start.setEnabled(False)
        elif len(checked) == total:
            self._btn_start.setText("▶  Alle Kategorien lernen")
            self._btn_start.setEnabled(True)
        else:
            self._btn_start.setText(f"▶  {len(checked)} Kategorien lernen")
            self._btn_start.setEnabled(True)

    def get_selected_kategorien(self) -> list[str]:
        selected: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                kat = item.data(Qt.ItemDataRole.UserRole)
                if kat:
                    selected.append(kat)
        return selected


# ── Dialog: Neue Kategorie erstellen ──────────────────────────────────────────
class AddKategorieDialog(QDialog):
    """Dialog zum Anlegen einer neuen benutzerdefinierten Kategorie."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neue Kategorie anlegen")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Neue Kategorie anlegen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setAccessibleName(" Neue Kategorie anlegen – Fenster")
        layout.addWidget(title)

        lbl_name = QLabel("NAME DER KATEGORIE")
        lbl_name.setObjectName("sectionLabel")
        self._name_edit = QLineEdit()
        self._name_edit.setMaxLength(200)
        self._name_edit.setPlaceholderText("z. B. Medizin, IT-Begriffe, Biologie …")
        self._name_edit.setAccessibleName(" Name der neuen Kategorie eingeben")
        lbl_name.setBuddy(self._name_edit)

        lbl_icon = QLabel("SYMBOL / EMOJI")
        lbl_icon.setObjectName("sectionLabel")
        self._icon_combo = QComboBox()
        self._icon_combo.setEditable(True)
        for ic in ["💻", "⌨️", "🎧", "📚", "🔬", "🌍", "🏛️", "🧪", "🎨", "🎵", "📐", "⚽", "💼", "⚖️", "🌿", "🏷️", "💡", "🩺", "✈️"]:
            self._icon_combo.addItem(f"{ic}  Symbol", userData=ic)
        self._icon_combo.setAccessibleName(" Symbol oder Emoji für die Kategorie auswählen oder eingeben")
        lbl_icon.setBuddy(self._icon_combo)

        lbl_desc = QLabel("KURZBESCHREIBUNG")
        lbl_desc.setObjectName("sectionLabel")
        self._desc_edit = QLineEdit()
        self._desc_edit.setMaxLength(500)
        self._desc_edit.setPlaceholderText("z. B. Medizinische Fachbegriffe und Definitionen")
        self._desc_edit.setAccessibleName(" Kurzbeschreibung der Kategorie eingeben")
        lbl_desc.setBuddy(self._desc_edit)

        for w in [lbl_name, self._name_edit, lbl_icon, self._icon_combo, lbl_desc, self._desc_edit]:
            layout.addWidget(w)

        lr_row = QHBoxLayout()
        lr_row.setSpacing(12)
        col_l, col_r = QVBoxLayout(), QVBoxLayout()
        lbl_l = QLabel("BEZEICHNUNG LINKS (VORDERSEITE)")
        lbl_l.setObjectName("sectionLabel")
        self._lbl_f_edit = QLineEdit("Vorderseite")
        self._lbl_f_edit.setMaxLength(100)
        self._lbl_f_edit.setAccessibleName(" Bezeichnung der linken Seite eingeben")
        lbl_l.setBuddy(self._lbl_f_edit)
        col_l.addWidget(lbl_l)
        col_l.addWidget(self._lbl_f_edit)

        lbl_r = QLabel("BEZEICHNUNG RECHTS (RÜCKSEITE)")
        lbl_r.setObjectName("sectionLabel")
        self._lbl_b_edit = QLineEdit("Rückseite")
        self._lbl_b_edit.setMaxLength(100)
        self._lbl_b_edit.setAccessibleName(" Bezeichnung der rechten Seite eingeben")
        lbl_r.setBuddy(self._lbl_b_edit)
        col_r.addWidget(lbl_r)
        col_r.addWidget(self._lbl_b_edit)
        lr_row.addLayout(col_l)
        lr_row.addLayout(col_r)
        layout.addLayout(lr_row)

        lbl_q1 = QLabel("FRAGETEXT VORDERSEITE → RÜCKSEITE")
        lbl_q1.setObjectName("sectionLabel")
        self._q1_edit = QLineEdit("Was bedeutet:")
        self._q1_edit.setMaxLength(300)
        self._q1_edit.setAccessibleName(" Fragetext von Vorderseite nach Rückseite eingeben")
        lbl_q1.setBuddy(self._q1_edit)

        lbl_q2 = QLabel("FRAGETEXT RÜCKSEITE → VORDERSEITE")
        lbl_q2.setObjectName("sectionLabel")
        self._q2_edit = QLineEdit("Welcher Begriff beschreibt folgendes:")
        self._q2_edit.setMaxLength(300)
        self._q2_edit.setAccessibleName(" Fragetext von Rückseite nach Vorderseite eingeben")
        lbl_q2.setBuddy(self._q2_edit)

        for w in [lbl_q1, self._q1_edit, lbl_q2, self._q2_edit]:
            layout.addWidget(w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok, cancel = btns.button(QDialogButtonBox.StandardButton.Ok), btns.button(QDialogButtonBox.StandardButton.Cancel)
        if ok:
            ok.setText("✔  Kategorie erstellen")
            ok.setObjectName("primaryBtn")
            ok.setAccessibleName(" Kategorie erstellen")
            ok.setAutoDefault(False)
            ok.setDefault(False)
        if cancel:
            cancel.setText("Abbrechen")
            cancel.setObjectName("secondaryBtn")
            cancel.setAccessibleName(" Abbrechen")
            cancel.setAutoDefault(False)
            cancel.setDefault(False)
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        self._name_edit.setFocus()

    def _on_save(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "Fehlender Name", "Bitte gib einen Namen für die Kategorie ein.")
            return
        self.accept()

    def get_data(self) -> dict[str, str]:
        icon_data = self._icon_combo.currentData()
        icon = icon_data if icon_data else self._icon_combo.currentText().strip()
        if " " in icon:
            icon = icon.split()[0]
        return {
            "name":         self._name_edit.text().strip(),
            "icon":         icon or "🏷️",
            "beschreibung": self._desc_edit.text().strip() or "Eigene Kategorie",
            "lbl_front":    self._lbl_f_edit.text().strip() or "Vorderseite",
            "lbl_back":     self._lbl_b_edit.text().strip() or "Rückseite",
            "frage_front":  self._q1_edit.text().strip() or "Was bedeutet:",
            "frage_back":   self._q2_edit.text().strip() or "Welcher Begriff beschreibt folgendes:",
        }


# ── Dialog: Kategorie entfernen ───────────────────────────────────────────────
class DeleteKategorieDialog(QDialog):
    """Dialog zum Löschen einer benutzerdefinierten Kategorie."""
    def __init__(self, trainer: VokabelTrainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self.setWindowTitle("Kategorie entfernen")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Kategorie entfernen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setAccessibleName(" Kategorie entfernen – Fenster")
        layout.addWidget(title)

        custom_kats = self._trainer.get_custom_kategorien()
        if not custom_kats:
            info = QLabel(
                "Es sind aktuell nur die Standard-Kategorien (Sprache, Fachwörter, Formeln, Befehle) vorhanden.\n\n"
                "Selbst erstellte Kategorien können hier jederzeit wieder entfernt werden."
            )
            info.setObjectName("statsLabel")
            info.setWordWrap(True)
            info.setAccessibleName(" Keine benutzerdefinierten Kategorien zum Entfernen vorhanden")
            layout.addWidget(info)

            btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            btns.rejected.connect(self.reject)
            btns.accepted.connect(self.reject)
            cl = btns.button(QDialogButtonBox.StandardButton.Close)
            if cl:
                cl.setText("Schließen")
                cl.setObjectName("primaryBtn")
            layout.addWidget(btns)
            return

        hint = QLabel("Wähle eine selbst erstellte Kategorie aus, die du entfernen möchtest:")
        hint.setObjectName("statsLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        lbl_sel = QLabel("KATEGORIE AUSWÄHLEN")
        lbl_sel.setObjectName("sectionLabel")
        self._combo = QComboBox()
        for k, inf in custom_kats.items():
            n = len(self._trainer.get_pool(k))
            self._combo.addItem(f"{inf.get('icon', '🏷️')}  {k}  ({n} Vokabel{'n' if n != 1 else ''})", userData=k)
        self._combo.setAccessibleName(" Zu löschende Kategorie auswählen")
        lbl_sel.setBuddy(self._combo)
        layout.addWidget(lbl_sel)
        layout.addWidget(self._combo)

        warn = QLabel("⚠️ Hinweis: Alle Vokabeln in dieser Kategorie werden ebenfalls gelöscht.")
        warn.setStyleSheet("color: #ff6b6b; font-size: 12px;")
        warn.setWordWrap(True)
        layout.addWidget(warn)

        btn_row = QHBoxLayout()
        del_btn = QPushButton("🗑  Kategorie löschen")
        del_btn.setObjectName("dangerBtn")
        del_btn.setAccessibleName(" Kategorie und enthaltene Vokabeln löschen")
        del_btn.setAutoDefault(False)
        del_btn.setDefault(False)
        del_btn.clicked.connect(self._do_delete)
        cancel_btn = QPushButton("Abbrechen")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setAccessibleName(" Abbrechen")
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(del_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _do_delete(self) -> None:
        kat = self._combo.currentData()
        if not kat:
            return
        n = len(self._trainer.get_pool(kat))
        vok_txt = f" und alle {n} enthaltenen Vokabeln" if n > 0 else ""
        confirm = QMessageBox.question(
            self, "Kategorie wirklich löschen?",
            f"Möchtest du die Kategorie \u201e{kat}\u201c{vok_txt} wirklich unwiderruflich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_kategorie(kat)
            self.accept()


# ── Kategorien-View (Kachelkarten & Eigene Kategorien) ────────────────────────
class KategorienView(QWidget):
    """Kachelübersicht aller Kategorien mit Vokabelanzahl und Schnellauswahl."""
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
        dlg = SelectKategorienDialog(self._trainer, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            selected = dlg.get_selected_kategorien()
            if selected:
                all_kats = list(self._trainer.get_kategorien().keys())
                self._on_start(None if len(selected) == len(all_kats) else selected)

    def _add_kategorie(self) -> None:
        dlg = AddKategorieDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            d = dlg.get_data()
            if self._trainer.add_kategorie(d["name"], d["icon"], d["beschreibung"], d["frage_front"], d["frage_back"], d["lbl_front"], d["lbl_back"]):
                self._rebuild_cards()
                self.refresh()
            else:
                QMessageBox.warning(self, "Kategorie existiert bereits", f"Die Kategorie \u201e{d['name']}\u201c existiert bereits.")

    def _delete_kategorie_dialog(self) -> None:
        dlg = DeleteKategorieDialog(self._trainer, self)
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
