# HBM-GEOM-2 11-12: q_mcb_nw per-bit FF sites of the 4 PHY_NW slots follow their re-laid E windows (phy_flip).
# Each bit site whose y lies in the slot's OLD window band maps linearly into the NEW window, snapped to the 0.27-um
# row grid; a taken (row, column) slides to the next free 2.16-um column (+x first, then -x).  Order kept (monotone).
import json, sys, hashlib
from collections import defaultdict
src, out_plan, delta_in, out_delta = sys.argv[1:5]
raw = open(src, 'rb').read(); R = json.loads(raw); t = R['partition_types']['q_mcb_nw']
D = json.load(open(delta_in))
win = {(o['slot'], o['key']): (o['frm'], o['to']) for o in D['ops'] if o['op'] == 'ft_slot_window'}
CW, RH, CP = 1.404, 0.27, 2.16
occ = defaultdict(list)   # row key -> [x]
names = {s for s, _ in win}
for sl in t['ft_slots']:
    if sl['name'] in names: continue
    for st in sl.get('bit_sites_um') or []:
        for x, y in st: occ[round(y / RH)].append(x)
for c in t.get('internal_stations', []):
    for st in c.get('bit_sites_um') or []:
        for x, y in st: occ[round(y / RH)].append(x)
def free(x, r): return all(abs(x - q) >= CW - 1e-6 for q in occ[r])
moved = 0; maxd = 0.0; ops = []
for sl in t['ft_slots']:
    if sl['name'] not in names: continue
    (k, (o, n)), = [(kk[1], v) for kk, v in win.items() if kk[0] == sl['name']]
    for si, st in enumerate(sl.get('bit_sites_um') or []):
        cnt = 0
        if len({x for x, _ in st}) > 30:         # entry fan (stations 0/1): keep; runs + the band-entry fan remap
            for x, y in st: occ[round(y / RH)].append(x)
            continue
        for b, (x, y) in enumerate(st):
            if not (o[0] - 0.6 <= y <= o[1] + 0.6):
                occ[round(y / RH)].append(x); continue
            yt = n[0] + (min(max(y, o[0]), o[1]) - o[0]) * (n[1] - n[0]) / (o[1] - o[0])
            r = round(yt / RH)
            for dx in [0] + [s * j * CP for j in range(1, 40) for s in (1, -1)]:
                if free(x + dx, r): break
            else: raise SystemExit(f'no site {sl["name"]} st{si} bit{b}')
            nx, ny = round(x + dx, 4), round(r * RH, 4)
            occ[r].append(nx); st[b] = [nx, ny]; moved += 1; cnt += 1; maxd = max(maxd, abs(ny - yt) + abs(dx))
        if cnt: ops.append(dict(op='bit_sites_remap', type='q_mcb_nw', slot=sl['name'], station=si, bits=cnt, window=k, frm=o, to=n))
    sl['note'] = (sl.get('note') or '') + ' | phy_flip 11-12 (HBM-GEOM-2): bit sites remapped into the re-laid E window'
json.dump(R, open(out_plan, 'w'), indent=1)
ph = hashlib.sha256(open(out_plan, 'rb').read()).hexdigest()
D['ops'] += ops; D['base_plan_sha256'] = D['base_plan_sha256']; D['result_plan_sha256'] = ph
D['bit_sites_remapped'] = moved; D['bit_site_max_offset_um'] = round(maxd, 3)
json.dump(D, open(out_delta, 'w'), indent=1)
print('remapped', moved, 'max offset', round(maxd, 3), 'ops', len(ops), ph[:16])
