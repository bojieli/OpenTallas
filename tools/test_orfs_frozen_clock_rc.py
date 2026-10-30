"""Opt-in frozen CLOCK RC runs after native GRT estimation, before consumers."""
import os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'orfs_hold_mm.tcl'
CHECKER=ROOT/'die_plan/clk_geom_diff.py'


def block_file(tmp_path):
    text=SOURCE.read_text();start=text.index('# FROZEN-CLOCK-RC:');end=text.index('# END FROZEN-CLOCK-RC',start)
    (tmp_path/'die_plan').mkdir(exist_ok=True)
    (tmp_path/'die_plan/frozen_clock_rc.tcl').write_text((ROOT/'die_plan/frozen_clock_rc.tcl').read_text())
    p=tmp_path/'helper.tcl';p.write_text(text[start:end]);return p


def run_tcl(tmp_path,setup):
    f=block_file(tmp_path)
    env=dict(os.environ,HELPER=str(f),OUT=str(tmp_path),CHECKER=str(CHECKER))
    p=subprocess.run(['tclsh'],input=setup,text=True,capture_output=True,env=env)
    assert p.returncode==0,p.stdout+p.stderr
    assert not p.stderr,p.stderr
    return p.stdout


def test_default_off_preserves_native_command(tmp_path):
    out=run_tcl(tmp_path,r'''
proc ::estimate_parasitics {args} {return "native:$args"}
set old [info body ::estimate_parasitics]
namespace eval ::ot_mm [list source $::env(HELPER)]
if {[info body ::estimate_parasitics] ne $old || [info commands ::ot_mm_frozen_native_estimate] ne ""} {error "default wrapper changed native behavior"}
if {[estimate_parasitics -global_routing] ne "native:-global_routing"} {error "native result changed"}
puts DEFAULT_OFF_PASS
''')
    assert out.strip()=='DEFAULT_OFF_PASS'


def test_every_global_refresh_precedes_consumer_and_fails_closed(tmp_path):
    out=run_tcl(tmp_path,r'''
set ::log {};set ::changed 0
proc ::ot_mm_sc {} {return tc}
proc ::estimate_parasitics {args} {lappend ::log "native:$args";return 17}
proc ::ot_clk_freeze_assert {tag} {lappend ::log freeze_assert}
proc ::ot_clk_dump {path tag names} {
 lappend ::log graph_dump
 set x $::baseline
 if {$::changed} {set x [string map {BUF_A BUF_B} $x]}
 set f [open $path w];puts $f $x;close $f
}
proc ::ot_clk_restore_parasitics {maps} {lappend ::log "restore:[dict keys $maps]"}
set ::env(RESULTS_DIR) $::env(OUT)
set ::env(OT_MM_FROZEN_CLOCK_DIFF) $::env(CHECKER)
set ::env(OT_MM_FROZEN_CLOCK_SPEFS) {tc clock_only.spef BC clock_only.spef}
set ::env(OT_MM_FROZEN_CLOCK_IDENTITY) $::env(OUT)/original.tsv
set ::baseline "#CLKDUMP tag pre nets 1 block top\nNET\tclk\tCLOCK\t3\t64\t0:M1 4:10 4:20 9:ff/CLK\nPIN\tclk\tbuf/Y ff/CLK\nINST\tbuf\tBUF_A\t10\t20\tR0\tLOCKED\nINST\tff\tDFF\t20\t20\tR0\tLOCKED"
set f [open $::env(OT_MM_FROZEN_CLOCK_IDENTITY) w];puts $f $::baseline;close $f
set ::ot_mm_stage 4_cts.sdc;set ::ot_clk_frozen 1;set ::ot_clk_frozen_nets clk
namespace eval ::ot_mm [list source $::env(HELPER)]
if {[estimate_parasitics -placement]!=17 || [llength $::log]!=1} {error "placement path changed"}
set ::log {}
foreach phase {first_native ff_reference ss_refresh calibrated_hold restored_hold} {
 if {[estimate_parasitics -global_routing]!=17} {error "native result changed"}
 lappend ::log "consumer:$phase"
}
set expected {}
foreach phase {first_native ff_reference ss_refresh calibrated_hold restored_hold} {
 lappend expected native:-global_routing freeze_assert graph_dump {restore:tc BC} "consumer:$phase"
}
if {$::log ne $expected} {error "restore did not precede every timing consumer: $::log"}
foreach reason {unarmed empty_wire_set wrong_corner changed_graph missing_identity} {
 set ::ot_clk_frozen 1;set ::ot_clk_frozen_nets clk;set ::changed 0
 set ::env(OT_MM_FROZEN_CLOCK_SPEFS) {tc clock_only.spef BC clock_only.spef}
 set saved $::env(OT_MM_FROZEN_CLOCK_IDENTITY)
 if {$reason eq "unarmed"} {set ::ot_clk_frozen 0}
 if {$reason eq "empty_wire_set"} {set ::ot_clk_frozen_nets {}}
 if {$reason eq "wrong_corner"} {set ::env(OT_MM_FROZEN_CLOCK_SPEFS) {TC clock_only.spef BC clock_only.spef}}
 if {$reason eq "changed_graph"} {set ::changed 1}
 if {$reason eq "missing_identity"} {set ::env(OT_MM_FROZEN_CLOCK_IDENTITY) /missing}
 set ::log {}
 if {![catch {estimate_parasitics -global_routing} msg] || ![string match "OT_MM_FROZEN_CLOCK_RC:*" $msg]} {error "precondition escaped: $reason $msg"}
 if {[lsearch -glob $::log restore:*]>=0} {error "unqualified old CLOCK was restored: $reason"}
 set ::env(OT_MM_FROZEN_CLOCK_IDENTITY) $saved
}
puts GLOBAL_LIFECYCLE_PASS
''')
    assert out.strip().endswith('GLOBAL_LIFECYCLE_PASS')


