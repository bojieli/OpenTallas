#!/usr/bin/env python3
"""HBM-PSLICE9 10-20 r11: pslice_c5 lp11a / lp11b = the r10 floorplans (lp10a 21.6-um boxes / lp10b ~2x taller, fences
released before placement DPL + CTS) on NEW RTL ot_hbm_su_programme_pslice_c5_lp10 (lp.py spec pslice_c5_r10.json): lp10a/b were
REFUSED by the pre-gate native census (ring read rc counters 1,532 loads / 96 roots, comb 513, rq 205) because every landing
was one wide ot_pl_land ring/read whose slot selectors fanned out across 256 bits.  Now every landing is CHUNKED (8-bit kept
ot_pl_land_local_w/_r selectors, ot_pl_land_vector_reset_*) and each region's reset PORT feeds a kept reset forest
(ot_pl_land_reset_forest: prefix -> one branch per 32 leaves -> one leaf per landing chunk) of the SAME 3-stage depth
(lp.py regional_reset_ports + landing_reset_forest, new in HBM-PSLICE9): no driver above 32 loads, reset release edge and
every landing offset unchanged (record compiler block == r8).
  python3 tools/landed_parent/specs/pslice_c5_r11_kit.py a -> hbm_su_pslice_c5_lp11a (r10a boxes)
  python3 tools/landed_parent/specs/pslice_c5_r11_kit.py b -> hbm_su_pslice_c5_lp11b (r10b ~2x taller boxes)
(r10 docstring follows.)  HBM-QCORE8 10-20 r10: pslice_c5 = r9b fence plan (every leaf's ONE soft-sink box on its cfg face) + the boxes RELEASED
after global placement, before the placement DPL and CTS (PRE_DETAIL_PLACE hook tools/landed_parent/lp_fence_release.tcl).  r9b (ot-epyc5, cancelled 10-20 21:30 after 23 h in
GRT): at CTS every leaf root matched its child (TT c1 soft mean 510 / all 534 vs child 477..540), but the fences are
EXCLUSIVE, so the post-CTS detailed_placement (6,416 violations) pushed every ck_c<k>_regs buffer out of the 21.6-um strips
and the soft insertion grew to 764 (FF) / 901 (TT) ps on the L roots -> soft-vs-child FAIL c1..c3 250-282, c0/c4/c7/c8/c9
87-132 ps.  r9a died in placement DPL-0033 (41,008 fence violations, strips too full).  Variants (gated in parallel):
  python3 tools/landed_parent/specs/pslice_c5_r10_kit.py a -> hbm_su_pslice_c5_lp10a: r9b boxes (21.6 tall) + release
  python3 tools/landed_parent/specs/pslice_c5_r10_kit.py b -> hbm_su_pslice_c5_lp10b: boxes ~2x taller (L 38.7, S 43.2-44.3) + release
RTL / record / pins / benches = r8 / r9.  (r9 docstring follows.)
L2H-SU-FB 10-19 r9: ref_tile kits for ot_hbm_su_programme_pslice_c5_lp8 (same RTL / record / benches as r8), after the r8
CTS verdict (agidock128 lp8a/lp8b 4_1_cts): every leaf root failed the soft-vs-child pair (114-535 ps) EXCEPT the r8b S leaves
whose WHOLE register set sat in one strip beside the clock entry (c4 39 / c5 56 ps).  Sink census of 4_1_cts.odb: the regional
reset chains u_lpr_<r> (3) + u_lprc_u_<r> (4) were UNFENCED and drifted 100-640 um from the landing boxes (r8b c7 down to
y 306 from a y 918 box; c9 115 um away = 86 ps; c4 75 um = 39 ps), and in r8a / r8b-L the reads (cfg face) and the status
write rings (command face) were two groups 260-470 um apart on ONE root.  r9 = ONE compact sink cluster per leaf root:
every soft sink of ck_c<k> (read halves + their mux cones, status write rings, BOTH reset chains) and of ck_h (head rings,
status reads, u_lpr_h) is fenced into ONE box.  Variants (gated in parallel):
  python3 tools/landed_parent/specs/pslice_c5_r9_kit.py a -> hbm_su_pslice_c5_lp9a: S leaves = the r8b-passing form (whole
      cluster in the command-face strip beside the entry + child clk pin; read -> cfg pin hop 259 um); L leaves = whole
      cluster in the cfg-face box beside the register mass (read -> cfg pin local; status / reset-port hops ~460 um, below)
  python3 tools/landed_parent/specs/pslice_c5_r9_kit.py b -> hbm_su_pslice_c5_lp9b: EVERY leaf's cluster in its cfg-face box
      beside the register mass (reads beside their pins; the entry trunk crosses the leaf once; CTS latency balancing delays
      the child clk pin to the cluster, as r8b c7 showed: macro pin 407 ps = soft 700 ps)
(r8 docstring follows.)  L2H-PSLICE 10-19 r8: ref_tile kits for ot_hbm_su_programme_pslice_c5_lp8 (structural redesign of the landed pslice_c5
after real7 FAIL), two variants gated in parallel (same RTL / record / benches, different landing-fence plan):
  python3 tools/landed_parent/specs/pslice_c5_r8_kit.py a   -> hbm_su_pslice_c5_lp8a (reads on each leaf's cfg face, status
                                                                rings on its command face beside the status pins)
  python3 tools/landed_parent/specs/pslice_c5_r8_kit.py b   -> hbm_su_pslice_c5_lp8b (S leaves: reads AND status rings on the
                                                                command face beside the clock entry / clk pin; L leaves as a)
r8 vs real7: ELEVEN clock regions (head + one per leaf; each entry at its leaf's clk pin on the command face) and ELEVEN
regional reset ports rst_n_<r> (each landed 3 stages on its own root beside its pin, lp.py regional_reset_ports: no reset
root, no cross-region reset path); per-leaf command ports command_c<k>.  The real7 notes below describe the shared form.
(real7 docstring follows.)  PL-PSLICE 10-18: ref_tile kit for ot_hbm_su_programme_pslice_c5_lp.

Floorplan (1900.8 x 950.4 um, every child origin on the 43.2 lattice, >= 43.2 channels):
  bottom row R0 (cfg face N up into the channel, command face S = parent S face):  L c1 c2 c3 (x 43.2 / 432 / 820.8), S c0 c4
  (x 1209.6 / 1555.2);  central channel y 496.8..648 with the head (86.4^2) at its W end (x 43.2, y 518.4) beside the W-face
  configuration pins (head inputs W, outputs E -> broadcast east along the channel);  top row MX (cfg face down into the
  channel, command face = parent N face): S c5..c9 (x 129.6 + 345.6 k, y 648).
Every command bit's parent pin sits straight below / above its leaf pin (same x, same layer).
10-18 PL-KIT form (landed cluster: kind cluster + clock multiple_cts_roots + landed_record; the gate judges each region root
at the child flops).  Regions h {head} / l {c1 c2 c3} / t {c5..c9, the whole top S row} / b {c0 c4}; every leaf clk pin sits
on its command face, so each region's entry is on that face beside its clk pins: ck_h W face at the head's clk height, ck_l S
face at c2's clk x, ck_t N face at c7's clk x (centre of the row), ck_b S face midway between c0's and c4's clk pins (the
old ck_se E-face entry fed clk pins 950 um apart: macro pins 645..661 ps TT).  The command bus is split per region
(command_l / command_t / command_b: one driver region per output port).  Landing halves are FENCED (kit pre-GPL hook
<name>_fences.tcl, generated here from the lp record): write rings beside their source, reads beside their readers, so
the h tree is compact (real1: 3,705 ring flops spread 780 um along the channel, ck_h 532..925 ps) and the long run is the
multicycle ring -> read hop (E = 3).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VARIANT = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in ("a", "b") else sys.exit("usage: pslice_c5_r9_kit.py a|b")
NAME = "hbm_su_pslice_c5_lp11" + VARIANT
TALL = VARIANT == "b"
W, H = 1900.8, 950.4
VS = "physical/ref_tile/hbm_su_pgcol_s_r5/views/ot_hbm_su_programme_pgcol_s"
VL = "physical/ref_tile/hbm_su_pgcol_l_r5/views/ot_hbm_su_programme_pgcol_l"
VH = "physical/ref_tile/hbm_su_pghead_r5/views/ot_hbm_su_programme_pghead"
LS, LL, HS = (302.4, 259.2), (345.6, 453.6), (86.4, 86.4)
BOT = {1: 43.2, 2: 432.0, 3: 820.8, 0: 1209.6, 4: 1555.2}
TOP = {5: 129.6, 6: 475.2, 7: 820.8, 8: 1166.4, 9: 1512.0}
YB, YT, HEAD = 43.2, 648.0, (43.2, 518.4)
LDIR = "rtl/hbm_accel/generic/adapters/static_su/programme/landed"
SB = 2422


def lef_pins(path):
    t = (ROOT / path).read_text()
    out = {}
    for m in re.finditer(r"^\s*PIN (\S+)\n(.*?)^\s*END \1\s*$", t, re.S | re.M):
        r = re.search(r"LAYER (\S+) ;\s*RECT\s+([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)", m.group(2))
        if r:
            out[m.group(1)] = (r.group(1), (float(r.group(2)) + float(r.group(4))) / 2, (float(r.group(3)) + float(r.group(5))) / 2)
    return out


def port_bit(c, k):
    """leaf c's command bit k -> its per-leaf parent port bit (flat8: command == {command_c9[117:0], command_c8, .., command_c0})"""
    return f"command_c{c}[{k}]"


