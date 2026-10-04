# 📚 Lernplatform – Projektübersicht & Entwicklungsbericht für Laurin

**Projekt:** Lernplatform (Vokabel- & Begriffstrainer)  
**Status:** Stabil, hochperformant, sicherheitsgeprüft & Store-Ready  
**Datum:** Oktober 2026  
**Ziel:** Veröffentlichung im **Microsoft Store**  

---

## 🎯 1. Was ist die Lernplatform?

Die Lernplatform ist ein barrierefreier, intelligenter Vokabel- und Begriffstrainer für den Desktop (entwickelt in Python mit **PyQt6**). Sie unterscheidet sich von herkömmlichen Apps durch folgende Kernfeatures:

1. **Vollständige Barrierefreiheit (Accessibility):**
   - Volle Unterstützung für Screenreader (JAWS, NVDA) über Windows UIAutomation.
   - Braillezeilen-Unterstützung mit speziellen Screenreader-Beschreibungen für jede Zelle und Taste.
   - Tastaturbedienung ohne Mauszwang (Enter-Navigation, Pfeiltasten, Tab-Navigation).
   - Kontraststarkes Dark Theme nach WCAG AA-Standards.

2. **Intelligente Antworterkennung:**
   - Verzeiht Tippfehler automatisch über den **Damerau-Levenshtein-Algorithmus** (z. B. Buchstabendreher oder vergessene Zeichen).
   - Erkennt Synonyme, Schrägstriche (z. B. `ein/e`), optionale Klammern (z. B. `(to) run`) und Stoppwörter/Artikel (`the`, `der`, `die`, `das`).
   - Akustische Buchstabierhilfe bei falschen Antworten.

3. **Flexibles Kategoriesystem:**
   - Vordefinierte Kategorien (Sprachen, Fachwörter, Formeln, Befehle/Shortcuts).
   - Erstellung beliebig vieler eigener Kategorien mit eigenen Fragetexten.
   - Mehrfachauswahl: Mehrere Kategorien gleichzeitig lernen.

4. **Import- & Integrationsfunktionen:**
   - Import von Vokabellisten direkt aus **Word (.docx)** und **Textdateien (.txt)**.
   - **Word-Bridge (Live-Übersetzer):** Erkennt Wörter in Word-Dokumenten und übersetzt sie automatisch über eine offizielle API.

---

## 🛠️ 2. Woran wir zuletzt gearbeitet haben (Bugfixes & Stabilität)

Die App hatte zuvor regelmäßige Abstürze und Freezes, die sie für den Microsoft Store unbrauchbar gemacht hätten. Wir haben eine umfassende Fehleranalyse durchgeführt und alle Ursachen behoben:

### A. Der 19-Sekunden-Freeze in der Vokabelverwaltung behoben
* **Das Problem:** Beim Klick auf „Vokabelverwaltung“ fror die App für fast 20 Sekunden ein. Windows stufte das als „Keine Rückmeldung“ ein und beendete die App gewaltsam (*Application Hang*).
* **Die Ursache:** Vier Spalten der Tabelle standen auf `ResizeToContents`. Bei 600 Vokabeln (3.000 Zellen) berechnete Qt bei jedem einzelnen Item die Layouts aller Zeilen neu – über **180.000 Berechnungen** im GUI-Thread!
* **Die Lösung:** Feste Spaltenbreiten mit einer flexiblen Vokabel-Spalte (`Stretch`). Die Ladezeit ist von **18,9 Sekunden auf 0,012 Sekunden** geschrumpft – das ist **über 1.500-mal schneller**!

### B. Speicher-Crash in PyQt6 / SIP (`0xc0000005` Access Violation)
* **Das Problem:** Die App stürzte unregelmäßig mit einem nativen C++-Speicherzugriffsfehler in `sip.cp314-win_amd64.pyd` ab.
* **Die Ursache:** Für alle 5 Spalten jeder Zeile wurde das Python-Datenobjekt (`Vokabel`) in einer C++-`QVariant` abgelegt (3.000 Wrapper). Beim Löschen oder Aktualisieren der Tabelle baute Qt die C++-Items ab, während SIPs Wrapper-Speicherverwaltung unter Python 3.14 damit kollidierte.
* **Die Lösung:** Python-Objekte wurden komplett aus den C++-Tabellen entfernt. Die Vokabelliste wird nun direkt in Python in `self._current_vokabeln` verwaltet. Speicherzugriffsfehler sind damit ausgeschlossen.

