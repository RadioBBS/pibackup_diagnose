#!/usr/bin/env python3
"""
pibackup_diagnose – Diagnose-Skript fuer GUI-Start von pibackup unter Wayland/Qt5.

Projekt:     pibackup_diagnose
Modul:       pibackup_diagnose.py
Version:     1.2.0
Stand:       2026-08-24
Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.10)
Bezug:       requirements.txt (leer – Stdlib only)
Lizenz:      MIT
Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
Erstellt mit: Cursor Grok 4.6
Autor:       (FFHB) / RadioBBS

Beschreibung
------------
Prueft auf einem Raspberry Pi (Debian GNU/Linux), warum die
pibackup-GUI nicht erscheint. Schwerpunkt: Wayland-Sitzung,
sudo/root ohne Display, Qt5-xcb, XWayland und qtfix.pas
(QT_QPA_PLATFORM=xcb, XDG_RUNTIME_DIR=/run/user/0).

Historie
--------
Version 1.0.0 – 2026-08-24 – Eigenstaendiges Projekt, aus pibackup ausgelagert.
Version 1.1.0 – 2026-08-24 – Sucht /usr/lib/pibackup/pibackup, --fix-path.
Version 1.2.0 – 2026-08-24 – PROJECT.yaml, pyproject.toml, CITATION.cff, CI.

Aufruf / Nutzung
----------------
  python3 pibackup_diagnose.py --help
  python3 pibackup_diagnose.py --version
  python3 pibackup_diagnose.py --log
  python3 pibackup_diagnose.py --log --probe
  sudo python3 pibackup_diagnose.py --fix-path
  sudo python3 pibackup_diagnose.py --log --probe
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

try:
    import project_meta as meta
except ImportError:
    sys.stderr.write(
        "Fehler: project_meta.py fehlt im gleichen Verzeichnis wie "
        "pibackup_diagnose.py.\n"
    )
    raise SystemExit(2)

STATUS_OK = "OK"
STATUS_WARN = "WARN"
STATUS_FAIL = "FAIL"
STATUS_INFO = "INFO"
EXIT_OK = 0
EXIT_PROBLEM = 1
EXIT_USAGE = 2
PROBE_TIMEOUT_SEC = 6
LOG_STAMP = "%Y-%m-%d %H:%M:%S"
DEFAULT_LOG_NAME = "pibackup_diagnose.log"

DESKTOP_PROCESS_NAMES = (
    "labwc",
    "wayfire",
    "Xwayland",
    "Xorg",
    "mutter",
    "lxsession",
    "pcmanfm",
)

SUDO_ENV_KEYS = (
    "DISPLAY",
    "WAYLAND_DISPLAY",
    "XDG_RUNTIME_DIR",
    "XAUTHORITY",
    "XDG_SESSION_TYPE",
    "QT_QPA_PLATFORM",
)


@dataclass
class CmdResult:
    """Ergebnis eines Prozessaufrufs ohne Shell."""

    returncode: int
    stdout: str
    stderr: str


@dataclass
class CheckItem:
    """Ein Diagnosebefund mit Status und Hinweis."""

    section: str
    name: str
    status: str
    detail: str
    hint: str = ""


@dataclass
class Options:
    """Ausgewertete Kommandozeile."""

    show_help: bool = False
    show_version: bool = False
    wait_ende: bool = False
    log_enabled: bool = False
    log_file: Path | None = None
    probe: bool = False
    fix_path: bool = False


@dataclass
class SessionFacts:
    """Wichtige Display- und Rechtewerte der aktuellen Sitzung."""

    is_root: bool
    uid: int
    user_name: str
    sudo_user: str
    session_type: str
    display: str
    wayland_display: str
    xdg_runtime: str
    xauthority: str
    ssh_connection: str
    machine: str


def now_stamp() -> str:
    """Liefert den Log-Zeitstempel.

    Parameter:
        keine
    Rueckgabewert:
        Zeitstempel YYYY-MM-DD HH:MM:SS.
    Fehlerfaelle:
        keine
    Beispiel:
        now_stamp()
    """
    return datetime.now().strftime(LOG_STAMP)


def effective_uid() -> int:
    """Liest die effektive Benutzer-ID (unter Windows -1).

    Parameter:
        keine
    Rueckgabewert:
        UID oder -1, wenn das System kein geteuid kennt.
    Fehlerfaelle:
        keine
    Beispiel:
        effective_uid()
    """
    getter = getattr(os, "geteuid", None)
    if getter is None:
        return -1
    return int(getter())


def current_user_name() -> str:
    """Ermittelt den Anmeldenamen ohne fest verdrahteten Default.

    Parameter:
        keine
    Rueckgabewert:
        Benutzername oder leer.
    Fehlerfaelle:
        KeyError in der Umgebung wird abgefangen.
    Beispiel:
        current_user_name()
    """
    for key in ("LOGNAME", "USER", "USERNAME"):
        value = os.environ.get(key, "").strip()
        if value:
            return value
    return ""


def run_command(
    argv: list[str],
    timeout_sec: float = 8.0,
    extra_env: dict[str, str] | None = None,
) -> CmdResult:
    """Startet ein Programm ohne Shell.

    Parameter:
        argv: Programmpfad und Argumente.
        timeout_sec: maximale Laufzeit in Sekunden.
        extra_env: zusaetzliche Umgebungsvariablen oder None.
    Rueckgabewert:
        CmdResult mit returncode, stdout und stderr.
    Fehlerfaelle:
        Fehlendes Binary wird als 127, Timeout als 124 geliefert.
    Beispiel:
        run_command(["uname", "-m"])
    """
    merged = os.environ.copy()
    if extra_env:
        merged.update(extra_env)
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=merged,
            check=False,
        )
    except FileNotFoundError:
        return CmdResult(127, "", f"nicht gefunden: {argv[0]}")
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or "Zeitueberschreitung"
        return CmdResult(124, _as_text(out), _as_text(err))
    return CmdResult(completed.returncode, completed.stdout or "", completed.stderr or "")


def _as_text(value: str | bytes) -> str:
    """Wandelt Prozessausgabe in Text.

    Parameter:
        value: stdout/stderr als str oder bytes.
    Rueckgabewert:
        Unicode-Text.
    Fehlerfaelle:
        ungueltige Bytes werden ersetzt.
    Beispiel:
        _as_text(b"ok")
    """
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def parse_kv_file(path: Path) -> dict[str, str]:
    """Liest KEY=VALUE-Zeilen (os-release).

    Parameter:
        path: Dateipfad.
    Rueckgabewert:
        Schluessel-Wert-Paare ohne Anfuehrungszeichen.
    Fehlerfaelle:
        fehlende Datei ergibt leeres Dict.
    Beispiel:
        parse_kv_file(Path("/etc/os-release"))
    """
    result: dict[str, str] = {}
    if not path.is_file():
        return result
    text = path.read_text(encoding="utf-8", errors="replace")
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"').strip("'")
    return result


def item(
    section: str,
    name: str,
    status: str,
    detail: str,
    hint: str = "",
) -> CheckItem:
    """Erzeugt einen Diagnosebefund.

    Parameter:
        section: Abschnittsname.
        name: Kurzname der Pruefung.
        status: OK, WARN, FAIL oder INFO.
        detail: beobachteter Wert.
        hint: optionaler naechster Schritt.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        keine
    Beispiel:
        item("System", "Architektur", STATUS_OK, "aarch64")
    """
    return CheckItem(section, name, status, detail, hint)


def evaluate_architecture(machine: str) -> CheckItem:
    """Bewertet CPU-Architektur gegen das ARM64-Binary.

    Parameter:
        machine: uname -m bzw. platform.machine().
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        leere Angabe ergibt WARN.
    Beispiel:
        evaluate_architecture("aarch64")
    """
    name = (machine or "").strip().lower()
    if name in {"aarch64", "arm64"}:
        return item("System", "Architektur", STATUS_OK, name)
    if name.startswith("arm"):
        return item(
            "System",
            "Architektur",
            STATUS_FAIL,
            name,
            "pibackup ist nur als 64-Bit-ARM64-Paket gebaut.",
        )
    if not name:
        return item("System", "Architektur", STATUS_WARN, "(unbekannt)")
    return item(
        "System",
        "Architektur",
        STATUS_WARN,
        name,
        "Kein Raspberry-Pi-ARM64. Ergebnis auf diesem Rechner nur begrenzt gueltig.",
    )


def evaluate_qtfix_runtime(dir_exists: bool, is_root: bool) -> CheckItem:
    """Bewertet das von qtfix.pas erzwungene XDG_RUNTIME_DIR.

    Parameter:
        dir_exists: ob /run/user/0 existiert.
        is_root: ob der aktuelle Prozess root ist.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        fehlendes Verzeichnis unter root ist FAIL.
    Beispiel:
        evaluate_qtfix_runtime(False, True)
    """
    path = meta.QTFIX_RUNTIME_DIR
    if dir_exists:
        return item(
            "qtfix",
            "XDG_RUNTIME_DIR",
            STATUS_WARN,
            f"{path} existiert",
            "pibackup setzt dieses Verzeichnis immer. Unter Wayland gehoert "
            "die Sitzung normalerweise zu /run/user/<UID>.",
        )
    if is_root:
        return item(
            "qtfix",
            "XDG_RUNTIME_DIR",
            STATUS_FAIL,
            f"{path} fehlt, Prozess laeuft als root",
            "qtfix.pas setzt XDG_RUNTIME_DIR auf /run/user/0. Ohne dieses "
            "Verzeichnis startet Qt oft ohne Fenster.",
        )
    return item(
        "qtfix",
        "XDG_RUNTIME_DIR",
        STATUS_WARN,
        f"{path} fehlt",
        "Sobald pibackup per sudo startet, setzt qtfix genau dieses Verzeichnis.",
    )


def evaluate_forced_xcb(session_type: str, xwayland_running: bool) -> CheckItem:
    """Bewertet QT_QPA_PLATFORM=xcb gegen die Desktop-Sitzung.

    Parameter:
        session_type: wayland, x11 oder leer.
        xwayland_running: ob ein Xwayland-Prozess laeuft.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        Wayland ohne XWayland ist FAIL.
    Beispiel:
        evaluate_forced_xcb("wayland", False)
    """
    kind = (session_type or "").strip().lower()
    if kind == "x11":
        return item(
            "qtfix",
            "QT_QPA_PLATFORM",
            STATUS_OK,
            f"{meta.QTFIX_PLATFORM} passt zu X11",
        )
    if kind == "wayland" and not xwayland_running:
        return item(
            "qtfix",
            "QT_QPA_PLATFORM",
            STATUS_FAIL,
            "xcb erzwungen, Sitzung ist Wayland, XWayland laeuft nicht",
            "sudo apt install xwayland   oder in raspi-config auf X11 umstellen.",
        )
    if kind == "wayland":
        return item(
            "qtfix",
            "QT_QPA_PLATFORM",
            STATUS_WARN,
            "xcb erzwungen unter Wayland (XWayland vorhanden)",
            "Root braucht trotzdem DISPLAY und xhost-Freigabe.",
        )
    return item(
        "qtfix",
        "QT_QPA_PLATFORM",
        STATUS_INFO,
        f"pibackup setzt intern QT_QPA_PLATFORM={meta.QTFIX_PLATFORM}",
    )


def evaluate_root_display(
    is_root: bool,
    display: str,
    wayland_display: str,
    session_type: str,
) -> CheckItem:
    """Prueft, ob root ein nutzbares Display sieht.

    Parameter:
        is_root: effektive UID 0.
        display: DISPLAY.
        wayland_display: WAYLAND_DISPLAY.
        session_type: XDG_SESSION_TYPE.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        root ohne DISPLAY unter Wayland/xcb ist FAIL.
    Beispiel:
        evaluate_root_display(True, "", "wayland-0", "wayland")
    """
    if not is_root:
        return item(
            "Rechte",
            "root-Display",
            STATUS_INFO,
            "nicht als root - pibackup selbst verlangt spaeter sudo",
            "Zum Vergleich der Root-Umgebung: sudo python3 pibackup_diagnose.py",
        )
    if display.strip():
        return item(
            "Rechte",
            "root-Display",
            STATUS_WARN,
            f"root sieht DISPLAY={display}",
            "Ohne xhost +SI:localuser:root lehnt der Compositor root oft ab.",
        )
    kind = (session_type or "").strip().lower()
    if wayland_display.strip() and kind == "wayland":
        return item(
            "Rechte",
            "root-Display",
            STATUS_FAIL,
            f"root unter Wayland ohne DISPLAY (WAYLAND_DISPLAY={wayland_display})",
            "pibackup nutzt xcb, nicht Wayland. DISPLAY und XWayland sind noetig.",
        )
    return item(
        "Rechte",
        "root-Display",
        STATUS_FAIL,
        "root ohne DISPLAY und ohne WAYLAND_DISPLAY",
        "sudo entfernt typischerweise die Desktop-Variablen. Mit sudo -E starten.",
    )


def evaluate_sudo_env(
    sudo_available: bool,
    sudo_needs_password: bool,
    sudo_map: dict[str, str],
    user_display: str,
) -> CheckItem:
    """Vergleicht die Umgebung von sudo -n env mit der Usersitzung.

    Parameter:
        sudo_available: sudo ist installiert.
        sudo_needs_password: sudo -n wurde abgelehnt.
        sudo_map: gefilterte Variablen aus sudo env.
        user_display: DISPLAY des aktuellen Users.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        fehlendes DISPLAY unter sudo ist FAIL.
    Beispiel:
        evaluate_sudo_env(True, False, {"DISPLAY": ""}, ":0")
    """
    if not sudo_available:
        return item("Rechte", "sudo-Umgebung", STATUS_WARN, "sudo nicht gefunden")
    if sudo_needs_password:
        return item(
            "Rechte",
            "sudo-Umgebung",
            STATUS_INFO,
            "sudo verlangt ein Passwort (sudo -n nicht moeglich)",
            "Skript zusaetzlich mit sudo ausfuehren, um die Root-Umgebung zu sehen.",
        )
    sudo_display = sudo_map.get("DISPLAY", "")
    sudo_wayland = sudo_map.get("WAYLAND_DISPLAY", "")
    sudo_runtime = sudo_map.get("XDG_RUNTIME_DIR", "")
    detail = (
        f"DISPLAY={sudo_display or '(leer)'} "
        f"WAYLAND_DISPLAY={sudo_wayland or '(leer)'} "
        f"XDG_RUNTIME_DIR={sudo_runtime or '(leer)'}"
    )
    if not sudo_display and not sudo_wayland:
        return item(
            "Rechte",
            "sudo-Umgebung",
            STATUS_FAIL,
            detail,
            "sudo streift die Display-Variablen. pibackup dann so starten: "
            "xhost +SI:localuser:root && sudo -E env "
            'QT_QPA_PLATFORM=xcb DISPLAY="$DISPLAY" pibackup',
        )
    if user_display and sudo_display and sudo_display != user_display:
        return item(
            "Rechte",
            "sudo-Umgebung",
            STATUS_WARN,
            detail,
            "DISPLAY unter sudo weicht von der Usersitzung ab.",
        )
    return item("Rechte", "sudo-Umgebung", STATUS_WARN, detail)


def evaluate_ssh_session(ssh_connection: str, display: str, wayland_display: str) -> CheckItem:
    """Erkennt SSH ohne grafisches Display.

    Parameter:
        ssh_connection: Inhalt von SSH_CONNECTION.
        display: DISPLAY.
        wayland_display: WAYLAND_DISPLAY.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        SSH ohne Display ist FAIL.
    Beispiel:
        evaluate_ssh_session("192.168.1.2 11 192.168.1.3 22", "", "")
    """
    if not ssh_connection.strip():
        return item("Sitzung", "SSH", STATUS_OK, "keine SSH-Verbindung erkannt")
    if display.strip() or wayland_display.strip():
        return item(
            "Sitzung",
            "SSH",
            STATUS_WARN,
            f"SSH aktiv, Display gesetzt ({display or wayland_display})",
            "GUI auf dem Pi-Desktop pruefen, nicht nur im SSH-Terminal.",
        )
    return item(
        "Sitzung",
        "SSH",
        STATUS_FAIL,
        "SSH ohne DISPLAY/WAYLAND_DISPLAY",
        "Auf dem grafischen Desktop anmelden oder ssh -X nutzen. "
        "Lite-Images ohne Desktop haben keine GUI.",
    )


def evaluate_wayland_socket(path: Path, exists: bool, readable: bool, is_root: bool) -> CheckItem:
    """Bewertet den Wayland-Socket.

    Parameter:
        path: erwarteter Socket-Pfad.
        exists: Datei existiert.
        readable: Zugriff moeglich.
        is_root: aktueller Prozess ist root.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        root ohne Leserecht ist FAIL.
    Beispiel:
        evaluate_wayland_socket(Path("/run/user/1000/wayland-0"), True, False, True)
    """
    shown = path.as_posix() if hasattr(path, "as_posix") else str(path)
    if not exists:
        return item(
            "Sitzung",
            "Wayland-Socket",
            STATUS_WARN,
            f"nicht gefunden: {shown}",
            "Kein aktives Wayland, oder XDG_RUNTIME_DIR zeigt nicht auf die Sitzung.",
        )
    if readable:
        return item("Sitzung", "Wayland-Socket", STATUS_OK, shown)
    if is_root:
        return item(
            "Sitzung",
            "Wayland-Socket",
            STATUS_FAIL,
            f"vorhanden, fuer root nicht lesbar: {shown}",
            "Wayland-Sockets sind 0700 fuer den Desktop-User. Root darf nicht andocken.",
        )
    return item(
        "Sitzung",
        "Wayland-Socket",
        STATUS_FAIL,
        f"keine Berechtigung: {shown}",
    )


def next_steps_for(items: list[CheckItem], session_type: str, is_root: bool) -> list[str]:
    """Leitet konkrete naechste Schritte aus den Befunden ab.

    Parameter:
        items: alle Checks.
        session_type: wayland/x11.
        is_root: aktueller Prozess ist root.
    Rueckgabewert:
        Liste kurzer Handlungsempfehlungen.
    Fehlerfaelle:
        leere Liste, wenn nichts Fail/Warn ist.
    Beispiel:
        next_steps_for([], "wayland", False)
    """
    steps: list[str] = []
    if _has_status(items, "PATH", STATUS_FAIL):
        steps.append(
            "Zuerst PATH reparieren: sudo python3 pibackup_diagnose.py --fix-path"
        )
        steps.append("Oder direkt: sudo /usr/lib/pibackup/pibackup")
    statuses = {entry.status for entry in items}
    kind = (session_type or "").lower()
    if STATUS_FAIL not in statuses and STATUS_WARN not in statuses:
        steps.append("Keine Blocker gefunden. pibackup im selben Terminal starten.")
        return steps
    if kind == "wayland":
        steps.append(
            "Kurzfristig: xhost +SI:localuser:root && "
            "sudo -E env QT_QPA_PLATFORM=xcb "
            'DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" pibackup'
        )
        steps.append(
            "Stabiler: raspi-config → Advanced Options → Wayland → X11, "
            "neu anmelden, danach sudo pibackup."
        )
    if _has_status(items, "QT_QPA_PLATFORM", STATUS_FAIL):
        steps.append("sudo apt install -y xwayland x11-xserver-utils")
    if any(entry.section == "Pakete" and entry.status == STATUS_FAIL for entry in items):
        steps.append("sudo apt install -y libqt5pas1 libxcb-cursor0 libqt5gui5")
    if not is_root:
        steps.append(
            "Diagnose als root vergleichen: sudo python3 pibackup_diagnose.py --log --probe"
        )
    steps.append(
        "Falls kein Desktop installiert ist: Raspberry Pi OS mit Desktop nutzen, nicht Lite."
    )
    return _unique(steps)


def _has_status(items: list[CheckItem], name: str, status: str) -> bool:
    """Prueft, ob ein benannter Befund den Status hat.

    Parameter:
        items: Befunde.
        name: Check-Name.
        status: erwarteter Status.
    Rueckgabewert:
        True bei Treffer.
    Fehlerfaelle:
        keine
    Beispiel:
        _has_status([], "xhost", STATUS_FAIL)
    """
    return any(entry.name == name and entry.status == status for entry in items)


def _unique(lines: list[str]) -> list[str]:
    """Entfernt doppelte Empfehlungen, Reihenfolge bleibt.

    Parameter:
        lines: Empfehlungstexte.
    Rueckgabewert:
        Liste ohne Wiederholungen.
    Fehlerfaelle:
        keine
    Beispiel:
        _unique(["a", "a", "b"])
    """
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        result.append(line)
    return result


def collect_session_facts() -> SessionFacts:
    """Liest Display- und Rechtewerte aus der Umgebung.

    Parameter:
        keine
    Rueckgabewert:
        SessionFacts.
    Fehlerfaelle:
        fehlende Variablen werden als leer geliefert.
    Beispiel:
        collect_session_facts()
    """
    uid = effective_uid()
    runtime = os.environ.get("XDG_RUNTIME_DIR", "").strip()
    if not runtime and uid >= 0:
        runtime = f"/run/user/{uid}"
    return SessionFacts(
        is_root=uid == 0,
        uid=uid,
        user_name=current_user_name(),
        sudo_user=os.environ.get("SUDO_USER", "").strip(),
        session_type=os.environ.get("XDG_SESSION_TYPE", "").strip(),
        display=os.environ.get("DISPLAY", "").strip(),
        wayland_display=os.environ.get("WAYLAND_DISPLAY", "").strip(),
        xdg_runtime=runtime,
        xauthority=os.environ.get("XAUTHORITY", "").strip(),
        ssh_connection=os.environ.get("SSH_CONNECTION", "").strip(),
        machine=platform.machine(),
    )


def collect_system_items(facts: SessionFacts) -> list[CheckItem]:
    """Prueft Betriebssystem und Architektur.

    Parameter:
        facts: Sitzungsdaten.
    Rueckgabewert:
        Liste von CheckItems.
    Fehlerfaelle:
        fehlendes os-release ergibt WARN.
    Beispiel:
        collect_system_items(collect_session_facts())
    """
    items = [evaluate_architecture(facts.machine)]
    data = parse_kv_file(Path("/etc/os-release"))
    pretty = data.get("PRETTY_NAME") or data.get("NAME") or "(kein /etc/os-release)"
    version_id = data.get("VERSION_ID", "")
    status = STATUS_OK if version_id else STATUS_WARN
    hint = ""
    if version_id == "12":
        hint = (
            "Debian 12 / Bookworm nutzt auf dem Pi oft Wayland. "
            "pibackup wurde gegen X11 (Trixie) getestet."
        )
        status = STATUS_WARN
    items.append(item("System", "Distribution", status, pretty, hint))
    kernel = platform.release()
    items.append(item("System", "Kernel", STATUS_INFO, kernel))
    pyver = platform.python_version()
    items.append(item("System", "Python", STATUS_INFO, pyver))
    return items


def session_type_from_loginctl() -> str:
    """Fragt den Sitzungstyp bei systemd-logind ab.

    Parameter:
        keine
    Rueckgabewert:
        wayland, x11, tty oder leer.
    Fehlerfaelle:
        fehlendes loginctl liefert leer.
    Beispiel:
        session_type_from_loginctl()
    """
    session_id = os.environ.get("XDG_SESSION_ID", "").strip()
    argv = ["loginctl", "show-session"]
    argv.append(session_id if session_id else "self")
    argv.extend(["-p", "Type", "--value"])
    result = run_command(argv, timeout_sec=4)
    if result.returncode != 0:
        return ""
    return result.stdout.strip().lower()


def process_running(name: str) -> bool:
    """Prueft, ob ein Prozessname in der Prozessliste vorkommt.

    Parameter:
        name: auszufilternder Name (pgrep -x bzw. -f).
    Rueckgabewert:
        True, wenn gefunden.
    Fehlerfaelle:
        fehlendes pgrep ergibt False.
    Beispiel:
        process_running("labwc")
    """
    exact = run_command(["pgrep", "-x", name], timeout_sec=3)
    if exact.returncode == 0 and exact.stdout.strip():
        return True
    fuzzy = run_command(["pgrep", "-f", name], timeout_sec=3)
    return fuzzy.returncode == 0 and bool(fuzzy.stdout.strip())


def collect_session_items(facts: SessionFacts) -> list[CheckItem]:
    """Prueft Wayland/X11-Sitzung, Sockets und Desktop-Prozesse.

    Parameter:
        facts: Sitzungsdaten.
    Rueckgabewert:
        Liste von CheckItems.
    Fehlerfaelle:
        fehlende Tools ergeben WARN/INFO, keine Ausnahme.
    Beispiel:
        collect_session_items(collect_session_facts())
    """
    login_type = session_type_from_loginctl()
    session_type = facts.session_type or login_type
    xwayland = process_running("Xwayland")
    items = [
        item(
            "Sitzung",
            "XDG_SESSION_TYPE",
            STATUS_WARN if session_type == "wayland" else STATUS_INFO,
            session_type or "(nicht gesetzt)",
            "wayland: pibackup erzwingt xcb und braucht XWayland plus xhost.",
        ),
        item("Sitzung", "DISPLAY", STATUS_INFO, facts.display or "(leer)"),
        item(
            "Sitzung",
            "WAYLAND_DISPLAY",
            STATUS_INFO,
            facts.wayland_display or "(leer)",
        ),
        item(
            "Sitzung",
            "XDG_RUNTIME_DIR",
            STATUS_INFO,
            facts.xdg_runtime or "(leer)",
        ),
        evaluate_ssh_session(facts.ssh_connection, facts.display, facts.wayland_display),
        evaluate_forced_xcb(session_type, xwayland),
    ]
    socket_name = facts.wayland_display or "wayland-0"
    runtime = (facts.xdg_runtime or f"/run/user/{max(facts.uid, 0)}").replace("\\", "/")
    socket_path = Path(runtime) / socket_name
    exists = socket_path.exists() if os.name != "nt" else False
    readable = os.access(socket_path, os.R_OK) if exists else False
    items.append(evaluate_wayland_socket(socket_path, exists, readable, facts.is_root))
    running = [name for name in DESKTOP_PROCESS_NAMES if process_running(name)]
    if running:
        items.append(item("Sitzung", "Desktop-Prozesse", STATUS_OK, ", ".join(running)))
    else:
        items.append(
            item(
                "Sitzung",
                "Desktop-Prozesse",
                STATUS_WARN,
                "kein labwc/wayfire/Xorg/Xwayland gefunden",
                "Ohne Desktop-Sitzung kann keine GUI erscheinen.",
            )
        )
    xhost = shutil.which("xhost")
    if not xhost:
        items.append(
            item(
                "Sitzung",
                "xhost",
                STATUS_WARN,
                "nicht installiert",
                "sudo apt install x11-xserver-utils",
            )
        )
        return items
    probed = run_command([xhost], timeout_sec=3)
    status = STATUS_INFO if probed.returncode == 0 else STATUS_WARN
    text = (probed.stdout or probed.stderr).strip().replace("\n", " | ")
    items.append(item("Sitzung", "xhost", status, text or f"exit {probed.returncode}"))
    return items


def parse_sudo_env(text: str) -> dict[str, str]:
    """Filtert Display-Variablen aus `sudo env`.

    Parameter:
        text: komplette env-Ausgabe.
    Rueckgabewert:
        Map der bekannten Schluessel.
    Fehlerfaelle:
        unvollstaendige Zeilen werden ignoriert.
    Beispiel:
        parse_sudo_env("DISPLAY=:0\\nHOME=/root\\n")
    """
    found: dict[str, str] = {key: "" for key in SUDO_ENV_KEYS}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if key in found:
            found[key] = value
    return found


def collect_rights_items(facts: SessionFacts) -> list[CheckItem]:
    """Prueft root, sudo und die von sudo gesehene Umgebung.

    Parameter:
        facts: Sitzungsdaten.
    Rueckgabewert:
        Liste von CheckItems.
    Fehlerfaelle:
        sudo -n kann mit Passwort-Pflicht scheitern (INFO).
    Beispiel:
        collect_rights_items(collect_session_facts())
    """
    uid_text = f"uid={facts.uid} user={facts.user_name or '(unbekannt)'}"
    if facts.sudo_user:
        uid_text += f" SUDO_USER={facts.sudo_user}"
    items = [
        item("Rechte", "Identitaet", STATUS_INFO, uid_text),
        evaluate_root_display(
            facts.is_root,
            facts.display,
            facts.wayland_display,
            facts.session_type,
        ),
        evaluate_qtfix_runtime(Path(meta.QTFIX_RUNTIME_DIR).exists(), facts.is_root),
    ]
    sudo_bin = shutil.which("sudo")
    if facts.is_root:
        items.append(
            item(
                "Rechte",
                "sudo-Umgebung",
                STATUS_INFO,
                "Skript laeuft bereits als root – sudo -n wird nicht zusaetzlich aufgerufen",
            )
        )
        return items
    if not sudo_bin:
        items.append(evaluate_sudo_env(False, False, {}, facts.display))
        return items
    probed = run_command([sudo_bin, "-n", "env"], timeout_sec=6)
    needs_password = probed.returncode != 0
    env_map = parse_sudo_env(probed.stdout) if not needs_password else {}
    items.append(evaluate_sudo_env(True, needs_password, env_map, facts.display))
    return items


def dpkg_query(package: str) -> CheckItem:
    """Prueft den Installationsstatus eines Debian-Pakets.

    Parameter:
        package: Paketname.
    Rueckgabewert:
        CheckItem.
    Fehlerfaelle:
        dpkg-query fehlt oder Paket ist nicht installiert.
    Beispiel:
        dpkg_query("libqt5pas1")
    """
    result = run_command(
        ["dpkg-query", "-W", "-f", "${Status} ${Version}", package],
        timeout_sec=4,
    )
    text = (result.stdout or result.stderr).strip()
    if result.returncode != 0:
        return item(
            "Pakete",
            package,
            STATUS_FAIL,
            text or "nicht installiert",
            f"sudo apt install {package}",
        )
    if "install ok installed" in text:
        status = STATUS_OK
        hint = ""
        if package in {"qtwayland5"}:
            hint = "Vorhanden, pibackup nutzt es aber nicht (xcb ist fest eingestellt)."
            status = STATUS_INFO
        return item("Pakete", package, status, text, hint)
    return item("Pakete", package, STATUS_WARN, text)


def collect_package_items() -> list[CheckItem]:
    """Prueft Qt-, X11- und pibackup-Pakete.

    Parameter:
        keine
    Rueckgabewert:
        Liste von CheckItems.
    Fehlerfaelle:
        fehlendes dpkg ergibt einen FAIL.
    Beispiel:
        collect_package_items()
    """
    if shutil.which("dpkg-query") is None:
        return [item("Pakete", "dpkg", STATUS_FAIL, "dpkg-query nicht gefunden")]
    items = [dpkg_query(name) for name in meta.QT_PACKAGES]
    items.append(dpkg_query(meta.APP_BIN_NAME))
    return items


def parse_desktop_exec(text: str) -> str:
    """Liest den Binary-Pfad aus einer .desktop-Exec-Zeile.

    Parameter:
        text: Inhalt der Desktop-Datei.
    Rueckgabewert:
        Absoluter Pfad oder leer.
    Fehlerfaelle:
        fehlende Exec-Zeile ergibt leer.
    Beispiel:
        parse_desktop_exec("Exec=/usr/lib/pibackup/pibackup\\n")
    """
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("Exec="):
            continue
        for part in line[5:].split():
            if part.startswith("%"):
                continue
            if part.startswith("/") and "pibackup" in part:
                return part
    return ""


def binaries_from_dpkg() -> list[Path]:
    """Listet pibackup-Dateien aus dem Debian-Paket.

    Parameter:
        keine
    Rueckgabewert:
        vorhandene Dateien namens pibackup.
    Fehlerfaelle:
        fehlendes dpkg oder Paket ergibt leere Liste.
    Beispiel:
        binaries_from_dpkg()
    """
    probed = run_command(["dpkg", "-L", meta.APP_BIN_NAME], timeout_sec=5)
    if probed.returncode != 0:
        return []
    found: list[Path] = []
    for raw in probed.stdout.splitlines():
        path = Path(raw.strip())
        if path.name == meta.APP_BIN_NAME and path.is_file():
            found.append(path)
    return found


def exec_from_desktop_file() -> Path | None:
    """Liest Exec= aus der installierten Desktop-Datei.

    Parameter:
        keine
    Rueckgabewert:
        Pfad oder None.
    Fehlerfaelle:
        fehlende Datei ergibt None.
    Beispiel:
        exec_from_desktop_file()
    """
    desktop = Path(meta.DESKTOP_FILE)
    if not desktop.is_file():
        return None
    text = desktop.read_text(encoding="utf-8", errors="replace")
    value = parse_desktop_exec(text)
    if not value:
        return None
    path = Path(value)
    if path.is_file():
        return path
    return None


def iter_candidate_binaries() -> list[Path]:
    """Sammelt alle gefundenen pibackup-Binaries ohne Dubletten.

    Parameter:
        keine
    Rueckgabewert:
        Liste vorhandener Pfade, PATH zuerst.
    Fehlerfaelle:
        nichts gefunden ergibt leere Liste.
    Beispiel:
        iter_candidate_binaries()
    """
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        if not path.is_file():
            return
        try:
            key = str(path.resolve())
        except OSError:
            key = path.as_posix()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    which = shutil.which(meta.APP_BIN_NAME)
    if which:
        add(Path(which))
    for candidate in meta.PIBACKUP_PATHS:
        add(Path(candidate))
    for path in binaries_from_dpkg():
        add(path)
    desktop = exec_from_desktop_file()
    if desktop is not None:
        add(desktop)
    return found


def evaluate_console_path(which_path: str, found: Path | None) -> CheckItem:
    """Bewertet, ob der Befehl pibackup in der Konsole greift.

    Parameter:
        which_path: Ergebnis von shutil.which oder leer.
        found: gefundenes Binary oder None.
    Rueckgabewert:
        CheckItem PATH.
    Fehlerfaelle:
        Binary ausserhalb PATH ist FAIL.
    Beispiel:
        evaluate_console_path("", Path("/usr/lib/pibackup/pibackup"))
    """
    if which_path:
        return item("Binary", "PATH", STATUS_OK, which_path)
    if found is not None:
        shown = found.as_posix()
        return item(
            "Binary",
            "PATH",
            STATUS_FAIL,
            f"{meta.APP_BIN_NAME} nicht im PATH, Binary liegt in {shown}",
            "sudo python3 pibackup_diagnose.py --fix-path",
        )
    return item(
        "Binary",
        "PATH",
        STATUS_FAIL,
        f"{meta.APP_BIN_NAME} nicht im PATH und kein Binary gefunden",
        "Paket pruefen: dpkg -L pibackup | grep pibackup",
    )


def decide_path_fix(
    source: Path | None,
    which_path: str,
    is_root: bool,
    link: Path,
    link_exists: bool,
    link_target: Path | None,
) -> str:
    """Entscheidet, ob ein Konsolen-Symlink noetig ist.

    Parameter:
        source: gefundenes Binary oder None.
        which_path: aktuelles which-Ergebnis.
        is_root: Prozess laeuft als root.
        link: Zielsymlink, meist /usr/local/bin/pibackup.
        link_exists: Link oder Datei existiert.
        link_target: Aufloesung des vorhandenen Links.
    Rueckgabewert:
        already_ok, create, exists_ok, need_root, conflict, missing
    Fehlerfaelle:
        missing wenn kein Binary da ist.
    Beispiel:
        decide_path_fix(Path("/usr/lib/pibackup/pibackup"), "", True, Path("/usr/local/bin/pibackup"), False, None)
    """
    if source is None:
        return "missing"
    if which_path:
        return "already_ok"
    if link_exists and link_target is not None:
        try:
            if link_target.resolve() == source.resolve():
                return "exists_ok"
        except OSError:
            return "conflict"
        return "conflict"
    if link_exists:
        return "conflict"
    if not is_root:
        return "need_root"
    return "create"


def apply_console_link(source: Path, link: Path) -> None:
    """Legt den Symlink fuer die Konsole an.

    Parameter:
        source: echtes Binary.
        link: /usr/local/bin/pibackup.
    Rueckgabewert:
        keine
    Fehlerfaelle:
        OSError bei fehlendem Verzeichnis oder Rechten.
    Beispiel:
        apply_console_link(Path("/usr/lib/pibackup/pibackup"), Path("/usr/local/bin/pibackup"))
    """
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to(source.resolve())


def run_fix_path() -> int:
    """Sucht pibackup und legt bei Bedarf /usr/local/bin/pibackup an.

    Parameter:
        keine
    Rueckgabewert:
        Exitcode 0 oder 1.
    Fehlerfaelle:
        Binary fehlt, keine root-Rechte, Zielkonflikt.
    Beispiel:
        run_fix_path()
    """
    source = find_pibackup_binary()
    which_path = shutil.which(meta.APP_BIN_NAME) or ""
    link = Path(meta.CONSOLE_LINK)
    link_exists = link.exists() or link.is_symlink()
    link_target: Path | None = None
    if link_exists:
        try:
            link_target = link.resolve()
        except OSError:
            link_target = None
    action = decide_path_fix(
        source,
        which_path,
        effective_uid() == 0,
        link,
        link_exists,
        link_target,
    )
    messages = {
        "already_ok": f"OK: {meta.APP_BIN_NAME} ist bereits im PATH ({which_path}).",
        "exists_ok": f"OK: {link.as_posix()} zeigt bereits auf {source}.",
        "missing": (
            "Fehler: pibackup-Binary nicht gefunden. "
            "Paket installieren, dann dpkg -L pibackup."
        ),
        "need_root": (
            f"Binary gefunden: {source}. "
            "Symlink fehlt. Bitte als root: sudo python3 pibackup_diagnose.py --fix-path"
        ),
        "conflict": (
            f"Fehler: {link.as_posix()} existiert bereits und zeigt nicht auf {source}."
        ),
    }
    if action == "create" and source is not None:
        try:
            apply_console_link(source, link)
        except OSError as exc:
            print(f"Fehler: Symlink nicht anlegbar ({exc})", file=sys.stderr)
            return EXIT_PROBLEM
        print(f"OK: {link.as_posix()} -> {source.as_posix()}")
        print(f"Pruefen: command -v {meta.APP_BIN_NAME}")
        print(f"Start: sudo {meta.APP_BIN_NAME}")
        return EXIT_OK
    print(messages[action])
    if action in {"already_ok", "exists_ok"}:
        return EXIT_OK
    return EXIT_PROBLEM


def find_pibackup_binary() -> Path | None:
    """Sucht das pibackup-Binary (PATH, /usr/lib, dpkg, Desktop-Datei).

    Parameter:
        keine
    Rueckgabewert:
        Pfad oder None.
    Fehlerfaelle:
        nicht installiert ergibt None.
    Beispiel:
        find_pibackup_binary()
    """
    found = iter_candidate_binaries()
    if found:
        return found[0]
    return None


def collect_binary_items() -> list[CheckItem]:
    """Prueft Binary, PATH, Dateityp und fehlende Bibliotheken.

    Parameter:
        keine
    Rueckgabewert:
        Liste von CheckItems.
    Fehlerfaelle:
        fehlendes Binary oder fehlender PATH-Eintrag ist FAIL.
    Beispiel:
        collect_binary_items()
    """
    binary = find_pibackup_binary()
    which_path = shutil.which(meta.APP_BIN_NAME) or ""
    items = [evaluate_console_path(which_path, binary)]
    if binary is None:
        items.append(
            item(
                "Binary",
                meta.APP_BIN_NAME,
                STATUS_FAIL,
                "nicht gefunden (erwartet: /usr/lib/pibackup/pibackup)",
                "dpkg -L pibackup ; ls -l /usr/lib/pibackup/pibackup",
            )
        )
        return items
    items.append(item("Binary", "Pfad", STATUS_OK, binary.as_posix()))
    file_tool = shutil.which("file")
    if file_tool:
        probed = run_command([file_tool, str(binary)], timeout_sec=4)
        items.append(item("Binary", "Dateityp", STATUS_INFO, probed.stdout.strip()))
    ldd = shutil.which("ldd")
    if not ldd:
        items.append(item("Binary", "ldd", STATUS_WARN, "ldd nicht gefunden"))
        return items
    probed = run_command([ldd, str(binary)], timeout_sec=8)
    missing = [
        line.strip()
        for line in probed.stdout.splitlines()
        if "not found" in line.lower()
    ]
    if missing:
        items.append(
            item(
                "Binary",
                "Bibliotheken",
                STATUS_FAIL,
                " ; ".join(missing),
                "sudo apt -f install   bzw. fehlende libqt5*-Pakete nachinstallieren.",
            )
        )
        return items
    items.append(item("Binary", "Bibliotheken", STATUS_OK, "ldd meldet keine fehlenden libs"))
    return items


def collect_qt_plugin_items() -> list[CheckItem]:
    """Sucht Qt5-Platform-Plugins (xcb, wayland).

    Parameter:
        keine
    Rueckgabewert:
        Liste von CheckItems.
    Fehlerfaelle:
        kein libqxcb.so ist FAIL.
    Beispiel:
        collect_qt_plugin_items()
    """
    root = Path("/usr/lib")
    plugins = []
    if root.is_dir():
        plugins = list(root.glob("*/qt5/plugins/platforms/libq*.so"))
    names = sorted({path.name for path in plugins})
    if "libqxcb.so" in names:
        status = STATUS_OK
        hint = ""
    else:
        status = STATUS_FAIL
        hint = "sudo apt install libqt5gui5"
    detail = ", ".join(names) if names else "keine Qt5-Platform-Plugins gefunden"
    return [item("Qt", "Platform-Plugins", status, detail, hint)]


def probe_pibackup() -> CheckItem:
    """Startet pibackup kurz mit Qt-Plugin-Debug und fängt die Ausgabe.

    Parameter:
        keine
    Rueckgabewert:
        CheckItem mit gekuerzter stderr/stdout.
    Fehlerfaelle:
        Binary fehlt, Timeout, Qt-Plugin-Fehler.
    Beispiel:
        probe_pibackup()
    """
    binary = find_pibackup_binary()
    if binary is None:
        return item("Probe", "Start", STATUS_FAIL, "pibackup nicht gefunden")
    extra = {
        "QT_DEBUG_PLUGINS": "1",
        "QT_QPA_PLATFORM": meta.QTFIX_PLATFORM,
    }
    argv = [str(binary)]
    timeout_bin = shutil.which("timeout")
    if timeout_bin:
        argv = [timeout_bin, "--signal=TERM", str(PROBE_TIMEOUT_SEC), str(binary)]
    probed = run_command(argv, timeout_sec=PROBE_TIMEOUT_SEC + 2, extra_env=extra)
    blob = (probed.stderr + "\n" + probed.stdout).strip()
    tail = " | ".join(blob.splitlines()[-12:]) if blob else f"exit {probed.returncode}"
    lowered = blob.lower()
    fail_marks = (
        "could not connect to display",
        "could not load the qt platform plugin",
        "no qt platform plugin could be initialized",
        "this application failed to start",
    )
    if any(mark in lowered for mark in fail_marks):
        return item(
            "Probe",
            "Start",
            STATUS_FAIL,
            tail,
            "Qt erreicht das Display nicht. Siehe Abschnitt Rechte/qtfix.",
        )
    if probed.returncode in {0, 124}:
        return item(
            "Probe",
            "Start",
            STATUS_WARN,
            tail or f"exit {probed.returncode}",
            "Prozess endete oder Timeout. Wenn ein Fenster kam, ist die GUI startfaehig.",
        )
    return item("Probe", "Start", STATUS_WARN, tail, f"Exit-Code {probed.returncode}")


def collect_all_items(facts: SessionFacts, do_probe: bool) -> list[CheckItem]:
    """Fuehrt alle Diagnoseabschnitte aus.

    Parameter:
        facts: Sitzungsdaten.
        do_probe: pibackup kurz starten.
    Rueckgabewert:
        flache Liste aller Befunde.
    Fehlerfaelle:
        Teilpruefungen liefern FAIL/WARN statt Exceptions.
    Beispiel:
        collect_all_items(collect_session_facts(), False)
    """
    items: list[CheckItem] = []
    items.extend(collect_system_items(facts))
    items.extend(collect_session_items(facts))
    items.extend(collect_rights_items(facts))
    items.extend(collect_package_items())
    items.extend(collect_binary_items())
    items.extend(collect_qt_plugin_items())
    if do_probe:
        items.append(probe_pibackup())
    return items


def format_report(items: list[CheckItem], facts: SessionFacts) -> str:
    """Baut den lesbaren Diagnosebericht.

    Parameter:
        items: Befunde.
        facts: Sitzungsdaten.
    Rueckgabewert:
        kompletter Bericht als Text.
    Fehlerfaelle:
        keine
    Beispiel:
        format_report([], collect_session_facts())
    """
    counts = count_status(items)
    lines = [
        f"{meta.DIAGNOSE_NAME} {meta.VERSION}  Stand {meta.STAND}",
        meta.BESCHREIBUNG,
        f"Zeit: {now_stamp()}",
        f"GUI-Anwendung: {meta.APP_BIN_NAME} {meta.GUI_APP_VERSION}",
        "",
        "Befunde",
        "-------",
    ]
    current = ""
    for entry in items:
        if entry.section != current:
            current = entry.section
            lines.append("")
            lines.append(f"[{current}]")
        lines.append(f"  [{entry.status:<4}] {entry.name}: {entry.detail}")
        if entry.hint:
            lines.append(f"         Hinweis: {entry.hint}")
    lines.extend(
        [
            "",
            "Zusammenfassung",
            "---------------",
            (
                f"OK={counts[STATUS_OK]}  WARN={counts[STATUS_WARN]}  "
                f"FAIL={counts[STATUS_FAIL]}  INFO={counts[STATUS_INFO]}"
            ),
            "",
            "Naechste Schritte",
            "-----------------",
        ]
    )
    session = facts.session_type or "(unbekannt)"
    for step in next_steps_for(items, session, facts.is_root):
        lines.append(f"- {step}")
    lines.append("")
    return "\n".join(lines)


def count_status(items: list[CheckItem]) -> dict[str, int]:
    """Zaehlt Statuswerte.

    Parameter:
        items: Befunde.
    Rueckgabewert:
        Map Status → Anzahl.
    Fehlerfaelle:
        keine
    Beispiel:
        count_status([])
    """
    counts = {STATUS_OK: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_INFO: 0}
    for entry in items:
        counts[entry.status] = counts.get(entry.status, 0) + 1
    return counts


def help_text() -> str:
    """Liefert den --help-Text gemaess Styleguide.

    Parameter:
        keine
    Rueckgabewert:
        Hilfetext.
    Fehlerfaelle:
        keine
    Beispiel:
        print(help_text())
    """
    return f"""{meta.BESCHREIBUNG}

