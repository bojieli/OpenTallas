"""free macro-free area near each failing landing bus (analysis only)"""
import json, sys, math, collections
sys.path.insert(0, 'tools/die_plan')
import numpy as np
import clock_landing_plan as CLP, reset_tree as RT
P = json.load(open(sys.argv[1])); S = json.load(open(sys.argv[2]))
T = P['partition_types']; F = S['collector']['placement_failures']
g = 2.16; margin = 17.28
out = []
byt = collections.defaultdict(list)
for f in F: byt[f['type']].append(f)
for tn, fs in sorted(byt.items()):
    t = T[tn]; w, h = t['outline_um']
    nx, ny = int(w // g), int(h // g)
    occ = np.zeros((nx, ny), bool)
    obs = RT.blockages(t)
    for slot in t.get('ft_slots', []):
        cell = slot.get('bit_site_cell_um', [1.404, .27])
        for st in slot.get('bit_sites_um', []):
            if st: obs.append([min(p[0] for p in st)-cell[0]/2, min(p[1] for p in st)-cell[1]/2, max(p[0] for p in st)+cell[0]/2, max(p[1] for p in st)+cell[1]/2])
        if not slot.get('bit_sites_um'):
            obs += [[x-2.16, y-2.16, x+2.16, y+2.16] for x, y in slot.get('regs_um', [])]
    for o in obs:
        occ[max(0,int(o[0]//g)):int(math.ceil(o[2]/g)), max(0,int(o[1]//g)):int(math.ceil(o[3]/g))] = True
    m = int(margin // g); occ[:m, :] = occ[-m:, :] = occ[:, :m] = occ[:, -m:] = True
    X, Y = np.meshgrid((np.arange(nx)+.5)*g, (np.arange(ny)+.5)*g, indexing='ij')
    free_tot = (~occ).sum()*g*g
    for f in fs:
        b = CLP._bus_geom(t, f['bus']); width = int(b.get('width') or 0)
        rw = 64*math.ceil((width+1)/64); area = (5*rw*.2916 + 4*rw*.0729 + 160*.2916)/.40
        px, py = CLP._bus_xy(t, f['bus'])
        near = (np.abs(X-px)+np.abs(Y-py)) <= 405-2.16
        fa = ((~occ) & near).sum()*g*g
        out.append(dict(type=tn, bus=f['bus'], face=b['face'], width=width, need_um2=round(area), free_near_um2=round(fa), free_type_um2=round(free_tot), outline=t['outline_um'], cores=len(t.get('hard_cores', []))))
json.dump(out, open(sys.argv[3], 'w'), indent=1)
ok = sum(1 for r in out if r['free_near_um2'] >= r['need_um2'])
print('failures', len(out), 'free-area-near>=need', ok)
agg = collections.defaultdict(lambda: [0, 0, 0])
for r in out:
    a = agg[r['type']]; a[0] += r['need_um2']; a[1] = max(a[1], r['free_near_um2']); a[2] = r['free_type_um2']
for k, v in sorted(agg.items()): print(k, 'need_sum', v[0], 'max_free_near', v[1], 'free_type', v[2])
