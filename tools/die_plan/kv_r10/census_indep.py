"""Independent island-identity census (CLOCK-KV-R10): closed containment + edge-margin report, per module,
independent of compose_align.census (no strict-inequality / any() filtering)."""
import json, sys, collections
plan, mesh, tools = sys.argv[1:4]
sys.path.insert(0, tools)
import schema as S
raw = json.load(open(plan)); raw.pop('plan_deltas', None)
P = S.Plan(raw); M = json.load(open(mesh))
TOL = 0.5
out = {}
for field in ('ideal', 'site'):
    mod = collections.defaultdict(list); near = []
    for pn, p in P.parts.items():
        t = P.types[p['type']]
        pts = [P.to_type(pn, d[field]) for d in M['drivers'].values()]
        for c in t.get('hard_cores', []):
            x, y = c['origin_um']; w, h = c['outline_um']; o = c.get('orient', 'R0'); s = []
            for px, py in pts:
                inside = x - TOL <= px <= x + w + TOL and y - TOL <= py <= y + h + TOL
                if not inside: continue
                u, v = px - x, py - y
                if o in ('MY', 'R180'): u = w - u
                if o in ('MX', 'R180'): v = h - v
                m = min(u, v, w - u, h - v)
                if m < 5.0: near.append((pn, c['inst'], c['module'], round(u, 3), round(v, 3), round(m, 3)))
                s.append((round(u, 3), round(v, 3)))
            mod[c['module']].append((pn + '/' + c['inst'], tuple(sorted(set(s)))))
    res = {}
    for m, rows in mod.items():
        sets = collections.Counter(s for _, s in rows)
        res[m] = dict(instances=len(rows), patterns=len(sets), sites=sorted({len(s) for s in sets}),
                      sets=[[list(s), n] for s, n in sets.most_common(3)])
    out[field] = dict(fail=[m for m, r in res.items() if r['patterns'] != 1],
                      with_islands={m: r for m, r in res.items() if any(r2[0] for r2 in r['sets'])},
                      modules_total=len(res), near_edge=near[:40], near_edge_n=len(near))
json.dump(out, open(sys.argv[4], 'w'), indent=1)
for f, r in out.items():
    print(f, 'modules', r['modules_total'], 'FAIL', r['fail'], 'near_edge(<5um)', r['near_edge_n'])
    for m, v in r['with_islands'].items(): print('  ', m, v['instances'], 'patterns', v['patterns'], 'sites', v['sites'], v['sets'][0][0])
