#!/usr/bin/env python3
"""qfd_sp_res_ser cluster floorplan (Qwen ROM TP8 contract v4b slot 777.6 x 518.4), generated top-down.

  res_ser_cluster_fp.py tile                      # slot tile kit qfd_res_slot_ru: spec + exact pin plan
  res_ser_cluster_fp.py cluster [--dx-my UM]      # cluster qfd_sp_res_ser: spec + exact pin plan + hop / cut analysis

Why top-down.  The first re-shape of the slot tile (qfd_res_slot_rs, 259.2 x 172.8, chain in W / out E, word S) closed
but cannot be composed: 3 x 259.2 leaves no channel and its W / E stubs short or corner-touch when abutted.  Here the
cluster is drawn first and the tile's outline and every tile pin follow from it.

Cluster (um).  Eight hard slot tiles ot_qfd_res_slot_tile of 216 x 142.56 on a 3 x 3 grid with a channel on every pin
face; the ninth cell (column 2, row 1) is the serialiser head (ot_qfd_res_tiles_ctl + the o / ok / cr / fault pin flops).

  x: 23.76 | col 0 216 | 43.2 | col 1 216 | 34.56 | col 2 216 | 28.08
  y: 23.76 | row 0 142.56 | 21.6 | row 1 142.56 | 21.6 | row 2 142.56 | 23.76

Tile pins.  N (M5): the 552-bit word at a 7-track pitch across the face, then i_we / i_last / i_empty / i_ov / me_en /
rst_n / slot_id at the E end, clk mid-face.  E (M4): the conveyor, in and out interleaved bit by bit (rd[k], od[k]) at a
2-track pitch.  S and W carry no pin, so rows stack with a plain 21.6-um gap and the word never crosses its own tile.

Orientation: column 0 R0 (conveyor face E), columns 1 and 2 MY (conveyor face W).  The 43.2-um gap between columns 0
and 1 holds the conveyor faces of six tiles: a hop is 35 um straight across (od[k] faces rd[k]) or 164 um to the next
row.  A 3 x 3 grid has no ring of adjacent cells through 8 tiles and one head (5 black / 3 white cells), so two hops
run over a column-1 tile on M6 (251 um).

Ring (slot g = ring position g): (2,2) (1,2) (0,2) (0,1) (1,1) (0,0) (1,0) (2,0); head at (2,1).

Input.  i word g sits on the N face directly above its tile's own word pins (the three tiles of a column interleaved
2 tracks apart), so a word is one straight M7 wire from its pin flop A down to the tile's pin flop: 22 um (row 2),
188 um (row 1), 352 um (row 0: two more stages M and X, X anchored at the tile pin).

The script prints / writes the analysis a die spec needs before RTL is hardened: every registered hop (<= 500 um) and
bits per cut against routing tracks (<= 0.60)."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W, H = 777.6, 518.4
TW, TH = 216.0, 142.56
COLX = [23.76, 282.96, 533.52]
ROWY = [23.76, 187.92, 352.08]
RING = [(2, 2), (1, 2), (0, 2), (0, 1), (1, 1), (0, 0), (1, 0), (2, 0)]      # slot g -> (col, row)
ORIENT = {0: "R0", 1: "MY", 2: "MY"}                                         # per column
HEAD = (2, 1)
P45, P67 = 0.048, 0.064                                                     # M4/M5 and M6/M7 track pitch
T0 = 0.012                                                                  # M4 / M5 track centre offset
MACRO = "physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2"
TKIT = "physical/ref_tile/qfd_res_slot_ru"
VIEW = TKIT + "/views/ot_qfd_res_slot_tile"
TILE_IO = "physical/res_ser/qfd_res_slot_ru_pins.tcl"
CL_IO = "physical/res_ser/qfd_sp_res_ser_pins.tcl"
CONTRACT = "results/arch/hier_contract_1012/qwen_rom_tp8.json"
CK_X, RST_X, ME_X = 388.788, 392.0, 396.0                                   # contract v4b offsets (N face)
OWNER, BRANCH = "Claude:el1013-qwen-elements-r6", "claude/el1013-qwen-elements-r6"


def trk(k):
    return round(T0 + k * P45, 3)


def snap(v):
    return trk(round((v - T0) / P45))


# ------------------------------------------------------------------------------------------------ tile pin plan
def tile_pins():
    """{pin: (face, layer, x, y)} in tile coordinates (R0), every pin on a track centre"""
    p = {}
    # N face: word order follows the macro (MY in the tile): wd_in[266..511] leave the macro on the tile's W side,
    # wd_in[0..265] on its E side; mask / addr (metadata flops) between them
    order = [f"i_data[{b}]" for b in range(266, 512)] + [f"i_mask[{b}]" for b in range(16)] \
        + [f"i_addr[{b}]" for b in range(24)] + [f"i_data[{b}]" for b in range(266)]
    k0 = 170                                                # x 8.172
    for j, n in enumerate(order):
        p[n] = ("N", "M5", trk(k0 + 7 * j), TH)
    p["clk"] = ("N", "M5", trk(k0 + 7 * 275 + 3), TH)       # mid-face, 3 / 4 tracks from its neighbours
    kc = k0 + 7 * 551 + 81                                  # 197.196: control group at the E end, 20-track pitch
    for j, n in enumerate(["i_we", "i_last", "i_empty", "i_ov", "me_en", "rst_n", "slot_id[0]", "slot_id[1]", "slot_id[2]"]):
        p[n] = ("N", "M5", trk(kc + 20 * j), TH)
    # E face: conveyor in / out interleaved, 2-track pitch, centred
    seq = ["rq_v", "rqf_v"]
    for b in range(3):
        seq += [f"rq_slot[{b}]", f"rqf_slot[{b}]"]
    for b in range(6):
        seq += [f"rq_ptr[{b}]", f"rqf_ptr[{b}]"]
    seq += ["rv", "ov"]
    for b in range(551):
        seq += [f"rd[{b}]", f"od[{b}]"]
    seq += ["fault"]
    assert len(seq) == 1125
    ke = round(((TH - 1124 * 2 * P45) / 2 - T0) / P45)
    for j, n in enumerate(seq):
        p[n] = ("E", "M4", TW, trk(ke + 2 * j))
    assert len(p) == 552 + 1 + 9 + 1125
    return p


def io_tcl(pins, head):
    L = [head]
    for n, (f, lay, x, y) in pins.items():
        size = "{0.024 0.192}" if f in "NS" else "{0.192 0.024}"
        L.append(f"place_pin -pin_name {{{n}}} -layer {lay} -location {{{x:.3f} {y:.3f}}} -pin_size {size} -force_to_die_boundary")
    return "\n".join(L) + "\n"


def tile_spec():
    tp = tile_pins()
    by = {}
    for n, (f, *_r) in tp.items():
        by.setdefault(f, set()).add(n.split("[")[0])
    lint = ("mkdir -p {RUN} && printf '%s\\n' 'module ot_lint_top; ot_qfd_res_slot_tile #(.USE_MACRO(1)) u_top (); endmodule' > "
            "{RUN}/ot_lint_top.sv && verilator --lint-only -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN "
            "-Wno-MODMISSING -DSYNTHESIS --top-module ot_lint_top {RUN}/ot_lint_top.sv rtl/qwen_sys/vm_me_20261008/ot_qfd_res_tiles.sv "
            f"rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv {MACRO}/ot_sram_1r1w_64x512_m1_r2c2_bb.v && echo lint-ok")
    return {
        "name": "qfd_res_slot_ru", "top": "ot_qfd_res_slot_tile", "kind": "tile",
        "sources": ["rtl/qwen_sys/vm_me_20261008/ot_qfd_res_tiles.sv", "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv",
                    f"{MACRO}/ot_sram_1r1w_64x512_m1_r2c2_bb.v"],
        "params": {"USE_MACRO": 1}, "clock_port": "clk", "reset_ports": ["rst_n"],
        "outline": {"w": TW, "h": TH},
        "macros": [{"view": MACRO, "count": 1, "orient": "MY", "at": [22.464, 32.4]}],
        "pins": {"N": sorted(by["N"]), "E": sorted(by["E"])},
        "io_tcl": TILE_IO,
        "route": {"pd": 0.45, "threads": 8, "peak_ram_gb": 8, "hold_margin_ns": 0.03, "macro_halo_um": 5.4},
        "inhold": True,
        "orfs_vars": {"DETAILED_ROUTE_ARGS": "-clean_patches", "OT_MEG_MASTER": "ot_sram_1r1w_64x512_m1_r2c2",
                      "OT_MEG_EXPECT": 1, "OT_MEG_BAND": "2.16", "OT_MEG_EDGES": "EW"},
        "boundary_tcl": ["physical/qwen_coll_cx/macro_edge_m5_guard.tcl"],
        "structural_change": ("pin plan and outline derived from the res_ser cluster floorplan: 216 x 142.56, word + strobes "
                              "on N (exact, 7-track pitch), conveyor in / out interleaved on E, S and W pin-free"),
        "job": {
            "owner": OWNER, "branch": BRANCH, "tag": "u1",
            "extra_paths": ["physical/res_ser", "tools/qwen_vm_me"],
            "purpose": ("Slot tile of the qfd_sp_res_ser cluster (TP8 v4b slot 777.6 x 518.4), drawn from the cluster down "
                        "(tools/qwen_vm_me/res_ser_cluster_fp.py). Same RTL and benches as rh / rs. Outline 216 x 142.56 "
                        "(util <= 58 %); exact pin plan: N = 552-bit word at a 7-track pitch above the macro, strobes / "
                        "reset / strap at the E end, clk mid-face; E = conveyor, rd[k] / od[k] interleaved at 2 tracks; S "
                        "and W pin-free. The closed rs view (259.2 x 172.8) cannot be composed (no channel, abutted "
                        "stubs short); rt (216 x 129.6) failed the in-flow util line (62.6 %)."),
            "benches": [
                {"name": "lint", "cmd": lint, "expect": "pass", "threads": 1, "peak_ram_gb": 4, "needs": ["verilator"]},
                {"name": "fullshape", "cmd": "bash physical/res_tiles/bench.sh {RUN}/bench/pos", "expect": "pass",
                 "pass_regex": "^PASS res_tiles", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "8-slot composition (ot_qfd_res_tiles, USE_MACRO=1) exact against the bench queue incl. the fixed "
                         "19-cycle conveyor latency"},
                {"name": "mutant", "cmd": "bash physical/res_tiles/bench.sh {RUN}/bench/neg 1", "expect": "fail",
                 "fail_regex": "^FAIL res_tiles mutant detected", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "MUT flips one data bit inside slot tile g==1"}]}}


# ------------------------------------------------------------------------------------------------ cluster
def word_bits(g):
    """tile word pin -> index in i[4424:0]"""
    out = {}
    for b in range(512):
        out[f"i_data[{b}]"] = 329 + g * 512 + b
    for b in range(16):
        out[f"i_mask[{b}]"] = 201 + g * 16 + b
    for b in range(24):
        out[f"i_addr[{b}]"] = 9 + g * 24 + b
    return out


def plan(dx_my=0.0):
    """dx_my: x shift of a MY child's origin that puts its mirrored M5 pins back on track (from ref_tile gen)"""
    tp = tile_pins()

    def org(c):
        return round(COLX[c] + (dx_my if ORIENT[c] == "MY" else 0.0), 3)

    def pabs(g, n):
        c, r = RING[g]
        x, y = tp[n][2], tp[n][3]
        if ORIENT[c] == "MY":
            x = TW - x
        return round(org(c) + x, 3), round(ROWY[r] + y, 3)

    pins = {}
    used = []

    def take(x):
        xs = snap(x)
        while any(abs(xs - u) < 2 * P45 - 1e-9 for u in used[-40:]):
            xs = round(xs + P45, 3)
        used.append(xs)
        return xs

    # control pins first (contract offsets), with a clear window around them
    ctl = [(CK_X, "ck"), (RST_X, "rst_n"), (ME_X, "me_en")] + [(397.5 + 0.96 * k, f"i[{k}]") for k in range(9)]
    cw = (min(x for x, _ in ctl) - 0.5, max(x for x, _ in ctl) + 0.5)
    for x, n in ctl:
        pins[n] = ("N", "M5", snap(x), H)
    ipin = {}
    for c in range(3):
        want = []
        for g, (cc, r) in enumerate(RING):
            if cc != c:
                continue
            for tn, bit in word_bits(g).items():
                px = pabs(g, tn)[0]
                want.append((px + (2 - r) * 2 * P45, r, f"i[{bit}]", g, tn))     # rows interleaved 2 tracks apart
        want.sort()
        used.clear()
        for xw, r, dn, g, tn in want:
            if cw[0] - 2 * P45 < xw < cw[1]:
                xw = max(xw, cw[1])
            xs = take(max(xw, used[-1] + 2 * P45) if used else xw)
            if cw[0] - 2 * P45 < xs < cw[1]:
                used.pop()
                xs = take(cw[1])
            pins[dn] = ("N", "M5", xs, H)
            ipin[dn] = (xs, g, tn)
    # E face: o beside the head (4-track pitch), then ok, cr, fault
    y0 = ROWY[1] + 12.0
    for b in range(551):
        pins[f"o[{b}]"] = ("E", "M4", W, snap(y0 + b * 4 * P45))
    ye = snap(y0 + 551 * 4 * P45 + 1.0)
    for k, n in enumerate(("ok", "cr", "fault")):
        pins[n] = ("E", "M4", W, trk(round((ye - T0) / P45) + 20 * k))
    need = {f"i[{b}]" for b in range(4425)} | {f"o[{b}]" for b in range(551)} | {"ck", "rst_n", "me_en", "ok", "cr", "fault"}
    assert set(pins) == need, (len(pins), len(need))
    nx = sorted(v[2] for v in pins.values() if v[0] == "N")
    assert min(b - a for a, b in zip(nx, nx[1:])) >= 2 * P45 - 1e-9, "N pins closer than 2 tracks"

    # ---- hops (flop to flop).  A = flop at the die pin (anchored); rows 1, 2: A drives the tile pin flop directly;
    # row 0: A -> M (free) -> X (anchored at the tile pin) -> tile pin flop.
    worst = {}

    def hop(k, bits, um):
        a = worst.setdefault(k, [bits, 0.0])
        a[1] = max(a[1], um)

    ya = H - 3.0
    for dn, (xs, g, tn) in ipin.items():
        c, r = RING[g]
        px, py = pabs(g, tn)
        d = abs(xs - px) + (ya - py)
        if r == 0:
            hop("word A -> M -> X at the tile pin (row 0): whole path, two hops", 3 * 552, d)
        else:
            hop(f"word A -> tile pin flop (row {r})", 3 * 552 if r == 2 else 3 * 552, d)
    cx = pins["me_en"][2]
    for g, (c, r) in enumerate(RING):
        for n in ("me_en", "i_ov", "i_we", "i_last", "i_empty"):
            px, py = pabs(g, n)
            d = abs(cx - px) + (ya - py)
            if r == 0:
                hop("strobes / we A (centre) -> M -> X at the tile pin (row 0): whole path, two hops", 15, d)
            else:
                hop(f"strobes / we A (centre) -> tile pin flop (row {r})", 15, d)
    hx0, hx1, hy0, hy1 = org(2) - 12.0, W - 2.16, ROWY[1], ROWY[1] + TH

    def near(p):
        return min(max(p[0], hx0), hx1), min(max(p[1], hy0), hy1)

    hop("strobes A (centre) -> head pe / po", 2, abs(cx - hx0) + (ya - hy1) + 10.0)
    pair = [("rqf_v", "rq_v")] + [(f"rqf_slot[{b}]", f"rq_slot[{b}]") for b in range(3)] \
        + [(f"rqf_ptr[{b}]", f"rq_ptr[{b}]") for b in range(6)] + [("ov", "rv")] + [(f"od[{b}]", f"rd[{b}]") for b in range(551)]
    chain = []
    for g in range(8):
        dmax = 0.0
        for po, pi in pair:
            b = pabs(g, pi)
            if g == 0:
                if pi.startswith("rd") or pi == "rv":
                    continue                      # tied low at slot 0
                a = near(b)
            else:
                a = pabs(g - 1, po)
            dmax = max(dmax, abs(a[0] - b[0]) + abs(a[1] - b[1]))
        over = None
        if g:
            xa, xb = pabs(g - 1, "ov")[0], pabs(g, "rv")[0]
            for c in range(3):                    # a tile body between the two faces
                if min(xa, xb) < org(c) + 1.0 and org(c) + TW - 1.0 < max(xa, xb):
                    over = [c, RING[g][1]]
        chain.append({"hop": f"{'head' if g == 0 else 'slot %d' % (g - 1)} -> slot {g}", "bits": 10 if g == 0 else 563,
                      "um": round(dmax, 1), "over_tile": over})
    dmax = 0.0
    for po, pi in pair:
        a = pabs(7, po)
        b = near(a)
        dmax = max(dmax, abs(a[0] - b[0]) + abs(a[1] - b[1]))
    chain.append({"hop": "slot 7 -> head (rd capture)", "bits": 552, "um": round(dmax, 1), "over_tile": None})
    oy = [v[3] for n, v in pins.items() if n.startswith("o[")]
    chain.append({"hop": "head rd capture (SW corner) -> o pin flops at E", "bits": 551,
                  "um": round((hx1 - hx0) + (max(oy) - hy0) * 0.5, 1), "over_tile": None})
    # ---- cuts
    cuts = []
    PG7, PG6 = 0.85, 0.90                    # track share left by the M7 PG stripes / M6 child straps (estimate)
    gapw = [COLX[1] - COLX[0] - TW, COLX[2] - COLX[1] - TW, W - COLX[2] - TW]
    span = 551 * 7 * P45                     # word pin span on the tile's N face
    for r in (2, 1):
        for c in range(3):
            if (c, r) == HEAD:
                continue
            below = sum(552 for (cc, rr) in RING if cc == c and rr < r)
            if not below:
                continue
            m7 = span / P67 * PG7
            cuts.append({"cut": f"y through tile ({c},{r}): words of the rows below, straight over the tile", "bits": below,
                         "tracks": int(m7), "ratio": round(below / m7, 3),
                         "basis": f"M7 over the tile's own word span ({span:.1f} um), {int(PG7 * 100)} % usable"})
    over_n = {}
    for h in chain:
        if h["over_tile"]:
            over_n.setdefault(tuple(h["over_tile"]), []).append(h)
    for (c, r), hs in over_n.items():
        bits = sum(h["bits"] for h in hs)
        m6 = TH / P67 * PG6
        cuts.append({"cut": f"x through tile ({c},{r}): {' + '.join(h['hop'] for h in hs)} on M6 over the tile", "bits": bits,
                     "tracks": int(m6), "ratio": round(bits / m6, 3), "basis": f"M6 over one tile row, {int(PG6 * 100)} % usable"})
    for gi, (xl, xr) in enumerate(((COLX[0] + TW, COLX[1]), (COLX[1] + TW, COLX[2]))):
        for rb in (1, 2):
            bits = 0
            for g in range(1, 8):
                xa, xb = pabs(g - 1, "ov")[0], pabs(g, "rv")[0]
                ra, rbw = RING[g - 1][1], RING[g][1]
                if xl - 1 <= xa <= xr + 1 and xl - 1 <= xb <= xr + 1 and min(ra, rbw) < rb <= max(ra, rbw):
                    bits += 563
            tr = (xr - xl) * (1 / 0.036 + 1 / P45) * 0.8
            cuts.append({"cut": f"y = row {rb - 1}/{rb} boundary in the gap x {xl:.2f}..{xr:.2f}: conveyor hops", "bits": bits,
                         "tracks": int(tr), "ratio": round(bits / tr, 3), "basis": "M3 + M5 in the gap, 80 % usable"})
    # row gap: the 561 N pins of the tile below are reached from above (M7 -> M5 stub); row-0 X flops live here too
    win = {}
    for v in pins.values():
        if v[0] == "N":
            win[int(v[2] // 100)] = win.get(int(v[2] // 100), 0) + 1
    dens = {"cluster_N_M5_max_b_per_um_100um": max(win.values()) / 100.0,
            "cluster_E_M4_b_per_um": round(554 / (max(oy) - min(oy) + 3.0), 2),
            "tile_N_M5_b_per_um": round(562 / TW, 2), "tile_E_M4_b_per_um_100um": round(100 / (2 * P45) / 100.0, 2)}
    single = [v[1] for k, v in worst.items() if "two hops" not in k] + [h["um"] for h in chain]
    paths = [v[1] for k, v in worst.items() if "two hops" in k]
    # tile input pins a parent flop drives: the row-0 X stage (word, strobes), the reset relay leaf, the head's rq
    mp = sorted(n for n, v in tp.items() if v[0] == "N" and n != "clk" and not n.startswith("slot_id")) \
        + ["rq_v"] + [f"rq_slot[{b}]" for b in range(3)] + [f"rq_ptr[{b}]" for b in range(6)]
    flops = {"A (die pins)": 4426, "M + X (row 0: 3 tiles x 557 x 2)": 3342, "head (ctl, rd capture 552, o 551)": 1160,
             "reset relay + fault ring": 31}
    fp = {"schema": "opentallas.qwen.res_ser_cluster_fp.v2", "outline_um": [W, H], "tile_um": [TW, TH],
          "col_x": [org(c) for c in range(3)], "row_y": ROWY, "orient": ORIENT, "ring": RING, "head_cell": HEAD,
          "ninth_cell": "column 2 row 1 = serialiser head (ot_qfd_res_tiles_ctl, o / ok / cr / fault pin flops)",
          "hops_um": {k: {"bits": v[0], "max_um": round(v[1], 1)} for k, v in worst.items()},
          "chain_hops": chain, "cuts": cuts, "pin_density": dens, "parent_flops_estimate": flops,
          "parent_flops_total_estimate": sum(flops.values()),
          "max_hop_um": round(max(single), 1), "max_path_two_hops_um": round(max(paths), 1),
          "max_cut": max(c["ratio"] for c in cuts)}
    return fp, pins, mp


def cluster_spec(fp, mp):
    ch = [{"view": VIEW, "count": 1, "inst": f"g_slot[{g}].u_t", "at": [COLX[c], ROWY[r]], "orient": ORIENT[c]}
          for g, (c, r) in enumerate(RING)]
    bench = "bash physical/res_ser/bench.sh {RUN}/bench/"
    return {
        "name": "qfd_sp_res_ser", "top": "qfd_sp_res_ser", "kind": "cluster",
        "sources": ["rtl/qwen_sys/vm_me_20261008/qfd_sp_res_ser.sv", "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_tiles.sv",
                    "rtl/qwen_sys/vm_me_20261008/ot_qfd_res_path.sv", "rtl/lib/ot_rst_relay.sv",
                    f"{MACRO}/ot_sram_1r1w_64x512_m1_r2c2_bb.v"],
        "params": {}, "defines": ["OT_HARD_CHILDREN"], "hard_define": "OT_HARD_CHILDREN",
        "clock_port": "ck", "reset_ports": ["rst_n"],
        "contract": {"file": CONTRACT, "slot": "sp_res_ser_0"},
        "child_lattice_um": 2.16,
        "children": ch,
        "pins": {"N": ["i", "me_en", "rst_n", "ck"], "E": ["o", "ok", "cr", "fault"]},
        "io_tcl": CL_IO,
        "io_flop_at_pins": {"cols": 12},
        "route": {"pd": 0.45, "threads": 16, "peak_ram_gb": 48, "hold_margin_ns": 0.03},
        # the flop that drives a tile input pin (row-0 X stage, reset relay leaf, head rq) is anchored at that pin
        "orfs_vars": {"OT_MPFLOP_PINS": ",".join(mp), "OT_MPFLOP_GAP": "2.7"},
        "slot_change_request": (
            "el1013-qwen-elements-r6 10-13: outline, faces, layers and the ck / rst_n / me_en offsets (388.8 / 392 / 396) "
            "as contract v4b. PIN SPANS re-planned (the v4b spans put 4,425 i pins on every M5 track over 212 um = 20.8 "
            "b/um and 551 o pins over 26 um, above the 12 b/um/layer limit): i[4424:0] on N M5 over x 32..750, each slot "
            "word directly above its tile (<= 9 b/um); o[550:0], ok, cr, fault on E M4 over y 200..310 beside the head "
            "cell (5 b/um). SUB-LAYOUT inside the unchanged slot: 8 tiles of 216 x 142.56 (kit qfd_res_slot_ru) on a "
            "3 x 3 grid WITH channels, columns 1 and 2 mirrored (MY), head in cell (2,1); the 259.2 x 172.8 rs tiles "
            "cannot abut (W/E stubs short or corner-touch). Packing: i = {i_data 4096, i_mask 128, i_addr 192, i_we 8, "
            "i_ov} (i_ov = i[0]); o = {o_v, o_end, o_nul, o_row 20, o_mask 16, o_data 512} (o_v = o[550]); 1-bit pins "
            "are scalars. +1 capture cycle at the head (RS + 1 inside; v4b allowed +2); reset release 4 ck edges after "
            "the pin."),
        "job": {
            "owner": OWNER, "branch": BRANCH, "tag": "c1",
            "purpose": ("Qwen ROM TP8 contract v4b slot cell qfd_sp_res_ser (3 instances sp_res_ser_0..2, 777.6 x 518.4): "
                        "hardened cluster under the die master name. 8 hard slot tiles (qfd_res_slot_ru) + the serialiser "
                        "head in the ninth cell; parent = one flop at every die pin, two more stages for the row-0 "
                        "tiles, reset relay, wires. Clock: balanced spine with each tile's routed insertion as its leaf "
                        "target; every seam registered on both sides. Floorplan, hops and cuts: "
                        "physical/res_ser/qfd_sp_res_ser_fp.json (tools/qwen_vm_me/res_ser_cluster_fp.py)."),
            "extra_paths": ["physical/res_ser", "rtl/test/res_ser", "rtl/test/res_tiles", "physical/res_tiles", MACRO,
                            "tools/qwen_vm_me"],
            "benches": [
                {"name": "res_ser_exact", "cmd": bench + "pos", "expect": "pass", "pass_regex": "^PASS res_ser",
                 "min_count_regex": "beats=(\\d+)", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "the assembled cluster (8 tiles USE_MACRO=1 + head + pin / row-0 stages + reset relay) through "
                         "the die ports: 360 bursts / 1,465 beats exact, conveyor latency 19, 42-edge stopping debt, "
                         "coverage floors"},
                {"name": "res_ser_mutant_tile", "cmd": bench + "neg1 1", "expect": "fail",
                 "fail_regex": "^FAIL res_ser mutant detected", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "MUT 1: one data bit of slot 1 inverted inside the tile"},
                {"name": "res_ser_mutant_seam", "cmd": bench + "neg2 2", "expect": "fail",
                 "fail_regex": "^FAIL res_ser mutant detected", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "MUT 2: the row-0 tiles' strobes bypass the X stage (word one cycle behind its strobe)"},
                {"name": "res_ser_coverage_refusal", "cmd": bench + "cov 0 0 40", "expect": "fail",
                 "fail_regex": "^COVERAGE_REFUSED", "threads": 8, "peak_ram_gb": 4, "needs": ["verilator"],
                 "note": "40-burst control: every beat exact but the floors are not reached, the bench must refuse"}]}}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=("tile", "cluster"))
    ap.add_argument("--dx-my", type=float, default=0.0, help="x shift of the MY children (on-track origin from gen)")
    ap.add_argument("--out", default=str(ROOT), help="repo root to write into")
    a = ap.parse_args(argv)
    out = Path(a.out)
    (out / "physical/res_ser").mkdir(parents=True, exist_ok=True)
    if a.what == "tile":
        tp = tile_pins()
        (out / TILE_IO).write_text(io_tcl(tp, "# qfd_res_slot_ru exact pin plan, generated by tools/qwen_vm_me/"
                                           "res_ser_cluster_fp.py tile -- do not edit"))
        (out / "tools/ref_tile/specs_qsp/qfd_res_slot_ru.json").write_text(json.dumps(tile_spec(), indent=1) + "\n")
        e = sorted(v[3] for v in tp.values() if v[0] == "E")
        n = sorted(v[2] for v in tp.values() if v[0] == "N")
        print(f"res_slot_ru pin plan: {len(tp)} pins; N {len(n)} x {n[0]}..{n[-1]}; E {len(e)} y {e[0]}..{e[-1]}")
        return 0
    fp, pins, mp = plan(a.dx_my)
    (out / "physical/res_ser/qfd_sp_res_ser_fp.json").write_text(json.dumps(fp, indent=1) + "\n")
    (out / "tools/ref_tile/specs_qsp/qfd_sp_res_ser.json").write_text(json.dumps(cluster_spec(fp, mp), indent=1) + "\n")
    (out / CL_IO).write_text(io_tcl(pins, "# qfd_sp_res_ser exact pin plan, generated by tools/qwen_vm_me/"
                                          "res_ser_cluster_fp.py cluster -- do not edit"))
    print(f"res_ser cluster fp: {len(pins)} pins, max single hop {fp['max_hop_um']} um, longest two-hop path "
          f"{fp['max_path_two_hops_um']} um, max cut {fp['max_cut']}, parent flops ~{fp['parent_flops_total_estimate']}, "
          f"pin density {fp['pin_density']}")
    for k, v in fp["hops_um"].items():
        print(f"  hop {k}: {v['bits']} b, <= {v['max_um']} um")
    for h in fp["chain_hops"]:
        print(f"  chain {h['hop']}: {h['bits']} b, {h['um']} um" + (f", over tile {h['over_tile']}" if h["over_tile"] else ""))
    for c in fp["cuts"]:
        print(f"  cut {c['cut']}: {c['bits']} / {c['tracks']} = {c['ratio']}")
    return 0 if fp["max_hop_um"] <= 500.0 and fp["max_path_two_hops_um"] <= 1000.0 and fp["max_cut"] <= 0.60 else 1


if __name__ == "__main__":
    sys.exit(main())
