#!/usr/bin/env python3
"""Per-(die, stack) held-row counts of the ONLY DeepSeek-V4.1 top-512 selections in the repository: the CPU golden
1M-context reference token (seed 20260930; results/inputs/ds_v41_1m_golden_s20260930, ref/ctx1048576_seed20260930
ctx1048576_LNN.json ctx_out.sel = the layer's own indexer top-512, released weights, SYNTHETIC i.i.d. KV / index-key
state).  ONE token -- a fixture, not a real-prompt distribution.  Owner = tools/v41_selection_global_ids.owner():
die g[5:4], stack g[7:6].  usage: fixture_counts.py GOLDEN_REF_DIR"""
import collections, hashlib, json, sys
from pathlib import Path
d = Path(sys.argv[1]); out = dict(source=str(d), layers={})
for L in (2, 8, 14, 20, 24, 28, 32, 36):
    f = d / f'ctx1048576_L{L:02d}.json'; raw = f.read_bytes(); j = json.loads(raw)
    sel = j['ctx_out']['sel']; assert len(sel) == 512 and j['index_select_n'] == 512
    c = collections.Counter(((g >> 4) & 3, (g >> 6) & 3) for g in sel)
    cnt = {f'd{a}s{b}': c.get((a, b), 0) for a in range(4) for b in range(4)}
    grp = collections.Counter(g >> 4 for g in sel)              # selected rows per 16-row group (one owner each)
    blk8 = collections.Counter(g >> 3 for g in sel)
    out['layers'][f'L{L}'] = dict(file_sha256=hashlib.sha256(raw).hexdigest(), kind=j['kind'], counts=cnt,
        max=max(cnt.values()), min=min(cnt.values()), owners_gt_40=sum(v > 40 for v in cnt.values()),
        owners_gt_80=sum(v > 80 for v in cnt.values()), owners_gt_128=sum(v > 128 for v in cnt.values()),
        non_held_for_worst_receiver=512 - min(cnt.values()), rows_per_16group_max=max(grp.values()),
        rows_per_8block_mean=round(512 / len(blk8), 3), span=[min(sel), max(sel)])
m = [v['max'] for v in out['layers'].values()]
out['summary'] = dict(layers=8, layer_max=m, max=max(m), layers_gt_40=sum(x > 40 for x in m), layers_gt_80=sum(x > 80 for x in m))
print(json.dumps(out, indent=1))
