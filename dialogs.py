# dialogs.py – VokabelMeister Dialoge (Hinzufügen, Importieren, Löschen, Kategorien-Verwaltung)
from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QDialogButtonBox, QMessageBox, QComboBox,
)
from PyQt6.QtCore import Qt, QSize, QPointF, QRectF
from PyQt6.QtGui import QFont, QPainter, QPixmap, QColor, QIcon, QPainterPath, QPen

from backend import Vokabel, VokabelTrainer, KATEGORIEN, STANDARD_SPRACHEN


# ── Flaggen-Icon-Generator ────────────────────────────────────────────────────
def _flag_icon(lang: str, size: int = 20) -> QIcon:
    """Erstellt ein präzises Flaggen-Icon für Dropdown-Menüs."""
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
        p.drawLine(0, 0, w, h); p.drawLine(0, h, w, 0)
        p.setPen(QPen(QColor("#c8102e"), max(1.2, w * 0.1)))
        p.drawLine(0, 0, w, h); p.drawLine(0, h, w, 0)
        p.setPen(QPen(QColor("#ffffff"), max(3.5, w * 0.3)))
        p.drawLine(int(w / 2), 0, int(w / 2), h); p.drawLine(0, int(h / 2), w, int(h / 2))
        p.setPen(QPen(QColor("#c8102e"), max(2.0, w * 0.18)))
        p.drawLine(int(w / 2), 0, int(w / 2), h); p.drawLine(0, int(h / 2), w, int(h / 2))
    elif lang == "Spanisch":
        p.fillRect(0, 0, w, h // 4, QColor("#aa151b"))
        p.fillRect(0, h // 4, w, h // 2, QColor("#f1bf00"))
        p.fillRect(0, 3 * (h // 4), w, h - 3 * (h // 4), QColor("#aa151b"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#aa151b"))
        p.drawRoundedRect(QRectF(w * 0.22, h * 0.38, w * 0.14, h * 0.24), 1, 1)
    elif lang == "Japanisch":
        p.fillRect(0, 0, w, h, QColor("#ffffff"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#bc002d"))
        r = w * 0.28; p.drawEllipse(QPointF(w / 2, h / 2), r, r)
    elif lang == "Chinesisch":
        p.fillRect(0, 0, w, h, QColor("#de2910"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#ffde00"))
        p.drawEllipse(QPointF(w * 0.3, h * 0.35), w * 0.16, w * 0.16)
        for pt, r in [((0.55, 0.2), 0.06), ((0.65, 0.32), 0.06), ((0.65, 0.48), 0.06), ((0.55, 0.6), 0.06)]:
            p.drawEllipse(QPointF(w * pt[0], h * pt[1]), w * r, w * r)
    elif lang == "Türkisch":
        p.fillRect(0, 0, w, h, QColor("#e30a17"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#ffffff"))
        p.drawEllipse(QPointF(w * 0.42, h * 0.5), w * 0.24, w * 0.24)
        p.setBrush(QColor("#e30a17")); p.drawEllipse(QPointF(w * 0.48, h * 0.5), w * 0.19, w * 0.19)
        p.setBrush(QColor("#ffffff")); p.drawEllipse(QPointF(w * 0.66, h * 0.5), w * 0.07, w * 0.07)
    elif lang == "Portugiesisch":
        p.fillRect(0, 0, int(w * 0.4), h, QColor("#006600"))
        p.fillRect(int(w * 0.4), 0, w - int(w * 0.4), h, QColor("#ff0000"))
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#ffcc00"))
        p.drawEllipse(QPointF(w * 0.4, h * 0.5), w * 0.15, w * 0.15)
        p.setBrush(QColor("#ffffff")); p.drawEllipse(QPointF(w * 0.4, h * 0.5), w * 0.08, w * 0.08)
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
        p.setPen(Qt.PenStyle.NoPen); p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(QRectF(w * 0.25, h * 0.35, w * 0.5, h * 0.18), 2, 2)
    elif lang == "Latein":
        p.fillRect(0, 0, w, h, QColor("#800020"))
        p.setPen(QPen(QColor("#ffc72c"), 1.2))
        p.drawRect(QRectF(w * 0.15, h * 0.15, w * 0.7, h * 0.7))
        p.setBrush(QColor("#ffc72c")); p.drawEllipse(QPointF(w * 0.5, h * 0.5), w * 0.12, w * 0.12)
    else:
        p.fillRect(0, 0, w, h, QColor("#3a3d52"))

    p.setClipping(False)
    p.setPen(QPen(QColor("#3e435e"), 1.0))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), 3, 3)
    p.end()
    return QIcon(pix)


# ── Dialog: Vokabel hinzufügen ────────────────────────────────────────────────
class AddVokabelDialog(QDialog):
    def __init__(
        self, parent: QWidget | None = None, trainer: VokabelTrainer | None = None,
        lang_f: str = "Englisch", lang_b: str = "Deutsch",
        canonical_lf: str = "", canonical_lb: str = "", initial_kat: str | None = None,
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
                    self._kat_combo.setCurrentIndex(idx); break
        self._kat_combo.setAccessibleName(" Kategorie auswählen")
        self._kat_combo.currentIndexChanged.connect(self._on_kat_changed)
        lbl_kat.setBuddy(self._kat_combo)

        self._lang_container = QWidget()
        lang_layout = QHBoxLayout(self._lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0); lang_layout.setSpacing(10)

        col_left = QVBoxLayout()
        lbl_lang_f = QLabel("SPRACHE LINKS")
        lbl_lang_f.setObjectName("sectionLabel")
        self._lang_f_combo = QComboBox()
        self._lang_f_combo.setEditable(True); self._lang_f_combo.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_f_combo.addItem(_flag_icon(s), s)
        self._lang_f_combo.setCurrentText(lang_f)
        self._lang_f_combo.setAccessibleName(" Sprache der Vorderseite")
        self._lang_f_combo.currentTextChanged.connect(self._on_lang_f_changed)
        lbl_lang_f.setBuddy(self._lang_f_combo)
        col_left.addWidget(lbl_lang_f); col_left.addWidget(self._lang_f_combo)

        arrow_lbl = QLabel("→")
        arrow_lbl.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        arrow_lbl.setStyleSheet("color: #7986e0; padding-top: 18px;")

        col_right = QVBoxLayout()
        lbl_lang_b = QLabel("SPRACHE RECHTS")
        lbl_lang_b.setObjectName("sectionLabel")
        self._lang_b_combo = QComboBox()
        self._lang_b_combo.setEditable(True); self._lang_b_combo.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_b_combo.addItem(_flag_icon(s), s)
        self._lang_b_combo.setCurrentText(lang_b)
        self._lang_b_combo.setAccessibleName(" Sprache der Rückseite")
        self._lang_b_combo.currentTextChanged.connect(self._on_lang_b_changed)
        lbl_lang_b.setBuddy(self._lang_b_combo)
        col_right.addWidget(lbl_lang_b); col_right.addWidget(self._lang_b_combo)

        lang_layout.addLayout(col_left); lang_layout.addWidget(arrow_lbl); lang_layout.addLayout(col_right)

        self._warn_widget = QWidget()
        self._warn_widget.setObjectName("warnBox")
        self._warn_widget.setStyleSheet("#warnBox { background: #3d2f00; border: 1px solid #f0a500; border-radius: 6px; padding: 2px; }")
        warn_layout = QVBoxLayout(self._warn_widget)
        warn_layout.setContentsMargins(12, 8, 12, 8); warn_layout.setSpacing(8)
        self._warn_lbl = QLabel()
        self._warn_lbl.setWordWrap(True)
        self._warn_lbl.setStyleSheet("color: #f0c040; font-size: 12px;")
        self._warn_lbl.setAccessibleName(" Richtungshinweis")
        warn_layout.addWidget(self._warn_lbl)

        warn_btn_row = QHBoxLayout(); warn_btn_row.setSpacing(8)
        self._btn_empfehlung = QPushButton(); self._btn_empfehlung.setObjectName("primaryBtn")
        self._btn_empfehlung.clicked.connect(self._empfehlung_uebernehmen)
        self._btn_weiter = QPushButton("Trotzdem so behalten"); self._btn_weiter.setObjectName("secondaryBtn")
        self._btn_weiter.clicked.connect(self._warn_widget.hide)
        warn_btn_row.addWidget(self._btn_empfehlung); warn_btn_row.addWidget(self._btn_weiter)
        warn_layout.addLayout(warn_btn_row)
        self._warn_widget.hide()

        self._lbl_front = QLabel("VORDERSEITE"); self._lbl_front.setObjectName("sectionLabel")
        self._front = QLineEdit(); self._lbl_front.setBuddy(self._front)
        self._lbl_back = QLabel("RÜCKSEITE"); self._lbl_back.setObjectName("sectionLabel")
        self._back = QLineEdit(); self._lbl_back.setBuddy(self._back)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_save); btns.rejected.connect(self.reject)
        save, cancel = btns.button(QDialogButtonBox.StandardButton.Save), btns.button(QDialogButtonBox.StandardButton.Cancel)
        if save: save.setText("💾  Speichern"); save.setObjectName("primaryBtn")
        if cancel: cancel.setObjectName("secondaryBtn")
        self._back.returnPressed.connect(self._on_save)

        for w in [lbl_kat, self._kat_combo, self._lang_container, self._warn_widget, self._lbl_front, self._front, self._lbl_back, self._back, btns]:
            layout.addWidget(w)

        self._on_kat_changed(); self._kat_combo.setFocus()

    def _on_lang_f_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_b_combo.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_b_combo.blockSignals(True)
                    self._lang_b_combo.setCurrentText(s)
                    self._lang_b_combo.blockSignals(False); break
        self._on_kat_changed(); self._check_direction()

    def _on_lang_b_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_f_combo.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_f_combo.blockSignals(True)
                    self._lang_f_combo.setCurrentText(s)
                    self._lang_f_combo.blockSignals(False); break
        self._on_kat_changed(); self._check_direction()

    def _check_direction(self) -> None:
        if self._kat_combo.currentData() != "Sprache" or not self._canonical_lf or not self._canonical_lb:
            self._warn_widget.hide(); return
        lf, lb = self._lang_f_combo.currentText().strip().lower(), self._lang_b_combo.currentText().strip().lower()
        clf, clb = self._canonical_lf.strip().lower(), self._canonical_lb.strip().lower()
        if lf == clb and lb == clf and clf != clb:
            self._warn_lbl.setText(f"⚠  Du hast bereits Vokabeln in der Richtung <b>{self._canonical_lf} → {self._canonical_lb}</b>. Die gewählte Richtung ist umgekehrt — das kann verwirren.")
            self._btn_empfehlung.setText(f"✔  Empfehlung: {self._canonical_lf} → {self._canonical_lb}")
            self._warn_widget.show()
        else:
            self._warn_widget.hide()

    def _empfehlung_uebernehmen(self) -> None:
        if self._canonical_lf and self._canonical_lb:
            self._lang_f_combo.blockSignals(True); self._lang_b_combo.blockSignals(True)
            self._lang_f_combo.setCurrentText(self._canonical_lf); self._lang_b_combo.setCurrentText(self._canonical_lb)
            self._lang_f_combo.blockSignals(False); self._lang_b_combo.blockSignals(False)
            self._warn_widget.hide(); self._on_kat_changed()

    def _on_kat_changed(self) -> None:
        kat = self._kat_combo.currentData()
        is_sprache = kat == "Sprache"
        self._lang_container.setVisible(is_sprache)
        if not is_sprache: self._warn_widget.hide()
        kat_info = self._trainer.get_kategorie_info(kat) if self._trainer else KATEGORIEN.get(kat, {})
        if is_sprache:
            lf = self._lang_f_combo.currentText().strip() or "Fremdsprache"
            lb = self._lang_b_combo.currentText().strip() or "Zielsprache"
            self._lbl_front.setText(lf.upper()); self._front.setAccessibleName(f" Vokabel auf {lf}")
            self._lbl_back.setText(lb.upper()); self._back.setAccessibleName(f" Vokabel auf {lb}")
        else:
            lbl_f = kat_info.get("lbl_front", "Vorderseite"); lbl_b = kat_info.get("lbl_back", "Rückseite")
            self._lbl_front.setText(lbl_f.upper()); self._front.setAccessibleName(f" {lbl_f} eingeben")
            self._lbl_back.setText(lbl_b.upper()); self._back.setAccessibleName(f" {lbl_b} eingeben")

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


# ── Dialog: Import-Kategorie & Sprachen wählen ────────────────────────────────
class ImportDialog(QDialog):
    def __init__(
        self, parent: QWidget | None = None, trainer: VokabelTrainer | None = None,
        lang_f: str = "Englisch", lang_b: str = "Deutsch", canonical_lf: str = "", canonical_lb: str = "",
    ) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._canonical_lf, self._canonical_lb = canonical_lf, canonical_lb
        self.setWindowTitle("Importieren – Kategorie & Sprachen")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setSpacing(14); layout.setContentsMargins(24, 24, 24, 24)

        lbl = QLabel("1. ZIELKATEGORIE WÄHLEN"); lbl.setObjectName("sectionLabel")
        self._combo = QComboBox()
        kats = self._trainer.get_kategorien() if self._trainer else KATEGORIEN
        for k, info in kats.items():
            self._combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
        self._combo.setAccessibleName(" Zielkategorie für den Import auswählen")
        self._combo.currentIndexChanged.connect(self._on_kat_changed)
        lbl.setBuddy(self._combo)

        self._lang_container = QWidget()
        lang_layout = QHBoxLayout(self._lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0); lang_layout.setSpacing(10)

        col_left = QVBoxLayout()
        lbl_lf = QLabel("SPRACHE LINKS"); lbl_lf.setObjectName("sectionLabel")
        self._lang_f = QComboBox()
        self._lang_f.setEditable(True); self._lang_f.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_f.addItem(_flag_icon(s), s)
        self._lang_f.setCurrentText(lang_f); self._lang_f.setAccessibleName(" Sprache der linken Spalte")
        self._lang_f.currentTextChanged.connect(self._on_lang_f_changed)
        col_left.addWidget(lbl_lf); col_left.addWidget(self._lang_f)

        arrow = QLabel("→"); arrow.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold)); arrow.setStyleSheet("color: #7986e0; padding-top: 18px;")

        col_right = QVBoxLayout()
        lbl_lb = QLabel("SPRACHE RECHTS"); lbl_lb.setObjectName("sectionLabel")
        self._lang_b = QComboBox()
        self._lang_b.setEditable(True); self._lang_b.setIconSize(QSize(18, 18))
        for s in STANDARD_SPRACHEN:
            self._lang_b.addItem(_flag_icon(s), s)
        self._lang_b.setCurrentText(lang_b); self._lang_b.setAccessibleName(" Sprache der rechten Spalte")
        self._lang_b.currentTextChanged.connect(self._on_lang_b_changed)
        col_right.addWidget(lbl_lb); col_right.addWidget(self._lang_b)

        lang_layout.addLayout(col_left); lang_layout.addWidget(arrow); lang_layout.addLayout(col_right)

        self._warn_widget = QWidget(); self._warn_widget.setObjectName("warnBox")
        self._warn_widget.setStyleSheet("#warnBox { background: #3d2f00; border: 1px solid #f0a500; border-radius: 6px; padding: 2px; }")
        warn_layout = QVBoxLayout(self._warn_widget); warn_layout.setContentsMargins(12, 8, 12, 8); warn_layout.setSpacing(8)
        self._warn_lbl = QLabel(); self._warn_lbl.setWordWrap(True); self._warn_lbl.setStyleSheet("color: #f0c040; font-size: 12px;")
        self._warn_lbl.setAccessibleName(" Richtungshinweis")
        warn_layout.addWidget(self._warn_lbl)

        warn_btn_row = QHBoxLayout(); warn_btn_row.setSpacing(8)
        self._btn_empfehlung = QPushButton(); self._btn_empfehlung.setObjectName("primaryBtn")
        self._btn_empfehlung.clicked.connect(self._empfehlung_uebernehmen)
        self._btn_weiter = QPushButton("Trotzdem so behalten"); self._btn_weiter.setObjectName("secondaryBtn")
        self._btn_weiter.clicked.connect(self._warn_widget.hide)
        warn_btn_row.addWidget(self._btn_empfehlung); warn_btn_row.addWidget(self._btn_weiter)
        warn_layout.addLayout(warn_btn_row)
        self._warn_widget.hide()

        self._hint = QLabel(""); self._hint.setObjectName("statsLabel"); self._hint.setWordWrap(True)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject)
        ok, cancel = btns.button(QDialogButtonBox.StandardButton.Ok), btns.button(QDialogButtonBox.StandardButton.Cancel)
        if ok: ok.setText("📂  Datei auswählen"); ok.setObjectName("primaryBtn")
        if cancel: cancel.setObjectName("secondaryBtn")

        for w in [lbl, self._combo, self._lang_container, self._warn_widget, self._hint, btns]:
            layout.addWidget(w)
        self._on_kat_changed(); self._combo.setFocus()

    def _on_lang_f_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_b.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_b.blockSignals(True); self._lang_b.setCurrentText(s); self._lang_b.blockSignals(False); break
        self._check_direction(); self._on_kat_changed()

    def _on_lang_b_changed(self, text: str) -> None:
        if text.strip().lower() == self._lang_f.currentText().strip().lower():
            for s in STANDARD_SPRACHEN:
                if s.lower() != text.strip().lower():
                    self._lang_f.blockSignals(True); self._lang_f.setCurrentText(s); self._lang_f.blockSignals(False); break
        self._check_direction(); self._on_kat_changed()

    def _check_direction(self) -> None:
        if self._combo.currentData() != "Sprache" or not self._canonical_lf or not self._canonical_lb:
            self._warn_widget.hide(); return
        lf, lb = self._lang_f.currentText().strip().lower(), self._lang_b.currentText().strip().lower()
        clf, clb = self._canonical_lf.strip().lower(), self._canonical_lb.strip().lower()
        if lf == clb and lb == clf and clf != clb:
            self._warn_lbl.setText(f"⚠ Du hast bereits Vokabeln in der Richtung <b>{self._canonical_lf} → {self._canonical_lb}</b>.<br>Die gewählte Richtung ist umgekehrt.")
            self._btn_empfehlung.setText(f"✔  Empfehlung: {self._canonical_lf} → {self._canonical_lb}")
            self._warn_widget.show()
        else:
            self._warn_widget.hide()

    def _empfehlung_uebernehmen(self) -> None:
        if self._canonical_lf and self._canonical_lb:
            self._lang_f.blockSignals(True); self._lang_b.blockSignals(True)
            self._lang_f.setCurrentText(self._canonical_lf); self._lang_b.setCurrentText(self._canonical_lb)
            self._lang_f.blockSignals(False); self._lang_b.blockSignals(False)
            self._warn_widget.hide(); self._on_kat_changed()

    def _on_kat_changed(self) -> None:
        kat = self._combo.currentData()
        is_sprache = kat == "Sprache"
        self._lang_container.setVisible(is_sprache)
        kat_info = self._trainer.get_kategorie_info(kat) if self._trainer else KATEGORIEN.get(kat, {})
        if is_sprache:
            self._check_direction()
            lf = self._lang_f.currentText().strip() or "Fremdsprache"
            lb = self._lang_b.currentText().strip() or "Deutsch"
            self._hint.setText(f"Format in der Datei (Word-Tabelle oder Textzeilen):\n[{lf}-Wort] | [{lb}-Übersetzung]")
        else:
            self._warn_widget.hide()
            lbl_f, lbl_b = kat_info.get("lbl_front", "Vorderseite"), kat_info.get("lbl_back", "Rückseite")
            self._hint.setText(f"Format in der Datei (Word-Tabelle oder Textzeilen):\n[{lbl_f}] | [{lbl_b}]")

    def get_data(self) -> tuple[str, str, str]:
        kat = self._combo.currentData() or "Sprache"
        lf = self._lang_f.currentText().strip() if kat == "Sprache" else ""
        lb = self._lang_b.currentText().strip() if kat == "Sprache" else ""
        return kat, lf or "Englisch", lb or "Deutsch"


# ── Dialog: Vokabeln löschen (Aufploppendes Fenster mit Checkboxen) ─────────────
class DeleteDialog(QDialog):
    def __init__(self, trainer: VokabelTrainer, initial_kategorie: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self.setWindowTitle("Vokabeln löschen")
        self.setMinimumSize(540, 500)

        layout = QVBoxLayout(self); layout.setSpacing(14); layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Vokabeln zum Löschen auswählen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold)); title.setAccessibleName(" Vokabeln löschen – Fenster")
        hint = QLabel("Setze bei den Vokabeln ein Häkchen (mit Leertaste oder Klick), die du löschen möchtest.")
        hint.setObjectName("statsLabel"); hint.setWordWrap(True)
        layout.addWidget(title); layout.addWidget(hint)

        filter_row = QHBoxLayout()
        filter_lbl = QLabel("KATEGORIE"); filter_lbl.setObjectName("sectionLabel")
        self._filter_combo = QComboBox(); self._filter_combo.addItem("Alle", userData=None)
        for k, info in self._trainer.get_kategorien().items():
            self._filter_combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)
        self._filter_combo.setAccessibleName(" Kategorie filtern")
        self._filter_combo.currentIndexChanged.connect(self._load_list)
        filter_lbl.setBuddy(self._filter_combo)
        filter_row.addWidget(filter_lbl); filter_row.addWidget(self._filter_combo); filter_row.addStretch()
        layout.addLayout(filter_row)

        select_row = QHBoxLayout()
        btn_desel_all = QPushButton("☐  Alle abwählen"); btn_desel_all.setObjectName("secondaryBtn")
        btn_desel_all.setAccessibleName(" Alle Häkchen entfernen"); btn_desel_all.clicked.connect(self._deselect_all)
        select_row.addWidget(btn_desel_all); select_row.addStretch()
        layout.addLayout(select_row)

        self._list = QListWidget(); self._list.setAccessibleName(" Vokabelliste mit Kontrollkästchen zum Löschen")
        self._list.itemChanged.connect(self._update_delete_button_text)
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self._btn_delete_selected = QPushButton("🗑  Markierte löschen"); self._btn_delete_selected.setObjectName("dangerBtn")
        self._btn_delete_selected.setAccessibleName(" Markierte Vokabeln löschen"); self._btn_delete_selected.clicked.connect(self._delete_selected)
        btn_delete_all = QPushButton("⚠️  Alle löschen"); btn_delete_all.setObjectName("dangerBtn")
        btn_delete_all.setAccessibleName(" Alle Vokabeln dieser Kategorie löschen"); btn_delete_all.clicked.connect(self._delete_all)
        btn_close = QPushButton("Fertig / Schließen"); btn_close.setObjectName("primaryBtn")
        btn_close.setAccessibleName(" Lösch-Fenster schließen"); btn_close.clicked.connect(self.accept)

        btn_row.addWidget(self._btn_delete_selected); btn_row.addWidget(btn_delete_all); btn_row.addStretch(); btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        if initial_kategorie:
            for idx in range(self._filter_combo.count()):
                if self._filter_combo.itemData(idx) == initial_kategorie:
                    self._filter_combo.setCurrentIndex(idx); break
        self._load_list()

    def _load_list(self) -> None:
        kat: str | None = self._filter_combo.currentData()
        self._list.blockSignals(True); self._list.clear()
        for vok in self._trainer.get_pool(kat):
            icon = KATEGORIEN.get(vok.kategorie, {}).get("icon", "")
            lang_tag = f" [{vok.lang_front} → {vok.lang_back}]" if vok.kategorie == "Sprache" and vok.lang_front else ""
            text = f"{icon}{lang_tag}  {vok.front}  →  {vok.back}"
            if vok.attempts > 0: text += f"  [{vok.score:.0f}%]"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, vok); item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked); self._list.addItem(item)
        self._list.blockSignals(False); self._update_delete_button_text()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None: item.setCheckState(Qt.CheckState.Unchecked)
        self._list.blockSignals(False); self._update_delete_button_text()

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
            self._btn_delete_selected.setText(f"🗑  {count} markierte löschen"); self._btn_delete_selected.setEnabled(True)
        else:
            self._btn_delete_selected.setText("🗑  Markierte löschen"); self._btn_delete_selected.setEnabled(False)

    def _delete_selected(self) -> None:
        checked = self._get_checked_vokabeln()
        if not checked: return
        confirm = QMessageBox.question(
            self, "Ausgewählte löschen", f"Möchtest du die {len(checked)} markierte(n) Vokabel(n) wirklich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_vokabeln(checked); self._load_list()

    def _delete_all(self) -> None:
        kat: str | None = self._filter_combo.currentData()
        pool = self._trainer.get_pool(kat)
        if not pool: QMessageBox.information(self, "Hinweis", "Keine Vokabeln vorhanden."); return
        kat_text = f"in Kategorie „{kat}“" if kat else "in allen Kategorien"
        confirm = QMessageBox.question(
            self, "Alle löschen", f"Möchtest du wirklich ALLE {len(pool)} Vokabeln {kat_text} unwiderruflich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_all(kat); self._load_list()


# ── Dialog: Kategorien zum Lernen auswählen (Mehrfachauswahl mit Checkboxen) ──
class SelectKategorienDialog(QDialog):
    """Dialog zum Auswählen mehrerer Kategorien für das gemeinsame Lernen."""
    def __init__(self, trainer: VokabelTrainer, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self.setWindowTitle("Kategorien zum Lernen auswählen")
        self.setMinimumSize(480, 440)

        layout = QVBoxLayout(self); layout.setSpacing(14); layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Kategorien zum Lernen auswählen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold)); title.setAccessibleName(" Kategorien zum Lernen auswählen – Fenster")
        hint = QLabel("Setze bei den Kategorien ein Häkchen (mit Leertaste oder Klick), die du zusammen abfragen möchtest.")
        hint.setObjectName("statsLabel"); hint.setWordWrap(True)
        layout.addWidget(title); layout.addWidget(hint)

        btn_row_sel = QHBoxLayout()
        btn_all = QPushButton("☑  Alle auswählen"); btn_all.setObjectName("secondaryBtn")
        btn_all.setAccessibleName(" Alle Kategorien auswählen"); btn_all.clicked.connect(self._select_all)
        btn_none = QPushButton("☐  Alle abwählen"); btn_none.setObjectName("secondaryBtn")
        btn_none.setAccessibleName(" Alle Häkchen entfernen"); btn_none.clicked.connect(self._deselect_all)
        btn_row_sel.addWidget(btn_all); btn_row_sel.addWidget(btn_none); btn_row_sel.addStretch()
        layout.addLayout(btn_row_sel)

        self._list = QListWidget(); self._list.setAccessibleName(" Kategorieliste mit Kontrollkästchen")
        self._list.itemChanged.connect(self._update_start_btn)
        layout.addWidget(self._list, stretch=1)

        btn_row = QHBoxLayout(); btn_row.setSpacing(10)
        self._btn_start = QPushButton("▶  Ausgewählte lernen"); self._btn_start.setObjectName("primaryBtn")
        self._btn_start.setAccessibleName(" Lernen mit ausgewählten Kategorien starten"); self._btn_start.clicked.connect(self.accept)
        btn_cancel = QPushButton("Abbrechen"); btn_cancel.setObjectName("secondaryBtn")
        btn_cancel.setAccessibleName(" Abbrechen"); btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_start); btn_row.addStretch(); btn_row.addWidget(btn_cancel)
        layout.addLayout(btn_row)

        self._load_list()

    def _load_list(self) -> None:
        self._list.blockSignals(True); self._list.clear()
        for kat_name, info in self._trainer.get_kategorien().items():
            icon = info.get("icon", "🏷️")
            pool_len = len(self._trainer.get_pool(kat_name))
            item = QListWidgetItem(f"{icon}  {kat_name}  ({pool_len} Vokabel{'n' if pool_len != 1 else ''})")
            item.setData(Qt.ItemDataRole.UserRole, kat_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked); self._list.addItem(item)
        self._list.blockSignals(False); self._update_start_btn()

    def _select_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None: item.setCheckState(Qt.CheckState.Checked)
        self._list.blockSignals(False); self._update_start_btn()

    def _deselect_all(self) -> None:
        self._list.blockSignals(True)
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None: item.setCheckState(Qt.CheckState.Unchecked)
        self._list.blockSignals(False); self._update_start_btn()

    def _update_start_btn(self) -> None:
        checked = self.get_selected_kategorien()
        total = self._list.count()
        if len(checked) == 0:
            self._btn_start.setText("▶  Bitte Kategorie wählen"); self._btn_start.setEnabled(False)
        elif len(checked) == total:
            self._btn_start.setText("▶  Alle Kategorien lernen"); self._btn_start.setEnabled(True)
        else:
            self._btn_start.setText(f"▶  {len(checked)} Kategorien lernen"); self._btn_start.setEnabled(True)

    def get_selected_kategorien(self) -> list[str]:
        selected: list[str] = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                kat = item.data(Qt.ItemDataRole.UserRole)
                if kat: selected.append(kat)
        return selected


# ── Dialog: Neue Kategorie erstellen ──────────────────────────────────────────
class AddKategorieDialog(QDialog):
    """Dialog zum Anlegen einer neuen benutzerdefinierten Kategorie."""
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neue Kategorie anlegen")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self); layout.setSpacing(14); layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Neue Kategorie anlegen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold)); title.setAccessibleName(" Neue Kategorie anlegen – Fenster")
        layout.addWidget(title)

        lbl_name = QLabel("NAME DER KATEGORIE"); lbl_name.setObjectName("sectionLabel")
        self._name_edit = QLineEdit(); self._name_edit.setPlaceholderText("z. B. Medizin, IT-Begriffe, Biologie …")
        self._name_edit.setAccessibleName(" Name der neuen Kategorie eingeben"); lbl_name.setBuddy(self._name_edit)

        lbl_icon = QLabel("SYMBOL / EMOJI"); lbl_icon.setObjectName("sectionLabel")
        self._icon_combo = QComboBox(); self._icon_combo.setEditable(True)
        for ic in ["💻", "⌨️", "🎧", "📚", "🔬", "🌍", "🏛️", "🧪", "🎨", "🎵", "📐", "⚽", "💼", "⚖️", "🌿", "🏷️", "💡", "🩺", "✈️"]:
            self._icon_combo.addItem(f"{ic}  Symbol", userData=ic)
        self._icon_combo.setAccessibleName(" Symbol oder Emoji für die Kategorie auswählen oder eingeben"); lbl_icon.setBuddy(self._icon_combo)

        lbl_desc = QLabel("KURZBESCHREIBUNG"); lbl_desc.setObjectName("sectionLabel")
        self._desc_edit = QLineEdit(); self._desc_edit.setPlaceholderText("z. B. Medizinische Fachbegriffe und Definitionen")
        self._desc_edit.setAccessibleName(" Kurzbeschreibung der Kategorie eingeben"); lbl_desc.setBuddy(self._desc_edit)

        for w in [lbl_name, self._name_edit, lbl_icon, self._icon_combo, lbl_desc, self._desc_edit]:
            layout.addWidget(w)

        lr_row = QHBoxLayout(); lr_row.setSpacing(12)
        col_l, col_r = QVBoxLayout(), QVBoxLayout()
        lbl_l = QLabel("BEZEICHNUNG LINKS (VORDERSEITE)"); lbl_l.setObjectName("sectionLabel")
        self._lbl_f_edit = QLineEdit("Vorderseite"); self._lbl_f_edit.setAccessibleName(" Bezeichnung der linken Seite eingeben"); lbl_l.setBuddy(self._lbl_f_edit)
        col_l.addWidget(lbl_l); col_l.addWidget(self._lbl_f_edit)

        lbl_r = QLabel("BEZEICHNUNG RECHTS (RÜCKSEITE)"); lbl_r.setObjectName("sectionLabel")
        self._lbl_b_edit = QLineEdit("Rückseite"); self._lbl_b_edit.setAccessibleName(" Bezeichnung der rechten Seite eingeben"); lbl_r.setBuddy(self._lbl_b_edit)
        col_r.addWidget(lbl_r); col_r.addWidget(self._lbl_b_edit)
        lr_row.addLayout(col_l); lr_row.addLayout(col_r); layout.addLayout(lr_row)

        lbl_q1 = QLabel("FRAGETEXT VORDERSEITE → RÜCKSEITE"); lbl_q1.setObjectName("sectionLabel")
        self._q1_edit = QLineEdit("Was bedeutet:"); self._q1_edit.setAccessibleName(" Fragetext von Vorderseite nach Rückseite eingeben"); lbl_q1.setBuddy(self._q1_edit)

        lbl_q2 = QLabel("FRAGETEXT RÜCKSEITE → VORDERSEITE"); lbl_q2.setObjectName("sectionLabel")
        self._q2_edit = QLineEdit("Welcher Begriff beschreibt folgendes:"); self._q2_edit.setAccessibleName(" Fragetext von Rückseite nach Vorderseite eingeben"); lbl_q2.setBuddy(self._q2_edit)

        for w in [lbl_q1, self._q1_edit, lbl_q2, self._q2_edit]: layout.addWidget(w)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok, cancel = btns.button(QDialogButtonBox.StandardButton.Ok), btns.button(QDialogButtonBox.StandardButton.Cancel)
        if ok: ok.setText("✔  Kategorie erstellen"); ok.setObjectName("primaryBtn"); ok.setAccessibleName(" Kategorie erstellen")
        if cancel: cancel.setText("Abbrechen"); cancel.setObjectName("secondaryBtn"); cancel.setAccessibleName(" Abbrechen")
        btns.accepted.connect(self._on_save); btns.rejected.connect(self.reject)
        layout.addWidget(btns); self._name_edit.setFocus()

    def _on_save(self) -> None:
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "Fehlender Name", "Bitte gib einen Namen für die Kategorie ein.")
            return
        self.accept()

    def get_data(self) -> dict[str, str]:
        icon_data = self._icon_combo.currentData()
        icon = icon_data if icon_data else self._icon_combo.currentText().strip()
        if " " in icon: icon = icon.split()[0]
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

        layout = QVBoxLayout(self); layout.setSpacing(14); layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Kategorie entfernen")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold)); title.setAccessibleName(" Kategorie entfernen – Fenster")
        layout.addWidget(title)

        custom_kats = self._trainer.get_custom_kategorien()
        if not custom_kats:
            info = QLabel(
                "Es sind aktuell nur die Standard-Kategorien (Sprache, Fachwörter, Formeln, Befehle) vorhanden.\n\n"
                "Selbst erstellte Kategorien können hier jederzeit wieder entfernt werden."
            )
            info.setObjectName("statsLabel"); info.setWordWrap(True)
            info.setAccessibleName(" Keine benutzerdefinierten Kategorien zum Entfernen vorhanden")
            layout.addWidget(info)

            btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            btns.rejected.connect(self.reject); btns.accepted.connect(self.reject)
            cl = btns.button(QDialogButtonBox.StandardButton.Close)
            if cl: cl.setText("Schließen"); cl.setObjectName("primaryBtn")
            layout.addWidget(btns)
            return

        hint = QLabel("Wähle eine selbst erstellte Kategorie aus, die du entfernen möchtest:")
        hint.setObjectName("statsLabel"); hint.setWordWrap(True); layout.addWidget(hint)

        lbl_sel = QLabel("KATEGORIE AUSWÄHLEN"); lbl_sel.setObjectName("sectionLabel")
        self._combo = QComboBox()
        for k, inf in custom_kats.items():
            n = len(self._trainer.get_pool(k))
            self._combo.addItem(f"{inf.get('icon', '🏷️')}  {k}  ({n} Vokabel{'n' if n != 1 else ''})", userData=k)
        self._combo.setAccessibleName(" Zu löschende Kategorie auswählen"); lbl_sel.setBuddy(self._combo)
        layout.addWidget(lbl_sel); layout.addWidget(self._combo)

        warn = QLabel("⚠️ Hinweis: Alle Vokabeln in dieser Kategorie werden ebenfalls gelöscht.")
        warn.setStyleSheet("color: #ff6b6b; font-size: 12px;"); warn.setWordWrap(True)
        layout.addWidget(warn)

        btn_row = QHBoxLayout()
        del_btn = QPushButton("🗑  Kategorie löschen"); del_btn.setObjectName("dangerBtn")
        del_btn.setAccessibleName(" Kategorie und enthaltene Vokabeln löschen"); del_btn.clicked.connect(self._do_delete)
        cancel_btn = QPushButton("Abbrechen"); cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setAccessibleName(" Abbrechen"); cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(del_btn); btn_row.addStretch(); btn_row.addWidget(cancel_btn)
        layout.addLayout(btn_row)

    def _do_delete(self) -> None:
        kat = self._combo.currentData()
        if not kat: return
        n = len(self._trainer.get_pool(kat))
        vok_txt = f" und alle {n} enthaltenen Vokabeln" if n > 0 else ""
        confirm = QMessageBox.question(
            self, "Kategorie wirklich löschen?",
            f"Möchtest du die Kategorie \u201e{kat}\u201c{vok_txt} wirklich unwiderruflich löschen?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self._trainer.delete_kategorie(kat); self.accept()
