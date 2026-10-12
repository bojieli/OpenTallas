#!/usr/bin/env python3
"""Physical hierarchy of the DS HBM SM element ot_hbm_accel_smh (rtl/hbm_accel/sm/ot_hbm_accel_smh.sv) at 1.2 GHz.

Writes ORFS work directories (config.mk, constraint.sdc, exact pin placement, macro placement) for the hardened pieces
and the element top, and a run.sh that routes, extracts the abstract (LEF + SS/FF timing models) and runs the
sign-off corner STA (tools/w18/corner_sta.py: SS setup / FF hold, 60 / 25 ps, never relaxed).

Pieces (production configuration SUB 4, NC 8, RPT 2, RMAX 4096):
  tile  ot_hbm_accel_smh_tile   two leaves of one column; variants toE (right of the front: row bundles enter west,
                                leave east) and toW (left of the front); identical netlist, mirrored pin sides
  be    ot_hbm_accel_smh_be     column back end; variants toE (left columns: results leave east, toward the front)
                                and toW
  front ot_hbm_accel_smh_front  pins, channels, bulk copy, issue, distribution, result deskew
  top   ot_hbm_accel_smh        abutment only: 16 tiles, 8 back ends, the front; tie cells for the straps

Every abutting pin pair sits on the same track at the same offset in both pieces, so the parent wire is a straight
hop across the channel.  Block constraints: the element clock with 60 / 25 ps; abutting ports budgeted against a
virtual clock carrying the neighbour's clock insertion (--lat): 300 ps outside on each side, so every port lands
in / leaves a flop with its wire inside the block; the element top carries the W13 die budget
(rtl/hbm_accel/sm/ot_hbm_accel_sm_v_die_budget.sdc) unchanged on its own pins.

    python3 tools/hbm_accel_smh_physical.py block --piece tile --variant toE --out DIR [--util ...]
    python3 tools/hbm_accel_smh_physical.py top --views VIEWDIR --out DIR
"""
from __future__ import annotations

import os

import argparse
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRAM_X = "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2"
SRAM_R = "physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2"
RTL = ["rtl/hdc/ot_hdc_prefix.sv", "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_bterm2.sv", "rtl/gpu/ot_gpu_fadd.sv",
       "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
       "rtl/gpu/ot_gpu_tree.sv", "rtl/gpu/ot_gpu_issue.sv", "rtl/gpu/ot_gpu_stack.sv", "rtl/gpu/ot_gpu_tc_col.sv",
       "rtl/gpu/ot_gpu_bd_col.sv", "rtl/hdc/v41/ot_hdc_blockdot.sv", "rtl/gpu/ot_gpu_bulk_copy.sv",
       "rtl/hdc/ot_hdc_fpu.sv", "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
       "rtl/hdc/ot_hdc_sfu.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_issue.sv",
       "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq4.sv", "rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy_oq5.sv",
       "rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv",
       "rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv", "rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv",
       "rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv", "rtl/hbm_accel/sm/ot_hbm_accel_stack.sv",
       "rtl/hbm_accel/sm/ot_hbm_accel_smh_bd.sv", "rtl/hbm_accel/sm/ot_hbm_accel_smh.sv",
       SRAM_X + "/ot_sram_1r1w_128x256_m1_r2c2_bb.v", SRAM_R + "/ot_sram_1r1w_512x256_m1_r2c2_bb.v", "rtl/lib/ot_hdly.sv"]
GRID = 8.64          # macro / die quantum: a multiple of every routing pitch (0.048 0.064 0.08) and the 0.27 row
PITCH = 0.096        # abutting pin slot (two M4 / M5 tracks)
# production geometry (um)
P = dict(SUB=4, RPT=2, NC=8, LBS=2, LSB=16, RW=12, SW=3, XW=7, NBEAT=13)
P["TAGW"] = P["RW"] + 1 + P["SW"]
P["CW"] = 6 + P["TAGW"]
P["WSW"] = P["LBS"] * 266 + P["LSB"] * 16
P["RBW"] = P["CW"] + P["WSW"] + 1 + P["XW"]
P["BBW"] = 1 + P["XW"] + P["NBEAT"] + 2048
P["GLW"] = 2 + 32 + P["TAGW"]
P["QLW"] = 2 + 32 + P["RW"]
P["NP"] = P["SUB"] // P["RPT"]
P["NH"] = P["NC"] // 2
P["A1B"], P["A2B"] = 9, 7


def q(v):
    return round(math.ceil(v / GRID - 1e-9) * GRID, 3)


def qd(v):
    return round(math.floor(v / GRID + 1e-9) * GRID, 3)


def bits(name, n):
    return [f"{name}[{i}]" for i in range(n)]


# ---------------- pin slot tables (offsets from the piece's origin) ----------------
def tile_edge_slots(h):
    """y of every row-bundle / x-write slot on the E/W edges, top to bottom: row j=0 bundle, x-write, row j=1."""
    n = P["RPT"] * P["RBW"] + P["BBW"]
    y0 = round((h - n * PITCH) / 2 / 0.048) * 0.048 + 0.012
    ys = [round(y0 + (n - 1 - k) * PITCH, 3) for k in range(n)]
    slots, k = [], 0
    for j in range(P["RPT"]):
        if j == 1:
            for i in range(P["BBW"]):
                slots.append((("b", i), ys[k])); k += 1
        for i in range(P["RBW"]):
            slots.append((("r", j * P["RBW"] + i), ys[k])); k += 1
    if P["RPT"] == 1:
        for i in range(P["BBW"]):
            slots.append((("b", i), ys[k])); k += 1
    return dict(slots)


def lane_slots(w, nl, lw, spacing=0.48):
    """x of gather-lane bit (lane, i) on the N/S edges: lanes side by side, centred."""
    n = nl * lw
    x0 = round((w - n * spacing) / 2 / 0.048) * 0.048 + 0.012
    return {(ln, i): round(x0 + (ln * lw + i) * spacing, 3) for ln in range(nl) for i in range(lw)}


def be_edge_slots(h, nl, lw):
    n = nl * lw
    y0 = round((h - n * PITCH) / 2 / 0.048) * 0.048 + 0.012
    return {(ln, i): round(y0 + (ln * lw + i) * PITCH, 3) for ln in range(nl) for i in range(lw)}


def pin_tcl(pins):
    """pins: [(name, layer, edge, coord, w, h)] -> place_pin commands (location = pin centre on the boundary)."""
    out = ["# exact pin placement (tools/hbm_accel_smh_physical.py): abutting pins share a track"]
    for name, layer, edge, x, y in pins:
        sz = "0.192 0.024" if layer in ("M4", "M6") else "0.024 0.192"
        out.append(f"place_pin -pin_name {{{name}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} "
                   f"-force_to_die_boundary")
    return "\n".join(out) + "\n"


def tile_pins(w, h, variant, cg=False):
    ys = tile_edge_slots(h)
    xin, xout = (0.0, w) if variant == "toE" else (w, 0.0)
    pins = []
    for (kind, i), y in ys.items():
        nin, nout = (f"rin[{i}]", f"rout[{i}]") if kind == "r" else (f"bin[{i}]", f"bout[{i}]")
        pins.append((nin, "M4", "", xin, y))
        pins.append((nout, "M4", "", xout, y))
    gx = lane_slots(w, P["SUB"], P["GLW"])
    for (ln, i), x in gx.items():
        pins.append((f"gout[{ln * P['GLW'] + i}]", "M5", "", x, 0.0))
        if ln < P["SUB"] - P["RPT"]:
            pins.append((f"gin[{ln * P['GLW'] + i}]", "M5", "", x, h))
    # straps, clock, reset on the north edge, clear of the lanes
    xs = sorted(gx.values())
    k = 0
    others = (bits("xs_a1", P["RPT"] * P["A1B"]) + bits("xs_g1", P["RPT"] * 5) + bits("xs_a2", P["RPT"] * P["A2B"])
              + bits("xs_g2", P["RPT"] * 5) + ["rst_n"] + (["cgi", "cgo"] if cg else []))
    xo = round(xs[-1] + 2.0, 3)
    for nme in others:
        pins.append((nme, "M5", "", round(xo + k * 0.48, 3), h)); k += 1
    pins.append(("clk", "M5", "", round(xs[0] - 4.008, 3), h))
    return pins


def be_pins(w, h, variant, cg=False):
    gx = lane_slots(w, P["SUB"], P["GLW"])
    pins = [(f"gin[{ln * P['GLW'] + i}]", "M5", "", x, h) for (ln, i), x in gx.items()]
    ys = be_edge_slots(h, P["NH"], P["QLW"])
    xin, xout = (0.0, w) if variant == "toE" else (w, 0.0)
    for (ln, i), y in ys.items():
        pins.append((f"qout[{ln * P['QLW'] + i}]", "M4", "", xout, y))
        if ln < P["NH"] - 1:
            pins.append((f"qin[{ln * P['QLW'] + i}]", "M4", "", xin, y))
    xs = sorted(gx.values())
    pins.append(("rst_n", "M5", "", round(xs[-1] + 2.0, 3), h))
    if cg:                                          # redesign-hbm --cg: the wake pins beside rst_n
        pins.append(("cgi", "M5", "", round(xs[-1] + 2.48, 3), h))
        pins.append(("cgo", "M5", "", round(xs[-1] + 2.96, 3), h))
    pins.append(("clk", "M5", "", round(xs[0] - 4.008, 3), h))
    return pins


# ---------------- element floorplan ----------------
def floorplan(g):
    """Positions of every piece in the element (origin = core lower-left), from the piece sizes."""
    tw, th, bh, fw, gap, m = g["tile_w"], g["tile_h"], g["be_h"], g["front_w"], g["gap"], g["margin"]
    bw = g.get("be_w", tw)
    if not (0 < bw <= tw):
        raise ValueError("backend width must fit the tile column")
    nl = P["NC"] // 2
    fx = m + nl * (tw + gap)
    pos = {}
    for c in range(P["NC"]):
        x = m + c * (tw + gap) if c < nl else fx + fw + gap + (c - nl) * (tw + gap)
        # Optional area fallback: preserve the real backend master width and
        # center its gather pins under the wider tile's centered lane field.
        pos[("be", c)] = (x if bw == tw else round(x + (tw - bw) / 2, 3), m)
        for p in range(P["NP"]):
            # tile p = 0 on top
            pos[("tile", c, p)] = (x, m + bh + gap + (P["NP"] - 1 - p) * (th + gap))
    hcore = bh + gap + P["NP"] * (th + gap) - gap
    pos["front"] = (fx, m)
    die = (round(2 * m + P["NC"] * tw + P["NC"] * gap + fw, 3), round(2 * m + hcore, 3))
    return pos, die, hcore


def front_pins(g, hcore):
    """The front's pins: tile-facing edges aligned with the tiles / back ends; element pins on N / S."""
    tw, th, bh, fw, gap = g["tile_w"], g["tile_h"], g["be_h"], g["front_w"], g["gap"]
    ys = tile_edge_slots(th)
    pins = []
    for side, xedge, suffix in (("l", 0.0, "_l"), ("r", fw, "_r")):
        for p in range(P["NP"]):
            ty = bh + gap + (P["NP"] - 1 - p) * (th + gap)
            for (kind, i), y in ys.items():
                if kind == "r":
                    nm = f"rout{suffix}[{p * P['RPT'] * P['RBW'] + i}]"
                else:
                    nm = f"bout{suffix}[{p * P['BBW'] + i}]"
                pins.append((nm, "M4", "", xedge, round(ty + y, 3)))
        qy = be_edge_slots(bh, P["NH"], P["QLW"])
        for (ln, i), y in qy.items():
            pins.append((f"qin{suffix}[{ln * P['QLW'] + i}]", "M4", "", xedge, y))
    # element pins: north = x-write, op channel, barrier; south = NoC, results
    # the clock enters on the west edge in the channel between the two tile rows (near mid-height: the tree root
    # is mid-block, so the pin-to-root wire is short); the element top routes it there through the channel
    ygap = round(bh + gap + (P["NP"] - 1) * (th + gap) - gap / 2, 3)
    pins.append(("clk", "M4", "", 0.0, round(round((ygap - 0.012) / 0.048) * 0.048 + 0.012, 3)))
    north = (["rst_n", "start", "start_ready", "busy", "arrive", "release_in", "released", "xw_en"]
             + bits("op_rows", P["RW"] + 1) + bits("op_c", 16) + bits("op_g", 8) + ["op_gs"] + bits("op_fmt", 2)
             + bits("op_xb", P["XW"]) + bits("xw_addr", P["XW"]) + bits("xw_grp", 7) + bits("xw_data", 2048))
    south = (["d_valid", "d_ready", "req_v", "req_ready", "rsp_v", "rv", "fault"] + bits("d_base", 32)
             + bits("d_lines", 24) + bits("req_addr", 32) + bits("req_tag", 10) + bits("rsp_tag", 10)
             + bits("rsp_data", 1088) + bits("rrow", P["RW"]) + bits("rdata", P["NC"] * 32))
    for names, y in ((north, hcore), (south, 0.0)):
        sp = min(0.096, (fw - 4.0) / len(names))
        sp = math.floor(sp / 0.048) * 0.048
        x0 = round((fw - len(names) * sp) / 2 / 0.048) * 0.048 + 0.012
        for k, nm in enumerate(names):
            pins.append((nm, "M5", "", round(x0 + k * sp, 3), y))
    return pins


# ---------------- (margin m3) the front as three strips ----------------
STRIPS = ("front_s", "front_c", "front_n")      # south to north


def strip_cuts(g):
    """The two strip cuts (front coordinates, on the 8.64 um grid): between the lowest row bundle of a tile row (its
    leaf 1) and that tile row's x-write bundle, so every bundle's pins stay in one strip.  front_s holds tile row 1's
    leaf-1 bundle and the result lanes, front_c tile row 1's x write and leaf 0, tile row 0's leaf 1, front_n tile row 0's
    x write and leaf 0."""
    th, bh, gap = g["tile_h"], g["be_h"], g["gap"]
    n = P["RPT"] * P["RBW"] + P["BBW"]
    y0 = round((th - n * PITCH) / 2 / 0.048) * 0.048 + 0.012
    cuts = []
    for p in (P["NP"] - 1, 0):
        ty = bh + gap + (P["NP"] - 1 - p) * (th + gap)
        row_top = ty + y0 + (P["RBW"] - 1) * PITCH
        b_bot = ty + y0 + P["RBW"] * PITCH
        c = qd(b_bot)
        assert row_top + 0.02 < c < b_bot - 0.02, (row_top, c, b_bot)
        cuts.append(round(c, 3))
    return cuts


def strip_span(g, hcore, strip):
    cs, cn = strip_cuts(g)
    return {"front_s": (0.0, cs), "front_c": (cs, cn), "front_n": (cn, hcore)}[strip]


def face_ports(strip, side):
    """Face port names in pin order; side 'n' = the strip's north face, 's' = its south face."""
    opx = (P["RW"] + 1) + 16 + 8 + 1 + 2 + P["XW"]
    if (strip, side) in (("front_n", "s"), ("front_c", "n")):
        r0, pz = ("fi_row0", "fi_pbz") if strip == "front_n" else ("fo_row0", "fo_pbz")
        return (["fs_v"] + bits("fs_d", opx) + ["fs_ret"] + bits("fx_b", P["BBW"]) + ["fr_rl"] + bits(r0, P["RBW"])
                + bits(pz, 3))
    if (strip, side) in (("front_c", "s"), ("front_s", "n")):
        r3 = "fo_row3" if strip == "front_c" else "fi_row3"
        return (["fd_v"] + bits("fd_d", 56) + ["fd_ret", "fq_v"] + bits("fq_d", 42) + ["fq_ret", "fp_v"]
                + bits("fp_d", 1098) + ["fsv"] + bits(r3, P["RBW"]))
    return []


def trk(y):
    return round(round((y - 0.012) / 0.048) * 0.048 + 0.012, 3)


