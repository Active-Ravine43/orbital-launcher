#!/bin/bash
# Orbital Launcher toggle — called by Hyprland keybind (e.g. SUPER+O)
# Sends SIGUSR1 to running instance, or launches a new one.
# Works from any clone location — auto-locates launcher.py relative to itself.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="/tmp/orbital-launcher.pid"
LAUNCHER="$SCRIPT_DIR/launcher.py"

PID=$(cat "$PID_FILE" 2>/dev/null)

if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    kill -USR1 "$PID"
else
    # Clean up stale PID file
    rm -f "$PID_FILE"
    python "$LAUNCHER" &
fi
