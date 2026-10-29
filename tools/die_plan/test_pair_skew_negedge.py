"""pair_skew.tcl active-edge CK arrivals (FLOW-CLOCK-R4 10-29, DIE-S81-28 H0 verify 14.75/7.79 ps).

A negedge register (yosys $_DFF_N_, Liberty Clk-to-Q arc from CK fall) launches on the clock's falling edge, so its
credited path uses the FALL CK arrival and the fall source insertion.  The raw/verify column used to read the RISE
arrival, so every N->P pair showed the clock tree's rise/fall delay difference as a path/arrival mismatch.
Stubbed OpenSTA in plain tclsh; P->P behaviour is pinned by test_pair_skew_targets GOLDEN (byte-identical to main)."""
from pathlib import Path
import subprocess

SRC = Path(__file__).with_name("pair_skew.tcl")

# report_edges text as printed by the asap7lock OpenROAD for ASAP7 DFFLQNx1 (negedge) / DFFHQNx1 (posedge) CLK
EDGES_N = "CLK -> QN Reg Clk to Q\n  v -> ^ 40.21:41.02\n  v -> v 38.10:39.33\nCLK -> D hold\n  v -> ^ 1.0:1.0\n"
EDGES_P = "CLK -> QN Reg Clk to Q\n  ^ -> ^ 40.21:41.02\n  ^ -> v 38.10:39.33\nCLK -> D setup\n  ^ -> ^ 1.0:1.0\n"

STUBS = r'''
set ::ot_ps_lib_only 1
source @SOURCE@
namespace eval sta {
  proc worst_slack_cmd {args} {}
  proc crpr_enabled {} { return 1 }
  proc crpr_mode {} { return same_pin }
  proc redirect_string_begin {} { set ::redir "" }
  proc redirect_string_end {} { return $::redir }
}
set ::edges_n "@EN@"
set ::edges_p "@EP@"
proc report_edges {args} { set p [lindex $args 1]; set ::redir [expr {[string match n* $p] ? $::edges_n : $::edges_p}] }
proc get_cells {args} { return [ot_ps_inst [lindex $args end]] }
proc get_full_name {x} { return $x }
'''


def tcl(body):
    script = (STUBS + body).replace("@SOURCE@", str(SRC)).replace("@EN@", EDGES_N).replace("@EP@", EDGES_P)
    p = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return p.stdout


def test_active_edge_from_clk_to_q_arc():
    out = tcl(r'''
proc get_property {obj prop} {
  if {$prop eq "ref_name"} { return [expr {[string match n* $obj] ? "DFFLQNx1" : "DFFHQNx1"}] }
  if {$prop eq "lib_pin_name"} { return CLK }
  error $prop
}
puts [list [ot_ps_edge n0/CLK] [ot_ps_edge a/CLK] [ot_ps_edge n1/CLK] [dict size $::ot_ps_edge_cache]]
# no Liberty answer (stub without report_edges / ref_name): previous rise read
rename get_property {}
proc get_property {obj prop} { error $prop }
puts [ot_ps_edge x/CLK]
''')
    assert out.split("\n")[:2] == ["fall rise fall 2", "rise"]


def test_fall_tag_arrival_removes_falling_waveform_edge():
    # rf fall -> path_iterator fall, "v" tag, minus waveform[1] (416.5 ps); rise keeps waveform[0]
    out = tcl(r'''
proc clk {m} { return {0 4.165e-10} }
proc pin {m} { return vertex }
proc vertex {args} { set ::rf [lindex $args 1]; set ::i 0; return it }
proc it {m} { switch $m { has_next { return [expr {$::i < 1}] } next { incr ::i; return pa_$::rf } finish { return } } }
proc pa_rise {m} { if {$m eq "tag"} { return {1 tt ^max clk ^ (clock prop) clk_src} }; return 3.0e-10 }
proc pa_fall {m} { if {$m eq "tag"} { return {1 tt vmax clk v (clock prop) clk_src} }; return 7.3e-10 }
set ::ot_ps_method tag
puts [format "%.3f %.3f %.3f" [ot_ps_ckarr pin clk max] [ot_ps_ckarr pin clk max rise] [ot_ps_ckarr pin clk max fall]]
''')
    assert out.split()[:3] == ["300.000", "300.000", "313.500"]


