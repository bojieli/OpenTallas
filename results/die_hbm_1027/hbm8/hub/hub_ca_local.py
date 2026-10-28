#!/usr/bin/env python3
"""DIE-HBM-8 ESTIMATE (no build): 12.16 / 12.16e count-aligned crossings of the hub A+B 4x3 region map in the LOCAL clock
form, with the SHARED model only: tools/die_plan/locality.py score (clk_aocv g021 0.21 %/mm table, one-sided droop between
regions, class-B core latency 250 TT / 202.5 FF, 5 % wander) and cap_reading (= count_align_plan unchanged: K, DEPTH 4/8,
start tree, path ambiguity, margins incl. the T/8 aperture). Each grid cell is one region (marked hard: both ends pay the
core latency). Every face of the 4x3 grid is a NEIGHBOUR crossing: far hub links are already hop chains of face crossings
(the L paths of hub_face_net.py), so no crossing spans more than one face. Ports: one per face and direction, width =
half the face's station bits (net-scored A+B placement).
Start / reset release (12.16 b(iv)): one dedicated start port per feed edge at the clock fork (CLK-LOCAL-EST-1 method,
startedge.py; COORD 08:0x: sync ON the forwarded spine at the fork tap = the release form, unshared ~0, width = 2 x 10 ps pin-cap): also reported with the sync at the child's root entry (unshared <= (w+h)/2 of the
child) and, worst, at the child's farthest leaf; width = setup + hold OCV (x spice 1.0485 TT / 1.0552 FF) + 2 x 10 ps;
clean-guaranteed if <= T/2 - 2 T/8 = 208 ps. Reset release to both ring counters rides the same start port.
usage: hub_ca_local.py REPO NET_JSON VARIANT V_TT_PS_MM OUT_JSON   (VARIANT e.g. A+B_net)"""
import json, sys, math, collections
repo, netj, variant, v, outp = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), sys.argv[5]
sys.path.insert(0, f"{repo}/tools/die_plan")
import locality as L
import clk_aocv as CA
N = json.load(open(netj)); Tt = CA.load(L.TABLE); P = 833.0; ap = P / 8
nx, ny = map(int, N["grid"].split("x"))
res = {"scope": "ESTIMATE only (no build); shared locality.py + count_align_plan via cap_reading", "net_json": netj,
       "variant": variant, "v_tt_ps_mm": v, "types": {}}
