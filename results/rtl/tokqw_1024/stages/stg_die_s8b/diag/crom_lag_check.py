#!/usr/bin/env python3
"""TOK-QK/S8B 10-25: locate the s8 SU CROM-operand misalignment from a resid stg run (readback of x').
usage (in the wf3 tree): crom_lag_check.py <run dir with run_resid_m0.log + lowering_resid.json> <fixture .npz>
For each slice, r = (x'_readback - x) / t is compared against the post-scale ps1 in the slice's own-row order at
shifts k: on the s8 row every slice matches ps1[e + k] at k = -24 for 100% of elements (first 24 elements: r = 0),
i.e. the CROM operand reaches the lane 3 edges (8 lanes x 3) after the VM operands of the same element."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, 'rtl/test/qwen_dv'); sys.path.insert(0, 'tools/qwen_layerbench')
import dv_lower_vec_bench as VB
R, FX = Path(sys.argv[1]), sys.argv[2]
lw = json.load(open(R / 'lowering_resid.json')); own = lw['ownership']['residual']['blocks_per_slice']
log = {}
for line in open(R / 'run_resid_m0.log'):
    p = line.split()
    if len(p) == 3:
        log.setdefault(p[1], []).append((int(p[0]), int(p[2].replace('x', '0').replace('X', '0').replace('z', '0'), 16)))
dd = VB.dd_words(log); c0 = dd[0][0]
fx = dict(np.load(FX)); p = fx['ps1'].astype(np.float64)
for s in range(12):
    got = {}
    for c, k, lst in dd:
        if c0 + 260 * s <= c < c0 + 260 * (s + 1):
            got.update(lst)
    n = len(own[s]) * 128
    g = np.array([got.get(i, 0) for i in range(n)], dtype=np.uint32).view(np.float32).astype(np.float64)
    idx = np.concatenate([np.arange(128 * b, 128 * (b + 1)) for b in own[s]])
    pl, x, t = p[idx], fx['x'].astype(np.float64)[idx], fx['t'].astype(np.float64)[idx]
    r = (g - x) / t
    res = []
    for k in range(-48, 49):
        lo, hi = max(0, -k), min(n, n - k)
        m = np.sum(np.abs(r[lo:hi] - pl[lo + k:hi + k]) < 1e-7) / (hi - lo)
        if m > 0.5:
            res.append((k, round(float(m), 3)))
    print(f'slice {s} n {n} matching shifts {res} zero-scale elements {int(np.sum(np.abs(r) < 1e-12))}')
