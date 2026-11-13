"""pEv11 delta 3 (DIE-HBM-102): NW_io re-form, the NE_io pR9b spread intent applied to NW (HBM-GEOM-2 00:49 BAD: NW_io a30 GRT-0232,
overflow 68,651 in x 118-647 y 1088-1312, where the L51_i/L52_o chains converge with the u_lk_N0 rx bus over u_ep_N0).
(a) The two 612-bit chains to the ep W/top pin (181.459, 1304.088) leave the E face, run up the free E channel (x 488-648, E of
    u_ep_N0) and enter over the ep top in their own rows (L51_i y ~1395, L52_o y ~1435; band y 1334.9-1468.8 between u_ep_N0
    and u_host_ep).  L51_i no longer climbs through the ep at x 233 across the rx bus.  Reg counts kept (cycles unchanged).
(b) Every reg site shared by more than one small (<100-bit) S-pin slice gets its own point (10 um apart along the free row it
    sat on; DIE-LAYOUT-HBM nwspread.py form, generalised to every shared site).  Reg counts kept."""
import json, sys, hashlib, collections
src, dst = sys.argv[1], sys.argv[2]
D = json.load(open(src)); t = D['partition_types']['NW_io']; W, H = t['outline_um']; HALO = 1.08
B = [(c['origin_um'][0], c['origin_um'][1], c['origin_um'][0] + c['outline_um'][0], c['origin_um'][1] + c['outline_um'][1]) for c in t['hard_cores']]
free = lambda q: 0 <= q[0] <= W and 0 <= q[1] <= H and not any(a - HALO < q[0] < c + HALO and b - HALO < q[1] < e + HALO for a, b, c, e in B)
hops = lambda p: [round(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1) for a, b in zip(p, p[1:])]
NEW = {('bus:L51_i', 181.459): [[612.0, 1240.0], [400.0, 1395.0]],
       ('bus:L52_o', 181.459): [[632.0, 1290.0], [420.0, 1435.0]]}
bad = []; rep = {}
for s in t['internal_stations']:
    k = (s['conn'], round(s['to_um'][0], 3))
    if k in NEW and s.get('bits', 0) >= 600:
        new = NEW.pop(k); assert len(new) == len(s['regs_um']), (k, s['regs_um'])
        s['regs_um'] = [q + list(o[2:]) for q, o in zip(new, s['regs_um'])]
        h = hops([s['from_um'][:2]] + new + [s['to_um'][:2]]); rep[str(k)] = h
        bad += [q for q in new if not free(q)]
assert not NEW, NEW
# (b) shared small-slice sites
use = collections.defaultdict(list)
for s in t['internal_stations']:
    if (s.get('bits') or 0) >= 100: continue
    for j, q in enumerate(s['regs_um']): use[(round(q[0], 2), round(q[1], 2))].append((s, j))
taken = {(round(q[0], 2), round(q[1], 2)) for s in t['internal_stations'] for q in s['regs_um']}
nmv = 0
for site, lst in sorted(use.items()):
    if len(lst) < 2: continue
    x0, y0 = site; k = 0
    for i, (s, j) in enumerate(lst):
        if i == 0: continue
        while True:
            k += 1
            for cand in ([x0 + 10.0 * k, y0], [x0 - 10.0 * k, y0], [x0, y0 - 10.0 * k]):
                c = (round(cand[0], 2), round(cand[1], 2))
                p = [s['from_um'][:2]] + [q[:2] for q in s['regs_um']] + [s['to_um'][:2]]; p[j + 1] = cand
                if free(cand) and c not in taken and max(hops(p)) <= 405.0: break
            else: continue
            break
        taken.add(c); s['regs_um'][j] = cand + list(s['regs_um'][j][2:]); nmv += 1
mx = max(max(hops([s['from_um'][:2]] + [q[:2] for q in s['regs_um']] + [s['to_um'][:2]])) for s in t['internal_stations'])
inc = [q[:2] for s in t['internal_stations'] for q in s['regs_um'] if not free(q)]
dup = [k for k, v in collections.Counter((round(q[0], 2), round(q[1], 2)) for s in t['internal_stations'] if (s.get('bits') or 0) < 100 for q in s['regs_um']).items() if v > 1]
print('612-bit chains', rep, 'bad', bad); print('slice regs moved', nmv, 'max hop', mx, 'regs in cores', inc, 'shared small sites left', dup)
assert not bad and not inc and mx <= 405.0
t['note'] = t.get('note', '') + ' | pEv11 11-13 DIE-HBM-102 nwio spread (NE_io pR9b intent mirrored): L51_i/L52_o 612-bit W-pin chains up the E channel and over the ep top in own rows; every shared small-slice reg site split (' + str(nmv) + ' regs)'
s = json.dumps(D, indent=1); open(dst, 'w').write(s); print('sha', hashlib.sha256(s.encode()).hexdigest()[:12])
