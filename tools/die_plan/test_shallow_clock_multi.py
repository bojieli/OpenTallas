"""Independent root ownership, shared CTS controller and global plan identities."""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import pytest

FLOW = Path(__file__).resolve().parents[2] / 'physical/common_flow'
SPEC = importlib.util.spec_from_file_location('shallow_multi', FLOW/'shallow_clock_multi.py')
MULTI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MULTI)


def tcl(body):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    p = subprocess.run(['tclsh'], input=f'source {{{FLOW / "shallow_clock_multi.tcl"}}}\n'+body,
                       text=True, capture_output=True)
    assert not p.stderr, p.stderr
    return p.stdout


def test_offsets_all_node_references_but_not_tap_or_parentport_identity():
    p = dict(nodes=[dict(name='ot_dtsh_0', parent=None), dict(name='ot_dtsh_1', parent='ot_dtsh_0')],
             edges=[['ot_dtsh_0','ot_dtsh_1'], ['ot_dtsh_1','ot_dtap_9']],
             legs=[dict(bufs=['ot_dtsh_0','ot_dtsh_1'])], best=dict(nodes=[['ot_dtsh_1',[1,2],'R0']]),
             root_name='clk_t1',taps=[dict(name='ot_dtap_9')])
    q, nxt = MULTI.offset_nodes(p, 37)
    assert nxt == 39 and q['nodes'][1]['parent'] == 'ot_dtsh_37'
    assert q['edges'][1] == ['ot_dtsh_38','ot_dtap_9']
    assert q['legs'][0]['bufs'] == ['ot_dtsh_37','ot_dtsh_38']
    assert q['best']['nodes'][0][0] == 'ot_dtsh_38'
    assert q['root_name'] == 'clk_t1' and p['nodes'][0]['name'] == 'ot_dtsh_0'


def test_loading_is_off_and_does_not_replace_single_root_controller():
    s=tcl('puts "OFF $::ot_dtsh_multi::active SINGLE $::ot_dtsh::active CTS=[info commands ::clock_tree_synthesis]"\n')
    assert 'OFF 0 SINGLE 0 CTS=\n' in s


def test_cloned_contexts_retain_separate_roots_and_globally_named_apply(tmp_path):
    apply = tmp_path/'apply.tcl'
    apply.write_text('ot_dtsh::node ot_dtsh_37 1 2 R0 @root\n')
    s=tcl('''
::ot_dtsh_multi::clone_context ::ot_dtsh_multi::r0
::ot_dtsh_multi::clone_context ::ot_dtsh_multi::r1
set ::ot_dtsh_multi::r0::root root0
set ::ot_dtsh_multi::r1::root root1
proc ::ot_dtsh_multi::r1::node {name args} {set ::record [list $::ot_dtsh_multi::r1::root $name $args]}
::ot_dtsh_multi::r1::source_apply {%s}
puts "ROOTS $::ot_dtsh_multi::r0::root $::ot_dtsh_multi::r1::root APPLY=$record"
''' % apply)
    assert 'ROOTS root0 root1 APPLY=root1 ot_dtsh_37 {1 2 R0 @root}' in s


def test_one_global_cts_call_covers_all_four_roots_and_repairs_local_only():
    s=tcl('''
set ::audits 0; set ::calls 0; set ::repairs {};set ::pgs 0
rename ::ot_dtsh_multi::audit ::ot_dtsh_multi::real_audit
proc ::ot_dtsh_multi::audit {} {incr ::audits}
proc ::ot_dtsh_multi::cts_orig {args} {incr ::calls;set ::args $args;return GLOBAL_RESULT}
set ::ot_dtsh_multi::active 1
set ::ot_dtsh_multi::block blk
for {set i 0} {$i<4} {incr i} {
 set ns ::ot_dtsh_multi::r$i; namespace eval $ns {}
 proc ${ns}::bind_new_pg {} {incr ::pgs}
 proc net$i {m} [format {return local%d} $i]
 set ${ns}::taps [dict create ot_dtap_$i [dict create output net$i]]
 dict set ::ot_dtsh_multi::contexts clk$i [dict create namespace $ns]
}
proc blk {m name} {return net[string range $name 5 end]}
proc estimate_parasitics {args} {}
namespace eval est {proc check_parasitics {} {}}
namespace eval sta {proc db_net_to_sta {n} {return $n}}
namespace eval rsz {
 proc check_max_wire_length {args} {return 123}
 proc repair_net_cmd {args} {lappend ::repairs $args}
}
puts "RESULT [::ot_dtsh_multi::cts -root_buf BUF -clk_nets forbidden_root -repair_clock_nets -balance_levels]"
puts "CALLS $calls ARGS $args AUDITS $audits PGS $pgs REPAIRS $repairs"
''')
    assert 'RESULT GLOBAL_RESULT' in s and 'CALLS 1' in s
    assert '-clk_nets {local0 local1 local2 local3}' in s
    assert 'forbidden_root' not in s and '-repair_clock_nets' not in s
    assert 'AUDITS 2 PGS 8' in s
    assert 'REPAIRS {net0 123 0 0} {net1 123 0 0} {net2 123 0 0} {net3 123 0 0}' in s


