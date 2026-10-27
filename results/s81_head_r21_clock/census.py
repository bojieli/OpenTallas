"""HEAD-R21 endpoint census on the plan: replace hd_serdes published grid endpoints with schema.tap_grid of the plan
(validated: old plan reproduces the old 384 serdes points exactly), then reach to the mesh straps."""
import json, sys
W, plan_old, plan_new, epf, strapf, out = sys.argv[1:7]
sys.path.insert(0, W + '/tools/die_plan'); import schema as S
def die_pts(planf):
    P = S.Plan(S.load(planf)); raw = json.load(open(planf)); t = raw['partition_types']['hd_serdes']; w, h = t['outline_um']
    pts = []
    for q in raw['partitions']:
        if q['type'] != 'hd_serdes': continue
        ox, oy = q['origin_um']; o = q.get('orient', 'R0')
        for n, x, y in S.tap_grid(P, 'hd_serdes'):
            lx, ly = {'R0': (x, y), 'MX': (x, h - y), 'MY': (w - x, y), 'R180': (w - x, h - y)}[o]
            pts.append(dict(part=q['name'], type='hd_serdes', port=n, kind='published_grid_clock', type_xy_um=[x, y], die_xy_um=[round(ox + lx, 4), round(oy + ly, 4)],
                            source='schema.tap_grid (HEAD-R21 census)', physical_attachment_required=True))
    return pts
ep = json.load(open(epf))['endpoints']
old = sorted((e['part'], round(e['die_xy_um'][0], 2), round(e['die_xy_um'][1], 2)) for e in ep if e['type'] == 'hd_serdes')
mine = sorted((e['part'], round(e['die_xy_um'][0], 2), round(e['die_xy_um'][1], 2)) for e in die_pts(plan_old))
assert old == mine, ('transform mismatch', len(old), len(mine), [a for a in mine if a not in old][:3])
new = [e for e in ep if e['type'] != 'hd_serdes'] + die_pts(plan_new)
s = json.load(open(strapf))
def dist(p, z):
    x, y = p
    if z[0] == 'M8': return abs(y - z[1]) + max(0, z[2] - x, x - z[3])
    return abs(x - z[1]) + max(0, z[2] - y, y - z[3])
r = [min(dist(e['die_xy_um'], z) for z in s) for e in new]
sd = [x for x, e in zip(r, new) if e['type'] == 'hd_serdes']
res = dict(validated_old_serdes_points=len(old), endpoints=len(new), kinds={k: sum(1 for e in new if e['kind'] == k) for k in {e['kind'] for e in new}},
           serdes_taps=len(sd), serdes_reach_max_um=round(max(sd), 3), over_450=sum(1 for x in r if x > 450), max_reach_um=round(max(r), 3))
json.dump(dict(status='PASS' if res['over_450'] == 0 else 'FAIL', summary=res, endpoints=new), open(out, 'w'), indent=1)
print(json.dumps(res))
