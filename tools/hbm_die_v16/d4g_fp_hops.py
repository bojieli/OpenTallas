#!/usr/bin/env python3
"""L2H-GEN2D-FP 10-19: lane-relay hop check for the widened-channel floorplan.  Compares two placed die cases (same
contract): for every placed net driven by one output pin, span = driver pin -> farthest load pin (Manhattan, real LEF
pins, die_relay_pass.load_case).  Reported per case, for 624-bit lane nets (driver or load master hbfd_(rly|lh|land)_624*
or a 624-wide bus between blocks) and for nets touching any instance whose placement differs between the cases:
max span, count > hop.  The relay COUNT per lane is a property of the contract (unchanged here), so hop-count changes
are reported from the contract instance census of both manifests.
    d4g_fp_hops.py CASE_OLD CASE_NEW CONTRACT [--hop 405] --out FILE"""
import argparse, collections, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v15'))
import die_relay_pass as RP  # noqa: E402

ap = argparse.ArgumentParser(); ap.add_argument('old'); ap.add_argument('new'); ap.add_argument('contract')
ap.add_argument('--hop', type=float, default=405.0); ap.add_argument('--out', required=True)
a = ap.parse_args()
C = json.loads(Path(a.contract).read_text())
LANE = re.compile(r'hbfd_(rly|lh|land)\d*_624')
m_old = json.loads((Path(a.old) / 'manifest.json').read_text())['placement']
m_new = json.loads((Path(a.new) / 'manifest.json').read_text())['placement']
moved = {n for n in m_new if n in m_old and (abs(m_new[n]['x'] - m_old[n]['x']) > 1e-3 or abs(m_new[n]['y'] - m_old[n]['y']) > 1e-3)}
census = lambda m: collections.Counter(v['m'] for v in m.values() if LANE.match(v['m']))
c_old, c_new = census(m_old), census(m_new)


def scan(case):
    pl, nets, directions, top = RP.load_case(Path(case), C)
    out = dict(lane=dict(n=0, over=0, max=0.0, worst=None), moved=dict(n=0, over=0, max=0.0, worst=None))
    per = {}
    for n, ends in nets.items():
        drv = [e for e in ends if directions.get(e[:2]) == 'OUTPUT']; lds = [e for e in ends if directions.get(e[:2]) == 'INPUT']
        if n in top or len(drv) != 1 or not lds:
            continue
        d = drv[0]; span = max(RP.md(d[2], l[2]) for l in lds)
        insts = {d[0]} | {l[0] for l in lds}
        is_lane = LANE.match(pl[d[0]]['master']) or any(LANE.match(pl[l[0]]['master']) for l in lds)
        for key, hit in (('lane', is_lane), ('moved', insts & moved)):
            if not hit:
                continue
            o = out[key]; o['n'] += 1
            if span > a.hop:
                o['over'] += 1
            if span > o['max']:
                o['max'], o['worst'] = round(span, 1), [n, d[0], sorted(l[0] for l in lds)[:3]]
        if insts & moved:
            k = (d[0], tuple(sorted({l[0] for l in lds})))
            per[k] = max(per.get(k, 0.0), span)
    return out, per


r_old, p_old = scan(a.old)
r_new, p_new = scan(a.new)
grew = sorted(((round(v - p_old.get(k, 0.0), 1), round(p_old.get(k, 0.0), 1), round(v, 1), k[0], list(k[1])[:3])
               for k, v in p_new.items() if k in p_old), reverse=True)
newly_over = [g for g in grew if g[2] > a.hop >= g[1]]
res = dict(schema='opentallas.hbm.d4g_fp_hops.v1', hop_um=a.hop, moved_instances=len(moved),
           moved_sample=sorted(moved)[:40], old=r_old, new=r_new,
           moved_edges=len(p_new), moved_edges_newly_over_hop=len(newly_over), newly_over=newly_over[:40],
           largest_growth=grew[:20], lane_relay_census_changed={k: [c_old.get(k, 0), c_new.get(k, 0)] for k in set(c_old) | set(c_new)
                                                                 if c_old.get(k, 0) != c_new.get(k, 0)})
Path(a.out).write_text(json.dumps(res, indent=1))
print('FP_HOPS', json.dumps({k: res[k] for k in ('moved_instances', 'old', 'new', 'moved_edges', 'moved_edges_newly_over_hop', 'lane_relay_census_changed')}))
