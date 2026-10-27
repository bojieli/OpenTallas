"""CLOCK-KV-R11 island-identity census (1-nm, closed containment) in the CORE frame incl. track_offset_um; driver
'site' points and node points of mesh.json; per module: patterns of in-core island sites."""
import json, sys, collections
plan, mesh, tools, out = sys.argv[1:5]
sys.path.insert(0, tools)
import schema as S, die_clock_mesh as DCM
raw = json.load(open(plan)); raw.pop('plan_deltas', None); P = S.Plan(raw); M = json.load(open(mesh))
pts = [tuple(d['site']) for d in M['drivers'].values()]
mod = collections.defaultdict(list)
for pn, p in P.parts.items():
    x0, y0, x1, y1 = P.rect(pn)
    loc = [q for q in pts if x0 - 1 <= q[0] <= x1 + 1 and y0 - 1 <= q[1] <= y1 + 1]
    for c in P.types[p['type']].get('hard_cores', []):
        w, h = c['outline_um']; s = []
        for q in loc:
            u, v = DCM.core_frame(P, pn, c, q)
            if -1e-6 <= u <= w + 1e-6 and -1e-6 <= v <= h + 1e-6:
                s.append((round(u, 3), round(v, 3)))
        mod[c['module']].append(tuple(sorted(set(s))))
res = {m: dict(instances=len(r), patterns=len(set(r)), top=[[list(k), n] for k, n in collections.Counter(r).most_common(2)])
       for m, r in mod.items()}
fail = [m for m, r in res.items() if r['patterns'] != 1]
json.dump(dict(fail=fail, modules=res), open(out, 'w'), indent=1)
print('modules', len(res), 'FAIL', fail)
for m, r in res.items():
    if any(k for k, _ in r['top']): print(' ', m, r['instances'], 'patterns', r['patterns'], r['top'][0])
