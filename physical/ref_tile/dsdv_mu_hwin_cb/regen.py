#!/usr/bin/env python3
"""Regenerate central HWIN kit; prune rows before tapcell without shrinking paid core."""
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[3]
kit = Path(__file__).resolve().parent
rc = subprocess.run(['python3', str(root/'tools/ref_tile/ref_tile.py'), 'gen', str(kit/'spec.json')], cwd=root).returncode
with (kit/'place.tcl').open('a') as out:
    out.write('\n# Row pruning must precede tapcell; physical core and macro placements remain unchanged.\nsource /src/physical/ref_tile/dsdv_mu_hwin_cb/hwin_cell_band.tcl\n')
raise SystemExit(rc)
