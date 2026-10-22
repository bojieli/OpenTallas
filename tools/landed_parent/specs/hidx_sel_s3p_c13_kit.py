#!/usr/bin/env python3
"""HBM-ELEM13/IDX-SEL 10-21: hidx_sel_s3p_c13a (MAIN) / c13b (FALLBACK) = the selector landed cluster after the c12 / c12b
CTS gates (ep9 10-21, both terminal FAIL: textbook.reset_landing + clock_rule ck_ctl 89.8 / 126.0 ps, ck_q2 199.0 / 235.6 TT).

Root cause (4_1_cts.odb sink census of c12, run dir ot-epyc9 .../ref_gate/hidx_sel_s3p_c12-20261021-103751):
  * ck_ctl: the five rst_n capture copies u_lpr_root_* were FIRM at the S face (io_flop_at_pins, y 2-4 um), 300 um from the
    other 701 ck_ctl sinks (y 165-401): the H-tree centred on the cluster sent a branch back to the face -> 409.6 ps TT
    against the ctl child flops at 320-325 ps.  rst_n also reached those 5 flops directly (reset_landing FAIL).
  * ck_q2: the region's 239 soft sinks spread x 116-349 / y 212-356 (pulled toward ctl), 300 um from the port, while the
    q2 clock pin sits 146 um from it (pin 98 ps, child flops 369-405, soft 422-568).  TritonCTS balances the macro and
    register trees only by PADDING the register tree up to pin + ETM insertion (286 ps TT); it never delays the macro
    branch, so a soft tree LATER than pin + 286 cannot be balanced.  q0 / q1 passed (40.8 / 65.0 ps) only because their
    soft cluster happened to sit beside their clock pin.
Fix (structural, no knob retry):
  * RTL (lp + hard + tb + record): rst_n -> u_rst_l0 -> u_rst_l1 (2 plain kept stages, ck_ctl) -> the 5 kept equal-age root
    copies; reset release +2 edges for every region (RB 2 -> 4, tb flat reference delayed 4).
  * ONE compact soft-sink fence per region root (landed-regions standard, pslice_c5 r10 pattern): write rings beside their
    source region, reads (+ their read-mux cones) beside their reader, the reset chain in the ctl box; each box sits on the
    PORT side of its child's clock pin so the register tree is earlier than pin + child insertion and TritonCTS pads it to
    match; fences released after GPL, before DPL / CTS (tools/landed_parent/lp_fence_release.tcl).
  * no pin anchor for rst_n (OT_OFLOP_PORT_RE matches no port): the landing stages live in the ctl box (S pin -> u_rst_l0
    <= ~240 um, one input hop inside the 405 um reach).
Variants (gated in parallel, same RTL / record / benches / closed child views s3u_b d903bcf15 + s3d_a db0cdd31d):
  a  691.2 x 648 (c12 outline, children as c12): ctl box in the centre column BELOW ctl (between the S-face ports and the
     ctl clock pin); q0 / q1 boxes under their clock pins, q2 / q3 boxes over their N faces (middle band).
  b  734.4 x 648 (q1 / q3 at x 432, ctl at x 345.6: 129.6-um centre column): ctl box below ctl; q2 / q3 boxes in the S
     channel beside their clock pins; q0 / q1 boxes under their clock pins.
  python3 tools/landed_parent/specs/hidx_sel_s3p_c13_kit.py a|b   -> physical/ref_tile/hidx_sel_s3p_c13<v>/spec.json (+ fences)
then: python3 tools/ref_tile/ref_tile.py gen physical/ref_tile/hidx_sel_s3p_c13<v>/spec.json
"""
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = "physical/ref_tile/hidx_sel_s3p_c12/spec.json"
HARD = "rtl/hbm_accel/index/sel_s3/lp/ot_hidx_s3_flat_lp_hard.sv"
REGIONS = ("ctl", "q0", "q1", "q2", "q3")
M = 6.48   # fence margin off every child edge (halo 5.4 + one site row)

