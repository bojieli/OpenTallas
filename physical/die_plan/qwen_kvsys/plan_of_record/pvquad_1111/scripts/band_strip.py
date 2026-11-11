#!/usr/bin/env python3
"""band_strip.py PLAN_IN PLAN_OUT DELTA : landing storage bands of the delta's types that overlap a hard core (+4.32)
are marked placement FAIL (rects dropped) so clock_landing_plan.py fill-bands re-places them in free area."""
import json, sys
pin, pout, dp = sys.argv[1:4]; P = json.load(open(pin)); D = json.load(open(dp)); H = 4.32
for tn in D:
    T = P['partition_types'][tn]
    B = [(h['origin_um'][0] - H, h['origin_um'][1] - H, h['origin_um'][0] + h['outline_um'][0] + H, h['origin_um'][1] + h['outline_um'][1] + H) for h in T['hard_cores']]
    bands = T['clock']['landing_contract']['bands']; n = []
    for k, b in bands.items():
        rs = b.get('rects_um') or ([b['rect_um']] if b.get('rect_um') else [])
        if any(r[0] < c[2] and r[2] > c[0] and r[1] < c[3] and r[3] > c[1] for r in rs for c in B):
            if k.startswith('monitor_'):
                # monitor bands are not face buses (fill-bands cannot place them): slide straight down/up to the
                # nearest free spot of the same size, x kept (the 2-bit monitor hop changes by the slide only)
                r = b['rect_um']; h = r[3] - r[1]; best = None
                for y0 in [8.64 + 0.54 * i for i in range(int((T['outline_um'][1] - 17.28 - h) / 0.54))]:
                    q = [r[0], y0, r[2], y0 + h]
                    if not any(q[0] < c[2] and q[2] > c[0] and q[1] < c[3] and q[3] > c[1] for c in B):
                        if best is None or abs(y0 - r[1]) < abs(best[1] - r[1]): best = q
                b['rect_um'] = [round(v, 4) for v in best]; b['note_cplkvpv3'] = 'slid from %s' % r; n.append(k + '(slid)')
                continue
            for kk in ('rect_um', 'rects_um'): b.pop(kk, None)
            b['placement'] = 'FAIL'; n.append(k)
    print(tn, 'bands re-placed', len(n), ','.join(n))
json.dump(P, open(pout, 'w'), indent=1); open(pout, 'a').write('\n')
