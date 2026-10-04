# abfrage.py – Vokabel-Abfrage, Lernkarten-View & Intelligente Antworterkennung
"""
Dieses Modul bündelt das gesamte Abfrage-Feature der Lernplatform:
1. Intelligente Antworterkennung & Fehlertoleranz:
   - Damerau-Levenshtein Distanzberechnung für automatisches Verzeihen von Tippfehlern
   - Erweiterung von Klammerzusätzen und Schrägstrichformen (z. B. "ein/e", "(in)", "/r/s")
   - Toleranz gegenüber Artikeln und Stoppwörtern ("the", "der", "die", "das")
   - Mehrwort- und Synonymabgleich
2. AbfrageView:
   - Barrierefreies Karten-Layout mit natürlicher Satzfragengenerierung
   - Direkte Enter-Bedienung (ohne störende Mausbenutzung)
   - Screenreader-optimierte Audioausgabe mit automatischer Buchstabierung bei Fehlern
"""
from __future__ import annotations

import logging
import random
import re
import time
from typing import Any

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from backend import Vokabel, VokabelTrainer
from einstellungen import DirectionSettingsDialog, get_direction_for_vocab, load_settings
from style import AccessibleQuestionInput, _motivation

logger = logging.getLogger(__name__)


# ── Intelligente Antworterkennung & Fehlertoleranz ────────────────────────────
STOPWORDS: set[str] = {
    "der", "die", "das", "ein", "eine", "einer", "eines", "einem", "einen",
    "the", "a", "an", "to", "of", "in", "on", "at", "by", "for", "with", "mit",
    "und", "and", "or", "oder", "sich", "zu", "von", "aus", "den", "dem", "des",
}


def damerau_levenshtein(s1: str, s2: str) -> int:
    """Berechnet die Damerau-Levenshtein-Distanz (Einfügen, Löschen, Ersetzen, Dreher)."""
    d: dict[tuple[int, int], int] = {}
    len1, len2 = len(s1), len(s2)
    for i in range(-1, len1 + 1):
        d[(i, -1)] = i + 1
    for j in range(-1, len2 + 1):
        d[(-1, j)] = j + 1
    for i in range(len1):
        for j in range(len2):
            cost = 0 if s1[i] == s2[j] else 1
            d[(i, j)] = min(
                d[(i - 1, j)] + 1,
                d[(i, j - 1)] + 1,
                d[(i - 1, j - 1)] + cost,
            )
            if i > 0 and j > 0 and s1[i] == s2[j - 1] and s1[i - 1] == s2[j]:
                d[(i, j)] = min(d[(i, j)], d[(i - 2, j - 2)] + 1)
    return d[(len1 - 1, len2 - 1)]


def max_allowed_typos(word_len: int) -> int:
    """Erlaubte Tippfehler: 0 bei <=3 Zeichen, 1 bei 4-7 Zeichen, 2 bei >=8 Zeichen."""
    if word_len <= 3:
        return 0
    if word_len <= 7:
        return 1
    return 2


def clean_matching_str(s: str) -> str:
    """Bereinigt Klammern, Satzzeichen und vereinheitlicht Leerzeichen."""
    s = re.sub(r"[\(\)\[\]\{\}<>\u201e\u201c\"\'\`\u00b4]", "", s)
    s = re.sub(r"[.,!?;:]", " ", s)
    s = re.sub(r"\s*([+=])\s*", r" \1 ", s)
    return " ".join(s.lower().split())


def _expand_brackets(text: str) -> set[str]:
    """Generiert alle Kombinationen von Klammer-Inhalten (mit Inhalt / ohne Inhalt)."""
    pattern = re.compile(r"[\(\[\{]([^\)\]\}]*)[\)\]\}]")

    def _recurse(curr: str) -> set[str]:
        m = pattern.search(curr)
        if not m:
            return {curr}
        content = m.group(1)
        start, end = m.span()
        opt_a = curr[:start] + content + curr[end:]
        opt_b = curr[:start] + curr[end:]
        res = _recurse(opt_a) | _recurse(opt_b)
        if "-" in content:
            opt_c = curr[:start] + content.replace("-", "") + curr[end:]
            res |= _recurse(opt_c)
        return res

    raw_res = _recurse(text)
    out: set[str] = set()
    for r in raw_res:
        cleaned = " ".join(r.split())
        if cleaned:
            out.add(cleaned)
    return out


