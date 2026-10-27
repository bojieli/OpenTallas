#!/usr/bin/env python3
"""S81-ROWX2: dump the CPU golden 1M reference token's indexer top-512 gids (ctx_out.sel, rank order as stored) of the
8 indexer layers as $readmemh files for tb_dsdv_svc_rowx (+fix=<file>), plus the per-(die, stack) counts.  ONE fixture
token, released weights, SYNTHETIC KV / index-key state (results/rowx_budget_1026/README.md).
usage: fixture_gids.py GOLDEN_REF_DIR OUTDIR"""
import collections, hashlib, json, sys
from pathlib import Path
d, o = Path(sys.argv[1]), Path(sys.argv[2]); o.mkdir(parents=True, exist_ok=True); man = {}
for L in (2, 8, 14, 20, 24, 28, 32, 36):
    f = d / f'ctx1048576_L{L:02d}.json'; raw = f.read_bytes(); sel = json.loads(raw)['ctx_out']['sel']
    assert len(sel) == 512 and len(set(sel)) == 512 and max(sel) < 1 << 21
    (o / f'gid_L{L:02d}.hex').write_text(''.join(f'{g:08x}\n' for g in sel))
    c = collections.Counter(((g >> 4) & 3, (g >> 6) & 3) for g in sel)
    (dm, sm), n = max(c.items(), key=lambda kv: (kv[1], -kv[0][0], -kv[0][1]))
    man[f'L{L}'] = dict(sha256=hashlib.sha256(raw).hexdigest(), max_owner=f'd{dm}s{sm}', max=n, die=dm, stack=sm,
                        counts={f'd{a}s{b}': c.get((a, b), 0) for a in range(4) for b in range(4)})
(o / 'manifest.json').write_text(json.dumps(man, indent=1))
for k, v in man.items(): print(k, v['max_owner'], v['max'])
