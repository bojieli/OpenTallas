"""CLOCK-KV-R12 island-identity census over ALL pushdown records (mesh drivers + tree nodes + leg repeaters):
per hard-core module, the set of in-core island points in the CORE frame (incl. track_offset_um, orient) must be one
pattern for every instance (12.2a1). 1-nm rounding."""
import json, sys, collections
plan, mesh, tools, out = sys.argv[1:5]
sys.path.insert(0, tools)
import schema as S, die_clock_mesh as DCM
raw = json.load(open(plan)); raw.pop('plan_deltas', None); P = S.Plan(raw); M = json.load(open(mesh))
pd = M['pushdown']
roles = collections.Counter(r['role'] for r in pd)
pts = [(tuple(r['xy']), r['role']) for r in pd]
pts += [(tuple(d['site']), 'drv_site') for d in M['drivers'].values()]
mod = collections.defaultdict(list)
for pn, p in P.parts.items():
    x0, y0, x1, y1 = P.rect(pn)
    loc = [q for q in pts if x0 - 1 <= q[0][0] <= x1 + 1 and y0 - 1 <= q[0][1] <= y1 + 1]
    for c in P.types[p['type']].get('hard_cores', []):
        w, h = c['outline_um']; s = []
        for q, role in loc:
            u, v = DCM.core_frame(P, pn, c, q)
            if -1e-6 <= u <= w + 1e-6 and -1e-6 <= v <= h + 1e-6:
                s.append((round(u, 3), round(v, 3), 'n' if role in ('tree_node', 'leg_rep') else 'd'))
        mod[c['module']].append(tuple(sorted(set(s))))
res = {m: dict(instances=len(r), patterns=len(set(r)), with_islands=sum(1 for x in r if x),
               top=[[list(k), n] for k, n in collections.Counter(r).most_common(2)]) for m, r in mod.items()}
fail = [m for m, r in res.items() if r['patterns'] != 1]
json.dump(dict(roles=roles, fail=fail, modules=res), open(out, 'w'), indent=1)
print('pushdown roles', dict(roles), 'modules', len(res), 'FAIL', fail)
for m, r in res.items():
    if r['with_islands']: print(' ', m, r['instances'], 'with', r['with_islands'], 'patterns', r['patterns'], [len(k) for k, _ in r['top']], [n for _, n in r['top']])