def test_prd_optin_avoids_old_full_spef_and_freeze_reset(tmp_path):
    source=(ROOT/'die_plan/post_route_drv/prd_hook.tcl').read_text()
    entry=source[source.index('set _here '):source.index('global_route -start_incremental')]
    p=tmp_path/'entry.tcl';p.write_text(entry);(tmp_path/'clk_freeze.tcl').write_text('')
    env=dict(os.environ,ENTRY=str(p),OUT=str(tmp_path))
    script=r'''
set ::env(RESULTS_DIR) $::env(OUT);set ::log {}
proc read_spef {path} {lappend ::log full_spef}
proc ot_clk_freeze {} {lappend ::log freeze}
source $::env(ENTRY)
if {$::log ne {full_spef freeze}} {error "legacy PRD behavior changed"}
set ::env(OT_MM_FROZEN_CLOCK_SPEFS) {tc clock_only BC clock_only};set ::log {}
proc ::ot_mm_frozen_clock_rc_restore {tag} {lappend ::log "clock_only:$tag"}
source $::env(ENTRY)
if {$::log ne {clock_only:prd_entry}} {error "old DATA SPEF/freeze baseline replayed in native DATA session"}
puts PRD_ENTRY_PASS
'''
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,env=env)
    assert result.returncode==0 and not result.stderr,result.stdout+result.stderr
    assert result.stdout.strip()=='PRD_ENTRY_PASS'


def test_standalone_gate_estimate_restore_measure_order(tmp_path):
    source=(ROOT/'die_plan/postcts_gate.tcl').read_text()
    block=source[source.index('set ot_pg_frozen_rc '):source.index('\nset per ')]
    gate=tmp_path/'gate.tcl';gate.write_text(block)
    helper=tmp_path/'clk.tcl';helper.write_text('proc ot_clk_freeze {} {lappend ::log freeze}\n')
    guard=tmp_path/'guard.tcl';guard.write_text('proc ::ot_clock_rc_restore_checked {args} {lappend ::log "restore:[lindex $args 0]"}\n')
    script=r'''
set ::log {};set ot_pg_c tt
proc estimate_parasitics {args} {lappend ::log "estimate:$args";if {$::fail} {error bad_native}}
set ::fail 0;set ::env(OT_POSTCTS_GRT) 1
# Legacy behavior still uses its placement fallback.
source $::env(GATE)
if {$::log ne {estimate:-global_routing}} {error legacy}
set ::env(OT_POSTCTS_FROZEN_CLOCK_SPEFS) {actual_native clock_only.spef}
foreach key {IDENTITY HELPER CHECKER GUARD} value [list $::env(HELPER) $::env(HELPER) $::env(HELPER) $::env(GUARD)] {
 set ::env(OT_POSTCTS_FROZEN_CLOCK_$key) $value
}
set ::log {};source $::env(GATE);lappend ::log measure
if {$::log ne {freeze estimate:-global_routing {restore:actual_native clock_only.spef} measure}} {error "bad consumer order $::log"}
set ::fail 1;set ::log {}
if {![catch {source $::env(GATE)}]} {error "native failure swallowed"}
if {$::log ne {freeze estimate:-global_routing}} {error "fallback or restore after failed native estimate"}
set ::fail 0;set ::env(OT_POSTCTS_FROZEN_CLOCK_SPEFS) {tc a BC b}
if {![catch {source $::env(GATE)}]} {error "multi dataset map accepted"}
puts SINGLE_CONSUMER_PASS
'''
    env=dict(os.environ,GATE=str(gate),HELPER=str(helper),GUARD=str(guard))
    result=subprocess.run(['tclsh'],input=script,text=True,capture_output=True,env=env)
    assert result.returncode==0 and not result.stderr,result.stdout+result.stderr
    assert result.stdout.strip()=='SINGLE_CONSUMER_PASS'
