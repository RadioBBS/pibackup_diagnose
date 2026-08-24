#!/bin/sh
# pibackup_diagnose – Startwrapper fuer das Diagnose-Skript.
#
# Projekt:     pibackup_diagnose
# Modul:       pibackup_diagnose.sh
# Version:     1.1.0
# Stand:       2026-08-24
# Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.10)
# Bezug:       requirements.txt (leer – Stdlib only)
# Lizenz:      MIT
# Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
# Erstellt mit: Cursor Grok 4.6
# Autor:       (FFHB) / RadioBBS
#
# Beschreibung
# ------------
# Ruft pibackup_diagnose.py mit dem python3 des Systems auf.
# --help und --version ohne sudo. Volldiagnose als Desktop-User,
# Vergleich der Root-Umgebung mit sudo.
#
# Historie
# --------
# Version 1.0.0 – 2026-08-24 – Eigenstaendiges Projekt, Wrapper aus pibackup ausgelagert.
# Version 1.1.0 – 2026-08-24 – --fix-path fuer Konsolen-Symlink.
#
# Aufruf / Nutzung
# ----------------
#   ./pibackup_diagnose.sh --help
#   ./pibackup_diagnose.sh --version
#   ./pibackup_diagnose.sh --log
#   sudo ./pibackup_diagnose.sh --fix-path
#   sudo ./pibackup_diagnose.sh --log --probe

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec python3 "$SCRIPT_DIR/pibackup_diagnose.py" "$@"
