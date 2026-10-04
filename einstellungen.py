# einstellungen.py – Einstellungen, feste Abfragerichtung & Einstellungs-View
"""
Dieses Modul verwaltet die Anwendungseinstellungen der Lernplatform:
1. Konfigurations-Persistenz:
   - Speichert und lädt einstellungen.json (Abfragerichtung, Kategorien-Konfiguration)
2. DirectionSettingsDialog:
   - Barrierefreier Dialog zum Festlegen der Abfragerichtung:
     - Für Sprachen: Auswahl von Ausgangssprache (Frage) und Zielsprache (Antwort), z. B. Englisch → Deutsch
     - Für andere Kategorien (Fachwörter, Formeln, Befehle, benutzerdefinierte Kategorien):
       Vorderseite → Rückseite oder Rückseite → Vorderseite
     - Live-Vorschau der daraus generierten Satzfragen in Echtzeit
     - Vollständige Enter- und Tastaturbedienung
3. EinstellungenView:
   - Zentrale Einstellungsansicht für die Seitenleiste
   - Aktivieren / Deaktivieren der Ein-Richtungs-Abfrage (feste Richtung)
   - Schneller Zugriff auf Speicherort, Barrierefreiheits-Infos und Statistiken
"""
from __future__ import annotations

import json
import logging
import os
import random
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from backend import APP_DIR, STANDARD_SPRACHEN, Vokabel, VokabelTrainer
from kategorien import _flag_icon

logger = logging.getLogger(__name__)

SETTINGS_FILE: Path = APP_DIR / "einstellungen.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "direction_enabled": False,  # True = feste Richtung, False = gemischt / zufällig
    "spelling_duration_seconds": 8,  # Anzeigedauer auf der Braillezeile / Bildschirm bei Fehlern (in Sekunden)
    "categories": {
        "Sprache": {
            "question_lang": "Englisch",
            "answer_lang": "Deutsch",
            "direction": "front_to_back",
        },
        "Fachwörter": {
            "direction": "front_to_back",
        },
        "Formeln": {
            "direction": "front_to_back",
        },
        "Befehle": {
            "direction": "front_to_back",
        },
    },
    "default_direction": "front_to_back",
}


# ── Einstellungen laden und speichern ─────────────────────────────────────────
def load_settings() -> dict[str, Any]:
    """Lädt die Einstellungen aus einstellungen.json oder liefert Standardwerte."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    settings: dict[str, Any] = json.loads(json.dumps(DEFAULT_SETTINGS))
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if "direction_enabled" in data:
                    settings["direction_enabled"] = bool(data["direction_enabled"])
                if "spelling_duration_seconds" in data:
                    try:
                        settings["spelling_duration_seconds"] = max(1, min(60, int(data["spelling_duration_seconds"])))
                    except Exception:
                        pass
                if "default_direction" in data:
                    settings["default_direction"] = str(data["default_direction"])
                if "categories" in data and isinstance(data["categories"], dict):
                    for k, v in data["categories"].items():
                        if isinstance(v, dict):
                            settings["categories"].setdefault(k, {})
                            settings["categories"][k].update(v)
        except Exception as exc:
            logger.warning("Fehler beim Laden von einstellungen.json: %s", exc)
    return settings


def save_settings(settings: dict[str, Any]) -> None:
    """Speichert die Einstellungen atomar in einstellungen.json."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp = SETTINGS_FILE.with_suffix(".json.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        tmp.replace(SETTINGS_FILE)
    except Exception as exc:
        logger.error("Fehler beim Speichern von einstellungen.json: %s", exc)
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass


def get_direction_for_vocab(vok: Vokabel, settings: dict[str, Any]) -> bool:
    """Ermittelt für eine Vokabel, ob reverse=True (Rückseite als Frage)
    oder reverse=False (Vorderseite als Frage) verwendet werden soll.
    """
    if not settings.get("direction_enabled", False):
        return random.choice([False, True])

    kat = vok.kategorie
    cat_cfg: dict[str, Any] = settings.get("categories", {}).get(kat, {})

    if kat == "Sprache":
        q_lang = cat_cfg.get("question_lang", "Englisch").strip().lower()
        a_lang = cat_cfg.get("answer_lang", "Deutsch").strip().lower()
        vf_lang = vok.lang_front.strip().lower()
        vb_lang = vok.lang_back.strip().lower()

        # 1. Prüfe Frage-Sprache
        if q_lang and vf_lang == q_lang:
            return False  # Vorderseite ist die Frage
        if q_lang and vb_lang == q_lang:
            return True   # Rückseite ist die Frage

        # 2. Prüfe Antwort-Sprache
        if a_lang and vb_lang == a_lang:
            return False  # Rückseite ist die gesuchte Antwort -> Vorderseite ist Frage
        if a_lang and vf_lang == a_lang:
            return True   # Vorderseite ist die gesuchte Antwort -> Rückseite ist Frage

        # 3. Fallback auf konfigurierte Richtung
        return cat_cfg.get("direction", "front_to_back") == "back_to_front"

    # Andere Kategorien: front_to_back oder back_to_front
    direction = cat_cfg.get("direction", settings.get("default_direction", "front_to_back"))
    return direction == "back_to_front"


