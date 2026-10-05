#!/usr/bin/env python3
"""Floorplan of the 1.2 GHz DS HBM SM element (rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv ENABLE=1, NC 8, SUB 4).

Four sub-quadrants (sp 0 SW, 1 SE, 2 NW, 3 NE) of 8 leaves each; a leaf tile is its 4 x-store SRAMs (stacked), its
BF16 column macro and its block-dot column macro side by side; a quadrant holds its two sub halves (columns 0-3 and
4-7) as two tile columns of 4 tiles, the half that feeds the hub-side column nearer the hub.  The hub (issue, bulk
copy with its 10 ring macros, s1, the column trees and stacks, the boundary channels) sits in the central cross.
Boundary pins sit at the middle of the edges: NoC (d_ req_ rsp_) south, x broadcast (xw_) west, results east,
control / barrier north.

    python3 tools/hbm_accel_sm_v_floorplan.py --views physical/hbm_accel_sm_views --out DIR
writes DIR/macro_place.tcl and DIR/floorplan.json (die / core area, pin regions, the run_abi3_physical args).
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRAM_X = ROOT / "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.lef"
SRAM_R = ROOT / "physical/hbm_accel_macros/ot_sram_1r1w_512x256_m1_r2c2/ot_sram_1r1w_512x256_m1_r2c2.lef"


def lef_size(p: Path):
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", p.read_text())
    return float(m.group(1)), float(m.group(2))


def snap(v, q):
    return round(round(v / q) * q, 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--views", type=Path, default=ROOT / "physical/hbm_accel_sm_views")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--gap", type=float, default=8.0, help="gap between macros inside a tile")
    ap.add_argument("--tile-gap-x", type=float, default=40.0)
    ap.add_argument("--tile-gap-y", type=float, default=24.0)
    ap.add_argument("--hub-x", type=float, default=160.0, help="width of the vertical hub channel")
    ap.add_argument("--hub-y", type=float, default=200.0, help="height of the horizontal hub channel")
    ap.add_argument("--margin", type=float, default=30.0)
    a = ap.parse_args()
    tw, th = lef_size(a.views / "ot_hbm_accel_tc16/ot_hbm_accel_tc16.lef")
    bw, bh = lef_size(a.views / "ot_hbm_accel_bd_col/ot_hbm_accel_bd_col.lef")
    xw, xh = lef_size(SRAM_X)
    rw, rh = lef_size(SRAM_R)
    g = a.gap
    xs_h = 4 * xh + 3 * 2.0
    tile_w = xw + g + tw + g + bw
    tile_h = max(xs_h, th, bh)
    quad_w = 2 * tile_w + a.tile_gap_x
    quad_h = 4 * tile_h + 3 * a.tile_gap_y
    hub_x = max(a.hub_x, 0.0)
    hub_y = max(a.hub_y, 2 * rh + 3 * g)
    core_w = 2 * quad_w + hub_x + 2 * a.tile_gap_x
    core_h = 2 * quad_h + hub_y + 2 * a.tile_gap_y
    m = a.margin
    die_w, die_h = snap(core_w + 2 * m, 0.432), snap(core_h + 2 * m, 0.27)
    place = {}
    # quadrant origins (lower-left of the quadrant's tile area)
    qx = {0: m + a.tile_gap_x / 2, 1: m + quad_w + hub_x + 1.5 * a.tile_gap_x}
    qy = {0: m + a.tile_gap_y / 2, 1: m + quad_h + hub_y + 1.5 * a.tile_gap_y}
    for sp in range(4):
        east, north = sp % 2, sp // 2
        for h in range(2):
            # the tile column of half h: half 0 nearer the hub (inner column)
            col = (1 - h) if east == 0 else h
            for r in range(4):
                c = h * 4 + r
                # the row of column c: rows nearer the hub first
                row = (3 - r) if north == 0 else r
                x0 = qx[east] + col * (tile_w + a.tile_gap_x)
                y0 = qy[north] + row * (tile_h + a.tile_gap_y)
                # inner (hub-side) macros: the tile is mirrored in x on the west side so the SRAMs face outward
                if east == 0:
                    xb, xt, xx = x0, x0 + bw + g, x0 + bw + g + tw + g
                else:
                    xx, xt, xb = x0, x0 + xw + g, x0 + xw + g + tw + g
                key = f"{sp}:{h}:{c}"
                place[f"bd:{key}"] = (xb, y0 + (tile_h - bh) / 2)
                place[f"tc:{key}"] = (xt, y0 + (tile_h - th) / 2)
                for k in range(4):
                    place[f"x:{key}:{k}"] = (xx, y0 + (tile_h - xs_h) / 2 + k * (xh + 2.0))
    # ring: 2 groups x 5 macros, two rows in the centre of the horizontal hub channel
    cx, cy = die_w / 2, die_h / 2
    for gg in range(2):
        for mb in range(5):
            x = cx - (5 * rw + 4 * g) / 2 + mb * (rw + g)
            y = cy - rh - g / 2 if gg == 0 else cy + g / 2
            place[f"ring:{gg}:{mb}"] = (x, y)
    place = {k: (snap(x, 0.432), snap(y, 0.27)) for k, (x, y) in place.items()}
    tcl = [
        "# DS HBM SM element (ot_hbm_accel_sm_v ENABLE=1): macro placement, tools/hbm_accel_sm_v_floorplan.py",
        "set ot_n 0",
        "array set ot_xy {",
    ]
    tcl += [f"  {{{k}}} {{{x} {y}}}" for k, (x, y) in sorted(place.items())]
    tcl += ["}",
            "foreach ot_inst [[ord::get_db_block] getInsts] {",
            "  if {![[$ot_inst getMaster] isBlock]} { continue }",
            "  set n [string map {\"\\\\\" \"\"} [$ot_inst getName]]",
            "  set key \"\"",
            "  if {[regexp {g_l2s\\[(\\d+)\\]\\.g_h\\[(\\d+)\\]\\.g_c\\[(\\d+)\\]\\.u_leaf.*g_xm\\[(\\d+)\\]\\.u_x} $n -> s h c k]} {",
            "    set key \"x:$s:$h:$c:$k\"",
            "  } elseif {[regexp {g_l2s\\[(\\d+)\\]\\.g_h\\[(\\d+)\\]\\.g_c\\[(\\d+)\\]\\.u_leaf.*u_bd} $n -> s h c]} {",
            "    set key \"bd:$s:$h:$c\"",
            "  } elseif {[regexp {g_l2s\\[(\\d+)\\]\\.g_h\\[(\\d+)\\]\\.g_c\\[(\\d+)\\]\\.u_leaf.*u_tc} $n -> s h c]} {",
            "    set key \"tc:$s:$h:$c\"",
            "  } elseif {[regexp {g_grp\\[(\\d+)\\]\\.g_mb\\[(\\d+)\\]\\.u_ring} $n -> gg mb]} {",
            "    set key \"ring:$gg:$mb\"",
            "  }",
            "  if {$key eq \"\" || ![info exists ot_xy($key)]} { error \"macro_place: no slot for $n ($key)\" }",
            "  set xy $ot_xy($key)",
            "  place_macro -macro_name [$ot_inst getName] -location $xy -orientation R0",
            "  incr ot_n",
            "}",
            f"if {{$ot_n != {len(place)}}} {{ error \"macro_place: placed $ot_n of {len(place)}\" }}",
            "puts \"ot macro_place: $ot_n macros placed\""]
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "macro_place.tcl").write_text("\n".join(tcl) + "\n")
    mid = lambda L: (round(L * 0.25, 1), round(L * 0.75, 1))  # noqa: E731
    fp = dict(die=[0, 0, die_w, die_h], core=[snap(m / 2, 0.432), snap(m / 2, 0.27), snap(die_w - m / 2, 0.432),
                                             snap(die_h - m / 2, 0.27)],
              tile=dict(w=round(tile_w, 3), h=round(tile_h, 3)), quad=dict(w=round(quad_w, 3), h=round(quad_h, 3)),
              macros=dict(tc=[tw, th], bd=[bw, bh], xstore=[xw, xh], ring=[rw, rh], count=len(place)),
              macro_area_um2=round(32 * (tw * th + bw * bh) + 128 * xw * xh + 10 * rw * rh, 1),
              die_area_um2=round(die_w * die_h, 1),
              pin_regions=[f"^(d_|req_|rsp_).*=bottom:{mid(die_w)[0]}-{mid(die_w)[1]}",
                           f"^xw_.*=left:{mid(die_h)[0]}-{mid(die_h)[1]}",
                           f"^(rv|rrow|rdata|fault)$=right:{mid(die_h)[0]}-{mid(die_h)[1]}",
                           f"^(start|op_|busy|arrive|release).*=top:{mid(die_w)[0]}-{mid(die_w)[1]}"])
    (a.out / "floorplan.json").write_text(json.dumps(fp, indent=1) + "\n")
    print(json.dumps({k: fp[k] for k in ("die", "tile", "quad", "macros", "macro_area_um2", "die_area_um2")}))


if __name__ == "__main__":
    main()
