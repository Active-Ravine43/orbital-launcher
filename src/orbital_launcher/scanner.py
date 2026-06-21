"""Orbital Launcher — desktop entry scanner.

Walks .desktop file directories, parses entries, and maintains a
JSON cache at XDG_DATA_HOME/orbital-launcher/apps_cache.json.
"""

import configparser
import json
import sys
from pathlib import Path
from typing import Optional

from .config import CACHE_FILE, DESKTOP_DIRS


def desktop_scan(force: bool = False) -> list[dict]:
    """
    Walk desktop-file directories, parse .desktop files,
    return a list of dicts with keys: name, icon_name, exec, terminal, desktop_file.
    Uses and updates apps_cache.json.
    """

    # Check cache freshness
    if not force and CACHE_FILE.exists():
        try:
            cache_mtime = CACHE_FILE.stat().st_mtime
            stale = False
            for d in DESKTOP_DIRS:
                if not d.exists():
                    continue
                for f in d.glob("*.desktop"):
                    if f.stat().st_mtime > cache_mtime:
                        stale = True
                        break
                if stale:
                    break
            if not stale:
                with open(CACHE_FILE) as fh:
                    data = json.load(fh)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception:
            pass

    entries = []
    for d in DESKTOP_DIRS:
        if not d.exists():
            continue
        for fpath in sorted(d.glob("*.desktop")):
            try:
                e = _parse_desktop_file(fpath)
                if e:
                    entries.append(e)
            except Exception:
                print(f"[orbital-launcher] WARN: skipping {fpath}", file=sys.stderr)

    # Deduplicate by name: prefer entry with non-empty exec
    seen = {}
    for e in entries:
        key = e["name"].lower()
        if key not in seen or (e["exec"] and not seen[key]["exec"]):
            seen[key] = e
    entries = list(seen.values())

    # Cache
    try:
        with open(CACHE_FILE, "w") as fh:
            json.dump(entries, fh, indent=2)
    except Exception:
        pass

    return entries


def _parse_desktop_file(path: Path) -> Optional[dict]:
    """Parse a single .desktop file. Returns None if should be skipped."""
    c = configparser.ConfigParser(interpolation=None)
    # .desktop files have no [DEFAULT] section; read raw
    try:
        with open(path) as fh:
            content = fh.read()
    except Exception:
        return None

    # Minimal: uppercase the [Desktop Entry] header which might be mixed-case
    # configparser is case-insensitive for section headers
    c.read_string(content)

    if not c.has_section("Desktop Entry"):
        return None

    s = c["Desktop Entry"]

    # Skip hidden / no-display entries
    if s.getboolean("NoDisplay", fallback=False):
        return None
    if s.getboolean("Hidden", fallback=False):
        return None

    name = s.get("Name", path.stem)
    icon = s.get("Icon", "")
    exec_cmd = s.get("Exec", "")
    terminal = s.getboolean("Terminal", fallback=False)

    if not exec_cmd:
        return None

    # Strip field codes per desktop entry spec
    exec_cmd = _clean_exec(exec_cmd)

    return {
        "name": name,
        "icon_name": icon,
        "exec": exec_cmd,
        "terminal": terminal,
        "desktop_file": str(path),
    }


def _clean_exec(cmd: str) -> str:
    """Remove freedesktop field codes from an Exec value."""
    for code in ["%f", "%F", "%u", "%U", "%i", "%c", "%k", "%d", "%D",
                 "%n", "%N", "%v", "%m"]:
        cmd = cmd.replace(f" {code}", "")
        cmd = cmd.replace(code, "")
    return cmd.strip()
