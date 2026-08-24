"""
pibackup_diagnose – Unittests fuer das Wayland/Qt-Diagnose-Skript.

Projekt:     pibackup_diagnose
Modul:       tests/test_pibackup_diagnose.py
Version:     1.1.0
Stand:       2026-08-24
Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.10)
Bezug:       requirements.txt (leer – Stdlib only)
Lizenz:      MIT
Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
Erstellt mit: Cursor Grok 4.6
Autor:       (FFHB) / RadioBBS

Beschreibung
------------
Prueft Bewertungsfunktionen und CLI von pibackup_diagnose ohne
einen Raspberry Pi zu benoetigen.

Historie
--------
Version 1.0.0 – 2026-08-24 – Tests ins eigene Projekt verschoben.
Version 1.1.0 – 2026-08-24 – Tests fuer PATH/--fix-path.

Aufruf / Nutzung
----------------
  python -m unittest tests.test_pibackup_diagnose
"""

from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pibackup_diagnose as diagnose  # noqa: E402
import project_meta as meta  # noqa: E402


class EvaluateTests(unittest.TestCase):
    """Bewertungen fuer Architektur, qtfix und Display."""

    def test_architecture_arm64_ok(self) -> None:
        """aarch64 gilt als unterstuetzte Zielarchitektur.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_architecture_arm64_ok()
        """
        result = diagnose.evaluate_architecture("aarch64")
        self.assertEqual(result.status, diagnose.STATUS_OK)

    def test_architecture_armhf_fail(self) -> None:
        """32-Bit-ARM wird abgelehnt.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_architecture_armhf_fail()
        """
        result = diagnose.evaluate_architecture("armv7l")
        self.assertEqual(result.status, diagnose.STATUS_FAIL)

    def test_qtfix_runtime_missing_as_root(self) -> None:
        """Fehlendes /run/user/0 unter root ist ein FAIL.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_qtfix_runtime_missing_as_root()
        """
        result = diagnose.evaluate_qtfix_runtime(False, True)
        self.assertEqual(result.status, diagnose.STATUS_FAIL)
        self.assertIn(meta.QTFIX_RUNTIME_DIR, result.detail)

    def test_forced_xcb_wayland_without_xwayland(self) -> None:
        """Wayland ohne XWayland blockiert die xcb-GUI.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_forced_xcb_wayland_without_xwayland()
        """
        result = diagnose.evaluate_forced_xcb("wayland", False)
        self.assertEqual(result.status, diagnose.STATUS_FAIL)

    def test_root_without_display_on_wayland(self) -> None:
        """root unter Wayland ohne DISPLAY ist ein FAIL.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_root_without_display_on_wayland()
        """
        result = diagnose.evaluate_root_display(True, "", "wayland-0", "wayland")
        self.assertEqual(result.status, diagnose.STATUS_FAIL)

    def test_sudo_strips_display(self) -> None:
        """Leeres DISPLAY unter sudo ist ein FAIL.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_sudo_strips_display()
        """
        result = diagnose.evaluate_sudo_env(True, False, {"DISPLAY": "", "WAYLAND_DISPLAY": ""}, ":0")
        self.assertEqual(result.status, diagnose.STATUS_FAIL)

    def test_ssh_without_display(self) -> None:
        """SSH ohne Display wird als FAIL erkannt.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_ssh_without_display()
        """
        result = diagnose.evaluate_ssh_session("10.0.0.2 11 10.0.0.3 22", "", "")
        self.assertEqual(result.status, diagnose.STATUS_FAIL)

    def test_wayland_socket_unreadable_for_root(self) -> None:
        """Root ohne Zugriff auf den User-Socket ist FAIL.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_wayland_socket_unreadable_for_root()
        """
        path = Path("/run/user/1000/wayland-0")
        result = diagnose.evaluate_wayland_socket(path, True, False, True)
        self.assertEqual(result.status, diagnose.STATUS_FAIL)


