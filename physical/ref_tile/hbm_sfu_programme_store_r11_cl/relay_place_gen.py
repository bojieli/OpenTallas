#!/usr/bin/env python3
"""HBM-ELEMOWN3/SFUPS 2026-10-19: placement plan for the r11 programme-store relays (ot_hgi_sfu_programme_store_r11).

Every relay chain of the r11 head runs along std-cell channels of the 1080 x 950.4 floorplan (leaves at x 43.2 / 388.8 /
734.4, y 43.2 / 259.2 / 475.2 / 691.2, 285.12 x 194.4, inputs on the leaf N face, outputs on the S face; host pins on the
E face, outputs on the S face).  For each chain this script draws the channel polyline from its source to its destination,
puts stage k at its equal-arc-length point, checks every register-to-register leg (<= 405 um, reach rule), and writes
  relay_place.tcl   PRE_GLOBAL_PLACE hook (spec pin_hook_before_flops): each stage's flops FIRM at their point, packed
                    legally by physical/common_flow/anchor_row_packing.tcl; names recorded for the release hook
  relay_release.tcl PRE_DETAIL_PLACE hook (spec pre_dpl_extra): back to PLACED so DPL legalises them in place
  relay_plan.json   the plan: per chain, polyline length, stage points and the longest leg.
Run from the repo root: python3 physical/ref_tile/hbm_sfu_programme_store_r11_cl/relay_place_gen.py
"""
import json, math, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
REACH = 405.0
KR, KI, KL, KS, KO = 3, 2, 4, 2, 4
KC = {0: 1, 3: 3, 6: 4, 8: KI}                 # chain-head data relays (P0, P3, P6, IO0)
PRED = {1: 0, 2: 1, 4: 3, 5: 4, 7: 6, 9: 8, 10: 9}
LW, SW, CW = 42, 38, 267
OWID = {l: (188 if l == 7 else 27 if l == 10 else 222) for l in range(11)}
# floorplan (spec children / gate_layout_placed.json of ref_gate/hbm_sfu_programme_store_r10_cl-20261018-180939)
COLX = [43.2, 388.8, 734.4]
ROWY = [43.2, 259.2, 475.2, 691.2]
LEAF = {0: (2, 0), 1: (1, 0), 2: (0, 0), 6: (0, 1), 8: (2, 1), 7: (0, 2), 10: (1, 2), 9: (2, 2), 5: (0, 3), 4: (1, 3), 3: (2, 3)}
LH = 194.4
EB = 1045.0                                    # E band (x 1019.5..1077.8, pin flops at ~1075)
VCH = [20.0, 358.6, 704.2, EB]                 # W band, v01, v12, E band
NCH = [248.4, 464.4, 680.4, 918.0]             # channel above row r (leaf N faces): c01, c12, c23, top band
SCH = [20.0, 248.4, 464.4, 680.4]              # channel below row r (leaf S faces): bottom band, c01, c12, c23
# leaf pin offsets (leaf LEF, x from the leaf origin)
IN_WE, IN_ADDR, IN_DATA, IN_START, RST_A = 131.0, 134.0, 220.0, 145.0, 156.0
OUT_CAL, OUT_STAT, OUT_HZ = 72.0, 183.0, 221.0
# host pins (E face, measured): cfg bus y 2..414, io_cfg 416..826, io_start 828..888, rst_n 889, start 891..949
SRC_CFG = (EB, 213.0); SRC_IOCFG = (EB, 627.0); SITE_CFG = (EB, 412.0); SITE_IOCFG = (EB, 825.0)
SITE_IOL = (EB, 858.0); SITE_PL = (EB, 920.0); RS2 = (EB, 889.0)
SITE_PSV = (704.2, 464.4); SITE_ST = (580.0, 20.0)
SITE_N7 = (COLX[0] + OUT_HZ, SCH[2]); SITE_N10 = (COLX[1] + OUT_HZ, SCH[2])
SITES = {0: SITE_CFG, 1: SITE_IOCFG, 2: SITE_IOL, 3: SITE_PSV, 4: SITE_N7, 5: SITE_N10, 6: SITE_ST}


HALO = 5.4


def blocked(pt):
    """inside a leaf or its halo (no std-cell rows there)"""
    x, y = pt
    return any(COLX[c] - HALO < x < COLX[c] + 285.12 + HALO and ROWY[r] - HALO < y < ROWY[r] + LH + HALO
               for (c, r) in LEAF.values())


