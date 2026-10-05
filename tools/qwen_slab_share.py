#!/usr/bin/env python3
"""Size the Qwen3-8B ROM band-slab port-group share (results/rtl/qwen_slab_share_20261005).

One port group (rtl/physical/ot_qwen_slab_port_group.sv: 16 ot_rom_4096x266_m8 scale banks, post-scale FP32
multipliers, argmax leaves, block-word meso FIFO) is placed and routed in a share of the slab width (777.576 um)
and a swept height.  The b3r16B40 slab abstract keeps a 40 um entry strip at the array-facing face routed M1-M5
only (block words enter on M6 there); everywhere else the slab may use M1-M7.  The element therefore routes
M2-M7 with M6/M7 obstructed over x 0..40 um (the bw_ face).

`tcl --height H` writes physical/qwen_slab_share/macro_place_h<H>.tcl: the 4 x 4 bank array (R0, columns as
qwen_slab_m5) with the free height split 40 % to the logic band between the south and north bank pairs and 15 %
to each of the other four gaps, every y on the 2.16 um lattice, plus the strip obstruction.
`args --height H` prints the run_abi3_physical die/core/pin-region arguments for that height."""
import argparse
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
W, ROM_H, LAT_Y, EDGE = 777.576, 62.910, 2.16, 2.16
COLS = (37.8, 231.12, 424.44, 617.76)
STRIP_UM = 40.0
BASE_H = 342.9


def snap(y, q=LAT_Y):
    return round(math.floor(y / q + 1e-9) * q, 3)


def rows(h):
    free = h - 2 * EDGE - 4 * ROM_H
    if free < 4 * LAT_Y:
        raise ValueError(f'height {h} does not fit 4 bank rows')
    g, mid = 0.15 * free, 0.40 * free
    y0 = EDGE + g
    y1 = y0 + ROM_H + g
    y2 = y1 + ROM_H + mid
    y3 = y2 + ROM_H + g
    return [snap(y) for y in (y0, y1, y2, y3)]


def tcl(h):
    ys = rows(h)
    L = ['# tools/qwen_slab_share.py: slab port-group share %.3f x %.3f um; 16 scale banks R0 (4 columns x 4 rows)' % (W, h),
         '# and the b3r16B40 entry strip: M6/M7 obstructed over x 0..%.0f um (the bw_ / array-facing face).' % STRIP_UM,
         'set ot_block [ord::get_db_block]', 'set ot_lut [dict create]',
         'foreach ot_inst [$ot_block getInsts] {', '  if {[[$ot_inst getMaster] isBlock]} {',
         '    dict set ot_lut [string map {"\\\\" ""} [$ot_inst getName]] [$ot_inst getName]', '  }', '}',
         'proc ot_place {name x y orient} {', '  global ot_lut',
         '  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }',
         '  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient', '}']
    for c, x in enumerate(COLS):
        for b, y in enumerate(ys):
            L.append(f'ot_place {{g_col[{c}].g_bank[{b}].u_rom}} {x} {y} R0')
    L += ['set ot_tech [ord::get_db_tech]', 'set ot_dbu [$ot_tech getDbUnitsPerMicron]',
          'foreach ot_l {M6 M7} {',
          f'  odb::dbObstruction_create $ot_block [$ot_tech findLayer $ot_l] 0 0 [expr {{round({STRIP_UM} * $ot_dbu)}}] '
          f'[expr {{round({h} * $ot_dbu)}}]', '}', '']
    return '\n'.join(L)


def args(h):
    lo, hi = snap(h / 2 - 35.0), snap(h / 2 + 35.0)
    return ['--die-area', '0', '0', f'{W}', f'{h}', '--core-area', f'{EDGE}', f'{EDGE}', f'{W - EDGE:.3f}', f'{h - EDGE:.3f}',
            '--pin-region', f'^bw_=left:{lo:g}-{hi:g}', '--pin-region', '^(res_in|tw_)=top',
            '--pin-region', '^(o_|ov$|am_|fault$)=bottom', '--pin-region', f'^(p_|rst_n$|clk$)=right:{lo:g}-{hi:g}']


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mode', choices=['tcl', 'args'])
    ap.add_argument('--height', type=float, required=True)
    a = ap.parse_args(argv)
    h = snap(a.height)
    if a.mode == 'tcl':
        p = ROOT / f'physical/qwen_slab_share/macro_place_h{h:g}.tcl'
        p.write_text(tcl(h))
        print(p.relative_to(ROOT))
    else:
        print(' '.join(f"'{x}'" if any(ch in x for ch in '^$|()') else x for x in args(h)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
