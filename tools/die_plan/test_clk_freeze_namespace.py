"""Clock-network census resolves global STA APIs inside namespaced ECO hooks."""
from pathlib import Path
import subprocess

TCL=Path(__file__).with_name('clk_freeze.tcl')


def test_namespace_clock_census_and_fail_closed_lifecycle():
    script=r'''
namespace eval ::ord {proc get_db_block {} {return ::block}}
proc ::block {method args} {
  if {$method eq "getNets"} {return $::dbnets}
  if {$method eq "findNet"} {return [expr {[lindex $args 0] eq "clk" ? "::x_odb__dbNet0" : "NULL"}]}
  error "unexpected block method $method"
}
proc ::x_odb__dbNet0 {method args} {
  if {$method eq "getName"} {return clk}
  if {$method eq "getSigType"} {return $::sigtype}
  error "unexpected net method $method"
}
proc ::all_clocks {} {return $::clocks}
proc ::all_registers {args} {return $::sinks}
proc ::get_full_name {net} {return $net}
namespace eval ::sta {
  proc all_clocks {} {return {}}
  proc find_all_clk_nets {} {
    incr ::calls
    if {$::mode eq "error"} {error "census failed"}
    if {$::mode eq "empty"} {return {}}
    if {$::mode eq "missing_db"} {return {absent}}
    return {::x_odb__dbNet0}
  }
}
set ::calls 0;set ::mode normal;set ::clocks {clk vclk};set ::sinks {ff/CLK};set ::dbnets {};set ::sigtype SIGNAL
namespace eval ::ot_mm [list source $::env(CLK_FREEZE)]
# The original relative info-command lookup misses the existing global helper.
namespace eval ::ot_mm {
  if {[llength [info commands sta::find_all_clk_nets]]} {error "baseline namespace miss was not reproduced"}
}
if {[::ot_mm::ot_clk_dbnets] ne {::x_odb__dbNet0} || $::calls!=1} {error "global census skipped in actual hook namespace"}
foreach mode {error empty missing_db} {
  set ::mode $mode
  if {![catch {::ot_mm::ot_clk_dbnets} msg] || ![string match "OT_CLK_FREEZE FAIL:*" $msg]} {error "negative census escaped: $mode"}
}
set ::mode empty;set ::dbnets {::x_odb__dbNet0};set ::sigtype CLOCK
if {![catch {::ot_mm::ot_clk_dbnets} msg]} {error "partial database CLOCK tag hid failed STA census"}
set ::dbnets {};set ::clocks {}
if {![catch {::ot_mm::ot_clk_dbnets} msg] || ![string match "*SDC/source ordering*" $msg]} {error "missing SDC/source ordering escaped"}
set ::sinks {}
if {[llength [::ot_mm::ot_clk_dbnets]]} {error "clockless combinational block should remain empty"}
set ::clocks {clk};set ::sinks {ff/CLK};set ::mode normal
rename ::sta::find_all_clk_nets ::sta::saved_find
if {![catch {::ot_mm::ot_clk_dbnets} msg] || ![string match "*enumeration is unavailable*" $msg]} {error "missing global helper escaped"}
puts "CLK_NAMESPACE_CENSUS PASS"
'''
    import os
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,
                          env=dict(os.environ,CLK_FREEZE=str(TCL)))
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.strip()=='CLK_NAMESPACE_CENSUS PASS',result.stdout+result.stderr
    assert not result.stderr,result.stderr
