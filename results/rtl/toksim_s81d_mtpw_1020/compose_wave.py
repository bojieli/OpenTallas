"""TOKSIM-S81D/MTPW: per-position S029 stage busy from the composer's CURRENT per-node cycles (read-only import of
/home/ubuntu/wt/toksim-s81b tools/toksim_s81_compose.py @c26aef028), grade-split, excluding the stage hop out
(V.L20.substage_hop0 = DAG wave.hop). Prints JSON."""
import json, sys, collections
sys.path.insert(0, sys.argv[1] + '/tools')
import toksim_s81_compose as C
d = json.load(open(C.DAGS['mtp']))
ops, slots, xparts, files, exc, ins = C.load_elements(C.OUT / 'elements')
for o in ins: ops[(o.get('dag_cls'), o['op'])] = o
d = C.insert_nodes(d, ins)
gk = {g['id']: g['kind'] for g in d['groups']}
base = json.load(open(C.BASE)); xd = {}
for t in base['workloads']['mtp']['terms']:
    if t['kind'] == 'xdie': xd.setdefault(t['slot'], []).append(t)
by = collections.Counter(); old = 0.0; nodes = []
for n in d['nodes']:
    if n.get('group') != 'V.S029' or n['id'] == 'V.L20.substage_hop0':
        continue
    o = float(n['cycles']); old += o
    if n.get('cls') in ('coll', 'hop'):
        parts = xd.get(f'{C.lkey(n, gk)}.xdie.{n["id"]}', [])
        v = [C.xdie_part(p, xparts) for p in parts] if parts else [(o, 'priced')]
        for c, g in v: by[g] += c
        nodes.append((n['id'], o, sum(c for c, _ in v), 'xdie'))
        continue
    g = {'measured': 'measured-old-RTL', 'measured+vendor': 'measured-old-RTL'}.get((n.get('src') or {}).get('grade'), 'priced')
    new, tail = o, 0.0
    ov = ops.get((n.get('cls'), n.get('op'))) or ops.get((None, n.get('op')))
    if ov:
        c, how = C.node_cycles(n, ov)
        if c is not None:
            new, g, tail = c, ov['grade'], float(ov.get('tail_priced') or 0)
    by[g] += new; by['priced'] += tail
    nodes.append((n['id'], o, new + tail, g))
tot = sum(by.values())
print(json.dumps(dict(old_busy_nodes=round(old, 1), new_busy=round(tot, 1), by_grade={k: round(v, 1) for k, v in by.items()},
                      nodes=nodes), indent=1))
