#!/usr/bin/env python3
"""VISLAYOUT3-S81-LEAF form LANE-PAIR (positions / orients only; core shapes, ports, cycles unchanged).

The 16 hcpost lanes of an S81 leaf go into ONE 2-column x 8-row strip on the side of the type their field already
sits on (E or W), as 4 row pairs = the 4 quad2 groups (CS_H_G 4):
  * inside a pair the two rows face each other with their S faces (clk + rst_n only, 2 pins) across LO um;
  * between pairs the 160-pin N faces (c0..c3, p) face each other across a HI um street;
  * the two columns keep HI um (W face 97 pins vs E face 18 pins); the lane W faces point at the hub;
  * the strip keeps HI um from every hub core.
Type clock leaf taps (soft, non-core) that fall under a lane move to the nearest strip street / channel centre line
(reported; at most --tap-move-max um).  Hub cores are not placed here: core_place.py legalises them under the same R3
face rule (--gap-pinface HI:LO:PINS) and searches.

usage: vl3_strip.py PLAN TYPES OUT_DIR [--hi 43.2] [--lo 21.6] [--edge 8.64] [--tap-move-max 200]
writes OUT_DIR/seed.json {type: {inst: {origin_um, orient}}}, OUT_DIR/plan_taps.json (PLAN with the moved taps),
OUT_DIR/strip_report.json
"""
import argparse
import copy
import itertools
import json
import re
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("types"); ap.add_argument("out")
ap.add_argument("--hi", type=float, default=43.2)
ap.add_argument("--lo", type=float, default=21.6)
ap.add_argument("--edge", type=float, default=8.64)
ap.add_argument("--tap-move-max", type=float, default=200.0)
ap.add_argument("--repo", help="repo root: pick the strip edge / y offset where every lane is legal in core_place's model")
a = ap.parse_args()
if a.repo:
    import sys as _s
    import numpy as _np
    _s.path.insert(0, str(Path(a.repo) / "tools" / "die_plan"))
    import core_place as CP     # noqa: E402
    import route_supply as RS   # noqa: E402
    RS.REF_DIRS[:] = [str(Path(a.plan).resolve().parent)]
    _rs = dict(RS.DEFAULTS, derate=dict(RS.DERATE), core_ceiling=RS.DEFAULTS["core_ceiling"], views={}, kit_views={})
    _conns = RS.load_conns(Path(a.repo) / "physical/die_plan/s81", None, Path(a.plan).resolve().parent, [])
    _cfg = dict(gap=a.lo, sweeps=1, topk=1, lam=4.0, reach=405.0, grid_um=21.6, grt_halving="full", fixed_re="",
                rs=_rs, flips_only=False, face_clear=[], gap_pinface=(43.2, 21.6, 24))
G = 4.32
snap = lambda v: round(round(v / G) * G, 4)   # noqa: E731
P = json.loads(Path(a.plan).read_text())
Q = copy.deepcopy(P)
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
LANE = re.compile(r"g_ln\[(\d+)\]\.u_l$")
# R0 lane: pins N 160 (c0..c3, p), W 97 (r0..r3, y), E 18 (o, vo, fault), S 2 (clk, rst_n)
#   pins-up = N on top, pins-down = MX; W pins toward the hub: E strip keeps R0/MX, W strip mirrors (MY/R180)
ORI = {("E", "up"): "R0", ("E", "down"): "MX", ("W", "up"): "MY", ("W", "down"): "R180"}
seeds, rep = {}, {}
types = [t for t in P["partition_types"] if re.fullmatch(a.types, t)] if not "," in a.types and "*" in a.types \
    else [t for t in a.types.split(",") if t]
