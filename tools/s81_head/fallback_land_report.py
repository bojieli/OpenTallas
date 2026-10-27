#!/usr/bin/env python3
"""FALLBACK-HEAD landed-seam clock report on a routed die clock (FB1: one region-root entry per partition).

    fallback_land_report.py PLAN RUN_DIR [--budget-ps 416.5]

RUN_DIR holds out_{TT,FF}/arr_<C>.txt (native OpenSTA arrivals on the GRT RC of the die clock routed in the combined
die global_route, mk_combo_dcm.py recipe) and clk/tree.json.  Under the fallback every partition is its own clock
region, so there is NO die-level related pair: each plan port is a LANDED crossing (ot_dp_clk_landing, forwarded clock,
+3 fixed cycles).  The die clock then only has to keep, per landed crossing, the region-root phase offset
    d = arrival(dst entry) - arrival(src entry)
inside the landing window |d| <= budget (default P/2 = 416.5 ps, die_clock_mesh report --landing-budget-ps) at TT AND
FF, and the TT->FF drift |d_TT - d_FF| small, so the ring alignment (fixed static latency) is corner independent.
Partition-internal trees (entry -> sinks, hard-core pins included) are each partition's own sign-off.
Writes RUN_DIR/landed_report.json.  Numbers are UNCHECKED until NUMBER-CHECK recomputes them.
"""
import argparse
import json
import math
from pathlib import Path


def arrivals(f):
    late, early, slew = {}, {}, {}
    for ln in Path(f).read_text().splitlines():
        x = ln.split()
        if x and x[0] == "T":
            late[x[1]], early[x[1]] = float(x[2]), float(x[3])
            slew[x[1]] = float(x[4]) if len(x) > 4 else float("nan")
    return late, early, slew


