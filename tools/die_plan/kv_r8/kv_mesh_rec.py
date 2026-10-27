#!/usr/bin/env python3
"""CLOCK-KV-R7: convert a die_clock_mesh build dir (mesh.json, nets.json, tree_<C>.txt routed driver-input arrivals)
into the QC-CLK-MESH-2 'rec' format (qc_clk_mesh2.py deck/solve): xs/ys straps, ndr, nodes (every clock cell above the
mesh drivers, one stage each -> hierarchical tree variation per stage; one node per mesh-driver site, m cells in
parallel), taps = mesh loads (array stub BUFx4 inputs + band-tree root inputs) at their strap foot.
usage: kv_mesh_rec.py BUILD_DIR OUT_JSON"""
import json, sys, collections
d, out = sys.argv[1], sys.argv[2]
M = json.load(open(d + '/mesh.json')); N = json.load(open(d + '/nets.json'))['nets']
r3 = lambda v: round(float(v), 3)
xs, ys = [r3(x) for x in M['xs']], [r3(y) for y in M['ys']]
par = {}
for n in N:
    for l in n['loads']:
        par[l] = n['drv']
arr = {}
for C in ('TT', 'FF'):
    for l in open(f'{d}/tree_{C}.txt'):
        f = l.split()
        if f and f[0] in ('D', 'N', 'R') and len(f) >= 3:
            arr.setdefault(f[1], {})[C] = float(f[2])
nodes, tag = [], {}
depth = {}
def dep(c):
    if c in depth: return depth[c]
    p = par.get(c)
    depth[c] = 0 if (p is None or p.startswith('port:')) else dep(p) + 1
    return depth[c]
# driver sites
drv_cells = {}
for k, v in M['drivers'].items():
    for c in v['cells']:
        drv_cells[c] = k
anc = set()
for c in drv_cells:
    p = par[c]
    while p and not p.startswith('port:'):
        anc.add(p); p = par.get(p)
idx = 0
for c in sorted(anc, key=dep):
    tag[c] = '~' * dep(c) + '%06d' % idx; idx += 1
for c in sorted(anc, key=dep):
    p = par.get(c)
    nodes.append(dict(tag=tag[c], cell=c, parent=tag.get(p), leg_um=450.0, driver=False, site=None, arr={}))
nm = 0
for k, v in M['drivers'].items():
    c0 = v['cells'][0]; p = par[c0]
    assert all(par[c] == p for c in v['cells']), k
    s = v['site']; st = v['strap']
    if st == 'M9':
        x = xs[v['i']]; assert abs(x - s[0]) < 0.01, (k, s, x); site = [x, r3(s[1])]
    else:
        raise SystemExit(f'driver {k} on {st}')
    a = {C: sum(arr[c][C] for c in v['cells']) / len(v['cells']) for C in ('TT', 'FF')}
    nodes.append(dict(tag='~' * (dep(c0)) + 'D%06d' % nm, cell=k, parent=tag[p], leg_um=450.0, driver=True, site=site, arr=a,
                      mult=len(v['cells'])))
    nm += 1
taps = []
def foot(ft, strap):
    lay, i = strap
    return [xs[i], r3(ft[1])] if lay == 'M9' else [r3(ft[0]), ys[i]]
for t in M['taps']:
    if t.get('mesh_in'):
        continue
    taps.append(dict(part=t['stub'], port=t['port'], tap=foot(t['foot'], t['strap']), stub_um=t['stub_um'], kind='stub'))
for b in M.get("band_roots", []):
    taps.append(dict(part=b['root'], tree=b['tree'], tap=foot(b['foot'], b['strap']), stub_um=0.0, kind='band_root'))
rec = dict(source=d, extend_to_points=True, xs=xs, ys=ys, ndr=M['meta']['ndr'], m=M['meta']['m'], nodes=nodes, taps=taps,
           note=__doc__, checked='UNCHECKED')
json.dump(rec, open(out, 'w'))
mult = collections.Counter(n.get('mult') for n in nodes if n['driver'])
print('nodes', len(nodes), 'drivers', sum(n['driver'] for n in nodes), 'mult', dict(mult), 'taps', len(taps),
      'max depth', max(dep(c) for c in drv_cells))
