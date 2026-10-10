#!/usr/bin/env python3
"""Read-only remote inventory gate before the authorized minimum pair route."""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
required = {
    'tools/run_abi3_physical.py', 'tools/orfs_hold_mm.py',
    'tools/orfs_hold_mm.tcl', 'tools/orfs_allcorner_spef.py',
    'tools/fp_margin_lint.tcl', 'tools/preroute_gate.tcl',
    'tools/w18/corner_sta.py', 'tools/w18/export_view.py',
    'physical/abi3/v41x_karb_repair_buffer_cap.tcl',
    'physical/dsrom_markov_lookup_pair/route.sh',
    'physical/dsrom_markov_lookup_pair/macro_capture.sdc',
    'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_port_pp.sv',
}
macro = 'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8'
required.update(macro + suffix for suffix in
                ['_bb.v', '.lef', '_ss.lib', '_tt.lib', '_ff.lib'])
# Include the patcher's transitive static /src/tools script references.
for name in ['tools/run_abi3_physical.py', 'tools/orfs_hold_mm.py',
             'tools/orfs_hold_mm.tcl', 'tools/orfs_allcorner_spef.py']:
    required.update(re.findall(r'(?:/src/)?(tools/[A-Za-z0-9_./-]+\.(?:py|tcl))',
                               (root / name).read_text()))
missing = sorted(name for name in required if not (root / name).is_file())
for name in sorted(required):
    if name.endswith('.py') and (root / name).is_file():
        ast.parse((root / name).read_text(), filename=name)
subprocess.run(['bash', '-n', str(root / 'physical/dsrom_markov_lookup_pair/route.sh')],
               check=True)
record = dict(passed=not missing, missing=missing,
              scope='read-only syntax and transitive helper inventory; no synthesis or physical qualification',
              files={name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                     for name in sorted(required) if (root / name).is_file()})
print(json.dumps(record, indent=2))
raise SystemExit(0 if record['passed'] else 1)
