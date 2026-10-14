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
XS_KIT = os.environ.get("SMT_XS_KIT", "smh_xs_ref_p45m")   # accepted mirror-safe p45m r3 view
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
CH_X = 367.2      # eg: centre of the free N-S channel between the W column (ends 345.6) and the E column (starts 388.8)
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
DEFINES = ["OT_SMH_CG_ENREG", "OT_SMH_XLK", "OT_FP_DATA_NORST", "OT_SMH_DRST0", "OT_SMH_RSTRELAY", "OT_SMH_RSTPIN", "OT_SMH_HIER",
           "OT_SMH_PTW_OHDLY", "OT_SMH_PRODUCTION_SHAPE"]
BDEF = " ".join(f"--define {d}" for d in DEFINES)
BENCH = ("W=$(mktemp -d /tmp/smtb.XXXXXX); python3 tools/dshbm_sm_pq_seq.py run --seq stress --nc 8 --active 8 --rmax 4096 --req-credit --smh --cg " + BDEF +
         " {mut}--cg-gap 300 --build-jobs 8 --workdir $W --out {{RUN}}/b_{n}.json > {{RUN}}/b_{n}.log 2>&1; rc=$?; "
         "cat {{RUN}}/b_{n}.log | tail -5; grep -h CG_LOCKSTEP $W/*/runtime.log; {tail}")