def seg_ok(pts, step=2.0):
    """every point of the polyline (except the end points, which sit at pins) runs through std-cell area"""
    for a, b in zip(pts, pts[1:]):
        n = max(1, int((abs(a[0] - b[0]) + abs(a[1] - b[1])) / step))
        for i in range(n + 1):
            q = (a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            if q in (pts[0], pts[-1]):
                continue
            if blocked(q):
                return False
    return True


def best_of(cands):
    ok = [c for c in cands if seg_ok(c)]
    if not ok:
        raise SystemExit(f"no channel route for {cands[0][0]} -> {cands[0][-1]}")
    return min(ok, key=plen)


def leaf_in(l, off):
    c, r = LEAF[l]
    return (COLX[c] + off, NCH[r])


def leaf_out(l, off):
    c, r = LEAF[l]
    return (COLX[c] + off, SCH[r])


def path_to_in(src, l, off):
    """source -> vertical channel -> the leaf's N-face channel -> leaf pin"""
    c, r = LEAF[l]
    dst = leaf_in(l, off)
    return best_of([[src, (xv, src[1]), (xv, NCH[r]), (dst[0], NCH[r]), dst] for xv in VCH])


def path_out(l, off, dst):
    """leaf S-face pin -> its S channel -> a vertical channel -> bottom band -> target"""
    src = leaf_out(l, off)
    return best_of([[src, (xv, src[1]), (xv, dst[1]), dst] for xv in VCH])


def path_site(src, dst):
    return best_of([[src, (xv, src[1]), (xv, dst[1]), dst] for xv in VCH]
                   + [[src, (src[0], y), (dst[0], y), dst] for y in SCH + NCH])


def plen(pts):
    return sum(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(pts, pts[1:]))


def at(pts, f, want_dir=False):
    """point at arc fraction f; with want_dir also the unit direction of the segment it lies on"""
    L = plen(pts) * f
    segs = [(a, b) for a, b in zip(pts, pts[1:]) if a != b] or [(pts[0], (pts[0][0] + 1, pts[0][1]))]
    for a, b in segs:
        s = abs(a[0] - b[0]) + abs(a[1] - b[1])
        if L <= s or (a, b) == segs[-1]:
            t = 0.0 if s == 0 else min(1.0, L / s)
            p = (round(a[0] + t * (b[0] - a[0]), 2), round(a[1] + t * (b[1] - a[1]), 2))
            d = ((b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1]))
            return (p, d) if want_dir else p
        L -= s
    return (pts[-1], (1, 0)) if want_dir else pts[-1]


chains = []      # (name, regex, width, [stage points], legs)


def chain(name, regex, width, pts, fracs, first_at_source):
    """fracs: stage positions along pts; legs are measured source reg -> stages -> destination"""
    stages = [at(pts, f) for f in fracs]
    dirs = [at(pts, f, True)[1] for f in fracs]
    L = plen(pts)
    marks = ([] if first_at_source else [0.0]) + list(fracs) + [1.0]
    legs = [round((b - a) * L, 1) for a, b in zip(marks, marks[1:])]
    chains.append(dict(name=name, regex=regex, width=width, length_um=round(L, 1), stages=stages, dirs=dirs, legs_um=legs,
                       max_leg_um=max(legs), polyline=pts))


# reset: rs2 -> KR relays -> ra at the leaf (rst_a pin); sites: rs2 -> K relays -> ra/rb/rbd1 at the site
for l in range(11):
    pts = path_to_in(RS2, l, RST_A)
    chain(f"rst_leaf{l}", rf"^g_rl\[{l}\]\.q\[(\d+)\]", 1, pts, [k / (KR + 1) for k in range(1, KR + 1)], False)
    chain(f"rst_leaf{l}_ra", rf"^g_rl\[{l}\]\.ra(\$|_reg)", 1, pts, [1.0], True)   # legs counted by rst_leaf{l}
for s, site in SITES.items():
    K = KR + KS if s == 6 else KR
    pts = path_site(RS2, site)
    chain(f"rst_site{s}", rf"^g_rs\[{s}\]\.q\[(\d+)\]", 1, pts, [k / (K + 1) for k in range(1, K + 1)], False)
    chain(f"rst_site{s}_regs", rf"^g_rs\[{s}\]\.(ra|rb|rbd1)(\$|_reg)", 1, [site, site], [0.0], True)
# programme start register at PSV
chains.append(dict(name="p_sv_q", regex=r"^p_sv_q(\$|_reg)", width=1, length_um=0, stages=[SITE_PSV], dirs=[(1, 0)], legs_um=[0], max_leg_um=0,
                   polyline=[SITE_PSV]))
# programme launch: args from the start pins (stage 1 beside them), sv from p_sv_q
for l in range(8):
    pts = path_to_in(SITE_PL, l, IN_START)
    chain(f"launch_args{l}", rf"^g_pl\[{l}\]\.a\[(\d+)\]", LW - 1, pts, [(k - 1) / KL for k in range(1, KL + 1)], True)
    pts = path_to_in(SITE_PSV, l, IN_START)
    chain(f"launch_sv{l}", rf"^g_pl\[{l}\]\.v\[(\d+)\]", 1, pts, [k / (KL + 1) for k in range(1, KL + 1)], False)