MOCK = '''
proc all_clocks {} {return ck}
proc get_property {obj prop} {return {clk0 clk1 clk2 clk3}}
proc get_full_name {obj} {return $obj}
set actual_roots {}
set actual_outputs {}
for {set i 0} {$i<4} {incr i} {
 dict set actual_roots $i root$i;dict set actual_outputs $i out$i
 proc root$i {m} [format {if {$m eq "getBTerms"} {return bt%d};if {$m eq "getITerms"} {return ip%d};error "root method $m"} $i $i]
 proc bt$i {m} [format {if {$m eq "getNet"} {return root%d};if {$m eq "getIoType"} {return INPUT};error "bt method $m"} $i]
 proc ip$i {m} [format {if {$m eq "getNet"} {return [dict get $::actual_roots %d]};if {$m eq "isInputSignal"} {return 1};if {$m eq "getInst"} {return inst%d};if {$m eq "getSigType"} {return CLOCK};if {$m eq "getMTerm"} {return mtin};error "ip method $m"} $i $i]
 proc op$i {m} [format {if {$m eq "getNet"} {return [dict get $::actual_outputs %d]};if {$m eq "getSigType"} {return CLOCK};if {$m eq "getMTerm"} {return mtout};error "op method $m"} $i]
 proc inst$i {m} [format {if {$m eq "getName"} {return ot_dtap_%d};if {$m eq "getITerms"} {return {ip%d op%d}};error "inst method $m"} $i $i $i]
 dict set roots clk$i [dict create root_net root$i tap_list [list [list $i 1 2 out$i]]]
}
proc mtin {m} {return INPUT}
proc mtout {m} {return OUTPUT}
proc blk {m name} {
 if {$m eq "findBTerm"} {return bt[string range $name 3 end]}
 if {$m eq "findInst"} {return inst[string range $name 8 end]}
 error "blk method $m"
}
'''


def test_actual_root_membership_and_disjointness_fail_closed():
    s=tcl(MOCK+'''
puts "BASE [catch {::ot_dtsh_multi::validate_roots blk $roots} msg] $msg"
dict set actual_roots 3 root2
puts "CROSS [catch {::ot_dtsh_multi::validate_roots blk $roots} msg] $msg"
dict set actual_roots 3 root3
dict set roots clk3 tap_list {{2 1 2 out2}}
puts "DUP [catch {::ot_dtsh_multi::validate_roots blk $roots} msg] $msg"
''')
    assert 'BASE 0' in s
    assert 'CROSS 1 OT_DTSH_MULTI tap/root or output ownership mismatch ot_dtap_3' in s
    assert 'DUP 1 OT_DTSH_MULTI tap owned by two roots: ot_dtap_2' in s


def test_root_clock_domains_cannot_be_silently_combined():
    s=tcl(MOCK+'''
proc all_clocks {} {return {ck0 ck1}}
proc get_property {obj prop} {if {$obj eq "ck0"} {return {clk0 clk1}};return {clk2 clk3}}
puts "MULTICLOCK [catch {::ot_dtsh_multi::validate_roots blk $roots} msg] $msg"
''')
    assert 'MULTICLOCK 1 OT_DTSH_MULTI roots must belong to the same actual timing clock' in s

def test_global_cts_refuses_second_call():
    s=tcl('''
set ::ot_dtsh_multi::active 1
set ::ot_dtsh_multi::cts_called 1
puts "SECOND [catch {::ot_dtsh_multi::cts} msg] $msg"
''')
    assert 'SECOND 1 OT_DTSH_MULTI global CTS may run only once' in s