def strip_pins(g, hcore, strip):
    """A strip's pins: its share of the front's W / E tile-facing pins (renamed per bundle), its element pins (N for
    front_n, S for front_s), the face pins (same x on both sides of a face), clk / rst_n on the W edge in the widest gap."""
    lo, hi = strip_span(g, hcore, strip)
    h = round(hi - lo, 3)
    fw = g["front_w"]
    pins, wy = [], []
    for name, layer, _, x, y in front_pins(g, hcore):
        if name == "clk":
            continue
        if layer == "M4":
            if not (lo < y < hi):
                continue
            m = re.match(r"(rout|bout)_(l|r)\[(\d+)\]", name)
            if m:
                k, sd, i = m.group(1), m.group(2), int(m.group(3))
                wdt = P["RBW"] if k == "rout" else P["BBW"]
                name = f"{k}_{sd}{i // wdt}[{i % wdt}]"
            pins.append((name, layer, "", x, round(y - lo, 3)))
            if x == 0.0:
                wy.append(y - lo)
        else:
            if strip == "front_n" and y > 0:
                pins.append((name, layer, "", x, h))
            elif strip == "front_s" and y == 0.0:
                pins.append((name, layer, "", x, 0.0))
    for side, y in (("n", h), ("s", 0.0)):
        names = face_ports(strip, side)
        if not names:
            continue
        fx = fc_face_x(g, strip, side, names)
        if fx:
            pins += [(nm, "M5", "", fx[nm], y) for nm in names]
            continue
        sp = math.floor(min(0.096, (fw - 4.0) / len(names)) / 0.048) * 0.048
        x0 = round((fw - len(names) * sp) / 2 / 0.048) * 0.048 + 0.012
        for k, nm in enumerate(names):
            pins.append((nm, "M5", "", round(x0 + k * sp, 3), y))
    # clk (and rst_n, when the strip has no north element row) mid-way in the widest W-edge gap
    ys = sorted([0.0] + wy + [h])
    a, b = max(zip(ys, ys[1:]), key=lambda t: t[1] - t[0])
    if g.get("fc_hier") and strip == "front_c":
        a = b = 760.0          # hbm-smh/fc: the open W-side region between fc_xr (top 669.6) and fc_t (872.64)
    pins.append(("clk", "M4", "", 0.0, trk((a + b) / 2)))
    if strip != "front_n":
        pins.append(("rst_n", "M4", "", 0.0, trk((a + b) / 2 + 4.8)))
    return pins, h


def sdc_strip(strip, lat, lat_ff=None, period=833, skew=0, die_skew=150, hold_io=50):
    """Strip constraints: element pins carry the die budget (as the m2 front), face and tile-facing ports the abutting
    budget (300 ps outside + the intra-element skew), the ring multicycle on front_c."""
    elem = {"front_n": ("start op_* xw_* release_in", "start_ready busy arrive released"),
            "front_s": ("d_valid d_base* d_lines* req_ready rsp_*", "d_ready req_v req_addr* req_tag* rv rrow* rdata* fault"),
            "front_c": ("", "")}[strip]
    nbr = {"front_n": ("fs_ret fi_*", "rout_* bout_* fs_v fs_d* fx_b* fr_rl"),
           "front_c": ("fs_v fs_d* fx_b* fr_rl fd_v fd_d* fq_ret fp_* fsv", "rout_* bout_* fs_ret fo_* fd_ret fq_v fq_d*"),
           "front_s": ("qin_* fd_ret fq_v fq_d* fi_*", "rout_* fd_v fd_d* fq_ret fp_* fsv")}[strip]
    base = sdc_block(lat, element_io=False, ring=(strip == "front_c"), nbr_in=nbr[0], lat_ff=lat_ff, period=period,
                     skew=skew, die_skew=die_skew, hold_io=hold_io)
    base = base.replace("set nbr_out [all_outputs]", f"set nbr_out [get_ports {{{nbr[1]}}}]")
    if elem[0]:
        add = ["# element pins: the W13 die budget magnitudes (473 / 323 external, 20 % min) plus the die term, referenced",
               "# like every port to the block's own clock insertion (nbr_clk)",
               f"set elem_in [get_ports {{{elem[0]}}}]",
               f"set elem_out [get_ports {{{elem[1]}}}]",
               "set_input_delay -max [expr 473 + $die_skew] -clock nbr_clk $elem_in",
               "set_input_delay -min [expr 833 * 0.2] -clock nbr_clk $elem_in   ;# RULE H1: hold_io on the sender output min only",
               "set_output_delay -max [expr 323 + $die_skew] -clock nbr_clk $elem_out",
               "set_output_delay -min [expr 833 * 0.2 + $dlo - $hold_io] -clock nbr_clk $elem_out"]
        base = base.replace(f"set nbr_in [get_ports {{{nbr[0]}}}]", "\n".join(add) + f"\nset nbr_in [get_ports {{{nbr[0]}}}]")
    return base


STRIP_HOPS = {
    "front_c": r"""ot_pin_place_auto {.*} 14
# central channel between the ring columns, bottom to top: line skid, s1, issue (+ op channel sink), bulk-copy
# control (+ descriptor channel sink, request channel credits)
ot_place {^u_sk\.g_c\[\d+\]\.g_d\.e[01]} 152 272 170 200
ot_place {^s1_(w|cv|ct)} 152 272 202 220
ot_place {^(u_issue\.|u_sch\.(?!u_)|pop_r|fmt_q|xb_q|g_f1\[)} 152 272 222 241
ot_place {^(u_bc\.(outstanding|g_lookahead\.((?!g_sram)|g_sram\.(oq_n|oq_wp|oq_rp|res|rd_v|u_rok_c)))|u_dch\.(?!u_)|u_rch\.cred)} 152 272 243 285
# hop H of the tile-row-0 rows above the ring, of the tile-row-1 rows below it
ot_place {^g_h\[0\]\.} 60 200 456 486
ot_place {^g_h\[2\]\.} 232 372 456 486
ot_place {^g_h\[1\]\.} 60 200 16 40
ot_place {^g_h\[3\]\.} 232 372 16 40
# retire landing -> issue; response stage beside the ring's write pins
ot_place {^u_sv\.g_s\[1\]} 170 210 150 166
ot_place {^u_prd\.g_s\[1\]} 100 330 42 66
# tile row 1's x write: landed at the north face, M in the W / E edge strips between the row-bundle pin fields
ot_place {^g_bs\[0\]\.u_bm[dv]} 4 50 282 438
ot_place {^g_bs\[1\]\.u_bm[dv]} 382 428 282 438
""",
    "front_n": r"""ot_pin_place_auto {.*} 14
# op channel credits beside the start pin
ot_place {^u_sch\.(cred|rq|u_cr\.g_s\[1\])} 108 124 330 338
""",
    "front_s": r"""ot_pin_place_auto {.*} 14
# descriptor channel credits beside d_valid / d_ready; request channel sink beside the request skid
ot_place {^u_dch\.(cred|rq|u_cr\.g_s\[1\])} 128 140 16 24
ot_place {^u_rsk\.(rp|rpq)} 140 160 16 24
ot_place {^u_rsk\.} 120 200 26 40
ot_place {^u_rch\.(?!u_)} 120 200 42 66
""",
}


# ---------------- ORFS config ----------------
def sdc_block(lat, element_io=False, ring=False, static_inputs=(), nbr_in="rin* bin* gin*", lat_ff=None, period=833,
              skew=0, die_skew=150, hold_io=50, io_ref=False):
    lat_ff = lat_ff if lat_ff is not None else round(0.6 * float(lat))
    s = [f"# block constraints (tools/hbm_accel_smh_physical.py); clock {period} ps (sign-off 833: run.sh rewrites the",
         "# period of the routed SDC), 60 / 25 ps uncertainty",
         f"set clk_period {period}",
         "create_clock -name core_clk -period $clk_period [get_ports clk]",
         "create_clock -name nbr_clk -period $clk_period",
         "# the neighbour's flop sits at this block's own clock insertion, in each corner.  One SDC serves both corners",
         "# and STA reads -min / -max latency as early / late (a setup check captures an output at the EARLY latency),",
         "# so nbr_clk carries the SS insertion alone; the FF hold check at an output port, where the neighbour",
         f"# captures {lat} - {lat_ff} ps earlier than SS, takes that difference in the output min delay (dlo below).",
         "# At SS the output hold holds by construction (same insertion both sides); input hold at FF is checked by",
         "# the parent on the real pair.",
         f"set_clock_latency -source {lat} [get_clocks nbr_clk]",
         "# setup-triage 2026-10-07: the latency above is a PLANNING insertion; sign-off must re-reference nbr_clk to the routed",
         "# block's measured insertion with physical/common_flow/nbr_clk_measured.sdc as a post-SDC (front_n: planning",
         "# 688 vs measured 506..600 cost the element inputs 135 ps: SS in2reg -53.6 -> +81.4 on re-STA).",
         f"set dlo {float(lat) - float(lat_ff):g}",
         "# (margin rule, clarified 2026-10-06) setup: abutting ports between pieces of one element (one clock region)",
         "# budget the region pair skew + 25 (skew); the element pins cross a die wire to another region (die_skew).",
         "# Hold: FF-corner insertion (dlo) and a 50 ps IO uncertainty (hold_io) on the SENDER output min only (rule H1,",
         "# h1-verify 2026-10-08: the receiver input min carried it too), closed by hold repair.",
         f"set skew {skew}",
         f"set die_skew {die_skew}",
         f"set hold_io {hold_io}",
         "set_clock_uncertainty -setup 60 [all_clocks]",
         "set_clock_uncertainty -hold 25 [all_clocks]",
         "set_false_path -from [get_ports rst_n]"]
    for st in static_inputs:
        s.append(f"set_false_path -from [get_ports {{{st}}}]   ;# static strap: a tie cell in the parent")
    if element_io:
        s += ["# element pins: the W13 die budget magnitudes (473 / 323 external, 20 % min), referenced like every port",
              "# to the block's own clock insertion (nbr_clk): the parent balances this block's internal flops with",
              "# the hub's.  The element top keeps the binding ideal-clock die budget and reports it unchanged.",
              "set elem_in [get_ports {start op_* d_valid d_base* d_lines* req_ready rsp_* xw_* release_in}]",
              "set elem_out [get_ports {start_ready busy d_ready req_v req_addr* req_tag* rv rrow* rdata* fault arrive released}]",
              "set_input_delay -max [expr 473 + $die_skew] -clock nbr_clk $elem_in",
              "set_input_delay -min [expr 833 * 0.2] -clock nbr_clk $elem_in   ;# RULE H1: hold_io on the sender output min only",
              "set_output_delay -max [expr 323 + $die_skew] -clock nbr_clk $elem_out",
              "set_output_delay -min [expr 833 * 0.2 + $dlo - $hold_io] -clock nbr_clk $elem_out",
              "set nbr_in [get_ports {qin_*}]",
              "set nbr_out [get_ports {rout_* bout_*}]"]
    else:
        s += [f"set nbr_in [get_ports {{{nbr_in}}}]",
              "set nbr_out [all_outputs]"]
    if io_ref:
        s += ["# abutting ports (m2g, 2026-10-06): the neighbour piece's flop sits on the same element clock tree, so its",
              "# clock arrives at THIS block's insertion in EVERY corner.  Reference the abutting port delays to a register",
              "# clock pin of this block (-reference_pin: the propagated arrival at that pin, per corner) instead of nbr_clk",
              "# with the SS insertion as a fixed source latency: the latter made FF input hold optimistic by lat - lat_ff and",
              "# SS input hold pessimistic, which over-filled CTS hold repair (RSZ-0060 max buffer count at hold margin 25).",
              "set refpin [lindex [all_registers -clock_pins -edge_triggered] 0]",
              "set_input_delay -max [expr 300 + $skew] -clock core_clk -reference_pin $refpin $nbr_in",
              "set_input_delay -min 30 -clock core_clk -reference_pin $refpin $nbr_in   ;# RULE H1: hold_io on the sender output min only",
              "set_output_delay -max [expr 300 + $skew] -clock core_clk -reference_pin $refpin $nbr_out",
              "set_output_delay -min [expr 50 - $hold_io] -clock core_clk -reference_pin $refpin $nbr_out   ;# the neighbour lands it >= 50 ps inside",
              "set_load 2.0 [all_outputs]",
              "set_max_fanout 32 [current_design]"]
    else:
        s += ["# abutting ports: 300 ps of the neighbour's flop / wire outside, its clock insertion carried by nbr_clk",
          "set_input_delay -max [expr 300 + $skew] -clock nbr_clk $nbr_in",
          "set_input_delay -min 30 -clock nbr_clk $nbr_in   ;# RULE H1: hold_io on the sender output min only",
          "set_output_delay -max [expr 300 + $skew] -clock nbr_clk $nbr_out",
          "set_output_delay -min [expr 50 + $dlo - $hold_io] -clock nbr_clk $nbr_out   ;# the neighbour lands it >= 50 ps inside (top STA checks the real pair)",
          "set_load 2.0 [all_outputs]",
          "set_max_fanout 32 [current_design]"]
    if ring:
        s += ["# the bulk copy's ring read: ot_hbm_accel_bulk_copy_mc2.sdc (unchanged)",
              "set_multicycle_path -setup 2 -from [get_cells -hierarchical *u_ring]",
              "set_multicycle_path -hold 1 -from [get_cells -hierarchical *u_ring]"]
    return "\n".join(s) + "\n"


def config_mk(name, nick, die, macros, extra):
    lib_ss = " ".join(f"/src/{m}/{Path(m).name}_ss.lib" for m in macros)
    lib_ff = " ".join(f"/src/{m}/{Path(m).name}_ff.lib" for m in macros)
    # OPTION B (2026-10-07): OT_SMH_CORNER=TC routes with setup repair at TT (macro _tt.lib), hold corner BC unchanged
    _SC = os.environ.get("OT_SMH_CORNER", "WC").strip().upper() or "WC"
    # LOOP-CORNER (2026-10-10): the closure loop's option-B route env (OT_ORFS_CORNER=TC, or a recipe's
    # OT_ORFS_CORNER_OVERRIDE=TC) is honoured as well: corner WC keeps its NAME (the loop's mm hold session builds scene
    # WC) and reads the TT std-cell + macro liberties.  Before this, a recipe that set only the override routed at SS.
    _OC = (os.environ.get("OT_ORFS_CORNER", "") or os.environ.get("OT_ORFS_CORNER_OVERRIDE", "")).strip().upper()
    _TT = _SC != "WC" or _OC in ("TC", "TT")
    lib_su = " ".join(f"/src/{m}/{Path(m).name}_tt.lib" for m in macros) if _TT else lib_ss
    _SL = "TC" if (_TT and _SC == "WC") else _SC
    lefs = " ".join(f"/src/{m}/{Path(m).name}.lef" for m in macros)
    lines = [f"export DESIGN_NICKNAME = {nick}", f"export DESIGN_NAME = {name}", "export PLATFORM = asap7",
             "export VERILOG_FILES = " + " ".join(f"/src/{s}" for s in RTL),
             "export VERILOG_DEFINES = -DSYNTHESIS", "export SDC_FILE = /work/constraint.sdc",
             f"export DIE_AREA = 0 0 {die[0]} {die[1]}", f"export CORE_AREA = 1.08 1.08 {round(die[0]-1.08,3)} {round(die[1]-1.08,3)}",
             "export SYNTH_REPEATABLE_BUILD = 1", "export SYNTH_HIERARCHICAL = 0", "export SYNTH_MEMORY_MAX_BITS = 65536",
             "export LEC_CHECK = 0", "export TNS_END_PERCENT = 100", "export SETUP_SLACK_MARGIN = 0",
             "export SKIP_REPORT_METRICS = 0", "export REPORT_CLOCK_SKEW = 1",
             f"export CORNER = {_SC}", "export ADDER_MAP_FILE = ", "export ASAP7_USE_VT = RVT", "export SLEW_MARGIN = 30",
             f"export CORNERS = {_SC} BC", f"export {_SC}_LIB_FILES = $({_SL}_NLDM_LIB_FILES) {lib_su}",
             f"export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) {lib_ff}",
             "export IO_CONSTRAINTS = /work/pins.tcl", "export GDS_ALLOW_EMPTY = (ot_sram.*|ot_hbm_accel_smh_.*)"]
    if macros:
        lines += [f"export ADDITIONAL_LEFS = {lefs}", f"export ADDITIONAL_LIBS = {lib_su}",
                  "export SYNTH_BLACKBOXES = " + " ".join(Path(m).name for m in macros),
                  "export MACRO_PLACEMENT_TCL = /work/macros.tcl"]
    lines += [f"export {k} = {v}" for k, v in extra.items()]
    # FLOW-FIX-0410: (* keep *) register copies survive yosys opt_merge (physical/common_flow/ot_keep_regs.tcl)
    if os.environ.get("OT_KEEP_REGS", "1").strip() != "0" and "SYNTH_CANONICALIZE_TCL" not in extra:
        lines.append("export SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl")
    return "\n".join(lines) + "\n"


