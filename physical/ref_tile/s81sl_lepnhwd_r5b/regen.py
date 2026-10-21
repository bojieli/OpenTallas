#!/usr/bin/env python3
"""r4m: plain ref_tile gen (no region hooks); full core rows kept."""
import subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[3];kit=Path(__file__).resolve().parent
raise SystemExit(subprocess.run(['python3',str(root/'tools/ref_tile/ref_tile.py'),'gen',str(kit/'spec.json')],cwd=root).returncode)