FIXTURE = r'''
proc get_property {obj prop} {
  switch -- $prop {
    clocks { return clk } sources { return src } lib_pin_name { return CLK }
    ref_name { return [expr {[string match n* $obj] ? "DFFLQNx1" : "DFFHQNx1"}] }
  }
  error $prop
}
# CK arrivals {late early} per transition (ps): the tree's fall delay is 12/11 ps above rise
set ::arr [dict create a/CLK,rise {300 290} b/CLK,rise {305 295} n/CLK,rise {300 290} n/CLK,fall {312 301} \
                       src,rise {0 0} src,fall {0 0}]
set ::fanin [dict create a/D {n/CLK} b/D {a/CLK n/CLK} n/D {b/CLK}]
proc all_registers {which} {
  switch -- $which { -clock_pins { return {a/CLK b/CLK n/CLK} } -data_pins { return {a/D b/D n/D} } default { return {} } }
}
proc ot_ps_ckarr {pin clk which {rf rise}} { return [lindex [dict get $::arr $pin,$rf] [expr {$which eq "max" ? 0 : 1}]] }
proc get_fanin {args} { return [dict get $::fanin [lindex $args 1]] }
# the timing path (truth): a negedge register launches/captures on its FALL CK arrival; 5 ps CPPR
proc truth {pin} { return [dict get $::arr $pin,[expr {[string match n* $pin] ? "fall" : "rise"}]] }
proc ot_ps_path {l dn dly} {
  set L [truth [lindex [dict get $::ot_ps_R $l] 0]]
  set C [truth [lindex [dict get $::ot_ps_R [ot_ps_inst $dn]] 0]]
  if {$dly eq "max"} { return [list [expr {[lindex $C 1] + 5.0 - [lindex $L 0]}] 5.0] }
  return [list [expr {[lindex $C 0] - 5.0 - [lindex $L 1]}] 5.0]
}
ot_ps_write [ot_ps_measure 5000] @OUT@ TT
'''


def header(text):
    return dict(l.split("\t")[1:3] for l in text.splitlines() if l.startswith("H\t"))


def test_negedge_launch_pairs_cross_check_agree(tmp_path):
    out = tmp_path / "ps.tsv"
    tcl(FIXTURE.replace("@OUT@", str(out)))
    t = out.read_text()
    h = header(t)
    # rise reads of n/CLK (previous script): verify 12.000 setup / 11.000 hold = the tree's fall-rise difference
    assert h["max_verify"] == "0.000" and h["min_verify"] == "0.000", t
    rows = {tuple(l.split("\t")[1:4]): l.split("\t")[4:] for l in t.splitlines() if l.startswith("P\t")}
    # setup N->P n->a: Cmin(a) + crpr - Lmax(n, fall) = 290 + 5 - 312 = -17, raw 312 - 290 = 22 (worst; next raw 17 stops)
    assert rows == {("max", "n", "a"): ["-17.00", "5.00", "22.00"],
                    # hold P->N b->n: Cmax(n, fall) - crpr - Lmin(b) = 312 - 5 - 295 = 12, raw 17
                    ("min", "b", "n"): ["12.00", "5.00", "17.00"],
                    # hold P->P a->b: 305 - 5 - 290 = 10, raw 15 (searched, raw 15 > worst 12)
                    ("min", "a", "b"): ["10.00", "5.00", "15.00"]}, t
    assert h["max_worst"] == "17.0" and (h["max_launch"], h["max_capture"]) == ("n", "a")
    assert h["min_worst"] == "12.0" and (h["min_launch"], h["min_capture"]) == ("b", "n")
    assert h["regs"] == "3" and h["pairs"] == "4" and h["no_clock_arrival"] == "0"