HOPS = r"""# front hop flops, FIRM (tools/hbm_accel_smh_physical.py); asap7 has no tapcells, rows alternate orientation
set ::ot_blk [ord::get_db_block]
set ::ot_rows {}
# cut_rows splits a row around the macros: one entry per y
set ::ot_ry [dict create]
foreach r [$::ot_blk getRows] { dict set ::ot_ry [lindex [$r getOrigin] 1] [$r getOrient] }
foreach y [lsort -integer [dict keys $::ot_ry]] { lappend ::ot_rows [list $y [dict get $::ot_ry $y]] }
# every flop of re whose D or Q reaches a port (through buffers / inverters) is placed FIRM at its pin: W / E pins
# in an edge strip `depth` um wide at the pin's row, N / S pins in the `depth` um of rows next to that edge at the
# pin's x.  Run before any other FIRM placement in the strips.
proc ::ot_net_port {net dir} {
    for {set d 0} {$d < 4} {incr d} {
        if {$net eq "NULL" || $net eq ""} { return "" }
        set bts [$net getBTerms]
        if {[llength $bts] > 0} { return [lindex $bts 0] }
        set nx "NULL"
        foreach it [$net getITerms] {
            set out [$it isOutputSignal]
            if {($dir eq "q" && $out) || ($dir eq "d" && !$out)} { continue }
            set inst [$it getInst]
            if {![regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]} { continue }
            foreach o [$inst getITerms] {
                if {![$o isInputSignal] && ![$o isOutputSignal]} { continue }
                if {($dir eq "q" && [$o isOutputSignal]) || ($dir eq "d" && [$o isInputSignal])} { set nx [$o getNet] }
            }
            break
        }
        set net $nx
    }
    return ""
}
proc ::ot_flop_port {inst} {
    set qn "NULL"; set dn "NULL"
    foreach it [$inst getITerms] {
        set mt [[$it getMTerm] getName]
        if {[$it isOutputSignal]} { set qn [$it getNet] } elseif {$mt eq "D"} { set dn [$it getNet] }
    }
    set bt [::ot_net_port $qn q]
    if {$bt eq ""} { set bt [::ot_net_port $dn d] }
    return $bt
}
# first slot from c (dir 1: rightwards, the slot is [c, c + w2]; dir -1: leftwards, the slot is [c - w2, c]) in row y
# clear of every cell placed before the pin placement (tap / boundary cells, FIRM flops)
proc ::ot_skip {c w2 y dir sw} {
    if {![dict exists $::ot_occ $y]} { return $c }
    set ivs [dict get $::ot_occ $y]
    set moved 1
    while {$moved} {
        set moved 0
        foreach iv $ivs {
            lassign $iv a b
            if {$dir > 0} {
                if {$c < $b + $sw && $c + $w2 > $a - $sw} { set c [expr {$b + $sw}]; set moved 1 }
            } else {
                if {$c - $w2 < $b + $sw && $c > $a - $sw} { set c [expr {$a - $sw}]; set moved 1 }
            }
        }
    }
    return $c
}
proc ::ot_pin_place_auto {re depth} {
    set dbu [$::ot_blk getDbUnitsPerMicron]
    set sw [expr {int(round(0.054 * $dbu))}]
    set die [$::ot_blk getDieArea]
    set dw [$die xMax]; set dh [$die yMax]
    set m0 [expr {int(round(1.08 * $dbu))}]
    set dp [expr {int(round($depth / 0.054)) * $sw}]
    # the row-end boundary cells (PHY_EDGE_ROW_*, inserted by the tapcell step) sit at both ends of every row
    set capw 0
    foreach i [$::ot_blk getInsts] {
        if {[string match PHY_EDGE_ROW* [$i getName]] && [[$i getMaster] getWidth] > $capw} { set capw [[$i getMaster] getWidth] }
    }
    set m0 [expr {$m0 + $capw}]
    set ::ot_occ [dict create]
    foreach i [$::ot_blk getInsts] {
        if {[[$i getMaster] isBlock] || ![$i isPlaced]} { continue }
        set bb [$i getBBox]
        dict lappend ::ot_occ [$bb yMin] [list [$bb xMin] [$bb xMax]]
    }
    set E [dict create W {} E {} S {} N {}]
    set skip 0
    foreach i [$::ot_blk getInsts] {
        if {![string match *DFF* [[$i getMaster] getName]]} { continue }
        if {![regexp $re [string map {"\\" ""} [$i getName]]]} { continue }
        set bt [::ot_flop_port $i]
        if {$bt eq ""} { incr skip; continue }
        set bb [$bt getBBox]
        set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
        if {$px < 2 * $m0} { set e W } elseif {$px > $dw - 2 * $m0} { set e E } elseif {$py < 2 * $m0} { set e S } else { set e N }
        dict lappend E $e [list [expr {($e eq "W" || $e eq "E") ? $py : $px}] $i]
    }
    set rows {}
    set par 0
    foreach r $::ot_rows { if {$par % 2 == 0} { lappend rows $r }; incr par }
    set nr [llength $rows]
    set placed 0
    foreach e {W E} {
        set fl [lsort -integer -index 0 [dict get $E $e]]
        if {![llength $fl]} { continue }
        if {$e eq "W"} { set lo $m0; set hi [expr {$m0 + $dp}] } else { set hi [expr {$dw - $m0}]; set lo [expr {$hi - $dp}] }
        set cur [lrepeat $nr [expr {$e eq "W" ? $lo : $hi}]]
        foreach f $fl {
            lassign $f py inst
            set w [[$inst getMaster] getWidth]; set w2 [expr {$w + 12 * $sw}]; set h [[$inst getMaster] getHeight]
            for {set a 0; set b [expr {$nr - 1}]} {$a <= $b} {} {
                set m [expr {($a + $b) / 2}]
                if {[lindex $rows $m 0] + $h / 2 < $py} { set a [expr {$m + 1}] } else { set b [expr {$m - 1}] }
            }
            set r0 [expr {$a >= $nr ? $nr - 1 : $a}]
            set done 0
            for {set s 0} {$s < $nr && !$done} {incr s} {
                foreach r [list [expr {$r0 - $s}] [expr {$r0 + $s}]] {
                    if {$r < 0 || $r >= $nr} { continue }
                    set c [lindex $cur $r]
                    set rr [lindex $rows $r]
                    set c [::ot_skip $c $w2 [lindex $rr 0] [expr {$e eq "W" ? 1 : -1}] $sw]
                    if {$e eq "W"} {
                        if {$c + $w2 > $hi} { continue }
                        set x $c; lset cur $r [expr {$c + $w2}]
                    } else {
                        if {$c - $w2 < $lo} { continue }
                        set x [expr {$c - $w2}]; lset cur $r [expr {$c - $w2}]   ;# upsizing grows rightwards: keep the room on the pin side
                    }
                    place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                    set done 1; incr placed; break
                }
            }
            if {!$done} { error "ot_pin_place_auto $re: no room on $e for [$inst getName]" }
        }
    }
    foreach e {S N} {
        set fl [lsort -integer -index 0 [dict get $E $e]]
        if {![llength $fl]} { continue }
        set er {}
        foreach r $rows {
            set y [lindex $r 0]
            if {($e eq "S" && $y >= $m0 && $y < $m0 + $dp) || ($e eq "N" && $y + 270 <= $dh - $m0 && $y + 270 > $dh - $m0 - $dp)} { lappend er $r }
        }
        if {$e eq "N"} { set er [lreverse $er] }
        set ne [llength $er]
        if {!$ne} { error "ot_pin_place_auto: no rows on $e" }
        set cur [lrepeat $ne [expr {$m0 + $dp}]]
        set k 0
        foreach f $fl {
            lassign $f px inst
            set w [[$inst getMaster] getWidth]; set w2 [expr {$w + 12 * $sw}]
            set done 0
            for {set t 0} {$t < $ne && !$done} {incr t} {
                set r [expr {($k + $t) % $ne}]
                set c [lindex $cur $r]
                set x [expr {$px - $w / 2}]
                set x [expr {$m0 + ($x - $m0) / $sw * $sw}]
                if {$x < $c} { set x $c }
                set rr [lindex $er $r]
                set x [::ot_skip $x $w2 [lindex $rr 0] 1 $sw]
                if {$x + $w2 > $dw - $m0 - $dp} { continue }
                place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                lset cur $r [expr {$x + $w2}]
                set done 1; incr placed
            }
            if {!$done} { error "ot_pin_place_auto $re: no room on $e for [$inst getName]" }
            incr k
        }
    }
    puts "ot_pin_place_auto $re: $placed flops at their pins (W [llength [dict get $E W]] E [llength [dict get $E E]] S [llength [dict get $E S]] N [llength [dict get $E N]]), $skip without a port"
}
proc ::ot_place {re xlo xhi ylo yhi} {
    set dbu [$::ot_blk getDbUnitsPerMicron]
    set x0 [expr {int(round(1.08 * $dbu))}]
    set sw [expr {int(round(0.054 * $dbu))}]
    set names {}
    set occ {}
    set rh [expr {int(round(0.27 * $dbu))}]
    foreach i [$::ot_blk getInsts] {
        set n [$i getName]
        if {[regexp $re [string map {"\\" ""} $n]] && [string match *DFF* [[$i getMaster] getName]] &&
            [$i getPlacementStatus] ne "FIRM"} { lappend names $i; continue }
        if {[$i isPlaced] || [$i getPlacementStatus] eq "FIRM"} {
            # any placed cell or macro whose box crosses the window (a macro starting below ylo counts too:
            # front_m2c DPL-0033, u_bmd flops placed over the ring macro whose yMin lay under the window)
            set bb [$i getBBox]
            set hl [expr {[[$i getMaster] isBlock] ? int(round(3.0 * $dbu)) : 0}]   ;# MACRO_PLACE_HALO 3 3
            if {[$bb yMax] + $hl > $ylo * $dbu && [$bb yMin] - $hl <= $yhi * $dbu + $rh &&
                [$bb xMax] + $hl > $xlo * $dbu - $sw && [$bb xMin] - $hl < $xhi * $dbu + $sw} {
                lappend occ [list [expr {[$bb xMin] - $hl}] [expr {[$bb xMax] + $hl}] [expr {[$bb yMin] - $hl}] [expr {[$bb yMax] + $hl}]]
            }
        }
    }
    set names [lsort -command {apply {{a b} {string compare [$a getName] [$b getName]}}} $names]
    set rows {}
    set par 0
    foreach r $::ot_rows {
        set y [lindex $r 0]
        if {$y < $ylo * $dbu || $y > $yhi * $dbu} { continue }
        if {$par % 2 == 0} { lappend rows $r }
        incr par
    }
    set k 0
    set n [llength $names]
    foreach r $rows {
        set y [lindex $r 0]
        set busy {}
        foreach iv $occ { if {[lindex $iv 2] < $y + $rh && [lindex $iv 3] > $y} { lappend busy $iv } }
        set x [expr {$x0 + (int($xlo * $dbu) - $x0 + $sw - 1) / $sw * $sw}]
        while {$k < $n} {
            set inst [lindex $names $k]
            set w [[$inst getMaster] getWidth]
            set w2 [expr {$w + 12 * $sw}]   ;# room for the resizer to upsize a FIRM flop in place
            if {$x + $w2 > int($xhi * $dbu)} { break }
            set hit 0
            foreach iv $busy {
                if {$x < [lindex $iv 1] + $sw && $x + $w2 > [lindex $iv 0] - $sw} { set hit [lindex $iv 1]; break }
            }
            if {$hit} { set x [expr {$x0 + ($hit + $sw - $x0 + $sw - 1) / $sw * $sw}]; continue }
            place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double($y) / $dbu}]] -orientation [lindex $r 1] -status FIRM
            set x [expr {$x + $w2}]
            incr k
        }
    }
    if {$k < $n} { error "ot_place $re: placed $k of $n in ($xlo $xhi $ylo $yhi)" }
    puts "ot_place $re: $n flops"
}
proc ::ot_port_y {inst} {
    set net "NULL"
    foreach it [$inst getITerms] { if {[$it isOutputSignal]} { set net [$it getNet]; break } }
    for {set d 0} {$d < 4} {incr d} {
        if {$net eq "NULL" || $net eq ""} { return "" }
        set bts [$net getBTerms]
        if {[llength $bts] > 0} {
            set bb [[lindex $bts 0] getBBox]
            return [expr {([$bb yMin] + [$bb yMax]) / 2}]
        }
        set nx "NULL"
        foreach it [$net getITerms] {
            if {[$it isOutputSignal]} { continue }
            set m [[$it getInst] getMaster]
            if {[regexp {^(BUF|INV|HB)} [$m getName]]} {
                foreach o [[$it getInst] getITerms] { if {[$o isOutputSignal]} { set nx [$o getNet] } }
                break
            }
        }
        set net $nx
    }
    return ""
}
# flops matching re, each at the row nearest its port pin, FIRM, in a strip xw wide xoff from the side's edge
proc ::ot_pin_place {re side xoff xw} {
    set dbu [$::ot_blk getDbUnitsPerMicron]
    set sw [expr {int(round(0.054 * $dbu))}]
    set dw [[$::ot_blk getDieArea] xMax]
    set m0 [expr {int(round(1.08 * $dbu))}]
    set xoff [expr {round($xoff / 0.054) * 0.054}]; set xw [expr {round($xw / 0.054) * 0.054}]
    if {$side eq "W"} {
        set lo [expr {$m0 + int(round($xoff * $dbu))}]; set hi [expr {$lo + int(round($xw * $dbu))}]
    } else {
        set hi [expr {$dw - $m0 - int(round($xoff * $dbu))}]; set lo [expr {$hi - int(round($xw * $dbu))}]
    }
    set fl {}
    foreach i [$::ot_blk getInsts] {
        if {![string match *DFF* [[$i getMaster] getName]]} { continue }
        if {![regexp $re [string map {"\\" ""} [$i getName]]]} { continue }
        set y [::ot_port_y $i]
        if {$y eq ""} { error "ot_pin_place $re: no port for [$i getName]" }
        lappend fl [list $y $i]
    }
    set fl [lsort -integer -index 0 $fl]
    set rows {}
    set par 0
    foreach r $::ot_rows { if {$par % 2 == 0} { lappend rows $r }; incr par }
    set nr [llength $rows]
    set cur [lrepeat $nr [expr {$side eq "W" ? $lo : $hi}]]
    set k 0
    foreach e $fl {
        lassign $e py inst
        set w [[$inst getMaster] getWidth]
        set w2 [expr {$w + 12 * $sw}]
        set h [[$inst getMaster] getHeight]
        # nearest row (row centre to pin y)
        set best 0; set bd 1e18
        for {set a 0; set b [expr {$nr - 1}]} {$a <= $b} {} {
            set m [expr {($a + $b) / 2}]
            if {[lindex $rows $m 0] + $h / 2 < $py} { set a [expr {$m + 1}] } else { set b [expr {$m - 1}] }
        }
        set r0 [expr {$a >= $nr ? $nr - 1 : $a}]
        set done 0
        for {set s 0} {$s < $nr && !$done} {incr s} {
            foreach r [list [expr {$r0 - $s}] [expr {$r0 + $s}]] {
                if {$r < 0 || $r >= $nr} { continue }
                set c [lindex $cur $r]
                if {$side eq "W"} {
                    if {$c + $w2 > $hi} { continue }
                    set x $c; lset cur $r [expr {$c + $w2}]
                } else {
                    if {$c - $w2 < $lo} { continue }
                    set x [expr {$c - $w2}]; lset cur $r [expr {$c - $w2}]   ;# upsizing grows rightwards: keep the room on the pin side
                }
                set rr [lindex $rows $r]
                place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                set done 1; incr k; break
            }
        }
        if {!$done} { error "ot_pin_place $re: no room for [$inst getName]" }
    }
    puts "ot_pin_place $re: $k flops ($side strip [expr {double($lo)/$dbu}] .. [expr {double($hi)/$dbu}])"
}
# (round 10) r9b post-CTS -623 ps: the issue (234 um2, 628 flops) was spread over 300 x 400 um (u_issue.oh at x 23,
# its consumers at x 267), the bulk copy's request half sat at the south pins 450 um from its ring half (hf_c -> used
# -230), and the far-row x-write O stage packed into y 230-265 against pins spanning y 242-440 (-584).
# Every row / x-write output flop now sits at its own pin's row (the bundle leaves through a 14 um edge strip); the
# issue with the start channel's sink and the bulk copy's control are FIRM, compact, in the central channel next to
# the line skid and s1 they talk to every cycle.
# (margin m1) every flop that reaches a pin sits at it: the O stages in the W / E strips, the element-pin landing
# and launch registers (x-write wl, response chain stage 0, request skid head, result outputs) in the N / S rows
ot_pin_place_auto {.*} 14
# central channel (x 148.4 .. 276.5 between the ring columns), bottom to top: line skid, s1, issue, bulk-copy control
ot_place {^u_sk\.g_c\[\d+\]\.g_d\.e[01]} 152 272 470 500
ot_place {^s1_(w|cv|ct)} 152 272 502 520
ot_place {^(u_issue\.|u_sch\.(?!u_)|pop_r|fmt_q|xb_q|g_f1\[)} 152 272 522 541
ot_place {^u_bc\.(outstanding|g_lookahead\.((?!g_sram)|g_sram\.(oq_n|oq_wp|oq_rp|res|rd_v|u_rok_c)))} 152 272 543 575
ot_place {^g_h\[0\]\.} 60 200 770 800
ot_place {^g_h\[2\]\.} 232 372 770 800
ot_place {^g_h\[1\]\.} 60 200 330 360
ot_place {^g_h\[3\]\.} 232 372 330 360
# retire chain (column 0's aligned valid -> issue) from the back-end edge up into the central channel
ot_place {^u_sv\.g_s\[0\]} 170 210 180 200
ot_place {^u_sv\.g_s\[1\]} 170 210 320 340
ot_place {^u_sv\.g_s\[2\]} 170 210 450 465
# x-write bundle of the far row (row 1): A above the ring block, M beside it (inside the edge strip)
ot_place {^g_side\[0\]\.g_rs\[2\]\.g_bo\.u_ba[dv]} 18 200 805 870
ot_place {^g_side\[1\]\.g_rs\[2\]\.g_bo\.u_ba[dv]} 232 414 805 870
ot_place {^g_side\[0\]\.g_rs\[2\]\.g_bo\.u_bm[dv]} 18 62 470 660
ot_place {^g_side\[1\]\.g_rs\[2\]\.g_bo\.u_bm[dv]} 370 414 470 660
# response chain (south pins -> ring block): four stages
ot_place {^u_prd\.g_s\[0\]} 100 330 20 50
ot_place {^u_prd\.g_s\[1\]} 100 330 110 140
ot_place {^u_prd\.g_s\[2\]} 100 330 200 230
ot_place {^u_prd\.g_s\[3\]} 100 330 290 320
# the request skid beside the south pins
ot_place {^u_rsk\.} 120 200 3 12
"""


