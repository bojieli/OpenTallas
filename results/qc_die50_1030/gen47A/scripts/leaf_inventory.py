#!/usr/bin/env python3
"""DIE-QC-39: fixed-tree load inventory for the leaf-driver ODB = trunk-side inverter A pins (role clock_leaf).
FF CLK pins now hang on leaf nets (leaf side inverter Y), so they are no tree loads. Net = the cluster's trunk net
(leaf_clusters.json, the net the FFs were on); stage = the inverter's stage (provider_cells_leaf.json);
shapes = actual M1 A pin metal read back from the applied ODB (export_geometry119)."""
import json, sys, collections
geom, clusters, cells, out = sys.argv[1:5]
g = json.load(open(geom)); cl = json.load(open(clusters))['clusters']
inv = {c['inst']: c for c in json.load(open(cells))['cells'] if c.get('role') == 'clock_leaf'}
shapes = collections.defaultdict(list)
for owner, pin, ly, *r in g['signal_shapes']:
    if pin == 'A' and owner.startswith('start_provider/ot_leaf_ck') and owner.endswith('_a'):
        shapes[owner].append([ly, *r])
loads = []
for c in cl:
    nm = f"ot_leaf_ck{c['cluster']}_a"; q = inv[nm]; inst = 'start_provider/' + nm
    if not shapes[inst]: raise SystemExit(f'no A pin metal for {inst}')
    loads.append(dict(inst=inst, stage=q['stage'], net=c['net'], master=q['master'], role='clock_leaf', pin='A',
                      shapes_dbu=shapes[inst]))
if len(loads) != len(shapes): raise SystemExit(f'cluster/inverter mismatch {len(loads)} vs {len(shapes)}')
json.dump(dict(dbu=g['dbu'], loads=loads), open(out, 'w'))
print('LEAF_LOADS', len(loads), 'nets', len({l['net'] for l in loads}), collections.Counter(l['master'] for l in loads))