VARIANTS = {
    "a": dict(
        w=691.2,
        kids={"u_q0": (43.2, 388.8), "u_q1": (388.8, 388.8), "u_q2": (43.2, 43.2), "u_q3": (388.8, 43.2), "u_ctl": (302.4, 302.4)},
        fences={
            "ctl": (302.4 + M, 151.2, 388.8 - M, 216.0),          # centre column, below ctl (port side of its clk pin)
            "q0": (43.2 + M, 345.6, 230.0, 388.8 - M),            # under q0's S face, W part (clk pin x 172.7)
            "q1": (388.8 + M, 345.6, 560.0, 388.8 - M),           # under q1's S face, W part (clk pin x 518.3)
            "q2": (43.2 + M, 259.2 + M, 230.0, 302.4 - M),        # over q2's N face (middle band)
            "q3": (388.8 + M, 259.2 + M, 560.0, 302.4 - M),       # over q3's N face (middle band)
        },
        why="c12 outline / children; boxes in the middle band and the centre column"),
    "b": dict(
        w=734.4,
        kids={"u_q0": (43.2, 388.8), "u_q1": (432.0, 388.8), "u_q2": (43.2, 43.2), "u_q3": (432.0, 43.2), "u_ctl": (345.6, 302.4)},
        fences={
            "ctl": (302.4 + M, 151.2, 432.0 - M, 216.0),          # wider centre column, below ctl
            "q0": (43.2 + M, 345.6, 230.0, 388.8 - M),
            "q1": (432.0 + M, 345.6, 615.0, 388.8 - M),
            "q2": (43.2 + M, 4.32, 230.0, 43.2 - M),               # S channel beside q2's clk pin (x 172.7)
            "q3": (432.0 + M, 4.32, 615.0, 43.2 - M),              # S channel beside q3's clk pin (x 561.5)
        },
        why="734.4 outline (q1 / q3 at x 432, ctl x 345.6); q2 / q3 boxes in the S channel beside their clock pins"),
}


def owners():
    """landing / reset instance -> region, read from the hard RTL's own .ck(ck_<r>) connections (fail closed)"""
    text = (ROOT / HARD).read_text()
    own = {}
    for m in re.finditer(r"\b(u_lpl_\d+_[wr]|u_lpr_root_\w+|u_lpr_\w+?|u_lprc_u_\w+|u_rst_l[01])\s*\(\s*\.ck\(ck_(\w+)\)", text):
        inst, r = m.group(1), m.group(2)
        if r not in REGIONS:
            raise SystemExit(f"fence owner: {inst} on unknown clock ck_{r}")
        own[inst] = r
    for r in REGIONS:
        if not any(v == r for v in own.values()):
            raise SystemExit(f"fence owner: region {r} has no landing / reset instance")
    if not {"u_rst_l0", "u_rst_l1"} <= set(own):
        raise SystemExit("fence owner: the hard RTL lacks the u_rst_l0 / u_rst_l1 face landing")
    return own


