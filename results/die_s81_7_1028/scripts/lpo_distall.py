# DIE-S81-7 diagnostic copy of main tools/s81_head/landed_phase_ocv.py with dist = dist_allcells
#!/usr/bin/env python3
"""LAND-HEAD-2: landed (mesochronous) crossing phase margin INCLUDING clock OCV on the unshared tree portion.

    landed_phase_ocv.py PLAN RUN_DIR [--budget-ps 416.5] [--core-lat TT=250,FF=202.5] [--out JSON]

Shared die timing model (METHODOLOGY 12.4a b1, main tools/die_plan/clk_aocv.py + the APPROVED 0.21 %/mm table that
die_sta_related.py uses): per crossing (src entry a, dst entry b, nominal d = arr_b - arr_a on the GRT-RC routed die
clock, out_<C>/arr_<C>.txt late arrivals), the branches below the LAST COMMON tree cell (LCA of the two entries'
buffer/repeater chains in clk/tree.json) are derated with clk_aocv.branch_pessimism exactly as die_sta_related.clock_ocv_fn
builds them: branch delay = entry arrival - LCA cell output arrival (+ declared partition-internal latency as class-B
stages), cell share from the table (class A), A stages = cells below the LCA on the path, distance = bounding-box
diagonal of the two entries + the LCA cell.  Droop (shared rule): the two entries are in DIFFERENT clock regions, so the
full one-sided +5.1 % late is charged on the late branch ('regions', GATE); 'same' (0) is reported as info.
Derated |d| = max(|d + p(b late, a early)|, |d - p(a late, b early)|); margin = budget - derated |d|.
"""
import argparse
import json
import math
import sys
from pathlib import Path


def arrivals(f):
    T, N = {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if not x:
            continue
        if x[0] == "T":
            T[x[1]] = float(x[2])
        elif x[0] == "N":
            N[x[1]] = float(x[2])
    return T, N


def chain(tree, cell):
    out = [cell]
    while cell in tree["parent_of"]:
        cell = tree["parent_of"][cell]
        out.append(cell)
    return out  # leaf ... root


def lca(ca, cb):
    sb = set(cb)
    for i, c in enumerate(ca):
        if c in sb:
            return c, i, cb.index(c)
    raise ValueError("no common cell")


def analyse(plan, tree, arr, CA, T, corner, core_lat, budget, droop):
    tap_of = {t["part"]: t for t in tree["taps"]}
    Tarr, Narr = arr
    B = T["classes"]["B"][corner]
    fc = T["classes"]["A"][corner]["cell_share"]
    nB = max(1, round(core_lat / B["mu_stage_ps"])) if core_lat > 0 else 0
    rows = []
    for pr in plan["ports"]:
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s not in tap_of or d not in tap_of:
            continue
        ta, tb = tap_of[s], tap_of[d]
        la, lb = tree["node_buf"][str(ta["node"])], tree["node_buf"][str(tb["node"])]
        ca, cb = chain(tree, la), chain(tree, lb)
        node, ia, ib = lca(ca, cb)
        nxy = tree["sites"][node]
        pts = [ta["xy"], tb["xy"], nxy]
        dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        cells = [tree["sites"][c] for c in ca[:ia] + cb[:ib]] + pts
        dist_all = math.hypot(max(p[0] for p in cells) - min(p[0] for p in cells), max(p[1] for p in cells) - min(p[1] for p in cells))
        dist = dist_all   # DIE-S81-7 sensitivity: AOCV distance over ALL clock cells of both branches (clk_aocv doc)
        aa, ab = Tarr[ta["port"]], Tarr[tb["port"]]
        nd = Narr[node]

        def br(arrv, nst):
            u = arrv - nd
            stg = {"A": nst}
            if nB:
                stg["B"] = nB
            return dict(cell_ps=fc * u + B["cell_share"] * core_lat, net_ps=(1 - fc) * u + (1 - B["cell_share"]) * core_lat,
                        stages=stg, unshared_ps=u)
        bra, brb = br(aa, ia), br(ab, ib)
        same = droop == "same"
        p_up = CA.branch_pessimism(T, corner, brb, bra, dist, same, "setup")   # b late, a early: d grows
        p_dn = CA.branch_pessimism(T, corner, bra, brb, dist, same, "setup")   # a late, b early: d shrinks
        dn = ab - aa
        der = max(abs(dn + p_up), abs(dn - p_dn))
        rows.append(dict(port=pr["id"], src=s, dst=d, lca=node, d_ps=round(dn, 2), unshared_a_ps=round(bra["unshared_ps"], 1),
                         unshared_b_ps=round(brb["unshared_ps"], 1), stages_a=ia, stages_b=ib, dist_um=round(dist, 1),
                         dist_allcells_um=round(dist_all, 1), p_up_ps=round(p_up, 2), p_dn_ps=round(p_dn, 2),
                         derated_abs_ps=round(der, 2), margin_ps=round(budget - der, 2)))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("run")
    ap.add_argument("--tools", required=True, help="dir holding main clk_aocv.py + clk_aocv_table_g021.json")
    ap.add_argument("--budget-ps", type=float, default=833.0 / 2)
    ap.add_argument("--core-lat", default="TT=250,FF=202.5", help="partition-internal latency per corner (12.3), class B")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tools)
    import clk_aocv as CA
    T = CA.load(Path(a.tools) / "clk_aocv_table_g021.json")
    assert abs(T["systematic"]["g_per_mm"] - 0.21) < 1e-9 or abs(T["systematic"]["g_per_mm"] - 0.0021) < 1e-9, T["systematic"]
    plan = json.loads(Path(a.plan).read_text())
    run = Path(a.run)
    tree = json.loads((run / "clk" / "tree.json").read_text())
    cl = dict(kv.split("=") for kv in a.core_lat.split(","))
    out = dict(method=__doc__.split("\n\n")[2].strip(), budget_ps=a.budget_ps, g_per_mm=T["systematic"]["g_per_mm"],
               droop_one_sided=T["droop"]["one_sided_late_frac"], core_lat=cl, corners={})
    for c in ("TT", "FF"):
        f = run / f"out_{c}" / f"arr_{c}.txt"
        if not f.is_file():
            continue
        arr = arrivals(f)
        for droop in ("regions", "same"):
            for clat in (float(cl[c]), 0.0):
                rows = analyse(plan, tree, arr, CA, T, c, clat, a.budget_ps, droop)
                rows.sort(key=lambda r: r["margin_ps"])
                key = f"{c}_droop-{droop}_corelat{clat:g}"
                out["corners"][key] = dict(crossings=len(rows), worst_margin_ps=rows[0]["margin_ps"],
                                           nominal_worst_abs_d_ps=max(abs(r["d_ps"]) for r in rows),
                                           under_100=sum(1 for r in rows if r["margin_ps"] < 100),
                                           under_0=sum(1 for r in rows if r["margin_ps"] < 0),
                                           max_unshared_ps=max(max(r["unshared_a_ps"], r["unshared_b_ps"]) for r in rows),
                                           lca_root_crossings=sum(1 for r in rows if r["lca"] == "b0"),
                                           worst=rows[:8], all=rows if (droop == "regions" and clat) else None)
                print(key, json.dumps({k: v for k, v in out["corners"][key].items() if k not in ("worst", "all")}))
    if a.out:
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