# ── Dialog: Abfragerichtung konfigurieren ─────────────────────────────────────
class DirectionSettingsDialog(QDialog):
    """Dialog zum Konfigurieren der festen Abfragerichtung für Sprachen und andere Kategorien."""

    def __init__(
        self,
        trainer: VokabelTrainer,
        settings: dict[str, Any],
        initial_kat: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Abfragerichtung einstellen")
        self.setMinimumWidth(560)
        self._trainer = trainer
        self._settings = json.loads(json.dumps(settings))
        self._initial_kat = initial_kat or "Sprache"
        self._build_ui()
        self._load_category_config(self._initial_kat)

    def _build_ui(self) -> None:
        self.setObjectName("directionDialog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        # Header
        title = QLabel("⇄  Abfragerichtung einstellen")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setAccessibleName(" Abfragerichtung einstellen")
        layout.addWidget(title)

        subtitle = QLabel(
            "Lege fest, welche Sprache oder welcher Begriff als Frage vorgegeben wird "
            "und was du als Antwort eingeben musst."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #8b90a8; font-size: 13px;")
        layout.addWidget(subtitle)

        # Kategorie-Auswahl
        kat_box = QHBoxLayout()
        kat_lbl = QLabel("KATEGORIE:")
        kat_lbl.setObjectName("sectionLabel")
        kat_lbl.setFixedWidth(100)
        self._kat_combo = QComboBox()
        self._kat_combo.setAccessibleName(" Kategorie für Richtungsauswahl")
        kats = self._trainer.get_kategorien()
        for k, info in kats.items():
            self._kat_combo.addItem(info.get("icon", "🏷️") + "  " + k, userData=k)

        # Vorbelegung der gewählten Kategorie
        for idx in range(self._kat_combo.count()):
            if self._kat_combo.itemData(idx) == self._initial_kat:
                self._kat_combo.setCurrentIndex(idx)
                break

        self._kat_combo.currentIndexChanged.connect(self._on_kat_changed)
        kat_lbl.setBuddy(self._kat_combo)
        kat_box.addWidget(kat_lbl)
        kat_box.addWidget(self._kat_combo, stretch=1)
        layout.addLayout(kat_box)

        # Trenner
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #2a2d3e;")
        layout.addWidget(sep)

        # ── Bereich A: Für Kategorie "Sprache" (Sprachauswahl) ────────────────
        self._lang_container = QWidget()
        lang_layout = QVBoxLayout(self._lang_container)
        lang_layout.setContentsMargins(0, 0, 0, 0)
        lang_layout.setSpacing(12)

        lang_row = QHBoxLayout()
        lang_row.setSpacing(10)

        # Linke Spalte: Frage-Sprache
        col_q = QVBoxLayout()
        lbl_q = QLabel("VORGEGEBENE SPRACHE (FRAGE)")
        lbl_q.setObjectName("sectionLabel")
        self._combo_q_lang = QComboBox()
        self._combo_q_lang.setEditable(True)
        self._combo_q_lang.setAccessibleName(" Vorgegebene Sprache als Frage")
        col_q.addWidget(lbl_q)
        col_q.addWidget(self._combo_q_lang)
        lang_row.addLayout(col_q, stretch=1)

        # Tauschen-Button in der Mitte
        self._swap_btn = QPushButton("⇄  Tauschen")
        self._swap_btn.setObjectName("secondaryBtn")
        self._swap_btn.setAccessibleName(" Sprachen tauschen")
        self._swap_btn.setAutoDefault(False)
        self._swap_btn.setDefault(False)
        self._swap_btn.setToolTip("Frage- und Antwortsprache vertauschen")
        self._swap_btn.clicked.connect(self._swap_languages)
        swap_col = QVBoxLayout()
        swap_col.addSpacing(18)
        swap_col.addWidget(self._swap_btn)
        lang_row.addLayout(swap_col)

        # Rechte Spalte: Antwort-Sprache
        col_a = QVBoxLayout()
        lbl_a = QLabel("GESUCHTE SPRACHE (ANTWORT)")
        lbl_a.setObjectName("sectionLabel")
        self._combo_a_lang = QComboBox()
        self._combo_a_lang.setEditable(True)
        self._combo_a_lang.setAccessibleName(" Gesuchte Sprache als Antwort")
        col_a.addWidget(lbl_a)
        col_a.addWidget(self._combo_a_lang)
        lang_row.addLayout(col_a, stretch=1)

        lang_layout.addLayout(lang_row)

        self._populate_language_combos()
        self._combo_q_lang.currentTextChanged.connect(self._update_preview)
        self._combo_a_lang.currentTextChanged.connect(self._update_preview)

        layout.addWidget(self._lang_container)

        # ── Bereich B: Für andere Kategorien (Fachwörter, Formeln, Befehle) ──
        self._other_container = QWidget()
        other_layout = QVBoxLayout(self._other_container)
        other_layout.setContentsMargins(0, 0, 0, 0)
        other_layout.setSpacing(10)

        lbl_dir = QLabel("ABFRAGERICHTUNG:")
        lbl_dir.setObjectName("sectionLabel")
        other_layout.addWidget(lbl_dir)

        self._radio_front_to_back = QRadioButton()
        self._radio_front_to_back.setObjectName("dirRadio")
        self._radio_front_to_back.setAccessibleName(" Vorderseite vorgeben, Rückseite abfragen")
        self._radio_front_to_back.toggled.connect(self._update_preview)

        self._radio_back_to_front = QRadioButton()
        self._radio_back_to_front.setObjectName("dirRadio")
        self._radio_back_to_front.setAccessibleName(" Rückseite vorgeben, Vorderseite abfragen")
        self._radio_back_to_front.toggled.connect(self._update_preview)

        other_layout.addWidget(self._radio_front_to_back)
        other_layout.addWidget(self._radio_back_to_front)

        # Umkehren-Button für andere Kategorien
        self._other_swap_btn = QPushButton("⇄  Richtung umkehren")
        self._other_swap_btn.setObjectName("secondaryBtn")
        self._other_swap_btn.setAutoDefault(False)
        self._other_swap_btn.setDefault(False)
        self._other_swap_btn.setAccessibleName(" Richtung der Abfrage umkehren")
        self._other_swap_btn.clicked.connect(self._swap_other_direction)
        other_layout.addWidget(self._other_swap_btn)

        layout.addWidget(self._other_container)

        # ── Live-Vorschau der generierten Fragestellung ──────────────────────
        self._preview_card = QFrame()
        self._preview_card.setObjectName("previewCard")
        self._preview_card.setStyleSheet("""
            QFrame#previewCard {
                background-color: #161922;
                border: 1px solid #7986e0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        prev_layout = QVBoxLayout(self._preview_card)
        prev_layout.setSpacing(6)

        prev_title = QLabel("BEISPIEL-FRAGESTELLUNG (LIVE-VORSCHAU):")
        prev_title.setObjectName("sectionLabel")
        prev_title.setStyleSheet("color: #7986e0; font-size: 11px; font-weight: bold;")
        prev_layout.addWidget(prev_title)

        self._preview_q_lbl = QLabel()
        self._preview_q_lbl.setWordWrap(True)
        self._preview_q_lbl.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600;")
        self._preview_q_lbl.setAccessibleName(" Beispiel-Fragestellung")
        prev_layout.addWidget(self._preview_q_lbl)

        self._preview_a_lbl = QLabel()
        self._preview_a_lbl.setWordWrap(True)
        self._preview_a_lbl.setStyleSheet("color: #4caf7d; font-size: 13px;")
        self._preview_a_lbl.setAccessibleName(" Erwartete Antwort")
        prev_layout.addWidget(self._preview_a_lbl)

        layout.addWidget(self._preview_card)

        # ── Dialog Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        btn_row.addStretch()

        self._cancel_btn = QPushButton("Abbrechen")
        self._cancel_btn.setObjectName("secondaryBtn")
        self._cancel_btn.setAutoDefault(False)
        self._cancel_btn.setDefault(False)
        self._cancel_btn.setAccessibleName(" Abbrechen")
        self._cancel_btn.clicked.connect(self.reject)

        self._save_btn = QPushButton("✓  Speichern & Übernehmen")
        self._save_btn.setObjectName("primaryBtn")
        self._save_btn.setAutoDefault(False)
        self._save_btn.setDefault(False)
        self._save_btn.setAccessibleName(" Speichern und Übernehmen")
        self._save_btn.clicked.connect(self._save_and_accept)

        btn_row.addWidget(self._cancel_btn)
        btn_row.addWidget(self._save_btn)
        layout.addLayout(btn_row)

    def _populate_language_combos(self) -> None:
        """Füllt die Sprach-Dropdowns mit Standard- und vorhandenen Sprachen."""
        all_langs: set[str] = set(STANDARD_SPRACHEN)
        for v in self._trainer.vokabeln:
            if v.lang_front:
                all_langs.add(v.lang_front.strip())
            if v.lang_back:
                all_langs.add(v.lang_back.strip())

        sorted_langs = sorted(all_langs)
        self._combo_q_lang.clear()
        self._combo_a_lang.clear()
        for s in sorted_langs:
            self._combo_q_lang.addItem(_flag_icon(s), s)
            self._combo_a_lang.addItem(_flag_icon(s), s)

    def _on_kat_changed(self) -> None:
        kat = self._kat_combo.currentData()
        if kat:
            self._load_category_config(kat)

    def _load_category_config(self, kat: str) -> None:
        """Lädt die Konfiguration für die gewählte Kategorie in die Dialogelemente."""
        cat_cfg = self._settings.get("categories", {}).get(kat, {})
        info = self._trainer.get_kategorie_info(kat)

        if kat == "Sprache":
            self._lang_container.show()
            self._other_container.hide()

            q_lang = cat_cfg.get("question_lang", "Englisch")
            a_lang = cat_cfg.get("answer_lang", "Deutsch")

            self._combo_q_lang.blockSignals(True)
            self._combo_a_lang.blockSignals(True)
            self._combo_q_lang.setCurrentText(q_lang)
            self._combo_a_lang.setCurrentText(a_lang)
            self._combo_q_lang.blockSignals(False)
            self._combo_a_lang.blockSignals(False)
        else:
            self._lang_container.hide()
            self._other_container.show()

            lbl_f = info.get("lbl_front", "Vorderseite")
            lbl_b = info.get("lbl_back", "Rückseite")

            self._radio_front_to_back.setText(f"{lbl_f} vorgeben  ➔  {lbl_b} abfragen (Standard)")
            self._radio_back_to_front.setText(f"{lbl_b} vorgeben  ➔  {lbl_f} abfragen (Umgekehrt)")

            direction = cat_cfg.get("direction", "front_to_back")
            if direction == "back_to_front":
                self._radio_back_to_front.setChecked(True)
            else:
                self._radio_front_to_back.setChecked(True)

        self._update_preview()

    def _swap_languages(self) -> None:
        """Tauscht Frage- und Antwortsprache für die Kategorie Sprache."""
        q = self._combo_q_lang.currentText()
        a = self._combo_a_lang.currentText()
        self._combo_q_lang.setCurrentText(a)
        self._combo_a_lang.setCurrentText(q)
        self._update_preview()

    def _swap_other_direction(self) -> None:
        """Tauscht die Richtung für andere Kategorien um."""
        if self._radio_front_to_back.isChecked():
            self._radio_back_to_front.setChecked(True)
        else:
            self._radio_front_to_back.setChecked(True)
        self._update_preview()

    def _update_preview(self) -> None:
        """Erzeugt die Live-Vorschau der Fragestellung."""
        kat = self._kat_combo.currentData() or "Sprache"
        info = self._trainer.get_kategorie_info(kat)

        # Suche nach einer echten Beispiel-Vokabel
        pool = self._trainer.get_pool(kat)
        sample_vok = pool[0] if pool else None

        if kat == "Sprache":
            q_lang = self._combo_q_lang.currentText().strip() or "Englisch"
            a_lang = self._combo_a_lang.currentText().strip() or "Deutsch"

            # Beispielbegriffe
            if sample_vok and sample_vok.lang_front.lower() == q_lang.lower():
                sample_word = sample_vok.front
                sample_ans = sample_vok.back
            elif sample_vok and sample_vok.lang_back.lower() == q_lang.lower():
                sample_word = sample_vok.back
                sample_ans = sample_vok.front
            else:
                sample_word = "apple" if q_lang == "Englisch" else "bonjour" if q_lang == "Französisch" else "casa"
                sample_ans = "Apfel" if a_lang == "Deutsch" else "house" if a_lang == "Englisch" else "Haus"

            self._preview_q_lbl.setText(f"„Wie lautet die Übersetzung von \u201e{sample_word}\u201c auf {a_lang}?“")
            self._preview_a_lbl.setText(f"✓ Erwartete Antwort: \u201e{sample_ans}\u201c")
        else:
            is_reverse = self._radio_back_to_front.isChecked()
            lbl_f = info.get("lbl_front", "Vorderseite")
            lbl_b = info.get("lbl_back", "Rückseite")

            if sample_vok:
                f_val = sample_vok.front
                b_val = sample_vok.back
            else:
                if kat == "Fachwörter":
                    f_val, b_val = "Photosynthese", "Pflanzen erzeugen mit Licht Zucker"
                elif kat == "Formeln":
                    f_val, b_val = "E = mc²", "Masse-Energie-Äquivalenz"
                elif kat == "Befehle":
                    f_val, b_val = "Windows + D", "Desktop anzeigen"
                else:
                    f_val, b_val = f"Beispiel-{lbl_f}", f"Beispiel-{lbl_b}"

            if kat == "Fachwörter":
                if is_reverse:
                    q_text = f"Welcher Begriff beschreibt: \u201e{b_val}\u201c?"
                    ans_text = f_val
                else:
                    q_text = f"Was bedeutet der Fachbegriff \u201e{f_val}\u201c?"
                    ans_text = b_val
            elif kat == "Formeln":
                if is_reverse:
                    q_text = f"Wie lautet die Formel für: \u201e{b_val}\u201c?"
                    ans_text = f_val
                else:
                    q_text = f"Was bedeutet die Formel \u201e{f_val}\u201c?"
                    ans_text = b_val
            elif kat == "Befehle":
                if is_reverse:
                    q_text = f"Welches Tastenkürzel bewirkt: \u201e{b_val}\u201c?"
                    ans_text = f_val
                else:
                    q_text = f"Was macht das Tastenkürzel \u201e{f_val}\u201c?"
                    ans_text = b_val
            else:
                if is_reverse:
                    raw_q = info.get("frage_back", "Welcher Begriff beschreibt:").strip().rstrip(":?")
                    q_text = f"{raw_q}: \u201e{b_val}\u201c?"
                    ans_text = f_val
                else:
                    raw_q = info.get("frage_front", "Was bedeutet:").strip().rstrip(":?")
                    q_text = f"{raw_q} \u201e{f_val}\u201c?"
                    ans_text = b_val

            self._preview_q_lbl.setText(f"„{q_text}“")
            self._preview_a_lbl.setText(f"✓ Erwartete Antwort: \u201e{ans_text}\u201c")

    def _save_and_accept(self) -> None:
        """Speichert die Eingaben in das Konfigurations-Dictionary und schließt den Dialog."""
        kat = self._kat_combo.currentData() or "Sprache"
        self._settings.setdefault("categories", {})
        self._settings["categories"].setdefault(kat, {})

        if kat == "Sprache":
            q_lang = self._combo_q_lang.currentText().strip() or "Englisch"
            a_lang = self._combo_a_lang.currentText().strip() or "Deutsch"
            self._settings["categories"][kat]["question_lang"] = q_lang
            self._settings["categories"][kat]["answer_lang"] = a_lang
        else:
            direction = "back_to_front" if self._radio_back_to_front.isChecked() else "front_to_back"
            self._settings["categories"][kat]["direction"] = direction

        self._settings["direction_enabled"] = True
        save_settings(self._settings)
        self.accept()

    def get_settings(self) -> dict[str, Any]:
        """Gibt die aktualisierten Einstellungen zurück."""
        return self._settings


# ── Einstellungen-View (Hauptansicht für die Seitenleiste) ────────────────────
class EinstellungenView(QWidget):
    """Zentrale Einstellungsansicht der Lernplatform:
    - Feste Abfragerichtung aktivieren/deaktivieren und konfigurieren
    - Tastaturnavigation & Screenreader-Status
    - Datenverwaltung & Ordnerzugriff
    """

    def __init__(
        self,
        trainer: VokabelTrainer,
        on_settings_changed: Callable[[], None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._trainer = trainer
        self._on_settings_changed = on_settings_changed
        self._settings = load_settings()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(24)

        title = QLabel("Einstellungen")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setAccessibleName(" Einstellungen")
        root.addWidget(title)

        # ── Karte 1: Abfrage & Lernmodus ─────────────────────────────────────
        card_query = QFrame()
        card_query.setObjectName("settingsCard")
        card_query.setStyleSheet("""
            QFrame#settingsCard {
                background-color: #161922;
                border: 1px solid #2a2d3e;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        q_layout = QVBoxLayout(card_query)
        q_layout.setSpacing(14)

        q_head = QLabel("Abfrage & Lernrichtung")
        q_head.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        q_head.setStyleSheet("color: #7986e0;")
        q_layout.addWidget(q_head)

        desc = QLabel(
            "Hier kannst du festlegen, ob Vokabeln zufällig in beide Richtungen oder "
            "strikt in einer festen Richtung abgefragt werden (z. B. nur Englisch vorgeben und auf Deutsch antworten)."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #8b90a8; font-size: 13px;")
        q_layout.addWidget(desc)

        # Checkbox: In einer Richtung aktivieren
        self._direction_cb = QCheckBox("Abfrage in einer Richtung aktivieren (feste Richtung)")
        self._direction_cb.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self._direction_cb.setAccessibleName(" Abfrage in einer Richtung aktivieren")
        self._direction_cb.clicked.connect(self._on_direction_toggle_clicked)
        q_layout.addWidget(self._direction_cb)

        # Status & Erklärung
        self._status_box = QFrame()
        self._status_box.setStyleSheet("background-color: #1e2130; border-radius: 6px; padding: 12px;")
        status_layout = QVBoxLayout(self._status_box)
        status_layout.setSpacing(6)

        self._status_lbl = QLabel()
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setFont(QFont("Segoe UI", 13))
        self._status_lbl.setAccessibleName(" Aktuelle Abfragerichtung")
        status_layout.addWidget(self._status_lbl)

        self._status_detail_lbl = QLabel()
        self._status_detail_lbl.setWordWrap(True)
        self._status_detail_lbl.setStyleSheet("color: #8b90a8; font-size: 12px;")
        status_layout.addWidget(self._status_detail_lbl)

        q_layout.addWidget(self._status_box)

        # Button: Richtung konfigurieren
        btn_row = QHBoxLayout()
        self._btn_configure_dir = QPushButton("⚙  Abfragerichtung konfigurieren …")
        self._btn_configure_dir.setObjectName("primaryBtn")
        self._btn_configure_dir.setAutoDefault(False)
        self._btn_configure_dir.setDefault(False)
        self._btn_configure_dir.setAccessibleName(" Abfragerichtung konfigurieren")
        self._btn_configure_dir.clicked.connect(self._open_direction_dialog)
        btn_row.addWidget(self._btn_configure_dir)
        btn_row.addStretch()
        q_layout.addLayout(btn_row)

        root.addWidget(card_query)

        # ── Karte 2: Braillezeile & Buchstabier-Dauer ─────────────────────────
        card_braille = QFrame()
        card_braille.setObjectName("settingsCard")
        card_braille.setStyleSheet("""
            QFrame#settingsCard {
                background-color: #161922;
                border: 1px solid #2a2d3e;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        b_layout = QVBoxLayout(card_braille)
        b_layout.setSpacing(14)

        b_head = QLabel("Braillezeile & Anzeigezeiten")
        b_head.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        b_head.setStyleSheet("color: #7986e0;")
        b_layout.addWidget(b_head)

        b_desc = QLabel(
            "Hier legst du fest, wie viele Sekunden das Buchstabierte und die Lösung "
            "bei falschen Antworten auf der Braillezeile und dem Bildschirm angezeigt werden soll. "
            "Die Eingabe erfolgt in Sekunden direkt über die Tastatur (kein ungenauer Schieberegler)."
        )
        b_desc.setWordWrap(True)
        b_desc.setStyleSheet("color: #8b90a8; font-size: 13px;")
        b_layout.addWidget(b_desc)

        spin_row = QHBoxLayout()
        spin_row.setSpacing(12)
        spin_lbl = QLabel("ANZEIGEDAUER IN SEKUNDEN:")
        spin_lbl.setObjectName("sectionLabel")
        self._spelling_spin = QSpinBox()
        self._spelling_spin.setRange(1, 60)
        self._spelling_spin.setSingleStep(1)
        self._spelling_spin.setSuffix(" Sekunden")
        self._spelling_spin.setFixedWidth(160)
        self._spelling_spin.setAccessibleName(
            " Anzeigedauer für Buchstabieren und Fehlerkorrektur auf der Braillezeile in Sekunden. Zahl direkt über Tastatur eintippen."
        )
        self._spelling_spin.valueChanged.connect(self._on_spelling_duration_changed)
        spin_lbl.setBuddy(self._spelling_spin)
        spin_row.addWidget(spin_lbl)
        spin_row.addWidget(self._spelling_spin)
        spin_row.addStretch()
        b_layout.addLayout(spin_row)

        b_hint = QLabel(
            "💡 Tipp: Du kannst die Zahl direkt über die Tastatur eintippen. "
            "Mit der Enter-Taste kannst du während der Abfrage jederzeit sofort weitergehen, "
            "ohne die Wartezeit abwarten zu müssen."
        )
        b_hint.setWordWrap(True)
        b_hint.setStyleSheet("color: #7986e0; font-size: 12px;")
        b_layout.addWidget(b_hint)

        root.addWidget(card_braille)

        # ── Karte 3: ℹ️ Formatierungen, Befehle & Easter Egg ─────────────────
        card_info = QFrame()
        card_info.setObjectName("settingsCard")
        card_info.setStyleSheet("""
            QFrame#settingsCard {
                background-color: #161922;
                border: 1px solid #2a2d3e;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        i_layout = QVBoxLayout(card_info)
        i_layout.setSpacing(14)

        i_head = QLabel("ℹ️   Formatierungs-Regeln & Tastaturbefehle")
        i_head.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        i_head.setStyleSheet("color: #4caf7d;")
        i_head.setAccessibleName(" Informationsfeld: Formatierungs-Regeln und Tastaturbefehle")
        i_layout.addWidget(i_head)

        info_box = QFrame()
        info_box.setObjectName("infoBox")
        info_box.setStyleSheet("""
            QFrame#infoBox {
                background-color: #131728;
                border: 1px solid #2e3460;
                border-left: 4px solid #7986e0;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        ib_layout = QVBoxLayout(info_box)
        ib_layout.setSpacing(12)

        guide_text = QLabel(
            "<b>1. Vokabel- & Antwort-Formatierungen:</b><br/>"
            "• <b>(Klammerzusätze):</b> z. B. <i>(ab)halten</i> ➔ Sowohl <i>abhalten</i> als auch <i>halten</i> gelten als richtig.<br/>"
            "• <b>Schrägstriche:</b> z. B. <i>ein/e</i> ➔ Sowohl <i>ein</i> als auch <i>eine</i> werden anerkannt.<br/>"
            "• <b>Synonyme & Alternativen:</b> Mit Komma trennen (z. B. <i>Haus, Heim</i>). Jedes Wort wird als volle Antwort gewertet.<br/>"
            "• <b>Automatische Tippfehler-Toleranz:</b> 1 Buchstabendreher bei Wörtern ab 4 Zeichen und 2 bei Wörtern ab 8 Zeichen werden verziehen.<br/>"
            "• <b>Artikel & Stoppwörter:</b> Artikel wie <i>der, die, das, the, a</i> oder Partikel <i>to</i> können flexibel mitgelernt oder weggelassen werden.<br/><br/>"
            "<b>2. Datei-Importformate:</b><br/>"
            "• <b>Word (.docx):</b> Tabellen oder Textzeilen mit Bindestrich werden automatisch sauber erkannt.<br/>"
            "• <b>TXT / CSV:</b> Jede Zeile im Format <code>Vorderseite - Rückseite</code> oder mit Semikolon getrennt.<br/><br/>"
            "<div style='background-color: #232038; border: 1px solid #f0a500; border-radius: 6px; padding: 10px; margin: 4px 0;'>"
            "<b style='color: #f0c040;'>⭐ GEHEIMER ENTWICKLER-TIPP (EASTER EGG):</b><br/>"
            "<span style='color: #e8eaf0;'>"
            "Wer sich die Anleitung gründlich durchliest, wird belohnt: Wenn du bei einer beliebigen Vokabelabfrage als Antwort "
            "<b>!superbrain</b> eingibst (oder die Tastenkombination <b>Strg + Shift + E</b> drückst), "
            "schaltest du das geheime Easter Egg frei! Du erhältst sofort die Meister-Fanfare, goldenes Feedback und 100% Erfolgsquote für die Karte!"
            "</span>"
            "</div><br/>"
            "<b>3. Wichtige Tastaturbefehle & Barrierefreiheit:</b><br/>"
            "• <b>Enter:</b> Antworten bestätigen, Weitergehen, alle Schaltflächen und Kontrollkästchen direkt aktivieren.<br/>"
            "• <b>Strg + F:</b> Schnellsuche in der Vokabelverwaltung mit sofortigen Suchvorschlägen.<br/>"
            "• <b>Strg + Z:</b> Zuletzt gelöschte Vokabeln mit einem Tastendruck wiederherstellen.<br/>"
            "• <b>Tab / Umschalt + Tab:</b> Nahtloser Fokuswechsel zwischen allen Feldern und Tabellenelementen.<br/>"
            "• <b>Entf:</b> Ausgewählte Vokabel aus der Verwaltungstabelle löschen.<br/>"
            "• <b>Strg + Shift + E:</b> Das geheime Meister-Easter-Egg aufrufen!"
        )
        guide_text.setTextFormat(Qt.TextFormat.RichText)
        guide_text.setWordWrap(True)
        guide_text.setStyleSheet("color: #c0c5d8; font-size: 13px; line-height: 1.5;")
        guide_text.setAccessibleName(
            " Formatierungs-Anleitung und Befehle. Enthält Regeln für Klammern, Schrägstriche, Word-Import, Tastaturkürzel und das geheime Superbrain Easter Egg."
        )
        ib_layout.addWidget(guide_text)

        i_layout.addWidget(info_box)
        root.addWidget(card_info)

        # ── Karte 3: Daten & Speicherort ─────────────────────────────────────
        card_data = QFrame()
        card_data.setObjectName("settingsCard")
        card_data.setStyleSheet("""
            QFrame#settingsCard {
                background-color: #161922;
                border: 1px solid #2a2d3e;
                border-radius: 10px;
                padding: 20px;
            }
        """)
        data_layout = QVBoxLayout(card_data)
        data_layout.setSpacing(12)

        data_head = QLabel("Datenbank & Anwendungsordner")
        data_head.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        data_head.setStyleSheet("color: #f0a500;")
        data_layout.addWidget(data_head)

        self._data_stats_lbl = QLabel()
        self._data_stats_lbl.setStyleSheet("color: #e8eaf0; font-size: 13px;")
        data_layout.addWidget(self._data_stats_lbl)

        path_lbl = QLabel(f"Speicherort: {APP_DIR}")
        path_lbl.setWordWrap(True)
        path_lbl.setStyleSheet("color: #8b90a8; font-size: 12px; font-family: Consolas, monospace;")
        data_layout.addWidget(path_lbl)

        btn_data_row = QHBoxLayout()
        open_folder_btn = QPushButton("📂  Speicherordner im Explorer öffnen")
        open_folder_btn.setObjectName("secondaryBtn")
        open_folder_btn.setAutoDefault(False)
        open_folder_btn.setDefault(False)
        open_folder_btn.setAccessibleName(" Speicherordner im Windows Explorer öffnen")
        open_folder_btn.clicked.connect(self._open_data_folder)
        btn_data_row.addWidget(open_folder_btn)
        btn_data_row.addStretch()
        data_layout.addLayout(btn_data_row)

        root.addWidget(card_data)
        root.addStretch()

        scroll.setWidget(container)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def refresh(self) -> None:
        """Aktualisiert alle Anzeigen basierend auf den aktuellen Einstellungen."""
        self._settings = load_settings()
        is_enabled = bool(self._settings.get("direction_enabled", False))

        self._direction_cb.blockSignals(True)
        self._direction_cb.setChecked(is_enabled)
        self._direction_cb.blockSignals(False)

        cat_cfg = self._settings.get("categories", {}).get("Sprache", {})
        q_lang = cat_cfg.get("question_lang", "Englisch")
        a_lang = cat_cfg.get("answer_lang", "Deutsch")

        if is_enabled:
            self._status_lbl.setText(f"🟢  Feste Richtung aktiv: {q_lang}  ➔  {a_lang}")
            self._status_lbl.setStyleSheet("color: #69db7c; font-weight: bold;")
            self._status_detail_lbl.setText(
                f"Es werden Vokabeln auf {q_lang} vorgegeben und die Übersetzung auf {a_lang} abgefragt."
            )
            self._btn_configure_dir.setEnabled(True)
        else:
            self._status_lbl.setText("⚪  Zufällige Richtung (Gemischt)")
            self._status_lbl.setStyleSheet("color: #8b90a8; font-weight: bold;")
            self._status_detail_lbl.setText(
                "Die Abfragerichtung wechselt automatisch zufällig hin und her (beide Richtungen werden trainiert)."
            )
            self._btn_configure_dir.setEnabled(True)

        self._spelling_spin.blockSignals(True)
        self._spelling_spin.setValue(self._settings.get("spelling_duration_seconds", 8))
        self._spelling_spin.blockSignals(False)

        vok_count = len(self._trainer.vokabeln)
        kat_count = len(self._trainer.get_kategorien())
        self._data_stats_lbl.setText(f"Gespeichert: {vok_count} Vokabeln in {kat_count} Kategorien.")

    def _on_spelling_duration_changed(self, value: int) -> None:
        """Wird aufgerufen, wenn der Benutzer die Anzeigedauer ändert."""
        self._settings["spelling_duration_seconds"] = value
        save_settings(self._settings)
        if callable(self._on_settings_changed):
            self._on_settings_changed()

    def _on_direction_toggle_clicked(self) -> None:
        """Wird aufgerufen, wenn der Benutzer die Checkbox anklickt."""
        new_state = self._direction_cb.isChecked()
        if new_state:
            # Wie vom Benutzer gewünscht: Wenn man es aktiviert, soll direkt das Fenster aufploppen!
            dlg = DirectionSettingsDialog(self._trainer, self._settings, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                self._settings = dlg.get_settings()
                self._settings["direction_enabled"] = True
                save_settings(self._settings)
            else:
                # Wurde abgebrochen -> Checkbox zurücksetzen
                self._direction_cb.setChecked(False)
                return
        else:
            self._settings["direction_enabled"] = False
            save_settings(self._settings)

        self.refresh()
        if callable(self._on_settings_changed):
            self._on_settings_changed()

    def _open_direction_dialog(self) -> None:
        """Öffnet den Konfigurationsdialog."""
        dlg = DirectionSettingsDialog(self._trainer, self._settings, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._settings = dlg.get_settings()
            save_settings(self._settings)
            self.refresh()
            if callable(self._on_settings_changed):
                self._on_settings_changed()

    def _open_data_folder(self) -> None:
        """Öffnet den Datenordner im Windows Explorer."""
        try:
            if sys.platform == "win32":
                os.startfile(APP_DIR)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(APP_DIR)])
            else:
                subprocess.Popen(["xdg-open", str(APP_DIR)])
        except Exception as exc:
            logger.error("Fehler beim Öffnen des Ordners %s: %s", APP_DIR, exc)
            QMessageBox.warning(self, "Hinweis", f"Ordner konnte nicht geöffnet werden:\n{APP_DIR}")


__all__ = [
    "SETTINGS_FILE",
    "DEFAULT_SETTINGS",
    "load_settings",
    "save_settings",
    "get_direction_for_vocab",
    "DirectionSettingsDialog",
    "EinstellungenView",
]