# fence boxes (um, x0 y0 x1 y1) per region: landing write rings in their SOURCE region, reads in their DESTINATION region.
# AD-HBM-SUK 10-18: COMPACT bands beside the faces the landings serve, never whole-region rectangles.  A fence is exclusive
# (DPL keeps every non-group cell -- the anonymous ring/read muxes, reset runs, repair buffers -- out of it): real2 fenced
# 1.72 of 1.79 mm^2, GPL did not converge, repair_design added ~1.2 M buffers and DPL stuck at 1.1 M illegal cells.
# TW2-PSLICE2 real7 10-19 (lp.py reader_per_inst + share_rings): fences PER LEAF, not per region.  real6 (DPL OK, CTS PASS,
# GRT ovf 0) failed setup -870 ps / TNS -364 ns on 1,453 read registers: the l / t / b region read halves sat by wirelength
# at x 224..590 next to the head's rings although their leaves span x 43..1857, so the same-root rc -> 8:1 mux -> o path and
# o -> far leaf ran 1-2 mm in one cycle and every region's soft flops were ~1 mm from its children (per-pair clock spread h
# 96 / l 168 / t ~364 / b 143 ps TT).  Now each leaf has its own read halves (and its status write rings) in a box on its cfg
# face, and the read-mux cone of every read register (8:1 slot mux, rc decode) is fenced WITH it, so the only long hop is the
# multicycle ring -> read bank (E = 3).  The head's 7 shared rings + 20 status reads sit in a short band on its E face.
# Every box keeps 6.48 um off macro edges (real5) and is <= 32.4 um tall (real4: DPL reach 27 um).
LEAF_W = {c: (345.6 if c in (1, 2, 3) else 302.4) for c in range(10)}