def _expand_slash_forms(text: str) -> set[str]:
    """Erweitert Formen mit Schrägstrichen (z. B. thai(länder/in), ein/e, Erwachsene/r, der/die/das)."""
    forms = {text}
    m_in = re.search(r"(\w+)/in\b", text, re.IGNORECASE)
    if m_in:
        base = m_in.group(1)
        forms.add(text[:m_in.start()] + base + text[m_in.end():])
        forms.add(text[:m_in.start()] + base + "in" + text[m_in.end():])

    m_e = re.search(r"(\w+)/e\b", text, re.IGNORECASE)
    if m_e:
        base = m_e.group(1)
        forms.add(text[:m_e.start()] + base + text[m_e.end():])
        forms.add(text[:m_e.start()] + base + "e" + text[m_e.end():])

    m_rs = re.search(r"(\w+)/r/s\b", text, re.IGNORECASE)
    if m_rs:
        base = m_rs.group(1)
        forms.add(text[:m_rs.start()] + base + text[m_rs.end():])
        forms.add(text[:m_rs.start()] + base + "r" + text[m_rs.end():])
        forms.add(text[:m_rs.start()] + base + "s" + text[m_rs.end():])

    m_r_s = re.search(r"(\w+)r/s\b", text, re.IGNORECASE)
    if m_r_s:
        stem = m_r_s.group(1)
        forms.add(text[:m_r_s.start()] + stem + text[m_r_s.end():])
        forms.add(text[:m_r_s.start()] + stem + "r" + text[m_r_s.end():])
        forms.add(text[:m_r_s.start()] + stem + "s" + text[m_r_s.end():])

    m_r = re.search(r"(\w+)/r\b", text, re.IGNORECASE)
    if m_r:
        base = m_r.group(1)
        forms.add(text[:m_r.start()] + base + text[m_r.end():])
        forms.add(text[:m_r.start()] + base + "r" + text[m_r.end():])

    if "/" in text and not any([m_in, m_e, m_rs, m_r_s, m_r]):
        forms.add(text.replace("/", " "))
        slash_words = text.split("/")
        for w in slash_words:
            w_str = w.strip()
            if len(w_str) >= 2 or w_str in {"a", "i", "o", "u"}:
                forms.add(w_str)

    return {f.strip() for f in forms if f.strip()}


def get_answer_candidates(expected: str) -> tuple[list[str], list[str], list[str]]:
    """Erzeugt Kandidaten-Vollformen, Synonym-Teile und Einzelwörter aus der Musterlösung."""
    raw = expected.strip().lower()
    full_forms: set[str] = set()
    parts: set[str] = set()
    all_words: set[str] = set()

    bracket_variants = _expand_brackets(raw)

    for bv in bracket_variants:
        for sf in _expand_slash_forms(bv):
            c = clean_matching_str(sf)
            if c:
                full_forms.add(c)
                parts.add(c)
                for w in c.split():
                    all_words.add(w)

        sub_items = re.split(r"[,;]+|\s+-\s+|\boder\b|\bor\b", bv)
        for item in sub_items:
            for sf in _expand_slash_forms(item):
                c = clean_matching_str(sf)
                if c:
                    parts.add(c)
                    for w in c.split():
                        all_words.add(w)
            if "/" in item:
                for slash_p in item.split("/"):
                    c = clean_matching_str(slash_p)
                    if c:
                        parts.add(c)
                        for w in c.split():
                            all_words.add(w)

    return list(full_forms), list(parts), list(all_words)


