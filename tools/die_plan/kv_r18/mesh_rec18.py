#!/usr/bin/env python3
"""CLOCK-KV-R18 (copy of kv_r17/mesh_rec17.py, used on the R18 band_feed strap build: band stubs are mesh loads, rec band = []): die_clock_mesh build dir -> QC-CLK-MESH-2 'rec' (qc_clk_mesh2.py netlist/solve) for the R15 clock.
Differences from kv_r7/kv_mesh_rec.py (R7/R8, mesh-fed band roots):
  * mesh loads = the 1824 array stub inputs only.  R15 band roots are LEAF-FED (band_feed leaf: the band root sits on the
    same leaf net as the mesh drivers of its leaf site), so they are not mesh loads; they are kept in rec['band'] as
    tree-fed pseudo loads: parent = the leaf tree node, routed arrival = tree_<C>.txt 'B' line (band root input).
  * every tree node carries xy (place.json) and routed arrivals (tree_<C>.txt N/D lines) so the MC can apply the
    12.4a b1 within-die distance gradient along the real tree paths (mesh_mc17.py).
usage: mesh_rec17.py BUILD_DIR OUT_JSON"""
import json, sys, collections
d, out = sys.argv[1], sys.argv[2]
M = json.load(open(d + '/mesh.json')); N = json.load(open(d + '/nets.json'))['nets']; P = json.load(open(d + '/place.json'))
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
        if f and f[0] in ('D', 'N', 'R', 'B') and len(f) >= 3:
            arr.setdefault(f[1], {})[C] = float(f[2])
depth = {}
def dep(c):
    if c in depth: return depth[c]
    p = par.get(c)
    depth[c] = 0 if (p is None or p.startswith('port:')) else dep(p) + 1
    return depth[c]
drv_cells = {c: k for k, v in M['drivers'].items() for c in v['cells']}
band = M.get('band_roots', [])
anc = set()
for c in list(drv_cells) + [b['root'] for b in band if b.get('feed') == 'leaf']:
    p = par[c]
    while p and not p.startswith('port:'):
        anc.add(p); p = par.get(p)
tag, nodes = {}, []
for i, c in enumerate(sorted(anc, key=lambda c: (dep(c), c))):
    tag[c] = '~' * dep(c) + '%06d' % i
for c in sorted(anc, key=lambda c: (dep(c), c)):
    nodes.append(dict(tag=tag[c], cell=c, parent=tag.get(par.get(c)), leg_um=450.0, driver=False, site=None,
                      xy=[r3(P[c]['x']), r3(P[c]['y'])], arr=arr[c]))
for nm, (k, v) in enumerate(M['drivers'].items()):
    c0 = v['cells'][0]; p = par[c0]
    assert all(par[c] == p for c in v['cells']), k
    s = v['site']
    assert v['strap'] == 'M9' and abs(xs[v['i']] - s[0]) < 1.0, (k, s)   # PG-track snap <= 0.68 um (meta pg_axis_snap_max_um)
    a = {C: sum(arr[c][C] for c in v['cells']) / len(v['cells']) for C in ('TT', 'FF')}
    nodes.append(dict(tag='~' * dep(c0) + 'D%06d' % nm, cell=k, parent=tag[p], leg_um=450.0, driver=True,
                      site=[xs[v['i']], r3(s[1])], xy=[xs[v['i']], r3(s[1])], arr=a, mult=len(v['cells'])))
def foot(ft, strap):
    lay, i = strap
    return [xs[i], r3(ft[1])] if lay == 'M9' else [r3(ft[0]), ys[i]]
taps = [dict(part=t['stub'], port=t['port'], tap=foot(t['foot'], t['strap']), stub_um=t['stub_um'], kind='stub')
        for t in M['taps'] if not t.get('mesh_in')]
# mesh-fed band roots (R6-R14 form, feed != leaf) are genuine mesh loads at their strap foot (kv_r7/kv_mesh_rec.py)
taps += [dict(part=b['root'], tree=b['tree'], tap=foot(b['foot'], b['strap']), stub_um=0.0, kind='band_root')
         for b in band if b.get('feed') != 'leaf']
band = [b for b in band if b.get('feed') == 'leaf']
brec = [dict(root=b['root'], tree=b['tree'], parent=tag[par[b['root']]], parent_cell=par[b['root']],
             xy=[r3(P[b['root']]['x']), r3(P[b['root']]['y'])], arr=arr[b['root']], leaf_driver=b.get('leaf_driver'))
        for b in band]
root = [n for n in nodes if n['parent'] is None]
assert len(root) == 1, root
rec = dict(source=d, extend_to_points=True, xs=xs, ys=ys, ndr=M['meta']['ndr'], m=M['meta']['m'], nodes=nodes, taps=taps,
           band=brec, root_xy=root[0]['xy'], plan_sha256=M['meta'].get('plan_sha256'), note=__doc__, checked='UNCHECKED')
json.dump(rec, open(out, 'w'))
print('nodes', len(nodes), 'drivers', sum(n['driver'] for n in nodes), 'mult',
      dict(collections.Counter(n.get('mult') for n in nodes if n['driver'])), 'mesh loads', len(taps), 'band roots', len(brec),
      'max depth', max(dep(c) for c in drv_cells), 'root', root[0]['cell'], root[0]['xy'])
