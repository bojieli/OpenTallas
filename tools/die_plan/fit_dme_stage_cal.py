#!/usr/bin/env python3
"""Fit the region-DME stage model (die_trial --region-dme-stage-cal FILE) on the ROUTED legs of a built region tree.

DIE-S81-18 (COORD 10-28 21:33 rule 1: the region tree builder must be calibrated on routed legs of its own cell/layer
stack).  DIE-S81-17 found the S81 go15 inv2 tree priced with the BUFx24 1x ladder fit (die_trial STAGE_1X_TT, wire
0.014 ps/um) while the routed inv2 legs cost 0.162 ps/um; the DME then balanced long legs against stacked short ones.
This tool turns that one-off estimate into the shared, repeatable fit:

  per DME leg (tree.json node with dme and a parent): measured = early arrival(child node buffer) - early
  arrival(parent node buffer) from the routed readout arr_<C>.txt (N rows: name late early ...);
  regressors = [n stages, sum L, sum L^2 over stages, end-node fanout - 1], the same form as die_trial leg_ps /
  chain_ps / snake legs + DME_FANOUT_PS at merge nodes (n, L as die_trial places them: snake legs one stage per
  waypoint pair; plain legs ceil(L / rep_um) equal stages, even if --even-legs).
  Least squares, no intercept -> leg [d0, k1, k2, kf] per corner, per-leg rms of the fit and of the model the tree was
  built with (--built-with: the default uncalibrated STAGE_1X_TT or a previous cal file).

The tap leg [k1, k2] is NOT fitted here (tap legs are often ~0 um, e.g. S81 go15): it is copied from --tap-from (a cal
file) or --tap K1 K2, and the output records which.  Output = a load_stage_cal-compatible JSON ("leg", "tap" = TT;
"leg_FF", "tap_FF" informational) + fit statistics.  Read-only on its inputs; no gate, no default change.

usage: fit_dme_stage_cal.py --tree KIT/clock/tree.json --arr-prefix RUN/out (reads RUN/out_TT/arr_TT.txt ...)
                            --tap-from OLD.json | --tap K1 K2 [--rep-um 250] [--even-legs] [--built-with CAL] -o OUT
"""
import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D  # noqa: E402


def read_node_early(path):
    """{node buffer name: early arrival ps} from an OT_EDGES readout (N rows: N name late early slew)"""
    out = {}
    for line in open(path):
        p = line.split()
        if len(p) >= 4 and p[0] == "N":
            out[p[1]] = float(p[3])
    return out


def leg_rows(tree, arr, rep_um=250.0, even_legs=True, placed_stages=False):
    """[(node id, [n, sumL, sumL2, fanout-1], measured ps, (pts, snake))] for every DME leg with both ends read"""
    nodes = {int(k): v for k, v in tree["nodes"].items()}
    nb = {int(k): v for k, v in tree["node_buf"].items()}
    ntap = collections.Counter(t["node"] for t in tree.get("taps", []))
    rows = []
    for i, nd in sorted(nodes.items()):
        if (not placed_stages and not nd.get("dme")) or nd.get("parent") is None:
            continue
        a, b = arr.get(nb.get(i)), arr.get(nb.get(nd["parent"]))
        if a is None or b is None:
            continue
        p = nodes[nd["parent"]]
        pa, q = (p["x"], p["y"]), (nd["x"], nd["y"])
        if placed_stages:
            # The retained native stage graph is authoritative: body packing and
            # legal detours can change both count and wire from the ideal leg.
            # This explicit mode also accepts isolated region coupons without
            # die-level dme labels; it never invents missing connectivity/sites.
            child, parent = nb[i], nb[nd["parent"]]
            chain, seen = [child], {child}
            while chain[-1] != parent:
                pred = tree.get("parent_of", {}).get(chain[-1])
                if pred is None or pred in seen:
                    raise ValueError(f"placed stage leg {i}: no connected chain {child} -> {parent}")
                chain.append(pred)
                seen.add(pred)
            try:
                pts = [tree["sites"][c] for c in reversed(chain)]
            except KeyError as exc:
                raise ValueError(f"placed stage leg {i}: missing site {exc}") from exc
            segs = [D._man(u, v) for u, v in zip(pts, pts[1:])]
        elif nd.get("snake"):
            pts = [pa] + [tuple(x) for x in nd["snake"]] + [q]
            segs = [D._man(u, v) for u, v in zip(pts, pts[1:])]
        else:
            pts = [tuple(x) for x in nd["route"]] if nd.get("route") else [pa, q]
            L = sum(D._man(u, v) for u, v in zip(pts, pts[1:]))
            n = max(1, int(math.ceil(L / rep_um - 1e-9)))
            if even_legs and n % 2:
                n += 1
            segs = [L / n] * n
        fo = len(nd.get("kids") or []) + ntap.get(i, 0)
        rows.append((i, [len(segs), sum(segs), sum(s * s for s in segs), fo - 1], a - b, bool(nd.get("snake"))))
    return rows


