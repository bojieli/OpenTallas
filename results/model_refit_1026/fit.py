#!/usr/bin/env python3
"""MODEL-REFIT: candidate core-insertion model forms on points.json; residual max/rms + leave-one-out (LOO)."""
import json, math
from pathlib import Path
import numpy as np

T = Path(__file__).resolve().parent
P = json.loads((T / "points.json").read_text())
EXCL = {("HBM", "side_rest"): "invalid oversized outline (lane)", ("QC", "R3"): "broken equal-load assignment, raw log missing"}


def excluded(p):
    if p["die"] == "HBM" and p["core"] == "side_rest":
        return True
    if p["trial"].startswith("R3"):
        return True
    return False


K_MAIN, RCX = 0.8963, 0.9429   # current master_plan.py: TT = RCX*K*L


def design(pts, form):
    X = []
    for p in pts:
        L = p["L"]; pl = 1.0 if p["basis"] == "PL" else 0.0
        if form == "K*L+c":
            X.append([1.0])
        elif form == "a+bL":
            X.append([1.0, L])
        elif form == "a+bL+PL":
            X.append([1.0, L, pl])
        elif form == "a+bL+PL+struct":
            X.append([1.0, L, pl, p["struct"] == "rt", p["struct"] in ("trunk",), p["struct"] == "plan"])
        elif form == "a+bL+PL+log2N":
            X.append([1.0, L, pl, math.log2(p["sinks"] or 5000)])
    return np.array(X, float)


def target(p, key, form):
    y = p[key]
    if form == "K*L+c":
        y = y - RCX * K_MAIN * p["L"]
    return y


def fit(pts, key, form):
    pts = [p for p in pts if p.get(key) is not None]
    X = design(pts, form); y = np.array([target(p, key, form) for p in pts])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    res = y - X @ beta
    loo = []
    for i in range(len(pts)):
        m = np.ones(len(pts), bool); m[i] = False
        b, *_ = np.linalg.lstsq(X[m], y[m], rcond=None)
        loo.append(float(y[i] - X[i] @ b))
    return pts, beta, res, np.array(loo)


def stats(r):
    return dict(n=len(r), max=round(float(np.max(np.abs(r))), 1), rms=round(float(np.sqrt(np.mean(r * r))), 1))


def main():
    pts_all = [p for p in P if not excluded(p)]
    sets = {
        "ALL (edge+centre, all structures)": pts_all,
        "CENTRE entry, CTS-grown (cts+rt)": [p for p in pts_all if p["entry"] == "centre" and p["struct"] in ("cts", "rt")],
        "CENTRE entry, CTS-grown, GRT only": [p for p in pts_all if p["entry"] == "centre" and p["struct"] in ("cts", "rt") and p["basis"] == "GRT"],
        "EDGE entry (cts+trunk)": [p for p in pts_all if p["entry"] == "edge"],
        "PLAN-built trees (QC SU R4b/R5/R6)": [p for p in pts_all if p["struct"] == "plan"],
    }
    out = {}
    for sname, pts in sets.items():
        out[sname] = {}
        for key in ("tt_mean", "tt_max", "ff_mean", "ff_max"):
            for form in ("K*L+c", "a+bL", "a+bL+PL", "a+bL+PL+struct", "a+bL+PL+log2N"):
                pp = [p for p in pts if p.get(key) is not None]
                X = design(pp, form)
                if not pp or len(pp) < X.shape[1] + 2 or np.linalg.matrix_rank(X) < X.shape[1]:
                    continue
                pp, beta, res, loo = fit(pts, key, form)
                out[sname][f"{key} | {form}"] = dict(beta=[round(float(b), 4) for b in beta], fit=stats(res), loo=stats(loo),
                                                    worst=[(pp[i]["die"] + ":" + pp[i]["core"] + ":" + pp[i]["trial"][:14], round(float(res[i]), 1))
                                                           for i in np.argsort(-np.abs(res))[:3]])
        # current model, no refit
        pp = [p for p in pts if p.get("tt_mean") is not None]
        r = np.array([p["tt_mean"] - RCX * K_MAIN * p["L"] for p in pp])
        out[sname]["tt_mean | CURRENT main (0.943*0.896*L, no offset)"] = dict(fit=stats(r), mean_bias=round(float(r.mean()), 1))
    (T / "fits.json").write_text(json.dumps(out, indent=1))
    for s, d in out.items():
        print("=====", s)
        for k, v in d.items():
            print(f"  {k:48} beta={v.get('beta')} fit={v['fit']} loo={v.get('loo')} {v.get('mean_bias', '')} {v.get('worst', '')}")


if __name__ == "__main__":
    main()
