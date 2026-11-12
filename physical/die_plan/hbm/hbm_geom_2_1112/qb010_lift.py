# HBM-GEOM-2 11-12: q_b010 S-face un-block, positions only: lift the bottom hard-core group (15 idx macros, y 4.32-486.43)
# by DY so the S face pins get a std-cell band (> the 10-um kit halo) under them; slot / station regs that the lifted
# group would cover move to the free band above it.
import json, sys, hashlib
src, out_plan, out_delta = sys.argv[1:4]
DY, NEWY = 17.28, 509.76
# hop-preserving re-sites (G0 hops <= 405 via the slot regs; clear of the lifted group, top 503.71)
FIX = {('L5056y0', 1): [801.36, 291.6], ('L5070y1', 8): [330.0, 509.76], ('L733y1', 2): [32.4, 509.76], ('L733y1', 3): [430.0, 509.76],
       ('L733y1', 4): [792.72, 475.2], ('L734y3', 2): [28.08, 509.76], ('L734y3', 3): [426.0, 509.76], ('L734y3', 4): [792.72, 479.52]}
raw = open(src, 'rb').read(); R = json.loads(raw); t = R['partition_types']['q_b010']; ops = []
low = [h for h in t['hard_cores'] if h['origin_um'][1] < 579]
boxes = []
for h in low:
    o = list(h['origin_um']); h['origin_um'] = [o[0], round(o[1] + DY, 4)]
    ops.append(dict(op='hard_core_pose', type='q_b010', inst=h['inst'], frm=o, to=h['origin_um']))
    x0, y0 = h['origin_um']; boxes.append((x0 - 1, y0 - 1, x0 + h['outline_um'][0] + 1, y0 + h['outline_um'][1] + 1))
top = max(b[3] for b in boxes)
def hit(x, y): return any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes)
bad = []
for sl in t['ft_slots']:
    for i, v in enumerate(sl.get('regs_um') or []):
        if (sl['name'], i) in FIX:
            ops.append(dict(op='slot_reg', type='q_b010', slot=sl['name'], k=i, frm=list(v), to=FIX[(sl['name'], i)])); v[:] = FIX[(sl['name'], i)]
    for i, v in enumerate(sl.get('regs_um') or []):
        if hit(*v):
            if 480 < v[1] < NEWY:
                ops.append(dict(op='slot_reg', type='q_b010', slot=sl['name'], k=i, frm=list(v), to=[v[0], NEWY])); v[1] = NEWY
            else: bad.append((sl['name'], 'reg', v))
    for i, site in enumerate(sl.get('bit_sites_um') or []):
        for x, y in site:
            if hit(x, y): bad.append((sl['name'], 'bit_site', i, x, y)); break
for s in t['internal_stations']:
    for i, v in enumerate(s['regs_um']):
        if hit(*v):
            if 480 < v[1] < NEWY:
                ops.append(dict(op='istation_reg', type='q_b010', conn=s['conn'], k=i, frm=list(v), to=[v[0], NEWY])); v[1] = NEWY
            else: bad.append(('ist', s['conn'], v))
for tp in t['clock'].get('taps', []):
    if hit(*tp['xy']): bad.append(('tap', tp['name']))
if hit(*t['clock']['tap_um']): bad.append(('tap_um',))
t['note'] = (t.get('note') or '') + f' | qb010-lift 11-12 (HBM-GEOM-2, COORD hbm-phy-face-blocked): bottom 15 idx macros +{DY} um, S std-cell band under the S face pins'
json.dump(R, open(out_plan, 'w'), indent=1)
D = dict(schema='hbm-geom-2.qb010_lift.v1', tag='hbm-phy-face-blocked', base_plan_sha256=hashlib.sha256(raw).hexdigest(),
         result_plan_sha256=hashlib.sha256(open(out_plan, 'rb').read()).hexdigest(), dy_um=DY, group_top_um=top - 1,
         unresolved=bad, ops=ops, note='positions only: no reshape, no outline, no pin/window change')
json.dump(D, open(out_delta, 'w'), indent=1)
print('ops', len(ops), 'unresolved', bad, 'top', top - 1, D['result_plan_sha256'][:16])
for o in ops[15:]: print(o)