for tn in types:
    t = Q["partition_types"][tn]
    W, H = t["outline_um"]
    lanes = {}
    for c in t["hard_cores"]:
        m = LANE.search(c["inst"])
        if m:
            lanes[int(m.group(1))] = c
    lw, lh = lanes[0]["outline_um"]
    cx = sum(c["origin_um"][0] + lw / 2 for c in lanes.values()) / 16
    side = "E" if cx > W / 2 else "W"
    hub = [c for c in t["hard_cores"] if not LANE.search(c["inst"])]
    qy = {g: sum(lanes[4 * g + j]["origin_um"][1] for j in range(4)) / 4 for g in range(4)}
    order = sorted(range(4), key=lambda g: qy[g])   # quad -> row pair by the quad2 sites' y order

    def geom(edge, dy):
        if side == "E":
            x_out = snap(W - edge - lw); x_in = snap(x_out - a.hi - lw)
        else:
            x_out = snap(edge); x_in = snap(x_out + lw + a.hi)
        cols = [x_in, x_out]
        pair_h = 2 * lh + a.lo
        tot = 4 * pair_h + 3 * a.hi
        y0 = snap((H - tot) / 2 + dy)
        rows = []
        for p in range(4):
            yb = y0 + p * (pair_h + a.hi)
            rows.append((snap(yb), "down"))
            rows.append((snap(yb + lh + a.lo), "up"))
        sd = {}
        for pair, g in enumerate(order):
            for j in range(4):
                y, ud = rows[2 * pair + j // 2]
                sd[lanes[4 * g + j]["inst"]] = {"origin_um": [cols[j % 2], y], "orient": ORI[(side, ud)]}
        return cols, rows, y0, tot, sd

    pick = (a.edge, 0)
    if a.repo:
        M = CP.TypeModel(tn, P["partition_types"][tn], Path(a.repo) / "physical/die_plan/s81", Path(a.repo), _conns, _cfg)
        ck0 = P["partition_types"][tn].get("clock") or {}
        mv = _np.zeros(len(M.FP), bool)
        for tp in (ck0.get("taps") or []) + (ck0.get("added_taps") or []):
            if isinstance(tp, dict) and tp.get("xy") and tp.get("kind") != "core":
                mv |= (_np.abs(M.FP[:, 0] - tp["xy"][0]) < 0.01) & (_np.abs(M.FP[:, 1] - tp["xy"][1]) < 0.01)
        M.FP, M.FPH = M.FP[~mv], M.FPH[~mv]
        lk = [k for k in range(M.m) if LANE.search(M.inst[M.CL[k][0]])]
        hubk = {k for k in range(M.m) if k not in lk}
        pick = None
        for edge in [4.32 * i for i in range(1, 40)]:
            for dy in [0] + [s_ * 4.32 * i for i in range(1, 12) for s_ in (1, -1)]:
                cols, rows, y0, tot, sd = geom(edge, dy)
                for inst, v in sd.items():
                    i = M.idx[inst]; k = M.cid[i]
                    M.cflip[k] = CP.comp(M.ori0[i], v["orient"])
                    ox, oy = M.coff[i]
                    M.cpos[k] = (CP.snap(v["origin_um"][0] - ox), CP.snap(v["origin_um"][1] - oy))
                if all(M.legal(k, *M.cpos[k], ignore=hubk) for k in lk):
                    pick = (edge, dy)
                    break
            if pick:
                break
        if not pick:
            print(tn, "NO LEGAL STRIP", flush=True)
            rep[tn] = dict(side=side, status="NO_LEGAL_STRIP")
            continue
    edge_u = pick[0]
    cols, rows, y0, tot, sd = geom(*pick)
    seeds[tn] = sd
    # lane rects (with the 8.65 tap halo) -> move soft clock taps out to the nearest street centre line
    rects = [(v["origin_um"][0], v["origin_um"][1], v["origin_um"][0] + lw, v["origin_um"][1] + lh) for v in sd.values()]
    hubr = [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0],
             c["origin_um"][1] + c["outline_um"][1]) for c in hub]
    hal = 8.65
    under = lambda x, y, R: any(r[0] - hal < x < r[2] + hal and r[1] - hal < y < r[3] + hal for r in R)  # noqa
    vlines = sorted({cols[0] + lw + a.hi / 2, (cols[0] - a.hi / 2) if side == "E" else (cols[0] + lw + a.hi / 2),
                     min(cols) + lw + a.hi / 2})
    vlines = [min(cols) - a.hi / 2, min(cols) + lw + a.hi / 2, max(cols) + lw + (edge_u / 2)]
    hlines = [rows[2 * p][0] + lh + a.lo / 2 for p in range(4)] + \
             [rows[2 * p + 1][0] + lh + a.hi / 2 for p in range(3)] + [y0 - a.hi / 2, y0 + tot + a.hi / 2]
    xs0, xs1 = min(cols) - a.hi, max(cols) + lw + edge_u
    ck = t.get("clock") or {}
    moved, failed = {}, []
    for tp in (ck.get("taps") or []) + (ck.get("added_taps") or []):
        if not isinstance(tp, dict) or not tp.get("xy") or tp.get("kind") == "core":
            continue
        x, y = tp["xy"][:2]
        if not under(x, y, rects):
            continue
        best = None
        for vx in vlines:
            for yy in [y0 - a.hi / 2 + k * G for k in range(int((tot + a.hi) / G) + 1)]:
                if 0 < vx < W and 0 < yy < H and not under(vx, yy, rects) and not under(vx, yy, hubr):
                    d = abs(vx - x) + abs(yy - y)
                    if best is None or d < best[0]:
                        best = (d, vx, yy)
        for hy in hlines:
            for xx in [xs0 + k * G for k in range(int((xs1 - xs0) / G) + 1)]:
                if 0 < xx < W and 0 < hy < H and not under(xx, hy, rects) and not under(xx, hy, hubr):
                    d = abs(xx - x) + abs(hy - y)
                    if best is None or d < best[0]:
                        best = (d, xx, hy)
        if best is None or best[0] > a.tap_move_max:
            failed.append(tp.get("name"))
            continue
        tp["xy"] = [round(best[1], 3), round(best[2], 3)] + list(tp["xy"][2:])
        moved[tp.get("name")] = [round(x, 3), round(y, 3), tp["xy"][0], tp["xy"][1], round(best[0], 1)]
    rep[tn] = dict(side=side, edge_dy=pick, cols=cols, rows=[r[0] for r in rows], quad_to_pair=order, taps_moved=moved,
                   taps_failed=failed)
    print(tn, side, "taps moved", len(moved), "failed", failed, flush=True)

(out / "seed.json").write_text(json.dumps(seeds, indent=1))
(out / "plan_taps.json").write_text(json.dumps(Q))
(out / "strip_report.json").write_text(json.dumps(rep, indent=1))
