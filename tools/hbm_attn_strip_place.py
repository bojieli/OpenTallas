#!/usr/bin/env python3
"""H16 registered tile ot_attn_tile_m6h1r, two-strip floorplan: 4 rows x 4 leaves; rows 0 / 1 face register strip A
(row 0 R0 with its top-edge pins on the strip, row 1 mirrored MX so its pins face down onto it), rows 2 / 3 strip B;
the ROOT sits in the middle gap between rows 1 and 2.  RTL mapping (ot_attn_tile_m6h1r, RV 0, RMID 0, ROC 0):
g_p = strip, g_h = half strip (columns 0-1 / 2-3), g_r = row side (0 below the strip, 1 above), g_s = column in the half;
each HC register bank drives the 4 leaves of its half strip.  Writes the MACRO_PLACEMENT_TCL and the IO constraint and
prints the die.  Origins: x on the 48 nm M5 grid (the leaf's pins are top-edge M5), y on the 48 nm grid too.

    python3 tools/hbm_attn_strip_place.py --lef physical/hbm_attn_tile_r/ot_attn_hgrp_m6h1t/ot_attn_hgrp_m6h1t.lef \
        --master ot_attn_hgrp_m6h1 --out physical/hbm_attn_tile_r/macro_placement_s5.tcl --io physical/hbm_attn_tile_r/io_s5.tcl
"""
import argparse
import math
import re
from pathlib import Path


