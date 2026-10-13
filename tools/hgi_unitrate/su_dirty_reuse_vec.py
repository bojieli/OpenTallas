#!/usr/bin/env python3
"""Extract the appended dirty adversary into a size-compatible existing binary vector set.
Reuse is legal only for binaries with NCASE=1; case counts bound every used array.
Unused compiled array slots are zero padded, never read by the live case.
"""
import argparse
import json
import re
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--generated', type=Path, required=True)
p.add_argument('--binary-sizes', type=Path, required=True)
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
z = {k: int(v) for k, v in re.findall(r'integer\s+(\w+)\s*=\s*(\d+)', a.binary_sizes.read_text())}
assert z['NCASE'] == 1, 'existing binary must run exactly one case'
meta = json.loads((a.generated / 'su_prod.json').read_text())['cases'][-1]
assert meta['tag'] == 'dirty_unstaged_sink_8x8192'
row = (a.generated / 'su_case.mem').read_text().splitlines()[-1]
r0, nr, vi0, nvi, ve0, nve, cid = [int(row[i:i+8],16) for i in range(0,56,8)]
a.out.mkdir(parents=True, exist_ok=True)
for name, start, count, capacity in [('su_rec.mem',r0,nr,z['NREC']),
        ('su_vmi.mem',vi0,nvi,z['NVMI']), ('su_vme.mem',ve0,nve,z['NVME'])]:
    lines = (a.generated/name).read_text().splitlines()[start:start+count]
    assert len(lines) == count and 0 < count <= capacity
    (a.out/name).write_text('\n'.join(lines+['0'*len(lines[0])]*(capacity-count))+'\n')
(a.out/'su_case.mem').write_text(''.join(f'{x:08X}' for x in [0,nr,0,nvi,0,nve,0])+'\n')
(a.out/'su_prod.json').write_text(json.dumps(dict(case=meta, compiled_sizes=z,
    scope='adversarial exactness only; production chain price unchanged'),indent=2)+'\n')
