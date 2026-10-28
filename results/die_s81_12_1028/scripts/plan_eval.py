#!/usr/bin/env python3
"""DIE-S81-12 plan-time CA check on a given feed tree (ESTIMATE): locality.score with the feed tree injected (fish
region trees, spine hop delay; margins = shared clk_aocv g021 table, clock_variation=table equivalent, one-sided
droop, spice-scaled v, core latency class B, 5 % wander), then count_align_plan unchanged via cap_reading (K from
the OCV-inclusive window centre, DEPTH 4/8, start-tree path ambiguity).  Adds: fork start-port widths (sync at child
root, START-TREE-1 form), restoring stages every 5 hops, face supply per the plan check rule (check.py: face_layers
n > face_pin_layers -> budget x n / face_pin_layers).  usage: plan_eval.py REPO PLAN BIND V FEED(fish|json) OUT"""
import json, sys, collections, math
from pathlib import Path
repo, planp, bindp, v, feedj, out = sys.argv[1:7]; v = float(v)
sys.path.insert(0, f"{repo}/tools/die_plan")
import locality as L
import clk_aocv as CA
P = json.loads(Path(planp).read_text())
D = L.load_plan(P)
bind = json.loads(Path(bindp).read_text())
reg = {p: x["region"] for p, x in bind["parts"].items() if isinstance(x, dict) and x.get("region")}
for p in D["parts"]: reg.setdefault(p, p)
if feedj != "fish":
    fj = json.load(open(feedj)); _orig = L.feed_tree
    def feed_tree(G, E, X, v, kind="fwd"):
        taps = L.tap_points(G, X); par = fj["parent"]; kids = collections.defaultdict(list)
        for c, p in par.items():
            if p: kids[p].append(c)
        order = [fj["root"]]; i = 0
        while i < len(order): order += sorted(kids[order[i]]); i += 1
        assert len(order) == len(G), (len(order), len(G))
        return dict(root=fj["root"], parent=par, order=order, joined=[], kind=kind,
                    tap={(p, c): taps.get((p, c)) or L.xing_point(G[p]["bbox"], G[c]["bbox"]) for c, p in par.items() if p})
    L.feed_tree = feed_tree
S = L.score(D, reg, v, "fish")
R = S["crossings"]; cs = L.cap_reading(R, D["period"])
G, F = S["G"], S["F"]; Tr, _ = L.arrivals(G, F, v)
rows = []
for r in R:
    u = r["unshared_tt"] if "ua_tt" not in r else r["ua_tt"] + r["ub_tt"]
    cls = "tree-edge" if r["on_feed"] else ("long-loop" if u > 2500 else "short-loop")
    rows.append(dict(id=r["id"], ra=r["ra"], rb=r["rb"], width=r["width"], cls=cls, lca=r["lca"], hops=r["tree_hops"],
                     unshared_ps=round(u, 1), p_tt=r.get("p_tt"), p_ff=r.get("p_ff"), depth=r["depth"], K_kind=r["K_kind"],
                     amb=r["amb"], lat=r["lat"], m_lo=r["m_lo"], m_hi=r["m_hi"]))
def st(sel):
    s = [x for x in rows if sel(x)]
    m = [min(x["m_lo"], x["m_hi"]) for x in s if x["depth"]]
    return dict(n=len(s), bits=sum(x["width"] for x in s), depth=dict(collections.Counter(str(x["depth"]) for x in s)),
                min_margin=min(m) if m else None, below100=sum(1 for x in s if not x["depth"] or min(x["m_lo"], x["m_hi"]) < 100),
                max_unshared_ns=round(max((x["unshared_ps"] for x in s), default=0) / 1000, 2),
                amb=dict(collections.Counter(str(x["amb"]) for x in s)))
