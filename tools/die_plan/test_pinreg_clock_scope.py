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
