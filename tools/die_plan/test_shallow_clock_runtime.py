"""Tcl scope, free-row guard, local-only CTS and immutable-data controls."""
from pathlib import Path
import shutil
import subprocess
import pytest

RUNTIME=Path(__file__).resolve().parents[2]/'physical/common_flow/shallow_clock.tcl'


def run(body):
    if not shutil.which('tclsh'):pytest.skip('tclsh unavailable')
    text=f'proc loader {{}} {{ source {{{RUNTIME}}} }}\nloader\n'+body
    p=subprocess.run(['tclsh'],input=text,text=True,capture_output=True)
    assert not p.stderr,p.stderr
    return p.stdout


def test_default_off_and_proc_scope():
    s=run('puts "ACTIVE $::ot_dtsh::active CTS=[info commands ::clock_tree_synthesis]"\n')
    assert 'ACTIVE 0 CTS=\n' in s


def test_site_guard_rejects_overlap_and_nonrow():
    s=run('''
proc master {m} {if {$m eq "getWidth"} {return 1620};return 270}
set ::ot_dtsh::master master
set ::ot_dtsh::rows [dict create 4320 {{4320 54 100 270 R0}}]
set ::ot_dtsh::ymin 4320;set ::ot_dtsh::rowheight 270
set ::ot_dtsh::occupied [dict create 0 {{data_ff 4320 4320 5940 4590}}]
puts "FREE [catch {::ot_dtsh::check_site 6480 4320 R0}]"
puts "OCC [catch {::ot_dtsh::check_site 4320 4320 R0} msg] $msg"
puts "GRID [catch {::ot_dtsh::check_site 6481 4320 R0} msg] $msg"
puts "ORIENT [catch {::ot_dtsh::check_site 6480 4320 MX} msg] $msg"
''')
    assert 'FREE 0' in s
    assert 'OCC 1 OT_DTSH planned node overlaps data_ff' in s
    assert 'GRID 1 OT_DTSH planned node is not row/site/orientation legal' in s
    assert 'ORIENT 1 OT_DTSH planned node is not row/site/orientation legal' in s


def test_cts_only_local_nets_and_scoped_repair():
    s=run('''
rename ::ot_dtsh::audit ::ot_dtsh::audit_real
proc ::ot_dtsh::audit {} {incr ::audits}
rename ::ot_dtsh::bind_new_pg ::ot_dtsh::bind_new_pg_real
proc ::ot_dtsh::bind_new_pg {} {incr ::pgs}
set audits 0;set pgs 0;set repairs {}
proc ::ot_dtsh::cts_orig {args} {set ::got $args;return ORIGINAL_RESULT}
proc n0 {m} {return ot_dtap_net_0}
proc n1 {m} {return ot_dtap_net_1}
proc blk {m name} {if {$name eq "ot_dtap_net_0"} {return n0};return n1}
set ::ot_dtsh::blk blk
set ::ot_dtsh::active 1
set ::ot_dtsh::taps [dict create ot_dtap_0 [dict create output n0] ot_dtap_1 [dict create output n1]]
proc estimate_parasitics {args} {}
namespace eval est {proc check_parasitics {} {}}
namespace eval sta {proc db_net_to_sta {n} {return $n}}
namespace eval rsz {
 proc check_max_wire_length {args} {return 123}
 proc repair_net_cmd {args} {lappend ::repairs $args}
}
puts "RESULT [::ot_dtsh::cts -root_buf BUF -clk_nets forbidden_root -repair_clock_nets -balance_levels]"
puts "ARGS $got"
puts "AUDIT $audits PG $pgs REPAIRS $repairs"
''')
    assert 'RESULT ORIGINAL_RESULT' in s
    assert 'ARGS -root_buf BUF -balance_levels -clk_nets {ot_dtap_net_0 ot_dtap_net_1}' in s
    assert 'forbidden_root' not in s and '-repair_clock_nets' not in s
    assert 'AUDIT 2 PG 2 REPAIRS {n0 123 0 0} {n1 123 0 0}' in s


