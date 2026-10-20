#!/usr/bin/env python3
"""HBM-VMEARLY-IDX (10-19): query vectors for R back-to-back IDX.INDEX operand records (32 heads x 128 FP32 each).

Same released golden quantisation as tools/hbm_idx_static_query_vectors.py (record 0 = that tool's set, seed 1014);
record r uses seed 1014 + r and head weight 0x3f00 + 32 r + h.  Writes OUT/query.hex (R x 128 blocks of 1,024 b) and
OUT/gold.hex (R x 32 lines {w16, scales32, codes512}).   usage: hbm_vmearly_idx_vectors.py OUT [R=4]
"""
import sys
from pathlib import Path
import numpy as np
import hdc_golden_v41 as g

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
R = int(sys.argv[2]) if len(sys.argv) > 2 else 4
levels = np.array([0, .5, 1, 1.5, 2, 3, 4, 6.])
blocks, expected = [], []
for r in range(R):
    rng = np.random.default_rng(1014 + r)
    x = (rng.normal(size=(32, 128)) * np.exp2(rng.integers(-12, 8, size=(32, 1)))).astype(np.float32)
    if r == 0:
        x[0, :16] = np.array([0, -0., .25, -.25, .75, -.75, 1.25, -1.25, 1.75, -1.75, 2.5, -2.5, 3.5, -3.5, 5, -5],
                             dtype=np.float32)
    for h in range(32):
        codes = 0; scales = 0
        for b in range(4):
            v = x[h, b * 32:b * 32 + 32]
            a = np.maximum(np.max(np.abs(v)), g.FP4_AMAX_FLOOR_E8M0).astype(np.float32)
            e = int(g._ceil_log2(g.mul(a, g.FP4_MAX_INV)))
            q = g._round_grid(np.clip(v.astype(np.float64) * np.exp2(-e), -6, 6), 0, 1)
            nib = [int(np.argmin(abs(levels - abs(t)))) + (8 if orig < 0 else 0) for t, orig in zip(q, v)]
            codes |= sum(n << (4 * (b * 32 + i)) for i, n in enumerate(nib))
            scales |= (e + 127) << (b * 8)
            blocks.append(sum(int(t) << (i * 32) for i, t in enumerate(v.view(np.uint32))))
        expected.append((codes, scales, 0x3f00 + 32 * r + h))
(out / 'query.hex').write_text(''.join(f'{v:0256x}\n' for v in blocks))
(out / 'gold.hex').write_text(''.join(f'{w:04x}{s:08x}{c:0128x}\n' for c, s, w in expected))
