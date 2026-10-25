from pathlib import Path
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[2]
FAMILY = ROOT / 'physical/common_flow/clock_family.tcl'


def tcl(script):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    full = f'source {{{FAMILY}}}\n' + script
    r = subprocess.run(['tclsh'], input=full, text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stderr
    return r.stdout.strip()


def test_collector_matches_data_outputs_and_excludes_async_fanout():
    out = tcl('''
proc get_full_name {pin} {return $pin}
proc all_registers {what} {
  switch -- $what {
    -clock_pins {return {in/CK body/CK out/CK reset/CK}}
    -async_pins {return {in/R body/R out/R reset/R}}
    -data_pins {return {in/D body/D out/D reset/D reset/R}}
  }
}
proc all_inputs {args} {return {data rst_n}}
proc all_outputs {} {return result}
proc get_fanout {args} {return {in/D body/R reset/R}}
proc get_fanin {args} {return out/Q}
puts [lsort [dict keys [ot_cf_pinregs]]]
''')
    assert out == 'in out'


def test_group_guard_rejects_hidden_spread_late_group_and_missing_measurement():
    out = tcl('''
set good [ot_cf_pinreg_limits [dict create a {244 100} b {257 3}] 250 20]
set spread [ot_cf_pinreg_limits [dict create a {220 1} b {250 1000}] 250 20]
set late [ot_cf_pinreg_limits [dict create a {271 1} b {272 1000}] 250 20]
set missing [ot_cf_pinreg_limits {} 250 20]
puts "[dict get $good verdict] [dict get $spread verdict] [dict get $late verdict] [dict get $missing verdict]"
''')
    assert out == 'PASS FAIL FAIL FAIL'


def test_all_three_consumers_use_canonical_membership():
    for file in ('postcts_gate.tcl', 'pinreg_pad.tcl', 'signoff.py'):
        text = (ROOT / 'tools/die_plan' / file).read_text()
        assert 'ot_cf_pinregs' in text, file
    pad = (ROOT/'tools/die_plan/pinreg_pad.tcl').read_text()
    assert 'unsupported measured pad step' in pad
    assert 'ot_cf_pinreg_limits' in pad
    assert 'set pp_step $pp_step_cap' in pad


def test_same_basis_hold_audit_blocks_shifted_work_and_hidden_spread():
    import copy
    import sys
    sys.path.insert(0, str(ROOT/'tools/die_plan'))
    import pinreg_audit
    def records():
        return {c: dict(corner=c.upper(),parasitics='global_routing',pinreg_n=100,
                        pinreg_mean_ps=250,bound_ps=250,tol_ps=20,
                        group_min_ps=245,group_max_ps=255,group_spread_ps=10,
                        hold_census_status='MEASURED',hold_census_n=0,
                        hold_census_worst_ps=0,hold_census_tns_ps=0,hold_census_margin_n=0)
                for c in ('tt','ff')}
    before=records(); after=records()
    assert pinreg_audit.evaluate(before,after)['verdict']=='PASS'
    bad=copy.deepcopy(after);bad['ff']['hold_census_margin_n']=1
    assert pinreg_audit.evaluate(before,bad)['verdict']=='FAIL'
    bad=copy.deepcopy(after);bad['tt']['group_spread_ps']=21
    assert pinreg_audit.evaluate(before,bad)['verdict']=='FAIL'
    bad=copy.deepcopy(before);bad['tt']['parasitics']='placement'
    assert pinreg_audit.evaluate(bad,after)['verdict']=='FAIL'
    assert pinreg_audit.evaluate({},after)['verdict']=='FAIL'


def test_negative_hold_census_counts_unique_endpoints_and_keeps_worst_slack():
    out = tcl("""
proc get_full_name {x} {return $x}
proc all_outputs {} {return {result}}
proc get_fanin {args} {return {out/Q out2/Q}}
proc all_registers {what} {
 switch -- $what {
  -async_pins {return {out/R}}
  -data_pins {return {in/D out/D out2/D out/R}}
  -output_pins {return {in/Q out/Q out2/Q}}
 }
}
proc find_timing_paths {args} {return {p0 p1 p2}}
proc get_property {object key} {
 if {$key eq "slack"} {return [dict get {p0 -2.0 p1 -5.0 p2 -1.0} $object]}
 if {$key eq "endpoint"} {return [dict get {p0 out/D p1 out/D p2 out2/D} $object]}
 error "unknown property"
}
set c [ot_cf_output_hold_census]
puts "[dict get $c n] [dict get $c worst_ps] [dict get $c tns_ps] [dict get $c margin_n]"
""")
    assert out == '2 -5.0 -6.0 2'
