# Chat-Auszug: Python-Umarbeitung, Diagnose, Pi-GUI

```
pibackup_diagnose – Chat-Auszug (Python-Weg, Diagnose, Debian-12-GUI).

Projekt:     pibackup_diagnose
Modul:       docs/chat-python-umstellung.md
Version:     1.1.0
Stand:       2026-08-24
Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.10)
Bezug:       requirements.txt (leer – Stdlib only)
Lizenz:      MIT
Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
Erstellt mit: Cursor Grok 4.6
Autor:       (FFHB) / RadioBBS
```

Auszug aus dem Cursor-Chat vom 2026-08-24, ab der Bewertung
„Umarbeiten nach Python“ bis zur Auswertung der Diagnose-Logs.
Tool-Aufrufe und interne Schritte sind weggelassen. Pfade in der Doku
nutzen Systemplatzhalter, keine Anmeldenamen.

---

## Umarbeiten nach Python: ja, das ist der sinnvollere Weg

Die Fachlogik von pibackup ist gut auf Python übertragbar, weil sie schon
auf Standard-Linux-Tools sitzt (`losetup`, `e2fsck`, `resize2fs`, `zstd`,
`mount`, `chroot`). Python auf dem Pi ist vorhanden, wartbar und
unabhängig von CodeTyphon.

| Bereich | Aufwand | Hinweis |
|---|---|---|
| Image lesen/schreiben, Loop-Devices, `e2fsck`/`resize2fs` | mittel | 1:1 nachvollziehbar |
| MBR, PARTUUID, `fstab`/`cmdline.txt` | mittel, aber kritisch | hier sitzt die Boot-Sicherheit |
| Exclude-Engine, User/SSH/WLAN-Setup | gering–mittel | klar abgegrenzt |
| zstd mit Fortschritt | gering | `zstandard` oder CLI `zstd` |
| GUI | mittel | nicht Qt5 als root |

**Wichtig:** nicht die aktuelle Architektur kopieren (eine Qt-App als
root). Besser trennen:

1. **Engine (CLI, root)** – Backup, Restore, Clone
2. **GUI als normaler User** – startet die Engine per `pkexec`/`sudo`
   nur für die Schreibaktion

Dann braucht die Oberfläche kein X11-Root-Display. Noch robuster auf dem
Pi: **lokale Web-UI** (Browser, auch per SSH-Tunnel) plus CLI für
Rescue-Karten ohne Desktop.

Grober Umfang: etwa 4000–6000 Zeilen Pascal, davon viel GUI-Kleber. Eine
Python-Engine plus Tkinter oder PySide und CLI ist realistisch in
ähnlicher Größenordnung, aber deutlich einfacher zu bauen und zu
debuggen.

Tkinter (`python3-tk`) ist auf Raspberry Pi OS Desktop oft schon da.
PyQt5 hätte dieselben Wayland-Fallen, wenn die GUI wieder als root
startet.

### Empfehlung (Stand Analyse)

1. **Jetzt:** auf dem Pi prüfen, ob es ein Display-/sudo-Problem ist.
   Oft reicht X11-Sitzung oder `xhost` + `sudo -E`.
2. **Mittelfristig:** **Python-Neuimplementierung** mit getrennter Engine
   und GUI/CLI, nicht CodeTyphon neu aufsetzen.
3. **Nicht** die Pascal-GUI 1:1 nach PyQt portieren und weiter als
   `sudo pibackup` starten – das Problem bleibt.

pibackup erzwingt in `qtfix.pas` `QT_QPA_PLATFORM=xcb` und
`XDG_RUNTIME_DIR=/run/user/0`. Getestet laut Upstream: Trixie + X11,
nicht Bookworm + Wayland.

---

## Nutzer: Es läuft Wayland, baue ein Diagnose-Skript für den Pi

Antwort: eigenständiges Python-Skript (Stdlib), später ausgelagert nach
`%USERPROFILE%\Documents\Cursor\GIT-Projects\pibackup_diagnose`.

Prüft unter anderem:

- Sitzung (Wayland/X11, wayfire/labwc, XWayland, xhost)
- qtfix (`xcb`, `/run/user/0`)
- `sudo` streift `DISPLAY` / `WAYLAND_DISPLAY`
- Wayland-Socket für root unlesbar
- Pakete, Binary, `ldd`, Qt-Plugins
- optional `--probe` (pibackup kurz starten, Qt-Fehler auffangen)

Auf den Pi gehören im **gleichen** Ordner:

- `pibackup_diagnose.py`
- `project_meta.py`
- optional `pibackup_diagnose.sh`

### Kopieren (PowerShell auf dem PC)

```powershell
cd $env:USERPROFILE\Documents\Cursor\GIT-Projects\pibackup_diagnose
ssh <pi-benutzer>@<pi-host> "mkdir -p ~/pibackup_diagnose"
scp pibackup_diagnose.py project_meta.py pibackup_diagnose.sh <pi-benutzer>@<pi-host>:~/pibackup_diagnose/
```

### Auf dem Pi (grafisches Desktop-Terminal, nicht nur SSH ohne Display)

```bash
cd "$HOME/pibackup_diagnose"
python3 pibackup_diagnose.py --help
python3 pibackup_diagnose.py --version
python3 pibackup_diagnose.py --log
sudo python3 pibackup_diagnose.py --log --probe
```

