#!/usr/bin/env python3
"""d4f r4 XQL pair stores in the widened SM pair gaps (H-DIE 10-17; compact_plan --sm-pair-gap): pair p of quadrant Q
(SMs 2p, 2p+1) = stack at the band end of the gap between its two SM columns:
  xq_<Q>_p<p>_eg   (pegress x6 369.36 sq: N face xw -> both SM xw windows at the column band ends, W bq_d, S rwq, E ctl)
  xq_<Q>_p<p>_bd   (bdring 86.4 x 302.4) W of eg (feeds eg W face)
  xq_<Q>_p<p>_bfq0..3 (bfqg 302.4 x 298.08) stacked away from the band under eg (feed eg S face)
N quadrants mirror (MX: band below the columns).  Writes plan blocks named as the contract instances.   d4f_xq_plan.py PLAN_DIR"""
import json, sys
from pathlib import Path
d = Path(sys.argv[1]); P = json.loads((d / 'compact.P.json').read_text())
C = 21.6; EG, BD, BQ = (369.36, 369.36), (86.4, 302.4), (302.4, 298.08)
for q in ('SW', 'NW'):
    sms = [P[f'sm_{q}{k}'] for k in range(8)]
    north = q.startswith('N')
    for p in range(4):
        a, b = sms[2 * p], sms[2 * p + 1]
        gx0, gx1 = a['x'] + a['w'], b['x']; gw = gx1 - gx0
        need = BD[0] + C + EG[0]
        assert gw >= need + 2 * 10.8 - 1e-6, (q, p, gw, need)
        x0 = gx0 + (gw - need) / 2
        band_end = a['y'] if north else a['y'] + a['h']        # the column face that carries the xw window
        sgn = 1 if north else -1                               # stack direction away from the band
        def y_of(h, off):                                      # block whose band-side edge is 'off' um from the band end
            return band_end + off if north else band_end - off - h
        P[f'xq_{q}_p{p}_eg'] = dict(x=round(x0 + BD[0] + C, 3), y=round(y_of(EG[1], 0.0), 3), w=EG[0], h=EG[1], orient='MX' if north else 'R0')
        P[f'xq_{q}_p{p}_bd'] = dict(x=round(x0, 3), y=round(y_of(BD[1], (EG[1] - BD[1]) / 2), 3), w=BD[0], h=BD[1], orient='MX' if north else 'R0')
        bx = x0 + BD[0] + C + (EG[0] - BQ[0]) / 2
        for g in range(4):
            P[f'xq_{q}_p{p}_bfq{g}'] = dict(x=round(bx, 3), y=round(y_of(BQ[1], EG[1] + C + g * (BQ[1] + C)), 3), w=BQ[0], h=BQ[1], orient='MX' if north else 'R0')
(d / 'compact.P.json').write_text(json.dumps(P, indent=1))
print('xq pair stores placed: 8 pairs x 6 blocks')