def leaf_box(c):
    x0 = BOT.get(c, TOP.get(c))
    x1 = x0 + LEAF_W[c] - 6.48
    x0 = max(x0 + 6.48, 136.08)                 # c1: E of u_h's halo (u_h x 43.2..129.6, y 518.4..604.8)
    if c in (1, 2, 3):
        return (x0, 503.28, x1, 541.98 if TALL else 524.88)   # above the L row's cfg (N) face; r10b 38.7 tall (h box from 545.4)
    if c in (0, 4):
        return (x0, 308.88, x1, 352.08 if TALL else 330.48)   # above c0 / c4's cfg (N) face; r10b 43.2 tall
    return (x0, 597.24 if TALL else 619.92, x1, 641.52)   # under the top row's cfg (S) face; r10b 44.3 tall (h box to 577.8)


def cmd_box(c):
    """L2H-PSLICE r8: the 43.2-um strip between the leaf's command face and the parent face (status pins busy / valid /
    done / fault / edge_index and the clk pin sit on this face): 6.48 um off the macro edge, 21.6 tall"""
    x0 = BOT.get(c, TOP.get(c))
    x1 = x0 + LEAF_W[c] - 6.48
    x0 = x0 + 6.48
    if c in BOT:
        return (x0, 10.8, x1, 32.4)             # under the bottom row (leaf y 43.2; parent S face y 0)
    return (x0, 918.0, x1, 939.6)               # over the top MX row (leaf top y 907.2; parent N face y 950.4)