Programm: {meta.DIAGNOSE_NAME}
Version:  {meta.VERSION}
Stand:    {meta.STAND}
Lizenz:   {meta.LIZENZ}

Verwendung:
  python3 pibackup_diagnose.py [Optionen]
  python3 pibackup_diagnose.py --help
  python3 pibackup_diagnose.py --version

Optionen:

  --help / -h
      Typ:          Flag
      Standardwert: aus
      Beschreibung: Diese Hilfe anzeigen und beenden.
      Beispiel:     python3 pibackup_diagnose.py --help

  --version
      Typ:          Flag
      Standardwert: aus
      Beschreibung: Versionsnummer, Datum und Programmbeschreibung.
      Beispiel:     python3 pibackup_diagnose.py --version

  --log
      Typ:          Flag
      Standardwert: aus
      Beschreibung: Bericht zusaetzlich in eine UTF-8-Logdatei schreiben.
      Beispiel:     python3 pibackup_diagnose.py --log

  --log-file
      Typ:          Pfad
      Standardwert: {DEFAULT_LOG_NAME} im aktuellen Verzeichnis (nur mit --log)
      Beschreibung: Logdatei setzen (ASCII-Name). Schaltet --log implizit ein.
      Beispiel:     python3 pibackup_diagnose.py --log-file pibackup_diagnose.log

  --probe
      Typ:          Flag
      Standardwert: aus
      Beschreibung: pibackup kurz starten (Timeout {PROBE_TIMEOUT_SEC}s) und
                    Qt-Fehlertexte auffangen. Kann ein Fenster oeffnen.
      Beispiel:     python3 pibackup_diagnose.py --probe
                    sudo python3 pibackup_diagnose.py --probe

  --fix-path
      Typ:          Flag
      Standardwert: aus
      Beschreibung: Sucht das Binary (typisch /usr/lib/pibackup/pibackup)
                    und legt den Konsolen-Befehl als Symlink
                    /usr/local/bin/pibackup an. Braucht root.
      Beispiel:     sudo python3 pibackup_diagnose.py --fix-path

  --Ende / -E
      Typ:          Flag
      Standardwert: aus
      Beschreibung: Am Ende auf Taste/Enter warten.
      Beispiel:     python3 pibackup_diagnose.py --Ende