def fence_tcl(name, fences, own):
    o = [f"# generated by tools/landed_parent/specs/hidx_sel_s3p_c13_kit.py ({name}): PRE_GLOBAL_PLACE fences, ONE compact box per",
         "# region root holding every soft sink of that root (landing write rings in their SOURCE region, reads + their read-mux",
         "# cones in their READER region, the reset landing / root copies / regional pads in their clock's box).  Released after",
         "# GPL, before DPL / CTS (tools/landed_parent/lp_fence_release.tcl).",
         "set ::lpf_blk [ord::get_db_block]", "set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]", "array set ::lpf_g {}",
         "array set ::lpf_n {}", "array set ::lpf_c {}"]
    for r in REGIONS:
        x0, y0, x1, y1 = fences[r]
        o.append(f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_{r}"]')
        o.append(f"odb::dbBox_create $::lpf_r [expr {{round({x0:.2f}*$::lpf_dbu)}}] [expr {{round({y0:.2f}*$::lpf_dbu)}}] "
                 f"[expr {{round({x1:.2f}*$::lpf_dbu)}}] [expr {{round({y1:.2f}*$::lpf_dbu)}}]")
        o.append(f'set ::lpf_g({r}) [odb::dbGroup_create $::lpf_r "lp_fence_grp_{r}"]')
    o.append("array set ::lpf_own {" + " ".join(f"{k} {v}" for k, v in sorted(own.items())) + "}")
    o += ["proc lpf_seq {m} {",
          "  foreach mt [$m getMTerms] { if {[$mt getSigType] eq \"CLOCK\"} { return 1 } }",
          "  return 0",
          "}",
          "set ::lpf_reads {}",
          "foreach i [$::lpf_blk getInsts] {",
          "  if {[[$i getMaster] isBlock] || [[$i getMaster] getType] ne \"CORE\"} continue",
          "  regsub -all {\\\\} [$i getName] {} n",
          "  if {![regexp {^(u_lpl_[0-9]+_[wr]|u_lpr_root_(?:ctl|q[0-3])|u_lpr_(?:ctl|q[0-3])(?:_l)?|u_lprc_u_(?:ctl|q[0-3])|u_rst_l[01])[./]} $n -> h]} continue",
          "  if {![info exists ::lpf_own($h)]} { error \"LP_FENCE: $n has no landing owner\" }",
          "  if {[$i getGroup] ne \"NULL\"} continue",
          "  set r $::lpf_own($h)",
          "  $::lpf_g($r) addInst $i",
          "  incr ::lpf_n($r)",
          "  if {[string match *_r $h] && [lpf_seq [$i getMaster]]} { lappend ::lpf_reads [list $i $r] }",
          "}",
          "# read-mux cone: walk back from every read-half register's data inputs through ungrouped combinational cells",
          "foreach ir $::lpf_reads {",
          "  lassign $ir i r",
          "  set front [list $i]",
          "  for {set d 0} {$d < 16 && [llength $front]} {incr d} {",
          "    set nxt {}",
          "    foreach x $front {",
          "      foreach it [$x getITerms] {",
          "        if {![$it isInputSignal] || [[$it getMTerm] getSigType] eq \"CLOCK\"} continue",
          "        set net [$it getNet]",
          "        if {$net eq \"NULL\" || [$net getSigType] ne \"SIGNAL\"} continue",
          "        foreach dt [$net getITerms] {",
          "          if {![$dt isOutputSignal]} continue",
          "          set di [$dt getInst]",
          "          set dm [$di getMaster]",
          "          if {[$dm isBlock] || [$dm getType] ne \"CORE\" || [$di getGroup] ne \"NULL\" || [lpf_seq $dm]} continue",
          "          if {[$di getPlacementStatus] eq \"FIRM\" || [$di isFixed]} continue",
          "          $::lpf_g($r) addInst $di",
          "          incr ::lpf_c($r)",
          "          lappend nxt $di",
          "        }",
          "      }",
          "    }",
          "    set front $nxt",
          "  }",
          "}",
          "foreach r {" + " ".join(REGIONS) + "} {",
          "  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error \"LP_FENCE: region $r got no landing cells\" }",
          "  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }",
          "  puts \"LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)\"",
          "}"]
    return "\n".join(o) + "\n"


CHECKLIST = {
    "1_pins": "PASS: ports / faces unchanged from c12 (die slot pin plan); every input lands in a child pin register (in_line -> q in_p1, "
              "op/pass/addr/k -> ctl) or the rst_n face landing; every output leaves a child register; region crossings are the 20 lp landings",
    "2_reach": "PASS: single-cycle hops bounded by the fence plan (read o -> child ctl pins, child ret / qfault -> ring, root copy -> "
               "regional pad, S pin -> u_rst_l0) <= ~375 um; ring -> read is the declared E = 2 multicycle landing",
    "3_fanout": "PASS: c12 native census max 32 kept (chunk12 landings unchanged); +2 reset stages drive 1 load each",
    "4_depth": "PASS: datapath unchanged (c12 reg->reg +54 ps, in->macro / reg->macro repaired in route); no new logic",
    "5_storage": "PASS: no parent storage beyond the D = 4 landing slots; SRAMs only inside the closed q children",
    "6_floorplan": "PASS: children on the 43.2 lattice, >= 43.2-um channels, fences 6.48 um off every child edge, released before DPL",
    "7_clock": "FIXED (c12 FAIL ck_ctl 89.8 / ck_q2 199.0 TT): one compact soft box per region root on the PORT side of its child "
               "clock pin, so the register tree is earlier than pin + ETM insertion and TritonCTS pads it to match (it never "
               "delays the macro branch); the 5 face-anchored reset copies (ck_ctl late outliers) now sit in the ctl box",
    "8_reset": "FIXED (c12 FAIL reset_landing 5 sinks): rst_n -> u_rst_l0 -> u_rst_l1 (2 plain kept stages, ck_ctl) -> 5 kept "
               "equal-age root copies -> regional pads; reset only on control / valid; release +2 edges uniform (record RB 4)",
}


def main():
    v = sys.argv[1] if len(sys.argv) > 1 else "a"
    if v not in VARIANTS:
        raise SystemExit("usage: hidx_sel_s3p_c13_kit.py a|b")
    V = VARIANTS[v]
    name = f"hidx_sel_s3p_c13{v}"
    kd = f"physical/ref_tile/{name}"
    s = copy.deepcopy(json.loads((ROOT / BASE).read_text()))
    s["name"] = name
    s["outline"]["w"] = V["w"]
    for ch in s["children"]:
        ch["at"] = list(V["kids"][ch["inst"]])
    fence = f"tools/landed_parent/specs/{name}_fences.tcl"
    (ROOT / fence).write_text(fence_tcl(name, V["fences"], owners()))
    s["pin_hook_before_flops"] = [fence]
    s["pre_dpl_extra"] = ["tools/landed_parent/lp_fence_release.tcl"]
    s["orfs_vars"] = {"OT_OFLOP_PORT_RE": "^ot_no_pin_flop$"}
    s["reset_landing"] = {"enable": False, "reason": "the RTL lands it: rst_n -> u_rst_l0 -> u_rst_l1 (2 plain kept stages on "
                          "ck_ctl, fenced in the ctl box) -> 5 kept equal-age root copies u_lpr_root_* -> regional pads; the port "
                          "net has ONE sink; release +2 edges priced in the landed record (RB 4)"}
    s["safe_design_checklist"] = CHECKLIST
    sc = ("HBM-ELEM13/IDX-SEL c13" + v + " 10-21 (after c12/c12b CTS FAIL): 2-stage rst_n face landing in RTL (u_rst_l0/l1, "
          "release +2) + one compact soft-sink fence per region root on the port side of its child clock pin (TritonCTS pads "
          "registers up to pin + ETM insertion), reset chain in the ctl box, no pin anchor; " + V["why"] +
          "; children = CLOSED s3u_b d903bcf15 + s3d_a db0cdd31d views (exact).")
    s["structural_change"] = sc
    s["slot_change_request"] = (f"Selector parent {V['w']}x648 (ports / pin faces as c12); reset release +2 edges "
                                "(rst_n face landing), data latency unchanged; hard children exact s3u_b d903bcf15 + s3d_a db0cdd31d.")
    j = s["job"]
    j["owner"] = "Claude:HBM-ELEM13/IDX-SEL"
    j["branch"] = "claude/hbm-idx-sel-c13-1021"
    j["tag"] = f"c13{v}"
    j["purpose"] = sc
    j["extra_paths"] = [p for p in j["extra_paths"] if not p.startswith("physical/ref_tile/hidx_sel_s3p_")] + [kd]
    for b in j["benches"]:
        for k in ("pass_witness", "fail_witness"):
            if k in b:
                b[k] = b[k].replace("/lp_c12/", "/lp_c13/")
    (ROOT / kd).mkdir(parents=True, exist_ok=True)
    (ROOT / kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
    print(f"wrote {kd}/spec.json + {fence}")


if __name__ == "__main__":
    main()