def render(plan, run, tree, A, rows, budget, png):
    import re
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    T = plan["partition_types"]
    W, H = (v / 1000 for v in plan["die"]["outline_um"])
    fig, ax = plt.subplots(figsize=(11, 11))
    col = {"hd_tile": "#dfe8f5", "hd_serdes": "#f3dede", "hd_spn": "#e3f1df", "hd_spn_end": "#e3f1df"}
    for p in plan["partitions"]:
        w, h = T[p["type"]]["outline_um"]
        ax.add_patch(Rectangle((p["origin_um"][0] / 1000, p["origin_um"][1] / 1000), w / 1000, h / 1000,
                               fc=col.get(p["type"], "#efefef"), ec="#888", lw=0.3))
    xy = {}
    for ln in (run / "clk" / "ctree.tcl").read_text().splitlines():
        m = re.match(r"place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}", ln)
        if m:
            xy[m.group(1)] = (float(m.group(2)) / 1000, float(m.group(3)) / 1000)
    for c, par in tree["parent_of"].items():
        if c in xy and par in xy:
            ax.plot([xy[c][0], xy[par][0]], [xy[c][1], xy[par][1]], color="#555", lw=0.35)
    late, _, slew = A["TT"]
    tp = {t["part"]: t for t in tree["taps"]}
    for t in tree["taps"]:
        lf = tree["node_buf"][str(t["node"])]
        if lf in xy:
            ax.plot([xy[lf][0], t["xy"][0] / 1000], [xy[lf][1], t["xy"][1] / 1000], color="#999", lw=0.35, ls=":")
    xs = [t["xy"][0] / 1000 for t in tree["taps"]]
    ys = [t["xy"][1] / 1000 for t in tree["taps"]]
    cs = [late.get(t["port"], float("nan")) for t in tree["taps"]]
    sc = ax.scatter(xs, ys, c=cs, s=14, cmap="plasma", zorder=3)
    fig.colorbar(sc, ax=ax, fraction=0.025, label="TT entry arrival (ps)")
    hi = [t for t in tree["taps"] if slew.get(t["port"], 0) > 320]
    ax.scatter([t["xy"][0] / 1000 for t in hi], [t["xy"][1] / 1000 for t in hi], s=60, facecolors="none",
               edgecolors="k", lw=0.8, zorder=4)
    for r in rows:
        if abs(r.get("d_TT", 0)) > budget or abs(r.get("d_FF", 0)) > budget:
            a, b = tp[r["src"]]["xy"], tp[r["dst"]]["xy"]
            ax.plot([a[0] / 1000, b[0] / 1000], [a[1] / 1000, b[1] / 1000], color="red", lw=2.0, zorder=5)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    m = tree["meta"]
    ax.set_title(f"s81_head FB1 landed fallback: {len(plan['partitions'])} regions = partitions, {m['taps']} entries, "
                 f"{m['repeaters']} reps, leaf {m['leaf_um']:g} um; red = landed crossing |d| > {budget:g} ps; "
                 f"ring = entry slew > 320 ps  [mm]", fontsize=8)
    fig.tight_layout(); fig.savefig(png, dpi=130); plt.close(fig)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("run")
    ap.add_argument("--budget-ps", type=float, default=833.0 / 2)
    ap.add_argument("--png", help="render: partitions (= regions), routed-tree cells/edges, entries by TT arrival, "
                                  "landed crossings over budget (red), entries with slew > 320 ps (black ring)")
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text())
    run = Path(a.run)
    tree = json.loads((run / "clk" / "tree.json").read_text())
    tap_of = {}
    for t in tree["taps"]:
        tap_of.setdefault(t["part"], []).append(t["port"])
    multi = {p: v for p, v in tap_of.items() if len(v) != 1}
    if multi:
        raise SystemExit(f"FB1 expects one entry per partition; {len(multi)} parts differ, e.g. {list(multi.items())[:3]}")
    A = {c: arrivals(run / f"out_{c}" / f"arr_{c}.txt") for c in ("TT", "FF") if (run / f"out_{c}" / f"arr_{c}.txt").is_file()}
    rows = []
    for pr in plan["ports"]:
        s, d = pr["src"]["part"], pr["dst"]["part"]
        if s not in tap_of or d not in tap_of:
            continue
        ts, td = tap_of[s][0], tap_of[d][0]
        r = dict(port=pr["id"], src=s, dst=d, width=int(pr["width"]))
        for c, (late, early, _) in A.items():
            r[f"d_{c}"] = round(late[td] - late[ts], 2)
        if "TT" in A and "FF" in A:
            r["drift_ps"] = round(abs(r["d_TT"] - r["d_FF"]), 2)
        rows.append(r)
    out = dict(method="FB1 one entry per partition; every plan port landed; phase offset of region roots on the GRT-RC "
                      "routed die clock (combined die global_route, signals M4-M7 + clock M8-M9, 50 congestion it)",
               budget_ps=a.budget_ps, tree_meta=tree["meta"], crossings=len(rows), corners={})
    for c, (late, early, slew) in A.items():
        ins = sorted(late.values())
        dv = [abs(r[f"d_{c}"]) for r in rows]
        sl = [v for v in slew.values() if not math.isnan(v)]
        out["corners"][c] = dict(entries=len(ins), insertion_min_ps=round(ins[0], 1), insertion_max_ps=round(ins[-1], 1),
                                 insertion_spread_ps=round(ins[-1] - ins[0], 1),
                                 entry_slew_max_ps=round(max(sl), 1) if sl else None,
                                 entry_slew_over_320=sum(1 for v in sl if v > 320),
                                 landed_phase_max_abs_ps=round(max(dv), 2),
                                 landed_over_budget=sum(1 for v in dv if v > a.budget_ps),
                                 landed_margin_ps=round(a.budget_ps - max(dv), 2),
                                 worst=sorted(rows, key=lambda r: -abs(r[f"d_{c}"]))[:6])
    if "TT" in A and "FF" in A:
        out["drift_max_ps"] = max(r["drift_ps"] for r in rows)
        ok = all(out["corners"][c]["landed_over_budget"] == 0 for c in ("TT", "FF"))
        out["verdict"] = dict(landing_window="PASS" if ok else "FAIL",
                              scope="die clock landing window only; NOT the 12.4a freeze gate (needs partition views "
                                    "with landing rings, ring-window STA, real-view die STA)")
    if a.png:
        render(plan, run, tree, A, rows, a.budget_ps, a.png)
    (run / "landed_report.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: (v if k != "corners" else {c: {x: y for x, y in cv.items() if x != "worst"} for c, cv in v.items()})
                      for k, v in out.items() if k != "tree_meta"}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
