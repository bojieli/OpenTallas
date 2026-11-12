#!/usr/bin/env python3
"""HBM-VSN-XTAP-2 11-12 plan-level paper check of every cross-port station hop with the lockup-latch form.
paper_hops.py HOPS_TSV OUT_TSV [--T 833] [--s 90] [--s0 30] [--tsu 30] [--th 15]
              [--aTT ps/um] [--cqTT ps] [--aFF ps/um] [--cqFF ps] [--measured vsN4=PAIRS_TSV]
Model (latch ot_dp_lk transparent-low, opens at T/2; hop wire split at fraction f from the launch station):
  D_TT = bTT + aTT*Lmax (vsN4 routed: d1max+d2max 334-361 ps flat over 170-335 um) (max corner, longest bit), D_FF = aFF*Lmin (min corner, shortest bit)
  d1max = cqTT + f*D_TT   d2max = (1-f)*D_TT   d1min = cqFF + f*D_FF   d2min = (1-f)*D_FF
  latch on LAUNCH tap (L): leg1 same port (CRPR), leg2 cross port (window W + real skew s charged):
     S1 = T - d1max - tsu - s0       H1 = d1min - th - s0
     S2 = T/2 - W - s - d2max - tsu  H2 = T/2 - W - s + d2min - th
  latch on CAPTURE tap (C): leg1 cross port, leg2 same port:
     S1 = T - W - s - d1max - tsu    H1 = d1min - th - W - s
     S2 = T/2 - s0 - d2max - tsu     H2 = T/2 - s0 + d2min - th
  default = generator default (L, f 0.5); when it fails, the best (tap, f in 0.05..0.95) by max min-slack.
  The flop form (today's non-lockup types): S = T - W - s - cqTT - D_TT - tsu, H = cqFF + D_FF - th - W - s.
vsN4 hops with a measured row (form A' pairs table) take the measured verdict / tap / f instead (stronger)."""
import argparse, csv

ap = argparse.ArgumentParser()
ap.add_argument("hops"); ap.add_argument("out")
for k, v in dict(T=833., s=90., s0=30., tsu=30., th=15., bTT=240., aTT=0.12, cqTT=90., aFF=0.55, cqFF=30.).items():
    ap.add_argument("--" + k, type=float, default=v)
ap.add_argument("--measured", action="append", default=[])
ap.add_argument("--pad", type=float, default=1.6)
ap.add_argument("--uniform", type=float, default=0.0, help="every plan hop at the default tap and this latch_frac")
ap.add_argument("--capdefault", default="L201x", help="slot prefixes whose latch the die default hangs on the capture tap")
a = ap.parse_args()
meas = {}
for m in a.measured:
    tn, p = m.split("=")
    for r in csv.DictReader(open(p), delimiter="\t"):
        meas[(tn, r["slot"], r["k"])] = r


def legs(tap, f, W, Lmax, Lmin):
    DT, DF = a.bTT + a.aTT * Lmax, a.aFF * Lmin
    d1M, d2M, d1m, d2m = a.cqTT + f * DT, (1 - f) * DT, a.cqFF + f * DF, (1 - f) * DF
    if tap == "L":
        S1, H1 = a.T - d1M - a.tsu - a.s0, d1m - a.th - a.s0
        S2, H2 = a.T / 2 - W - a.s - d2M - a.tsu, a.T / 2 - W - a.s + d2m - a.th
    else:
        S1, H1 = a.T - W - a.s - d1M - a.tsu, d1m - a.th - W - a.s
        S2, H2 = a.T / 2 - a.s0 - d2M - a.tsu, a.T / 2 - a.s0 + d2m - a.th
    return min(S1, S2), min(H1, H2), padok(S1, H1) and padok(S2, H2)


def padok(S, H):
    """a leg closes raw (S, H >= 0) or after hold padding: -H ps of FF min delay costs pad*(-H) of TT setup"""
    return S >= 0 and (H >= 0 or S + a.pad * H >= 0)


