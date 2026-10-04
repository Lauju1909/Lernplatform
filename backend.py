# backend.py – Datenmodell, Persistenz, Konfiguration & Lernalgorithmus (Trainer)
"""
Dieses Modul verwaltet die gesamte Datenhaltung, Konfiguration und Lernlogik:
- AppDir-Ermittlung (automatisch lokaler Ordner oder %LOCALAPPDATA%)
- Kategorien-Konfiguration und Standardsprachen
- Vokabel-Datenmodell mit Score- und Gewichtungsberechnung
- Persistenz: Laden & atomares Speichern von JSON-Dateien
- Volle Kompatibilität zu Klartext-JSON und alten Base64+zlib (DEFLATE) Dateien
- VokabelTrainer: Verwaltung von Vokabeln, Kategorien, gewichteter Zufallsauswahl,
  2er-Streak-Schutz und 30-stufigem Undo-Stapel.
"""
from __future__ import annotations

import base64
import json
import os
import random
import shutil
import sys
import time
import zlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# ── Speicherort für Anwendungsdaten ───────────────────────────────────────────
def _get_app_dir() -> Path:
    """Ermittelt das Datenverzeichnis:
    1. Wenn der Ordner der .exe / des Skripts beschreibbar ist (Desktop, USB-Stick, Projektordner),
       wird direkt dieser Ordner als Speicherort genutzt, damit die JSON-Dateien direkt bei der .exe liegen.
    2. Andernfalls (z. B. C:\\Program Files) Ausweichordner in %LOCALAPPDATA%\\Lernplatform.
    """
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
    else:
        exe_dir = Path(__file__).resolve().parent

    try:
        test = exe_dir / ".write_test"
        test.touch()
        test.unlink()
        return exe_dir
    except Exception:
        local_app = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Lernplatform"
        local_app.mkdir(parents=True, exist_ok=True)
        return local_app


APP_DIR: Path = _get_app_dir()
DATA_FILE: Path = APP_DIR / "vokabeln.json"
KATEGORIEN_FILE: Path = APP_DIR / "kategorien.json"
LAST_SAVED_MTIME: float = 0.0
LAST_SAVED_TIME: float = 0.0


# ── Häufig genutzte Sprachen ──────────────────────────────────────────────────
STANDARD_SPRACHEN: list[str] = [
    "Englisch", "Deutsch", "Französisch", "Spanisch", "Italienisch",
    "Latein", "Russisch", "Japanisch", "Chinesisch", "Türkisch",
    "Portugiesisch", "Niederländisch", "Griechisch", "Polnisch", "Arabisch",
]


# ── Standard-Kategorien mit Fragetext für Vorder- und Rückseite ───────────────
DEFAULT_KATEGORIEN: dict[str, dict[str, str]] = {
    "Sprache": {
        "icon":         "🌍",
        "beschreibung": "Fremdwörter und Übersetzungen",
        "frage_front":  "Wie lautet die Übersetzung von:",
        "frage_back":   "In welcher Sprache heißt der Begriff:",
        "lbl_front":    "Fremdsprache",
        "lbl_back":     "Zielsprache",
    },
    "Fachwörter": {
        "icon":         "📚",
        "beschreibung": "Fachbegriffe und ihre Bedeutung",
        "frage_front":  "Was bedeutet der Begriff:",
        "frage_back":   "Welcher Begriff beschreibt folgendes:",
        "lbl_front":    "Fachbegriff",
        "lbl_back":     "Bedeutung",
    },
    "Formeln": {
        "icon":         "🔬",
        "beschreibung": "Formeln und ihre Anwendung",
        "frage_front":  "Erkläre die Formel:",
        "frage_back":   "Welche Formel beschreibt folgendes:",
        "lbl_front":    "Formel",
        "lbl_back":     "Beschreibung",
    },
    "Befehle": {
        "icon":         "💻",
        "beschreibung": "Tastenkürzel und was sie machen",
        "frage_front":  "Was macht das Tastenkürzel:",
        "frage_back":   "Welches Tastenkürzel macht folgendes:",
        "lbl_front":    "Tastenkürzel",
        "lbl_back":     "Was sie machen",
    },
}