def test_fall_launch_restores_fall_source_insertion():
    # ot_ps_path on a fall-edge launch adds the source's FALL insertion (key "clk fall"), rise launch the rise one
    out = tcl(r'''
proc get_pins {args} { return pin }
proc get_property {obj prop} { return 833.0 }
proc find_timing_paths {args} { return pe }
proc clkedge {m} { return 0 }
proc tp {m} { return 2e-10 }
proc pe {m} {
  switch $m { is_check { return 1 } is_latch_check { return 0 } check_role { return setup } target_clk_path { return tp }
              target_clk { return clk } target_clk_edge { return clkedge } clk_skew { return -5e-11 }
              data_required_time { return 1.023e-9 } margin { return 2e-11 } }
}
set ::ot_ps_insertion [dict create clk {10 10} {clk fall} {-30 -30}]
set ::ot_ps_R [dict create r [list r/CLK clk 250 200 rise] n [list n/CLK clk 250 200 fall] o [list o/CLK clk 250 200]]
puts [list [lindex [ot_ps_path r c/D max] 0] [lindex [ot_ps_path n c/D max] 0] [lindex [ot_ps_path o c/D max] 0]]
''')
    r, n, o = (float(x) for x in out.split()[:3])
    # s = -(clk_skew + ins): rise 50 - 10 = 40, fall 50 + 30 = 80, legacy 4-field entry = rise
    assert (round(r, 6), round(n, 6), round(o, 6)) == (40.0, 80.0, 40.0)


def test_fall_edge_capture_crpr_has_no_half_period():
    # P->N pair: the capture register samples on the falling edge (416.5 ps).  data_required and the target clock path
    # arrival both carry that edge (hold: one period earlier), so CPPR = their difference mod period; the old
    # "- target_clk_edge time" term put T/2 into it (H0 TT: crpr -414.95, skew +833, verify 416.5).
    out = tcl(r'''
proc get_pins {args} { return pin }
proc get_property {obj prop} { return 833.0 }
proc find_timing_paths {args} { return pe }
proc fall_edge {m} { return 4.165e-10 }
# target clock path arrival = fall edge 416.5 + capture insertion 300 ps
proc tp {m} { return 7.165e-10 }
proc pe {m} {
  switch $m { is_check { return 1 } is_latch_check { return 0 } check_role { return $::role } target_clk_path { return tp }
              target_clk { return clk } target_clk_edge { return fall_edge } clk_skew { return $::sk }
              data_required_time { return $::req } margin { return 1e-11 } }
}
set ::ot_ps_insertion [dict create clk {0 0}]
set ::ot_ps_R [dict create r [list r/CLK clk 250 240 rise]]
# hold: launch rise 0 + 240, capture edge 416.5 - 833 (+300), CPPR 2: required = tarr - 833 + margin - crpr
set ::role hold; set ::sk [expr {(240 - 300 - 2) * 1e-12}]; set ::req [expr {(716.5 - 833 + 10 - 2) * 1e-12}]
puts [ot_ps_path r n/D min]
# setup: capture edge 416.5 (+300), CPPR 2: required = tarr - margin + crpr
set ::role setup; set ::sk [expr {(250 - 300 - 2) * 1e-12}]; set ::req [expr {(716.5 - 10 + 2) * 1e-12}]
puts [ot_ps_path r n/D max]
''')
    (hs, hc), (ss, sc) = [[round(float(x), 6) for x in l.split()] for l in out.split("\n")[:2]]
    # hold h = Cmax - crpr - Lmin = 300 - 2 - 240 = 58 ; setup s = Cmin + crpr - Lmax = 300 + 2 - 250 = 52
    assert (hs, hc) == (58.0, 2.0) and (ss, sc) == (52.0, 2.0), out
