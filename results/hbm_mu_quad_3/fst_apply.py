#!/usr/bin/env python3
"""HBM-MU-QUAD-3 delta (F4): adopt hbm_final_stations.py candidates for q_hub_nw/q_hub_ne (final-pin station
regeneration on the fixed core rectangles, priced register count preserved; FAIL rows keep their original data), then
re-station any remaining > reach first/last hop along a free L path (x then y, registers <= 360 um apart on free
4.32-um sites).  Records added cycles per station.  Usage: fst_apply.py TOOLS PLAN_DIR FST_DIR"""
import json, sys, pathlib, hashlib
sys.path.insert(0, sys.argv[1]); import hub_repack as HR
pd = pathlib.Path(sys.argv[2]); F = pathlib.Path(sys.argv[3])
P = json.load(open(pd / 'die_plan.json')); rep = json.load(open(pd / 'delta_report.json')); G = HR.G
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])  # noqa: E731
out = {}
for k in ('nw', 'ne'):
    tn = f'q_hub_{k}'; t = json.load(open(F / k / 'candidate_type.json')); r = json.load(open(F / k / 'report.json'))
    W, H = t['outline_um']; ras = HR.Raster(W, H, [HR._core_rect(h) for h in t.get('hard_cores', [])])
    fixed = []
    for i, s in enumerate(t['internal_stations']):
        pts = [s['from_um']] + s.get('regs_um', []) + [s['to_um']]
        if max(md(a, b) for a, b in zip(pts, pts[1:])) <= 405 + 1e-6:
            continue
        new = [pts[0]]
        for a, b in zip(pts, pts[1:]):
            if md(a, b) > 405:
                cur = list(new[-1]); legs = [(0, b[0]), (1, b[1])]
                for ax, tgt in legs:
                    while abs(tgt - cur[ax]) > 1e-6 and md(cur, b) > 360:
                        step = min(345.6, abs(tgt - cur[ax])); nxt = list(cur); nxt[ax] += step if tgt > cur[ax] else -step
                        q = [round(round(nxt[0] / G) * G, 3), round(round(nxt[1] / G) * G, 3)]
                        q = [min(max(q[0], 0), W), min(max(q[1], 0), H)]
                        for dd in range(0, 20):
                            if ras.free(q[0] + (dd * G if ax == 1 else 0), q[1] + (dd * G if ax == 0 else 0)):
                                q = [round(q[0] + (dd * G if ax == 1 else 0), 3), round(q[1] + (dd * G if ax == 0 else 0), 3)]; break
                        new.append(q); cur = q
            new.append(list(b))
        add = len(new) - len(pts)
        s['regs_um'] = new[1:-1]
        fixed.append(dict(station=i, conn=s.get('conn'), added=add, max_hop=round(max(md(a, b) for a, b in zip(new, new[1:])), 2)))
    P['partition_types'][tn] = t
    out[tn] = dict(regen_added_cycles=r['added_cycles'], regen_pass=sum(x['verdict'] == 'PASS' for x in r['rows']),
                   regen_fail_kept_original=len(r['failed']), lpath_fixed=fixed,
                   max_hop_um=round(max(max(md(a, b) for a, b in zip(p, p[1:])) for p in ([s['from_um']] + s.get('regs_um', []) + [s['to_um']] for s in t['internal_stations'])), 2))
rep['F4_hub_final_stations'] = out
s = json.dumps(P, indent=1) + '\n'
(pd / 'die_plan.json').write_text(s); (pd / 'die_plan.sha256').write_text(hashlib.sha256(s.encode()).hexdigest() + '  die_plan.json\n')
(pd / 'delta_report.json').write_text(json.dumps(rep, indent=1) + '\n')
print(json.dumps(dict(sha=hashlib.sha256(s.encode()).hexdigest()[:12], **{k: {kk: v for kk, v in o.items()} for k, o in out.items()})))
