#!/usr/bin/env python3
"""Cut analysis for the TP8 collective cluster coll_tp8_rt (owner rule "CUT ANALYSIS BEFORE RTL", 2026-10-12).

E-W bits per cycle crossing each vertical cut line of the cluster vs the usable horizontal tracks there:
  M4 (48 nm pitch, no cluster PG) + M6 (64 nm pitch, minus the M6 PG pair: 2 x 0.288 + 0.096 um + one track per
  5.4 um = 13.6 %), over the y-span NOT covered by a block whose OBS holds that layer (ot_coll_fold_slice: M1-M6;
  ot_sram_1r1w_32x546_m1: M1-M4, so M6 passes over the macros).  M2 is left out (cell-local reserve); M7 is vertical.
Demand = sum of the flows whose two ends lie on opposite sides of the cut (flow ends = the block / region positions
of the floorplan; a bus is counted once however many queues it feeds).  Target <= 0.55 (owner band 0.55-0.60).
usage: python3 tools/qwen_tp8_coll_cut.py [--spec SPEC.json]   (no spec: both built-in variants v1 / v2)
"""
import argparse
import json

M4 = 1 / 0.048
M6 = (1 / 0.064) * (1 - 0.136)
OBS = {"ot_coll_fold_slice": {"M4", "M6"}, "ot_sram_1r1w_32x546_m1": {"M4"}}
SL, MW, MH = 181.44, 177.768, 81.0


def blocks_of(spec):
    out = []
    for c in spec["children"] + spec["macros"]:
        m = "ot_coll_fold_slice" if "fold_slice" in c["view"] else "ot_sram_1r1w_32x546_m1"
        w, h = (SL, SL) if m == "ot_coll_fold_slice" else (MW, MH)
        out.append((c["inst"], m, c["at"][0], c["at"][1], w, h))
    return out


def capacity(blocks, x, H):
    cap = 0.0
    for lay, tr in (("M4", M4), ("M6", M6)):
        cov = sorted((y, y + h) for _, m, bx, y, w, h in blocks if lay in OBS[m] and bx <= x <= bx + w)
        free, cur = 0.0, 0.0
        for a, b in cov:
            if a > cur:
                free += a - cur
            cur = max(cur, b)
        free += max(0.0, H - cur)
        cap += free * tr
    return cap


# flows (name, bits, x_from, x_to) per variant; x = where the bus starts / ends (um from the W face)
def flows(v, W):
    if v == "v1":   # 8349bde87: queues LB/PQ/RQ/TQ/LQ0 in column A, pairing + EQ + merger + engine heads in C
        A, pair, Bw, Be, C, Dw, De, E = 132, 564, 259.2, 440.6, 564, 691.2, 872.6, 996
        return [("S in_* (whole S face) -> relay/LB (A)", 548, 561.6, A), ("LB+PQ heads (A) -> pairing (C)", 1092, A, pair),
                ("pairing (C) -> pre-fold src (B W face)", 1024, pair, Bw), ("pre-fold sum (B E face) -> EQ (C)", 512, Be, C),
                ("engine FIFO reads (E) -> heads (C)", 2184, E, C), ("heads (C) -> engine slice src (D W face)", 2048, C, Dw),
                ("engine result (D E face) -> TQ/LQ0 (A)", 520, De, A), ("RQ+LQ0 reads (A) -> merger (C)", 1031, A, C),
                ("engine tx (C) -> 3 SerDes copies (E face)", 546, C, W), ("SerDes rx (E face) -> FIFOs (E)", 1638, W, E),
                ("UCIe up/dp/ur/dr (W face) <-> A", 2130, 0, A), ("tags/credits/control", 100, A, C)]
    A, pair, Bw, Be, C, Dw, De, E = 132, 262, 302.4, 483.8, 607, 734.4, 915.8, 1039
    return [("S in_* (S face 43-302) -> relay/LB (A)", 548, 172, A), ("LB+PQ heads (A) -> pairing (A|B channel)", 1092, A, pair),
            ("pairing -> pre-fold src (B W face)", 1024, pair, Bw), ("pre-fold sum (B E face) -> EQ (C)", 512, Be, C),
            ("gather words: pairing -> EQ (C)", 546, pair, C),
            ("engine FIFO reads (E) -> heads (C)", 2184, E, C), ("heads (C) -> engine slice src (D W face)", 2048, C, Dw),
            ("engine result (D E face) -> TQ/LQ (A)", 520, De, A), ("RQ+LQ reads (A) -> merger (A, N face 43-302)", 1031, A, A),
            ("engine tx (C) -> 3 SerDes copies (E face)", 546, C, W), ("SerDes rx (E face) -> FIFOs (E)", 1638, W, E),
            ("UCIe up/dp (W 43-475) / ur/dr (W 475-907) <-> A", 2130, 0, A), ("tags/credits/control", 100, pair, C)]


def analyse(spec, v):
    W, H = spec["outline"]["w"], spec["outline"]["h"]
    bl = blocks_of(spec)
    cols = sorted({round(b[2], 3) for b in bl})
    cuts = []
    for c in cols:
        w = max(b[4] for b in bl if round(b[2], 3) == c)
        cuts.append((f"col@{c:g} mid", c + w / 2))
    rows = []
    fl = flows(v, W)
    for nm, x in cuts:
        d = sum(b for _, b, a, z, in fl if min(a, z) < x < max(a, z))
        cap = capacity(bl, x, H)
        rows.append((nm, x, d, cap, d / cap))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", action="append")
    a = ap.parse_args()
    specs = a.spec or ["tools/ref_tile/specs_qwen_tp8/coll_tp8_rt.json", "tools/ref_tile/specs_qwen_tp8/coll_tp8_rt2.json"]
    for p in specs:
        s = json.load(open(p))
        v = "v1" if s["name"] == "coll_tp8_rt" else "v2"
        W, H = s["outline"]["w"], s["outline"]["h"]
        print(f"== {s['name']} ({v}) {W} x {H} um; face pins/um: W {2130 / H:.2f}  E {3290 / H:.2f}")
        worst = 0
        for nm, x, d, cap, u in analyse(s, v):
            worst = max(worst, u)
            print(f"  {nm:<16} x={x:7.1f}  demand {d:5d}  tracks {cap:7.0f}  util {u:.2f}")
        print(f"  worst E-W cut util {worst:.2f} -> {'PASS' if worst <= 0.55 else 'FAIL'} (target <= 0.55)")


if __name__ == "__main__":
    main()
