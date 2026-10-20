#!/usr/bin/env python3
"""TOKSIM-HBM-idxdma 2026-10-19: production-shape vectors for IDX.TOPK and ARGMAX.LOCAL on the d4g IDX root.

  toksim_idx_vectors.py OUT topk|argmax N [nrec] [seed]

topk  : DS route.top6 = census shape {"A": ["VM", 384, 1, "FP32"], "O": ["VM", 6, 1, "U32"]}: k 6, n 384, m 1,
        ascending ids (order 1), REPL (mirror) scores, no R. Golden hgi_sim.machine.topk_ids.
argmax: ARGMAX.LOCAL over N FP32 logits in VM (the die-bound ot_hbm_argmax_static_sw_vm_r2 has no STREAM input:
        mode 1 faults), O = {value, id} at o_base / o_base+1. Golden numpy argmax (lowest index on ties),
        id = local + RANK * imm (RANK = die_id strap 3, imm = N).
Files: mem.hex (@{mirror,sector15} 256-b sectors), rec.txt (one record a line), exp.txt (per record: count, then
word-address/value pairs that must be in VM after done).
"""
import sys
from pathlib import Path
import numpy as np


def topk_ids(v, k, asc=False):
    """Verbatim tools/hgi_sim/machine.py topk_ids (the golden; inlined: machine.py imports the whole simulator)."""
    v = np.asarray(v, dtype=np.float64)
    assert not np.isnan(v).any()
    ids = np.lexsort((np.arange(len(v)), -v))[:k]
    return np.sort(ids) if asc else ids

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
kind, N = sys.argv[2], int(sys.argv[3])
nrec = int(sys.argv[4]) if len(sys.argv) > 4 else 4
rng = np.random.default_rng(20261019 + (int(sys.argv[5]) if len(sys.argv) > 5 else 0))
mem = {}          # (mirror, word) -> u32
recs, exps = [], []
RANK = 3
for i in range(nrec):
    v = rng.standard_normal(N).astype(np.float32)
    if i == 1:                                   # ties: a repeated maximum (lowest index must win)
        j0, j1 = sorted(rng.choice(N, 2, replace=False)); v[j0] = v[j1] = np.float32(9.5)
    u = v.view(np.uint32)
    if kind == 'topk':
        a = 4096 + i * 512; o = 60000 + 16 * i
        for j, x in enumerate(u): mem[(1, a + j)] = int(x)
        ids = topk_ids(v, 6, True)
        recs.append(f"6 1 {N} 1 1 {a} {N} {o} 8")
        exps.append([(o + j, int(x)) for j, x in enumerate(ids)])
    else:
        a = 8192 if N > 20000 else 8192 + i * 2048
        if N > 20000 and i > 0:
            mem_rows = None
        o = 60000 + 16 * i
        for j, x in enumerate(u): mem[(1, a + j)] = int(x)
        idx = int(np.argmax(v))
        recs.append(f"{N} 1 {a} {N} {o} 1")
        exps.append([(o, int(u[idx])), (o + 1, idx + RANK * N)])
        if N > 20000:                            # big rows share one region: record i overwrites it before it runs
            break
secs = {}
for (mr, w), x in mem.items():
    secs.setdefault((mr << 15) | (w >> 3), [0] * 8)[w & 7] = x
with open(out / 'mem.hex', 'w') as f:
    for s in sorted(secs):
        f.write(f"@{s:x} " + ''.join(f'{x:08x}' for x in reversed(secs[s])) + '\n')
(out / 'rec.txt').write_text(f"{len(recs)}\n" + '\n'.join(recs) + '\n')
(out / 'exp.txt').write_text(''.join(f"{len(e)}\n" + ''.join(f"{w} {x}\n" for w, x in e) for e in exps))
print(f"toksim_idx_vectors {kind} N {N} records {len(recs)} sectors {len(secs)}")
