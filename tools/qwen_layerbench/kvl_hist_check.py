#!/usr/bin/env python3
"""TOK-QK-KVL 10-27: the real-prefill history (kvl_prefill_hist.py, HF arithmetic) vs the ISA golden's own prefill
(qwen_hbmacc_position_oracle_gpu --run, positions 0..P-1 by sequential decode; kv_pre/ at P) on rows 0..P-1:
layout / head / die mapping identity and the per-element agreement of the two arithmetics (FP8 codes).
    kvl_hist_check.py --hist hist_real --kvpre pf16/P16/kv_pre --rows 16 [--layers 36 --tp 4] --out check.json"""
import argparse, json
from pathlib import Path
import numpy as np

TMAX, HD, KVD, W = 8192, 128, 2, 16
ap = argparse.ArgumentParser()
ap.add_argument('--hist', type=Path, required=True); ap.add_argument('--kvpre', type=Path, required=True)
ap.add_argument('--rows', type=int, default=16); ap.add_argument('--layers', type=int, default=36)
ap.add_argument('--tp', type=int, default=4); ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
t = np.arange(a.rows)[:, None]; d = np.arange(HD)[None, :]
res = {}; tot = {'K': [0, 0], 'V': [0, 0]}; worst = {'K': 0.0, 'V': 0.0}
for n in range(a.layers):
    for die in range(a.tp):
        h = np.fromfile(a.hist / f'L{n}_die{die}.bin', dtype='<u4').view(np.float32)
        g_ = np.load(a.kvpre / f'L{n}_die{die}.npy').view(np.float32)
        r = {}
        for g in range(KVD):
            for nm, idx in (('K', ((g * (TMAX // W) + t // W) * HD + d) * W + t % W),
                            ('V', KVD * TMAX * HD + (g * TMAX + t) * HD + d)):
                x, y = h[idx], g_[idx]
                eq = int(np.sum(x.view(np.uint32) == y.view(np.uint32)))
                rel = float(np.max(np.abs(x - y)) / max(float(np.max(np.abs(y))), 1e-30))
                corr = float(np.corrcoef(x.ravel(), y.ravel())[0, 1])
                r[f'{nm}{g}'] = {'equal': eq, 'of': x.size, 'max_abs_over_absmax': rel, 'corr': corr}
                tot[nm][0] += eq; tot[nm][1] += x.size; worst[nm] = max(worst[nm], rel)
        res[f'L{n}_die{die}'] = r
summ = {k: {'equal_frac': v[0] / v[1], 'worst_max_abs_over_absmax': worst[k]} for k, v in tot.items()}
min_corr = min(v['corr'] for r in res.values() for v in r.values())
json.dump({'rows': a.rows, 'summary': summ, 'min_corr': min_corr, 'per_layer_die': res}, open(a.out, 'w'), indent=1)
print('KVL_HIST_CHECK', json.dumps(summ), 'min_corr', round(min_corr, 5))
