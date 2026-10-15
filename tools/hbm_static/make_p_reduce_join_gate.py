#!/usr/bin/env python3
"""Native source/reducer join fixture; SCscaled and E are declared VM inputs.

This deliberately does not claim the missing upstream SFU computation.
"""
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np

spec = importlib.util.spec_from_file_location('reducer', sys.argv[1])
reducer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reducer)
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
p = reducer.Program()
# Fill boundaries are explicit setup gaps before each head and E reread.
fills = []
for rows in (128, 640):
    for head in range(16):
        tag = len(p.rows)
        fill_start = p.c
        fills.append((fill_start, rows, 0, tag))
        p.c += rows // 64 + 2
        sc = (1 + np.arange(rows, dtype=np.float32) / 1024).astype(np.float32)
        e = np.ones(rows, dtype=np.float32)
        before = len(p.commands)
        p.row(sc, tag, sum_values=e)
        sources = [s for s in p.sources if s[1] == tag]
        first_sum = next(s[0] for s in sources if s[2] == 'SUM_UNROUNDED_E')
        fills.append((first_sum - rows // 64 - 1, rows, 1, tag))
        p.c += 20
sources = {r[0]: r for r in p.sources}
(out/'commands.txt').write_text(''.join(' '.join(map(str, (*r, sources[r[0]][3] if r[0] in sources else 0, int(r[0] in sources))))+'\n' for r in p.commands))
(out/'expected.txt').write_text(''.join(f'{c+1} {tag} {x} {bf}\n' for c,tag,x,bf in p.outputs))
(out/'fills.txt').write_text(''.join(' '.join(map(str,r))+'\n' for r in fills))
(out/'scope.json').write_text(json.dumps({'scope':'T128/T640 H16 actual SRAM ingress + actual reducer + masked scalar publisher; external scaledSC and unroundedE VM boundaries', 'native_whole_kernel_qualified':False,'scalar_count':len(p.outputs),'cycles':p.c},indent=2)+'\n')