# IO launch (stage 1 beside the io_start pins)
for i in range(3):
    pts = path_to_in(SITE_IOL, 8 + i, IN_START)
    chain(f"io_launch{i}", rf"^g_il\[{i}\]\.a\[(\d+)\]", LW, pts, [(k - 1) / KI for k in range(1, KI + 1)], True)
# configuration chain heads (data from the cfg pin flops: pure registers)
for c, l in enumerate([0, 3, 6, 8]):
    K = KC[l]
    pts = path_to_in(SRC_IOCFG if l == 8 else SRC_CFG, l, IN_DATA)
    chain(f"cfg_head{l}", rf"^g_cd\[{c}\]\.q\[(\d+)\]", CW, pts, [k / (K + 1) for k in range(1, K + 1)], False)
# write strobes: we0 logic at the strobe site, stage 1 beside it
depth = {}
for l in range(11):
    h = l
    pos = 0
    while h in PRED:
        h = PRED[h]
        pos += 1
    depth[l] = KC[h] + 2 * pos
    pts = path_to_in(SITE_IOCFG if l >= 8 else SITE_CFG, l, IN_WE)
    chain(f"strobe{l}", rf"^g_we\[{l}\]\.q\[(\d+)\]", 1, pts, [(k - 1) / depth[l] for k in range(1, depth[l] + 1)], True)
# status: leaf out regs -> KS relays -> combine point beside the status pins
for l in range(11):
    pts = path_out(l, OUT_STAT, SITE_ST)
    chain(f"status{l}", rf"^g_st\[{l}\]\.q\[(\d+)\]", SW, pts, [k / (KS + 1) for k in range(1, KS + 1)], False)
# outputs: leaf out_cal -> KO-1 relays -> the S-face pin registers (compiler_control / io_word, pin x ascending with bit)
for l in range(11):
    if l < 8:
        lo, n = 222 * l, OWID[l]
        x = 21.6 + (lo + n / 2) * (452.0 - 21.6) / 1742
    else:
        lo, n = 222 * (l - 8), OWID[l]
        x = 452.0 + (lo + n / 2) * (568.8 - 452.0) / 471
    pts = path_out(l, OUT_CAL, (round(x, 1), 4.0))
    chain(f"out{l}", rf"^g_oc\[{l}\]\.q\[(\d+)\]", OWID[l], pts, [k / KO for k in range(1, KO)], False)

for c in chains:
    for p in c["stages"]:
        if blocked(p):
            raise SystemExit(f"stage point inside a leaf: {c['name']} {p}")
worst = max(chains, key=lambda c: c["max_leg_um"])
bad = [c["name"] for c in chains if c["max_leg_um"] > REACH]
plan = dict(schema="opentallas.sfu_store_r11.relay_plan.v1", reach_um=REACH, KR=KR, KI=KI, KL=KL, KS=KS, KO=KO, KC=KC,
            strobe_depth=depth, worst_chain=worst["name"], worst_leg_um=worst["max_leg_um"], over_reach=bad,
            expected_flops=sum(c["width"] * len(c["stages"]) for c in chains if "(\\d+)" in c["regex"]), chains=chains)
