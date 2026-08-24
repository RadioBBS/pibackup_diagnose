# pibackup_diagnose

```
pibackup_diagnose – Diagnose fuer die pibackup-GUI unter Wayland/Qt5.

Projekt:     pibackup_diagnose
Modul:       README.md
Version:     1.1.0
Stand:       2026-08-24
Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.10)
Bezug:       requirements.txt (leer – Stdlib only)
Lizenz:      MIT
Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
Erstellt mit: Cursor Grok 4.6
Autor:       (FFHB) / RadioBBS
```

## Zweck

Prueft auf einem Raspberry Pi (Debian GNU/Linux 12, Wayland), warum die
**pibackup**-GUI nach der Installation nicht erscheint. Das Skript aendert
nichts am System (ausser optional `--probe`, das pibackup kurz startet).

Fuer wen: Betrieb am Pi-Desktop, wenn `sudo pibackup` kein Fenster oeffnet.

## Voraussetzungen

- Raspberry Pi mit Desktop (nicht Lite ohne grafische Sitzung)
- Python 3.10 oder neuer (Debian 12: `python3`)
- pibackup darf, muss aber nicht bereits installiert sein
- Aufruf in einem Terminal **auf dem grafischen Desktop**
  (nicht nur per SSH ohne Display)

Keine pip-Pakete noetig. Optional:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Aufruf

`--help` und `--version` ohne sudo. Die Volldiagnose zuerst als Desktop-User,
danach einmal mit sudo (Root-Umgebung von `sudo pibackup`).

```bash
python3 pibackup_diagnose.py --help
python3 pibackup_diagnose.py --version
python3 pibackup_diagnose.py --log
sudo python3 pibackup_diagnose.py --log --probe
```

## Anwendung auf dem Raspberry Pi

### 0. Befehl `pibackup` auf der Konsole (zuerst)

Das Debian-Paket legt das Programm **nicht** nach `/usr/bin`, sondern nach:

`/usr/lib/pibackup/pibackup`

Deshalb antwortet die Konsole mit `command not found`, obwohl das Paket
installiert ist. Sofort nutzbar:

```bash
ls -l /usr/lib/pibackup/pibackup
sudo /usr/lib/pibackup/pibackup
```

Damit `pibackup` als Befehl funktioniert (Symlink nach `/usr/local/bin`):

```bash
cd "$HOME/pibackup_diagnose"
sudo python3 pibackup_diagnose.py --fix-path
command -v pibackup
```

`--help` und `--version` bleiben ohne sudo. `--fix-path` braucht root.

### 1. Dateien auf den Pi kopieren

Vom Windows-PC (PowerShell), Projektordner:

```powershell
cd $env:USERPROFILE\Documents\Cursor\GIT-Projects\pibackup_diagnose
scp pibackup_diagnose.py project_meta.py pibackup_diagnose.sh <pi-benutzer>@<pi-host>:~/pibackup_diagnose/
```

`<pi-benutzer>` und `<pi-host>` durch den SSH-Login des Pi ersetzen
(z. B. Hostnamen oder IP). Beide `.py`-Dateien muessen im **gleichen**
Verzeichnis liegen.

Ohne scp: die drei Dateien auf einen USB-Stick legen und auf dem Pi nach
`$HOME/pibackup_diagnose/` kopieren.

### 2. Auf dem Pi: Desktop-Terminal oeffnen

Am Pi an der grafischen Oberflaeche anmelden. Ein Terminal oeffnen
(nicht eine reine SSH-Sitzung ohne `DISPLAY`/`WAYLAND_DISPLAY`).

```bash
cd "$HOME/pibackup_diagnose"
chmod +x pibackup_diagnose.sh
python3 pibackup_diagnose.py --log
sudo python3 pibackup_diagnose.py --fix-path
```

### 3. Dieselbe Diagnose als root

```bash
sudo python3 pibackup_diagnose.py --log --probe
```

`--probe` startet pibackup etwa 6 Sekunden und faengt Qt-Fehler ein
(z. B. `could not connect to display`). Es kann kurz ein Fenster erscheinen.

Logdatei im aktuellen Verzeichnis: `pibackup_diagnose.log` (UTF-8 ohne BOM).

### 4. Bericht lesen

Am Ende stehen **Naechste Schritte**. Typisch unter Wayland:

```bash
xhost +SI:localuser:root
sudo -E env QT_QPA_PLATFORM=xcb DISPLAY="$DISPLAY" XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" pibackup
```

Oder in `raspi-config` unter Advanced Options die Sitzung auf **X11**
umstellen, neu anmelden, danach `sudo pibackup`.

## Risiken

- `--fix-path` legt einen Symlink in `/usr/local/bin` an (nur das).
- `--probe` startet die pibackup-GUI kurz; pibackup selbst kann bei
  Fehlbedienung Daten loeschen. Probe nur zur Display-Pruefung nutzen,
  keine Backup-/Restore-Aktion ausloesen.
- `xhost +SI:localuser:root` erlaubt root den Zugriff auf die grafische
  Sitzung (nur solange noetig).

## Dokumentation

Chat-Auszug (Python-Weg, Diagnose, Debian-12-Logs):
`docs/chat-python-umstellung.md`

## Tests

```bash
python3 -m unittest tests.test_pibackup_diagnose
```

## Lizenz

MIT – siehe `LICENSE`.
