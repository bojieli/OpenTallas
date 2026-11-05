#!/usr/bin/env python3
"""MEM v2 packet: the 15 v1 closed svc bounds (s81_svc_memory_closure_1103) rebound to the right-sized children.
closure.json keeps each type's kit-bound before_sha256 so `s81_svc_memory_closure.py --kit-rtl ... --closed-dir
<this dir>` reuses these texts (the v2 rename is idempotent)."""
import gzip, json, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'tools/die_plan'))
import s81_svc_memory_closure as m

V1 = ROOT / 'results/rtl/s81_svc_memory_closure_1103'
v1 = json.loads((V1 / 'closure.json').read_text())
out = dict(form='v2', base_packet=str(V1.relative_to(ROOT)), self_check=v1.get('self_check'), macros=m.MACROS['v2'],
           types={})
(HERE / 'closed').mkdir(exist_ok=True)
for t, r in sorted(v1['types'].items()):
    if r.get('status') != 'CLOSED':
        out['types'][t] = r; continue
    name = 's81p_%s_bound.sv' % t
    s1 = gzip.decompress((V1 / 'closed' / (name + '.gz')).read_bytes()).decode()
    assert m.sha(s1) == r['after_sha256'], t
    s2 = m.fit_v2(s1)
    (HERE / 'closed' / (name + '.gz')).write_bytes(gzip.compress(s2.encode(), mtime=0))
    out['types'][t] = dict(r, v1_after_sha256=r['after_sha256'], after_sha256=m.sha(s2))
    print(t, m.sha(s2)[:8])
(HERE / 'closure.json').write_text(json.dumps(out, indent=1) + '\n')
