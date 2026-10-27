import sys, json, collections
P = json.load(open(sys.argv[1] + '/die_plan.json'))
for tn in ('q_hub_nw', 'q_hub_ne'):
    t = P['partition_types'][tn]; W, H = t['outline_um']
    g = collections.defaultdict(lambda: [0, None, set()])
    pts = {}
    for s in t['internal_stations']:
        b = s['conn'][4:] if s['conn'].startswith('bus:') else None
        if not b: continue
        for p in (s['from_um'], s['to_um']):
            if p[1] <= .5 or p[1] >= H - .5:
                k = ('S' if p[1] <= .5 else 'N', round(p[0], 3), b); pts[k] = max(pts.get(k, 0), s.get('bits_parallel', s['bits']))
    xs = collections.defaultdict(list)
    for (f, x, b), v in pts.items():
        g[(f, b)][0] += v; xs[(f, b)].append(x)
    rows = []
    for (f, b), (v, _, _) in g.items():
        span = max(xs[(f, b)]) - min(xs[(f, b)]) + v / 6
        rows.append((v / max(max(xs[(f, b)]) - min(xs[(f, b)]), 1), f, b, v, round(min(xs[(f, b)])), round(max(xs[(f, b)]))))
    rows.sort(reverse=True)
    print(tn, [(round(r[0], 1),) + r[1:] for r in rows[:8]])