def check_answer(user_input: str, expected: str) -> tuple[bool, bool]:
    """Prüft eine Benutzereingabe gegen die erwartete Antwort.
    Gibt (ist_richtig, ist_tippfehler_oder_teilantwort) zurück.
    """
    u_clean = clean_matching_str(user_input)
    if not u_clean:
        return False, False

    full_forms, parts, all_words = get_answer_candidates(expected)
    u_words = u_clean.split()

    # 1. Exakte Übereinstimmung mit Vollform oder Synonym-Teil
    if u_clean in full_forms or u_clean in parts:
        return True, False

    # 2. Ein einzelnes Wort von mehreren reicht (außer reine Stoppwörter)
    if len(u_words) == 1 and u_words[0] in all_words:
        if u_words[0] not in STOPWORDS:
            return True, False

    # 2b. Mehrere Wörter, aber nur Artikel/Stopwörter als Zusatz (z. B. "die Schule" für "Schule")
    if len(u_words) > 1:
        non_stop = [w for w in u_words if w not in STOPWORDS]
        if len(non_stop) == 1 and non_stop[0] in all_words:
            return True, False

    # 3. Beliebige Wortreihenfolge und Teilmengen (z. B. stellen legen tun)
    if len(u_words) >= 1:
        for p in list(full_forms) + list(parts):
            p_words = p.split()
            if len(p_words) > 1:
                if set(u_words) == set(p_words):
                    return True, False
                if len(u_words) > 1 and set(u_words).issubset(set(p_words)):
                    if any(w not in STOPWORDS for w in u_words):
                        return True, False

    # 4. Tippfehler-Erkennung (Fuzzy Matching)
    # 4a. Auf Vollformen oder Synonym-Teilen
    for target in list(full_forms) + list(parts):
        if not target:
            continue
        limit = max_allowed_typos(len(target))
        if limit > 0 and damerau_levenshtein(u_clean, target) <= limit:
            return True, True

    # 4b. Auf Einzelwörtern aus der Musterlösung
    if len(u_words) == 1:
        w = u_words[0]
        for tw in all_words:
            if tw in STOPWORDS:
                continue
            limit = max_allowed_typos(len(tw))
            if limit > 0 and damerau_levenshtein(w, tw) <= limit:
                return True, True

    # 4c. Mehrere Wörter mit Tippfehlern in beliebiger Reihenfolge
    if len(u_words) > 1:
        for p in list(full_forms) + list(parts):
            p_words = p.split()
            if len(p_words) == len(u_words):
                used_indices: set[int] = set()
                matched_all = True
                for uw in u_words:
                    found = False
                    for idx, pw in enumerate(p_words):
                        if idx in used_indices:
                            continue
                        lim = max_allowed_typos(len(pw))
                        if damerau_levenshtein(uw, pw) <= lim:
                            used_indices.add(idx)
                            found = True
                            break
                    if not found:
                        matched_all = False
                        break
                if matched_all:
                    return True, True

    return False, False


