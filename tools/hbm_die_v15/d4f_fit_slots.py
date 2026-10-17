#!/usr/bin/env python3
"""d4f r2 shared-region fits (coordinator 10-17 run1 review: no squeezing): regions that hold more than one instance (or an
instance bigger than the region) are resized from the measured abstracts, then re-homed at the nearest free origin
(clear of plan blocks and every other die-level slot, 21.6-um halo):
  hb_dbk_SW / hb_dbk_NW : DMA back (240.8 sq SYNTH) + wb_kport (495.7 sq SYNTH) side by side -> 800 x 560
  host_cp               : host_cp_ep (584 sq) + landing (196 sq) + packet + ep_face -> 1300 x 700
  sfus_<Q>              : only user = sfup_<Q> = SFU programme store r6 routed outline 447.12 x 1023.84 (H-SU)
    d4f_fit_slots.py GRANTS PLAN_DIR"""
import json, sys
g, pd = sys.argv[1], sys.argv[2]
G = json.load(open(g)); P = json.load(open(pd + '/compact.P.json'))
W, H = G['slots'][0]['outline']['w'], G['slots'][0]['outline']['h']
FIT = {'hb_dbk_SW': (800.0, 560.0), 'hb_dbk_NW': (800.0, 560.0), 'host_cp': (1300.0, 700.0)}
for q in ('SW', 'SE', 'NE', 'NW'):
    FIT[f'sfus_{q}'] = (447.12, 1023.84)
S = {s['name']: s for s in G['slots']}
def rects(skip):
    r = [(k, b['x'], b['y'], b['w'], b['h']) for k, b in P.items() if k not in skip]
    for s in G['slots'][1:]:
        if s['name'] in skip or s.get('parent') != 'die' or s.get('origin', {}).get('x') is None or s.get('plan_block') in P:
            continue
        fp = s.get('placed_footprint') or s['outline']; r.append((s['name'], s['origin']['x'], s['origin']['y'], fp['w'], fp['h']))
    return r
log = {}
for n, (w, h) in FIT.items():
    s = S[n]; pb = s.get('plan_block'); x0, y0 = s['origin']['x'], s['origin']['y']
    R = rects({n, pb})
    free = lambda x, y: 20 <= x and 20 <= y and x + w <= W - 20 and y + h <= H - 20 and \
        not any(x - 21.6 < a + c and a < x + w + 21.6 and y - 21.6 < b + d and b < y + h + 21.6 for _, a, b, c, d in R)
    best = None
    for r in range(0, 3000, 10):
        for dx in range(-r, r + 1, 10):
            for dy in {r - abs(dx), -(r - abs(dx))}:
                if free(x0 + dx, y0 + dy):
                    best = (x0 + dx, y0 + dy); break
            if best: break
        if best: break
    assert best, n
    s['outline'] = dict(w=w, h=h); s['origin'] = dict(s['origin'], x=round(best[0], 3), y=round(best[1], 3))
    s.pop('placed_footprint', None); s['fit_r2'] = dict(reason=__doc__.split('\n')[0], moved_um=round(abs(best[0] - x0) + abs(best[1] - y0), 1))
    if pb in P:
        P[pb] = dict(P[pb], x=s['origin']['x'], y=s['origin']['y'], w=w, h=h)
    log[n] = (best, (w, h))
json.dump(G, open(g, 'w'), indent=1); open(g, 'a').write('\n'); json.dump(P, open(pd + '/compact.P.json', 'w'), indent=1)
print(json.dumps(log))
