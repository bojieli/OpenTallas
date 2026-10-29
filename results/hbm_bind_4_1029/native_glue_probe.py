#!/usr/bin/env python3
"""HBM-BIND-4: emit main bind_native_glue helpers for every actual flat $shift/$shiftx cell (outside bind,
because strict-bind emission currently stops earlier at a reset EMIT) so glue_equiv.py can prove them."""
import json, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools' / 'die_plan'))
import bind_elab as E, bind_native_glue as NG
src, outd = Path(sys.argv[1]), Path(sys.argv[2])
F = E.flatten(json.loads(src.read_text()), 'hbm_current_native_top')
cells = [c for c in F.cells if c.ytype in ('$shift', '$shiftx')]
G = NG.NativeGlue(outd, ['$shift', '$shiftx'])
for i, c in enumerate(cells):
    G.emit(c, {p: f'n{i}_{p}' for p in c.ports}, f'g{i}')
print(json.dumps(dict(flat_cells=len(cells), by_type=dict(collections.Counter(c.ytype for c in cells)), helpers=len(G.files))))
