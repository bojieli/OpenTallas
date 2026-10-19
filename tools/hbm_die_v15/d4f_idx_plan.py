#!/usr/bin/env python3
"""d4f IDX soft hierarchy (contract claude/hnl-idxd4f-2050 50de1fe73: hb_idx -> 7 die instances) into the E column:
  S of hc_eng (below the ep_S / lk_S rows): row [idx_sel 600x450 | idx_link 650x500], then idx_s0 scorer cluster
  N of hc_eng (above the ep_N / lk_N rows): row [idx_ctl 300x260 | idx_q 260x260 | idx_op 216x108], then idx_s1
Scorer = hardened cluster of 16 replicated square leaves (4x4 x ~700 um, regional roots), slot 3050 x 3050
(ot_hbm_idx_score_static 4.70 mm2 std / 0.6 = 7.84 mm2).     d4f_idx_plan.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); P = json.loads((d / 'compact.P.json').read_text()); W, H = json.loads((d / 'compact.metrics.json').read_text())['die_um']
GAP = 100.0; e = P['hc_eng']; c0 = e['x']; cw = W - 42.4 - c0
S = dict(idx_s0=(3050.0, 3050.0), idx_s1=(3050.0, 3050.0), idx_sel=(600.0, 450.0), idx_link=(650.0, 500.0),
         idx_ctl=(300.0, 260.0), idx_q=(260.0, 260.0), idx_op=(216.0, 108.0))
assert cw >= 3050 - 1e-6, ('E column too narrow for the IDX scorer cluster', cw)
lo = min(P[k]['y'] for k in P if k.startswith(('ep_S', 'lk_S')))
hi = max(P[k]['y'] + P[k]['h'] for k in P if k.startswith(('ep_N', 'lk_N')))
y = lo - GAP - 500.0; x = c0
for k in ('idx_sel', 'idx_link'):
    w, h = S[k]; P[k] = dict(x=round(x, 3), y=round(lo - GAP - h, 3), w=w, h=h, orient='R0'); x += w + GAP
P['idx_s0'] = dict(x=round(c0 + (cw - 3050) / 2, 3), y=round(y - GAP - 3050, 3), w=3050.0, h=3050.0, orient='R0')
x = c0
for k in ('idx_ctl', 'idx_q', 'idx_op'):
    w, h = S[k]; P[k] = dict(x=round(x, 3), y=round(hi + GAP, 3), w=w, h=h, orient='R0'); x += w + GAP
P['idx_s1'] = dict(x=round(c0 + (cw - 3050) / 2, 3), y=round(hi + GAP + 260.0 + GAP, 3), w=3050.0, h=3050.0, orient='R0')
for k in S:
    assert P[k]['y'] >= 20 and P[k]['y'] + P[k]['h'] <= H - 20, (k, P[k])
(d / 'compact.P.json').write_text(json.dumps(P, indent=1))
print(json.dumps({k: P[k] for k in S}))