PIN_HDR = r"""# piece port flops at their pins, FIRM (tools/hbm_accel_smh_physical.py; margin rule: every boundary flop -> pin)
set ::ot_blk [ord::get_db_block]
set ::ot_rows {}
set ::ot_ry [dict create]
foreach r [$::ot_blk getRows] { dict set ::ot_ry [lindex [$r getOrigin] 1] [$r getOrient] }
foreach y [lsort -integer [dict keys $::ot_ry]] { lappend ::ot_rows [list $y [dict get $::ot_ry $y]] }
"""
PIN_TCL = PIN_HDR + r"""# every flop of re whose D or Q reaches a port (through buffers / inverters) is placed FIRM at its pin: W / E pins
# in an edge strip `depth` um wide at the pin's row, N / S pins in the `depth` um of rows next to that edge at the
# pin's x.  Run before any other FIRM placement in the strips.
proc ::ot_net_port {net dir} {
    for {set d 0} {$d < 4} {incr d} {
        if {$net eq "NULL" || $net eq ""} { return "" }
        set bts [$net getBTerms]
        if {[llength $bts] > 0} { return [lindex $bts 0] }
        set nx "NULL"
        foreach it [$net getITerms] {
            set out [$it isOutputSignal]
            if {($dir eq "q" && $out) || ($dir eq "d" && !$out)} { continue }
            set inst [$it getInst]
            if {![regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]} { continue }
            foreach o [$inst getITerms] {
                if {![$o isInputSignal] && ![$o isOutputSignal]} { continue }
                if {($dir eq "q" && [$o isOutputSignal]) || ($dir eq "d" && [$o isInputSignal])} { set nx [$o getNet] }
            }
            break
        }
        set net $nx
    }
    return ""
}
proc ::ot_flop_port {inst} {
    set qn "NULL"; set dn "NULL"
    foreach it [$inst getITerms] {
        set mt [[$it getMTerm] getName]
        if {[$it isOutputSignal]} { set qn [$it getNet] } elseif {$mt eq "D"} { set dn [$it getNet] }
    }
    set bt [::ot_net_port $qn q]
    if {$bt eq ""} { set bt [::ot_net_port $dn d] }
    return $bt
}
# first slot from c (dir 1: rightwards, the slot is [c, c + w2]; dir -1: leftwards, the slot is [c - w2, c]) in row y
# clear of every cell placed before the pin placement (tap / boundary cells, FIRM flops)
proc ::ot_skip {c w2 y dir sw} {
    if {![dict exists $::ot_occ $y]} { return $c }
    set ivs [dict get $::ot_occ $y]
    set moved 1
    while {$moved} {
        set moved 0
        foreach iv $ivs {
            lassign $iv a b
            if {$dir > 0} {
                if {$c < $b + $sw && $c + $w2 > $a - $sw} { set c [expr {$b + $sw}]; set moved 1 }
            } else {
                if {$c - $w2 < $b + $sw && $c > $a - $sw} { set c [expr {$a - $sw}]; set moved 1 }
            }
        }
    }
    return $c
}
proc ::ot_pin_place_auto {re depth} {
    set dbu [$::ot_blk getDbUnitsPerMicron]
    set sw [expr {int(round(0.054 * $dbu))}]
    set die [$::ot_blk getDieArea]
    set dw [$die xMax]; set dh [$die yMax]
    set m0 [expr {int(round(1.08 * $dbu))}]
    set dp [expr {int(round($depth / 0.054)) * $sw}]
    # the row-end boundary cells (PHY_EDGE_ROW_*, inserted by the tapcell step) sit at both ends of every row
    set capw 0
    foreach i [$::ot_blk getInsts] {
        if {[string match PHY_EDGE_ROW* [$i getName]] && [[$i getMaster] getWidth] > $capw} { set capw [[$i getMaster] getWidth] }
    }
    set m0 [expr {$m0 + $capw}]
    set ::ot_occ [dict create]
    foreach i [$::ot_blk getInsts] {
        if {[[$i getMaster] isBlock] || ![$i isPlaced]} { continue }
        set bb [$i getBBox]
        dict lappend ::ot_occ [$bb yMin] [list [$bb xMin] [$bb xMax]]
    }
    set E [dict create W {} E {} S {} N {}]
    set skip 0
    foreach i [$::ot_blk getInsts] {
        if {![string match *DFF* [[$i getMaster] getName]]} { continue }
        if {![regexp $re [string map {"\\" ""} [$i getName]]]} { continue }
        set bt [::ot_flop_port $i]
        if {$bt eq ""} { incr skip; continue }
        set bb [$bt getBBox]
        set px [expr {([$bb xMin] + [$bb xMax]) / 2}]; set py [expr {([$bb yMin] + [$bb yMax]) / 2}]
        if {$px < 2 * $m0} { set e W } elseif {$px > $dw - 2 * $m0} { set e E } elseif {$py < 2 * $m0} { set e S } else { set e N }
        dict lappend E $e [list [expr {($e eq "W" || $e eq "E") ? $py : $px}] $i]
    }
    set rows {}
    set par 0
    foreach r $::ot_rows { if {$par % 2 == 0} { lappend rows $r }; incr par }
    set nr [llength $rows]
    set placed 0
    foreach e {W E} {
        set fl [lsort -integer -index 0 [dict get $E $e]]
        if {![llength $fl]} { continue }
        if {$e eq "W"} { set lo $m0; set hi [expr {$m0 + $dp}] } else { set hi [expr {$dw - $m0}]; set lo [expr {$hi - $dp}] }
        set cur [lrepeat $nr [expr {$e eq "W" ? $lo : $hi}]]
        foreach f $fl {
            lassign $f py inst
            set w [[$inst getMaster] getWidth]; set w2 [expr {$w + 12 * $sw}]; set h [[$inst getMaster] getHeight]
            for {set a 0; set b [expr {$nr - 1}]} {$a <= $b} {} {
                set m [expr {($a + $b) / 2}]
                if {[lindex $rows $m 0] + $h / 2 < $py} { set a [expr {$m + 1}] } else { set b [expr {$m - 1}] }
            }
            set r0 [expr {$a >= $nr ? $nr - 1 : $a}]
            set done 0
            for {set s 0} {$s < $nr && !$done} {incr s} {
                foreach r [list [expr {$r0 - $s}] [expr {$r0 + $s}]] {
                    if {$r < 0 || $r >= $nr} { continue }
                    set c [lindex $cur $r]
                    set rr [lindex $rows $r]
                    set c [::ot_skip $c $w2 [lindex $rr 0] [expr {$e eq "W" ? 1 : -1}] $sw]
                    if {$e eq "W"} {
                        if {$c + $w2 > $hi} { continue }
                        set x $c; lset cur $r [expr {$c + $w2}]
                    } else {
                        if {$c - $w2 < $lo} { continue }
                        set x [expr {$c - $w2}]; lset cur $r [expr {$c - $w2}]   ;# upsizing grows rightwards: keep the room on the pin side
                    }
                    place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                    set done 1; incr placed; break
                }
            }
            if {!$done} { error "ot_pin_place_auto $re: no room on $e for [$inst getName]" }
        }
    }
    foreach e {S N} {
        set fl [lsort -integer -index 0 [dict get $E $e]]
        if {![llength $fl]} { continue }
        set er {}
        foreach r $rows {
            set y [lindex $r 0]
            if {($e eq "S" && $y >= $m0 && $y < $m0 + $dp) || ($e eq "N" && $y + 270 <= $dh - $m0 && $y + 270 > $dh - $m0 - $dp)} { lappend er $r }
        }
        if {$e eq "N"} { set er [lreverse $er] }
        set ne [llength $er]
        if {!$ne} { error "ot_pin_place_auto: no rows on $e" }
        set cur [lrepeat $ne [expr {$m0 + $dp}]]
        set k 0
        foreach f $fl {
            lassign $f px inst
            set w [[$inst getMaster] getWidth]; set w2 [expr {$w + 12 * $sw}]
            set done 0
            for {set t 0} {$t < $ne && !$done} {incr t} {
                set r [expr {($k + $t) % $ne}]
                set c [lindex $cur $r]
                set x [expr {$px - $w / 2}]
                set x [expr {$m0 + ($x - $m0) / $sw * $sw}]
                if {$x < $c} { set x $c }
                set rr [lindex $er $r]
                set x [::ot_skip $x $w2 [lindex $rr 0] 1 $sw]
                if {$x + $w2 > $dw - $m0 - $dp} { continue }
                place_inst -name [$inst getName] -location [list [expr {double($x) / $dbu}] [expr {double([lindex $rr 0]) / $dbu}]] -orientation [lindex $rr 1] -status FIRM
                lset cur $r [expr {$x + $w2}]
                set done 1; incr placed
            }
            if {!$done} { error "ot_pin_place_auto $re: no room on $e for [$inst getName]" }
            incr k
        }
    }
    puts "ot_pin_place_auto $re: $placed flops at their pins (W [llength [dict get $E W]] E [llength [dict get $E E]] S [llength [dict get $E S]] N [llength [dict get $E N]]), $skip without a port"
}
ot_pin_place_auto {.*} 16
"""


RUN = r"""#!/bin/bash
# {label}: route, abstract, sign-off corner STA.  Host-side paths; the container sees /src (sources) and /work.
set -u
W={work}
S={src}
NEED={need}
CORES={cores}
IMG=openroad/orfs:asap7lock
cd $W
echo "start $(date -Is)" > $W/status
{admit}docker run --rm --name {cname} -v $S:/src:ro -v $W:/work \
  -w /OpenROAD-flow-scripts/flow $IMG bash -lc "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; \
  source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work \
  FLOW_VARIANT=base NUM_CORES=$CORES {make_extra}{target}" > $W/flow.log 2>&1
echo "flow_rc=$?" >> $W/status
B=$(ls -d $W/results/asap7/*/base | head -1)
if [ -f $B/6_final.odb ]; then
  docker run --rm -v $S:/src:ro -v $W:/work $IMG bash -lc \
    "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/abstract.tcl" > $W/abstract.log 2>&1
  echo "abstract_rc=$?" >> $W/status
  # sign-off at 833 ps: the routed SDC with the (over-constrained) route period put back to 833
  sed -E 's/-period [0-9.]+/-period 833.0000/g' $B/6_final.sdc > $B/6_signoff.sdc
  # later consumers of 6_final.sdc (the closure loop's post-route hold ECO) sign off at 833 too; the route SDC is kept
  [ -f $B/6_final_route.sdc ] || cp $B/6_final.sdc $B/6_final_route.sdc; cp $B/6_signoff.sdc $B/6_final.sdc
  (cd $S && python3 tools/w18/corner_sta.py --orfs-dir $W {macro_args} --sdc-name 6_signoff.sdc --output $W/corner_sta.json) > $W/corner.log 2>&1
  echo "corner_rc=$?" >> $W/status
fi
echo "end $(date -Is)" >> $W/status
"""

def write_abstract(work: Path, name, macros, view_name, tt=False):
    mlefs = "\n".join(f"read_lef /src/{m}/{Path(m).name}.lef" for m in macros)
    for c in (("ss", "ff", "tt") if tt else ("ss", "ff")):
        C = c.upper()
        libs = [f"asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz", f"asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz",
                f"asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz", f"asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib",
                f"asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz"]
        t = ["set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7",
             "read_lef $PLAT/lef/asap7_tech_1x_201209.lef", "read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef",
             mlefs] + [f"read_liberty $PLAT/lib/NLDM/{l}" for l in libs] + \
            [f"read_liberty /src/{m}/{Path(m).name}_{c}.lib" for m in macros] + [
             "set base [lindex [glob /work/results/asap7/*/base] 0]",
             "read_db $base/6_final.odb", "read_spef $base/6_final.spef",
             "create_clock -name core_clk -period 833 [get_ports clk]", "set_propagated_clock [all_clocks]",
             f"write_timing_model -library_name {view_name}_{c} /work/views/{view_name}_{c}.lib"]
        if c == "ss":
            t.append(f"write_abstract_lef /work/views/{view_name}.lef")
        t.append("exit")
        (work / f"abstract_{c}.tcl").write_text("\n".join(t) + "\n")
    (work / "abstract.tcl").write_text("source /work/abstract_ss.tcl\n")


