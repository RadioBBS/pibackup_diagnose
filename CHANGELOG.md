# Changelog

```
pibackup_diagnose – Release-Historie.

Projekt:     pibackup_diagnose
Modul:       CHANGELOG.md
Version:     1.1.0
Stand:       2026-08-24
Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.10)
Bezug:       requirements.txt (leer – Stdlib only)
Lizenz:      MIT
Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
Erstellt mit: Cursor Grok 4.6
Autor:       (FFHB) / RadioBBS
```

Alle wesentlichen Aenderungen dieses Produkts.

## [1.1.0] – 2026-08-24

### Fixed

- pibackup liegt im .deb unter `/usr/lib/pibackup/pibackup` und fehlt im PATH.
  Suche erweitert; `sudo python3 pibackup_diagnose.py --fix-path` legt
  `/usr/local/bin/pibackup` an.


## [1.0.0] – 2026-08-24

### Added

- Diagnose-Skript fuer GUI-Startprobleme von pibackup unter Wayland, sudo/root und Qt5/xcb.
- Eigenes Git-Projekt, aus dem Repository pibackup ausgelagert.
