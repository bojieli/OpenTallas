#!/usr/bin/env python3
"""KV-P6-PV 10-23: self-check of a PV pad table (kv_pv_pads.py output) from its members only (landed = bound + pad).

    kv_pv_pads_selfcheck.py PV_PADS.json      (exit 1 on any violation)

For every slice / join leaf: dV(k) - dC - dH(k) must be ONE constant over all vports k and all columns of a pair side,
where d = landed - asbuilt of the member (V: vport_* -> leaf, crossing or INNER; C: ctl.cmd -> leaf; H: vport -> ctl
in_*); and per column dC(join) + dR(join flags) must be one constant (col_valid all-equal check).
"""
import collections, json, re, sys
T = json.load(open(sys.argv[1]))
d = collections.defaultdict(set)
for m in T['members']:
    d[(m['sink'], m['source'].rsplit('.', 1)[0] if not m['id'].startswith('INNER:') else m['source'])].add(m['landed'] - m['asbuilt'])
bad = []
def one(k):
    v = d.get(k, set())
    if len(v) > 1: bad.append(f'{k}: member shifts {sorted(v)}')
    return next(iter(v)) if v else None
res = {}
for side, pvw in (('S', 'pvw_0'), ('N', 'pvw_1')):
    ctl = pvw + '__u_ctl'
    H = {}
    for (sink, src), v in d.items():
        if sink == ctl and src.startswith('vport_'): H[src] = one((sink, src))
    vdh, dr = collections.Counter(), collections.Counter()
    for (sink, src), v in list(d.items()):
        if src.startswith('vport_') and src in H and re.match(pvw + r'__u_s\d+_b\d+$', sink):
            c = one((sink, ctl))
            if c is None: bad.append(f'{sink}: no cmd member'); continue
            vdh[one((sink, src)) - c - H[src]] += 1
    for s in range(32):
        j = f'{pvw}__u_s{s}_j'
        c = one((j, ctl))
        r = one((ctl, j))
        if c is None or r is None: bad.append(f'{j}: cmd/flag member missing'); continue
        dr[c + r] += 1
    res[side] = dict(vports=len(H), V_D_H_shift=dict(vdh), D_plus_R_shift=dict(dr))
    if len(vdh) != 1: bad.append(f'{side}: V-D-H shifts {dict(vdh)}')
    if len(dr) != 1: bad.append(f'{side}: D+R shifts {dict(dr)}')
print(json.dumps(res, indent=1)); print('violations:', len(bad)); [print(' ', b) for b in bad[:20]]
sys.exit(1 if bad else 0)
