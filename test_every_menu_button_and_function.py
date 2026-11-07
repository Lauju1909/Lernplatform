import ast
import ctypes
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import MagicMock

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Provide lightweight PyQt6 shim if running in a Python environment without PyQt6 installed
try:
    import PyQt6.QtWidgets  # noqa: F401
except ImportError:
    class _DynamicQtModule(types.ModuleType):
        def __getattr__(self, name):
            return MagicMock

    sys.modules["PyQt6"] = _DynamicQtModule("PyQt6")
    sys.modules["PyQt6.QtCore"] = _DynamicQtModule("PyQt6.QtCore")
    sys.modules["PyQt6.QtGui"] = _DynamicQtModule("PyQt6.QtGui")
    sys.modules["PyQt6.QtWidgets"] = _DynamicQtModule("PyQt6.QtWidgets")

import backend
from backend import Vokabel, VokabelTrainer
import abfrage
import import_funktionen


def test_rust_core_dll_ffi():
    dll_path = BASE_DIR / "lernplatform_core.dll"
    assert dll_path.is_file(), "lernplatform_core.dll must exist"

    dll = ctypes.CDLL(str(dll_path))
    dll.rust_lp_levenshtein.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    dll.rust_lp_levenshtein.restype = ctypes.c_uint32
    dll.rust_lp_similarity_percent.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    dll.rust_lp_similarity_percent.restype = ctypes.c_uint32
    dll.rust_lp_calc_weight.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
    dll.rust_lp_calc_weight.restype = ctypes.c_double
    dll.rust_lp_file_hash.argtypes = [ctypes.c_char_p]
    dll.rust_lp_file_hash.restype = ctypes.c_uint64

    assert dll.rust_lp_levenshtein(b"Rechnung", b"rechnung") == 0
    assert dll.rust_lp_levenshtein(b"Katze", b"Kaze") == 1
    assert dll.rust_lp_similarity_percent(b"invoice", b"invoice") == 100
    assert dll.rust_lp_similarity_percent(b"entrepreneur", b"enterpreneur") >= 80

    w_new = dll.rust_lp_calc_weight(0, 0, 0)
    w_hard = dll.rust_lp_calc_weight(0, 4, 0)
    w_easy = dll.rust_lp_calc_weight(8, 0, 4)
    assert w_hard > w_new > w_easy

    vok_file = str(BASE_DIR / "vokabeln.json").encode("utf-8")
    h1 = dll.rust_lp_file_hash(vok_file)
    h2 = dll.rust_lp_file_hash(vok_file)
    assert h1 != 0 and h1 == h2


def test_vokabel_trainer_crud_categories_leitner_and_undo():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        vok_file = tmp_path / "vokabeln.json"
        kat_file = tmp_path / "kategorien.json"
        vok_file.write_text("[]", encoding="utf-8")
        kat_file.write_text("{}", encoding="utf-8")

        orig_data = backend.DATA_FILE
        orig_kat = backend.KATEGORIEN_FILE
        try:
            backend.DATA_FILE = vok_file
            backend.KATEGORIEN_FILE = kat_file

            trainer = VokabelTrainer()
            initial_count = len(trainer.vokabeln)

            # 1. Add vocabulary item
            v = trainer.add_vokabel(
                front="accessibility",
                back="Barrierefreiheit",
                kategorie="Sprache",
                lang_front="Englisch",
                lang_back="Deutsch",
            )
            assert v is not None
            assert len(trainer.vokabeln) == initial_count + 1

            # Duplicate prevention
            assert trainer.add_vokabel("accessibility", "Barrierefreiheit", "Sprache") is None

            # 2. Record quiz result & verify Leitner weight update
            w_initial = v.weight
            trainer.record_result(v, is_correct=True)
            assert v.attempts == 1 and v.correct == 1
            assert v.score == 100.0
            assert v.weight < w_initial

            # 3. Get next card with streak protection
            card = trainer.get_next_card("Sprache")
            assert isinstance(card, Vokabel)

            # 4. Custom category creation & deletion
            ok = trainer.add_kategorie(
                name="IT-Begriffe",
                icon="💻",
                beschreibung="Computer & Technik",
                frage_front="Was heißt:",
                frage_back="Wie nennt man:",
                lbl_front="Englisch",
                lbl_back="Deutsch",
            )
            assert ok is True
            assert "IT-Begriffe" in trainer.get_kategorie_namen()
            assert trainer.delete_kategorie("IT-Begriffe") is True

            # 5. Delete & 30-step Undo stack
            trainer.delete_vokabel(v)
            assert len(trainer.vokabeln) == initial_count
            assert trainer.can_undo() is True
            restored = trainer.undo_last_delete()
            assert restored == 1
            assert len(trainer.vokabeln) == initial_count + 1
        finally:
            backend.DATA_FILE = orig_data
            backend.KATEGORIEN_FILE = orig_kat


def test_abfrage_fuzzy_matching_brackets_slashes_and_synonyms():
    assert abfrage.damerau_levenshtein("haus", "huas") == 1
    assert abfrage.damerau_levenshtein("test", "test") == 0
    assert abfrage.max_allowed_typos(3) == 0
    assert abfrage.max_allowed_typos(5) == 1
    assert abfrage.max_allowed_typos(10) == 2

    # Exact match
    assert abfrage.check_answer("Apfel", "Apfel") == (True, False)
    # Article tolerance
    assert abfrage.check_answer("die Schule", "Schule")[0] is True
    # Bracket expansion
    assert abfrage.check_answer("walk", "(to) walk")[0] is True
    assert abfrage.check_answer("to walk", "(to) walk")[0] is True
    # Slash form expansion
    assert abfrage.check_answer("Lehrerin", "Lehrer/in")[0] is True
    assert abfrage.check_answer("Lehrer", "Lehrer/in")[0] is True
    # Synonym matching
    assert abfrage.check_answer("Gebäude", "Haus, Gebäude")[0] is True
    # Typo tolerance on longer words
    ok, is_typo = abfrage.check_answer("Entreprenur", "Entrepreneur")
    assert ok is True and is_typo is True


def test_all_ui_modules_buttons_menus_and_accessibility_labels():
    ui_files = [
        "main.py",
        "abfrage.py",
        "kategorien.py",
        "verwaltung.py",
        "einstellungen.py",
        "import_funktionen.py",
        "style.py",
    ]
    total_buttons_found = 0
    total_methods_found = 0

    for fname in ui_files:
        fpath = BASE_DIR / fname
        assert fpath.is_file(), f"Missing UI module: {fname}"
        source = fpath.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=fname)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                total_methods_found += 1
            elif isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name == "QPushButton":
                    total_buttons_found += 1

    assert total_buttons_found >= 20, f"Expected >=20 QPushButtons across UI modules, found {total_buttons_found}"
    assert total_methods_found >= 60, f"Expected >=60 methods across UI modules, found {total_methods_found}"
