#!/usr/bin/env python3
"""STW-S81c-DIE3-C28: die clock at placement -> one summary block.
  c28_clk_summ.py CASE_OUT_DIR   (reads ckr_spread.json + dieclk/manifest.json)
CKR: entry-buffer spread displacement (target = reserved site).  Groups: per balance group (trees without one are their own
group) TT spread = max(flop_max) - min(pin_min), FF spread = max(ff_max) - min(ff_max - ff_spread), last iteration; long
trees = model insertion > 2 ns or sink bbox side > 2 mm."""
import json, sys, collections
d = sys.argv[1]
try:
    c = json.load(open(f'{d}/ckr_spread.json'))
    print(f"CKR placed {c['placed']} unplaced {c['unplaced']} on_obstacle {c['ideal_on_obstacle']} mean_disp {c['mean_disp_um']} um "
          f"max_disp {c['max_disp_um']} um max_ring {c['max_ring']} hard_cap {c['placed_at_hard_cap']}")
except Exception as e:
    print('CKR no ckr_spread.json', e)
m = json.load(open(f'{d}/dieclk/manifest.json'))
grp = {t['name']: t.get('balance_group', t['name']) for t in m['spec']['trees']}
its = m['iterations']
def spreads(it):
    g = collections.defaultdict(list)
    for t, v in it['trees'].items():
        g[grp.get(t, t)].append(v)
    out = {}
    for k, vs in g.items():
        tt = max(v['flop_max'] for v in vs) - min(v['pin_min'] for v in vs)
        ff = max(v['ff_max'] for v in vs) - min(v['ff_max'] - v['ff_spread'] for v in vs)
        out[k] = (round(tt, 1), round(ff, 1))
    return out
hist = []
for it in its:
    s = spreads(it); w = max(max(v) for v in s.values())
    hist.append(f"{w:.0f}/{sum(max(v) > 80 for v in s.values())}")
s = spreads(its[-1])
print(f"GROUPS {len(s)} trees {len(m['trees'])} iterations {len(its)}; worst/over80 per iteration: {' '.join(hist)}")
print(f"GROUPS over 80 (max TT,FF): {sum(max(v) > 80 for v in s.values())}; over 40: {sum(max(v) > 40 for v in s.values())}")
print('WORST ' + '; '.join(f'{k} {v[0]}/{v[1]}' for k, v in sorted(s.items(), key=lambda kv: -max(kv[1]))[:8]))
sk = collections.defaultdict(list)
for p, v in m['sinks'].items():
    sk[v['tree']].append((v['x'], v['y']))
lt = []
for t, v in m['trees'].items():
    pts = sk.get(t, [])
    side = max(max(q[0] for q in pts) - min(q[0] for q in pts), max(q[1] for q in pts) - min(q[1] for q in pts)) if pts else 0
    ins = v.get('model', {}).get('model_insertion_ps', 0)
    if side > 2000 or ins > 2000:
        lt.append((t, round(side), round(ins)))
print(f"LONG trees (bbox side > 2 mm or model > 2 ns): {len(lt)}; groups holding one: {len({grp.get(t, t) for t, _, _ in lt})}; "
      + ', '.join(f'{t} {s_}um/{i}ps' for t, s_, i in sorted(lt, key=lambda x: -x[2])[:6]))