def up(v, ph=0, p=48):
    return v + ((ph - v) % p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lef", type=Path, required=True)
    ap.add_argument("--master", default="ot_attn_hgrp_m6h1")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--io", type=Path, required=True)
    ap.add_argument("--strip", type=float, default=60.0)
    ap.add_argument("--mid", type=float, default=40.0)
    ap.add_argument("--gap", type=float, default=12.0)
    ap.add_argument("--margin", type=float, default=10.0)
    ap.add_argument("--half", action="store_true", help="the half tile ot_attn_tile_m6h1s: one strip, rows 0 / 1")
    ap.add_argument("--quad", action="store_true", help="the quad ot_attn_tile_m6h1q: one strip, 2 columns, rows 0 / 1")
    a = ap.parse_args()
    lef = a.lef.read_text()
    w, h = (round(float(x) * 1000) for x in re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef).groups())
    S, M, G, E = (round(v * 1000) for v in (a.strip, a.mid, a.gap, a.margin))
    xs = [up(E)]
    for _ in range(3):
        xs.append(up(xs[-1] + w + G))
    ys = [up(E)]                                   # row 0
    ys.append(up(ys[0] + h + S))                    # row 1 (MX)
    ys.append(up(ys[1] + h + M))                    # row 2
    ys.append(up(ys[2] + h + S))                    # row 3 (MX)
    if a.quad:
        a.half = True
        xs = xs[:2]
    if a.half:
        ys = ys[:2]
    dw = math.ceil((xs[-1] + w + E) / 54) * 54
    dh = math.ceil((ys[-1] + h + E) / 270) * 270
    L = [f"# H16 registered tile, two-strip floorplan (tools/hbm_attn_strip_place.py): leaf {w/1000} x {h/1000} um,",
         f"# strips {S/1000} um (rows 0|1 and 2|3), middle gap {M/1000} um, column gaps {G/1000} um, margins {E/1000} um;",
         f"# die {dw/1000} x {dh/1000} um"]
    for p in range(1 if a.half else 2):
        for hh in range(1 if a.quad else 2):
            for r in range(2):
                for s in range(2):
                    row, col = 2 * p + r, 2 * hh + s
                    n = (f"g_r\\[{r}\\].g_s\\[{s}\\].u_g" if a.quad else
                         f"g_h\\[{hh}\\].g_r\\[{r}\\].g_s\\[{s}\\].u_g" if a.half else
                         f"g_p\\[{p}\\].g_h\\[{hh}\\].g_r\\[{r}\\].g_s\\[{s}\\].u_g")
                    L.append(f"place_macro -macro_name {{{n}}} -location {{{xs[col]/1000:.3f} {ys[row]/1000:.3f}}} "
                             f"-orientation {'R0' if r == 0 else 'MX'} -exact")
    L += ["set ot_b [ord::get_db_block]",
          "set ot_n 0",
          "foreach ot_i [$ot_b getInsts] {",
          f"  if {{[[$ot_i getMaster] getName] ne \"{a.master}\"}} {{continue}}",
          "  $ot_i setPlacementStatus FIRM",
          "  foreach ot_t [$ot_i getITerms] {",
          "    set ot_m [[$ot_t getMTerm] getName]",
          "    if {$ot_m ne \"ib\\[288\\]\" && $ot_m ne \"iv\" && $ot_m ne \"ld_w\\[0\\]\" && $ot_m ne \"rst_n\" && $ot_m ne \"clk\" && $ot_m ne \"oy\\[0\\]\"} {continue}",
          "    set ot_bb [$ot_t getBBox]",
          "    set ot_xc [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}]",
          "    set ot_yc [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]",
          "    set ot_l [[[lindex [[lindex [[$ot_t getMTerm] getMPins] 0] getGeometry] 0] getTechLayer] getName]",
          "    if {$ot_l eq \"M4\" || $ot_l eq \"M6\"} {set ot_ph [expr {$ot_yc % 48}]} else {set ot_ph [expr {$ot_xc % 48}]}",
          "    puts \"OT_PINPHASE [$ot_i getName] [$ot_i getOrient] $ot_m $ot_l centre=$ot_xc,$ot_yc phase=$ot_ph\"",
          "    if {$ot_ph != 12} {error \"pin $ot_m of [$ot_i getName] off the $ot_l track grid (phase $ot_ph)\"}",
          "  }",
          "  incr ot_n",
          "}",
          f"if {{$ot_n != {4 if a.quad else 8 if a.half else 16}}} {{error \"expected {4 if a.quad else 8 if a.half else 16} leaves, placed $ot_n\"}}",
          "puts OT_H16S_MACROS_PLACED_ON_GRID"]
    a.out.write_text("\n".join(L) + "\n")
    if a.quad:
        yc = (ys[0] + h + ys[1]) / 2000
        a.io.write_text(f"""# H4 quad: every input port on the left edge at the register strip (y {yc:.1f} um); the HC bank sits in the strip.
set ot_ins {{}}
foreach ot_p [get_ports *] {{
  if {{[get_property $ot_p direction] eq "input"}} {{ lappend ot_ins [get_full_name $ot_p] }}
}}
puts "OT_IO_LEFT_STRIP inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region left:{yc - 150:.1f}-{yc + 150:.1f}
""")
        print(f"die {dw/1000} {dh/1000} xs {xs} ys {ys}")
        return
    if a.half:
        xc = dw / 2000
        a.io.write_text(f"""# H8 half tile: every input port on the bottom edge centre (x {xc:.1f} um); the ROOT sits in the strip above.
set ot_ins {{}}
foreach ot_p [get_ports *] {{
  if {{[get_property $ot_p direction] eq "input"}} {{ lappend ot_ins [get_full_name $ot_p] }}
}}
puts "OT_IO_BOTTOM_CENTRE inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region bottom:{xc - 170:.1f}-{xc + 170:.1f}
""")
        print(f"die {dw/1000} {dh/1000} xs {xs} ys {ys}")
        return
    ymid = (ys[1] + h + ys[2]) / 2000
    a.io.write_text(f"""# H16 two-strip tile: every input port (the packet, rst_n, clk) on the left edge around the middle gap (y {ymid:.1f} um),
# beside the ROOT bank; the outputs (straight from the leaves) are left to the pin placer.
set ot_ins {{}}
foreach ot_p [get_ports *] {{
  if {{[get_property $ot_p direction] eq "input"}} {{ lappend ot_ins [get_full_name $ot_p] }}
}}
puts "OT_IO_LEFT_MIDDLE inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region left:{ymid - 160:.1f}-{ymid + 160:.1f}
""")
    print(f"die {dw/1000} {dh/1000} xs {xs} ys {ys}")


if __name__ == "__main__":
    main()
