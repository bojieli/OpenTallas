#!/usr/bin/env python3
"""Omit the final southbound landing in a PRIVATE source snapshot only."""
import hashlib
import json
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
path = root / 'rtl/dsrom_sys/s81_dv/unit/bk/plana/lp/dsdv_bk_sel_pa_lp.sv'
original = path.read_bytes()
needle = 'assign rung_s_out_d6__l_r37 = lpl_210_o;'
assert original.decode().count(needle) == 1
mutant = original.decode().replace(needle, 'assign rung_s_out_d6__l_r37 = rung_s_out_d6; // MUTANT: omit final +2-edge landing')
path.write_text(mutant)
(root / 'output_landing_mutant.json').write_text(json.dumps({
    'mutation': 'final southbound landing210 bypassed; all other RTL/calendar bytes unchanged',
    'source_sha256': hashlib.sha256(original).hexdigest(),
    'mutant_sha256': hashlib.sha256(mutant.encode()).hexdigest(),
    'expected_effect': 'all southbound output beats two edges early; fixed compiler calendar must reject',
}, indent=2) + '\n')