def run_sh(work: Path, label, src, need, cores, macros, target="finish", admit=True, make_extra="", tt=False):
    margs = " ".join(f"--macro {m}" for m in macros)
    txt = RUN.format(label=label, work=work, src=src, need=need, cores=cores, cname=f"claude-smh-{label}",
                     macro_args=margs, target=target, make_extra=make_extra,
                     admit="/srv/opentallas-scratch/admit.sh $NEED -- " if admit else "")
    # setup-triage IO fix (OPTION B, 2026-10-07): OT_SMH_POST_SDC (space-separated repo paths, normally
    # physical/common_flow/nbr_clk_measured.sdc) re-times the SETUP corners (TT sign-off, SS sensitivity) with the
    # neighbour clock at this route's measured insertion.  The FF hold check keeps the generator SDC (its dlo term
    # models the FF neighbour against the SS planning latency; re-referencing nbr_clk there would double-count it).
    _post = os.environ.get("OT_SMH_POST_SDC", "").split()
    if _post:
        pa = " ".join(f"--post-sdc {q}" for q in _post)
        merge = ("import json,sys; b=json.load(open(sys.argv[1])); p=json.load(open(sys.argv[2])); "
                 "b['setup_tt']=p['setup_tt']; b['setup_ss']=p['setup_ss']; b['setup_post_sdc']=p['post_sdc']; "
                 "json.dump(b,open(sys.argv[1],'w'),indent=1)")
        step = (f'  echo "corner_rc=$?" >> $W/status\n'
                f'  (cd $S && python3 tools/w18/corner_sta.py --orfs-dir $W {margs} {pa} --sdc-name 6_signoff.sdc '
                f'--output $W/corner_sta_setup_post.json) > $W/corner_setup_post.log 2>&1 && '
                f'cp $W/corner_sta.json $W/corner_sta_hold_model.json && '
                f'python3 -c "{merge}" $W/corner_sta.json $W/corner_sta_setup_post.json\n'
                f'  echo "setup_post_rc=$?" >> $W/status\n')
        assert txt.count('  echo "corner_rc=$?" >> $W/status\n') == 1
        txt = txt.replace('  echo "corner_rc=$?" >> $W/status\n', step)
    # two abstract sessions (SS and FF)
    txt = txt.replace('"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/abstract.tcl"',
                      '"mkdir -p /work/views; for c in ' + ('ss ff tt' if tt else 'ss ff') + '; do /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/'
                      'openroad -no_init -exit /work/abstract_\\$c.tcl || exit 1; done"')
    (work / "run.sh").write_text(txt)
    (work / "run.sh").chmod(0o755)


SIGNOFF_HOLD_UNC_PS = 25.0   # set_clock_uncertainty -hold of the generated SDC (sign-off at FF)


def loop_hold_margin(arg_ps, env=None):
    """ORFS HOLD_SLACK_MARGIN (ps) for this piece.  The closure loop exports HM (ns: spec route_hold_margin_ns, default
    HM_MM 0.050) to every calibrate / route stage; a piece routed with its own --hold-margin 25 ignored it (redesign-0315,
    hbm_smh_front_s m3f/m3g: FF -18..-28).  When HM is set the repair aims HM + the sign-off hold uncertainty (50 + 25 =
    75 ps), never below an explicit larger --hold-margin."""
    hm = (os.environ if env is None else env).get("HM", "").strip()
    if not hm:
        return arg_ps
    try:
        want = float(hm) * 1000.0 + SIGNOFF_HOLD_UNC_PS
    except ValueError:
        return arg_ps
    return f"{max(float(arg_ps), want):g}"


