#!/usr/bin/env python3
"""Regenerate dsdv_mu_hwin_c22q: ref_tile gen + c21h band hooks + c21q OPT_POST_GRT_WNS=0."""
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[3]
kit = Path(__file__).resolve().parent
rc = subprocess.run(['python3', str(root/'tools/ref_tile/ref_tile.py'), 'gen', str(kit/'spec.json')], cwd=root).returncode
with (kit/'place.tcl').open('a') as out:
    out.write('\n# Row pruning must precede tapcell; physical core and macro placements remain unchanged.\nsource /src/physical/ref_tile/dsdv_mu_hwin_c22q/hwin_cell_band.tcl\n')
with (kit/'pre_grt.tcl').open('a') as out:
    out.write('\n# c21q: skip ORFS post-GRT vt_swap/reroute WNS pass (EST-0104 class)\nset ::env(OPT_POST_GRT_WNS) 0\nputs "HWIN_OPT_POST_GRT_WNS=0"\n')
raise SystemExit(rc)
