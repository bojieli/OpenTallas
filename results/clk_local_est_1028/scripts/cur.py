#!/usr/bin/env python3
"""CLK-LOCAL-EST-1 (estimate-only): CURRENT clock topology per crossing on a die's gate inputs, with the CA-OCV-1
die_sta_related model (spice, region key, cppr-lca when tree_path, table/shared droop).  Per crossing: last common
node, launch/capture unshared branch (late, nominal), distance, OCV lo/hi, gate margins, and the best K-replan margin
at DEPTH 8 / 16 (K common to TT+FF).  usage: cur.py TOOLS PROOF PLAN BIND OUT.json"""
import json, sys, math, collections
from pathlib import Path
tools, proof, planp, bindp, out = sys.argv[1:6]
sys.path.insert(0, tools)
import die_sta_related as D
proof = Path(proof); plan = json.loads(Path(planp).read_text()); bind = json.loads(Path(bindp).read_text())
dr = str(proof / "droop_regions.json") if (proof / "droop_regions.json").exists() else None
lat_tt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
T = D.PERIOD_PS
pr = {p: v["region"] for p, v in (bind.get("parts") or {}).items() if isinstance(v, dict) and v.get("region")}
res = dict(proof=str(proof), plan=planp, bind=bindp, corners={})
rows_by = {}
for c in ("TT", "FF"):
    meta, taps = D.load_taps(proof, c)
    D.CPPR_LCA = all("tree_path" in t for t in taps.values())
    meta, taps = D.scale_clock(meta, taps, D.SPICE_CLOCK_CAL[c])
    pairs, _ = D.build_pairs(plan, taps)
    lat = lat_tt if c == "TT" else 202.5
    ocv = D.ca_ocv(proof, meta, taps, c, lat, "table", "shared", "mesh", dr)
    A = D.count_align_landed(pairs["landed"], taps, bind, T, None, need_ps=100.0,
                             cppr_range=meta["cppr_node_range_ps"], key="region", ocv=ocv, ocv_label="table/shared")
    nl = meta["node_late_ps"]; nst = meta["node_stages"]; nxy = meta["node_xy_um"]
    st = {}
    reg_ins = collections.defaultdict(list)
    for a, b, tag in pairs["landed"]:
        X, Y = taps[a], taps[b]
        tg = f"{pr[X['part']]}->{pr[Y['part']]}"
        node = D.pair_node(X, Y)
        la = X.get("abs_late_ps", X["late_ps"]) if node == "h" else X["late_ps"]
        lb = Y.get("abs_late_ps", Y["late_ps"]) if node == "h" else Y["late_ps"]
        ua, ub = la - float(nl[node]), lb - float(nl[node])
        pts = [X["xy_um"], Y["xy_um"]] + ([nxy[node]] if nxy.get(node) else [])
        dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        sep = math.dist(X["xy_um"], Y["xy_um"])
        s = st.setdefault(tg, dict(un=0, ua=0, ub=0, node=node, depth=len(node), dist=0, sep=0, npairs=0,
                                   abs_a=0, abs_b=0))
        s["npairs"] += 1
        if ua + ub > s["un"]:
            s.update(un=ua + ub, ua=ua, ub=ub, node=node, depth=len(node), stA=X["stages_from_root"] - nst[node],
                     stB=Y["stages_from_root"] - nst[node])
        s["dist"] = max(s["dist"], dist); s["sep"] = max(s["sep"], sep)
        s["abs_a"] = max(s["abs_a"], X.get("abs_late_ps", X["late_ps"])); s["abs_b"] = max(s["abs_b"], Y.get("abs_late_ps", Y["late_ps"]))
    # region insertion: tap abs arrival per region (max/min), the die root insertion of region trees
    for p, t in taps.items():
        r = pr.get(t["part"])
        if r: reg_ins[r].append(t.get("abs_late_ps", t["late_ps"]))
    rows = {r["port"]: r for r in A["rows"]}
    dsta = D.count_align_d_intervals(pairs["landed"], taps, meta["cppr_node_range_ps"], part_region=pr, ocv=ocv)
    dsta0 = D.count_align_d_intervals(pairs["landed"], taps, meta["cppr_node_range_ps"], part_region=pr, ocv=None)
    res.setdefault("dsta", {})[c] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in dsta.items()}
    res.setdefault("dsta0", {})[c] = {k: [round(v[0], 1), round(v[1], 1)] for k, v in dsta0.items()}
    res["corners"][c] = dict(cppr_lca=D.CPPR_LCA, crossings=A["crossings"], below=A["below_need"],
                             worst_lo=A["worst_lo"]["margin_lo_ps"], worst_hi=A["worst_hi"]["margin_hi_ps"],
                             ocv_max=A["ocv_max_lo_ps"],
                             region_ins={r: [round(min(v), 1), round(max(v), 1)] for r, v in reg_ins.items()})
    rows_by[c] = (rows, st)
out_rows = []
for pid, b in sorted(bind["ports"].items()):
    tag = f"{b['src']}->{b['dst']}"
    R = {}
    for c in ("TT", "FF"):
        rows, st = rows_by[c]
        r = rows.get(pid); s = st.get(tag)
        if r is None or s is None: continue
        R[c] = dict(ml=r["margin_lo_ps"], mh=r["margin_hi_ps"], ocv_lo=r.get("ocv_lo_ps"), ocv_hi=r.get("ocv_hi_ps"),
                    un=round(s["un"], 1), ua=round(s["ua"], 1), ub=round(s["ub"], 1), node=s["node"], depth=s["depth"],
                    stA=s.get("stA"), stB=s.get("stB"), dist_mm=round(s["dist"] / 1000, 3), sep_mm=round(s["sep"] / 1000, 3),
                    src=r["source"], npairs=s["npairs"])
    if not R: continue
    D0 = int(b["depth"])
    ml = min(R[c]["ml"] for c in R); mh = min(R[c]["mh"] for c in R)
    best = {}
    for Dn in (8, 16):
        h = mh + (Dn - D0) * T
        # integer K shift k: lo ml + kT, hi h - kT
        k = math.floor((h - ml) / (2 * T))
        best[Dn] = round(max(min(ml + kk * T, h - kk * T) for kk in (k, k + 1)), 1)
    span = (D0 - 1) * T - ml - mh  # union lag width (ps) incl OCV + wander
    out_rows.append(dict(port=pid, tag=tag, depth=D0, tree=bool(b.get("tree")), wander=b.get("wander_ps"),
                         span_ps=round(span, 1), best8=best[8], best16=best[16], **{c: R[c] for c in R}))
res["rows"] = out_rows
Path(out).write_text(json.dumps(res, indent=0))
for c in res["corners"]:
    x = res["corners"][c]; print(c, {k: x[k] for k in ("cppr_lca", "crossings", "below", "worst_lo", "worst_hi", "ocv_max")})