BENCHES = [
    {"name": "lockstep_enreg_xlk", "expect": "pass", "pass_regex": "SMT_LOCKSTEP_PASS", "threads": 8, "peak_ram_gb": 72,
     "cmd": BENCH.format(n="lockstep_enreg_xlk", mut="", tail=(
         "test $rc -eq 0 && grep -q 'CG_LOCKSTEP mismatches 0 ' $W/*/runtime.log && echo SMT_LOCKSTEP_PASS"))},
    {"name": "mut_late32", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 72,
     "cmd": BENCH.format(n="mut_late32", mut="--cg-mut-late ", tail=(
         "test $rc -eq 0 && ! grep -q 'CG_LOCKSTEP mismatches [1-9]' $W/*/runtime.log"))},
    {"name": "mut_hold0", "expect": "fail", "fail_regex": "CG_LOCKSTEP mismatches [1-9]", "threads": 8, "peak_ram_gb": 72,
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
    # N face: gin lanes (2 x 50) + straps, then clock / reset / wake over the centre channel; S face: gout lanes (4 x 50);
    # 0.48 um pitch on M5 tracks (0.012 + k * 0.048).  r11 (el1013-smh-r11): (1) gout started at x = 5,568 um (a 48 for
    # 0.048 in the track snap), off the die; (2) gin[i] now sits at the x of gout[i] of the tile above (straight seam);
    # (3) clk / rst_n / cgi / cgo sit over the free N-S centre channel (x 345.6-388.8 in eg), where the tile ICG, the
    # reset pin flop and the spine root go; (4) wg is the MY mirror, so its N / S pins mirror too.
    snap = lambda x: round(0.012 + 0.048 * round((x - 0.012) / 0.048), 3)
    mx = (lambda x: x) if variant == "eg" else (lambda x: W - x)
    def row(names, x0, y, pitch=0.48):
        for i, n in enumerate(names):
            pp(n, "M5", snap(mx(x0 + i * pitch)), y)
    gx0 = snap(W / 2 - 100 * 0.48)
    row(bits("gout", 200), gx0, 0.0)
    nn = bits("gin", 100) + bits("xs_a1", 18) + bits("xs_g1", 10) + bits("xs_a2", 14) + bits("xs_g2", 10)
    row(nn, gx0, H)
    assert gx0 + len(nn) * 0.48 < CH_X - 6
    row(["rst_n", "cgi", "cgo"], CH_X - 4.8, H)
    pp("clk", "M5", snap(mx(CH_X)), H)
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
        "orfs_vars": {"OT_CG_EXCLUDE": "*u_cgt.u_cg.u_icg", "OT_SPINE_SYM": "1", "OT_SPINE_TREE_PAD": "1", "POST_TAPCELL_TCL": f"physical/ref_tile_specs/smh/{name}_strap_regions.tcl"},
        "refglob": "*",
        "route": {"pd": 0.5, "threads": 16, "peak_ram_gb": 96},
        "job": {"owner": "Claude:el1013-smh-r11", "branch": "claude/el1013-smh-r11", "tag": "r13",
                # r13 (el1013-smh-r11, 10-13): eg r11 / wg r12 died at 4_1_cts with DPL-0033 -- the spine's THROUGH_ICG move
                # left the ICG enable cone FIRM but resizable; repair_timing sized the cgi input buffer over an abutting
                # FIRM AND3.  Fixed in physical/common_flow/clock_spine.tcl (main 8e4929331).
                "structural_change": (
                    "clock root rebuilt: only the tile ICG and its enable registers are fixed beside the clk pin and "
                    "they are dont_touch; the ICG enable cone (input buffer of cgi + gates) is movable and legalised "
                    "(r11/r12: cone cells FIRM yet resizable -> input2099 sized to BUFx12f over FIRM _0956_, DPL-0033 "
                    "at CTS in both tiles; spine errors if a moved cell is fixed and resizable)"
                    + ("" if variant == "eg" else "; wg station plan mirrors about the PLACED centre channel "
                       "(x 259.2-302.4; reset 271.2, strap 283.0), every station window asserted clear of each child "
                       "+ halo at generation")),
                "purpose": (f"[smmv-b/smt] ot_hbm_accel_smh_tile_{variant}: SM tile as ONE ref_tile cluster (owner "
                            "contract: harden once, step x16; wg = MY mirror) over the 12 closed ref_tile sub-tiles "
                            "(pt_w p45h, pt_e p40s, xs p45m, bdc p50, tcl p45, tct p45), floorplan re-derived from their "
                            "LEFs on the 43.2-um lattice (630.72 x 1252.8, landing channels 58-60 um, cut 0.59), clock "
                            "spine through the tile ICG (symmetric insertion-aware topology), exact abutment pin plan re-applied after place_pins, rst_n pin flop + registered N-S reset tree (16 stations FFs, no reset on the raw clock: RSTEN 0 / RAWRST 0). Five registered regional static-strap stages per leaf (260 DFFs), zero data latency; "
                            "production NC8 active8 RMAX4096 TAGW16 native-default lockstep exactness plus strap-offset/late32/hold0 mutants must fail."),
                "benches": BENCHES + [{"name": "mut_strap_region", "expect": "fail",
                "fail_regex": "SMT_STRAP_MUTANT_KILLED", "threads": 8, "peak_ram_gb": 72,
                "cmd": BENCH.format(n="mut_strap_region", mut="--define OT_SMH_MUT_STRAP_REGION ",
                    tail=("python3 -c 'import json,sys; x=json.load(open(sys.argv[1])); "
                          "assert x[\"timeout\"] is None and x[\"mismatching_ops\"] > 0; "
                          "print(\"SMT_STRAP_MUTANT_KILLED\", x[\"mismatching_ops\"])' "
                          "{RUN}/b_mut_strap_region.json; test $rc -eq 0"))} ]},
    }


HALO = 2.16            # ref_tile macro-place halo (rows are cut this far from every child)
SBX, SBY = 8.0, 4.0    # station search window half extents (sr_place)


def child_boxes(variant):
    """(eg x, x0, y0, x1, y1) of every child as PLACED for this variant.  wg children are NOT the die mirror of eg: a
    mirrored origin W - x - w is off the 43.2-um child lattice (W = 14.6 pitches), so spec() snaps it and the whole wg
    image sits 17.28 um east of the die mirror."""
    out = []
    for kind, _inst, x, y, _o in EG:
        w, h = DIM[kind]
        px = x if variant == "eg" else round(round((W - x - w) / L) * L, 3)
        out.append((x, px, y, px + w, y + h))
    return out


def channel(variant):
    """free N-S centre channel (x_lo, x_hi) between the two child columns AS PLACED"""
    b = child_boxes(variant)
    wcol = [r for r in b if r[0] < CH_X]          # pt_w column (W in eg, E in wg)
    ecol = [r for r in b if r[0] > CH_X]
    left, right = (wcol, ecol) if variant == "eg" else (ecol, wcol)
    lo, hi = max(r[3] for r in left), min(r[1] for r in right)
    assert hi - lo >= 2 * (SBX + HALO + 0.5), f"{variant}: centre channel {lo}-{hi} narrower than a station window"
    return lo, hi


def station_x(variant, x):
    """eg station x -> this variant.  A station in the centre channel is mirrored about the CHANNEL centre of the placed
    wg image (r11 wg crash 10-13: the die mirror W - x put the reset stations at x 253.9, inside tcl h0 at 172.8-259.2:
    'STRAP_REGION no legal station site for u_rt.n3'); a station outside it is mirrored about the die (it follows the
    N / S pins, which are the die mirror)."""
    if variant == "eg":
        return x
    elo, ehi = channel("eg")
    if elo <= x <= ehi:
        wlo, whi = channel("wg")
        return round((wlo + whi) / 2 - (x - (elo + ehi) / 2), 3)
    return round(W - x, 3)


def station_check(variant, name, x, y):
    """the whole search window must be legal rows: inside the core and clear of every child + halo (0.5 um for the
    mirrored-pin track shift of a placed origin).  Fails at generation, not in the route."""
    m = HALO + 0.5
    assert m + SBX <= x <= W - m - SBX and m + SBY <= y <= H - m - SBY, f"{variant} {name}: window ({x}, {y}) leaves the core"
    for _ex, x0, y0, x1, y1 in child_boxes(variant):
        if x + SBX > x0 - m and x - SBX < x1 + m and y + SBY > y0 - m and y - SBY < y1 + m:
            raise AssertionError(f"{variant} station {name} window ({x}, {y}) +-({SBX}, {SBY}) overlaps a child + halo "
                                 f"at x {x0}-{x1} y {y0}-{y1}")


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
            x = station_x(variant, x)
            name=f"strap_l{leaf}_s{stage}"
            station_check(variant, name, x, y)
            lines += [f"set rg [odb::dbRegion_create $::sr_blk {name}]", "$rg setRegionType EXCLUSIVE",
                      f"odb::dbBox_create $rg [expr {{round({x-8}*$::sr_dbu)}}] [expr {{round({y-4}*$::sr_dbu)}}] [expr {{round({x+8}*$::sr_dbu)}}] [expr {{round({y+4}*$::sr_dbu)}}]",
                      f"set gr [odb::dbGroup_create $::sr_blk {name}]", "set nc 0",
                      "foreach net [$::sr_blk getNets] {", "  set nm [string map {\\\\ {}} [$net getName]]",
                      f"  if {{[string first {{g_strap[{leaf}].u_sr.s{stage}[}} $nm] >= 0 }} {{ sr_bind $net $gr; incr nc; incr sn }}",
                      "}", f"if {{$nc != 26}} {{error \"STRAP_REGION {name}: expected 26 DFFs, got $nc\"}}", f"sr_place $gr {x} {y}", "odb::dbGroup_destroy $gr", "odb::dbRegion_destroy $rg"]
    lines += ["if {$sn != 260} {error \"STRAP_REGION expected 260 DFFs\"}", "puts \"STRAP_REGION_PLACED 10 DFFS $sn FIXED_CELLS $::sr_fixed\""]
    # el1013-smh-r11: the reset tree's registers (ot_hbm_accel_smh_rst_tree) at fixed stations down the centre channel:
    # pin flop under the rst_n pin, one band station per stage, <= 340 um a hop (strap stations use x 365 at other y)
    rx = CH_X + 9.6
    rst = {"p0": H - 14, "n1": 1200, "n2": 1160, "n3": 1040, "f_gn": 1022, "f_lhn": 1014,
           "t1": 900, "m2": 760, "m3": 632, "f_gm": 618, "f_ptw": 610, "f_pte": 602,
           "t2": 560, "s3": 250, "f_gs": 232, "f_lhs": 224}
    lines += ["set rn 0"]
    for reg, y in rst.items():
        x = station_x(variant, rx)
        name = f"rst_{reg}"
        station_check(variant, name, x, y)
        lines += [f"set rg [odb::dbRegion_create $::sr_blk {name}]", "$rg setRegionType EXCLUSIVE",
                  f"odb::dbBox_create $rg [expr {{round({x-8}*$::sr_dbu)}}] [expr {{round({y-4}*$::sr_dbu)}}] [expr {{round({x+8}*$::sr_dbu)}}] [expr {{round({y+4}*$::sr_dbu)}}]",
                  f"set gr [odb::dbGroup_create $::sr_blk {name}]", "set nc 0",
                  "foreach net [$::sr_blk getNets] {", "  set nm [string map {\\\\ {}} [$net getName]]",
                  f"  if {{[regexp {{u_rt\\.{reg}$}} $nm]}} {{ sr_bind $net $gr; incr nc; incr rn }}",
                  "}", f"if {{$nc != 1}} {{error \"RESET_STATION {name}: expected 1 register, got $nc\"}}", f"sr_place $gr {x} {y}", "odb::dbGroup_destroy $gr", "odb::dbRegion_destroy $rg"]
    lines += [f"if {{$rn != {len(rst)}}} {{error \"RESET_STATION expected {len(rst)} registers\"}}", f"puts \"RESET_STATION_PLACED {len(rst)} FIXED_CELLS $::sr_fixed\""]
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