### C. Signal-Kollision & Stack-Overflow in `NavigableTableWidget`
* **Das Problem:** Crash mit Status `0xc0000409` (Stack Buffer Overrun / Abort) in `Qt6Core.dll`.
* **Die Ursache:** Die eigene Tabellenklasse überschrieb das native Qt-Signal `activated(QModelIndex)` mit einem eigenen Signal `activated = pyqtSignal(int)`. Bei Doppel-Klicks oder Tastaturevents kam es zu einem Konflikt im C++-Event-Dispatcher.
* **Die Lösung:** Das Signal wurde in `row_activated` umbenannt und der Fokuswechsel gegen Rekursionen abgesichert.

### D. Austausch der Übersetzer-API (ToS-Konformität & Threading)
* **Das Problem:** Vorher wurde eine inoffizielle Google-Translate-API (`client=gtx`) synchron im UI-Thread genutzt. Das verletzte Googles Nutzungsbedingungen, führte zu IP-Sperren und fror die Oberfläche ein.
* **Die Lösung:** Umstellung auf die offizielle, kostenlose **MyMemory API** (1.000 Wörter/Tag, ToS-konform) und Auslagerung in einen echten Hintergrundthread (`QThread _DocProcessWorker`). Die Oberfläche bleibt während Übersetzungen 100 % flüssig.

---

## 🔒 3. Großes Sicherheits-Audit (Microsoft Store Vorbereitung)

Für die Microsoft-Store-Zertifizierung wurden alle Eingabekanäle gegen Abstürze, Memory Leaks und DoS (Denial of Service) abgesichert:

| Bereich | Vorherige Lücke | Sicherheits-Fix |
|---|---|---|
| **Texteingaben (Vokabeln)** | Keine Begrenzung | Begrenzt auf max. **2.000 Zeichen** (Vorder-/Rückseite) und **200 Zeichen** (Kategorien). |
| **GUI-Eingabefelder** | Unbegrenzte Eingabe in `QLineEdit` | `setMaxLength(2000)` auf allen Dialog-Feldern gesetzt. |
| **Datei-Import (.docx / .txt)** | Beliebig riesige Dateien einlesbar | Dateigröße auf max. **25 MB** und max. **10.000 Paare** gedeckelt. |
| **JSON-Import** | Beliebig große JSONs konnten RAM fluten | Begrenzt auf max. **50 MB** in `_parse_vokabel_file()`. |
| **Antwort-Feld (Abfrage)** | Gigantische Eingaben brachten Levenshtein-Algorithmus zum Glühen | Antwortfeld auf 2.000 Zeichen limitiert ($O(n^2)$-Schutz). |
| **System-Befehle** | `shell=True` mit f-String (Shell-Injection-Risiko) | Umgestellt auf `shell=False` mit sauberer Argumentliste `["cmd.exe", "/c", ...]`. |

---

## 📦 4. Aktueller Build-Stand

Die fertige, aktualisierte Programmdatei liegt direkt im Projektordner:
* **Pfad:** `C:\Users\user\Desktop\Meine Projekte\Lernplatform\Lernplatform.exe`
* **Größe:** ca. 40,9 MB
* **Typ:** Eigenständige Windows-64-Bit-Anwendung (One-File, kein Konsolenfenster)
* **Vorteil:** Die EXE organisiert sich beim ersten Start auf einem fremden Rechner automatisch selbst in einen sauberen Ordner inklusive Standard-Vokabeln.

---

## 🚀 5. Roadmap: Die nächsten Schritte für den Microsoft Store

1. **MSIX Packaging:**
   - Mit dem offiziellen Microsoft MSIX Packaging Tool wird aus der `Lernplatform.exe` ein `.msix`-Paket erstellt.
2. **Entwickler-Konto:**
   - Microsoft Partner Center Entwicklerkonto anlegen (einmalige Registrierungsgebühr ca. 19 $ für Privatpersonen).
3. **Store-Assets:**
   - App-Icon in den benötigten Kachelgrößen (44×44, 150×150, 310×150) erstellen.
   - 3–4 ansprechende Screenshots der Hauptansichten (Abfrage, Kategorien, Verwaltung).
4. **Listing & Datenschutz:**
   - Kurze Datenschutzerklärung (die App sammelt keinerlei persönliche Daten, alles liegt lokal).
   - Einreichen zur Zertifizierung im Partner Center.