for tn, R in N["types"].items():
    W, H = 8216.64, 4320.0
    cw, ch = W / nx, H / ny
    rows = R[variant]["all_faces"]
    cells = [(x, y) for x in range(nx) for y in range(ny)]
    name = lambda c: f"c{c[0]}{c[1]}"
    plan = {"die": {"outline_um": [W, H], "period_ps": P}, "budgets": {"face_pins_per_um": 6.0},
            "partition_types": {"cell": {"outline_um": [cw, ch], "hard": True}},
            "partitions": [{"name": name(c), "type": "cell", "origin_um": [c[0] * cw, c[1] * ch]} for c in cells], "ports": []}
    for f in rows:
        o, x, y = f["face"][0], int(f["face"][1]), int(f["face"][2])
        a, b = ((x, y), (x + 1, y)) if o == "v" else ((x, y), (x, y + 1))
        if f["bits"] <= 0: continue
        for s, d in ((a, b), (b, a)):
            plan["ports"].append({"id": f"{f['face']}_{name(s)}", "src": {"part": name(s)}, "dst": {"part": name(d)},
                                  "width": max(1, f["bits"] // 2), "kind": "data"})
    D = L.load_plan(plan); reg = {p: p for p in D["parts"]}
    padj = L.part_adjacency(D); M = L.traffic(D)
    out = {}
    for feed in ("fish", "spine", "dme", "spt", "fwd", "top"):
        S = L.score(D, reg, v, feed, padj, M, Tt); X = S["crossings"]; cs = L.cap_reading(X, P)
        s = S["summary"]
        on = [r for r in X if r["on_feed"]]; off = [r for r in X if not r["on_feed"]]
        o = dict(crossings=len(X), on_feed=len(on), off_feed=len(off), max_tree_hops=s["max_tree_hops"],
                 worst_unshared_on_ps=s["worst_unshared_on_feed_tt"], worst_unshared_off_ps=s["worst_unshared_off_feed_tt"],
                 max_p_tt=max(r["p_tt"] for r in X), max_p_ff=max(r["p_ff"] for r in X),
                 depth4=cs["depth4"], depth8=cs["depth8"], fail=cs["fail"], worst_margin_lo_ps=cs["worst_margin_lo_ps"],
                 worst_margin_hi_ps=cs["worst_margin_hi_ps"], max_path_ambiguous_cycles=cs["max_path_ambiguous_cycles"],
                 tree_edges=cs["tree_edges"], tree_edges_clean=cs["tree_edges_clean"],
                 below100=sum(1 for r in X if r["depth"] is None or min(r["m_lo"], r["m_hi"]) < 100), max_lat=cs["max_lat"],
                 per_crossing=[dict(id=r["id"], ra=r["ra"], rb=r["rb"], bits=r["width"], on_feed=r["on_feed"], lca=r["lca"],
                                    unshared_ps=round(r["ua_tt"] + r["ub_tt"], 1), p_tt=r["p_tt"], p_ff=r["p_ff"], depth=r["depth"],
                                    m_lo=r["m_lo"], m_hi=r["m_hi"], amb=r["amb"], lat=r["lat"]) for r in X])
        if feed != "top":
            # start / reset release edges per feed edge (fork start port)
            G = {g["region"]: g for g in S["regions"]}
            ff = Tt["classes"]["A"]["FF"]["mu_stage_ps"] / Tt["classes"]["A"]["TT"]["mu_stage_ps"]
            def ocv(U, dist_um, corner, spice):
                A_ = Tt["classes"]["A"][corner]; fc = A_["cell_share"]; U = U * spice
                br = dict(cell_ps=fc * U, net_ps=(1 - fc) * U, stages={"A": max(1, round(U / A_["mu_stage_ps"]))})
                z = dict(cell_ps=0.0, net_ps=0.0, stages={"A": 0})
                return CA.branch_pessimism(Tt, corner, z, br, dist_um, False, "setup"), CA.branch_pessimism(Tt, corner, z, br, dist_um, False, "hold")
            st = []
            for k in S["feed"]["tap"]:
                p_, c_ = k.split("->"); g = G[c_]; d_root = (g["w_mm"] + g["h_mm"]) / 2 * 1000
                for where, um in (("tap", 0.0), ("root", d_root), ("leaf", 2 * d_root)):
                    U = v * um / 1000; w = 0
                    for corner, sc, sp in (("TT", 1.0, 1.0485), ("FF", ff, 1.0552)):
                        a_, b_ = ocv(U * sc, um, corner, sp); w = max(w, a_ + b_ + 20)
                    st.append(dict(edge=k, sync_at=where, unshared_ps=round(U, 1), width_ps=round(w, 1)))
            clean = P / 2 - 2 * ap
            for where in ("tap", "root", "leaf"):
                r_ = [x for x in st if x["sync_at"] == where]
                o[f"start_sync_{where}"] = dict(edges=len(r_), max_unshared_ps=max(x["unshared_ps"] for x in r_),
                                                max_width_ps=max(x["width_ps"] for x in r_), clean_bound_ps=round(clean, 1),
                                                clean=sum(x["width_ps"] <= clean for x in r_))
            o["feed_root"] = S["feed"]["root"]; o["feed_parent"] = S["feed"]["parent"]
        out[feed] = o
        print(tn, feed, json.dumps({k: v_ for k, v_ in o.items() if k not in ("per_crossing", "feed_parent")}), flush=True)
    res["types"][tn] = out
json.dump(res, open(outp, "w"), indent=1)
