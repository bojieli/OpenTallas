#!/usr/bin/env python3
"""HNX-DIE 10-20: P3 die re-pack -- each HC bank ring (8 x hbfd hcb_Qk, ~0.30 mm2 each) goes INTO its quadrant's planned
HC_ENGINE block hce_Q (compact plan, 1598.4^2 = 2.555 mm2, abutting the band beside the hub hc_Q), as a 3 x 3 PERIMETER ring
(8 cells around an empty centre; every ring neighbour abuts, b7 -> b0 closes the ring), instead of the corner racetrack slots
of f4c_t9p3r (rings 12-15 mm from hc_Q; the hce_Q block was left to relay rows).

The 3 x 3 ring (3 x 548.856 + 2 gaps) is ~60 um wider than hce_Q, so the ring takes the free envelope around hce_Q: grown
from hce_Q until it meets another plan block (vmh_Q on one side, the hub column hc_Q / idxq_Q / cij_Q on the other,
sfucore_Q / sfus_* above and below), centred across x with HALO on both sides, and pushed vertically toward hc_Q.

    hnx_hcb_repack.py --src-tag f4c_t9p3r --tag f4c_t9p3s [--root REPO] [--gap 5.4] [--halo 5.4]
Writes physical/hbm_next/die/<tag>/ (grants with the moved hcbk_Qk slots, region map with hcb_Qk -> the hce_Q clock region,
pin files copied) and results/arch/hbm_next_1019/die/plan/<tag>/ (plan copied, unchanged); prints the ring geometry, the
ring -> hub Manhattan distance before/after and every overlap with plan blocks / grant slots (must be 0, else exit 2)."""
import argparse, json, shutil
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--src-tag', default='f4c_t9p3r'); ap.add_argument('--tag', default='f4c_t9p3s')
ap.add_argument('--root', default=str(Path(__file__).resolve().parents[3]))
ap.add_argument('--gap', type=float, default=5.4); ap.add_argument('--halo', type=float, default=5.4)
a = ap.parse_args()
R = Path(a.root); DS = R / 'physical/hbm_next/die' / a.src_tag; PS = R / 'results/arch/hbm_next_1019/die/plan' / a.src_tag
DT = R / 'physical/hbm_next/die' / a.tag; PT = R / 'results/arch/hbm_next_1019/die/plan' / a.tag
G = json.loads((DS / f'grants_hnx_{a.src_tag}.json').read_text())
RM = json.loads((DS / f'region_map_hnx_{a.src_tag}.json').read_text())
P = json.loads((PS / 'compact.P.json').read_text())
B = {k: v for k, v in P.items() if isinstance(v, dict) and 'x' in v}
W, H = G['floorplan']['die_um']
snap = lambda v, g=0.216: round(round(v / g) * g, 3)
slots = {s['name']: s for s in G['slots']}


def ov(r, q):
    return min(r[2], q[2]) - max(r[0], q[0]) > 1e-6 and min(r[3], q[3]) - max(r[1], q[1]) > 1e-6


def box(b):
    return (b['x'], b['y'], b['x'] + b['w'], b['y'] + b['h'])


