#!/bin/bash
# Orbital Launcher toggle — called by Hyprland keybind (SUPER+O)
# Sends SIGUSR1 to running instance, or launches a new one.
# Works from any location — auto-locates launcher.py relative to itself.

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
PID_FILE="/tmp/orbital-launcher.pid"
TARGET_FILE="/tmp/orbital-launcher-target"
LAUNCHER="$SCRIPT_DIR/launcher.py"

PID=$(cat "$PID_FILE" 2>/dev/null)

if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    # Running instance exists — determine which display the cursor is on
    # and toggle only that one. Falls back to all if hyprctl isn't available.
    TARGET=""
    if command -v hyprctl &>/dev/null; then
        CURSOR=$(hyprctl cursorpos 2>/dev/null)
        if [ -n "$CURSOR" ]; then
            CURSOR_X=$(echo "$CURSOR" | cut -d',' -f1 | tr -d ' ')
            CURSOR_Y=$(echo "$CURSOR" | cut -d',' -f2 | tr -d ' ')
            MONITORS=$(hyprctl monitors -j 2>/dev/null)
            if [ -n "$MONITORS" ]; then
                TARGET=$(echo "$MONITORS" | python3 -c "
import json, sys
monitors = json.load(sys.stdin)
x, y = float('$CURSOR_X'), float('$CURSOR_Y')
for m in monitors:
    if m['x'] <= x < m['x'] + m['width'] and m['y'] <= y < m['y'] + m['height']:
        print(m['name'])
        break
")
            fi
        fi
    fi
    echo "${TARGET:-}" > "$TARGET_FILE"
    kill -USR1 "$PID"
else
    # No running instance — clean up and launch fresh
    rm -f "$PID_FILE" "$TARGET_FILE"
    # Kill any orphaned launcher processes that lost their PID file
    pkill -f "orbital_launcher" 2>/dev/null || true
    # Preload layer-shell to fix Wayland linker ordering
    LD_PRELOAD=/usr/lib/libgtk4-layer-shell.so python "$LAUNCHER" &
fi
