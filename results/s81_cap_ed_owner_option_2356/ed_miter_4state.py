#!/usr/bin/env python3
"""Four-state variant of ed_miter.py (X injected on i_f every 31 edges; literal old-if semantics hold the sticky)."""
import subprocess, sys
from pathlib import Path
sys.exit(subprocess.call([sys.executable, str(Path(__file__).with_name('ed_miter.py')), '--four-state'] + sys.argv[1:]))