# ── Abfrage-View (Karten-Layout & Direkte Enter-Bedienung) ─────────────────────
class AbfrageView(QWidget):
    """Interaktive Lernansicht mit integrierten Satzfragen, gewichteter
    Zufallsauswahl und akustischer Rückmeldung für Screenreader.
    """
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
        self._settings: dict = load_settings()  # Gecacht – wird in refresh() aktualisiert
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 22, 32, 22)
        root.setSpacing(14)

        # 1. Header-Zeile (Kategorie-Badge links, Richtungsauswahl & Statistik rechts)
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        self._cat_badge = QLabel("")
        self._cat_badge.setObjectName("catBadge")
        self._cat_badge.setAccessibleName(" Aktive Kategorie")
        header_row.addWidget(self._cat_badge)

        self._dir_btn = QPushButton("🔀  Gemischt")
        self._dir_btn.setObjectName("dirBtn")
        self._dir_btn.setStyleSheet("""
            QPushButton#dirBtn {
                background-color: #1e2130;
                color: #7986e0;
                border: 1px solid #2e3460;
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton#dirBtn:hover {
                background-color: #262a3d;
                color: #9aa5f5;
                border: 1px solid #5c6bc0;
            }
        """)
        self._dir_btn.setAutoDefault(False)
        self._dir_btn.setDefault(False)
        self._dir_btn.setAccessibleName(" Abfragerichtung konfigurieren")
        self._dir_btn.clicked.connect(self._open_direction_dialog)
        header_row.addWidget(self._dir_btn)

        header_row.addStretch()

        self._stats_lbl = QLabel("0 richtig  |  0 falsch")
        self._stats_lbl.setObjectName("statsLabel")
        self._stats_lbl.setAccessibleName(" Statistik: 0 richtig, 0 falsch")
        header_row.addWidget(self._stats_lbl)
        root.addLayout(header_row)

        # 2. Haupt-Karten-Container
        self._card_frame = QFrame()
        self._card_frame.setObjectName("abfrageCard")
        card_layout = QVBoxLayout(self._card_frame)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(0)

        self._question_lbl = QLabel("")
        self._question_lbl.setObjectName("questionLabel")
        self._question_lbl.setWordWrap(True)
        self._question_lbl.setAccessibleName(" ")
        card_layout.addWidget(self._question_lbl)
        card_layout.addSpacing(32)

        self._input = AccessibleQuestionInput()
        self._input.returnPressed.connect(self._aktion)
        card_layout.addWidget(self._input)
        card_layout.addSpacing(50)

        self._hint_lbl = QLabel("💡 Drücke Enter zum Bestätigen und Weitergehen")
        self._hint_lbl.setObjectName("enterHint")
        self._hint_lbl.setAccessibleName(" ")
        card_layout.addWidget(self._hint_lbl)
        card_layout.addSpacing(22)

        self._feedback_lbl = QLabel("")
        self._feedback_lbl.setObjectName("feedbackLabel")
        self._feedback_lbl.setWordWrap(True)
        self._feedback_lbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._feedback_lbl.setAccessibleName(" ")
        self._feedback_lbl.hide()
        card_layout.addWidget(self._feedback_lbl)
        card_layout.addSpacing(14)

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
        if isinstance(kategorien, str):
            self._kategorien = [kategorien]
        elif isinstance(kategorien, (list, set)):
            self._kategorien = list(kategorien)
        else:
            self._kategorien = None
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

        if self._kategorien and len(self._kategorien) == 1:
            kat = self._kategorien[0]
            info = self._trainer.get_kategorie_info(kat)
            self._cat_badge.setText(f"{info.get('icon', '🏷️')}  {kat}  –  {info.get('beschreibung', '')}")
            self._cat_badge.setAccessibleName(f" Aktive Kategorie: {kat}")
        elif self._kategorien and len(self._kategorien) > 1:
            icons_str = "  ".join(self._trainer.get_kategorie_info(k).get("icon", "🏷️") + " " + k for k in self._kategorien)
            self._cat_badge.setText(f"🗂  {len(self._kategorien)} Kategorien: {icons_str}")
            self._cat_badge.setAccessibleName(f" {len(self._kategorien)} Kategorien aktiv: {', '.join(self._kategorien)}")
        else:
            self._cat_badge.setText("Alle Kategorien")
            self._cat_badge.setAccessibleName(" Alle Kategorien aktiv")

    def set_kategorie(self, kategorie: str | None) -> None:
        self.set_kategorien(kategorie)

    def refresh(self) -> None:
        self._settings = load_settings()  # Einstellungen aktualisieren
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
        self._input.setEnabled(True)
        self._hint_lbl.show()
        if self._aktuelle is None:
            self._lade_karte()
        else:
            settings = load_settings()
            if settings.get("direction_enabled", False):
                self._reverse = get_direction_for_vocab(self._aktuelle, settings)
                self._update_dir_btn(settings, self._aktuelle)
                kat_info = self._trainer.get_kategorie_info(self._aktuelle.kategorie)
                self._expected = self._aktuelle.front if self._reverse else self._aktuelle.back
                full_question = self._build_integrated_question(self._aktuelle, self._reverse, kat_info)
                self._question_lbl.setText(full_question)
                self._input.set_question(full_question)
            else:
                self._dir_btn.setText("🔀  Gemischt")
                self._dir_btn.setAccessibleName(" Abfragerichtung: Gemischt. Klicken zum Konfigurieren.")

    def _build_integrated_question(self, vok: Vokabel, reverse: bool, kat_info: dict[str, str]) -> str:
        if vok.kategorie == "Sprache":
            lf = vok.lang_front.strip() or "Englisch"
            lb = vok.lang_back.strip() or "Deutsch"
            if reverse:
                return f"Wie lautet die Übersetzung von \u201e{vok.back}\u201c auf {lf}?"
            return f"Wie lautet die Übersetzung von \u201e{vok.front}\u201c auf {lb}?"

        if vok.kategorie == "Befehle":
            if reverse:
                return f"Welches Tastenkürzel bewirkt: \u201e{vok.back}\u201c?"
            return f"Was macht das Tastenkürzel \u201e{vok.front}\u201c?"

        if vok.kategorie == "Fachwörter":
            if reverse:
                return f"Welcher Begriff beschreibt: \u201e{vok.back}\u201c?"
            return f"Was bedeutet der Fachbegriff \u201e{vok.front}\u201c?"

        if vok.kategorie == "Formeln":
            if reverse:
                return f"Wie lautet die Formel für: \u201e{vok.back}\u201c?"
            return f"Was bedeutet die Formel \u201e{vok.front}\u201c?"

        if reverse:
            raw_q = kat_info.get("frage_back", "Welcher Begriff beschreibt:").strip().rstrip(":?")
            return f"{raw_q}: \u201e{vok.back}\u201c?"
        raw_q = kat_info.get("frage_front", "Was bedeutet:").strip().rstrip(":?")
        return f"{raw_q} \u201e{vok.front}\u201c?"

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

            settings = self._settings
            if settings.get("direction_enabled", False):
                self._reverse = get_direction_for_vocab(self._aktuelle, settings)
                self._update_dir_btn(settings, self._aktuelle)
            else:
                if self._consecutive_dir_count >= 5:
                    neue_richtung = not self._reverse
                else:
                    neue_richtung = random.choice([False, True])

                if neue_richtung == self._reverse:
                    self._consecutive_dir_count += 1
                else:
                    self._reverse = neue_richtung
                    self._consecutive_dir_count = 1
                self._dir_btn.setText("🔀  Gemischt")
                self._dir_btn.setAccessibleName(" Abfragerichtung: Gemischt. Klicken zum Konfigurieren.")
        else:
            settings = self._settings
            if settings.get("direction_enabled", False):
                self._update_dir_btn(settings, self._aktuelle)
            else:
                self._dir_btn.setText("🔀  Gemischt")
                self._dir_btn.setAccessibleName(" Abfragerichtung: Gemischt. Klicken zum Konfigurieren.")

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

        # ── Geheimes Entwickler-Easter-Egg ──────────────────────────────────
        if text.lower() in ("!superbrain", "!easteregg", "!meister"):
            self._trainer.record_result(vok, True)
            self._session_total += 1
            self._session_richtig += 1
            self._update_stats()
            self._last_eval_time = time.time()
            self._waiting_for_next = True
            self._input.setReadOnly(True)
            self._motiv_lbl.setText("🚀 EASTER EGG FREIGESCHALTET! Meister-Status erreicht! ⭐⭐⭐")
            self._motiv_lbl.setStyleSheet("color: #f0c040; font-size: 18px; font-weight: bold;")
            self._motiv_lbl.show()
            vis_text = f"🌟 100% MEISTER-BONUS AKTIVIERT! (Lösung: {self._expected}) 🎉"
            audio_text = "Glückwunsch! Du hast das geheime Superhirn Easter Egg gefunden! 100 Prozent Meister-Bonus verliehen!"
            self._set_feedback(vis_text, "#f0c040", audio_text)
            self._wiederholen = False
            self._advance_timer.stop()
            self._advance_timer.start(8000)
            return

        try:
            richtig, is_fuzzy = check_answer(text, self._expected)
            self._trainer.record_result(vok, richtig)
        except Exception as exc:
            logger.error("Fehler beim Auswerten der Antwort: %s", exc, exc_info=True)
            self._set_feedback("⚠  Interner Fehler beim Auswerten.", "#f0a500", "Interner Fehler.")
            return

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
            total_wait_ms = 4000
            self._wiederholen = False
        else:
            spelling_sec = self._settings.get("spelling_duration_seconds", 8)
            buchstabiert = " - ".join(list(self._expected))
            vis_text = f"✗  Falsch.  Richtig: {self._expected}   ({buchstabiert})"
            audio_text = f"Falsch. {self._expected}. Buchstabiert: {buchstabiert}. {spruch}"
            self._set_feedback(vis_text, "#e05c5c", audio_text)
            total_wait_ms = max(2000, int(spelling_sec * 1000))
            self._wiederholen = True

        self._advance_timer.stop()
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

    def _update_dir_btn(self, settings: dict[str, Any], vok: Vokabel | None) -> None:
        """Aktualisiert die Beschriftung und Zugänglichkeit des Richtungs-Buttons."""
        if not vok:
            self._dir_btn.setText("⇄  Feste Richtung")
            return
        if vok.kategorie == "Sprache":
            cat_cfg = settings.get("categories", {}).get("Sprache", {})
            q = cat_cfg.get("question_lang", "Englisch")
            a = cat_cfg.get("answer_lang", "Deutsch")
            self._dir_btn.setText(f"⇄  {q} → {a}")
            self._dir_btn.setAccessibleName(
                f" Feste Abfragerichtung aktiv: Vorgegebene Sprache {q}, gesuchte Sprache {a}. Klicken zum Konfigurieren."
            )
        else:
            cat_cfg = settings.get("categories", {}).get(vok.kategorie, {})
            direction = cat_cfg.get("direction", "front_to_back")
            dir_text = "Vorderseite nach Rückseite" if direction == "front_to_back" else "Rückseite nach Vorderseite"
            short_dir = "Vor → Rück" if direction == "front_to_back" else "Rück → Vor"
            self._dir_btn.setText(f"⇄  {short_dir}")
            self._dir_btn.setAccessibleName(
                f" Feste Abfragerichtung für Kategorie {vok.kategorie} aktiv: {dir_text}. Klicken zum Konfigurieren."
            )

    def _open_direction_dialog(self) -> None:
        """Öffnet den barrierefreien Dialog zur Richtungs-Einstellung."""
        initial_kat = (
            self._kategorien[0]
            if (self._kategorien and len(self._kategorien) == 1)
            else (self._aktuelle.kategorie if self._aktuelle else "Sprache")
        )
        dlg = DirectionSettingsDialog(self._trainer, load_settings(), initial_kat=initial_kat, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