rep = dict(tag=a.tag, src_tag=a.src_tag, gap_um=a.gap, halo_um=a.halo, rings={}, overlaps=[])
new = {}
for q in ('SW', 'SE', 'NW', 'NE'):
    hce, hub = B[f'hce_{q}'], B[f'hc_{q}']
    bank = [slots[f'hcbk_{q}{k}'] for k in range(8)]
    bw = max(s['outline']['w'] for s in bank); bh = max(s['outline']['h'] for s in bank)
    px, py = snap(bw + a.gap), snap(bh + a.gap)
    rw, rh = 2 * px + bw, 2 * py + bh
    hx0, hy0, hx1, hy1 = box(hce)
    others = [box(b) for k, b in B.items() if k != f'hce_{q}']
    # free envelope: grow hce_Q left/right (rows hy0..hy1) and down/up (columns hx0..hx1) to the nearest plan block
    L = max([o[2] for o in others if o[2] <= hx0 + 1e-6 and o[1] < hy1 and o[3] > hy0] + [0.0])
    Rt = min([o[0] for o in others if o[0] >= hx1 - 1e-6 and o[1] < hy1 and o[3] > hy0] + [W])
    Dn = max([o[3] for o in others if o[3] <= hy0 + 1e-6 and o[0] < hx1 and o[2] > hx0] + [0.0])
    Up = min([o[1] for o in others if o[1] >= hy1 - 1e-6 and o[0] < hx1 and o[2] > hx0] + [H])
    if Rt - L - 2 * a.halo < rw or Up - Dn - 2 * a.halo < rh:
        raise SystemExit(f'{q}: ring {rw:.1f}x{rh:.1f} does not fit envelope {Rt - L:.1f}x{Up - Dn:.1f} (halo {a.halo})')
    x0 = snap(L + (Rt - L - rw) / 2)
    hub_cy = hub['y'] + hub['h'] / 2
    y0 = snap(Dn + a.halo) if hub_cy < (hy0 + hy1) / 2 else snap(Up - a.halo - rh)
    # 3 x 3 perimeter, clockwise from the lower-left: b0 (0,0) b1 (1,0) b2 (2,0) b3 (2,1) b4 (2,2) b5 (1,2) b6 (0,2) b7 (0,1)
    cells = [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1)]
    old_d, new_d = [], []
    hc = (hub['x'] + hub['w'] / 2, hub['y'] + hub['h'] / 2)
    for k, (i, j) in enumerate(cells):
        s = slots[f'hcbk_{q}{k}']
        oc = (s['origin']['x'] + s['outline']['w'] / 2, s['origin']['y'] + s['outline']['h'] / 2)
        nx, ny = snap(x0 + i * px), snap(y0 + j * py)
        new[s['name']] = (nx, ny)
        nc = (nx + s['outline']['w'] / 2, ny + s['outline']['h'] / 2)
        old_d.append(abs(oc[0] - hc[0]) + abs(oc[1] - hc[1])); new_d.append(abs(nc[0] - hc[0]) + abs(nc[1] - hc[1]))
    rep['rings'][q] = dict(envelope=[round(L, 3), round(Dn, 3), round(Rt, 3), round(Up, 3)], ring=[x0, y0, round(x0 + rw, 3), round(y0 + rh, 3)],
                           pitch=[px, py], hce=[round(v, 3) for v in (hx0, hy0, hx1, hy1)],
                           bank_to_hub_um_old=[round(min(old_d)), round(max(old_d))], bank_to_hub_um_new=[round(min(new_d)), round(max(new_d))])
for s in G['slots']:
    if s['name'] in new:
        s['origin']['x'], s['origin']['y'] = new[s['name']]
        s['grant'] = 'hnx_die_hcb_hce_ring_1020'
        s['notes'] = ('HNX-DIE 10-20: HC bank in its quadrant HC_ENGINE block hce_Q (3x3 perimeter ring, ring neighbours abut '
                      f'at gap {a.gap} um, empty centre; beside hub hc_Q) -- re-pack of the f4c_t9p3r corner racetrack (12-15 mm to hc_Q)')
# overlap check: every moved slot vs plan blocks (except its hce_Q) and every other grant slot
sb = {s['name']: (s['origin']['x'], s['origin']['y'], s['origin']['x'] + s['outline']['w'], s['origin']['y'] + s['outline']['h'])
      for s in G['slots'] if s['name'] != 'die' and 'origin' in s and 'outline' in s}
for n in new:
    r = sb[n]
    if r[0] < 0 or r[1] < 0 or r[2] > W or r[3] > H:
        rep['overlaps'].append([n, 'OFF_DIE'])
    for k, b in B.items():
        if k != 'hce_' + n[5:7] and ov(r, box(b)):
            rep['overlaps'].append([n, 'plan ' + k])
    for k, o in sb.items():
        if k != n and ov(r, o):
            rep['overlaps'].append([n, 'slot ' + k])
G['version'] = f"{G.get('version', '')}+hnx_die_hcb_hce_ring_1020"
G['floorplan']['candidate'] = a.tag
RM.setdefault('instances', {})
for q in ('SW', 'SE', 'NW', 'NE'):
    reg = next(k for k, v in RM['regions'].items() if f'hce_{q}' in v.get('members', []))
    for k in range(8):
        RM['instances'][f'hcb_{q}{k}'] = dict(region=reg, site=RM['regions'][reg]['site'])
    rep['rings'][q]['clock_region'] = reg
RM['rule'] = str(RM.get('rule', '')) + ' | HNX-DIE 10-20: hcb_Qk -> the clock region holding hce_Q (ring inside hce_Q)'
DT.mkdir(parents=True, exist_ok=True)
(DT / f'grants_hnx_{a.tag}.json').write_text(json.dumps(G, indent=1) + '\n')
(DT / f'region_map_hnx_{a.tag}.json').write_text(json.dumps(RM, indent=1) + '\n')
shutil.copy(DS / f'pin_plan_{a.src_tag}.json', DT / f'pin_plan_{a.tag}.json')
for f in DS.glob('*.tcl'):
    shutil.copy(f, DT / f.name)
if PT.exists():
    shutil.rmtree(PT)
shutil.copytree(PS, PT)
(DT / 'hcb_repack_report.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(rep, indent=1))
if rep['overlaps']:
    raise SystemExit(2)
