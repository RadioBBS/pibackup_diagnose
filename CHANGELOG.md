# Changelog

```
pibackup_diagnose – Release-Historie.

Projekt:     pibackup_diagnose
Modul:       CHANGELOG.md
Version:     1.2.1
Stand:       2026-11-02
Abhaengig:   nur Python-Standardbibliothek (Python ≥ 3.11)
Bezug:       requirements.txt (leer – Stdlib only)
Lizenz:      MIT
Upstream:    https://github.com/RaspberryFpc/pibackup (RaspberryFpc)
Erstellt mit: Cursor Grok 4.6
Autor:       (FFHB) / RadioBBS

Historie
--------
Version 1.2.1 – 2026-11-02 – Startausgabe und Python 3.11 nach Styleguide 2.1.0.
```

Alle wesentlichen Aenderungen dieses Produkts.

## [1.2.1] – 2026-11-02

### Changed

- Startausgabe: hellcyaner Rahmen mit Kurzname, Zweckzeile, Version und Stand.
- Python-Untergrenze 3.11.
- Plattformprüfung: Windows 11 und Linux.

## [1.2.0] – 2026-08-24

### Added

- Maschinenlesbare Produktdateien: `PROJECT.yaml`, `pyproject.toml`,
  `CITATION.cff` und `.github/workflows/ci.yml` (Software-Standard 1.2.0).
- Unittest prueft, dass Version in YAML/TOML mit `project_meta.py` uebereinstimmt.

## [1.1.0] – 2026-08-24

### Fixed

- pibackup liegt im .deb unter `/usr/lib/pibackup/pibackup` und fehlt im PATH.
  Suche erweitert; `sudo python3 pibackup_diagnose.py --fix-path` legt
  `/usr/local/bin/pibackup` an.


## [1.0.0] – 2026-08-24

### Added

- Diagnose-Skript fuer GUI-Startprobleme von pibackup unter Wayland, sudo/root und Qt5/xcb.
- Eigenes Git-Projekt, aus dem Repository pibackup ausgelagert.