(KIT / "relay_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
if bad:
    sys.exit(f"relay plan: legs over {REACH} um: {bad}")

tcl = ["# GENERATED by relay_place_gen.py (HBM-ELEMOWN3/SFUPS 2026-10-19) -- do not edit; re-run the generator.",
       "# PRE_GLOBAL_PLACE hook (spec pin_hook_before_flops): every r11 relay stage FIRM at its channel point (plan:",
       "# relay_plan.json; legs <= %.0f um, worst %s %.1f um), packed legally by anchor_row_packing.tcl, released for DPL by"
       % (REACH, worst["name"], worst["max_leg_um"]),
       "# relay_release.tcl.  Placement only: no cells, nets, clocks or constraints change.",
       "set ot_rl_blk [ord::get_db_block]",
       "set ot_rl_dbu [[ord::get_db_tech] getDbUnitsPerMicron]",
       "# name-regex  stage-width  {x y} per stage  {ux uy} per stage: a W-bit stage is spread along its channel",
       "# (bit b at (b - (W-1)/2) x SPREAD um from the stage point) so a bus stage is a bus, not a blob",
       "set ot_rl_spread 0.6",
       "set ot_rl_plan {"]
for c in chains:
    tcl.append("  {%s %d {%s} {%s}}" % ("{" + c["regex"] + "}", c["width"], " ".join("{%g %g}" % p for p in c["stages"]),
                                       " ".join("{%d %d}" % d for d in c["dirs"])))
tcl += ["}",
        "set ot_rl_insts {}",
        "foreach i [$ot_rl_blk getInsts] {",
        "  if {[[$i getMaster] isBlock]} continue",
        "  set m [[$i getMaster] getName]",
        "  if {![string match {DFF*} $m] && ![string match {ASYNC_DFF*} $m]} continue",
        "  lappend ot_rl_insts [list [string map {\\\\ {}} [$i getName]] $i]",
        "}",
        "set ot_rl_list {}; set ot_rl_miss {}; set ot_rl_total 0",
        "foreach row $ot_rl_plan {",
        "  lassign $row re w pts dirs",
        "  set n 0",
        "  foreach p $ot_rl_insts {",
        "    lassign $p name inst",
        "    if {![regexp -- $re $name -> idx]} continue",
        "    if {[$inst isFixed]} continue",
        "    set st 0; set bit 0",
        "    if {[string is integer -strict $idx]} { set st [expr {$idx / $w}]; set bit [expr {$idx % $w}] }",
        "    if {$st >= [llength $pts]} { set st [expr {[llength $pts] - 1}] }",
        "    lassign [lindex $pts $st] x y",
        "    lassign [lindex $dirs $st] ux uy",
        "    set off [expr {($bit - ($w - 1) / 2.0) * $ot_rl_spread}]",
        "    set x [expr {$x + $ux * $off}]; set y [expr {$y + $uy * $off}]",
        "    $inst setLocation [expr {round($x * $ot_rl_dbu)}] [expr {round($y * $ot_rl_dbu)}]",
        "    $inst setPlacementStatus FIRM",
        "    lappend ot_rl_list [$inst getName]",
        "    incr n",
        "  }",
        "  if {$n == 0} { lappend ot_rl_miss $re }",
        "  incr ot_rl_total $n",
        "}",
        "puts \"OT_RELAY_PLACE matched $ot_rl_total relay flops on [expr {[llength $ot_rl_plan] - [llength $ot_rl_miss]}] / [llength $ot_rl_plan] plan rows\"",
        "if {[llength $ot_rl_miss]} { puts \"OT_RELAY_PLACE rows with no flop: $ot_rl_miss\" }",
        "if {[llength $ot_rl_miss] > [llength $ot_rl_plan] / 4} { error \"OT_RELAY_PLACE: [llength $ot_rl_miss] plan rows matched no flop (netlist naming changed?)\" }",
        "if {[llength $ot_rl_list]} {",
        "  set ot_anchor_script /src/physical/common_flow/anchor_row_packing.tcl",
        "  if {![file exists $ot_anchor_script] && [info script] ne \"\"} {",
        "    set ot_anchor_script [file join [file dirname [info script]] .. .. common_flow anchor_row_packing.tcl]",
        "  }",
        "  source $ot_anchor_script",
        "  ot_anchor_pack::repair $ot_rl_blk $ot_rl_list",
        "}",
        "set fh [open $::env(RESULTS_DIR)/ot_relay_place.txt w]",
        "foreach n $ot_rl_list { puts $fh $n }",
        "close $fh",
        ""]
(KIT / "relay_place.tcl").write_text("\n".join(tcl))
(KIT / "relay_release.tcl").write_text("\n".join([
    "# PRE_DETAIL_PLACE hook (spec pre_dpl_extra, HBM-ELEMOWN3/SFUPS 2026-10-19): release the r11 relay flops fixed by",
    "# relay_place.tcl back to PLACED so detailed_placement legalises them at their channel points.",
    "set ot_rl_blk [ord::get_db_block]",
    "set ot_rl_f $::env(RESULTS_DIR)/ot_relay_place.txt",
    "set ot_rl_n 0",
    "if {[file exists $ot_rl_f]} {",
    "  set fh [open $ot_rl_f r]",
    "  foreach n [split [read $fh] \"\\n\"] {",
    "    if {$n eq \"\"} continue",
    "    set i [$ot_rl_blk findInst $n]",
    "    if {$i eq \"NULL\" || $i eq \"\"} continue",
    "    $i setPlacementStatus PLACED",
    "    incr ot_rl_n",
    "  }",
    "  close $fh",
    "}",
    "puts \"OT_RELAY_PLACE released $ot_rl_n relay flops for DPL\"",
    ""]))
print(f"relay plan: {len(chains)} chains, {plan['expected_flops']} relay flops, worst leg {worst['name']} {worst['max_leg_um']} um")
for c in sorted(chains, key=lambda c: -c["max_leg_um"])[:8]:
    print(f"  {c['name']}: length {c['length_um']} legs {c['legs_um']}")
