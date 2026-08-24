"""
pibackup_diagnose – Gemeinsame Projekmetadaten (eine Quelle).

Projekt:     pibackup_diagnose
Modul:       project_meta.py
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
Zentrale Konstanten fuer Dateikoepfe, --help/--version und das
Diagnose-Skript. Werte nicht in den aufrufenden Dateien verdoppeln.

Historie
--------
Version 1.0.0 – 2026-08-24 – Eigenstaendiges Projekt, aus pibackup ausgelagert.
Version 1.1.0 – 2026-08-24 – Binary-Suche unter /usr/lib/pibackup, --fix-path.

Aufruf / Nutzung
----------------
Wird importiert, nicht als Programm gestartet:

    python3 -c "import project_meta as m; print(m.VERSION, m.STAND)"
"""

from __future__ import annotations

PROJEKT = "pibackup_diagnose"
VERSION = "1.1.0"
STAND = "2026-08-24"
LIZENZ = "MIT"
UPSTREAM = "https://github.com/RaspberryFpc/pibackup (RaspberryFpc)"
AUTOR = "(FFHB) / RadioBBS"
PYTHON_MIN = "3.10"

APP_BIN_NAME = "pibackup"
DIAGNOSE_NAME = "pibackup_diagnose"
GUI_APP_VERSION = "2.1.0"

BESCHREIBUNG = (
    "Diagnose fuer Startprobleme der pibackup-GUI unter Debian GNU/Linux "
    "(Wayland, sudo/root, Qt5/xcb)."
)

QTFIX_PLATFORM = "xcb"
QTFIX_RUNTIME_DIR = "/run/user/0"

PIBACKUP_PATHS = (
    "/usr/lib/pibackup/pibackup",
    "/usr/bin/pibackup",
    "/usr/local/bin/pibackup",
    "/opt/pibackup/pibackup",
)

CONSOLE_LINK = "/usr/local/bin/pibackup"
DESKTOP_FILE = "/usr/share/applications/pibackup.desktop"

QT_PACKAGES = (
    "libqt5pas1",
    "libqt5gui5",
    "libqt5widgets5",
    "libqt5core5a",
    "libxcb-cursor0",
    "qtwayland5",
    "xwayland",
    "x11-xserver-utils",
)
