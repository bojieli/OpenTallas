#!/usr/bin/env python3
"""Floorplan, placement hook and run_abi3_physical argv for the W2 V4.1 ROM/MAC neighborhoods.

    python3 tools/v41_w2_romac_pnr.py qe --write-hook      # writes physical/abi3/v41_w2_<case>_place.tcl
    python3 tools/v41_w2_romac_pnr.py qe --print           # the run_abi3_physical argv (JSON)

Layout (x left to right): FP8 ROM columns A1 A2 | activation SRAMs (MY, pins east) | lane logic |
activation SRAMs (R0, pins west) | FP4 ROM columns B1 B2.  Each ROM is 125.712 x 119.340 um with its
274 rd_out pins split over the west (130) and east (144) M4 edges; its capture flops are FIXED in the
12 um channel beside the pin they capture, one flop per pin at the pin's row (the MP1/VM local-cut
lesson: fix the first capture at the macro; place every fixed flop in its row's orientation; put the
macro on the joint site/M4-track grid; check PG before detailed route).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MACRO_DIR = "physical/asap7_memory_macros"
ROM = ("ot_rom_8192x274_m8", 125.712, 119.340)
ACT_QE = ("ot_sram_1r1w_64x512_m1_r2c2", 171.288, 77.760)
ACT_ME = ("ot_sram_1r1w_128x256_m1_r2c2", None, None)
MARGIN = 2.16
CH = 12.0          # capture/routing channel beside every ROM edge
GAP = 4.0          # vertical gap between stacked ROMs
QE_SOURCES = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv",
              "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
              "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv"]


def snap(v: float, g: float) -> float:
    return round(round(v / g) * g, 3)


def qe_plan(logic_w: float = 150.0) -> dict:
    rom, rw, rh = ROM
    act, aw, ah = ACT_QE
    col_h = 4 * rh + 3 * GAP
    die_h = snap(2 * MARGIN + 2 * 4.0 + col_h, 0.27)
    x = MARGIN + CH
    macros = []
    cols = {}
    for name in ("A1", "A2"):
        cols[name] = x
        x += rw + CH
    x_sl = x
    x += aw + CH
    x_logic0 = x
    x += logic_w
    x += CH
    x_sr = x
    x += aw + CH
    for name in ("B1", "B2"):
        cols[name] = x
        x += rw + CH
    die_w = snap(x + MARGIN - CH + 4.0, 0.054)
    # ROM b: FP8 0-3 in A1, 4-7 in A2; FP4 8-11 in B1, 12-15 in B2 (bottom to top)
    for b in range(16):
        col = ("A1", "A2", "B1", "B2")[b // 4]
        macros.append({"inst": f"g_rom[{b}].u_rom", "master": rom, "x": cols[col],
                       "y": MARGIN + 4.0 + (b % 4) * (rh + GAP), "orient": "R0", "capture": True})
    act_stack = 4 * ah + 3 * 10.0
    y0 = (die_h - act_stack) / 2
    for c in range(8):
        left = c < 4
        macros.append({"inst": f"g_act[{c}].u_act", "master": act, "x": x_sl if left else x_sr,
                       "y": y0 + (c % 4) * (ah + 10.0), "orient": "MY" if left else "R0", "capture": False})
    return {"case": "qe", "top": "ot_chip_v41x_qe_romac", "die_um": [die_w, die_h],
            "logic_region_um": [round(x_logic0, 3), MARGIN, round(x_logic0 + logic_w, 3), die_h - MARGIN],
            "pin_span_um": [round(x_sl, 3), round(x_sr + aw, 3)], "macros": macros,
            "sources": QE_SOURCES + [f"{MACRO_DIR}/{rom}/{rom}_bb.v", f"{MACRO_DIR}/{act}/{act}_bb.v",
                                     "rtl/chip/physical/ot_chip_v41x_qe_romac.sv"],
            "macro_views": sorted({rom, act})}


def hook_tcl(plan: dict) -> str:
    lines = [
        f"# POST_MACRO_PLACE hook for the W2 V4.1 {plan['case']} ROM/MAC neighborhood (tools/v41_w2_romac_pnr.py).",
        "# Places every macro FIRM on the joint site / M4-track grid, then FIXES each ROM output's capture flop",
        "# beside the pin it captures, in the orientation of its row (VDD/VSS rails align).",
        "set block [ord::get_db_block]",
        "set dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
        "set row0 [lindex [$block getRows] 0]",
        "set origin [$row0 getOrigin]",
        "set xgrid0 [expr {double([lindex $origin 0])/$dbu}]",
        "set ygrid0 [expr {double([lindex $origin 1])/$dbu}]",
        "set xpitch [expr {double([[$row0 getSite] getWidth])/$dbu}]",
        "set ypitch [expr {double([[$row0 getSite] getHeight])/$dbu}]",
        "proc ot_snap {v origin pitch} { return [expr {$origin+round(($v-$origin)/$pitch)*$pitch}] }",
        "proc ot_snap_joint {value site_origin site_pitch track_origin track_pitch} {",
        "    set so [expr {round($site_origin*1000)}]; set sp [expr {round($site_pitch*1000)}]",
        "    set to [expr {round($track_origin*1000)}]; set tp [expr {round($track_pitch*1000)}]",
        "    set center [expr {round(($value*1000-$so)/$sp)}]",
        "    set best {}; set bestdist 1000000000",
        "    for {set delta -1000} {$delta <= 1000} {incr delta} {",
        "        set candidate [expr {$so+($center+$delta)*$sp}]",
        "        if {($candidate-$to)%$tp != 0} { continue }",
        "        set dist [expr {abs($candidate-$value*1000)}]",
        "        if {$dist < $bestdist} { set best $candidate; set bestdist $dist }",
        "    }",
        "    if {$best eq {}} { error \"No intersection of site and track origin grids\" }",
        "    return [expr {$best/1000.0}]",
        "}",
        "proc ot_find {block want} {",
        "    foreach inst [$block getInsts] {",
        "        if {[string map {\\\\ {}} [$inst getName]] eq $want} { return $inst }",
        "    }",
        "    error \"placement hook: no instance $want\"",
        "}",
        "proc ot_row_orient {block y dbu} {",
        "    set yi [expr {round($y*$dbu)}]",
        "    foreach row [$block getRows] { if {[lindex [$row getOrigin] 1] == $yi} { return [$row getOrient] } }",
        "    error \"No placement row at Y=$y\"",
        "}",
        "set ot_macros {",
    ]
    for m in plan["macros"]:
        lines.append(f"    {{{m['inst']}}} {m['x']:.3f} {m['y']:.3f} {m['orient']} {int(m['capture'])}")
    lines += [
        "}",
        "set nfixed 0",
        "set used [dict create]",
        "foreach {name mx my orient capture} $ot_macros {",
        "    set inst [ot_find $block $name]",
        "    set px [ot_snap_joint $mx $xgrid0 $xpitch 0.0 0.054]",
        "    set py [ot_snap_joint $my $ygrid0 $ypitch 0.0 0.048]",
        "    place_inst -name [$inst getName] -location [format \"%.3f %.3f\" $px $py] -orientation $orient -status FIRM",
        "    if {!$capture} { continue }",
        "    set box [$inst getBBox]",
        "    set bx0 [expr {double([$box xMin])/$dbu}]; set bx1 [expr {double([$box xMax])/$dbu}]",
        "    foreach it [$inst getITerms] {",
        "        set mt [$it getMTerm]",
        "        if {![string match rd_out* [$mt getName]]} { continue }",
        "        set net [$it getNet]",
        "        if {$net eq \"NULL\" || $net eq \"\"} { continue }",
        "        set ff {}",
        "        foreach o [$net getITerms] {",
        "            set oi [$o getInst]",
        "            if {[string match *DFF* [[$oi getMaster] getName]]} { set ff $oi; break }",
        "        }",
        "        if {$ff eq {}} { error \"capture flop missing on [$net getName]\" }",
        "        set xy [$it getAvgXY]",
        "        set pinx [expr {double([lindex $xy 1])/$dbu}]; set piny [expr {double([lindex $xy 2])/$dbu}]",
        "        set fw [expr {double([[$ff getMaster] getWidth])/$dbu}]",
        "        set fh [expr {double([[$ff getMaster] getHeight])/$dbu}]",
        "        set west [expr {abs($pinx-$bx0) < abs($pinx-$bx1)}]",
        "        set y [ot_snap [expr {$piny-$fh/2.0}] $ygrid0 $ypitch]",
        "        # one column first; if the row slot is taken, step outward by one flop width",
        "        for {set col 0} {$col < 6} {incr col} {",
        "            if {$west} { set x [expr {$bx0-2.2-($col+1)*($fw+0.216)}] } else { set x [expr {$bx1+2.2+$col*($fw+0.216)}] }",
        "            set x [ot_snap $x $xgrid0 $xpitch]",
        "            set key \"[format %.3f $x],[format %.3f $y]\"",
        "            if {![dict exists $used $key]} { break }",
        "        }",
        "        dict set used $key 1",
        "        place_inst -name [$ff getName] -location [format \"%.3f %.3f\" $x $y] -orientation [ot_row_orient $block $y $dbu] -status FIRM",
        "        incr nfixed",
        "    }",
        "}",
        "puts \"OT_W2_ROMAC_PLACE macros=[expr {[llength $ot_macros]/5}] fixed_capture_flops=$nfixed\"",
        f"if {{$nfixed != {274 * sum(1 for m in plan['macros'] if m['capture'])}}} {{ error \"capture flop count $nfixed\" }}",
    ]
    return "\n".join(lines) + "\n"


def argv(plan: dict, tag: str, keep: str, output: str) -> list[str]:
    w, h = plan["die_um"]
    args = ["tools/run_abi3_physical.py", "--view", "asap7", "--top", plan["top"]]
    for s in plan["sources"]:
        args += ["--source", s]
    args += ["--clock-period-ns", "0.92", "--clock-uncertainty-ns", "0.06", "--io-delay-fraction", "0.2",
             "--stages", "pnr", "--die-area", "0", "0", f"{w:g}", f"{h:g}",
             "--core-area", f"{MARGIN:g}", f"{MARGIN:g}", f"{w - MARGIN:g}", f"{h - MARGIN:g}",
             "--place-density", "0.6", "--macro-place-halo", "2", "2",
             "--pin-region", f".*=bottom:{plan['pin_span_um'][0]:g}-{plan['pin_span_um'][1]:g}",
             "--max-transition-ns", "0.32", "--slew-margin-percent", "40", "--hold-margin-ns", "0.02",
             "--step-tcl", f"POST_MACRO_PLACE=physical/abi3/v41_w2_{plan['case']}_romac_place.tcl",
             "--step-tcl", "POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl",
             "--nickname-tag", tag, "--keep-workdir", keep, "--output", output]
    for m in plan["macro_views"]:
        args += ["--macro-view", f"{m}={MACRO_DIR}/{m}"]
    return args


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("case", choices=["qe"])
    ap.add_argument("--write-hook", action="store_true")
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--tag", default="w2b_qe_romac")
    ap.add_argument("--keep", default="/tmp/w2b_qe_romac_work")
    ap.add_argument("--output", default="results/physical_abi3/asap7/chip/v41_w2_rommac/qe_romac_physical.json")
    a = ap.parse_args()
    plan = qe_plan()
    if a.write_hook:
        (ROOT / f"physical/abi3/v41_w2_{plan['case']}_romac_place.tcl").write_text(hook_tcl(plan))
    if a.print:
        print(json.dumps({"plan": plan, "argv": argv(plan, a.tag, a.keep, a.output)}, indent=1))


if __name__ == "__main__":
    main()
