#!/usr/bin/env python3
"""el1011-hbm-smt 2026-10-12: ref_tile CLUSTER specs for the SM tile (ot_hbm_accel_smh_tile_eg / _wg).

One hardened cluster per SM tile: the 12 closed ref_tile sub-tiles (pt_w, pt_e, 2 x {xs, bdc, tcl, tcl, tct}) + the tile
glue (ot_cg_tile ICG + enable regs, reset relay, leaf i-stages, G1 select / gather relays), hardened once and stepped x16.

Floorplan re-derived from the CLOSED child LEFs on the 43.2-um child lattice with >= 20 um channels and >= 20 um from
every pin face (ref_tile floorplan_checks):
  W column  : bdc1 / xs1 / pt_w / xs0 / bdc0  (xs <-> pt_w landing channels 58-60 um: 2,900 landing wires with lateral
              shifts, cut demand 1,821 at x 115 vs ~3,100 H tracks at 60 um -> 0.59; at 43.2 um it would be 0.82)
  E column  : tct1 / tcl pair1 / pt_e / tct0 / tcl pair0 (tcc stays R0 in both leaves: tcl sum_o S -> tct sum_i N)
  leaf 1's xs and bdc are MX images (landing / input faces turn towards pt_w / xs).  A mirrored child must carry no M6
  face pins (M4 48/12 and M6 64/16 tracks have no common mirror residue): xs is the exact-io_tcl re-route p50x.
The 587.52 x 1080 hand slot does not fit on the lattice (bdc above xs needs 1,245 um of column height; the tcl pair needs a
216-um column beside pt_e): outline 630.72 x 1252.8 (children 381.6k um2 = 48 % + glue).
Pin plan: rin/bin at the y of pt_w's own rin/bin pins and rout/bout at the SAME y on the opposite face (abutment-ready for
the next tile; pt_e's rout/bout sit at those y within 0.5 um, cut demand 30), gin + straps + clk/rst/cg on N, gout on S.
wg = MY mirror: pt_w on the E side, rin/bin on E, rout/bout on W, children MY (R0 ones) / R180 (MX ones).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
L = 43.2
import math
import os
XS_KIT = os.environ.get("SMT_XS_KIT", "smh_xs_ref_p40x")   # exact-io_tcl xs re-route that closed (p40x / t40)
V = "physical/ref_tile/{}/views/{}"
VIEWS = {"pt_w": V.format("smh_pt_w_ref_p45h", "ot_hbm_accel_smh_pt_w"),
         "pt_e": V.format("smh_pt_e_ref_p40s", "ot_hbm_accel_smh_pt_e"),
         "xs": V.format(XS_KIT, "ot_hbm_accel_smh_xs"),
         "bdc": V.format("smh_bdc_ref_p50", "ot_hbm_accel_smh_bdc"),
         "tcl": V.format("smh_tcl_ref_p45", "ot_hbm_accel_smh_tcl"),
         "tct": V.format("smh_tct_ref_p45", "ot_hbm_accel_smh_tct")}


def lef_size(view):
    t = (ROOT / view / f"{Path(view).name}.lef").read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    return float(m.group(1)), float(m.group(2))


DIM = {k: lef_size(v) for k, v in VIEWS.items()}
up = lambda v: round(math.ceil(round(v / L, 6)) * L, 3)       # next origin on the child lattice
# W column bottom-up: bdc1 / xs1 / pt band / xs0 / bdc0; landing channels (xs <-> pt_w) >= 55 um (cut <= 0.6), others >= 20
Y_BDC1 = 43.2
Y_XS1 = up(Y_BDC1 + DIM["bdc"][1] + 20.0)
Y_BAND = up(Y_XS1 + DIM["xs"][1] + 55.0)
Y_XS0 = up(Y_BAND + DIM["pt_w"][1] + 55.0)
Y_BDC0 = up(Y_XS0 + DIM["xs"][1] + 20.0)
W = 630.72
H = round(math.ceil((Y_BDC0 + DIM["bdc"][1] + 22.16) / 8.64 - 1e-9) * 8.64, 3)
# eg (R0 leaf 0 above the band, MX leaf 1 below): (kind, instance glob, x, y, orient); E column relative to the band
EG = [("pt_w", "*u_ptw", 43.2, Y_BAND, "R0"), ("pt_e", "*u_pte", 388.8, Y_BAND, "R0"),
      ("xs", "*g_lf?0?.u_lh.u_xs", 43.2, Y_XS0, "R0"), ("bdc", "*g_lf?0?.u_lh.u_bdc", 129.6, Y_BDC0, "R0"),
      ("tct", "*g_lf?0?.u_lh.u_tcc.u_tr", 388.8, round(Y_BAND + 432.0, 3), "R0"),
      ("tcl", "*g_lf?0?.u_lh.u_tcc.u_h0", 388.8, round(Y_BAND + 561.6, 3), "R0"),
      ("tcl", "*g_lf?0?.u_lh.u_tcc.u_h1", 518.4, round(Y_BAND + 561.6, 3), "R0"),
      ("xs", "*g_lf?1?.u_lh.u_xs", 43.2, Y_XS1, "MX"), ("bdc", "*g_lf?1?.u_lh.u_bdc", 129.6, Y_BDC1, "MX"),
      ("tct", "*g_lf?1?.u_lh.u_tcc.u_tr", 388.8, round(Y_BAND - 302.4, 3), "R0"),
      ("tcl", "*g_lf?1?.u_lh.u_tcc.u_h0", 388.8, round(Y_BAND - 172.8, 3), "R0"),
      ("tcl", "*g_lf?1?.u_lh.u_tcc.u_h1", 518.4, round(Y_BAND - 172.8, 3), "R0")]
MYO = {"R0": "MY", "MX": "R180"}
DEFINES = ["OT_SMH_CG_ENREG", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY", "OT_SMH_HIER",
           "OT_SMH_PTW_OHDLY", "OT_SMH_PRODUCTION_SHAPE"]
BDEF = " ".join(f"--define {d}" for d in DEFINES)
BENCH = ("W=$(mktemp -d /tmp/smtb.XXXXXX); python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 8 --rmax 4096 --req-credit --smh --cg " + BDEF +
         " {mut}--cg-gap 300 --build-jobs 8 --workdir $W --out {{RUN}}/b_{n}.json > {{RUN}}/b_{n}.log 2>&1; rc=$?; "
         "cat {{RUN}}/b_{n}.log | tail -5; grep -h CG_LOCKSTEP $W/*/runtime.log; {tail}")
BENCHES = [
    {"name": "lockstep_enreg_xlk", "expect": "pass", "pass_regex": "SMT_LOCKSTEP_PASS", "threads": 8, "peak_ram_gb": 48,
     "cmd": BENCH.format(n="lockstep_enreg_xlk", mut="", tail=(
         "test $rc -eq 0 && grep -q 'CG_LOCKSTEP mismatches 0 ' $W/*/runtime.log && echo SMT_LOCKSTEP_PASS"))},
    {"name": "mut_late32", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 48,
     "cmd": BENCH.format(n="mut_late32", mut="--cg-mut-late ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))},
    {"name": "mut_hold0", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 48,
     "cmd": BENCH.format(n="mut_hold0", mut="--cg-mut-hold0 ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))}]


def ptw_pins():
    """pt_w face pins (name -> (layer, x, y)) from its LEF (the closed view, or its placeholder before closure)"""
    t = (ROOT / VIEWS["pt_w"] / "ot_hbm_accel_smh_pt_w.lef").read_text()
    out = {}
    for m in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", t, re.S):
        r = re.search(r"LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", m.group(2))
        if r:
            out[m.group(1).replace("\\", "")] = (r.group(1), round((float(r.group(2)) + float(r.group(4))) / 2, 3),
                                                 round((float(r.group(3)) + float(r.group(5))) / 2, 3))
    return out


def bits(n, k):
    return [f"{n}[{i}]" for i in range(k)]


def io_tcl(variant):
    pw = ptw_pins()
    xin, xout = (0.0, W) if variant == "eg" else (W, 0.0)
    y0 = Y_BAND
    out = ["# generated by physical/ref_tile_specs/smh/mk_smh_tile_cluster.py: SM tile cluster pin plan (" + variant + ")",
           "# rin/bin at pt_w's own pin y (straight into the child), rout/bout at the same y on the far face (next tile)"]
    def pp(n, layer, x, y):
        sz = "0.192 0.024" if layer == "M4" else "0.024 0.192"
        out.append(f"place_pin -pin_name {{{n}}} -layer {layer} -location {{{x} {y}}} -pin_size {{{sz}}} "
                   "-force_to_die_boundary")
    for src, dst, k in (("rin", "rout", 1636), ("bin", "bout", 2069)):
        for i in range(k):
            lay, _, y = pw[f"{src}[{i}]"]
            assert lay == "M4"
            pp(f"{src}[{i}]", "M4", xin, round(y0 + y, 3))
            pp(f"{dst}[{i}]", "M4", xout, round(y0 + y, 3))
    # N face: gin lanes (2 x 50) + straps / clock / reset / wake; S face: gout lanes (4 x 50); 0.48 um pitch, M5 tracks
    def row(names, x0, y, pitch=0.48):
        for i, n in enumerate(names):
            pp(n, "M5", round(x0 + i * pitch, 3), y)
    gx0 = 0.012 + 48 * round((W / 2 - 100 * 0.48) / 0.048 / 48)   # centred, on the M5 track (0.012 + k * 0.048)
    row(bits("gout", 200), round(gx0, 3), 0.0)
    nn = (bits("gin", 100) + bits("xs_a1", 18) + bits("xs_g1", 10) + bits("xs_a2", 14) + bits("xs_g2", 10)
          + ["rst_n", "cgi", "cgo"])
    nx0 = 0.012 + 0.048 * round((W / 2 - len(nn) * 0.24) / 0.048)
    row(nn, round(nx0, 3), H)
    pp("clk", "M5", round(nx0 + len(nn) * 0.48 + 4.8, 3), H)
    return "\n".join(out) + "\n"


def spec(variant):
    name = f"smh_tile_{variant}_ref"
    kids = []
    for kind, inst, x, y, o in EG:
        if variant == "wg":
            w = DIM[kind][0]
            x = round(round((W - x - w) / L) * L, 3)
            o = MYO[o]
        kids.append({"view": VIEWS[kind], "count": 1, "at": [x, y], "orient": o, "inst": inst})
    io = f"physical/ref_tile_specs/smh/{name}_pins.tcl"
    (ROOT / io).write_text(io_tcl(variant))
    fin, fout = ("W", "E") if variant == "eg" else ("E", "W")
    src = json.loads((OUT / "smh_pt_w_ref_p45h.json").read_text())["sources"]
    src = src + [f for f in ("rtl/hdc/ot_hdc_cg.sv", "rtl/hbm_accel/cg/ot_cg_tile.sv") if f not in src]
    return {
        "name": name, "top": f"ot_hbm_accel_smh_tile_{variant}", "kind": "cluster",
        "sources": src, "params": {}, "defines": DEFINES, "clock_port": "clk", "reset_ports": ["rst_n"],
        "spine_through_icg": True,
        "outline": {"w": W, "h": H},
        "children": kids,
        "pins": {fin: ["rin", "bin"], fout: ["rout", "bout"], "S": ["gout"],
                 "N": ["gin", "xs_a1", "xs_g1", "xs_a2", "xs_g2", "clk", "rst_n", "cgi", "cgo"]},
        "io_tcl": io,
        "orfs_vars": {"POST_TAPCELL_TCL": f"physical/ref_tile_specs/smh/{name}_strap_regions.tcl"},
        "refglob": "*",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 96},
        "job": {"owner": "Codex:hbm-sm-cluster", "branch": "codex/hbm-sm-cluster", "tag": "r8",
                "purpose": (f"[smmv-b/smt] ot_hbm_accel_smh_tile_{variant}: SM tile as ONE ref_tile cluster (owner "
                            "contract: harden once, step x16; wg = MY mirror) over the 12 closed ref_tile sub-tiles "
                            "(pt_w p45h, pt_e p40s, xs p50, bdc p50, tcl p45, tct p45), floorplan re-derived from their "
                            "LEFs on the 43.2-um lattice (630.72 x 1252.8, landing channels 58-60 um, cut 0.59), clock "
                            "spine through the tile ICG, exact abutment pin plan. Five registered regional static-strap stages per leaf (260 DFFs), zero data latency; "
                            "production NC8 active8 RMAX4096 TAGW16 native-default lockstep exactness plus strap-offset/late32/hold0 mutants must fail."),
                "benches": BENCHES + [{"name": "mut_strap_region", "expect": "fail",
                "fail_regex": "SMT_STRAP_MUTANT_KILLED", "threads": 8, "peak_ram_gb": 48,
                "cmd": BENCH.format(n="mut_strap_region", mut="--define OT_SMH_MUT_STRAP_REGION ",
                    tail=("python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); "
                          "assert x[\"timeout\"] is None and x[\"mismatching_ops\"] > 0; "
                          "print(\"SMT_STRAP_MUTANT_KILLED\", x[\"mismatching_ops\"])' "
                          "{RUN}/b_mut_strap_region.json; test $rc -eq 0"))} ]},
    }


def strap_regions(variant):
    # Five physical stages per leaf, kept on the gated cluster clock.
    points = [[(300,H-12),(365,1100),(365,1060),(300,1060),(260,Y_XS0+DIM["xs"][1]+12)],
              [(340,H-12),(365,950),(365,650),(365,350),(260,Y_XS1-16)]]
    lines = ["# Generated fixed legal strap-stage stations: no child/clock/pin budget change.",
             "set ::sr_blk [ord::get_db_block]", "set ::sr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]", "set sn 0",
             "proc sr_init {} {",
             "  set ::sr_rows {}; set ::sr_used [dict create]; set ::sr_fixed 0",
             "  foreach r [$::sr_blk getRows] {set rb [$r getBBox]; lassign [$r getOrigin] ox oy; set ::sr_sw [[$r getSite] getWidth]; set ::sr_rh [[$r getSite] getHeight]; lappend ::sr_rows [list $ox $oy [$rb xMax] [$r getOrient]]}",
             "  set ::sr_mw_inv 0; set ::sr_mw_dff 0",
             "  foreach lib [[ord::get_db] getLibs] {foreach m [$lib getMasters] {set n [$m getName]; if {[regexp {^INV} $n]} {set ::sr_mw_inv [expr {max($::sr_mw_inv,[$m getWidth])}]} elseif {[regexp {^DFF} $n]} {set ::sr_mw_dff [expr {max($::sr_mw_dff,[$m getWidth])}]}}}",
             "  puts \"STRAP_GROWTH_RESERVE INV $::sr_mw_inv DFF $::sr_mw_dff DBU $::sr_dbu\"",
             "  foreach i [$::sr_blk getInsts] {if {[$i isPlaced]} {set bb [$i getBBox]; sr_occupy [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]}}",
             "}",
             "proc sr_occupy {x0 y0 x1 y1} {for {set k [expr {int(floor(double($y0)/$::sr_rh))}]} {$k <= int(floor(double($y1-1)/$::sr_rh))} {incr k} {dict lappend ::sr_used $k [list $x0 $x1]}}",
             "proc sr_place {group cx cy} {",
             "  set cx [expr {round($cx*$::sr_dbu)}]; set cy [expr {round($cy*$::sr_dbu)}]; set rows {}",
             "  foreach r $::sr_rows {lassign $r ox oy xe ori; if {abs($oy-$cy) < 4*$::sr_dbu} {lappend rows [linsert $r 0 [expr {abs($oy-$cy)}]]}}",
             "  set rows [lsort -integer -index 0 $rows]",
             "  foreach i [$group getInsts] {",
             "    set w [[$i getMaster] getWidth]; set h [[$i getMaster] getHeight]; set master [[$i getMaster] getName]; set mw [expr {[regexp {^INV} $master] ? $::sr_mw_inv : $::sr_mw_dff}]; set w [expr {max($w,$mw)+4*$::sr_sw}]; set found 0",
             "    foreach r $rows {lassign $r delta ox oy xe ori; if {$oy < $cy-4*$::sr_dbu || $oy+$h > $cy+4*$::sr_dbu} continue",
             "      set x [expr {$ox+int(ceil(double(max($ox,$cx-8*$::sr_dbu)-$ox)/$::sr_sw))*$::sr_sw}]",
             "      while {$x+$w <= min($xe,$cx+8*$::sr_dbu)} {",
             "        set jump $x; for {set k [expr {int(floor(double($oy)/$::sr_rh))}]} {$k <= int(floor(double($oy+$h-1)/$::sr_rh))} {incr k} {",
             "          if {![dict exists $::sr_used $k]} continue; foreach iv [dict get $::sr_used $k] {lassign $iv a b; if {$x+$w > $a && $x < $b} {set jump [expr {max($jump,$ox+int(ceil(double($b-$ox)/$::sr_sw))*$::sr_sw)}]}}",
             "        }",
             "        if {$jump > $x} {set x $jump; continue}",
             "        $i setOrient $ori; $i setLocation [expr {$x+2*$::sr_sw}] $oy; $i setPlacementStatus FIRM; incr ::sr_fixed; sr_occupy $x $oy [expr {$x+$w}] [expr {$oy+$h}]; set found 1; break",
             "      }; if {$found} break",
             "    }; if {!$found} {error \"STRAP_REGION no legal station site for [$i getName]\"}",
             "  }",
             "}", "sr_init",
             "proc sr_bind {net group} {",
             "  for {set hop 0} {$hop < 5} {incr hop} {",
             "    set driver {}; foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend driver $it}}",
             "    if {[llength $driver] != 1} {error \"STRAP_REGION ambiguous driver\"}",
             "    set si [[lindex $driver 0] getInst]; set master [[$si getMaster] getName]",
             "    $group addInst $si",
             "    if {[string match *DFF* $master]} {return 1}",
             "    if {![regexp {^(INV|BUF)} $master]} {error \"STRAP_REGION non-register logic $master\"}",
             "    set ins {}; foreach it [$si getITerms] {if {[$it isInputSignal]} {lappend ins [$it getNet]}}",
             "    if {[llength $ins] != 1} {error \"STRAP_REGION buffer input ambiguity\"}; set net [lindex $ins 0]",
             "  }; error \"STRAP_REGION register not found\"", "}"]
    for leaf, ps in enumerate(points):
        for stage, (x,y) in enumerate(ps):
            if variant == "wg": x = W-x
            name=f"strap_l{leaf}_s{stage}"
            lines += [f"set rg [odb::dbRegion_create $::sr_blk {name}]", "$rg setRegionType EXCLUSIVE",
                      f"odb::dbBox_create $rg [expr {{round({x-8}*$::sr_dbu)}}] [expr {{round({y-4}*$::sr_dbu)}}] [expr {{round({x+8}*$::sr_dbu)}}] [expr {{round({y+4}*$::sr_dbu)}}]",
                      f"set gr [odb::dbGroup_create $::sr_blk {name}]", "set nc 0",
                      "foreach net [$::sr_blk getNets] {", "  set nm [string map {\\\\ {}} [$net getName]]",
                      f"  if {{[string first {{g_strap[{leaf}].u_sr.s{stage}[}} $nm] >= 0 }} {{ sr_bind $net $gr; incr nc; incr sn }}",
                      "}", f"if {{$nc != 26}} {{error \"STRAP_REGION {name}: expected 26 DFFs, got $nc\"}}", f"sr_place $gr {x} {y}", "odb::dbGroup_destroy $gr", "odb::dbRegion_destroy $rg"]
    lines += ["if {$sn != 260} {error \"STRAP_REGION expected 260 DFFs\"}", "puts \"STRAP_REGION_PLACED 10 DFFS $sn FIXED_CELLS $::sr_fixed\""]
    (OUT/f"smh_tile_{variant}_ref_strap_regions.tcl").write_text("\n".join(lines)+"\n")


def main():
    for v in sys.argv[1:] or ["eg", "wg"]:
        strap_regions(v)
        s = spec(v)
        p = OUT / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print(p.relative_to(ROOT))


if __name__ == "__main__":
    main()
