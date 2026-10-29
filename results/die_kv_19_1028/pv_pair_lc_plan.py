#!/usr/bin/env python3
"""DIE-KV-19 (2026-10-28) pv_pair (b2) plan delta: per-lane-group red_issue / red_capture copy pins on kv3_pv_pair.

1. Pins: kv3_pv_pair pins files r26c (R0) + fMX_r26c get s0__bcx[5:0] / s1__bcx[5:0] (1652 -> 1664 bracketed pins),
   placed by the SAME law that made the face (core_pins_v37p.py: one face, M5 x-tracks, pitch 0.048 offset 0.024, 2.16 um
   corner keep-out, pins in (port, bit) order spread evenly, the 4 clk/rst slots reserved then moved to the 12.8a entry
   island by KV-CORE-SLICE-1).  Reproduces the committed face exactly before the delta (asserted), so the delta is only
   the 12 new pins + the even re-spread (max move reported).  Clock/reset island pins, ft pins, island_ft, core_tree unchanged.
2. Plan: every kv3_pv* partition type's 32 bank leaves ot_qwen_tp8_pv_slice_t -> ot_qwen_tp8_pv_slice_lc_t (the leaf of
   the LC=1 column, rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv) and the kv3_pv_pair cores point at the new pins files.
usage: pv_pair_lc_plan.py IN_PLAN OUT_PLAN (OUT_PLAN dir at the same depth as IN_PLAN's, pins written to ../cores)
"""
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "die_kv_7_1028/input/cores"
PITCH, OFFS, KEEP, L = 0.048, 0.024, 2.16, 380.16
FILES = {"kv3_pv_pair_pins_r26c.json": 189.984, "kv3_pv_pair_pins_fMX_r26c.json": 0.096}
NEW = [f"s{k}__bcx[{b}]" for k in (0, 1) for b in range(6)]


def key(n):
    m = re.match(r"(.*)\[(\d+)\]$", n)
    return (m.group(1), int(m.group(2)))


def spread(names):
    lo = math.ceil((KEEP - OFFS) / PITCH)
    hi = math.floor((L - KEEP - OFFS) / PITCH)
    nl = len(names)
    return {n: round(OFFS + (lo + int((j + 0.5) * (hi - lo + 1) / nl)) * PITCH, 6) for j, n in enumerate(names)}


def pins_delta(fn, fy):
    d = json.loads((SRC / fn).read_text())
    P = d["pins"]
    br = sorted([q["name"] for q in P if "[" in q["name"]], key=key)
    old = spread(br)
    face = [q for q in P if abs(q["y"] - fy) < 1e-6]
    assert all(abs(q["x"] - old[q["name"]]) < 1e-6 for q in face), fn          # committed face == the law
    new = spread(sorted(br + NEW, key=key))
    moves = []
    for q in face:
        moves.append(abs(new[q["name"]] - q["x"]))
        q["x"] = new[q["name"]]
    P.extend(dict(name=n, layer="M5", x=new[n], y=fy) for n in NEW)
    xs = sorted(q["x"] for q in P if abs(q["y"] - fy) < 1e-6)
    gap = min(b - a for a, b in zip(xs, xs[1:]))
    d["source"] += (" | DIE-KV-19 10-28 (b2): + s0__bcx[5:0] s1__bcx[5:0] (per-lane-group red_issue/red_capture copy pins, "
                    "1652 -> 1664), face re-spread by the same law (results/die_kv_19_1028/pv_pair_lc_plan.py)")
    out = HERE / "cores" / fn.replace(".json", "_lc.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(d, indent=1) + "\n")
    return out, dict(face_pins=len(face) + len(NEW), max_move_um=round(max(moves), 3), min_gap_um=round(gap, 3))


def main(inp, outp):
    rep = {}
    for fn, fy in FILES.items():
        out, r = pins_delta(fn, fy)
        rep[fn] = r
    p = json.loads(Path(inp).read_text())
    nt = nl = nc = 0
    for tn, t in p["partition_types"].items():
        hit = 0
        for c in t.get("contents", []):
            if c["module"] == "ot_qwen_tp8_pv_slice_t":
                c["module"] = "ot_qwen_tp8_pv_slice_lc_t"
                c["note"] = c.get("note", "") + " | DIE-KV-19 lc leaf (bcx copy pins)"
                hit += 1
        for h in t.get("hard_cores", []):
            if h["module"] == "kv3_pv_pair":
                pf = h["pins_file"]
                base = pf.rsplit("/", 1)[1]
                assert base in FILES, pf
                h["pins_file"] = "../cores/" + base.replace(".json", "_lc.json")
                h["note"] = h.get("note", "") + " | DIE-KV-19 (b2): + bcx[5:0] per slice (red_issue/red_capture lane-group copies)"
                nc += 1
        if hit:
            assert hit == 32, (tn, hit)
            nt += 1
            nl += hit
    p["note"] = p.get("note", "") + " | DIE-KV-19 (b2): pv bank leaves -> ot_qwen_tp8_pv_slice_lc_t, kv3_pv_pair pins +12 (bcx)"
    Path(outp).parent.mkdir(parents=True, exist_ok=True)
    Path(outp).write_text(json.dumps(p))
    rep.update(types=nt, leaves=nl, cores=nc)
    print(json.dumps(rep))


if __name__ == "__main__":
    main(*sys.argv[1:3])
