# VokabelMeister 📖

> **Barrierefreier schriftlicher Vokabel- und Begriffstrainer für Windows (PyQt6)**  
> *100% barrierefrei für Blinde & Sehbehinderte (NVDA & JAWS) – Reine schriftliche Abfrage zum aktiven Trainieren der Rechtschreibung*

---

## 🌟 Über VokabelMeister

**VokabelMeister** ist ein spezialisierter Trainer für Fremdsprachen, Fachbegriffe, Formeln und Tastaturkürzel. Im Gegensatz zu reinen Multiple-Choice-Trainern setzt VokabelMeister auf das **aktive Eintippen der Antwort** (schriftliche Abfrage).

### ✨ Hauptfunktionen

* **✍️ Reine schriftliche Abfrage ("Nur schriftlich"):** Fördert die aktive Erinnerung und präzise Rechtschreibung durch direktes Eintippen der Lösung.
* **🧠 Intelligente Fehlertoleranz (Damerau-Levenshtein):**
  * Erkennt Buchstabendreher und kleine Tippfehler automatisch.
  * Weist mit *"Fast richtig (Tippfehler)"* gezielt auf die korrekte Schreibweise hin, ohne frustrierend abzustrafen.
* **🧩 Fortgeschrittene Mustererkennung:**
  * **Klammern:** Erkennt optionale Zusätze wie `(quer) über` und akzeptiert sowohl `über` als auch `quer über`.
  * **Schrägstriche:** Löst Formen wie `ein/e`, `Erwachsene/r` oder `der/die/das` automatisch in alle gültigen Varianten auf.
  * **Synonyme:** Mehrere Bedeutungen (getrennt durch Komma, Semikolon oder "oder") werden flexibel erkannt.
* **♿ Barrierefreiheit für Screenreader (NVDA / JAWS):**
  * Spezielles `AccessibleQuestionInput`-Eingabefeld, das bei Fokus stets die aktuelle Frage bzw. Rückmeldung für den Screenreader ansagt.
  * Vollständig per Tastatur bedienbar (Eingabe mit <kbd>Enter</kbd> prüfen, <kbd>Leertaste</kbd> zum Aufdecken).
* **📚 Vielseitige Kategorien:**
  * 🌍 **Sprache:** Fremdsprachenvokabeln (Englisch, Französisch, Spanisch, Latein etc.)
  * 📚 **Fachwörter:** Fachbegriffe und Definitionen
  * 🔬 **Formeln:** Formeln und mathematisch-naturwissenschaftliche Erklärungen
  * 💻 **Befehle:** Tastaturkürzel und ihre Funktionen (inkl. Screenreader-Befehle)
  * ➕ **Eigene Kategorien:** Beliebig viele neue Kategorien anlegen
* **📥 Universal-Import:** Importiere eigene Listen direkt aus **Word (.docx)** oder Textdateien (.txt, .csv).
* **🔒 100% Offline & Lokal:** Daten werden sicher in `%LOCALAPPDATA%\VokabelMeister\` gespeichert.

---

## 💾 Download (Windows EXE)

Die fertige Windows-Anwendung kann direkt unter [Releases](https://github.com/Lauju1909/VokabelMeister/releases) heruntergeladen werden:
* **`VokabelMeister.exe`** – Standalone-Anwendung ohne Installation. Einfach doppelklicken und loslegen!

---

## 🛠️ Entwicklung & Ausführung aus dem Quellcode

```bash
# Virtuelle Umgebung erstellen und aktivieren
python -m venv venv
venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# VokabelMeister starten
python main.py
```

---

## 📜 Lizenz
MIT License © 2026 Lauri
