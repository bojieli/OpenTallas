"""Clock placement remains protected during final post-DRV timing legalization."""
import subprocess
from pathlib import Path
import pytest

HOOK = Path(__file__).with_name('core_final_repair.tcl')

@pytest.mark.parametrize('overlap,fail', [(False, False), (True, False), (False, True)])
def test_final_clock_placement_contract(overlap, fail):
    stub = r'''
set ::ot_mm_active 1
proc ot_mm_sc {} {return TC}
proc repair_timing_helper {args} {lappend ::repairs $args}
set ::repairs {}
namespace eval ord {proc get_db_block {} {return block}}
proc block {op} {if {$op eq "getNets"} {return clocknet};if {$op eq "getInsts"} {return {i0 i1}};error $op}
proc clocknet {op} {if {$op eq "getSigType"} {return CLOCK};if {$op eq "getITerms"} {return {t0 t1}};error $op}
proc t0 {op} {return i0};proc t1 {op} {return i1}
set ::status(i0) PLACED;set ::status(i1) PLACED
proc inst {name op args} {
 if {$op eq "getPlacementStatus"} {return $::status($name)}
 if {$op eq "setPlacementStatus"} {set ::status($name) [lindex $args 0];return}
 if {$op eq "getMaster"} {return master}
 if {$op eq "getBBox"} {return b$name}
 error $op
}
proc i0 {op args} {return [inst i0 $op {*}$args]}
proc i1 {op args} {return [inst i1 $op {*}$args]}
proc master {op} {return 0}
proc bi0 {op} {return [dict get {yMin 0 xMin 0 xMax 10} $op]}
proc bi1 {op} {return [dict get [list yMin 0 xMin $::x1 xMax 30] $op]}
proc estimate_parasitics {args} {}
proc global_route {args} {}
proc check_placement {args} {}
proc ot_mm_sync {} {}
proc ot_mm_ws {args} {return -1}
proc ot_mm_unsync {} {}
proc report_check_types {args} {}
proc ot_pg_connect_all {args} {}
proc ot_pg_require_bound {args} {}
proc detailed_placement {args} {
 foreach i {i0 i1} {if {$::status($i) ne $::expected} {error "clock status $i=$::status($i), expected $::expected"}}
 if {$::fail} {error "native DPL failure"}
}
'''
    stub += f'\nset ::x1 {5 if overlap else 20}\nset ::expected {"PLACED" if overlap else "FIRM"}\nset ::fail {int(fail)}\n'
    stub += 'set rc [catch {source {' + str(HOOK) + '}} msg]\n'
    stub += f'if {{$rc != {int(fail)}}} {{error "unexpected hook result $rc/$msg"}}\n'
    stub += '''
foreach i {i0 i1} {if {$::status($i) ne "PLACED"} {error "clock status leaked after DPL"}}
if {[llength $::repairs] != 2 || "-setup" ni [lindex $::repairs 0] || "-hold" ni [lindex $::repairs 1]} {error "missing ordered setup/hold repairs"}
puts CLOCK_CONTRACT_PASS
'''
    script = 'if {[catch {\n' + stub + '\n} message]} {puts stderr $message;exit 1}\n'
    result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert result.returncode == 0 and 'CLOCK_CONTRACT_PASS' in result.stdout, result.stdout + result.stderr
