#!/usr/bin/env python3
"""Generate the standard kits, then append the leaf-local clock adapter."""
from pathlib import Path
import subprocess
ROOT = Path(__file__).resolve().parents[2]
for leaf in ('head', 'tree'):
    subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen',
                    f'tools/ref_tile/specs_qttsplit/qfd_tt_ctlm_{leaf}.json'], cwd=ROOT, check=True)
    if leaf == 'tree':
        p = ROOT / 'physical/ref_tile/qfd_tt_ctlm_tree/pre_cts.tcl'
        p.write_text(p.read_text() + 'source /src/physical/qfd_tt_ctlm_split/dual_clock_spine.tcl\n')