def test_occupancy_refresh_keeps_other_roots_but_restores_single_baseline():
    s=tcl('''
namespace eval ::ot_dtsh_multi::r0 {}
set ::ot_dtsh_multi::original BASELINE
set ::ot_dtsh_multi::ff_data FF_BASELINE
proc ::ot_dtsh_multi::r0::capture {} {
 set ::ot_dtsh_multi::r0::occupied other_root_node
 set ::ot_dtsh_multi::r0::original changed_snapshot
 set ::ot_dtsh_multi::r0::ff_data changed_ff
}
::ot_dtsh_multi::refresh_occupancy ::ot_dtsh_multi::r0
puts "STATE $::ot_dtsh_multi::r0::occupied $::ot_dtsh_multi::r0::original $::ot_dtsh_multi::r0::ff_data"
''')
    assert 'STATE other_root_node BASELINE FF_BASELINE' in s


def test_every_root_is_audited_and_root_state_mutant_fails():
    s=tcl(MOCK+'''
set ::audited {}
set ::ot_dtsh_multi::block blk
set ::ot_dtsh_multi::owners [::ot_dtsh_multi::validate_roots blk $roots]
for {set i 0} {$i<4} {incr i} {
 set ns ::ot_dtsh_multi::r$i;namespace eval $ns {}
 set ${ns}::root root$i
 set ${ns}::taps [dict create ot_dtap_$i {}]
 set ${ns}::nodes [dict create ot_dtsh_$i {}]
 proc ${ns}::audit {} [format {lappend ::audited %d} $i]
 dict set ::ot_dtsh_multi::contexts clk$i [dict create namespace $ns root_net root$i]
}
puts "BASE [catch {::ot_dtsh_multi::audit} msg] $msg ROOTS=$audited"
set ::ot_dtsh_multi::r2::root root3
puts "MUTANT [catch {::ot_dtsh_multi::audit} msg] $msg"
''')
    assert 'BASE 0' in s and 'ROOTS=0 1 2 3' in s
    assert 'MUTANT 1 OT_DTSH_MULTI root state overwritten: clk2' in s


def test_globally_duplicated_node_mutant_fails_all_root_audit():
    s=tcl(MOCK+'''
set ::ot_dtsh_multi::block blk
set ::ot_dtsh_multi::owners [::ot_dtsh_multi::validate_roots blk $roots]
for {set i 0} {$i<4} {incr i} {
 set ns ::ot_dtsh_multi::r$i;namespace eval $ns {}
 set ${ns}::root root$i;set ${ns}::taps [dict create ot_dtap_$i {}]
 set ${ns}::nodes [dict create ot_dtsh_0 {}]
 proc ${ns}::audit {} {}
 dict set ::ot_dtsh_multi::contexts clk$i [dict create namespace $ns root_net root$i]
}
puts "COLLISION [catch {::ot_dtsh_multi::audit} msg] $msg"
''')
    assert 'COLLISION 1 OT_DTSH_MULTI planned node identity collision' in s

def test_targets_need_explicit_both_corners_and_exact_membership():
    s=tcl('''
set cfg [dict create sink_targets_ps [dict create ot_dtap_0 [dict create tt 232.5 basis BUDGET]]]
puts "MISSING_FF [catch {::ot_dtsh_multi::validate_targets $cfg {ot_dtap_0}} msg] $msg"
dict set cfg sink_targets_ps ot_dtap_0 ff 185.0
puts "PAIR [catch {::ot_dtsh_multi::validate_targets $cfg {ot_dtap_0}} msg] $msg"
puts "MISSING_MEMBER [catch {::ot_dtsh_multi::validate_targets $cfg {ot_dtap_0 ot_dtap_1}} msg] $msg"
''')
    assert 'MISSING_FF 1 OT_DTSH_MULTI target ot_dtap_0 needs explicit finite positive TT AND FF' in s
    assert 'PAIR 0' in s
    assert 'MISSING_MEMBER 1 OT_DTSH_MULTI target membership' in s