Beispiele:
  python3 pibackup_diagnose.py --help
  python3 pibackup_diagnose.py --version
  python3 pibackup_diagnose.py --log
  python3 pibackup_diagnose.py --log --probe
  sudo python3 pibackup_diagnose.py --fix-path
  sudo python3 pibackup_diagnose.py --log --probe
"""


def version_text() -> str:
    """Liefert den --version-Text.

    Parameter:
        keine
    Rueckgabewert:
        Versionsblock.
    Fehlerfaelle:
        keine
    Beispiel:
        print(version_text())
    """
    return (
        f"{meta.DIAGNOSE_NAME} {meta.VERSION}\n"
        f"Stand: {meta.STAND}\n"
        f"{meta.BESCHREIBUNG}"
    )


class DiagnoseParser(argparse.ArgumentParser):
    """ArgumentParser mit deutscher Fehlerausgabe."""

    def error(self, message: str) -> None:
        """Bricht bei ungueltigen Angaben mit klarem Fehler ab.

        Parameter:
            message: argparse-Fehlertext.
        Rueckgabewert:
            keine (beendet den Prozess).
        Fehlerfaelle:
            immer Exit-Code 2.
        Beispiel:
            parser.error("unrecognized arguments: --foo")
        """
        sys.stderr.write(f"Fehler: ungueltige Angaben ({message})\n")
        sys.stderr.write("Hinweis: python3 pibackup_diagnose.py --help\n")
        raise SystemExit(EXIT_USAGE)


def build_parser() -> DiagnoseParser:
    """Erzeugt den Parser ohne Standard-Help.

    Parameter:
        keine
    Rueckgabewert:
        DiagnoseParser.
    Fehlerfaelle:
        keine
    Beispiel:
        build_parser()
    """
    parser = DiagnoseParser(
        prog="pibackup_diagnose.py",
        add_help=False,
        allow_abbrev=False,
    )
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--Ende", "-E", dest="ende", action="store_true")
    parser.add_argument("--log", action="store_true")
    parser.add_argument("--log-file", dest="log_file", default=None)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--fix-path", dest="fix_path", action="store_true")
    return parser


def parse_options(argv: list[str] | None = None) -> Options:
    """Liest die Kommandozeile.

    Parameter:
        argv: Argumente ohne Skriptname, oder None fuer sys.argv.
    Rueckgabewert:
        Options.
    Fehlerfaelle:
        unbekannte Schalter beenden mit Code 2.
    Beispiel:
        parse_options(["--log"])
    """
    parsed = build_parser().parse_args(argv)
    log_file = Path(parsed.log_file) if parsed.log_file else None
    log_enabled = bool(parsed.log or log_file)
    if log_enabled and log_file is None:
        log_file = Path(DEFAULT_LOG_NAME)
    return Options(
        show_help=bool(parsed.help),
        show_version=bool(parsed.version),
        wait_ende=bool(parsed.ende),
        log_enabled=log_enabled,
        log_file=log_file,
        probe=bool(parsed.probe),
        fix_path=bool(parsed.fix_path),
    )


def write_log(path: Path, report: str) -> None:
    """Schreibt den Bericht UTF-8 ohne BOM.

    Parameter:
        path: Zieldatei (ASCII-Name empfohlen).
        report: Berichtstext.
    Rueckgabewert:
        keine
    Fehlerfaelle:
        OSError wird nach oben gereicht.
    Beispiel:
        write_log(Path("pibackup_diagnose.log"), "ok")
    """
    line = f"{now_stamp()} {meta.DIAGNOSE_NAME} {meta.VERSION}\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.write(report)
        if not report.endswith("\n"):
            handle.write("\n")


def wait_for_ende() -> None:
    """Wartet auf Enter, wenn --Ende gesetzt ist.

    Parameter:
        keine
    Rueckgabewert:
        keine
    Fehlerfaelle:
        EOF (Pipe) wird ignoriert.
    Beispiel:
        wait_for_ende()
    """
    print('Programmende: "Hit any Key or Enter"')
    try:
        input()
    except EOFError:
        return


def resolve_log_path(path: Path) -> Path:
    """Prueft den Logpfad auf Schreibbarkeit.

    Parameter:
        path: Wunschpfad.
    Rueckgabewert:
        aufgeloester Pfad.
    Fehlerfaelle:
        ValueError bei leerem Namen oder nicht schreibbarem Ordner.
    Beispiel:
        resolve_log_path(Path("pibackup_diagnose.log"))
    """
    if path.name == "":
        raise ValueError("Logdatei ohne Dateinamen.")
    target = path.expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    parent = target.parent
    if not parent.exists():
        raise ValueError(f"Log-Verzeichnis existiert nicht: {parent}")
    if not os.access(parent, os.W_OK):
        raise ValueError(f"Log-Verzeichnis nicht schreibbar: {parent}")
    return target


def run_diagnose(options: Options) -> int:
    """Fuehrt Hilfe, Version oder den vollen Diagnosebericht aus.

    Parameter:
        options: ausgewertete CLI.
    Rueckgabewert:
        Prozess-Exitcode.
    Fehlerfaelle:
        Logfehler werden gemeldet und als Code 1 gewertet.
    Beispiel:
        run_diagnose(parse_options([]))
    """
    if options.show_help:
        print(help_text())
        return EXIT_OK
    if options.show_version:
        print(version_text())
        return EXIT_OK
    if options.fix_path:
        return run_fix_path()
    facts = collect_session_facts()
    items = collect_all_items(facts, options.probe)
    report = format_report(items, facts)
    print(report)
    if options.log_enabled and options.log_file is not None:
        try:
            log_path = resolve_log_path(options.log_file)
            write_log(log_path, report)
            print(f"Logdatei: {log_path}")
        except (OSError, ValueError) as exc:
            print(f"Fehler: Logdatei nicht schreibbar ({exc})", file=sys.stderr)
            return EXIT_PROBLEM
    if count_status(items)[STATUS_FAIL] > 0:
        return EXIT_PROBLEM
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    """Einstieg: CLI auswerten, Diagnose laufen lassen, optional warten.

    Parameter:
        argv: Argumente ohne Skriptname oder None.
    Rueckgabewert:
        Exitcode 0, 1 oder 2.
    Fehlerfaelle:
        ungueltige CLI-Optionen, Logfehler, FAIL-Befunde.
    Beispiel:
        main(["--help"])
    """
    options = parse_options(argv)
    code = EXIT_OK
    try:
        code = run_diagnose(options)
    except SystemExit as exc:
        code = int(exc.code) if isinstance(exc.code, int) else EXIT_USAGE
    if options.wait_ende:
        wait_for_ende()
    return code


if __name__ == "__main__":
    sys.exit(main())
