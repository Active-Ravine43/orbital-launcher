#!/usr/bin/env python3
"""Orbital Launcher — thin entry point.

Adds src/ to sys.path and delegates to the orbital_launcher package.
Preserves the simple `python launcher.py` invocation from the repo root.
"""

import os
import sys

# Ensure the repo root is discoverable so imports resolve
_REPO = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(_REPO, "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from orbital_launcher.app import main

sys.exit(main())