def model_ps(x, coef):
    """leg model ps for regressors x = [n, sumL, sumL2, fo-1] and coef [d0, k1, k2, kf]"""
    return x[0] * coef[0] + x[1] * coef[1] + x[2] * coef[2] + x[3] * coef[3]


def fit(rows, built=None):
    """least-squares [d0, k1, k2, kf] + statistics; built = [d0, k1, k2, kf] the tree was planned with (rms_built)"""
    if len(rows) < 8:
        raise ValueError(f"only {len(rows)} routed DME legs with both ends read: too few to fit 4 coefficients")
    X = np.array([r[1] for r in rows], float)
    y = np.array([r[2] for r in rows], float)
    c, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ c
    out = dict(coef=[round(float(v), 6) for v in c], legs=len(rows), rms_ps=round(float(np.sqrt((res ** 2).mean())), 2),
               abs_resid_pctl_ps={q: round(float(np.percentile(np.abs(res), q)), 2) for q in (50, 90, 99)},
               max_abs_resid_ps=round(float(np.abs(res).max()), 2))
    if built is not None:
        rb = y - X @ np.array(built, float)
        out["rms_built_ps"] = round(float(np.sqrt((rb ** 2).mean())), 2)
        out["median_measured_over_built"] = round(float(np.median(y / np.maximum(X @ np.array(built, float), 1e-6))), 3)
    sn = np.array([r[3] for r in rows])
    if sn.any() and (~sn).any():
        out["rms_ps_by_kind"] = dict(snake=round(float(np.sqrt((res[sn] ** 2).mean())), 2),
                                     plain=round(float(np.sqrt((res[~sn] ** 2).mean())), 2))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--tree", required=True, help="kit clock/tree.json of the built region tree")
    ap.add_argument("--arr-prefix", required=True, help="readout prefix: <prefix>_<C>/arr_<C>.txt per corner")
    ap.add_argument("--corners", default="TT,FF")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--tap-from", help="copy tap [k1, k2] (and tap_FF) from this cal file")
    g.add_argument("--tap", nargs=2, type=float, metavar=("K1", "K2"), help="tap leg wire coefficients (TT)")
    ap.add_argument("--rep-um", type=float, default=250.0, help="repeater pitch the tree was built with")
    ap.add_argument("--even-legs", action="store_true", help="the tree used even stage counts (die_trial EVEN_LEGS)")
    ap.add_argument("--placed-stages", action="store_true",
                    help="use retained parent_of/sites stage chains for every logical region leg; accepts isolated "
                         "region coupons without dme labels, refuses disconnected chains or missing sites")
    ap.add_argument("--built-with", default=None, help="cal file the tree was built with (default: uncalibrated "
                    "STAGE_1X_TT, fanout 0) -> rms_built_ps")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    tree = json.loads(Path(a.tree).read_text())
    if a.built_with:
        bc = json.loads(Path(a.built_with).read_text())
        built = {"TT": bc["leg"], "FF": bc.get("leg_FF", bc["leg"])}
        built_lab = a.built_with
    else:
        built = {"TT": list(D.STAGE_1X_TT) + [0.0], "FF": list(D.STAGE_1X_TT) + [0.0]}
        built_lab = "die_trial STAGE_1X_TT (BUFx24 1x ladder, uncalibrated), fanout 0"
    if a.tap_from:
        tc = json.loads(Path(a.tap_from).read_text())
        tap = {"TT": tc["tap"], "FF": tc.get("tap_FF", tc["tap"])}
        tap_src = a.tap_from
    else:
        tap = {"TT": list(a.tap), "FF": list(a.tap)}
        tap_src = "--tap"
    out = dict(scope="fit_dme_stage_cal: region DME stage model fitted on routed legs; leg = n*d0 + k1*sumL + "
                     "k2*sumL^2 + kf*(end-node fanout - 1); tap copied, not fitted",
               source=dict(tree=str(a.tree), arrivals=str(a.arr_prefix), rep_um=a.rep_um, even_legs=a.even_legs,
                           built_with=built_lab, tap_from=tap_src),
               fit={})
    if a.placed_stages:
        out["source"]["placed_stages"] = True
    for c in a.corners.split(","):
        arr = read_node_early(f"{a.arr_prefix}_{c}/arr_{c}.txt")
        f = fit(leg_rows(tree, arr, a.rep_um, a.even_legs, a.placed_stages), built[c] if c in built else None)
        out["fit"][c] = f
        key = "leg" if c == "TT" else f"leg_{c}"
        out[key] = f["coef"]
        out["tap" if c == "TT" else f"tap_{c}"] = tap.get(c, tap["TT"])
        print(f"{c}: legs {f['legs']} coef d0/k1/k2/kf {f['coef']} rms {f['rms_ps']} ps "
              f"(built model {f.get('rms_built_ps')}) |resid| p50/p90/p99 {list(f['abs_resid_pctl_ps'].values())}")
    if "leg" not in out:
        raise SystemExit("TT corner required: load_stage_cal reads 'leg'/'tap' (TT)")
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    return out


if __name__ == "__main__":
    main()