FENCES = {"h": [(136.08, 545.4, 302.4, 577.8)]}  # beside the head's E (output) face; 7 rings + 20 status reads
# r8a: reads on the cfg face box (c<k>), status write rings on the command face box (c<k>s).  r8b: S leaves keep ALL their
# landing halves on the command face box (c<k>s, beside the clock entry and the clk pin); L leaves (453.6 tall: read ->
# cfg pin would be a > 405-um single-cycle hop) as r8a.
# r9: ONE box per leaf root holds every soft sink of that root (reads + cones, status write rings, both reset chains)
ON_CMD = set()   # r10: every leaf in its cfg-face box (r9b form)


def box_key(c):
    return f"c{c}s" if c in ON_CMD else f"c{c}"


FENCES.update({box_key(c): [cmd_box(c) if c in ON_CMD else leaf_box(c)] for c in range(10)})


def owner(inst):
    if inst == "u_h":
        return "h"
    m = re.fullmatch(r"u_c(\d)", inst)
    if not m:
        raise SystemExit(f"fence owner: {inst} is not a pslice child")
    return f"c{m[1]}"


def fence_tcl(name, rec):
    own = {}
    for L in rec["landings"]:
        g = L["ring"].split()[0]
        if g == f"u_lpl_{L['name']}_w":
            src = [x for x in L["src_nodes"] if not x.startswith("port:")]
            o_ = owner(src[0]) if src else "h"
            own[g[:-2] + "_w"] = box_key(int(o_[1:])) if o_ != "h" else o_   # r9: status rings in the leaf's ONE box
        rd = owner(L.get("dst_inst") or L["readers"][0].split(".")[0])
        own[f"u_lpl_{L['name']}_r"] = box_key(int(rd[1:])) if rd != "h" else rd
    # r9: the regional reset chains join their root's box (r8 left them free: they drifted 100-640 um and set the soft max)
    for r in ["h"] + [f"c{c}" for c in range(10)]:
        k = r if r == "h" else box_key(int(r[1:]))
        own[f"u_lpr_{r}"] = k
        if r != "h":
            own[f"u_lprc_u_{r}"] = k
    o = [f"# generated by tools/landed_parent/specs/pslice_c5_kit.py ({name}): PRE_GLOBAL_PLACE fences of the lp.py landing halves",
         "# (landed-regions standard: ring ot_pl_land_w beside its source, read ot_pl_land_r beside its reader leaf), PER LEAF;",
         "# each read half's input cone (slot mux, rc decode: anonymous combinational cells back to the ring / its own",
         "# registers) joins its fence.  r9: the regional reset chains u_lpr_<r> / u_lprc_u_<r> join their root's ONE box.",
         "set ::lpf_blk [ord::get_db_block]", "set ::lpf_dbu [$::lpf_blk getDbUnitsPerMicron]", "array set ::lpf_g {}",
         "array set ::lpf_n {}", "array set ::lpf_c {}"]
    for r, boxes in FENCES.items():
        o.append(f'set ::lpf_r [odb::dbRegion_create $::lpf_blk "lp_fence_{r}"]')
        for (x0, y0, x1, y1) in boxes:
            o.append(f"odb::dbBox_create $::lpf_r [expr {{round({x0}*$::lpf_dbu)}}] [expr {{round({y0}*$::lpf_dbu)}}] "
                     f"[expr {{round({x1}*$::lpf_dbu)}}] [expr {{round({y1}*$::lpf_dbu)}}]")
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
          "  if {![regexp {^(u_lpl_[0-9]+_[wr]|u_lprc?_(?:u_)?(?:h|c[0-9]))[./]} $n -> h]} continue",
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
          "          $::lpf_g($r) addInst $di",
          "          incr ::lpf_c($r)",
          "          lappend nxt $di",
          "        }",
          "      }",
          "    }",
          "    set front $nxt",
          "  }",
          "}",
          "foreach r {" + " ".join(FENCES) + "} {",
          "  if {![info exists ::lpf_n($r)] || $::lpf_n($r) < 1} { error \"LP_FENCE: region $r got no landing cells\" }",
          "  if {![info exists ::lpf_c($r)]} { set ::lpf_c($r) 0 }",
          "  puts \"LP_FENCE $r cells=$::lpf_n($r) read_cone=$::lpf_c($r)\"",
          "}"]
    return "\n".join(o) + "\n"


