#!/usr/bin/env python3
"""HBM-NEXT-UNITS-IDX 2026-10-19: full-shape N-row IDX.INDEX operands + independent exact oracle per row.

    hnx_idx_rows_vectors.py OUT [ROWS=4]

Row 0 and the key lines are generated EXACTLY as tools/hbm_idx_static_parent_vectors.py (legacy invocation: seed
2026101501, query then keys, n 10,928, rank 3), so row 0 is the d4g bench frame bit for bit. Rows 1..ROWS-1 are new
queries + head weights drawn after the keys (one shared key stream). Per row: the golden 16-b scores of every key and
the top-512 set (hdc_golden_v41 via rtl_hdc_v41x_idx_campaign.golden, the d4g oracle).
Files: query.hex (ROWS x 128 VM blocks), weights.hex (ROWS lines), keylines.hex (171), scores.hex / gold.hex (ROWS x n).
"""
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_idx_die_bench as B  # noqa: E402
import rtl_hdc_v41x_idx_campaign as C  # noqa: E402
import hdc_golden_v41 as G  # noqa: E402

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rows = int(sys.argv[2]) if len(sys.argv) > 2 else 4
rng = np.random.default_rng(2026101501)
nq, n = 4, 10928
qs = [B.query(rng)]
kc, ku = B.qdq_codes(rng.standard_normal((n, 128)).astype(np.float32))
for _ in range(rows - 1):
    qs.append(B.query(rng))
keys = [B.key_word(kc[i], ku[i]) for i in range(n)]
lines = []
for a in range(171):
    packed = 0
    for s in range(nq):
        for p in range(8):
            index = s * 2736 + a * 16 + p * 2
            two = sum((keys[index + j] if index + j < n else 0) << (j * 544) for j in range(2))
            payload = (two << 11) | (((p * 128 + a) & 1023) << 1) | 1
            packed |= payload << (s * 8792 + p * 1099)
    lines.append(packed)
(out / 'keylines.hex').write_text(''.join(f'{x:0{nq*2198}x}\n' for x in lines))
qtxt, wtxt, stxt, gtxt = [], [], [], []
for r, (q, w) in enumerate(qs):
    qc, qu = B.qdq_codes(q)
    exp, bad = C.golden(C.values(qc, qu), w, C.values(kc, ku), np.ones(n, dtype=bool), qu, ku)
    assert not bad.any()
    qtxt += [f'{(x >> 7) & ((1 << 1024) - 1):0256x}\n' for x in B.qblocks(q, w)]
    weights = sum((int(G.bits(np.float32(w[h]))) >> 16) << (h * 16) for h in range(32))
    wtxt.append(f'{weights:0128x}\n')
    stxt += [f'{int(x):04x}\n' for x in exp]
    values = (exp.astype(np.uint32) << 16).view(np.float32)
    chosen = set(sorted(range(n), key=lambda i: (-float(values[i]), i))[:512])
    gtxt += [f'{int(i in chosen):x}\n' for i in range(n)]
    print(f'row {r}: top512 threshold score {min(int(exp[i]) for i in chosen):04x}, distinct from row 0: '
          f'{len(chosen) if r == 0 else len(chosen - row0)}')
    if r == 0:
        row0 = chosen
for name, t in (('query.hex', qtxt), ('weights.hex', wtxt), ('scores.hex', stxt), ('gold.hex', gtxt)):
    (out / name).write_text(''.join(t))
