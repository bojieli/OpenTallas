#!/usr/bin/env python3
"""adv_tap_step.py -- PRECHECK advisory TAP-STEP (HEAD-ALLFIX 11-25, from FABLE-RC-HEAD tap_step_check draft).

For every partition type with a plan clock.tap_offset.per_port_ps row: neighbouring kit clock taps (K nearest by site)
whose die-arrival offsets differ by more than TOL_PS (42 ps, the TT setup budget), every hard core whose surrounding taps
(core box + 60 um) spread more than TOL_PS, and kit taps with no offset row.  A flop on tap A talking to a flop / macro on a
neighbouring tap B loses (off_A - off_B) of setup (and B -> A that much hold) unless the kit tap balance removes it; the
kit SDC grants only tap_window (HEAD W6: hd_lep0N 16 neighbour pairs > 42 ps, max 125.4, table priced on the 11-20 r13 die
clock).  Types with taps but no table are counted as UNPRICED (one summary line).  Report only: never changes the PRE verdict.

    python3 adv_tap_step.py PLAN [--types a,b] [--tol 42] [--k 4] [--tsv OUT]    (rc 1 when any listed type FAILs)
"""
import argparse
import json
import math
import sys

TOL_PS = 42.0
K = 4
RING_UM = 60.0


def _box(h):
    x, y = h["origin_um"]
    w, hh = h["outline_um"]
    if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
        w, hh = hh, w
    return x, y, w, hh


def judge_type(t, off, tol=TOL_PS, k=K):
    """{'pairs': [(|s|, corner, a, b, s, dist)], 'macros': [(spread, inst, n)], 'missing': [port], 'max_step': ps}"""
    taps = [x for x in ((t.get("clock") or {}).get("taps") or []) if x.get("kind") != "core"]
    P = {x["name"]: tuple(x["xy"]) for x in taps}
    miss = sorted(n for n in P if n not in off)
    near = {}
    for n, xy in P.items():
        near[n] = sorted((m for m in P if m != n), key=lambda m: math.hypot(P[m][0] - xy[0], P[m][1] - xy[1]))[:k]
    seen, pairs, steps = set(), [], []
    for n in P:
        if n not in off:
            continue
        for m in near[n]:
            if m not in off or (m, n) in seen:
                continue
            seen.add((n, m))
            for cn in ("TT", "FF"):
                if cn not in off[n] or cn not in off[m]:
                    continue
                s = float(off[n][cn]) - float(off[m][cn])
                if cn == "TT":
                    steps.append(abs(s))
                if abs(s) > tol:
                    pairs.append((abs(s), cn, n, m, s, math.hypot(P[n][0] - P[m][0], P[n][1] - P[m][1])))
    macros = []
    for h in t.get("hard_cores") or []:
        if "origin_um" not in h or "outline_um" not in h:
            continue
        x0, y0, w, hh = _box(h)
        ring = [n for n, (x, y) in P.items() if n in off and "TT" in off[n]
                and x0 - RING_UM <= x <= x0 + w + RING_UM and y0 - RING_UM <= y <= y0 + hh + RING_UM]
        v = [float(off[n]["TT"]) for n in ring]
        if v and max(v) - min(v) > tol:
            macros.append((max(v) - min(v), h.get("inst", "?"), len(ring)))
    return {"pairs": sorted(pairs, reverse=True), "macros": sorted(macros, reverse=True), "missing": miss,
            "max_step": max(steps) if steps else 0.0, "npairs": len(seen), "ntaps": len(P)}


def check(raw, types=None, tol=TOL_PS, k=K):
    ck = raw.get("clock") or {}
    off_all = (ck.get("tap_offset") or {}).get("per_port_ps") or {}
    pt = raw.get("partition_types") or {}
    res, unpriced = {}, []
    for tn in (types or sorted(pt)):
        t = pt.get(tn)
        if not isinstance(t, dict) or not (t.get("clock") or {}).get("taps"):
            continue
        if tn not in off_all:
            unpriced.append(tn)
            continue
        res[tn] = judge_type(t, off_all[tn], tol, k)
    return res, unpriced


def _fails(r):
    return bool(r["pairs"] or r["macros"] or r["missing"])


def findings(raw, plan_path, tree=None, **_kw):
    try:
        res, unpriced = check(raw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [f"WARN ADV-TAP-STEP not checked: {type(e).__name__}: {str(e)[:200]}"]
    out = []
    for tn, r in sorted(res.items()):
        if not _fails(r):
            continue
        tt = [p for p in r["pairs"] if p[1] == "TT"]
        top = "; ".join(f"{p[2]}-{p[3]} {p[4]:+.1f} ps" for p in tt[:3])
        out.append(f"WARN ADV-TAP-STEP {tn}: {len(tt)} TT neighbour tap pairs > {TOL_PS:g} ps (max {r['max_step']:.1f}; {top}), "
                   f"{len(r['macros'])} hard cores with tap spread > {TOL_PS:g} ps, {len(r['missing'])} taps without an offset row")
    if unpriced:
        out.append(f"WARN ADV-TAP-STEP summary: {len(unpriced)} type(s) with taps and no per-port tap_offset row (UNPRICED): {', '.join(unpriced[:12])}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="adv_tap_step", description=__doc__.split("\n\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--types", default="")
    ap.add_argument("--tol", type=float, default=TOL_PS)
    ap.add_argument("--k", type=int, default=K)
    ap.add_argument("--tsv", default="")
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    res, unpriced = check(raw, [t for t in a.types.split(",") if t] or None, a.tol, a.k)
    rows = []
    for tn, r in sorted(res.items()):
        tt = [p for p in r["pairs"] if p[1] == "TT"]
        print(f"{tn:16s} taps {r['ntaps']:3d} pairs {r['npairs']:4d} max |step| TT {r['max_step']:.1f}  pairs>{a.tol:g}: {len(tt)}  "
              f"macros>{a.tol:g}: {len(r['macros'])}  no row: {len(r['missing'])}  {'FAIL' if _fails(r) else 'PASS'}")
        rows += ["\t".join(map(str, (tn, "pair", p[1], p[2], p[3], f"{p[4]:.1f}", f"{p[5]:.0f}"))) for p in r["pairs"]]
        rows += ["\t".join(map(str, (tn, "macro", "TT", m[1], "", f"{m[0]:.1f}", m[2]))) for m in r["macros"]]
        rows += ["\t".join((tn, "missing", "", n, "", "", "")) for n in r["missing"]]
    for tn in unpriced:
        print(f"{tn:16s} UNPRICED (taps, no per-port tap_offset row)")
    if a.tsv:
        open(a.tsv, "w").write("type\tkind\tcorner\ta\tb\tstep_ps\tdist_um_or_ntaps\n" + "\n".join(rows) + "\n")
    return 1 if any(_fails(r) for r in res.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
