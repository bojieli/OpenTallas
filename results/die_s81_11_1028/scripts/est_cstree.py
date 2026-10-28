#!/usr/bin/env python3
"""DIE-S81-11 ESTIMATE (12.16 b(i)/(iv)): start (reset-release) tree derived from the CLOCK tree instead of the
min-ambiguity tree: Prim from a root over directed crossings, edge weight = unshared clock max(a,b) of the crossing
(minimum-bottleneck tree: every tree path's worst hop has the least unshared clock possible), ties fewer sync values,
larger sync distance.  Everything else = count_align_plan.plan (CA-OCV-1 hull rows, skew-clean) unchanged."""
import json, sys, copy, heapq
MT, OUT = sys.argv[1], sys.argv[2]
sys.path.insert(0, MT)
import count_align_plan as C
rows = json.load(open(OUT + "/rows_hull.json"))
SK = (46.9, 79.4)
ROOT = [None]
def us(r): return max(r.get("unshared_a_ps", 0), r.get("unshared_b_ps", 0))
def tree_clock(rows_, regions):
    out = {}
    for r in rows_:
        if r["src"] != r["dst"]:
            out.setdefault(r["src"], []).append(r)
    best = None
    for root in ([ROOT[0]] if ROOT[0] else regions):
        par = {root: None}; h = []
        for r in out.get(root, []):
            heapq.heappush(h, (us(r), r["_nv"], -r["_dist"], r["port"], r))
        while h:
            w, nv, nd, p, r = heapq.heappop(h)
            if r["dst"] in par: continue
            par[r["dst"]] = (r["src"], r)
            for q in out.get(r["dst"], []):
                if q["dst"] not in par:
                    heapq.heappush(h, (us(q), q["_nv"], -q["_dist"], q["port"], q))
        bott = max((us(v[1]) for v in par.values() if v), default=0)
        key = (len(regions) - len(par), bott)
        if best is None or key < best[0]:
            best = (key, root, par)
    return best[1], best[2]
C.directed_tree = tree_clock
res = {}
for root in [None]:
    s, out, regs = C.plan(copy.deepcopy(rows), 833.0, 833.0 / 8, 0.05, 26.5, 0, None, SK, True)
    f = [o for o in out if not o.get("depth")]
    print(json.dumps(dict(root=s["tree_root"], fail=s["fail"], d4=s["depth4"], d8=s["depth8"], lo=s["worst_margin_lo_ps"],
          hi=s["worst_margin_hi_ps"], amb_edges=len(s["tree_edges_ambiguous"]), max_tree_depth=s["max_tree_depth"],
          max_path_amb=s["max_path_ambiguous_cycles"], lat_vs_old3=s["lat_total_vs_old3"],
          padded=s.get("start_skew_clean", {}).get("padded_edges")), indent=0))
    from collections import Counter
    print(Counter((min(o["src"], o["dst"]), max(o["src"], o["dst"])) for o in f).most_common(40))
    # what L_hi would each failing crossing need: interval width breakdown
    for o in sorted(f, key=lambda o: -o["L_hi_ps"])[:60]:
        r = next(q for q in rows if q["port"] == o["port"])
        print("FAIL", o["port"], o["src"], o["dst"], "amb", o["path_ambiguous_cycles"], "Lw", o["L_width_ps"], "Lhi", o["L_hi_ps"], "unsh", round(us(r)))
    json.dump(dict(summary=s, regions=regs, crossings=out), open(OUT + "/plan_cstree.json", "w"), indent=0)