def cmd_block(a):
    a.hold_margin = loop_hold_margin(a.hold_margin)
    print(f"HOLD_SLACK_MARGIN {a.hold_margin} ps (loop HM={os.environ.get('HM', '')} ns)")
    work = Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    g = json.loads(Path(a.geom).read_text()) if a.geom else GEOM
    extra = {"PLACE_DENSITY": a.pd, "MIN_ROUTING_LAYER": "M2", "MAX_ROUTING_LAYER": a.max_layer, "HOLD_SLACK_MARGIN": a.hold_margin,
             "PDN_TCL": "/src/tools/chip_assembly/tcl/pdn_smh_block.tcl", "MACRO_PLACE_HALO": "3 3"}
    if getattr(a, "io_ref", False):
        # OpenROAD buffer_ports segfaults (Sim::findDisabledEdges) on the canonical SDC's -reference_pin under the
        # WC + BC corners; the port flops sit at the pins (no port buffer needed), so skip port buffering.
        extra["DONT_BUFFER_PORTS"] = "1"
    if getattr(a, "hold_buffer_pct", None):
        # hold repair to the sign-off target (FF >= +15 after the 25 ps uncertainty needs ORFS hold margin ~25) inserts
        # more hold buffers than repair_timing's default cap (20 % of instances: RSZ-0060 on be m2g at 21 % utilization):
        # wrap ORFS's repair_timing_helper before CTS / global route to raise -max_buffer_percent.
        (work / "rt_hook.tcl").write_text(
            "# raise repair_timing's buffer cap (tools/hbm_accel_smh_physical.py --hold-buffer-pct)\n"
            "if {[info commands ::ot_rth_orig] eq \"\"} { rename ::repair_timing_helper ::ot_rth_orig }\n"
            f"proc ::repair_timing_helper {{args}} {{ ::ot_rth_orig {{*}}$args -max_buffer_percent {a.hold_buffer_pct} }}\n")
        extra["PRE_CTS_TCL"] = "/work/rt_hook.tcl"
        extra["PRE_GLOBAL_ROUTE_TCL"] = "/work/rt_hook.tcl"
    if a.grt_allow:
        extra["GLOBAL_ROUTE_ARGS"] = "-congestion_report_iter_step 5 -verbose -allow_congestion -congestion_iterations 60"
    if a.piece == "tile":
        w, h = g["tile_w"], g["tile_h"]
        pins = tile_pins(w, h, a.variant, cg=a.cg)
        macros = [SRAM_X]
        name = "ot_hbm_accel_smh_tile_" + ("e" if a.variant == "toE" else "w") + ("g" if a.cg else "")
        # the 2 x 4 x-store macros: leaf 0 upper half, leaf 1 lower half, a 2 x 2 block each, centred
        mw, mh = 94.824, 41.04
        xs = [round(w / 2 - mw - 2.16, 3), round(w / 2 + 2.16, 3)]
        # a leaf's 4 x-store macros stacked in one column (their pins are on the left / right edges, kept free),
        # leaf 0 in the upper half, leaf 1 in the lower half, centred
        xy = {}
        x0 = qd((w - mw) / 2)
        for j in range(P["RPT"]):
            yc = h * (0.75 if j == 0 else 0.25)
            y0 = qd(yc - 2 * mh - 1.5 * 4.32)
            for mi in range(4):
                xy[(j, mi)] = (x0, round(y0 + mi * (mh + 4.32), 3))
        tcl = ["set ot_n 0", "array set ot_xy {"] + [f"  {{{j}:{mi}}} {{{x} {y}}}" for (j, mi), (x, y) in xy.items()] + [
               "}", "foreach ot_inst [[ord::get_db_block] getInsts] {",
               "  if {![[$ot_inst getMaster] isBlock]} { continue }",
               "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
               "  if {[regexp {g_lf\\[(\\d+)\\]\\.(?:u_lh\\.)?u_leaf\\.g_xm\\[(\\d+)\\]\\.u_x} $n -> j mi]} {",
               "    place_macro -macro_name [$ot_inst getName] -location $ot_xy($j:$mi) -orientation R0",
               "  } elseif {[regexp {g_lf\\[(\\d+)\\]\\.u_lh\\.u_leaf\\.u_(tcc|bdc)} $n -> j c]} {",
               "    place_macro -macro_name [$ot_inst getName] -location [lrange $ot_cx($j:$c) 0 1] -orientation [lindex $ot_cx($j:$c) 2]",
               "  } else { error \"no slot for $n\" }",
               "  incr ot_n", "}",
               f"if {{$ot_n != {12 if a.hier_views else 8}}} {{ error \"macro_place: placed $ot_n\" }}"]
        if a.hier_views:
            # el1011-hbm-smh: the 2 x 2 hardened columns (geom col_xy: "j:tcc" -> [x, y, orient]); x-store overrides xs_xy
            hv = [x.strip() for x in a.hier_views.split(",")]
            if sorted(Path(x).name for x in hv) != ["ot_hbm_accel_smh_bdc", "ot_hbm_accel_smh_tcc"]:
                raise ValueError("--hier-views: the two column view dirs (.../ot_hbm_accel_smh_tcc,.../ot_hbm_accel_smh_bdc)")
            macros = [SRAM_X] + hv
            extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_smh_tile_hier.tcl"
            if "xs_xy" in g:
                xy = {tuple(int(t) for t in k.split(":")): tuple(v) for k, v in g["xs_xy"].items()}
                tcl[2:2 + len(xy)] = [f"  {{{j}:{mi}}} {{{x} {y}}}" for (j, mi), (x, y) in xy.items()]
            tcl = ["array set ot_cx {"] + [f"  {{{k}}} {{{v[0]} {v[1]} {v[2]}}}" for k, v in g["col_xy"].items()] + ["}"] + tcl
        sdc = sdc_block(a.lat, static_inputs=("xs_*",), lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew, io_ref=a.io_ref,
                        nbr_in="rin* bin* gin*" + (" cgi" if a.cg else ""))
    if a.piece == "tile" and a.hier3:
        # el1011-hbm-smh round 3 (physical spec in el1011-hbm-smh.log): 12 hardened sub-element macros, no SRAM at the top
        w, h = H3_TILE
        pins = tile_pins(w, h, a.variant, cg=a.cg)
        macros = [x.strip() for x in a.hier3.split(",")]
        want = sorted(H3_MASTER[k] for k in H3_DIM)
        if sorted(set(Path(x).name for x in macros)) != sorted(set(want)):
            raise ValueError(f"--hier3 needs the view dirs of {sorted(set(want))}")
        tcl, _slots = h3_tile_macros_tcl(macros)
        extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_smh_tile_hier.tcl"
    elif a.piece in H3_DIM:
        if a.max_layer != "M6":
            raise ValueError(f"--piece {a.piece}: route with --max-layer M6 (the tile owns M7)")
        w, h = H3_DIM[a.piece]
        name = H3_MASTER[a.piece]
        pins = h3_pins(a.piece)
        macros, tcl = [], None
        if a.piece == "xs":
            # the 4 x-store SRAMs as a 2 x 2 block, 21.6 um channels, pins (left / right edges) facing the channels
            macros = [SRAM_X]
            mw, mh = 94.824, 41.04
            xy = {mi: (round(45.36 + (mi % 2) * (mw + 21.6), 3), round(30.24 + (mi // 2) * (mh + 21.6), 3)) for mi in range(4)}
            tcl = ["set ot_n 0", "array set ot_xy {"] + [f"  {{{mi}}} {{{x} {y}}}" for mi, (x, y) in xy.items()] + [
                   "}", "foreach ot_inst [[ord::get_db_block] getInsts] {",
                   "  if {![[$ot_inst getMaster] isBlock]} { continue }",
                   "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
                   "  if {![regexp {g_xm\\[(\\d+)\\]\\.u_x} $n -> mi]} { error \"no slot for $n\" }",
                   "  place_macro -macro_name [$ot_inst getName] -location $ot_xy($mi) -orientation R0",
                   "  incr ot_n", "}", "if {$ot_n != 4} { error \"macro_place: placed $ot_n of 4\" }"]
        extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_smh_child.tcl"
        nbr = {"pt_w": "rin* bin*", "pt_e": "rpm* bm*", "xs": "rl1* bk1* ohl1*", "bdc3": "i_*", "tcl": "i_*",
               "tct": "i_* sum_i* lf_*"}[a.piece]
        sdc = sdc_block(a.lat, nbr_in=nbr, static_inputs=(("xs_*",) if a.piece == "xs" else ()), lat_ff=a.lat_ff,
                        period=a.period, skew=a.skew, die_skew=a.die_skew, io_ref=a.io_ref).replace("[get_ports rst_n]", "[get_ports rst_a]")
    elif a.piece in FC_DIM:
        # hbm-smh/fc: a hardened sub-element of front_c (OT_SMH_FC_HIER; spec in el1011-hbm-smh.log)
        if a.max_layer != "M6":
            raise ValueError(f"--piece {a.piece}: route with --max-layer M6 (front_c owns M7)")
        w, h = FC_DIM[a.piece]
        name = FC_MASTER[a.piece]
        pins = fc_pins(a.piece)
        macros, tcl = [], None
        if a.piece == "fc_bc":
            macros = [SRAM_R]
            tcl = fc_ring_tcl(w, h)
        extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_smh_child.tcl"
        nbr = {"fc_bc": "fd_v fd_d* fq_ret fp_* fsv k1_sr* r3a*", "fc_is": "k0_* fs_v fs_d* fr_rl sv_i",
               "fc_xl": "fx_b* r0a*", "fc_t": "li* fi*", "fc_xr": "xi* li* fi*", "fc_b": "li* fi* xi*"}[a.piece]
        # fc_bc holds front_c's ring macros: their read is the designed two-cycle path (bulk_copy_oq5 RING_MACRO = 1:
        # a group is read at most every other edge and holds its output two cycles), so it carries front_c's ring
        # multicycle (fcbc-r6: TT -80 / -92 = u_ring rd_out 516 ps + group select + wire -> oq*, timed as one cycle)
        sdc = sdc_block(a.lat, nbr_in=nbr, lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew,
                        io_ref=a.io_ref, ring=(a.piece == "fc_bc")).replace("[get_ports rst_n]", "[get_ports rst_a]")
    elif a.piece in ("tcc", "bdc"):
        # el1011-hbm-smh: a hardened column of one leaf (OT_SMH_HIER).  Inputs (the j-stage pin flops) on the W edge,
        # lane-major (i_w[k] beside i_x[k]), M4 every 4 tracks (5.2 b/um); results on the E edge; clk / rst_a north.
        w, h = g[a.piece + "_w"], g[a.piece + "_h"]
        name = "ot_hbm_accel_smh_" + a.piece
        if a.max_layer != "M6":
            # layer contract (el1011-hbm-smh, PDN-0006 on 732c417d6): a column routes M2-M6 and powers on M6; the tile
            # owns M7 (its straps land on the column pins, and its pass-through crosses over the columns)
            raise ValueError("--piece tcc / bdc: route with --max-layer M6 (the tile owns M7)")
        nw = P["LBS"] * 266 if a.piece == "bdc" else P["LSB"] * 16
        ins = ["i_v", "i_first", "i_last"] + (["i_fp4"] if a.piece == "bdc" else []) + bits("i_tag", P["TAGW"])
        for k in range(nw):
            ins += [f"i_w[{k}]", f"i_x[{k}]"]
        outs = ["ov", "fault"] + bits("y", 32) + bits("otag", P["TAGW"])
        def edge(names, x):
            y0 = trk((h - len(names) * 0.192) / 2)
            if y0 < 1.0:
                raise ValueError(f"{a.piece}: {len(names)} pins do not fit a {h} um edge at 0.192")
            return [(nm, "M4", "", x, round(y0 + i * 0.192, 3)) for i, nm in enumerate(names)]
        # bdc sits WEST of the x-store stack in the tile (R0, no mirror: mirrored pins leave the track grid), so its
        # operand inputs face EAST toward the SRAM capture flops; tcc sits east of the stack with its inputs WEST.
        pins = (edge(ins, w) + edge(outs, 0.0)) if a.piece == "bdc" else (edge(ins, 0.0) + edge(outs, w))
        xc = round(round((w / 2 - 0.012) / 0.048) * 0.048 + 0.012, 3)
        pins += [("clk", "M5", "", xc, h), ("rst_a", "M5", "", round(xc + 0.48, 3), h)]
        macros = []
        tcl = None
        extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_block.tcl"
        sdc = sdc_block(a.lat, nbr_in="i_*", lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew,
                        io_ref=a.io_ref).replace("[get_ports rst_n]", "[get_ports rst_a]")
    elif a.piece == "be":
        w, h = g.get("be_w", g["tile_w"]), g["be_h"]
        pins = be_pins(w, h, a.variant, cg=a.cg)
        macros = []
        name = "ot_hbm_accel_smh_be_" + ("e" if a.variant == "toE" else "w") + ("g" if a.cg else "")
        tcl = None
        extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_block.tcl"
        sdc = sdc_block(a.lat, nbr_in="gin* qin*" + (" cgi" if a.cg else ""), lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew, io_ref=a.io_ref)
    elif a.piece in STRIPS:
        pos, die, hcore = floorplan(g)
        pins, h = strip_pins(g, hcore, a.piece)
        w = g["front_w"]
        name = "ot_hbm_accel_smh_" + a.piece
        tcl = None
        macros = []
        if a.piece == "front_c":
            macros = [SRAM_R]
            mw, mh = 96.552, 69.66
            ch = float(g.get("front_channel_um", 120.0))
            xl, xr = qd(w / 2 - ch / 2 - mw), q(w / 2 + ch / 2)
            y0 = qd(h / 2 - 2.5 * (mh + 4.32))
            tcl = ["set ot_n 0", "foreach ot_inst [[ord::get_db_block] getInsts] {",
                   "  if {![[$ot_inst getMaster] isBlock]} { continue }",
                   "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
                   "  if {![regexp {g_grp\\[(\\d+)\\]\\.g_mb\\[(\\d+)\\]\\.u_ring} $n -> gg mb]} { error \"no slot for $n\" }",
                   f"  set y [expr {{{y0} + $mb * {q(mh + 4.32)}}}]",
                   f"  if {{$gg == 0}} {{ place_macro -macro_name [$ot_inst getName] -location [list {xl} $y] -orientation MY }} \\",
                   f"  else {{ place_macro -macro_name [$ot_inst getName] -location [list {xr} $y] -orientation R0 }}",
                   "  incr ot_n", "}", "puts \"ot macro_place: $ot_n ring macros\""]
        if a.fc_hier:
            # hbm-smh/fc: front_c = 9 hardened children (6 masters), wiring only at the top
            if a.piece != "front_c" or not g.get("fc_hier"):
                raise ValueError("--fc-hier: --piece front_c with an fc_hier geometry")
            macros = [x.strip() for x in a.fc_hier.split(",")]
            if sorted(Path(x).name for x in macros) != sorted(FC_MASTER.values()):
                raise ValueError(f"--fc-hier needs the view dirs of {sorted(FC_MASTER.values())}")
            tcl = fc_parent_macros_tcl()
            extra["PDN_TCL"] = "/src/tools/chip_assembly/tcl/pdn_smh_tile_hier.tcl"
        sdc = sdc_strip(a.piece, a.lat, lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew)
        hops = STRIP_HOPS[a.piece] if not a.fc_hier else "ot_pin_place_auto {.*} 14\n"
        if g.get("front_channel_um", 120.0) != 120.0 and not a.fc_hier:
            if a.piece == "front_c":
                shift = w - 432.0
                channel = float(g["front_channel_um"])
                def widen_hop(match):
                    prefix, xlo, xhi, suffix = match.groups()
                    xlo, xhi = float(xlo), float(xhi)
                    if "g_bs" in prefix and "1" in prefix or "g_h" in prefix and ("2" in prefix or "3" in prefix):
                        xlo += shift; xhi += shift
                    elif xlo >= 152 and xhi <= 272:
                        xlo = w / 2 + (xlo - 212) * channel / 120
                        xhi = w / 2 + (xhi - 212) * channel / 120
                    elif "u_prd" in prefix:
                        xhi += shift
                    return f"{prefix} {xlo:g} {xhi:g}{suffix}"
                hops = re.sub(r"^(ot_place \{[^\n]*?\}) ([0-9.]+) ([0-9.]+)( [0-9.]+ [0-9.]+)$", widen_hop, hops, flags=re.M)
                # Converter register stations beside skid/issue, in the enlarged
                # macro corridor. Pin-facing register placement remains literal.
                hops += f"ot_place {{^g_int8\\.}} {w/2-channel/2:g} {w/2+channel/2:g} 100 140\n"
        (work / "hops.tcl").write_text(HOPS[:HOPS.index("ot_pin_place_auto {.*} 14")] + hops)
        extra["POST_TAPCELL_TCL"] = "/work/hops.tcl"
    else:
        pos, die, hcore = floorplan(g)
        w, h = g["front_w"], hcore
        pins = front_pins(g, hcore)
        macros = [SRAM_R]
        name = "ot_hbm_accel_smh_front"
        mw, mh = 96.552, 69.66
        # the 2 x 5 ring macros: slice mb in row mb, group 0 left (MY: pins on its right edge) and group 1 right (R0:
        # pins on its left edge), both facing a central channel where the bulk copy's queue and control sit
        ch = float(g.get("front_channel_um", 120.0))
        xl, xr = qd(w / 2 - ch / 2 - mw), q(w / 2 + ch / 2)
        y0 = qd(h / 2 - 2.5 * (mh + 4.32))
        tcl = ["set ot_n 0", "foreach ot_inst [[ord::get_db_block] getInsts] {",
               "  if {![[$ot_inst getMaster] isBlock]} { continue }",
               "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
               "  if {![regexp {g_grp\\[(\\d+)\\]\\.g_mb\\[(\\d+)\\]\\.u_ring} $n -> gg mb]} { error \"no slot for $n\" }",
               f"  set y [expr {{{y0} + $mb * {q(mh + 4.32)}}}]",
               f"  if {{$gg == 0}} {{ place_macro -macro_name [$ot_inst getName] -location [list {xl} $y] -orientation MY }} \\",
               f"  else {{ place_macro -macro_name [$ot_inst getName] -location [list {xr} $y] -orientation R0 }}",
               "  incr ot_n", "}", "puts \"ot macro_place: $ot_n ring macros\""]
        sdc = sdc_block(a.lat, element_io=True, ring=True, lat_ff=a.lat_ff, period=a.period, skew=a.skew, die_skew=a.die_skew, io_ref=a.io_ref)
        # (round 7) long-haul pipeline flops pre-placed FIRM along their routes (the placer clumped each chain at
        # one end: the retire chain sat at y 60-211 with the issue at ~900): see HOPS
        (work / "hops.tcl").write_text(HOPS)
        extra["POST_TAPCELL_TCL"] = "/work/hops.tcl"
    if a.piece in FC_HOPS and not a.pin_flops:
        # hbm-smh/fc: unanchored children still get their pass stages spread (no adjacent zero-logic pairs)
        k0 = HOPS.index("proc ::ot_place ")
        (work / "hops.tcl").write_text(PIN_HDR + HOPS[k0:HOPS.index("\n}\n", k0) + 3] + FC_HOPS[a.piece])
        extra["POST_TAPCELL_TCL"] = "/work/hops.tcl"
    if (a.piece in ("tile", "be", "tcc", "bdc", "pt_w", "pt_e") or a.piece in FC_DIM) and a.pin_flops:
        # m2: the pass-through landing registers join the input face's strip (tile W 16 um overflowed: --pin-depth)
        ht = PIN_TCL.replace("ot_pin_place_auto {.*} 16\n", f"ot_pin_place_auto {{.*}} {a.pin_depth}\n")
        if a.piece in FC_HOPS:
            # hbm-smh/fc: the pass stages with no port on either side, spread along their path (no adjacent zero-logic
            # pairs: pt_e RSZ-0060 lesson)
            k0 = HOPS.index("proc ::ot_place ")
            ht += HOPS[k0:HOPS.index("\n}\n", k0) + 3] + FC_HOPS[a.piece]
        (work / "hops.tcl").write_text(ht)
        extra["POST_TAPCELL_TCL"] = "/work/hops.tcl"
    die = (round(w, 3), round(h, 3))
    (work / "pins.tcl").write_text(pin_tcl(pins))
    if tcl:
        (work / "macros.tcl").write_text("\n".join(tcl) + "\n")
    (work / "constraint.sdc").write_text(sdc)
    nick = f"smh_{a.piece}_{a.variant}_{a.label}"
    (work / "config.mk").write_text(config_mk(name, nick, die, macros, extra))
    if getattr(a, "rch_nonempty", False):
        if a.piece != "front_s":
            raise ValueError("--rch-nonempty applies only to front_s")
        with (work / "config.mk").open("a") as f:
            f.write("export VERILOG_FILES += /src/rtl/hbm_accel/sm/ot_hbm_accel_smh_csnk_ne.sv\n"
                    "export VERILOG_DEFINES += -DOT_SMH_RCH_NONEMPTY\n")
    if getattr(a, "cg", False):
        if a.piece not in ("tile", "be"):
            raise ValueError("--cg applies to tile / be")
        pre = ["# redesign-hbm --cg: ICG push-down (one clone per sink cluster) before CTS"]
        if "PRE_CTS_TCL" in extra:
            pre.append("source " + extra["PRE_CTS_TCL"])
        if not getattr(a, "cg_nopush", False):
            pre.append("source /src/physical/common_flow/cg_pushdown.tcl")
        (work / "pre_cts_cg.tcl").write_text("\n".join(pre) + "\n")
        with (work / "config.mk").open("a") as f:
            f.write("export VERILOG_FILES += /src/rtl/hdc/ot_hdc_cg.sv /src/rtl/hbm_accel/cg/ot_cg_tile.sv\n"
                    "export PRE_CTS_TCL = /work/pre_cts_cg.tcl\n")
    defs = (["OT_SMH_CG_ENREG"] if getattr(a, "cg_enreg", False) else []) + (["OT_SMH_XLK"] if getattr(a, "xlk", False) else [])
    # fe-push-hphys-1010: valid-only reset in the fp32 add pipelines / bmul (--drst0), the port reset through ot_rst_relay (--rst-relay)
    defs += (["OT_FP_DATA_NORST", "OT_SMH_DRST0"] if getattr(a, "drst0", False) else []) + (["OT_SMH_RSTRELAY"] if getattr(a, "rst_relay", False) else [])
    if getattr(a, "rst_relay", False):
        if a.piece not in ("tile", "tcc", "bdc") and a.piece not in H3_DIM:
            raise ValueError("--rst-relay applies to the tile / its sub-elements")
        with (work / "config.mk").open("a") as f:
            f.write("export VERILOG_FILES += /src/rtl/lib/ot_rst_relay.sv\n")
    if defs:
        if getattr(a, "cg_enreg", False) and not (getattr(a, "cg", False) and a.piece == "tile"):
            raise ValueError("--cg-enreg applies to the gated tile (--cg --piece tile)")
        if getattr(a, "xlk", False) and a.piece not in ("tile", "tcc", "bdc") and a.piece not in H3_DIM:
            raise ValueError("--xlk applies to the tile (its x-store macros)")
        with (work / "config.mk").open("a") as f:
            f.write("export VERILOG_DEFINES += " + " ".join("-D" + d for d in defs) + "\n")
    int8_enabled = any(x == "ENABLE_INT8=1" for x in (a.top_param or []))
    if int8_enabled:
        if a.piece != "front_c":
            raise ValueError("ENABLE_INT8 belongs to the central strip candidate")
        with (work / "config.mk").open("a") as f:
            f.write("export VERILOG_FILES += /src/rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv\n")
    if getattr(a, "hold_mm", False):
        with (work / "config.mk").open("a") as f:
            f.write("export OT_HOLD_MM = 1\n")
    if a.piece in FC_DIM or a.fc_hier:
        with (work / "config.mk").open("a") as f:
            f.write("export VERILOG_DEFINES += -DOT_SMH_FC_HIER\n"
                    + ("export VERILOG_FILES += /src/rtl/lib/ot_rst_relay.sv\n" if a.piece in FC_DIM else "")
                    + ("export VERILOG_FILES += /src/rtl/hbm_accel/sm/ot_hbm_accel_int8_line.sv\n" if a.piece == "fc_is" else ""))
    if a.piece in ("tcc", "bdc") or a.piece in H3_DIM or a.hier_views or a.hier3:
        defs_h = "export VERILOG_DEFINES += -DOT_SMH_HIER\n"
        if a.piece in ("tcc", "bdc") or a.piece in H3_DIM:
            defs_h += "export VERILOG_FILES += /src/rtl/lib/ot_rst_relay.sv\n" if not getattr(a, "rst_relay", False) else ""
        with (work / "config.mk").open("a") as f:
            f.write(defs_h)
    hier_tt = a.piece in ("tcc", "bdc") or a.piece in H3_DIM or bool(a.hier_views) or bool(a.hier3) or a.piece in FC_DIM or bool(a.fc_hier)
    write_abstract(work, name, macros, name, tt=hier_tt)
    if a.top_param:
        # e.g. --top-param REQCR=1: the hardened master built with a non-default parameter (ORFS VERILOG_TOP_PARAMS)
        (work / "config.mk").write_text((work / "config.mk").read_text() + "export VERILOG_TOP_PARAMS = "
                                        + " ".join(" ".join(x.split("=", 1)) for x in a.top_param) + "\n")
    mx = " ".join(f"{k}={v}" for k, v in (x.split("=", 1) for x in (a.make_var or [])))
    run_sh(work, a.label, a.src, a.need, a.cores, macros, target=a.stop_after or "finish", admit=not a.no_admit,
           make_extra=(mx + " ") if mx else "", tt=hier_tt)
    (work / "geometry.json").write_text(json.dumps(dict(piece=a.piece, variant=a.variant, die=die, geom=g,
                                                        pins=len(pins)), indent=1) + "\n")
    if getattr(a, "hold_mm", False):
        script = work / "run.sh"
        content = script.read_text()
        hook = "python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts; "
        token = "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; make"
        if content.count(token) != 1:
            raise ValueError("multi-mode container patch anchor missing")
        script.write_text(content.replace(token, hook + token))
    print(f"wrote {work}: {name} {a.variant} die {die} pins {len(pins)} macros {len(macros)}")



# ---------------- hbm-smh/fc OT_SMH_FC_HIER: front_c as hardened sub-elements (spec: el1011-hbm-smh.log [hbm-smh/fc]) ----
# front_c 898.56 x 1088.64 (geom fc_hier, front_w 898.56, tile 587.52 x 1080).  Children route M2-M6 (power M6); the
# front_c top owns M7 and holds no flops.  E-side copies of fc_t / fc_xr / fc_b are MY images (w = 0.024 mod 0.048).
FC_DIM = {"fc_bc": (388.8, 479.52), "fc_is": (388.8, 280.8), "fc_xl": (302.4, 297.36),
          "fc_t": (216.024, 216.0), "fc_xr": (216.024, 151.2), "fc_b": (216.024, 302.4)}
FC_MASTER = {k: "ot_hbm_accel_smh_" + k for k in FC_DIM}
FC_EX = 678.192                # E-side MY origin x (on the 0.048 grid; pins map onto tracks)
FC_POS = {"u_bc": ("fc_bc", 254.88, 4.32, "R0"), "u_is": ("fc_is", 254.88, 494.64, "R0"),
          "u_xl": ("fc_xl", 298.08, 786.24, "R0"),
          "u_tw": ("fc_t", 4.32, 872.64, "R0"), "u_te": ("fc_t", FC_EX, 872.64, "MY"),
          "u_rw": ("fc_xr", 4.32, 518.4, "R0"), "u_re": ("fc_xr", FC_EX, 518.4, "MY"),
          "u_bw": ("fc_b", 4.32, 0.0, "R0"), "u_be": ("fc_b", FC_EX, 0.0, "MY")}
FC_GEOM = dict(tile_w=587.52, tile_h=1080.0, be_h=77.76, front_w=898.56, gap=8.64, margin=8.64, fc_hier=1)


def fc_face_x(g, strip, side, names):
    """fc_hier N face of front_c (= front_n S face): group A [fx_b, fo_row0] centred over fc_xl, group B (op channel,
    release, barrier) 10.8 um east of fc_xl.  None: the default centred layout."""
    if not g.get("fc_hier") or (strip, side) not in (("front_n", "s"), ("front_c", "n")):
        return None
    fw = g["front_w"]
    # row 0 first: its face register (fc_xl u_m0) sits in fc_xl's NW corner, beside both its W-edge input (from fc_t)
    # and its N-face output (fc_xl 5b228c4a2-cal: TT -95.8 ps at fo_row0 with the bundle on the far side of fx_b)
    a = ([n for n in names if n.startswith(("fo_row0[", "fi_row0["))] + [n for n in names if n.startswith("fx_b[")])
    b = [n for n in names if n not in set(a)]
    x0 = trk((fw - len(a) * PITCH) / 2)
    xb = trk(FC_POS["u_xl"][1] + FC_DIM["fc_xl"][0] + 10.8)
    out = {n: round(x0 + k * PITCH, 3) for k, n in enumerate(a)}
    out.update({n: round(xb + k * PITCH, 3) for k, n in enumerate(b)})
    return out


def fc_pins(m):
    """pin list [(name, layer, edge, x, y)] of front_c sub-element master m (local, R0), aligned to its W instance and
    to front_c's pins (FC_GEOM)."""
    g = FC_GEOM
    w, h = FC_DIM[m]
    pos, die, hcore = floorplan(g)
    fpins, fh = strip_pins(g, hcore, "front_c")
    fp = {p[0]: (p[3], p[4]) for p in fpins}
    inst = {"fc_bc": "u_bc", "fc_is": "u_is", "fc_xl": "u_xl", "fc_t": "u_tw", "fc_xr": "u_rw", "fc_b": "u_bw"}[m]
    ox, oy = FC_POS[inst][1], FC_POS[inst][2]
    P_ = []
    def hf(names, x, y0, pitch=PITCH):
        return [(n, "M4", "", x, round(trk(y0) + i * pitch, 3)) for i, n in enumerate(names)]
    def vf(names, y, x0, pitch=PITCH):
        return [(n, "M5", "", round(trk(x0) + i * pitch, 3), y) for i, n in enumerate(names)]
    def at_face(names, y):
        return [(n, "M5", "", round(fp[n][0] - ox, 3), y) for n in names]
    lt = bits("li", 1082) + bits("fi", 3)
    if m == "fc_bc":
        s = (["fd_v"] + bits("fd_d", 56) + ["fd_ret", "fq_v"] + bits("fq_d", 42) + ["fq_ret", "fp_v"] + bits("fp_d", 1098)
             + ["fsv"] + bits("fo_row3", 818))
        P_ += at_face(s, 0.0)
        n = bits("k0_mv", 36) + bits("k0_d", 1088) + bits("k1_sr", 36) + ["sv_o"]
        P_ += vf(n, h, (w - len(n) * PITCH) / 2)
        P_ += vf(["clk", "rst_a"], h, (w + len(n) * PITCH) / 2 + 8.0, pitch=0.48)
        P_ += hf(bits("r3a", 818), 0.0, 20.0 - oy)
    elif m == "fc_is":
        n = bits("k0_mv", 36) + bits("k0_d", 1088) + bits("k1_sr", 36) + ["sv_i"]
        P_ += vf(n, 0.0, (w - len(n) * PITCH) / 2)
        top = ["fs_v"] + bits("fs_d", 47) + ["fs_ret", "fr_rl"] + bits("fo_pbz", 3)
        P_ += at_face(top, h)
        P_ += vf(["clk", "rst_a"], h, fp["fs_v"][0] - ox - 6.0, pitch=0.48)
        fm = bits("fm", 12)
        for e, x in ((0, 0.0), (1, w)):
            P_ += hf(bits(f"lt{e}", 1082) + fm[6 * e: 6 * e + 3], x, 174.0)
            P_ += hf(bits(f"lb{e}", 570) + fm[6 * e + 3: 6 * e + 6], x, 608.4 + 4.0 - oy)
    elif m == "fc_xl":
        P_ += at_face(bits("fo_row0", 818) + bits("fx_b", 2069), h)
        P_ += hf(bits("xw_w", 2069), 0.0, 4.0) + hf(bits("r0a", 818), 0.0, 210.0)
        P_ += hf(bits("xw_e", 2069), w, 4.0)
        P_ += vf(["clk", "rst_a"], 0.0, w / 2, pitch=0.48)
    elif m == "fc_t":
        P_ += [(f"rout[{i}]", "M4", "", 0.0, round(fp[f"rout_l1[{i}]"][1] - oy, 3)) for i in range(818)]
        P_ += vf(lt, 0.0, 30.0)          # clear of the 24-30 um W / E pin-flop strips
        P_ += vf(["clk", "rst_a"], 0.0, 30.0 + len(lt) * PITCH + 2.0, pitch=0.48)
        P_ += hf(bits("r0a", 818), w, 210.0 + 786.24 - oy)
    elif m == "fc_xr":
        P_ += vf(bits("xi", 2069), h, 8.0) + vf(bits("xo", 2069), 0.0, 8.0)
        P_ += vf(["clk", "rst_a"], 0.0, 8.0 + 2069 * PITCH + 2.0, pitch=0.48)
        P_ += hf(bits("li", 570) + bits("fi", 3), w, 608.4 + 4.0 - oy)
        P_ += hf(bits("lo", 570) + bits("fo", 3), w, 8.0)
    elif m == "fc_b":
        for i in range(2069):
            P_ += [(f"bout[{i}]", "M4", "", 0.0, round(fp[f"bout_l1[{i}]"][1] - oy, 3))]
        P_ += [(f"rout[{i}]", "M4", "", 0.0, round(fp[f"rout_l2[{i}]"][1] - oy, 3)) for i in range(818)]
        P_ += vf(bits("xi", 2069), h, 8.0)
        P_ += vf(["clk", "rst_a"], h, 8.0 + 2069 * PITCH + 2.0, pitch=0.48)
        P_ += hf(bits("li", 570) + bits("fi", 3), w, 230.0)
        P_ += hf(bits("r3a", 818), w, 20.0)
    else:
        raise ValueError(m)
    names = [p_[0] for p_ in P_]
    if len(set(names)) != len(names):
        raise ValueError(f"{m}: duplicate pins")
    for n, layer, _, x, y in P_:
        if not (0 <= x <= w and 0 <= y <= h):
            raise ValueError(f"{m}: pin {n} at {x},{y} outside {w}x{h}")
    return P_


FC_HOPS = {
    # fc_t: H2 at the S-edge pins (x 30-134), O at the W-edge pins (y 137-216): p1 / p2 / M / P stepped between them
    "fc_t": "ot_place {^u_p1[vd]\\.} 60 150 36 60\not_place {^u_p2[vd]\\.} 60 150 76 100\n"
            "ot_place {^u_m1\\.} 70 130 120 150\not_place {^u_p1\\.} 24 70 150 200\n",
    # fc_bc (round 6): u_sk0's registered head (H) + slice control at the N end of the centre channel (x 121-267 between
    # the ring macros' halos), <= ~30 um from the k0_d / k0_mv / k1_sr pins (cal3: TT -205, 397 ps of wire to the pins)
    "fc_bc": "ot_place {^u_sk0\\.g_c\\[[0-9]+\\]\\.(g_d\\.h|u\\.)} 124 264 420 476\n",
    # fc_xl: row 0's face register in the NW corner (W-edge input y 210-288, N-face output x 12-91)
    "fc_xl": "ot_place {^u_m0\\.} 4 90 236 292\n",
    # fc_b: H2 at the E-edge pins (y 230-285), O at the W-edge pins (y 199-277)
    "fc_b": "ot_place {^u_p2[vd]\\.} 150 196 220 270\not_place {^u_m2\\.} 90 130 210 260\n"
            "ot_place {^u_p2\\.} 30 70 205 270\n",
}


def fc_parent_macros_tcl():
    """front_c (OT_SMH_FC_HIER) macro placement: instance-name suffix -> lower-left of the oriented box."""
    tcl = ["set ot_n 0", "array set ot_s {"] + [f"  {{{k}}} {{{x} {y} {o}}}" for k, (_, x, y, o) in FC_POS.items()] + [
           "}", "foreach ot_inst [[ord::get_db_block] getInsts] {",
           "  if {![[$ot_inst getMaster] isBlock]} { continue }",
           "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
           "  set hit \"\"",
           "  foreach k [array names ot_s] { if {[string range $n end-[expr {[string length $k] - 1}] end] eq $k} { set hit $k } }",
           "  if {$hit eq \"\"} { error \"no slot for $n\" }",
           "  set v $ot_s($hit)",
           "  place_macro -macro_name [$ot_inst getName] -location [lrange $v 0 1] -orientation [lindex $v 2]",
           "  incr ot_n", "}",
           f"if {{$ot_n != {len(FC_POS)}}} {{ error \"macro_place: placed $ot_n of {len(FC_POS)}\" }}"]
    return tcl


def fc_ring_tcl(w, h):
    """fc_bc's 10 ring macros: group 0 MY at the W edge (pins right), group 1 R0 at the E edge (pins left), slice mb in
    row mb, 21.6 um from the edges and between rows; the pins face a 152.5-um centre channel."""
    mw, mh = 96.552, 69.66
    xl, xr = 21.6, round(w - 21.6 - mw, 3)
    y0 = 21.6
    return ["set ot_n 0", "foreach ot_inst [[ord::get_db_block] getInsts] {",
            "  if {![[$ot_inst getMaster] isBlock]} { continue }",
            "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
            "  if {![regexp {g_grp\\[(\\d+)\\]\\.g_mb\\[(\\d+)\\]\\.u_ring} $n -> gg mb]} { error \"no slot for $n\" }",
            f"  set y [expr {{{y0} + $mb * {round(mh + 21.6, 3)}}}]",
            f"  if {{$gg == 0}} {{ place_macro -macro_name [$ot_inst getName] -location [list {xl} $y] -orientation MY }} \\",
            f"  else {{ place_macro -macro_name [$ot_inst getName] -location [list {xr} $y] -orientation R0 }}",
            "  incr ot_n", "}", "if {$ot_n != 10} { error \"macro_place: placed $ot_n of 10 ring macros\" }"]


# ---------------- el1011-hbm-smh round 3: the hierarchical SM tile (OT_SMH_HIER), physical spec in el1011-hbm-smh.log ----
H3_TILE = (587.52, 1080.0)
H3_YM2 = 1080.024             # 2 x the mirror axis: leaf 1 = MX image of leaf 0 about y 540.012 (tracks map onto tracks)
H3_DIM = {"pt_w": (302.4, 371.52), "pt_e": (194.4, 371.52), "xs": (302.4, 155.544), "bdc3": (112.32, 142.56),
          "tcl": (86.4, 120.024), "tct": (194.4, 69.144)}
H3_MASTER = {"pt_w": "ot_hbm_accel_smh_pt_w", "pt_e": "ot_hbm_accel_smh_pt_e", "xs": "ot_hbm_accel_smh_xs",
             "bdc3": "ot_hbm_accel_smh_bdc", "tcl": "ot_hbm_accel_smh_tcl", "tct": "ot_hbm_accel_smh_tct"}
H3_BAND_Y = 354.24
H3_XS_X, H3_XS_Y = 10.8, 747.36
H3_TCX = 367.2                 # tct / tcl0 x (tcc region 334.8 + 32.4 input channel)


def _h3_pos():
    """leaf-0 / band macro origins (R0); leaf 1 is derived by mirroring."""
    tw = H3_TILE[0]
    xb0 = trk((H3_DIM["bdc3"][0] - 1084 * 0.096) / 2)
    pos = {"ptw": (10.8, H3_BAND_Y), "pte": (round(tw - 10.8 - H3_DIM["pt_e"][0], 3), H3_BAND_Y),
           "xs": (H3_XS_X, H3_XS_Y), "bdc": (round(H3_XS_X + trk(20.0) - xb0, 3), 924.48),
           "tct": (H3_TCX, 758.16), "tcl0": (H3_TCX, 849.12), "tcl1": (round(H3_TCX + 86.4 + 21.6, 3), 849.12)}
    return pos


def h3_pins(m, T=16):
    """pin list [(name, layer, edge, x, y)] of round-3 master m (local coordinates)."""
    w, h = H3_DIM[m]
    P_ = []
    def hf(names, x, y0, pitch=0.192, layer="M4"):
        return [(n, layer, "", x, round(y0 + i * pitch, 3)) for i, n in enumerate(names)]
    def vf(names, y, x0, pitch=0.096, layer="M5"):
        return [(n, layer, "", round(x0 + i * pitch, 3), y) for i, n in enumerate(names)]
    land = lambda suf: bits("rl1" + suf, 22 + T - 16 + 818 - 22) if False else None
    rbw = 6 + T + 788 + 1 + 7
    def landing(suf):
        return bits("rl1" + suf, rbw) + bits("bk1" + suf, 2069) + bits("ohl1" + suf, 13)
    XL = trk(12.0)
    if m in ("pt_w", "pt_e"):
        ys = tile_edge_slots(H3_TILE[1])
        rin_i, rout_o = ("rin", "rpm") if m == "pt_w" else ("rpm", "rout")
        bin_i, bout_o = ("bin", "bm") if m == "pt_w" else ("bm", "bout")
        for (kind, i), y in ys.items():
            yl = round(y - H3_BAND_Y, 3)
            if not 0.5 < yl < h - 0.5:
                raise ValueError(f"{m}: slot {kind}{i} y {y} outside the band")
            a_, b_ = (rin_i, rout_o) if kind == "r" else (bin_i, bout_o)
            P_ += [(f"{a_}[{i}]", "M4", "", 0.0, yl), (f"{b_}[{i}]", "M4", "", w, yl)]
        if m == "pt_w":
            P_ += vf(landing("_n"), h, XL) + vf(landing("_s"), 0.0, XL)
            P_ += [("clk", "M5", "", trk(w - 8.0), h), ("rst_a", "M5", "", trk(w - 7.5), h)]
        else:
            P_ += [("clk", "M5", "", trk(w / 2), h), ("rst_a", "M5", "", trk(w / 2 + 0.5), h)]
    elif m == "xs":
        P_ += vf(landing(""), 0.0, XL)
        nb = ["o_iv_b", "o_ifirst", "o_ilast", "o_ifp4"] + bits("o_itag", T)
        for k in range(532):
            nb += [f"o_iw[{k}]", f"o_ix[{k}]"]
        P_ += vf(nb, h, trk(20.0))
        x2 = trk(20.0 + len(nb) * 0.096 + 5.0)
        st = bits("xs_a1", 9) + bits("xs_g1", 5) + bits("xs_a2", 7) + bits("xs_g2", 5) + ["clk", "rst_a"]
        P_ += vf(st, h, x2, pitch=0.48)
        ne = ["o_iv_f", "o_ifirst_e", "o_ilast_e"] + bits("o_itag_e", T)
        for k in range(256):
            ne += [f"o_iw[{532 + k}]", f"o_ix[{532 + k}]"]
        P_ += hf(ne, w, trk((h - len(ne) * 0.192) / 2))
    elif m == "bdc3":
        ni = ["i_v", "i_first", "i_last", "i_fp4"] + bits("i_tag", T)
        for k in range(532):
            ni += [f"i_w[{k}]", f"i_x[{k}]"]
        xb0 = trk((w - len(ni) * 0.096) / 2)
        P_ += vf(ni, 0.0, xb0)
        P_ += vf(["ov", "fault"] + bits("y", 32) + bits("otag", T) + ["clk", "rst_a"], h, trk(20.0), pitch=0.192)
    elif m == "tcl":
        ni = ["clk", "rst_a", "i_v", "i_first"]
        for k in range(128):
            ni += [f"i_w[{k}]", f"i_x[{k}]"]
        P_ += vf(ni, h, trk(10.0))
        P_ += vf(bits("sum_o", 256) + ["lfault"], 0.0, trk(10.0))
    elif m == "tct":
        xa, xb = trk(10.0), round(trk(10.0) + 108.0, 3)
        P_ += vf(bits("sum_i", 256)[:256] + ["lf_a"], h, xa)
        P_ += vf([f"sum_i[{256 + k}]" for k in range(256)] + ["lf_b"], h, xb)
        P_ += hf(["i_v", "i_last"] + bits("i_tag", T), 0.0, trk((h - (T + 2) * 0.192) / 2))
        P_ += hf(["ov", "fault"] + bits("y", 32) + bits("otag", T), w, trk((h - (T + 34) * 0.192) / 2))
        P_ += vf(["clk", "rst_a"], 0.0, trk(w / 2), pitch=0.48)
    else:
        raise ValueError(m)
    names = [p_[0] for p_ in P_]
    if len(set(names)) != len(names):
        raise ValueError(f"{m}: duplicate pins")
    for n, layer, _, x, y in P_:
        if not (0 <= x <= w and 0 <= y <= h):
            raise ValueError(f"{m}: pin {n} at {x},{y} outside {w}x{h}")
    return P_


def h3_tile_macros_tcl(views):
    """tile macro placement (instance regex -> origin, orientation) for the 12 round-3 macros."""
    pos = _h3_pos()
    H = dict(H3_DIM)
    slots = {}
    slots["u_ptw"] = (*pos["ptw"], "R0")
    slots["u_pte"] = (*pos["pte"], "R0")
    for j in range(2):
        for key, inst, dim in (("xs", "u_xs", "xs"), ("bdc", "u_bdc", "bdc3"), ("tct", "u_tcc.u_tr", "tct"),
                               ("tcl0", "u_tcc.u_h0", "tcl"), ("tcl1", "u_tcc.u_h1", "tcl")):
            x, y = pos[key]
            if abs(y / 0.048 - round(y / 0.048)) > 1e-6:
                raise ValueError(f"leaf-0 origin {key} y {y} off the 0.048 grid (mirror would leave the tracks)")
            if j == 1:
                y = round(H3_YM2 - y - H[dim][1], 3)
            slots[f"g_lf[{j}].u_lh.{inst}"] = (x, y, "R0" if j == 0 else "MX")
    tcl = ["set ot_n 0", "array set ot_s {"] + [f"  {{{k}}} {{{x} {y} {o}}}" for k, (x, y, o) in slots.items()] + [
           "}", "foreach ot_inst [[ord::get_db_block] getInsts] {",
           "  if {![[$ot_inst getMaster] isBlock]} { continue }",
           "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
           "  set hit \"\"",
           "  foreach k [array names ot_s] { if {[string range $n end-[expr {[string length $k] - 1}] end] eq $k} { set hit $k } }",
           "  if {$hit eq \"\"} { error \"no slot for $n\" }",
           "  set v $ot_s($hit)",
           "  place_macro -macro_name [$ot_inst getName] -location [lrange $v 0 1] -orientation [lindex $v 2]",
           "  incr ot_n", "}",
           f"if {{$ot_n != {len(slots)}}} {{ error \"macro_place: placed $ot_n of {len(slots)}\" }}"]
    return tcl, slots

VIEWS = "physical/hbm_accel_smh_views"
PIECES = ["ot_hbm_accel_smh_tile_e", "ot_hbm_accel_smh_tile_w", "ot_hbm_accel_smh_be_e", "ot_hbm_accel_smh_be_w",
          "ot_hbm_accel_smh_front_n", "ot_hbm_accel_smh_front_c", "ot_hbm_accel_smh_front_s"]   # (m3) front strips


def cmd_top(a):
    """The element: pieces placed by abutment slots, element pins over the front, the W13 die budget."""
    work = Path(a.out)
    work.mkdir(parents=True, exist_ok=True)
    g = json.loads(Path(a.geom).read_text()) if a.geom else GEOM
    pos, die, hcore = floorplan(g)
    m = g["margin"]
    # macro placement by instance name
    xy = {}
    nl = P["NC"] // 2
    for c in range(P["NC"]):
        for p in range(P["NP"]):
            xy[f"t:{c}:{p}"] = pos[("tile", c, p)]
        xy[f"b:{c}"] = pos[("be", c)]
    for st in STRIPS:                                     # (m3) the front as three strips
        xy[st] = (pos["front"][0], round(pos["front"][1] + strip_span(g, hcore, st)[0], 3))
    tcl = ["set ot_n 0", "array set ot_xy {"] + [f"  {{{k}}} {{{round(v[0], 3)} {round(v[1], 3)}}}" for k, v in xy.items()] + [
           "}", "foreach ot_inst [[ord::get_db_block] getInsts] {",
           "  if {![[$ot_inst getMaster] isBlock]} { continue }",
           "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
           "  if {[regexp {g_c\\[(\\d+)\\]\\.g_p\\[(\\d+)\\]\\.(?:genblk\\d+\\.)?g_t[ew]\\.u_t} $n -> c p]} { set k t:$c:$p } \\",
           "  elseif {[regexp {g_c\\[(\\d+)\\]\\.(?:genblk\\d+\\.)?g_be_[ew]\\.u_be} $n -> c]} { set k b:$c } \\",
           "  elseif {[regexp {g_fd\\.u_fn} $n]} { set k front_n } elseif {[regexp {g_fd\\.u_fc} $n]} { set k front_c } \\",
           "  elseif {[regexp {g_fd\\.u_fs} $n]} { set k front_s } else { error \"no slot for $n\" }",
           "  place_macro -macro_name [$ot_inst getName] -location $ot_xy($k) -orientation R0",
           "  incr ot_n", "}",
           f"if {{$ot_n != {P['NC'] * P['NP'] + P['NC'] + len(STRIPS)}}} {{ error \"macro_place: placed $ot_n\" }}",
           "puts \"ot macro_place: $ot_n pieces\""]
    (work / "macros.tcl").write_text("\n".join(tcl) + "\n")
    # element pins straight above / below the front's own N / S pins
    fx, fy = pos["front"]
    pins = []
    for name, layer, _, x, y in front_pins(g, hcore):
        if layer == "M5":
            pins.append((name, "M5", "", round(fx + x, 3), die[1] if y > 0 else 0.0))
    # the element clock: north edge over the front's west corner (the front's own clock pin is mid-height west)
    pins.append(("clk", "M5", "", round(round((fx + 4.0 - 0.012) / 0.048) * 0.048 + 0.012, 3), die[1]))
    (work / "pins.tcl").write_text(pin_tcl(pins))
    sdc = ["# ot_hbm_accel_smh element: clock 833 ps, 60 / 25 ps; the W13 die budget on the element pins, unchanged",
           "set clk_period 833",
           "create_clock -name core_clk -period $clk_period [get_ports clk]",
           "set_clock_uncertainty -setup 60 [all_clocks]",
           "set_clock_uncertainty -hold 25 [all_clocks]",
           "set non_clock_inputs [all_inputs -no_clocks]",
           "set_input_delay [expr $clk_period * 0.2] -clock core_clk $non_clock_inputs",
           "set_output_delay [expr $clk_period * 0.2] -clock core_clk [all_outputs]",
           "set_load 3.898 [all_outputs]",
           "set_max_fanout 32 [current_design]"]
    sdc += (ROOT / "rtl/hbm_accel/sm/ot_hbm_accel_sm_v_die_budget.sdc").read_text().splitlines()
    (work / "constraint.sdc").write_text("\n".join(sdc) + "\n")
    views = [f"{VIEWS}/{n}" for n in PIECES]
    extra = {"PLACE_DENSITY": "0.30", "MIN_ROUTING_LAYER": "M4", "MAX_ROUTING_LAYER": "M9", "HOLD_SLACK_MARGIN": "20",
             "PDN_TCL": "/src/tools/chip_assembly/tcl/pdn_smh_top.tcl", "MACRO_PLACE_HALO": "0.5 0.5",
             "CTS_ARGS": "-sink_clustering_enable -repair_clock_nets -macro_clustering_size 1 "
                         "-macro_clustering_max_diameter 20",
             "VERILOG_TOP_PARAMS": ""}
    del extra["VERILOG_TOP_PARAMS"]
    (work / "config.mk").write_text(config_mk("ot_hbm_accel_smh", f"smh_top_{a.label}", die, views, extra))
    # The top exports the same SS/FF view contract as its children. Keep the
    # shared runner's 6_signoff.sdc generation before corner STA.
    write_abstract(work, "ot_hbm_accel_smh", views, "ot_hbm_accel_smh")
    run_sh(work, a.label, a.src, a.need, a.cores, views,
           target=a.stop_after or "finish", admit=not a.no_admit)
    (work / "geometry.json").write_text(json.dumps(dict(die=die, hcore=hcore, geom=g, slots=xy, pins=len(pins)),
                                                   indent=1) + "\n")
    print(f"wrote {work}: element die {die}, {len(xy)} pieces, {len(pins)} pins")


# front 432 um wide (round 4; was 233): the ring macros as a compact 5 x 2 block facing a central channel
GEOM = dict(tile_w=q(319), tile_h=q(509), be_h=q(77), front_w=q(432), gap=GRID, margin=GRID)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("block")
    b.add_argument("--piece", choices=("tile", "be", "front", "tcc", "bdc", "pt_w", "pt_e", "xs", "bdc3", "tcl", "tct", "fc_bc", "fc_is", "fc_xl", "fc_t", "fc_xr", "fc_b") + STRIPS, required=True)
    b.add_argument("--variant", default="toE", choices=("toE", "toW", "one"))
    b.add_argument("--label", required=True)
    b.add_argument("--out", required=True)
    b.add_argument("--geom", default=None)
    b.add_argument("--pd", default="0.60")
    b.add_argument("--max-layer", default="M7", help="top signal layer inside a hardened piece (M2-M7 default: the "
                   "bundle pin fields need the extra tracks; the parent keeps M7/M8 for the abutment hops)")
    b.add_argument("--lat", default="720", help="the block's own measured clock insertion (ps): the parent balances "
                   "internal flops, so a neighbour's flop sits at the same latency relative to this block's pin")
    b.add_argument("--lat-ff", default=None, help="the block's FF clock insertion (ps; default 0.6 x --lat)")
    b.add_argument("--src", required=True, help="host path of the source tree mounted at /src")
    b.add_argument("--need", default="40")
    b.add_argument("--hold-margin", default="10", help="ORFS hold repair margin (ps); sign-off stays 25 ps at FF")
    b.add_argument("--grt-allow", action="store_true", help="global route may finish with overflow and leave it "
                   "to detailed route (sign-off still requires zero DRC)")
    b.add_argument("--cores", default="16")
    b.add_argument("--period", default="833", help="route clock period (ps); sign-off is always 833 (margin rule: "
                   "route at ~770 for +60 ps at 833)")
    b.add_argument("--skew", default="0", help="setup budget on abutting piece ports (ps): the element's region pair "
                   "skew + 25 (90 until the element top measures it)")
    b.add_argument("--die-skew", default="150", help="setup budget on the element pins (cross a die wire, ps)")
    b.add_argument("--pin-flops", action="store_true", help="tile / be: every port flop FIRM at its pin")
    b.add_argument("--pin-depth", default="16", help="tile / be: edge strip depth (um) for the W / E port flops")
    b.add_argument("--hold-buffer-pct", default=None, help="raise repair_timing -max_buffer_percent at CTS / GRT")
    b.add_argument("--io-ref", action="store_true", help="abutting port delays referenced to a register clock pin of "
                   "the block (per-corner insertion) instead of nbr_clk with the SS insertion as source latency")
    b.add_argument("--stop-after", default=None, choices=("cts",), help="ORFS make target to stop at (closure-loop "
                   "calibrate: a CTS-only run)")
    b.add_argument("--no-admit", action="store_true", help="run without /srv/opentallas-scratch/admit.sh (the closure "
                   "loop does its own admission)")
    b.add_argument("--make-var", action="append", default=None, help="extra NAME=VALUE on the ORFS make line")
    b.add_argument("--hold-mm", action="store_true", help="opt-in SS setup/FF hold multi-mode flow repair")
    b.add_argument("--top-param", action="append", default=None, help="NAME=VALUE parameter of the hardened master")
    b.add_argument("--cg", action="store_true", help="tile / be: the COARSE CLOCK-GATED master (redesign-hbm 2026-10-09): "
                   "ot_hbm_accel_smh_{tile,be}_{w,e}g = the same netlist on one ICG (ot_cg_tile) + wake pins cgi / cgo; "
                   "cg_pushdown.tcl clones the ICG per sink cluster before CTS")
    b.add_argument("--cg-nopush", action="store_true", help="--cg: keep the ONE ICG at the root (no cg_pushdown cloning; small pieces: "
                   "the back end's CTS segfaulted with the push-down hook)")
    b.add_argument("--cg-enreg", action="store_true", help="[cg-smt] 2026-10-10: --cg tile: the ICG ENA from one register beside the "
                   "gate (ot_cg_tile ENREG; tile_wg cal: ENA from leaf-insertion cnt/wq, TT -198 ps)")
    b.add_argument("--drst0", action="store_true", help="fe-push-hphys-1010: fp32 add cuts / y / err and the bmul y unreset (valid bits keep the reset)")
    b.add_argument("--rst-relay", action="store_true", help="fe-push-hphys-1010: tile rst_n port -> ot_rst_relay (4 regions, release +3 edges)")
    b.add_argument("--xlk", action="store_true", help="[cg-smt] 2026-10-10: tile: a negedge lockup stage at every x-store macro input "
                   "(0 cycles; macro clock pin late + 47 ps lib hold: FF hold -55..-84 ps at r_addr_in / w_mask_in)")
    b.add_argument("--hier-views", default=None, help="el1011-hbm-smh: tile under OT_SMH_HIER with the hardened columns: TCCDIR,BDCDIR (repo view dirs named after the masters)")
    b.add_argument("--fc-hier", default=None, help="hbm-smh/fc: front_c under OT_SMH_FC_HIER from its hardened children: comma-separated view dirs of ot_hbm_accel_smh_{fc_bc,fc_is,fc_xl,fc_t,fc_xr,fc_b}")
    b.add_argument("--hier3", default=None, help="el1011-hbm-smh round 3: tile from the hardened sub-elements: comma-separated view dirs of ot_hbm_accel_smh_{pt_w,pt_e,xs,bdc,tcl,tct}")
    b.add_argument("--rch-nonempty", action="store_true", help="opt-in front_s cached-nonempty request FIFO candidate")
    t = sub.add_parser("top")
    t.add_argument("--label", required=True)
    t.add_argument("--out", required=True)
    t.add_argument("--geom", default=None)
    t.add_argument("--src", required=True)
    t.add_argument("--need", default="64")
    t.add_argument("--cores", default="24")
    t.add_argument("--stop-after", choices=("floorplan", "cts"), default=None,
                   help="stop at a floorplan check or closure-loop CTS calibration")
    t.add_argument("--no-admit", action="store_true",
                   help="omit the host admission wrapper when the closure loop admits the job")
    a = ap.parse_args(argv)
    if a.cmd == "block":
        cmd_block(a)
    else:
        cmd_top(a)


if __name__ == "__main__":
    main()
