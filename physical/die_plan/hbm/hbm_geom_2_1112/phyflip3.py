# HBM-GEOM-2 11-12: phy_flip delta (COORD-approved): u_phy_Q of PHY_NC/PHY_NW -> y 889.92 MX; NW W pin windows
# (declared on q_mcb_nw ft slots, E face, type frame = die y - 16467.84) re-laid in y [0.496, <=880].
import json, sys, hashlib
sys.path.insert(0, sys.argv[1])          # tools/die_plan
import schema as S
src, out_plan, out_delta = sys.argv[2], sys.argv[3], sys.argv[4]
raw_b = open(src, 'rb').read(); R = json.loads(raw_b)
T = R['partition_types']; ops = []
Y = 889.92
for tn in ('PHY_NC', 'PHY_NW'):
    for h in T[tn]['hard_cores']:
        if h['inst'] == 'u_phy_Q':
            ops.append(dict(op='hard_core_pose', type=tn, inst='u_phy_Q',
                            frm=dict(origin_um=list(h['origin_um']), orient=h.get('orient', 'R0')),
                            to=dict(origin_um=[h['origin_um'][0], Y], orient='MX')))
            h['origin_um'] = [h['origin_um'][0], Y]; h['orient'] = 'MX'
    T[tn]['note'] = (T[tn].get('note') or '') + (' | phy_flip 11-12 (HBM-GEOM-2, COORD approved hbm-phy-face-blocked): '
                     'u_phy_Q at y 889.92 MX so the std-cell logic band y 0-880 touches the face pins')
# NW face windows
P0 = S.Plan(json.loads(raw_b), src)
slots = {s['name']: s for s in T['q_mcb_nw']['ft_slots']}
seq = [('L21x1', 'in', 'L21_0'), ('L114wx1', 'in', 'L114w_0'), ('L8x5', 'out', 'L8_5'), ('L63wx5', 'out', 'L63w_5')]
need = {pid: S.port_pins_count(P0.ports[pid]) for _, _, pid in seq}
LIM, GAP, LO = 880.0, 0.48, 0.496
def lay(per):
    lo, res = LO, []
    for nm, d, pid in seq:
        lays = slots[nm].get(d + '_layers', slots[nm].get('layers'))
        hi = S.window_for(lo, need[pid], lays, P0.layers, per_um=per, track_max=0.6)
        res.append((nm, d, [round(lo, 4), hi])); lo = hi + GAP
    return res
per = 6.0
while lay(per)[-1][2][1] > LIM:
    per += 0.01
res = lay(per)
for nm, d, win in res:
    k = d + '_window_um'
    ops.append(dict(op='ft_slot_window', type='q_mcb_nw', slot=nm, key=k, frm=slots[nm][k], to=win))
    slots[nm][k] = win
json.dump(R, open(out_plan, 'w'), indent=1)
ph = hashlib.sha256(open(out_plan, 'rb').read()).hexdigest()
# verify pins: every NW pin y (type frame of PHY_NW) <= LIM, and both sides coincide by construction
P1 = S.Plan(json.load(open(out_plan)), out_plan)
ys = [c - 16467.84 for _, _, pid in seq for _, _, c in P1.ports[pid] and P1.port_pins(pid)]
tot = sum(need.values())
D = dict(schema='hbm-geom-2.phy_flip.v2', tag='hbm-phy-face-blocked', status='COORD approved 11-12; for DIE-HBM-100 compose',
         base_plan_sha256=hashlib.sha256(raw_b).hexdigest(), result_plan_sha256=ph, ops=ops,
         nw_face=dict(pins=tot, span_um=[min(ys), max(ys)], pins_per_um=round(tot / (max(ys) - min(ys)), 3),
                      per_um_used=round(per, 2), budget_face_pins_per_um=P0.budgets['face_pins_per_um']),
         note='positions/orientation + NW W window re-lay only; no core shape, outline, bus width, lane or station change. '
              'NW_mcb (q_mcb_nw) E-face pins move with the PHY_NW W pins (same port windows).')
json.dump(D, open(out_delta, 'w'), indent=1)
print(json.dumps(D['nw_face']), ph[:16])
for o in ops: print(o)
