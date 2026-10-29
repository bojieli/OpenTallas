"""pair_skew.tcl target-relative skew (COORD 2026-10-28 21:33 rule 2: arrival minus planned target).

Stubbed OpenSTA fixture (plain tclsh): registers a, b and a hard core 'core' whose clock pin is planned L = 255 ps
early (core_latency.txt).  Path ends follow the CK arrivals with 5 ps CPPR.  Without a target file the TSV must be
byte-identical to the pre-change script (GOLDEN, recorded from origin/main 6a56d58118 pair_skew.tcl)."""
from pathlib import Path
import subprocess

import pytest

SRC = Path(__file__).with_name("pair_skew.tcl")
FIXTURE = r'''
set ::ot_ps_lib_only 1
source @SOURCE@
namespace eval sta {
  proc worst_slack_cmd {args} {}
  proc crpr_enabled {} { return 1 }
  proc crpr_mode {} { return same_pin }
}
# CK arrivals {late early} (ps); src = the clock source port
set ::arr [dict create a/CK {300 290} b/CK {300 290} core/ck {50 45} src {0 0}]
set ::fanin [dict create a/D {b/CK} b/D {core/ck a/CK} core/d {a/CK}]
proc all_registers {which} {
  switch -- $which { -clock_pins { return {a/CK b/CK core/ck} } -data_pins { return {a/D b/D core/d} } default { return {} } }
}
proc get_full_name {x} { return $x }
proc get_property {obj prop} { if {$prop eq "clocks"} { return clk } ; if {$prop eq "sources"} { return src } ; error $prop }
proc ot_ps_ckarr {pin clk which} { return [lindex [dict get $::arr $pin] [expr {$which eq "max" ? 0 : 1}]] }
proc get_fanin {args} { return [dict get $::fanin [lindex $args 1]] }
proc ot_ps_path {l dn dly} {
  set L [dict get $::arr [lindex [dict get $::ot_ps_R $l] 0]]
  set C [dict get $::arr [lindex [dict get $::ot_ps_R [ot_ps_inst $dn]] 0]]
  if {$dly eq "max"} { return [list [expr {[lindex $C 1] + 5.0 - [lindex $L 0]}] 5.0] }
  return [list [expr {[lindex $C 0] - 5.0 - [lindex $L 1]}] 5.0]
}
@TARGETS@
ot_ps_write [ot_ps_measure 5000] @OUT@ TT
'''

GOLDEN = """H\tcorner\tTT
H\tregs\t3
H\tno_clock_arrival\t0
H\tmethod\ttag
H\tdata_pins\t3
H\tpairs\t4
H\tinter_clock\t0
H\tcrpr\t1 same_pin
H\tmax_n\t4
H\tmax_worst\t250.0
H\tmax_bounded\t0
H\tmax_signed\t-250.0
H\tmax_launch\ta
H\tmax_capture\tcore
H\tmax_crpr\t5.0
H\tmax_p99_raw\t255.00
H\tmax_searched\t1
H\tmax_nopath\t0
H\tmax_verify\t0.000
P\tmax\ta\tcore\t-250.00\t5.00\t255.00
H\tmin_n\t4
H\tmin_worst\t250.0
H\tmin_bounded\t0
H\tmin_signed\t250.0
H\tmin_launch\tcore
H\tmin_capture\tb
H\tmin_crpr\t5.0
H\tmin_p99_raw\t255.00
H\tmin_searched\t1
H\tmin_nopath\t0
H\tmin_verify\t0.000
P\tmin\tcore\tb\t250.00\t5.00\t255.00
"""


def run(tmp_path, targets=None, source=SRC):
    out = tmp_path / "ps.tsv"
    load = ""
    if targets is not None:
        tf = tmp_path / "core_latency.txt"
        tf.write_text(targets)
        load = f"ot_ps_load_targets {tf}"
    script = FIXTURE.replace("@SOURCE@", str(source)).replace("@TARGETS@", load).replace("@OUT@", str(out))
    p = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return out.read_text()


def header(text):
    return dict(l.split("\t")[1:3] for l in text.splitlines() if l.startswith("H\t"))


def test_no_target_file_is_byte_identical(tmp_path):
    assert run(tmp_path) == GOLDEN


TARGETS = "# inst pin mean_pin_register_insertion_ps tap (TT; corner/source basis in JSON)\ncore ck 255 grid\nghost ck 10 grid\n"


def test_target_relative_skew_removes_planned_core_earliness(tmp_path):
    t = run(tmp_path, TARGETS)
    # pin-arrival keys keep their meaning and values
    assert t.startswith(GOLDEN.rsplit("P\tmin", 1)[0])
    h = header(t)
    assert h["max_worst"] == "250.0" and h["min_worst"] == "250.0"
    assert h["gate_basis"] == "target_relative" and h["target_pins"] == "1" and h["target_unmatched"] == "1"
    # d = L_capture - L_launch; setup s_t = s + d, hold h_t = h + d
    # setup: core->b s = 290+5-50 = 245, d = -255 -> -10 (damage 10); a->core -250+255 = +5; a->b -5
    assert h["max_tgt_worst"] == "10.0" and h["max_tgt_signed"] == "-10.0"
    assert (h["max_tgt_launch"], h["max_tgt_capture"]) == ("core", "b")
    # hold: a->core h = 50-5-290 = -245, d = +255 -> +10; core->b 250-255 = -5; a->b +5
    assert h["min_tgt_worst"] == "10.0" and h["min_tgt_signed"] == "10.0"
    assert (h["min_tgt_launch"], h["min_tgt_capture"]) == ("a", "core")
    assert h["max_tgt_verify"] == "0.000" and h["min_tgt_verify"] == "0.000"
    assert h["max_tgt_crpr"] == "5.0" and h["max_tgt_bounded"] == "0"
    assert any(l.startswith("PT\tmin\ta\tcore\t10.00\t5.00\t15.00") for l in t.splitlines())


def test_late_core_tap_is_charged(tmp_path):
    # core planned 400 ps early (L = 400) but its pin arrives only ~250 ps before the registers: the core is LATE
    # against its target by ~150 ps, charged as setup damage on core->reg and hold damage on reg->core.
    h = header(run(tmp_path, TARGETS.replace("core ck 255", "core ck 400")))
    # a->core setup s_t = -250 + 400 = 150 (fine); core->b setup 245 - 400 = -155 -> damage 155
    assert h["max_tgt_worst"] == "155.0" and (h["max_tgt_launch"], h["max_tgt_capture"]) == ("core", "b")
    # hold a->core -245 + 400 = 155
    assert h["min_tgt_worst"] == "155.0"


def test_bad_target_file_fails_closed(tmp_path):
    with pytest.raises(AssertionError):
        run(tmp_path, "core ck abc grid\n")
