#!/usr/bin/env python3
"""DIE-HBM-9 ESTIMATE (no build): re-tree the hub 4x3 local clock form (12.16 b(i): every data link is a tree edge or closes
a SHORT tree loop). A 4x3 grid has 17 faces and every spanning tree has 11 edges, so 6 face pairs are always off-tree; the
choice is which loops they close. Enumerates ALL spanning trees x roots of the grid with the shared spine hop delay
(locality.hop_delay, spine kind) and picks the MINIMUM-BOTTLENECK tree on off-tree unshared clock (tie: bits x unshared),
then scores it with the SHARED model unchanged (locality.score + cap_reading) by handing score() that parent map.
Same port construction as hbm8/hub/hub_ca_local.py (one port per face and direction, width = half the face bits).
usage: hub_retree_est.py REPO NET_JSON VARIANT V_TT_PS_MM OUT_JSON"""
import json, sys, itertools, collections
repo, netj, variant, v, outp = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
sys.path.insert(0, f"{repo}/tools/die_plan")
import locality as L
import clk_aocv as CA
N = json.load(open(netj)); Tt = CA.load(L.TABLE); P = 833.0
nx, ny = map(int, N["grid"].split("x"))
ORIG_FEED = L.feed_tree
res = {"scope": "ESTIMATE only (no build); shared locality.score + cap_reading, spine feed, forced tree = min-bottleneck enumeration",
       "net_json": netj, "variant": variant, "v_tt_ps_mm": v, "types": {}}
for tn, R in N["types"].items():
    W, H = 8216.64, 4320.0; cw, ch = W / nx, H / ny
    rows = R[variant]["all_faces"]; cells = [(x, y) for x in range(nx) for y in range(ny)]
    name = lambda c: f"c{c[0]}{c[1]}"
    plan = {"die": {"outline_um": [W, H], "period_ps": P}, "budgets": {"face_pins_per_um": 6.0},
            "partition_types": {"cell": {"outline_um": [cw, ch], "hard": True}},
            "partitions": [{"name": name(c), "type": "cell", "origin_um": [c[0] * cw, c[1] * ch]} for c in cells], "ports": []}
    fbits = {}
    for f in rows:
        o, x, y = f["face"][0], int(f["face"][1]), int(f["face"][2])
        a, b = ((x, y), (x + 1, y)) if o == "v" else ((x, y), (x, y + 1))
        fbits[frozenset((name(a), name(b)))] = f["bits"]
        if f["bits"] <= 0: continue
        for s, d in ((a, b), (b, a)):
            plan["ports"].append({"id": f"{f['face']}_{name(s)}", "src": {"part": name(s)}, "dst": {"part": name(d)},
                                  "width": max(1, f["bits"] // 2), "kind": "data"})
    D = L.load_plan(plan); reg = {p: p for p in D["parts"]}; padj = L.part_adjacency(D); M = L.traffic(D)
    G = L.region_geom(D, reg); X = L.crossings(D, reg, G, padj); taps = L.tap_points(G, X)
    faces = sorted(tuple(sorted(f)) for f in fbits)
    def hd(p, c):
        t = taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"]); return L.hop_delay(G, p, c, t, v, "spine")
    nodes = sorted(G)
    best = None; ntrees = 0
    for E in itertools.combinations(faces, len(nodes) - 1):
        par = {n: n for n in nodes}
        def find(a):
            while par[a] != a: par[a] = par[par[a]]; a = par[a]
            return a
        ok = True
        for a, b in E:
            ra, rb = find(a), find(b)
            if ra == rb: ok = False; break
            par[ra] = rb
        if not ok: continue
        ntrees += 1
        adj = collections.defaultdict(list)
        for a, b in E: adj[a].append(b); adj[b].append(a)
        off = [f for f in faces if f not in E]
        for root in nodes:
            parent = {root: None}; T = {root: 0.0}; order = [root]; i = 0
            while i < len(order):
                p = order[i]; i += 1
                for c in sorted(adj[p]):
                    if c not in parent: parent[c] = p; T[c] = T[p] + hd(p, c); order.append(c)
            def anc(n):
                s = [];
                while n is not None: s.append(n); n = parent[n]
                return s
            worst = 0.0; wsum = 0.0
            for a, b in off:
                A_ = anc(a); B_ = set(anc(b)); lca = next(n for n in A_ if n in B_)
                u = (T[a] - T[lca]) + (T[b] - T[lca]); worst = max(worst, u); wsum += u * fbits[frozenset((a, b))]
            ecc = max(T.values())
            key = (round(worst, 1), round(ecc, 1), wsum)
            if best is None or key < best[0]: best = (key, root, dict(parent), list(order), E)
    (worst, ecc, wsum), root, parent, order, E = best
    def forced(G_, E_, X_, v_, kind="spine"):
        tp = {}
        for c, p in parent.items():
            if p is not None: tp[(p, c)] = taps.get((p, c)) or L.xing_point(G_[p]["bbox"], G_[c]["bbox"])
        return dict(root=root, parent=parent, order=order, tap=tp, joined=[], kind="spine")
    out = {"spanning_trees": ntrees, "chosen": dict(root=root, parent=parent, off_tree=[f"{a}-{b}" for a, b in faces if (a, b) not in E],
           cheap_worst_off_unshared_ps=worst, cheap_spine_ecc_ps=ecc)}
    for nm, fn in (("spine_mst", ORIG_FEED), ("spine_retree", forced)):
        L.feed_tree = fn
        S = L.score(D, reg, v, "spine", padj, M, Tt); Xs = S["crossings"]; cs = L.cap_reading(Xs, P); s = S["summary"]
        L.feed_tree = ORIG_FEED
        offr = [r for r in Xs if not r["on_feed"]]
        out[nm] = dict(root=S["feed"]["root"], worst_unshared_on_ps=s["worst_unshared_on_feed_tt"], worst_unshared_off_ps=s["worst_unshared_off_feed_tt"],
                       off_feed=len(offr), off_bits=sum(r["width"] for r in offr), max_tree_hops=s["max_tree_hops"],
                       depth4=cs["depth4"], depth8=cs["depth8"], fail=cs["fail"], worst_margin_lo_ps=cs["worst_margin_lo_ps"],
                       worst_margin_hi_ps=cs["worst_margin_hi_ps"], max_p_tt=max(r["p_tt"] for r in Xs),
                       below100=sum(1 for r in Xs if r["depth"] is None or min(r["m_lo"], r["m_hi"]) < 100), max_lat=cs["max_lat"],
                       off_rows=[dict(id=r["id"], lca=r["lca"], tree_hops=r["tree_hops"], unshared_ps=round(r["ua_tt"] + r["ub_tt"], 1),
                                      p_tt=r["p_tt"], m_lo=r["m_lo"], m_hi=r["m_hi"], depth=r["depth"]) for r in offr])
        print(tn, nm, json.dumps({k: x for k, x in out[nm].items() if k != "off_rows"}), flush=True)
    print(tn, "chosen", json.dumps(out["chosen"]), flush=True)
    res["types"][tn] = out
json.dump(res, open(outp, "w"), indent=1)
