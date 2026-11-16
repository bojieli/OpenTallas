"""Forwarded-ring writer clocks must not contaminate the local insertion census."""
from pathlib import Path
import subprocess

SRC = Path(__file__).with_name("pinreg_measure.tcl")
STUBS = r"""
proc get_full_name {p} {return $p}
proc get_clocks {args} {return [lindex $args end]}
proc all_registers {args} {
  set n [lsearch -exact $args -clock]
  if {$n < 0} {return {local/CK writer/CK generated/CK}}
  switch [lindex $args [expr {$n+1}]] {
    clk {return {local/CK generated/CK}}
    fclk_in {return {writer/CK}}
    default {return {}}
  }
}
proc all_inputs {args} {return {data}}
proc all_outputs {} {return {out}}
proc get_fanout {args} {return {local/D writer/D generated/D}}
proc get_fanin {args} {return {local/Q writer/Q generated/Q}}
"""

def run(body):
    p = subprocess.run(["tclsh"], input=STUBS + "\nsource {" + str(SRC) + "}\n" + body,
                       capture_output=True, text=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return p.stdout.strip()

def test_forwarded_writer_is_outside_local_clock_budget():
    assert run("puts [dict keys [ot_pinreg_set]]") == "generated local"

def test_forwarded_writer_can_be_measured_against_own_clock():
    assert run("puts [dict keys [ot_pinreg_set_for_clock fclk_in]]") == "writer"

def test_missing_clock_fails_closed():
    assert run('rename get_clocks old_get_clocks\nproc get_clocks {args} {return {}}\nputs [catch {ot_pinreg_set} message]\nputs $message') == "1\nOT_PINREG: missing unique clock clk"

def test_generated_descendants_use_clock_family_ownership():
    assert run("proc ot_cf_pins {clock} {return [list {local/CK generated/CK} {}]}\nputs [dict keys [ot_pinreg_set]]") == "generated local"

def test_single_clock_census_is_unchanged():
    assert run("rename all_registers old_all_registers\nproc all_registers {args} {return {local/CK writer/CK generated/CK}}\nputs [dict keys [ot_pinreg_set]]") == "generated local writer"


def run_arr(wave, arrival, per=833.0):
    """ot_pinreg_arr fallback (no ot_cf_wire): clock `clk` with waveform `wave`, register CK arrival_max_rise `arrival`"""
    return run(f"""namespace eval sta {{ proc time_sta_ui {{t}} {{return $t}} }}
proc clk {{args}} {{ if {{[lindex $args 0] eq "waveform"}} {{return {{{wave}}}}} }}
proc get_property {{obj prop}} {{ if {{$prop eq "arrival_max_rise"}} {{return {arrival}}} ; if {{$prop eq "period"}} {{return {per}}} }}
puts [ot_pinreg_arr reg/CK clk]""")


def test_fallback_arrival_is_not_folded_by_magnitude():
    # KIT-OPS-5 (FABLE-PD-S81C-0730): real insertion 484.2 on a {0 T/2} clock was read as 67.7 (484.2 - 416.5)
    assert float(run_arr("0 416.5", 484.2)) == 484.2
    assert float(run_arr("0 416.5", 504.3)) == 504.3
    assert float(run_arr("0 416.5", 389.7)) == 389.7


def test_fallback_arrival_subtracts_the_waveform_offset_only():
    assert float(run_arr("416.5 833", 900.5)) == 484.0          # a clock whose first rise is at T/2
