#!/usr/bin/env python3
"""H16 attention tile as a parent of four hardened quads (ot_attn_tile_m6h1p): two quad rows, the left quad of a row
mirrored (MY) so both quads' input edges face one central register channel; origins on the quad's M4 / M5 pin grids.
Writes the MACRO_PLACEMENT_TCL and the IO constraint (inputs on the bottom edge under the channel) and prints the die.

    python3 tools/hbm_attn_quad_parent_place.py --lef physical/hbm_attn_tile_r/quad/ot_attn_tile_m6h1q/ot_attn_tile_m6h1q.lef \
        --out physical/hbm_attn_tile_r/macro_placement_p16.tcl --io physical/hbm_attn_tile_r/io_p16.tcl
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
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--io", type=Path, required=True)
    ap.add_argument("--channel", type=float, default=60.0)
    ap.add_argument("--rowgap", type=float, default=20.0)
    ap.add_argument("--margin", type=float, default=10.0)
    ap.add_argument("--m9-lattice", action="store_true",
                    help="also put each quad's M9 VDD / VSS pins on the parent's M9 strap lattice (pdn.tcl: pitch 5.4, "
                         "offset 1.5 from x 0), so physical/hbm_attn_tile_r/quad_m9_bridge.tcl can join them")
    a = ap.parse_args()
    lef = a.lef.read_text()
    w, h = (round(float(x) * 1000) for x in re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef).groups())
    # pin phases: M4 (horizontal) by y centre, M5 (vertical) by x centre
    ph4, ph5 = set(), set()
    for lay, x0, y0, x1, y1 in re.findall(r"LAYER (M4|M5) ;\s+RECT\s+([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)", lef):
        xc, yc = round((float(x0) + float(x1)) * 500), round((float(y0) + float(y1)) * 500)
        (ph4.add(yc % 48) if lay == "M4" else ph5.add(xc % 48))
    assert len(ph4) <= 1 and len(ph5) <= 1, (ph4, ph5)
    p4 = ph4.pop() if ph4 else 12
    p5 = ph5.pop() if ph5 else 12
    C, G, E = (round(v * 1000) for v in (a.channel, a.rowgap, a.margin))
    y_ph = (12 - p4) % 48                           # R0 and MY keep y
    xr_ph = (12 - p5) % 48                          # R0: x0 + p5 on track 12
    xm_ph = (12 - (w - p5)) % 48                    # MY: x0 + w - p5 on track 12
    x0 = up(E, xm_ph)
    x1 = up(x0 + w + C, xr_ph)
    if a.m9_lattice:
        vss = re.search(r"PIN VSS\b(.*?)END VSS", lef, re.S).group(1)
        xs, lay = [], None
        for ln in vss.splitlines():
            t = ln.split()
            if t[:1] == ["LAYER"]:
                lay = t[1]
            elif t[:1] == ["RECT"] and lay == "M9":
                xs.append(round((float(t[1]) + float(t[3])) * 500))
        pv = {x % 5400 for x in xs}
        pv = max(pv, key=lambda v: sum(1 for x in xs if x % 5400 == v))   # the regular lattice (not a partial strap)
        x0 = next(v for v in range(x0, x0 + 10800 * 2, 48) if (v - x0) % 48 == 0 and (v + w - pv - 1500) % 5400 == 0)
        x1 = next(v for v in range(x1, x1 + 10800 * 2, 48) if (v - x1) % 48 == 0 and (v + pv - 1500) % 5400 == 0)
    y0 = up(E, y_ph)
    y1 = up(y0 + h + G, y_ph)
    dw = math.ceil((x1 + w + E) / 54) * 54
    C = x1 - x0 - w
    dh = math.ceil((y1 + h + E) / 270) * 270
    L = [f"# H16 parent of four quads (tools/hbm_attn_quad_parent_place.py): quad {w/1000} x {h/1000} um, channel {C/1000} um,",
         f"# row gap {G/1000} um; quad pin phases M4 y {p4} / M5 x {p5} nm; die {dw/1000} x {dh/1000} um"]
    for y, yy in enumerate((y0, y1)):
        for x, (xx, o) in enumerate(((x0, "MY"), (x1, "R0"))):
            L.append(f"place_macro -macro_name {{g_y\\[{y}\\].g_x\\[{x}\\].u_q}} -location {{{xx/1000:.3f} {yy/1000:.3f}}} "
                     f"-orientation {o} -exact")
    L += ["set ot_n 0",
          "foreach ot_i [[ord::get_db_block] getInsts] {",
          "  if {[[$ot_i getMaster] getName] ne \"ot_attn_tile_m6h1q\"} {continue}",
          "  $ot_i setPlacementStatus FIRM",
          "  foreach ot_t [$ot_i getITerms] {",
          "    set ot_m [[$ot_t getMTerm] getName]",
          "    if {$ot_m ne \"ib\\[0\\]\" && $ot_m ne \"clk\" && $ot_m ne \"oy\\[0\\]\" && $ot_m ne \"oy\\[127\\]\"} {continue}",
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
          "if {$ot_n != 4} {error \"expected 4 quads, placed $ot_n\"}",
          "puts OT_P16_QUADS_PLACED_ON_GRID"]
    a.out.write_text("\n".join(L) + "\n")
    xc = (x0 + w + x1) / 2000
    a.io.write_text(f"""# H16 quad parent: every input port on the bottom edge under the register channel (x {xc:.1f} um).
set ot_ins {{}}
foreach ot_p [get_ports *] {{
  if {{[get_property $ot_p direction] eq "input"}} {{ lappend ot_ins [get_full_name $ot_p] }}
}}
puts "OT_IO_BOTTOM_CHANNEL inputs=[llength $ot_ins]"
set_io_pin_constraint -pin_names $ot_ins -region bottom:{xc - 170:.1f}-{xc + 170:.1f}
""")
    print(f"die {dw/1000} {dh/1000} x {x0} {x1} y {y0} {y1} phases M4 {p4} M5 {p5}")


if __name__ == "__main__":
    main()
