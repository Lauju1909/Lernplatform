# 🤖 Hinweise für KI-Agenten (AI Agents Guide)

## ⚡ Automatisiertes Build-, Auto-Versioning- und Release-System
- **Automatische Versionserhöhung:** Die Versionsnummer in `version.json` wird bei jedem Push auf den Branch `main` **vollautomatisch durch GitHub Actions erhöht** (z. B. `1.2.2` -> `1.2.3`).
- **Automatischer Multi-Plattform Build (Windows & Linux):**
  - **Windows:** GitHub Actions kompiliert auf `windows-latest` automatisch `dist/Lernplatform.exe` über PyInstaller.
  - **Linux:** GitHub Actions kompiliert auf `ubuntu-latest` automatisch `dist/Lernplatform-Linux` über PyInstaller.
- **Automatisches GitHub-Release:** Für jeden Commit auf `main` wird automatisch ein neues GitHub-Release erstellt und die Windows- sowie Linux-Binaries als Download angehängt.
- **Barrierefreiheit (PyQt6 & Screenreader):**
  - Auf Windows: Vollständige NVDA/JAWS-Unterstützung über Windows UIAutomation.
  - Auf Linux: Native AT-SPI2 / Orca-Kompatibilität über Qt Accessibility.

## 📌 Was KI-Agenten beachten MÜSSEN:
1. **Keine manuellen Releases oder Versionsnummern-Änderungen erzwingen:** Features und Bugfixes normal committen. Nach dem Push auf `main` übernimmt GitHub Actions das Hochzählen der Patch-Version, das Taggen und das Veröffentlichen des Releases vollautomatisch.
2. **Barrierefreiheit gewähren:** Immer AccessibleName, AccessibleDescription, Tastaturnavigation und Damerau-Levenshtein-Toleranz beibehalten.
