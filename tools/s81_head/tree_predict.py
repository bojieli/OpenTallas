#!/usr/bin/env python3
"""FALLBACK-HEAD die-tree predictor: per-entry insertion from tree geometry only (stage features), fitted by least
squares on measured runs (GRT-RC OpenSTA arrivals), then the landed phase offsets |d| per plan port.
    tree_predict.py fit PLAN RUN [RUN...] --out coef.json
    tree_predict.py predict PLAN CLKDIR --coef coef.json [--arr RUN]   (CLKDIR holds ctree.tcl + tree.json)"""
import argparse, json, re, sys
from collections import defaultdict
from pathlib import Path
import numpy as np


def sites(clk):
    xy = {}
    for ln in (Path(clk) / "ctree.tcl").read_text().splitlines():
        m = re.match(r"place_inst -name (\S+) -location \{([\d.]+) ([\d.]+)\}", ln)
        if m:
            xy[m.group(1)] = (float(m.group(2)), float(m.group(3)))
        m = re.match(r"place_pin -pin_name (\S+) -layer \S+ -location \{([\d.]+) ([\d.]+)\}", ln)
        if m:
            xy[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    return xy


def features(clk):
    clk = Path(clk)
    T = json.loads((clk / "tree.json").read_text())
    xy = sites(clk)
    par = dict(T["parent_of"])
    kids = defaultdict(list)
    for c, p in par.items():
        kids[p].append(c)
    leaf_of = {}
    for t in T["taps"]:
        b = T["node_buf"][str(t["node"])]
        kids[b].append(t["port"])
        par[t["port"]] = b
        xy[t["port"]] = tuple(t["xy"])
    man = lambda a, b: abs(xy[a][0] - xy[b][0]) + abs(xy[a][1] - xy[b][1])
    # net length ~ half-perimeter-ish: sum of driver->sink Manhattan (star) for the driver's net
    netlen = {d: sum(man(d, k) for k in ks) for d, ks in kids.items()}
    F = {}
    for t in T["taps"]:
        q = t["port"]; f = np.zeros(5)
        while q in par:
            d = par[q]; L = man(d, q); N = netlen[d]
            f += [1.0, N, L, N * L, len(kids[d])]
            q = d
        F[t["port"]] = (t["part"], f)
    return F


def arrivals(run, c):
    out = {}
    for ln in (Path(run) / f"out_{c}" / f"arr_{c}.txt").read_text().splitlines():
        x = ln.split()
        if x and x[0] == "T":
            out[x[1]] = float(x[2])
    return out


def ports(plan):
    return [(p["id"], p["src"]["part"], p["dst"]["part"]) for p in json.loads(Path(plan).read_text())["ports"]]


def dstats(plan, ins):
    """ins {part: insertion} -> max |d|, worst ports"""
    rows = [(abs(ins[d] - ins[s]), pid, s, d) for pid, s, d in ports(plan) if s in ins and d in ins]
    rows.sort(reverse=True)
    return dict(max_abs_d=round(rows[0][0], 2), worst=[(r[1], r[2], r[3], round(r[0], 1)) for r in rows[:5]],
                spread=round(max(ins.values()) - min(ins.values()), 1))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fit"); f.add_argument("plan"); f.add_argument("runs", nargs="+"); f.add_argument("--out", required=True)
    p = sp.add_parser("predict"); p.add_argument("plan"); p.add_argument("clk"); p.add_argument("--coef", required=True)
    p.add_argument("--arr")
    a = ap.parse_args()
    if a.cmd == "fit":
        coef = {}
        for c in ("TT", "FF"):
            X, y = [], []
            for r in a.runs:
                F = features(Path(r) / "clk"); A = arrivals(r, c)
                for port, (part, fv) in F.items():
                    X.append(fv); y.append(A[port])
            X, y = np.array(X), np.array(y)
            w, *_ = np.linalg.lstsq(X, y, rcond=None)
            res = X @ w - y
            coef[c] = dict(w=w.tolist(), rms=float(np.sqrt((res ** 2).mean())), maxres=float(abs(res).max()))
            for r in a.runs:   # per-run check of the predicted landed d against measured
                F = features(Path(r) / "clk"); A = arrivals(r, c)
                pi = {part: float(fv @ w) for port, (part, fv) in F.items()}
                mi = {part: A[port] for port, (part, fv) in F.items()}
                coef[c][r] = dict(pred=dstats(a.plan, pi), meas=dstats(a.plan, mi))
        Path(a.out).write_text(json.dumps(coef, indent=1) + "\n"); print(json.dumps(coef, indent=1))
    else:
        coef = json.loads(Path(a.coef).read_text()); F = features(a.clk); out = {}
        for c in ("TT", "FF"):
            w = np.array(coef[c]["w"])
            out[c] = dstats(a.plan, {part: float(fv @ w) for port, (part, fv) in F.items()})
        print(json.dumps(out))


if __name__ == "__main__":
    main()
