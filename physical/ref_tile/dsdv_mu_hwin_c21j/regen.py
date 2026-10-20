#!/usr/bin/env python3
"""Regenerate central HWIN kit; prune rows before tapcell without shrinking paid core."""
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[3]
kit = Path(__file__).resolve().parent
rc = subprocess.run(['python3', str(root/'tools/ref_tile/ref_tile.py'), 'gen', str(kit/'spec.json')], cwd=root).returncode
if rc:
    raise SystemExit(rc)
with (kit/'place.tcl').open('a') as out:
    out.write('\n# Row pruning must precede tapcell; physical core and macro placements remain unchanged.\nsource /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_cell_band.tcl\n')
# Each ORFS stage is a fresh Tcl process. Install wrappers before its repairs.
for name in ('pre_cts.tcl', 'pre_grt.tcl', 'pre_drt.tcl', 'pre_fill.tcl'):
    path = kit/name
    path.write_text('source /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl\n' + path.read_text())
for name in ('post_cts.tcl', 'post_grt.tcl', 'post_drt.tcl', 'post_fill.tcl'):
    with (kit/name).open('a') as out:
        out.write('\nsource /src/physical/ref_tile/dsdv_mu_hwin_c21j/hwin_native_fences.tcl\not_hj_fences_install\not_hj_assign_births 0\not_hj_fences_check ' + name + '\n')
raise SystemExit(rc)