# fork start ports (one per feed edge, launch at the feed tap on the parent spine, sync at the child root entry)
T = CA.load(f"{repo}/tools/die_plan/clk_aocv_table_g021.json"); regs = {g["region"]: g for g in S["regions"]}
ff = T["classes"]["A"]["FF"]["mu_stage_ps"] / T["classes"]["A"]["TT"]["mu_stage_ps"]
def ocv(U, um, corner, sp):
    A = T["classes"]["A"][corner]; fc = A["cell_share"]; U = U * sp
    br = dict(cell_ps=fc * U, net_ps=(1 - fc) * U, stages={"A": max(1, round(U / A["mu_stage_ps"]))})
    z = dict(cell_ps=0.0, net_ps=0.0, stages={"A": 0})
    return CA.branch_pessimism(T, corner, z, br, um, False, "setup"), CA.branch_pessimism(T, corner, z, br, um, False, "hold")
ws = []
for c, p in F["parent"].items():
    if not p: continue
    g = regs[c]; um = (g["w_mm"] + g["h_mm"]) / 2 * 1000; U = v * um / 1000; w = 0
    for corner, sc, sp in (("TT", 1.0, 1.0485), ("FF", ff, 1.0552)):
        s, h = ocv(U * sc, um, corner, sp); w = max(w, s + h + 20)
    ws.append(w)
clean_lim = D["period"] / 2 - 2 * D["period"] / 8
depth_hops = {r: len(L.lineage(F, r)) - 1 for r in F["parent"]}
restore = sorted(r for r, d in depth_hops.items() if d > 0 and d % 5 == 0)
# faces per the plan check rule
B = P.get("budgets", {}); base = float(B.get("face_pins_per_um", 6)); nl0 = int(B.get("face_pin_layers", 2))
pt = {p["name"]: P["partition_types"][p["type"]] for p in P["partitions"]}
faces = []
for t in S["tracks"]["worst"]:
    a, b = t["pair"]; ga, gb = G[a]["bbox"], G[b]["bbox"]
    # face of a toward b
    fa = "N" if abs(ga[3] - gb[1]) < 1 else "S" if abs(ga[1] - gb[3]) < 1 else "E" if abs(ga[2] - gb[0]) < 1 else "W"
    fb = {"N": "S", "S": "N", "E": "W", "W": "E"}[fa]
    na = len((pt.get(a, {}).get("face_layers") or {}).get(fa, [])) ; nb = len((pt.get(b, {}).get("face_layers") or {}).get(fb, []))
    n = max(nl0, min(na or nl0, nb or nl0))
    sup = base * n / nl0 * t["face_um"]
    faces.append(dict(pair=t["pair"], bits=t["bits"], face=fa, layers=n, flat_ratio=t["ratio"], plan_rule_ratio=round(t["bits"] / sup, 3)))
summ = dict(feed=feedj, root=F["root"], regions=len(F["parent"]), crossings=len(rows), cap={k: cs[k] for k in ("depth4", "depth8", "fail", "worst_margin_lo_ps", "worst_margin_hi_ps", "max_path_ambiguous_cycles", "max_lat", "max_phys") if k in cs},
            all=st(lambda x: True), tree_edge=st(lambda x: x["cls"] == "tree-edge"), short_loop=st(lambda x: x["cls"] == "short-loop"),
            long_loop=st(lambda x: x["cls"] == "long-loop"), long_loop_pairs=len({(x["ra"], x["rb"]) for x in rows if x["cls"] == "long-loop"}),
            chain_max_hops=max(depth_hops.values()), chain_max_arrival_ps=round(max(Tr[r] + L.ins(G[r], v) for r in Tr)),
            start_ports=dict(n=len(ws), clean=sum(w <= clean_lim for w in ws), width_med=round(sorted(ws)[len(ws) // 2]), width_max=round(max(ws)), clean_limit=round(clean_lim)),
            restoring_stages=len(restore), faces_over_flat=sum(1 for f in faces if f["flat_ratio"] > 1), faces_over_plan_rule=sum(1 for f in faces if f["plan_rule_ratio"] > 1), faces=faces[:6])
Path(out).write_text(json.dumps(dict(summary=summ, rows=rows, restore=restore, feed=dict(root=F["root"], parent=F["parent"])), indent=0, default=str))
print(json.dumps(summ, default=str))