class CliTests(unittest.TestCase):
    """Kommandozeile und Berichtstexte."""

    def test_version_text_contains_meta(self) -> None:
        """--version enthaelt Nummer, Datum und Beschreibung.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei fehlendem Text.
        Beispiel:
            test_version_text_contains_meta()
        """
        text = diagnose.version_text()
        self.assertIn(meta.VERSION, text)
        self.assertIn(meta.STAND, text)
        self.assertIn(meta.BESCHREIBUNG, text)

    def test_help_lists_required_flags(self) -> None:
        """Hilfe listet --help, --version und --Ende.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei fehlender Option.
        Beispiel:
            test_help_lists_required_flags()
        """
        text = diagnose.help_text()
        self.assertIn("--help", text)
        self.assertIn("--version", text)
        self.assertIn("--Ende", text)
        self.assertIn("--probe", text)
        self.assertIn("--fix-path", text)
        self.assertIn("Typ:", text)
        self.assertIn("Beispiel:", text)

    def test_unknown_argument_exit_2(self) -> None:
        """Unbekannte Schalter enden mit Code 2.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei anderem Exitcode.
        Beispiel:
            test_unknown_argument_exit_2()
        """
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as ctx:
            with redirect_stderr(stderr):
                diagnose.parse_options(["--gibt-es-nicht"])
        self.assertEqual(ctx.exception.code, diagnose.EXIT_USAGE)
        self.assertIn("ungueltige Angaben", stderr.getvalue())

    def test_parse_log_file_enables_logging(self) -> None:
        """--log-file schaltet das Logging ein.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschen Options.
        Beispiel:
            test_parse_log_file_enables_logging()
        """
        options = diagnose.parse_options(["--log-file", "pibackup_diagnose.log"])
        self.assertTrue(options.log_enabled)
        self.assertEqual(options.log_file, Path("pibackup_diagnose.log"))

    def test_main_help_exit_0(self) -> None:
        """--help endet mit 0 und schreibt Hilfe.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei Exitcode oder leerer Ausgabe.
        Beispiel:
            test_main_help_exit_0()
        """
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = diagnose.main(["--help"])
        self.assertEqual(code, diagnose.EXIT_OK)
        self.assertIn("Verwendung:", stdout.getvalue())

    def test_next_steps_wayland(self) -> None:
        """Bei Wayland-FAIL kommt der xhost/sudo-Hinweis.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError wenn der Hinweis fehlt.
        Beispiel:
            test_next_steps_wayland()
        """
        items = [
            diagnose.item("qtfix", "QT_QPA_PLATFORM", diagnose.STATUS_FAIL, "xcb")
        ]
        steps = diagnose.next_steps_for(items, "wayland", False)
        joined = "\n".join(steps)
        self.assertIn("xhost", joined)
        self.assertIn("sudo python3 pibackup_diagnose.py", joined)

    def test_parse_sudo_env_filters_keys(self) -> None:
        """Nur Display-relevante Variablen werden aus env gelesen.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Filter.
        Beispiel:
            test_parse_sudo_env_filters_keys()
        """
        text = "HOME=/root\nDISPLAY=:0\nWAYLAND_DISPLAY=\nSECRET=nope\n"
        parsed = diagnose.parse_sudo_env(text)
        self.assertEqual(parsed["DISPLAY"], ":0")
        self.assertEqual(parsed["WAYLAND_DISPLAY"], "")
        self.assertNotIn("SECRET", parsed)


class PathFixTests(unittest.TestCase):
    """Konsolen-PATH und Symlink-Entscheidung."""

    def test_lib_path_is_first_candidate(self) -> None:
        """Das .deb legt das Binary unter /usr/lib/pibackup ab.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError wenn der Pfad fehlt.
        Beispiel:
            test_lib_path_is_first_candidate()
        """
        self.assertEqual(meta.PIBACKUP_PATHS[0], "/usr/lib/pibackup/pibackup")

    def test_parse_desktop_exec(self) -> None:
        """Exec= aus der Desktop-Datei wird erkannt.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Pfad.
        Beispiel:
            test_parse_desktop_exec()
        """
        text = "[Desktop Entry]\nExec=/usr/lib/pibackup/pibackup\n"
        self.assertEqual(
            diagnose.parse_desktop_exec(text),
            "/usr/lib/pibackup/pibackup",
        )

    def test_console_path_fail_when_not_in_path(self) -> None:
        """Gefundenes Binary ohne PATH-Eintrag ist FAIL.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falschem Status.
        Beispiel:
            test_console_path_fail_when_not_in_path()
        """
        found = Path("/usr/lib/pibackup/pibackup")
        result = diagnose.evaluate_console_path("", found)
        self.assertEqual(result.status, diagnose.STATUS_FAIL)
        self.assertEqual(result.name, "PATH")
        self.assertIn("--fix-path", result.hint)

    def test_decide_path_fix_need_root(self) -> None:
        """Ohne root wird der Symlink nicht angelegt.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falscher Aktion.
        Beispiel:
            test_decide_path_fix_need_root()
        """
        source = Path("/usr/lib/pibackup/pibackup")
        link = Path("/usr/local/bin/pibackup")
        action = diagnose.decide_path_fix(source, "", False, link, False, None)
        self.assertEqual(action, "need_root")

    def test_decide_path_fix_create(self) -> None:
        """Als root wird create gewaehlt.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError bei falscher Aktion.
        Beispiel:
            test_decide_path_fix_create()
        """
        source = Path("/usr/lib/pibackup/pibackup")
        link = Path("/usr/local/bin/pibackup")
        action = diagnose.decide_path_fix(source, "", True, link, False, None)
        self.assertEqual(action, "create")

    def test_next_steps_path_first(self) -> None:
        """PATH-FAIL steht in den naechsten Schritten vorn.

        Parameter:
            keine
        Rueckgabewert:
            keine
        Fehlerfaelle:
            AssertionError wenn --fix-path fehlt.
        Beispiel:
            test_next_steps_path_first()
        """
        items = [
            diagnose.item("Binary", "PATH", diagnose.STATUS_FAIL, "nicht im PATH")
        ]
        steps = diagnose.next_steps_for(items, "wayland", False)
        self.assertIn("--fix-path", steps[0])


if __name__ == "__main__":
    unittest.main()
