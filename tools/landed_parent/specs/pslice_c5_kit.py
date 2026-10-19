#!/usr/bin/env python3
"""PL-PSLICE 10-18: ref_tile kit for ot_hbm_su_programme_pslice_c5_lp (the landed per-quarter SU programme cluster, pgp_<q>).

Writes tools/ref_tile/specs_hbm_su/hbm_su_pslice_c5_lp.json + hbm_su_pslice_c5_lp_pins.tcl (exact pin plan).

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
NAME = "hbm_su_pslice_c5_lp"
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
    """leaf c's command bit k -> its per-region parent port bit (flat parent: command == {command_t, command_b[511:256],
    command_l, command_b[255:0]})"""
    if c in (1, 2, 3):
        return f"command_l[{256 * (c - 1) + k}]"
    if c in (0, 4):
        return f"command_b[{256 * (c // 4) + k}]"
    return f"command_t[{256 * (c - 5) + k}]"


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
        return (x0, 503.28, x1, 524.88)         # above the L row's cfg (N) face (496.8 + 6.48), 21.6 tall
    if c in (0, 4):
        return (x0, 308.88, x1, 330.48)         # above c0 / c4's cfg (N) face (302.4 + 6.48), 21.6 tall
    return (x0, 619.92, x1, 641.52)             # under the top row's cfg (S) face (648.0 - 6.48), 21.6 tall


FENCES = {"h": [(136.08, 545.4, 302.4, 577.8)]}  # beside the head's E (output) face; 7 rings + 20 status reads
FENCES.update({f"c{c}": [leaf_box(c)] for c in range(10)})


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
            own[g[:-2] + "_w"] = owner(src[0]) if src else "h"
        own[f"u_lpl_{L['name']}_r"] = owner(L.get("dst_inst") or L["readers"][0].split(".")[0])
    o = [f"# generated by tools/landed_parent/specs/pslice_c5_kit.py ({name}): PRE_GLOBAL_PLACE fences of the lp.py landing halves",
         "# (landed-regions standard: ring ot_pl_land_w beside its source, read ot_pl_land_r beside its reader leaf), PER LEAF;",
         "# each read half's input cone (slot mux, rc decode: anonymous combinational cells back to the ring / its own",
         "# registers) joins its fence.  Reset runs (u_lpr_*) stay free.",
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
          "  if {![regexp {^(u_lpl_[0-9]+_[wr])[./]} $n -> h]} continue",
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
    diag = "--diag" in sys.argv
    name = NAME + ("_diag" if diag else "")
    vl = VS if diag else VL
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
        if n.startswith(("cfg_", "rst_n")):
            pin(n, "M4", 0.0, hy + y)
    pin("ck_h", "M4", 0.0, hy + h["clk"][2])
    ys = 609.0
    for n in ["start"] + [f"length[{k}]" for k in range(16)] + ["fault"]:
        pin(n, "M4", 0.0, ys)
        ys += 1.92
    # region clocks
    pin("ck_l", "M3", BOT[2] + (lp["clk"][1] if lp else 172.712), 0.0)  # c2 clk pin x (L leaf clk)
    pin("ck_t", "M3", TOP[7] + s["clk"][1], H)               # c7 clk pin x (MX keeps x): centre of the 5-leaf top row
    pin("ck_b", "M3", (BOT[0] + BOT[4]) / 2 + s["clk"][1], 0.0)  # midway between c0's and c4's clk pins (1382.4 on the lattice)
    tcl = ROOT / f"tools/ref_tile/specs_hbm_su/{NAME}_pins.tcl"
    tcl.write_text("\n".join(lines) + "\n")

    kids = [dict(view=VH, count=1, inst="u_h", at=list(HEAD), orient="R0")]
    for c in range(10):
        v = vl if c in (1, 2, 3) else VS
        if c in BOT:
            kids.append(dict(view=v, count=1, inst=f"u_c{c}", at=[BOT[c], YB], orient="R0"))
        else:
            kids.append(dict(view=v, count=1, inst=f"u_c{c}", at=[TOP[c], YT], orient="MX"))
    rec_path = "results/arch/landed_parent_1018/pslice_c5/ot_hbm_su_programme_pslice_c5_lp_record.json"
    rec = json.loads((ROOT / rec_path).read_text())
    fence = f"tools/ref_tile/specs_hbm_su/{name}_fences.tcl"
    (ROOT / fence).write_text(fence_tcl(name, rec))
    benches = [
        dict(name="lp_lockstep_mut0", cmd=f"ONLY=0 SIM=verilator bash {LDIR}/ot_hbm_su_programme_pslice_c5_lp_bench.sh {{RUN}}/bench/lp0",
             expect="pass", pass_regex="MUT 0: LP_LOCKSTEP PASS", threads=8, peak_ram_gb=24, needs=["verilator"]),
        dict(name="lp_mut1_bypass", cmd=f"ONLY=1 SIM=verilator bash {LDIR}/ot_hbm_su_programme_pslice_c5_lp_bench.sh {{RUN}}/bench/lp1",
             expect="fail", fail_regex="MUT 1: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"],
             fail_witness="results/arch/landed_parent_1018/pslice_c5/bench_v5050/bench_summary.log"),
        dict(name="lp_mut2_read_k1", cmd=f"ONLY=2 SIM=verilator bash {LDIR}/ot_hbm_su_programme_pslice_c5_lp_bench.sh {{RUN}}/bench/lp2",
             expect="fail", fail_regex="MUT 2: LP_LOCKSTEP FAIL", threads=8, peak_ram_gb=24, needs=["verilator"],
             fail_witness="results/arch/landed_parent_1018/pslice_c5/bench_v5050/bench_summary.log"),
        dict(name="flat_eq_mut0", cmd=f"ONLY=0 LP_ROOT=. bash {LDIR}/pslice_c5_flat_eq_bench.sh {{RUN}}/bench/eq0",
             expect="pass", pass_regex="EQ MUT 0: FLAT_EQ PASS", threads=8, peak_ram_gb=24, needs=["verilator"]),
        dict(name="flat_eq_mut1_phase", cmd=f"ONLY=1 LP_ROOT=. bash {LDIR}/pslice_c5_flat_eq_bench.sh {{RUN}}/bench/eq1",
             expect="fail", fail_regex="EQ MUT 1: FLAT_EQ FAIL", threads=8, peak_ram_gb=24, needs=["verilator"],
             fail_witness="results/arch/landed_parent_1018/pslice_c5/bench_v5050/bench_summary.log"),
    ]
    spec = dict(
        name=NAME, top="ot_hbm_su_programme_pslice_c5_lp", kind="cluster",
        sources=[f"{LDIR}/ot_hbm_su_programme_pslice_c5_lp.sv", "rtl/common/landed_parent/ot_pl_land.sv"],
        params={}, clock="multiple_cts_roots", clock_port="ck_h",
        clock_ports=[rec["regions"][r]["clock_port"] for r in rec["regions"]],
        clock_data_paths="related_same_frequency",
        clock_relationship=dict(kind="same_pll_fixed_phase", ratio=[1, 1], phase_ps=0),
        clock_entry_domains=dict(
            core=dict(ratio=[1, 1], ports=["ck_h"], inputs=["cfg_we", "cfg_bank", "cfg_row", "cfg_data", "start", "length", "rst_n"],
                      outputs=["fault"]),
            l=dict(ratio=[1, 1], ports=["ck_l"], inputs=[], outputs=["command_l"]),
            t=dict(ratio=[1, 1], ports=["ck_t"], inputs=[], outputs=["command_t"]),
            b=dict(ratio=[1, 1], ports=["ck_b"], inputs=[], outputs=["command_b", "busy", "valid", "done", "edge_index"])),
        landed_record=rec_path,
        reset_ports=["rst_n"],
        outline=dict(w=W, h=H, exact=True),
        children=kids, macros=[], inter=[],
        pins={"S": ["command_l", "command_b", "busy", "valid", "done", "edge_index", "ck_l", "ck_b"],
              "W": ["cfg_data", "cfg_bank", "cfg_row", "cfg_we", "rst_n", "start", "length", "fault", "ck_h"],
              "N": ["command_t", "ck_t"]},
        io_tcl=f"tools/ref_tile/specs_hbm_su/{NAME}_pins.tcl",
        route=dict(pd=0.5, threads=16, peak_ram_gb=64, macro_halo_um=5.4, pin_h="M4", pin_v="M3 M5",
                   hold_margin_ns=0.03, io_hold_margin_ns=0.03),
        recipe=4, inhold=False, outhold=False,
        # io_flop_at_pins only to carry the kit-local PRE_GLOBAL_PLACE hook (ref_tile pin_hook_flops_only): the landing fences
        io_flop_at_pins={"cols": 4, "allow_none": True},
        pin_hook_before_flops=[fence],
        pin_regs=dict(enable=False, reason="every parent input lands on a child pin register (head c_* / leaf start-length "
                      "stage) or a landing ring in its region; every output leaves a child register (leaf command / status, "
                      "head fault); a kit flop stage would add an edge the landed record does not price"),
        reset_landing=dict(enable=False, reason="the RTL lands it: rst_n has ONE sink, u_lpr_root (ot_pl_pad on ck_h beside the "
                           "W-face pin), then the regional reset runs u_lpr_* (depth 6, priced in the landed record); a kit "
                           "landing would add 2 unpriced release edges"),
        slot_change_request="H-D4G pgp_<q>: slot 939.6 x 760.32 (flat pslice_q4) -> 1900.8 x 950.4 landed cluster (10 leaves "
                            "1.03 mm^2 incl. the 345.6-wide L leaf + head + 41 landings); cfg/start/length/fault/rst_n W face; "
                            "PORT CHANGE: command[2421:0] -> command_l[767:0] (S, cols 1..3) + command_b[511:0] (S, cols 0,4) + "
                            "command_t[1141:0] (N, cols 5..9); the parent re-assembles command = {command_t, command_b[511:256], "
                            "command_l, command_b[255:0]}; busy/valid/done/edge_index S under column 0; 4 region clocks ck_h W / "
                            "ck_l S / ck_b S / ck_t N, each timed on its own region (command_l on ck_l, command_t on ck_t, "
                            "command_b + status on ck_b, fault on ck_h); every output +4 edges, reset release +6",
        why_floorplan="two leaf rows facing one configuration channel: the head broadcasts east along it, every leaf's cfg face "
                      "touches it, every command bit leaves straight through its own face; regions by insertion class and "
                      "placement (L leaves TT 483 vs S 310): h = head, l = L row, sw = W S trio, se = E S quad",
        landed=dict(record="results/arch/landed_parent_1018/pslice_c5/ot_hbm_su_programme_pslice_c5_lp_record.json",
                    landings=len(rec["landings"]), landing_flops=rec["flops"]["landing"], reset_depth=rec["reset"]["depth"],
                    lp_spec="tools/landed_parent/specs/pslice_c5.json"),
        structural_change="PL-PSLICE (PARENTS-LANDED 10-18, landed-regions-standard-1018): pslice_c5 (head + 7 S + 3 L leaves, "
                          "r5 per-column split) as a LANDED parent: 4 clock regions h / l / t / b, each its own CTS root "
                          "(PL-KIT form); all 41 cross-region nets landed (D 8, E = K = 3, +4 edges; 8,951 landing flops, 0 "
                          "pads), landing halves fenced beside source / reader; 1-bit regional reset runs (depth 6). TW2-PSLICE2 real7 10-19: "
                          "lp.py reader_per_inst + share_rings -> 27 rings (one per net and source region) read by 90 per-leaf "
                          "read halves (6,399 landing flops), every read half + its slot-mux cone fenced on its leaf's cfg face "
                          "(same offsets / D / E / K). The head's "
                          "status inputs (l_fault / l_valid) are read 8 edges after its own time (lp.py lag_pins). Compiler: "
                          "leaves +4 edges, reset release +6, leaf faults reach the fault port +4 later relative to "
                          "command/done than in the flat cluster.",
        job=dict(owner="Claude:PL-PSLICE", branch="claude/pl-pslice-1018", tag="lp3",
                 purpose="landed per-quarter SU programme cluster pslice_c5 (pgp_<q>)",
                 views_to=f"physical/ref_tile/{NAME}/views", record_to=f"results/rtl/ref_tile/{NAME}",
                 extra_paths=["tools/landed_parent", "rtl/common/landed_parent", "rtl/lib",
                              "rtl/hbm_accel/generic/adapters/static_su/programme",
                              "physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2",
                              "results/arch/landed_parent_1018/pslice_c5"],
                 benches=benches))
    if diag:
        # the L instances bind the S master in the diag RTL copy (same ports; module name unchanged so the SDC applies)
        src = ROOT / LDIR / "ot_hbm_su_programme_pslice_c5_lp.sv"
        dg = ROOT / LDIR / "diag" / "ot_hbm_su_programme_pslice_c5_lp.sv"
        dg.parent.mkdir(exist_ok=True)
        dg.write_text("// DIAG COPY (pslice_c5_kit.py --diag): L instances bound to the S master; never submitted / bound\n" +
                      src.read_text().replace("ot_hbm_su_programme_pgcol_l ", "ot_hbm_su_programme_pgcol_s "))
        spec["sources"][0] = f"{LDIR}/diag/ot_hbm_su_programme_pslice_c5_lp.sv"
        spec.update(name=name, diagnostic=True)
        spec["job"].update(tag="diag1", submit=False, views_to=f"physical/ref_tile/{name}/views",
                           record_to=f"results/rtl/ref_tile/{name}",
                           hold_merge="PL-PSLICE diagnostic: L slots hold the S view stand-in (pgcol_l not closed)")
    out = ROOT / f"tools/ref_tile/specs_hbm_su/{name}.json"
    out.write_text(json.dumps(spec, indent=1) + "\n")
    print(out, tcl, len(lines) - 1, "pins")


if __name__ == "__main__":
    main()