def test_moved_data_cell_mutant_fails_audit():
    s=run('''
set moved 0
proc rect {m} {global moved;switch $m {xMin {return $moved} yMin {return 0} xMax {return 54} yMax {return 270}}}
proc mast {m} {return DFFHQNx1_ASAP7_75t_R}
proc inst {m} {switch $m {getBBox {return rect} getOrient {return R0} getMaster {return mast}}}
proc blk {m name} {return inst}
proc root {m} {return {}}
set ::ot_dtsh::blk blk;set ::ot_dtsh::root root
set ::ot_dtsh::original [dict create data_ff {{0 0 54 270} R0 DFFHQNx1_ASAP7_75t_R}]
puts "BASE [catch {::ot_dtsh::audit} msg] $msg"
set moved 1
puts "MUTANT [catch {::ot_dtsh::audit} msg] $msg"
''')
    assert 'BASE 0' in s
    assert 'MUTANT 1 OT_DTSH moved/resized existing cell data_ff' in s


def test_ndr_explicit_optin_and_trunk_only():
    s=run('''
unset -nocomplain ::env(OT_DTSH_NDR)
puts "OFF [catch {::ot_dtsh::trunk_ndr}]"
namespace eval ord {proc get_db {} {return db}}
proc db {m} {return tech}
set created 0
proc tech {m name} {global created;if {$m eq "findLayer"} {return layer};if {$created} {return ndr};return NULL}
proc layer {m} {if {$m eq "getWidth"} {return 20};return 30}
proc blk {m} {return 1000}
proc root {m v} {lappend ::assigned [list root $m $v]}
proc planned {m v} {lappend ::assigned [list planned $m $v]}
proc create_ndr {args} {set ::created 1;set ::ndrargs $args}
set ::ot_dtsh::blk blk;set ::ot_dtsh::root root
set ::ot_dtsh::nodes [dict create node0 [dict create net planned]]
set ::env(OT_DTSH_NDR) 4w
::ot_dtsh::trunk_ndr
puts "NDRARGS $ndrargs"
puts "ASSIGNED $assigned"
set ::env(OT_DTSH_NDR) invalid
puts "BAD [catch {::ot_dtsh::trunk_ndr} msg] $msg"
''')
    assert 'OFF 0' in s
    assert '-width {M2 0.08 M3 0.08 M4 0.08 M5 0.08 M6 0.08 M7 0.08}' in s
    assert '-spacing {M2 0.06 M3 0.06 M4 0.06 M5 0.06 M6 0.06 M7 0.06}' in s
    assert 'ASSIGNED {root setNonDefaultRule ndr} {planned setNonDefaultRule ndr}' in s
    assert 'BAD 1 OT_DTSH unknown NDR option invalid' in s


def test_freeze_requires_complete_wiring_then_protects_all():
    s=run('''
set frozen {}
proc inst {m value} {lappend ::frozen [list inst $m $value]}
proc net {m value} {lappend ::frozen [list net $m $value]}
proc root {m value} {lappend ::frozen [list root $m $value]}
proc tap0 {m value} {lappend ::frozen [list tap0 $m $value]}
proc tap1 {m value} {lappend ::frozen [list tap1 $m $value]}
proc blk {m name} {if {$name eq "ot_dtap_0"} {return tap0};return tap1}
set ::ot_dtsh::blk blk;set ::ot_dtsh::root root
set ::ot_dtsh::nodes [dict create n0 [dict create inst inst net net]]
set ::ot_dtsh::taps [dict create ot_dtap_0 {} ot_dtap_1 {}]
set ::ot_dtsh::leaves [dict create ot_dtap_0 net]
puts "EARLY [catch {::ot_dtsh::freeze} msg] $msg FLAGS=$frozen"
dict set ::ot_dtsh::leaves ot_dtap_1 net
::ot_dtsh::freeze
puts "FROZEN $frozen"
''')
    assert 'EARLY 1 OT_DTSH cannot freeze before all tap inputs are wired FLAGS=\n' in s
    assert 'FROZEN {inst setDoNotTouch true} {net setDoNotTouch true} {tap0 setDoNotTouch true} {tap1 setDoNotTouch true} {root setDoNotTouch true}' in s
    source=RUNTIME.read_text()
    node=source.split('proc ::ot_dtsh::node {',1)[1].split('proc ::ot_dtsh::freeze',1)[0]
    assert 'setDoNotTouch' not in node
    assert source.index('uplevel #0 [list source $apply]') < source.index('\n  freeze\n')
