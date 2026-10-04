# main.py – VokabelMeister Einstiegspunkt (PyQt6)

import os
import sys
from pathlib import Path

# Projektordner in Suchpfad aufnehmen
sys.path.insert(0, os.fspath(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication
from backend import VokabelTrainer
from frontend import MainWindow, STYLE


def main() -> None:
    # Trainer initialisieren (lädt Vokabeln automatisch aus JSON)
    trainer = VokabelTrainer()

    app = QApplication(sys.argv)
    app.setApplicationName("VokabelMeister")
    app.setOrganizationName("VokabelMeister")
    app.setStyleSheet(STYLE)

    window = MainWindow(trainer)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