def test_objective_normalization_retains_raw_physical_values_and_basis(tmp_path):
    path=tmp_path/'metric.tsv'
    raw=Path(str(path)+'.raw.tsv')
    raw.write_text('T ot_dtap_0 232.5 185.0\nT ot_dtap_1 250.0 202.5\nB ot_dtsh_37 75.0 62.0\n')
    s=tcl('''
set profiles [dict create ot_dtap_0 [dict create tt 232.5 ff 185.0 basis BUDGET] ot_dtap_1 [dict create tt 250.0 ff 202.5 basis BUDGET]]
::ot_dtsh_multi::normalize_measurement {%s} $profiles clk_t1
puts DONE
''' % path)
    assert 'DONE' in s
    assert raw.read_text().startswith('T ot_dtap_0 232.5 185.0\n')
    assert path.read_text() == 'T ot_dtap_0 250.0 202.5\nT ot_dtap_1 250.0 202.5\nB ot_dtsh_37 75.0 62.0\n'
    report=Path(str(path)+'.targets.tsv').read_text()
    assert '232.5\t185.0\t232.5\t185.0\tBUDGET' in report
    assert 'PROVISIONAL_OBJECTIVE_ONLY' in report


def test_missing_actual_measurement_fails_instead_of_filling_target(tmp_path):
    path=tmp_path/'missing.tsv';Path(str(path)+'.raw.tsv').write_text('B ot_dtsh_0 1 1\n')
    s=tcl('''
set profiles [dict create ot_dtap_0 [dict create tt 232.5 ff 185.0 basis BUDGET]]
puts "MISSING [catch {::ot_dtsh_multi::normalize_measurement {%s} $profiles clk} msg] $msg"
''' % path)
    assert 'MISSING 1 OT_DTSH_MULTI incomplete actual target measurement' in s
    assert not path.exists()

def test_qualified_lowlevel_references_stay_in_own_root_context():
    s=tcl('''
proc ::ot_dtsh::absolute_reader {} {return $::ot_dtsh::root}
set ::ot_dtsh::root GLOBAL_SENTINEL
::ot_dtsh_multi::clone_context ::ot_dtsh_multi::r0
::ot_dtsh_multi::clone_context ::ot_dtsh_multi::r1
set ::ot_dtsh_multi::r0::root root0;set ::ot_dtsh_multi::r1::root root1
puts "READ [::ot_dtsh_multi::r0::absolute_reader] [::ot_dtsh_multi::r1::absolute_reader] GLOBAL=$::ot_dtsh::root"
''')
    assert 'READ root0 root1 GLOBAL=GLOBAL_SENTINEL' in s

def test_phase_geometry_keeps_other_roots_and_removes_only_own_nodes(tmp_path):
    path=tmp_path/'geometry.tsv'
    s=tcl('''
namespace eval ::ot_dtsh_multi::r0 {}
set ::ot_dtsh_multi::r0::nodes [dict create ot_dtsh_0 {}]
proc ::ot_dtsh_multi::r0::export {path} {
 set f [open $path w]
 puts $f "DBU\\t1000"
 puts $f "CELL\\tdata_ff\\t0\\t0\\t1\\t1\\t0"
 puts $f "CELL\\tot_dtsh_0\\t1\\t0\\t2\\t1\\t0"
 puts $f "CELL\\tot_dtsh_7\\t2\\t0\\t3\\t1\\t0"
 close $f
}
::ot_dtsh_multi::refresh_geometry ::ot_dtsh_multi::r0 {%s}
puts DONE
''' % path)
    assert 'DONE' in s
    geometry=path.read_text()
    assert 'data_ff' in geometry and 'ot_dtsh_7' in geometry and 'ot_dtsh_0' not in geometry

def test_new_base_defaults_are_copied_per_root_without_cached_sink_leakage():
    s=tcl('''
set ::ot_dtsh::new_policy [dict create stage auto]
set ::ot_dtsh::sink_pins stale_root_pins
::ot_dtsh_multi::clone_context ::ot_dtsh_multi::r0
::ot_dtsh_multi::clone_context ::ot_dtsh_multi::r1
dict set ::ot_dtsh_multi::r0::new_policy stage explicit
puts "POLICY [dict get $::ot_dtsh_multi::r0::new_policy stage] [dict get $::ot_dtsh_multi::r1::new_policy stage] BASE=[dict get $::ot_dtsh::new_policy stage] CACHE=[info exists ::ot_dtsh_multi::r1::sink_pins]"
''')
    assert 'POLICY explicit auto BASE=auto CACHE=0' in s