def stol(tap, f, W, Lmax, Lmin):
    """largest real cross-port skew |s| (both signs) the leg pair tolerates (raw or padded), by bisection"""
    s0 = a.s
    lo, hi = 0.0, 600.0
    for _ in range(40):
        mid = (lo + hi) / 2
        a.s = mid
        ok = legs(tap, f, W, Lmax, Lmin)[2]
        lo, hi = (mid, hi) if ok else (lo, mid)
    a.s = s0
    return lo


out = []
for r in csv.DictReader(open(a.hops), delimiter="\t"):
    W, Lmax, Lmin = float(r["W_ps"]), float(r["Lmax_um"]), float(r["Lmin_um"])
    key = (r["type"], r["slot"], r["k"])
    fS = a.T - W - a.s - a.cqTT - a.bTT - a.aTT * Lmax - a.tsu
    fH = a.cqFF + a.aFF * max(Lmin, 0) - a.th - W - a.s
    if Lmax < 0:
        out.append({**r, "flopS": "", "flopH": "", "defS": "", "defH": "", "tap": "?", "f": "", "S": "", "H": "",
                    "verdict": "UNKNOWN_SITES", "basis": "plan", "dtap": "", "stol_def": "", "stol": ""})
        continue
    dtap = "C" if any(r["slot"].startswith(p) for p in a.capdefault.split(",") if p) else "L"
    dS, dH, dP = legs(dtap, 0.5, W, Lmax, Lmin)
    if key in meas:
        m = meas[key]
        best = m["best"]
        tap = "C" if best == "latC" else "L"
        S, H = (float(m["latC_S"]), float(m["latC_H"])) if tap == "C" else (float(m["latL_S"]), float(m["latL_H"]))
        out.append({**r, "flopS": f"{fS:.1f}", "flopH": f"{fH:.1f}", "defS": f"{dS:.1f}", "defH": f"{dH:.1f}",
                    "tap": tap, "f": "meas", "S": f"{S:.1f}", "H": f"{H:.1f}", "verdict": m["verdict"],
                    "basis": "measured_vsN4_formAp", "dtap": dtap, "stol_def": "", "stol": ""})
        continue
    uS, uH, uP = legs(dtap, a.uniform, W, Lmax, Lmin) if a.uniform else (-1, -1, False)
    if a.uniform and uP:
        tap, f, S, H, Pd = dtap, a.uniform, uS, uH, uP
    elif min(dS, dH) >= 0:
        tap, f, S, H, Pd = dtap, 0.5, dS, dH, True
    else:
        cands = []
        for t in "LC":
            for fi in range(5, 100, 5):
                S_, H_, P_ = legs(t, fi / 100, W, Lmax, Lmin)
                cands.append((min(S_, H_) >= 0, P_, min(S_, H_), t == dtap, t, fi / 100))
        *_, tap, f = max(cands)
        S, H, Pd = legs(tap, f, W, Lmax, Lmin)
    out.append({**r, "flopS": f"{fS:.1f}", "flopH": f"{fH:.1f}", "defS": f"{dS:.1f}", "defH": f"{dH:.1f}",
                "tap": tap, "f": f"{f:.2f}", "S": f"{S:.1f}", "H": f"{H:.1f}",
                "verdict": "PASS" if min(S, H) >= 0 else ("PASS_PAD" if Pd else "FAIL"), "basis": "plan",
                "stol_def": f"{stol(dtap, 0.5, W, Lmax, Lmin):.0f}", "stol": f"{stol(tap, f, W, Lmax, Lmin):.0f}",
                "dtap": dtap})
cols = list(out[0].keys()) if out else []
with open(a.out, "w") as fo:
    w = csv.DictWriter(fo, cols, delimiter="\t"); w.writeheader(); w.writerows(out)
from collections import Counter
print("params", {k: getattr(a, k) for k in "T s s0 tsu th bTT aTT cqTT aFF cqFF pad".split()})
print("hops", len(out), Counter(o["verdict"] for o in out))
print("need key (not default L/0.5):", sum(1 for o in out if o["tap"] != "?" and (o["tap"] != o["dtap"] or o["f"] not in ("0.50",))))
print("flop form fails:", sum(1 for o in out if o["flopH"] and min(float(o["flopS"]), float(o["flopH"])) < 0))
