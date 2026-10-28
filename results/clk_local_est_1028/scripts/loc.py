#!/usr/bin/env python3
"""CLK-LOCAL-EST-1 local-form estimate on a die's CURRENT region map (bind parts -> region), reusing
tools/die_plan/locality.py (score + cap_reading = count_align_plan unchanged; clk_aocv g021 + one-sided droop between
regions + core latency class B, wander 5 %).  usage: loc.py REPO PLAN BIND V_TT OUTDIR FEEDS [--map JSON]"""
import json, sys, collections, math
from pathlib import Path
repo, planp, bindp, v, outd, feeds = sys.argv[1:7]
mapj = sys.argv[7] if len(sys.argv) > 7 else None
v = float(v); outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, f"{repo}/tools/die_plan")
import importlib.util, types
_p = f"{repo}/tools/die_plan/locality.py"; _s = open(_p).read()
_old = '                x["margin_lo_ps"] = round(x["L_lo_ps"] - 0.5 * period, 1)\n'
assert _old in _s
_s = _s.replace(_old, '                if "L_lo_ps" not in x:\n                    x.update(L_lo_ps=None, L_hi_ps=None, margin_lo_ps=None, margin_hi_ps=None, depth=None, lat_cycles=x.get("lat_cycles"), kind=x.get("kind", "FAIL"), path_ambiguous_cycles=x.get("path_ambiguous_cycles", -1))\n                    res[x["port"]] = x\n                    continue\n' + _old)
L = types.ModuleType("locality"); L.__file__ = _p; sys.modules["locality"] = L; exec(compile(_s, _p, "exec"), L.__dict__)
D = L.load_plan(planp)
if mapj:
    reg = L.load_regions(mapj, D)
else:
    bind = json.loads(Path(bindp).read_text())
    reg = {p: x["region"] for p, x in bind["parts"].items() if isinstance(x, dict) and x.get("region")}
miss = [p for p in D["parts"] if p not in reg]
for p in miss: reg[p] = p   # partitions the bind does not list keep their own region
padj = L.part_adjacency(D); M = L.traffic(D); Tt = L.CA.load(L.TABLE); P = D["period"]
summ = {}
for feed in feeds.split(","):
    S = L.score(D, reg, v, feed, padj, M, Tt)
    R = S["crossings"]
    cs = L.cap_reading(R, P)
    ap = P / 8
    for r in R:
        r["d16_ok"] = (r["depth"] is not None) or (r["L_hi"] is not None and r["L_hi"] <= 15.5 * P - ap)
        r["m_hi16"] = round(15.5 * P - ap - r["L_hi"] + ap, 1) if r["L_hi"] is not None else None
    s = S["summary"]
    regs = {g["region"]: g for g in S["regions"]}
    F = S["feed"]
    # forwarded chain: root -> farthest region (hops, root arrival)
    Tr, _ = L.arrivals(S["G"], S["F"], v)
    depth_hops = {r: len(L.lineage(S["F"], r)) - 1 for r in F["parent"]}
    far = max(Tr, key=lambda r: Tr[r] + L.ins(S["G"][r], v))
    out = dict(feed=feed, v_ps_mm=v, regions=s["regions"], crossings=len(R), off_feed=s["off_feed_ports"],
               worst_unshared_tt=s["worst_unshared_tt"], worst_unshared_on=s["worst_unshared_on_feed_tt"],
               worst_unshared_off=s["worst_unshared_off_feed_tt"], max_tree_hops=s["max_tree_hops"],
               max_ins_ps=round(s["max_ins_ps"], 1), max_span_mm=s["max_span_mm"], root=F["root"],
               chain_max_hops=max(depth_hops.values()), chain_max_arrival_ps=round(Tr[far] + L.ins(S["G"][far], v), 1),
               chain_far_region=far, cap=cs, d16_fail=sum(1 for r in R if not r["d16_ok"]),
               below100=sum(1 for r in R if r["depth"] is None or min(r["m_lo"], r["m_hi"]) < 100), fail_rows=[dict(id=r["id"], ra=r["ra"], rb=r["rb"], un=round(r["ua_tt"]+r["ub_tt"]), on=r["on_feed"], kind=r.get("K_kind"), amb=r.get("amb")) for r in R if r["depth"] is None][:20],
               max_p_tt=max(r["p_tt"] for r in R), max_p_ff=max(r["p_ff"] for r in R),
               tracks_over_1=s["tracks_over_1"], tracks_worst_ratio=s["tracks_worst_ratio"])
    summ[feed] = out
    print(json.dumps({k: out[k] for k in out if k != "cap"}), {k: cs[k] for k in ("depth4", "depth8", "fail", "worst_margin_lo_ps", "worst_margin_hi_ps", "max_phys")}, flush=True)
    rows = [dict(id=r["id"], ra=r["ra"], rb=r["rb"], width=r["width"], on_feed=r["on_feed"], tree_hops=r["tree_hops"],
                 lca=r["lca"], ua=r["ua_tt"], ub=r["ub_tt"], unshared=round(r["ua_tt"] + r["ub_tt"], 1), dist_um=r["dist_um"],
                 p_tt=r["p_tt"], p_ff=r["p_ff"], depth=r["depth"], kind=r["K_kind"], amb=r["amb"], L_lo=r["L_lo"],
                 L_hi=r["L_hi"], m_lo=r["m_lo"], m_hi=r["m_hi"], d16_ok=r["d16_ok"], lat=r["lat"], phys=r["phys"])
            for r in R]
    (outd / f"loc_{feed}.json").write_text(json.dumps(dict(summary=out, feed=F, regions=S["regions"], rows=rows), default=str))
(outd / "loc_summary.json").write_text(json.dumps(summ, indent=1, default=str))
