#!/usr/bin/env python3
"""LAND-HEAD-3: quick per-crossing PRE-BUILD model of a die clock topology for the landed (mesochronous) form.

    landed_topo_model.py PLAN KIT_CLOCK_DIR OUT_DIR --tools MAIN_TOOLS [--calib RUN_DIR]

Estimates every tree-cell and tap arrival of KIT_CLOCK_DIR/tree.json (any topology die_trial.py kit writes) from a stage
model fitted by least squares on a MEASURED GRT-RC routed die clock (--calib RUN_DIR with clk/tree.json + out_<C>/arr_<C>.txt,
default LAND-HEAD-1 sl300):  cell delay = a + b1*L + b2*L^2 + f*(fanout(parent)-1)  (L = Manhattan leg to the parent cell),
tap leg = c0 + c1*L + c2*L^2.  It writes OUT_DIR/clk/tree.json + out_<C>/arr_<C>.txt in the native arrival format and runs
the shared landed_phase_ocv.analyse (main clk_aocv + APPROVED g021 table, branch below the last common cell, 12.3 core latency
as class B, one-sided droop on different regions) on them.  MODEL numbers only (UNCHECKED by construction); the gate number
is landed_phase_ocv on the routed die GRT arrivals."""
import argparse
import collections
import json
import shutil
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import landed_phase_ocv as LPO  # noqa: E402


def _kids(tree):
    return collections.Counter(tree["parent_of"].values())


def _L(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def fit(run, corner):
    tree = json.loads((Path(run) / "clk" / "tree.json").read_text())
    T, N = LPO.arrivals(Path(run) / f"out_{corner}" / f"arr_{corner}.txt")
    S, par, kids = tree["sites"], tree["parent_of"], _kids(tree)
    X, Y = [], []
    for c, p in par.items():
        if c in N and p in N:
            L = _L(S[c], S[p])
            X.append([1, L, L * L, kids[p] - 1])
            Y.append(N[c] - N[p])
    X, Y = np.array(X), np.array(Y)
    cs = np.linalg.lstsq(X, Y, rcond=None)[0]
    Z, W = [], []
    for t in tree["taps"]:
        c = tree["node_buf"][str(t["node"])]
        L = _L(t["xy"], S[c])
        Z.append([1, L, L * L])
        W.append(T[t["port"]] - N[c])
    Z, W = np.array(Z), np.array(W)
    ct = np.linalg.lstsq(Z, W, rcond=None)[0]
    root = N[tree["node_buf"]["0"]]
    return dict(cell=cs.tolist(), tap=ct.tolist(), root_ps=root, rms_cell_ps=float((Y - X @ cs).std()),
                rms_tap_ps=float((W - Z @ ct).std()))


def estimate(tree, m):
    S, par, kids = tree["sites"], tree["parent_of"], _kids(tree)
    N = {}
    root = tree["node_buf"]["0"]

    def arr(c):
        if c in N:
            return N[c]
        stack = [c]
        while stack[-1] in par and par[stack[-1]] not in N:
            stack.append(par[stack[-1]])
        for x in reversed(stack):
            if x not in par:
                N[x] = m["root_ps"]
            else:
                p = par[x]
                L = _L(S[x], S[p])
                a, b1, b2, f = m["cell"]
                N[x] = N[p] + a + b1 * L + b2 * L * L + f * (kids[p] - 1)
        return N[c]
    for c in S:
        arr(c)
    assert root in N
    T = {}
    for t in tree["taps"]:
        c = tree["node_buf"][str(t["node"])]
        L = _L(t["xy"], S[c])
        c0, c1, c2 = m["tap"]
        T[t["port"]] = N[c] + c0 + c1 * L + c2 * L * L
    return T, N


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("clock_dir", help="die_trial kit clock/ dir holding tree.json")
    ap.add_argument("out")
    ap.add_argument("--tools", required=True)
    ap.add_argument("--calib", default="/srv/opentallas-scratch2/claude/land-head-1/sl300")
    ap.add_argument("--budget-ps", type=float, default=833.0 / 2)
    a = ap.parse_args(argv)
    sys.path.insert(0, a.tools)
    import clk_aocv as CA
    Tb = CA.load(Path(a.tools) / "clk_aocv_table_g021.json")
    plan = json.loads(Path(a.plan).read_text())
    tree = json.loads((Path(a.clock_dir) / "tree.json").read_text())
    out = Path(a.out)
    (out / "clk").mkdir(parents=True, exist_ok=True)
    shutil.copy(Path(a.clock_dir) / "tree.json", out / "clk" / "tree.json")
    res = dict(method=__doc__.split("\n\n")[2].strip(), calib=a.calib, corners={})
    for c, clat in (("TT", 250.0), ("FF", 202.5)):
        m = fit(a.calib, c)
        T, N = estimate(tree, m)
        d = out / f"out_{c}"
        d.mkdir(exist_ok=True)
        (d / f"arr_{c}.txt").write_text("".join(f"T {k} {v:.3f}\n" for k, v in T.items()) +
                                        "".join(f"N {k} {v:.3f}\n" for k, v in N.items()))
        rows = LPO.analyse(plan, tree, (T, N), CA, Tb, c, clat, a.budget_ps, "regions")
        rows.sort(key=lambda r: r["margin_ps"])
        res["corners"][c] = dict(fit=m, insertion_max_ps=round(max(T.values()), 1), insertion_min_ps=round(min(T.values()), 1),
                                 crossings=len(rows), worst_margin_ps=rows[0]["margin_ps"],
                                 under_100=sum(r["margin_ps"] < 100 for r in rows), under_0=sum(r["margin_ps"] < 0 for r in rows),
                                 max_abs_d_ps=max(abs(r["d_ps"]) for r in rows),
                                 max_unshared_ps=max(max(r["unshared_a_ps"], r["unshared_b_ps"]) for r in rows), worst=rows[:6])
        print(c, json.dumps({k: v for k, v in res["corners"][c].items() if k not in ("worst", "fit")}))
        for r in rows[:4]:
            print("  ", r["port"], r["src"], r["dst"], "d", r["d_ps"], "uns", r["unshared_a_ps"], r["unshared_b_ps"], "margin", r["margin_ps"])
    (out / "model.json").write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