def load_kategorien() -> dict[str, dict[str, str]]:
    """Lädt Standard- und benutzerdefinierte Kategorien aus kategorien.json."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    kats: dict[str, dict[str, str]] = {k: dict(v) for k, v in DEFAULT_KATEGORIEN.items()}
    if KATEGORIEN_FILE.exists():
        try:
            with open(KATEGORIEN_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                kats.update(saved)
        except Exception:
            pass
    return kats


def save_kategorien(kategorien: dict[str, dict[str, str]]) -> None:
    """Speichert benutzerdefinierte Kategorien atomar in JSON."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    custom = {k: v for k, v in kategorien.items() if k not in DEFAULT_KATEGORIEN or v != DEFAULT_KATEGORIEN[k]}
    tmp_file = KATEGORIEN_FILE.with_suffix(".json.tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(custom, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, KATEGORIEN_FILE)
    except Exception:
        if tmp_file.exists():
            tmp_file.unlink(missing_ok=True)
        raise


KATEGORIEN: dict[str, dict[str, str]] = load_kategorien()
KATEGORIE_NAMEN: list[str] = list(KATEGORIEN.keys())


# ── Standard-Beispielvokabeln für den ersten Start ────────────────────────────
DEFAULT_VOKABELN: list[dict[str, Any]] = [
    {"front": "apple",                     "back": "Apfel",                              "kategorie": "Sprache",    "lang_front": "Englisch", "lang_back": "Deutsch", "attempts": 0, "correct": 0},
    {"front": "house",                     "back": "Haus",                               "kategorie": "Sprache",    "lang_front": "Englisch", "lang_back": "Deutsch", "attempts": 0, "correct": 0},
    {"front": "Photosynthese",             "back": "Pflanzen erzeugen mit Licht Zucker", "kategorie": "Fachwörter", "lang_front": "",         "lang_back": "",        "attempts": 0, "correct": 0},
    {"front": "E = mc²",                   "back": "Masse-Energie-Äquivalenz (Einstein)","kategorie": "Formeln",    "lang_front": "",         "lang_back": "",        "attempts": 0, "correct": 0},
    {"front": "a² + b² = c²",              "back": "Satz des Pythagoras",                "kategorie": "Formeln",    "lang_front": "",         "lang_back": "",        "attempts": 0, "correct": 0},
    {"front": "Windows + D",               "back": "Desktop anzeigen",                   "kategorie": "Befehle",    "lang_front": "",         "lang_back": "",        "attempts": 0, "correct": 0},
    {"front": "Insert + F7",               "back": "Linkliste öffnen in JAWS",           "kategorie": "Befehle",    "lang_front": "",         "lang_back": "",        "attempts": 0, "correct": 0},
    {"front": "Insert + Pfeil nach unten", "back": "Alles vorlesen ab Cursor in JAWS",   "kategorie": "Befehle",    "lang_front": "",         "lang_back": "",        "attempts": 0, "correct": 0},
]


# ── Datenmodell: Vokabel ───────────────────────────────────────────────────────
@dataclass
class Vokabel:
    """Repräsentiert eine einzelne Lernkarte."""
    front:      str
    back:       str
    kategorie:  str = "Sprache"
    lang_front: str = "Englisch"  # Sprache der Vorderseite (linke Spalte)
    lang_back:  str = "Deutsch"   # Sprache der Rückseite (rechte Spalte)
    attempts:   int = 0           # Anzahl Abfragen
    correct:    int = 0           # Anzahl richtige Antworten

    @property
    def score(self) -> float:
        """Erfolgsquote 0.0–100.0 Prozent. Bei neuen Vokabeln 0.0.
        Wird auf [0, 100] begrenzt, um bei fehlerhaften Rohdaten keinen Überlauf zu erzeugen.
        """
        if self.attempts <= 0:
            return 0.0
        raw = (self.correct / self.attempts) * 100.0
        return round(min(100.0, max(0.0, raw)), 1)

    @property
    def weight(self) -> float:
        """Gewicht für die Zufallsauswahl: schwächere Vokabeln erhalten ein höheres Gewicht.
        Minimum 1.0, damit random.choices() niemals mit nicht-positiven Gewichten fehlschlägt.
        """
        return max(1.0, (100.0 - self.score) + 10.0)

    def to_dict(self) -> dict[str, Any]:
        """Serialisiert die Vokabel in ein Dictionary für JSON."""
        return {
            "front":      self.front,
            "back":       self.back,
            "kategorie":  self.kategorie,
            "lang_front": self.lang_front,
            "lang_back":  self.lang_back,
            "attempts":   self.attempts,
            "correct":    self.correct,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Vokabel:
        """Deserialisiert eine Vokabel mit voller Abwärts- und Formatkompatibilität.
        Unterstützt:
        - Standard-Format: front, back, kategorie, lang_front, lang_back, attempts, correct
        - Legacy-Vokabeltrainer: en, de, abfragen, score_prozent
        - Alternative Feldnamen: vorderseite/rueckseite, wort/uebersetzung, term/definition, question/answer
        - Automatische Spracherkennung aus Feldnamen (en, fr, es, la, it)
        """
        attempts = max(0, int(d.get("attempts", d.get("abfragen", 0))))

        if "correct" in d:
            try:
                correct = max(0, int(d["correct"]))
            except (ValueError, TypeError):
                correct = 0
        elif "score_prozent" in d:
            try:
                sp = float(d["score_prozent"])
                correct = max(0, int(round(attempts * sp / 100.0)))
            except (ValueError, TypeError):
                correct = 0
        else:
            correct = 0

        front = (
            d.get("front") or d.get("en") or d.get("vorderseite") or
            d.get("wort") or d.get("word") or d.get("question") or
            d.get("frage") or d.get("term") or d.get("begriff") or ""
        )
        back = (
            d.get("back") or d.get("de") or d.get("rueckseite") or
            d.get("uebersetzung") or d.get("translation") or d.get("answer") or
            d.get("antwort") or d.get("definition") or d.get("bedeutung") or ""
        )

        lang_front = d.get("lang_front")
        lang_back = d.get("lang_back")
        if not lang_front or not lang_back:
            if "en" in d and "de" in d:
                lang_front, lang_back = "Englisch", "Deutsch"
            elif "fr" in d and "de" in d:
                lang_front, lang_back = "Französisch", "Deutsch"
            elif "es" in d and "de" in d:
                lang_front, lang_back = "Spanisch", "Deutsch"
            elif "la" in d and "de" in d:
                lang_front, lang_back = "Latein", "Deutsch"
            elif "it" in d and "de" in d:
                lang_front, lang_back = "Italienisch", "Deutsch"
            else:
                lang_front = lang_front or "Englisch"
                lang_back = lang_back or "Deutsch"

        kategorie = d.get("kategorie", "Sprache")

        return cls(
            front=str(front).strip(),
            back=str(back).strip(),
            kategorie=str(kategorie).strip() or "Sprache",
            lang_front=str(lang_front).strip() or "Englisch",
            lang_back=str(lang_back).strip() or "Deutsch",
            attempts=attempts,
            correct=correct,
        )


# ── Persistenz & Datei-Parser ─────────────────────────────────────────────────
def _extract_dict_list(parsed: object) -> list[dict[str, Any]]:
    """Extrahiert eine Liste von Dictionaries aus einem beliebigen JSON-Objekt."""
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    if isinstance(parsed, dict):
        for key in ("vokabeln", "vocabularies", "words", "cards", "items", "data", "cards_list"):
            if key in parsed and isinstance(parsed[key], list):
                return [x for x in parsed[key] if isinstance(x, dict)]
    return []


def _parse_vokabel_file(file_path: Path) -> list[Vokabel]:
    """Liest und dekodiert eine Vokabeldatei – unterstützt Klartext-JSON,
    in Dictionaries verschachtelte Listen sowie Base64 + zlib (DEFLATE)
    komprimierte Dateien alter Vokabeltrainer.
    """
    _MAX_JSON_SIZE = 50 * 1024 * 1024  # 50 MB Limit für importierte JSON-Dateien

    if not file_path.exists():
        return []
    try:
        stat = file_path.stat()
        if stat.st_size == 0:
            return []
        if stat.st_size > 50 * 1024 * 1024:  # 50 MB
            return []
        raw_bytes = file_path.read_bytes()
    except Exception:
        return []

    # 1. Versuch: Direkt als JSON dekodieren
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw_bytes.decode(enc).strip()
            if text.startswith(("[", "{")):
                parsed = json.loads(text)
                items = _extract_dict_list(parsed)
                if items:
                    voks = [Vokabel.from_dict(d) for d in items if isinstance(d, dict)]
                    valid_voks = [v for v in voks if v.front and v.back]
                    if valid_voks:
                        return valid_voks
        except Exception:
            continue

    # 2. Versuch: Base64 + zlib (DEFLATE) Dekomprimierung (Format alter Vokabeltrainer)
    try:
        clean_b64 = raw_bytes.strip()
        decoded = base64.b64decode(clean_b64)
        decompressed = zlib.decompress(decoded)
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                dec_text = decompressed.decode(enc).strip()
                if dec_text.startswith(("[", "{")):
                    parsed = json.loads(dec_text)
                    items = _extract_dict_list(parsed)
                    if items:
                        voks = [Vokabel.from_dict(d) for d in items if isinstance(d, dict)]
                        valid_voks = [v for v in voks if v.front and v.back]
                        if valid_voks:
                            return valid_voks
            except Exception:
                continue
    except Exception:
        pass

    return []


def load_vokabeln() -> list[Vokabel]:
    """Lädt Vokabeln aus der JSON-Datei.
    Prüft:
    1. DATA_FILE (vokabeln.json im App-Verzeichnis)
    2. Ordner der .exe (falls DATA_FILE abweicht)
    3. Durchsucht das Verzeichnis nach anderen hineingeschobenen *.json-Dateien
    """
    APP_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Standard-Datei (DATA_FILE) laden falls vorhanden
    if DATA_FILE.exists():
        voks = _parse_vokabel_file(DATA_FILE)
        if voks:
            return voks

    # 2. Ordner der EXE prüfen (falls DATA_FILE abweichend)
    exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    exe_vok = exe_dir / "vokabeln.json"
    if exe_vok != DATA_FILE and exe_vok.exists():
        voks = _parse_vokabel_file(exe_vok)
        if voks:
            return voks

    # 3. Durchsuche den Ordner nach anderen vorhandenen JSON-Dateien
    search_dirs = [APP_DIR]
    if exe_dir not in search_dirs:
        search_dirs.append(exe_dir)

    for sdir in search_dirs:
        if not sdir.exists():
            continue
        candidates = sorted(sdir.glob("*.json"), key=lambda p: (0 if "vokabel" in p.name.lower() else 1, p.name))
        for cand in candidates:
            if cand.name.lower() in ("kategorien.json", "kategorien.json.tmp", "vokabeln.json.tmp"):
                continue
            if cand == DATA_FILE:
                continue
            voks = _parse_vokabel_file(cand)
            if voks:
                return voks

    return []


def save_vokabeln(vokabeln: list[Vokabel]) -> None:
    """Speichert alle Vokabeln atomar in die JSON-Datei.
    Schreibt zuerst in eine temporäre Datei und ersetzt dann die Originaldatei —
    so bleibt die Datenbank auch bei einem Stromausfall oder Absturz intakt.
    Aktualisiert LAST_SAVED_MTIME zur Vermeidung von Fehlalarmen beim Datei-Watcher.
    """
    global LAST_SAVED_MTIME, LAST_SAVED_TIME
    APP_DIR.mkdir(parents=True, exist_ok=True)
    tmp_file = DATA_FILE.with_suffix(".json.tmp")
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump([v.to_dict() for v in vokabeln], f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, DATA_FILE)
        try:
            LAST_SAVED_MTIME = DATA_FILE.stat().st_mtime
            LAST_SAVED_TIME = time.time()
        except Exception:
            pass
    except Exception:
        if tmp_file.exists():
            tmp_file.unlink(missing_ok=True)
        raise


# ── Lernalgorithmus: VokabelTrainer ──────────────────────────────────────────
class VokabelTrainer:
    """Zentrale Trainer-Klasse zur Verwaltung des Vokabelbestands, der Lernabfragen
    und der Kategorien mit Undo-Historie.
    """
    def __init__(self) -> None:
        self.kategorien: dict[str, dict[str, str]] = load_kategorien()
        self.vokabeln: list[Vokabel] = load_vokabeln()
        self._undo_stack: deque[list[Vokabel]] = deque(maxlen=30)

    def reload_vokabeln(self) -> int:
        """Lädt Vokabeln und Kategorien neu von der Festplatte."""
        self.kategorien = load_kategorien()
        self.vokabeln = load_vokabeln()
        KATEGORIEN.clear()
        KATEGORIEN.update(self.kategorien)
        KATEGORIE_NAMEN.clear()
        KATEGORIE_NAMEN.extend(self.kategorien.keys())
        return len(self.vokabeln)

    def add_kategorie(
        self,
        name: str,
        icon: str,
        beschreibung: str,
        frage_front: str,
        frage_back: str,
        lbl_front: str = "Vorderseite",
        lbl_back: str = "Rückseite",
    ) -> bool:
        """Legt eine neue benutzerdefinierte Kategorie an."""
        clean_name = name.strip()[:200]  # Max 200 Zeichen für Kategorienamen
        if not clean_name or clean_name in self.kategorien:
            return False
        self.kategorien[clean_name] = {
            "icon":         icon.strip() or "🏷️",
            "beschreibung": beschreibung.strip() or "Eigene Kategorie",
            "frage_front":  frage_front.strip() or "Was bedeutet:",
            "frage_back":   frage_back.strip() or "Welcher Begriff beschreibt folgendes:",
            "lbl_front":    lbl_front.strip() or "Vorderseite",
            "lbl_back":     lbl_back.strip() or "Rückseite",
        }
        KATEGORIEN.clear()
        KATEGORIEN.update(self.kategorien)
        KATEGORIE_NAMEN.clear()
        KATEGORIE_NAMEN.extend(self.kategorien.keys())
        save_kategorien(self.kategorien)
        return True

    def delete_kategorie(self, name: str) -> bool:
        """Löscht eine benutzerdefinierte Kategorie und alle darin enthaltenen Vokabeln."""
        if name not in self.kategorien:
            return False
        deleted_voks = [v for v in self.vokabeln if v.kategorie == name]
        if deleted_voks:
            self._push_undo(deleted_voks)
        del self.kategorien[name]
        self.vokabeln = [v for v in self.vokabeln if v.kategorie != name]
        save_vokabeln(self.vokabeln)
        KATEGORIEN.clear()
        KATEGORIEN.update(self.kategorien)
        KATEGORIE_NAMEN.clear()
        KATEGORIE_NAMEN.extend(self.kategorien.keys())
        save_kategorien(self.kategorien)
        return True

    def get_custom_kategorien(self) -> dict[str, dict[str, str]]:
        """Gibt alle benutzerdefinierten (löschbaren) Kategorien zurück."""
        return {k: v for k, v in self.kategorien.items() if k not in DEFAULT_KATEGORIEN}

    def get_kategorien(self) -> dict[str, dict[str, str]]:
        return dict(self.kategorien)

    def get_kategorie_namen(self) -> list[str]:
        return list(self.kategorien.keys())

    def get_kategorie_info(self, name: str) -> dict[str, str]:
        if name in self.kategorien:
            return self.kategorien[name]
        return DEFAULT_KATEGORIEN.get(name, {
            "icon": "🏷️",
            "beschreibung": "",
            "frage_front": "Was bedeutet:",
            "frage_back": "Welcher Begriff beschreibt folgendes:",
            "lbl_front": "Vorderseite",
            "lbl_back": "Rückseite",
        })

    def is_duplicate(self, front: str, kategorie: str, lang_front: str = "Englisch") -> bool:
        """Prüft, ob eine Vokabel mit gleicher Vorderseite in dieser Kategorie schon existiert."""
        target = front.strip().lower()
        for v in self.vokabeln:
            if v.kategorie == kategorie and v.front.lower() == target:
                if kategorie != "Sprache" or v.lang_front.lower() == lang_front.strip().lower():
                    return True
        return False

    def get_reversed_lang_pair(self, lang_front: str, lang_back: str) -> tuple[str, str] | None:
        """Gibt die existierende Richtung zurück, wenn die umgekehrte Kombination schon genutzt wird."""
        lf = lang_front.strip().lower()
        lb = lang_back.strip().lower()
        for v in self.vokabeln:
            if v.kategorie == "Sprache":
                vf = v.lang_front.strip().lower()
                vb = v.lang_back.strip().lower()
                if vf == lb and vb == lf:
                    return (v.lang_front.strip(), v.lang_back.strip())
        return None

    def get_most_used_lang_pair(self) -> tuple[str, str]:
        """Gibt die am häufigsten genutzte Sprachkombi (lang_front, lang_back) zurück."""
        counts: dict[tuple[str, str], int] = {}
        for v in self.vokabeln:
            if v.kategorie == "Sprache" and v.lang_front and v.lang_back:
                key = (v.lang_front.strip(), v.lang_back.strip())
                counts[key] = counts.get(key, 0) + 1
        if not counts:
            return ("Englisch", "Deutsch")
        return max(counts.items(), key=lambda item: item[1])[0]

    # Maximale Feldlängen – verhindert extrem lange Eingaben
    _MAX_FIELD_LEN: int = 2000
    _MAX_LANG_LEN: int = 100
    _MAX_KAT_LEN: int = 200

    def add_vokabel(
        self,
        front: str,
        back: str,
        kategorie: str = "Sprache",
        lang_front: str = "Englisch",
        lang_back: str = "Deutsch",
    ) -> Vokabel | None:
        """Fügt eine neue Vokabel hinzu. Gibt None zurück, falls sie bereits existiert."""
        clean_front = front.strip()[: self._MAX_FIELD_LEN]
        clean_back = back.strip()[: self._MAX_FIELD_LEN]
        clean_kat = str(kategorie).strip()[: self._MAX_KAT_LEN] or "Sprache"
        clean_lf = lang_front.strip()[: self._MAX_LANG_LEN] or "Englisch"
        clean_lb = lang_back.strip()[: self._MAX_LANG_LEN] or "Deutsch"
        if not clean_front or not clean_back:
            return None
        if self.is_duplicate(clean_front, clean_kat, clean_lf):
            return None
        vok = Vokabel(
            front=clean_front,
            back=clean_back,
            kategorie=clean_kat,
            lang_front=clean_lf,
            lang_back=clean_lb,
        )
        self.vokabeln.append(vok)
        self.save()
        return vok

    def _push_undo(self, deleted: list[Vokabel]) -> None:
        """Legt gelöschte Vokabeln auf den Undo-Stapel (maximal 30 Schritte, O(1))."""
        if deleted:
            self._undo_stack.append(list(deleted))  # deque(maxlen=30) entfernt älteste Einträge automatisch

    def can_undo(self) -> bool:
        """Prüft, ob gelöschte Vokabeln wiederhergestellt werden können."""
        return len(self._undo_stack) > 0

    def undo_last_delete(self) -> int:
        """Stellt die zuletzt gelöschten Vokabeln wieder her."""
        if not self._undo_stack:
            return 0
        to_restore = self._undo_stack.pop()
        restored_count = 0
        for v in to_restore:
            if not self.is_duplicate(v.front, v.kategorie, v.lang_front):
                self.vokabeln.append(v)
                restored_count += 1
        if restored_count > 0:
            self.save()
        return restored_count

    def delete_vokabel(self, vokabel: Vokabel) -> None:
        """Einzelne Vokabel löschen."""
        if vokabel in self.vokabeln:
            self.vokabeln.remove(vokabel)
            self._push_undo([vokabel])
            self.save()

    def delete_vokabeln(self, to_delete: list[Vokabel]) -> None:
        """Mehrere Vokabeln gleichzeitig löschen."""
        actually_deleted: list[Vokabel] = []
        for v in to_delete:
            if v in self.vokabeln:
                self.vokabeln.remove(v)
                actually_deleted.append(v)
        if actually_deleted:
            self._push_undo(actually_deleted)
            self.save()

    def delete_all(self, kategorie: str | None = None) -> None:
        """Alle Vokabeln (oder alle einer bestimmten Kategorie) löschen."""
        if kategorie:
            actually_deleted = [v for v in self.vokabeln if v.kategorie == kategorie]
            self.vokabeln = [v for v in self.vokabeln if v.kategorie != kategorie]
        else:
            actually_deleted = list(self.vokabeln)
            self.vokabeln = []
        if actually_deleted:
            self._push_undo(actually_deleted)
            self.save()

    def save(self) -> None:
        """Speichert den aktuellen Stand atomar in JSON."""
        save_vokabeln(self.vokabeln)

    def get_pool(self, kategorie: list[str] | set[str] | str | None = None) -> list[Vokabel]:
        """Gibt Vokabeln zurück, optional nach Kategorie(n) gefiltert."""
        if kategorie is None:
            return list(self.vokabeln)
        if isinstance(kategorie, str):
            return [v for v in self.vokabeln if v.kategorie == kategorie]
        kat_set = set(kategorie)
        return [v for v in self.vokabeln if v.kategorie in kat_set]

    def get_next_card(
        self,
        kategorie: list[str] | set[str] | str | None = None,
        exclude: Vokabel | None = None,
    ) -> Vokabel:
        """Wählt per gewichtetem Zufallsprinzip die nächste Karte (schwächere Vokabeln häufiger).
        Streak-Schutz verhindert, dass dieselbe Karte dreimal hintereinander kommt.
        """
        pool = self.get_pool(kategorie)
        if not pool:
            msg = "in den ausgewählten Kategorien" if isinstance(kategorie, (list, set)) else (f"in {kategorie}" if kategorie else "")
            raise ValueError(f"Keine Vokabeln {msg} vorhanden.".strip())
        if exclude is not None:
            filtered = [v for v in pool if v is not exclude]
            if filtered:
                pool = filtered
        weights = [v.weight for v in pool]
        return random.choices(pool, weights=weights, k=1)[0]

    def record_result(self, vokabel: Vokabel, is_correct: bool) -> None:
        """Ergebnis erfassen und sofort persistent speichern."""
        vokabel.attempts += 1
        if is_correct:
            vokabel.correct += 1
        self.save()