`--help` / `--version` ohne sudo. `--probe` startet pibackup kurz
(ca. 6 s). Protokoll: `pibackup_diagnose.log` (UTF-8 ohne BOM).

---

## Nutzer: Dateien nach pibackup_diagnose verschieben und Anwendung auf dem Pi zeigen

Das Diagnose-Tool ist ein **eigenes Git-Projekt**:

`%USERPROFILE%\Documents\Cursor\GIT-Projects\pibackup_diagnose`

Aus dem Pascal-Projekt `pibackup` wurden die Diagnose-Dateien entfernt
(dort nur noch ein Verweis).

---

## Nutzer: Auf der Konsole wird pibackup nicht gefunden – zuerst lösen

Ursache: Das `.deb` installiert nach

`/usr/lib/pibackup/pibackup`

und **nicht** nach `/usr/bin`. Deshalb `command not found`, obwohl
`dpkg` das Paket als installiert zeigt. Das Menü „Utility → PiBackup“
nutzt den vollen Pfad.

### Sofort

```bash
ls -l /usr/lib/pibackup/pibackup
dpkg -L pibackup | grep pibackup
sudo /usr/lib/pibackup/pibackup
```

Damit der Befehl `pibackup` existiert:

```bash
cd "$HOME/pibackup_diagnose"
sudo python3 pibackup_diagnose.py --fix-path
command -v pibackup
```

oder:

```bash
sudo ln -sf /usr/lib/pibackup/pibackup /usr/local/bin/pibackup
```

Skript-Version dafür: **1.1.0** (sucht `/usr/lib/pibackup/pibackup`,
`--fix-path`).

---

## Nutzer: Diagnose-Logs ohne/mit sudo

Auswertung der beiden Berichte (Bookworm, Kernel 6.12, Python 3.11,
wayfire + XWayland, pibackup 2.1.0).

| Befund | Ohne sudo | Mit sudo |
|---|---|---|
| System | Debian 12, ARM64, Wayland | gleich |
| Paket | installiert, Binary unter `/usr/lib/pibackup/pibackup` | gleich |
| Befehl `pibackup` | nicht im PATH | nicht im PATH |
| Display | `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-1` | `DISPLAY=:0` bleibt, Wayland-Socket von root nicht die User-Sitzung |
| Probe | nicht gelaufen | Qt lädt Plugins, dann Absturz |

**Eigentlicher GUI-Absturz (Probe, Exit 127):**

```text
/usr/lib/pibackup/pibackup: symbol lookup error:
undefined symbol: QGuiApplication_setFallbackSessionManagementEnabled
```

pibackup ist mit CodeTyphon/neuerem Lazarus-Qt5 gebaut. Debian 12 liefert
`libqt5pas1` **2.6+2.2.0** – darin fehlt das Symbol.

`libxcb-cursor0`: auf Bookworm kein treffendes Paket (eher Qt6).
Kann ignoriert werden.

`xhost` ist noch restriktiv. Das wird erst relevant, **nachdem** die
Bibliothek passt. Qt kam in der Probe bereits bis zu den Plugins – der
Start bricht an `libQt5Pas` ab, nicht am fehlenden Display.

### Reihenfolge auf dem Pi

**1. PATH**

```bash
cd "$HOME/pibackup_diagnose"
sudo python3 pibackup_diagnose.py --fix-path
command -v pibackup
```

**2. Passende libQt5Pas (GUI-Absturz)**

ARM64-Paket z. B. [libqt5pas v1.2.16](https://github.com/davidbannon/libqt5pas/releases/tag/v1.2.16)
(`libqt5pas1_2.16-4_arm64.deb`):

```bash
cd /tmp
wget -O libqt5pas1_arm64.deb \
  "https://github.com/davidbannon/libqt5pas/releases/download/v1.2.16/libqt5pas1_2.16-4_arm64.deb"
sudo apt install ./libqt5pas1_arm64.deb
nm -D /usr/lib/aarch64-linux-gnu/libQt5Pas.so.1 | grep FallbackSession
```

Es muss eine Zeile mit `QGuiApplication_setFallbackSessionManagementEnabled`
erscheinen.

**3. Start unter Wayland**

```bash
xhost +SI:localuser:root
sudo -E env QT_QPA_PLATFORM=xcb DISPLAY="$DISPLAY" \
  XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
  /usr/lib/pibackup/pibackup
```

Ohne Schritt 2 bleibt `symbol lookup error`, egal ob PATH und `xhost`
stimmen. Optional danach: `raspi-config` → Advanced Options → Wayland →
X11, neu anmelden.

---

## Mittelfristig (zurück zur Python-Empfehlung)

Die Logs bestätigen die Analyse: Wayland+sudo ist unbequem, der harte
Blocker auf Bookworm ist aber die **Qt5Pas-ABI**. Eine Python-Engine mit
GUI als User (pkexec nur für Schreibaktionen) umgeht CodeTyphon, Qt5Pas
und Root-Display zugleich.

Nicht empfehlenswert: Pascal-GUI 1:1 nach PyQt portieren und weiter als
`sudo pibackup` starten.
