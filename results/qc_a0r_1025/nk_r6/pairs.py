#!/usr/bin/env python3
"""PATH-QC-NK2: related-pair skew with CPPR for the top tap pairs of PREFIX.tsv.
pairs.py mk PREFIX N   -> PREFIX.pairs_in.txt (start end per top pair's worst endpoint)
pairs.py parse PREFIX  -> reads PREFIX.pairs.rpt (report_checks -format full_clock_expanded) -> PREFIX.pairs.txt"""
import csv, sys, collections, re
mode, P = sys.argv[1], sys.argv[2]
if mode == "mk":
    N = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    rows = [r for r in csv.DictReader(open(P + ".tsv"), delimiter="\t") if r["class"].startswith("R2R")]
    cnt = collections.Counter((r["ltap"], r["ctap"]) for r in rows)
    with open(P + ".pairs_in.txt", "w") as f:
        for (a, b), n in cnt.most_common(N):
            w = min((r for r in rows if (r["ltap"], r["ctap"]) == (a, b)), key=lambda r: float(r["slack"]))
            f.write(f"{a}\t{b}\t{n}\t{w['slack']}\t{w['start']}\t{w['end']}\n")
else:
    pairs = [l.rstrip("\n").split("\t") for l in open(P + ".pairs_in.txt")]
    txt = open(P + ".pairs.rpt").read().split("Startpoint:")[1:]
    out = ["# launch_tap capture_tap n_ep worst_slack launch_clk capture_clk crpr pair_skew(=capture-launch-crpr) ps"]
    for (a, b, n, sl, s, e), blk in zip(pairs, txt):
        cn = [float(x) for x in re.findall(r"^\s*(-?[\d.]+)\s+-?[\d.]+\s+clock network delay \(propagated\)", blk, re.M)]
        if not cn:   # full_clock_expanded: launch / capture clock edges = the time column at the clock pin of start / end
            cn = []
        cr = re.findall(r"^\s*(-?[\d.]+)\s+-?[\d.]+\s+clock reconvergence pessimism", blk, re.M)
        crpr = float(cr[0]) if cr else 0.0
        clk = re.findall(r"^\s*-?[\d.]+\s+(-?[\d.]+)\s+[\^v]\s+\S+/CLK \(", blk, re.M)
        if len(clk) >= 2: L, C = float(clk[0]), float(clk[1])
        elif len(cn) >= 2: L, C = cn[0], cn[1]
        else: L = C = float("nan")
        out.append(f"{a} {b} {n} {float(sl):.2f} {L:.1f} {C:.1f} {crpr:.1f} {C - L - crpr:.1f}")
    open(P + ".pairs.txt", "w").write("\n".join(out) + "\n"); print("\n".join(out))