def main():
    # --diag (10-18, while pgcol_l is SUBMITTED but not CLOSED): the three L slots hold the CLOSED S view as a stand-in so
    # the h / sw / se regions, the landings, the channel and the pins are gated now; never submitted, never bound
    diag = False
    name = NAME
    vl = VL
    s = lef_pins(f"{VS}/ot_hbm_su_programme_pgcol_s.lef")
    h = lef_pins(f"{VH}/ot_hbm_su_programme_pghead.lef")
    # L view not closed yet: its kit spreads command over pin range [4.0, 169.612] exactly as the S kit spread [4.0, 148.0]
    # (S LEF: command[0] x 4.293 .. command[255] x 147.708, M3 even / M5 odd) -> same rule scaled to the L range
    s0, s1 = s["command[0]"][1], s["command[255]"][1]
    l0, l1 = s0, s0 + (s1 - s0) * (169.612 - 4.0) / (148.0 - 4.0)
    # real kit (pgcol_l CLOSED 10-18 06:47, hbm_su_pgcol_l_r5-r5-0fb4501e8): take the L pins from its LEF (the scaled
    # estimate was off by up to 0.08 um, i.e. off the leaf's own tracks)
    lp = None if diag else lef_pins(f"{VL}/ot_hbm_su_programme_pgcol_l.lef")
    lines = [f"# generated by tools/landed_parent/specs/pslice_c5_kit.py ({NAME}): command bits straight under / over their leaf"
             " pins (bottom row S face, top row N face), cfg / reset / start / length / fault on the W face beside the head,"
             " region clocks beside their regions"]

    def pin(n, layer, x, y):
        sz = {"M3": "0.018 0.144", "M5": "0.024 0.192", "M4": "0.192 0.024", "M6": "0.192 0.032"}[layer]
        lines.append(f"place_pin -pin_name {{{n}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary")

    for c in range(10):
        big = c in (1, 2, 3)
        x0 = BOT.get(c, TOP.get(c))
        y = 0.0 if c in BOT else H
        for k in range(256):
            b = 256 * c + k
            if b >= SB:
                break
            lx = (lp[f"command[{k}]"][1] if lp else l0 + (l1 - l0) * k / 255) if big else s[f"command[{k}]"][1]
            pin(port_bit(c, k), "M3" if k % 2 == 0 else "M5", x0 + lx, y)
    # column 0 (S, bottom row) drives busy / valid / done / edge_index: straight under its pins
    for n in ["busy", "valid", "done"] + [f"edge_index[{k}]" for k in range(16)]:
        L_, x, _ = s[n]
        pin(n, L_, BOT[0] + x, 0.0)
    # W face: head inputs at their own height (head at y 518.4), then start / length / fault above the head
    hx, hy = HEAD
    for n, (L_, x, y) in sorted(h.items()):
        if n.startswith("cfg_"):
            pin(n, "M4", 0.0, hy + y)
        elif n == "rst_n":
            pin("rst_n_h", "M4", 0.0, hy + y)            # r8: the head region's own reset port at the head's rst_n height
    pin("ck_h", "M4", 0.0, hy + h["clk"][2])
    ys = 609.0
    for n in ["start"] + [f"length[{k}]" for k in range(16)] + ["fault"]:
        pin(n, "M4", 0.0, ys)
        ys += 1.92
    # r8 region clocks + regional resets: one per leaf, the clock entry straight under / over the leaf's own clk pin on its
    # command face, the reset port 1.512 um (42 M3 tracks) W of it (between command[255] and clk on every leaf)
    for c in range(10):
        cx = (lp["clk"][1] if (lp and c in (1, 2, 3)) else s["clk"][1])
        x0 = BOT.get(c, TOP.get(c))
        y = 0.0 if c in BOT else H
        pin(f"ck_c{c}", "M3", x0 + cx, y)
        pin(f"rst_n_c{c}", "M3", x0 + cx - 1.512, y)
    tcl = ROOT / f"tools/ref_tile/specs_hbm_su/{NAME}_pins.tcl"
    tcl.write_text("\n".join(lines) + "\n")

    kids = [dict(view=VH, count=1, inst="u_h", at=list(HEAD), orient="R0")]
    for c in range(10):
        v = vl if c in (1, 2, 3) else VS
        if c in BOT:
            kids.append(dict(view=v, count=1, inst=f"u_c{c}", at=[BOT[c], YB], orient="R0"))
        else:
            kids.append(dict(view=v, count=1, inst=f"u_c{c}", at=[TOP[c], YT], orient="MX"))
    rec_path = "results/arch/landed_parent_1018/pslice_c5_r10/ot_hbm_su_programme_pslice_c5_lp10_record.json"
    rec = json.loads((ROOT / rec_path).read_text())
    fence = f"tools/ref_tile/specs_hbm_su/{name}_fences.tcl"
    (ROOT / fence).write_text(fence_tcl(name, rec))
    W5 = "results/arch/landed_parent_1018/pslice_c5_r10/bench_v5050/bench_summary.log"
    W8 = "results/arch/landed_parent_1018/pslice_c5_r8/bench_v5050/bench_summary.log"   # flat8 eq: flat8 RTL unchanged since r8
    benches = [
        dict(name="lp_lockstep_mut0", cmd=f"MUTS=0 SIM=verilator bash {LDIR}/ot_hbm_su_programme_pslice_c5_lp10_bench.sh {{RUN}}/bench/lp0",
             expect="pass", pass_regex="MUT 0: LP_LOCKSTEP PASS", threads=8, peak_ram_gb=24, needs=["verilator"]),
        dict(name="lp_mut1_bypass", cmd=f"MUTS=1 SIM=verilator bash {LDIR}/ot_hbm_su_programme_pslice_c5_lp10_bench.sh {{RUN}}/bench/lp1",
             expect="fail", fail_regex="MUT 1: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"],
             fail_witness=W5),
        dict(name="lp_mut2_read_k1", cmd=f"MUTS=2 SIM=verilator bash {LDIR}/ot_hbm_su_programme_pslice_c5_lp10_bench.sh {{RUN}}/bench/lp2",
             expect="fail", fail_regex="MUT 2: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"],
             fail_witness=W5),
        dict(name="flat8_eq_mut0", cmd=f"ONLY=0 LP_ROOT=. bash {LDIR}/pslice_c5_flat8_eq_bench.sh {{RUN}}/bench/eq0",
             expect="pass", pass_regex="EQ MUT 0: FLAT_EQ PASS", threads=8, peak_ram_gb=24, needs=["verilator"]),
        dict(name="flat8_eq_mut1_phase", cmd=f"ONLY=1 LP_ROOT=. bash {LDIR}/pslice_c5_flat8_eq_bench.sh {{RUN}}/bench/eq1",
             expect="fail", fail_regex="EQ MUT 1: FLAT_EQ FAIL", threads=8, peak_ram_gb=24, needs=["verilator"],
             fail_witness=W8),
    ]
    regions = list(rec["regions"])
    dom = dict(core=dict(ratio=[1, 1], ports=["ck_h"], inputs=["cfg_we", "cfg_bank", "cfg_row", "cfg_data", "start", "length",
                                                                 "rst_n_h"], outputs=["fault"]))
    for c in range(10):
        dom[f"c{c}"] = dict(ratio=[1, 1], ports=[f"ck_c{c}"], inputs=[f"rst_n_c{c}"],
                            outputs=[f"command_c{c}"] + (["busy", "valid", "done", "edge_index"] if c == 0 else []))
    S_ = [f"command_c{c}" for c in BOT] + ["busy", "valid", "done", "edge_index"] + [f"ck_c{c}" for c in BOT] + [f"rst_n_c{c}" for c in BOT]
    N_ = [f"command_c{c}" for c in TOP] + [f"ck_c{c}" for c in TOP] + [f"rst_n_c{c}" for c in TOP]
    LS_ = "S leaves (command-face strip beside the entry; read -> cfg pin hop <= 259 um vertical)" if VARIANT == "a" else \
        "S leaves (cfg-face box beside the register mass; status pin -> ring and reset port -> stage 1 hops 259 um)"
    checklist = {
        "1_pins": "PASS: every input lands on a child pin register (head c_* stage) or a landing ring; every output leaves a child register; "
                  "each regional reset port lands on its own root (r11: kept forest u_lpr_<r> prefix -> branch -> leaf = 3 stages, + u_lprc_u_<r> 4 stages, "
                  "lp regional_reset_ports + landing_reset_forest); reset only on control/valid (selectors, counters, valid; ring data unreset); "
                  "r9: both chains fenced in their root's one box",
        "2_reach": "WAIVED (L leaves only, 3 bits per L leaf): the L leaf (453.6 um tall) has its cfg pins on one face and clk / status / "
                   "reset pins on the other, so one compact cluster per root leaves three single-cycle hops of ~455-470 um "
                   "(rst_n_c<k> port -> u_lpr stage 1, child fault / valid -> status write ring), each one repeated bit, STA-timed at "
                   "TT / FF, inside the measured 600-750 um repeated reach; the alternative (a relay or a second register group "
                   "on the same root) is exactly what failed r8 (stray sinks 100-640 um from the cluster = 86-535 ps soft spread). "
                   "Everything else PASS: head ring -> leaf read is the E = 3 multicycle landing (<= ~1.9 mm); " + LS_,
        "3_fanout": "r11 FIXED (lp10a/b census: ring read rc 1,532 loads / 96 roots, comb 513, rq 205): landings chunked at 8 bits with kept "
                    "per-chunk one-hot selectors (slot enable 2 x 12 + 1 = 25 loads; 16-bit census max was 41), each chunk reset from its own forest leaf (1 load), forest prefix -> "
                    "<= 2 branches, branch -> <= 32 leaves; pre-gate native census decides (numbers in the gate packet)",
        "4_depth": "PASS: landing read = 8:1 registered slot mux (lp ot_pl_land_r); no combinational in -> out path (all child-registered)",
        "5_storage": "PASS: ring banks are D = 8 slot landings (fixed-latency rings, not runtime-indexed storage); leaf storage is SRAM in the hard leaves",
        "6_floorplan": "PASS: children on the 43.2 lattice, 43.2-um command strips + 151-um cfg channel; child faces <= 3.5 pins/um (head W 302 / 86.4); "
                       "fill 57% (1.03 mm2 macros / 1.81 mm2); aspect 2:1; fences 6.48 um off every macro edge, <= 21.6 tall; r9: one fence per root",
        "7_clock": "r10 FIXED (r9b FAIL after the post-CTS DPL pushed region tree buffers out of the exclusive fences): fences released "
                   "before CTS, so CTS / repair buffers sit beside their sinks. r9: FIXED (r8 FAIL: soft vs child 114-535 ps on 10 of 11 roots): 11 regional roots, entry at each leaf's clk pin; r9 puts EVERY "
                   "soft sink of a root (reads + cones, status rings, reset chains) in ONE <= 21.6-um box (r8 census: unfenced reset chains "
                   "100-640 um away and split read / ring groups set the soft max); landed crossings between every pair; io_hold_margin "
                   "0.03; hard-child clock references from views/<child>/insertion.json",
        "8_schedule": "PASS: static; r11 record compiler block identical to r8 (no latency change, same ports); RTL / record otherwise as r8 (pslice_c5_r8: leaves +4 edges, reset release +3, head status lag 8); r9 is "
                      "placement only, 0 added cycles",
    }
    spec = dict(
        name=NAME, top="ot_hbm_su_programme_pslice_c5_lp10", kind="cluster",
        sources=[f"{LDIR}/ot_hbm_su_programme_pslice_c5_lp10.sv", "rtl/common/landed_parent/ot_pl_land.sv",
                 "rtl/common/landed_parent/ot_pl_land_field_copies.sv", "rtl/common/landed_parent/ot_pl_land_reset_forest.sv"],
        params={}, clock="multiple_cts_roots", clock_port="ck_h",
        clock_ports=[rec["regions"][r]["clock_port"] for r in regions],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dom,
        landed_record=rec_path,
        reset_ports=[f"rst_n_{r}" for r in regions],
        outline=dict(w=W, h=H, exact=True),
        children=kids, macros=[], inter=[],
        pins={"S": S_, "W": ["cfg_data", "cfg_bank", "cfg_row", "cfg_we", "rst_n_h", "start", "length", "fault", "ck_h"], "N": N_},
        io_tcl=f"tools/ref_tile/specs_hbm_su/{NAME}_pins.tcl",
        route=dict(pd=0.5, threads=16, peak_ram_gb=64, macro_halo_um=5.4, pin_h="M4", pin_v="M3 M5",
                   hold_margin_ns=0.03, io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        # io_flop_at_pins only to carry the kit-local PRE_GLOBAL_PLACE hook (ref_tile pin_hook_flops_only): the landing fences
        io_flop_at_pins={"cols": 4, "allow_none": True},
        pin_hook_before_flops=[fence],
        pre_dpl_extra=["tools/landed_parent/lp_fence_release.tcl"],   # r10: after GPL, before placement DPL + CTS (multiple_cts_roots refuses PRE_CTS hooks)
        pin_regs=dict(enable=False, reason="every parent input lands on a child pin register (head c_* / leaf start-length "
                      "stage) or a landing ring in its region; every output leaves a child register (leaf command / status, "
                      "head fault); a kit flop stage would add an edge the landed record does not price"),
        reset_landing=dict(enable=False, reason="the RTL lands every regional reset port: rst_n_<r> has ONE sink, u_lpr_<r> "
                           "(r11: kept ot_pl_land_reset_forest DEPTH 3 on ck_<r> beside its pin: prefix + branch landing stages + one leaf per landing chunk; lp.py regional_reset_ports + landing_reset_forest, "
                           "priced in the landed record: reset release +3); a kit landing would add 2 unpriced release edges"),
        safe_design_checklist=checklist,
        slot_change_request="H-D4G pgp_<q> (r8, supersedes the real7 request): same slot 1900.8 x 950.4; PORT CHANGE: 11 region "
                            "clocks ck_h (W, head) + ck_c0..ck_c9 (each under / over its leaf's clk pin: c0..c4 S face, c5..c9 N "
                            "face) and 11 regional resets rst_n_h / rst_n_c<k> (beside each clock; the die releases all 11 on the "
                            "SAME edge, each timed on its own region clock: die obligation in the record); command split per leaf "
                            "command_c0..c8[255:0] + command_c9[117:0] (command = {command_c9, .., command_c0}); "
                            "busy/valid/done/edge_index on ck_c0; every output +4 edges, reset release +3 (was +6)",
        why_floorplan="unchanged from real7 / r8: two leaf rows facing one configuration channel, head at its W end; r9 changes only "
                      "the landing fences: one box per root holding all of its soft sinks; r10 releases them before CTS",
        landed=dict(record=rec_path, landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"],
                    reset_depth=rec["reset"]["depth"], lp_spec="tools/landed_parent/specs/pslice_c5_r10.json"),
        structural_change="HBM-PSLICE9 10-20 r11: NEW RTL lp10 (chunked 16-bit kept landing selectors + per-region reset forest fed by its own reset port, same depth; lp10a/b native census refused the r8 RTL: rc 1,532 loads). Floorplan = HBM-QCORE8 r10: r9b fence plan" + (" with ~2x taller boxes" if TALL else "") + ", the "
                          "fences RELEASED before CTS (lp_fence_release.tcl): r9b's exclusive fences pushed the region tree buffers out "
                          "of the strips at the post-CTS DPL, soft insertion +360 ps on the L roots -> soft-vs-child FAIL 87-282 ps. "
                          "Prior: L2H-SU-FB 10-19 r9 (after r8 CTS FAIL: per-leaf soft vs child 114-535 ps; 4_1_cts sink census: unfenced "
                          "regional reset chains 100-640 um from the landing boxes, r8a / r8b-L reads and status rings 260-470 um "
                          "apart on one root; only the r8b S leaves with everything in one strip passed, 39 / 56 ps): ONE fence per "
                          "root holds every soft sink of that root (reads + cones, status write rings, u_lpr_<r> + u_lprc_u_<r>). "
                          "RTL, record, ports, pins, benches = r8. Variant " + VARIANT + ": " + (
                              "S leaves in the command-face strip (r8b form), L leaves in the cfg-face box" if VARIANT == "a" else
                              "every leaf in its cfg-face box beside the register mass"),
        job=dict(owner="Claude:DRIVE-HBM/HBM-PSLICE9", branch="claude/hbm-pslice10-1020", tag="r11" + VARIANT,
                 purpose="landed per-quarter SU programme cluster pslice_c5 (pgp_<q>), r11 chunked landings + regional reset forest, r10 fences released before CTS",
                 views_to=f"physical/ref_tile/{NAME}/views", record_to=f"results/rtl/ref_tile/{NAME}",
                 extra_paths=["tools/landed_parent", "rtl/common/landed_parent", "rtl/lib",
                              "rtl/hbm_accel/generic/adapters/static_su/programme",
                              "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2",
                              "results/arch/landed_parent_1018/pslice_c5_r8",
                              "results/arch/landed_parent_1018/pslice_c5_r10"],
                 benches=benches))
    name = NAME
    out = ROOT / f"tools/ref_tile/specs_hbm_su/{name}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out, tcl, len(lines) - 1, "pins")


if __name__ == "__main__":
    main()
