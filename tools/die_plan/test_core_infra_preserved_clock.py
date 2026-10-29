"""Signed hard-clock feeds stay physical inputs, fully counted by the tree audit."""
import copy
import math
import subprocess
from pathlib import Path
import pytest
import core_infra as CI
from test_core_infra import sample


def hard_tree():
    s = sample()
    s['core_tree'] = {'clock_port': 'ck', 'nodes': [
        dict(name='root', master='BUFx16f_ASAP7_75t_R', xy_um=[430, 430], parent='port:ck'),
        dict(name='n0', master='BUFx8_ASAP7_75t_R', xy_um=[200, 200], parent='root'),
        dict(name='n1', master='BUFx8_ASAP7_75t_R', xy_um=[600, 600], parent='root')],
        'leaves': [dict(node='n0', sinks=['u0/CLK', 'u1/CLK']), dict(node='n1', sinks=['u2/CLK', 'u3/CLK'])],
        'preserved_hard_clocks': [dict(pin='u_recip/clk', master='ot_qkh_recip_leaf',
            signed_latency_ps={'TT': {'min': 201.60768, 'max': 264.82568},
                               'FF': {'min': 155.0, 'max': 205.0}},
            signed_view='signed/ot_qkh_recip_leaf/core.json')]}
    s['pg_obstructions_um'] = {}
    return s


def test_preserved_hard_clock_is_counted_without_a_new_stage():
    s = hard_tree(); p = CI.compile_slice(s)
    assert p['core_tree']['depth'] == 2
    assert len(p['core_tree']['preserved_hard_clocks']) == 1
    t = CI.emit_tcl(s)
    call = 'ot_ci_tree_preserve_hard {ck} {u_recip/clk} {ot_qkh_recip_leaf}'
    assert t.index(call) < t.index('ot_ci_tree_finish')
    assert sum(len(l['sinks']) for l in p['core_tree']['leaves']) == 4
    s['core_tree'].pop('preserved_hard_clocks')
    assert 'ot_ci_tree_preserve_hard' not in CI.emit_tcl(s)


@pytest.mark.parametrize('change,match', [
    (lambda h: h.update(pin='u0/CLK'), 'twice'),
    (lambda h: h.update(pin='unqualified'), 'instance/pin'),
    (lambda h: h.update(master=''), 'master'),
    (lambda h: h.update(signed_view=''), 'receipt'),
    (lambda h: h['signed_latency_ps'].pop('FF'), 'TT/FF'),
    (lambda h: h['signed_latency_ps'].update(SS={'min': 1, 'max': 2}), 'TT/FF'),
    (lambda h: h['signed_latency_ps']['TT'].update(min=math.nan), 'invalid'),
    (lambda h: h['signed_latency_ps']['TT'].update(min=-1), 'invalid'),
    (lambda h: h['signed_latency_ps']['FF'].update(min=206), 'invalid'),
])
def test_invalid_preserved_clock_metadata_is_refused(change, match):
    s = hard_tree(); change(s['core_tree']['preserved_hard_clocks'][0])
    with pytest.raises(CI.InfraError, match=match): CI.compile_slice(s)


def test_preserved_clock_cannot_be_declared_twice():
    s = hard_tree(); s['core_tree']['preserved_hard_clocks'] *= 2
    with pytest.raises(CI.InfraError, match='twice'): CI.compile_slice(s)


def test_runtime_preserves_root_and_keeps_unassigned_ff_in_census():
    mocks = r'''
set ::net ROOT;set ::typed 1;set ::block 1
proc B {op args} {if {$op eq "findInst" && [lindex $args 0] eq "u_recip"} {return I};return NULL}
proc I {op args} {switch $op {getMaster {return M} findITerm {return IT} getName {return u_recip}}}
proc M {op args} {switch $op {isBlock {return $::block} getName {return ot_qkh_recip_leaf}}}
proc IT {op args} {switch $op {isInputSignal {return 1} getNet {return $::net} getInst {return I} getMTerm {return P} default {error "MUTATION_REFUSED $op"}}}
proc P {op args} {return clk}
proc FF {op args} {if {$op eq "getInst"} {return FI};return FP}
proc FI {op args} {return unassigned_ff}
proc FP {op args} {return CLK}
proc get_pins {args} {return PIN}
proc get_cells {args} {return CELL}
proc get_lib_cells {args} {return LIBCELL}
proc get_lib_pins {args} {return LIBPIN}
proc get_property {obj prop} {if {$prop eq "name"} {return clk};if {$prop eq "is_clock"} {return $::typed};error BADPROP}
set ::ot_ci_b B;set ::ot_ci_tree_out [dict create port:ck ROOT]
set ::ot_ci_tree_expected {IT FF};set ::ot_ci_tree_seen {};set ::ot_ci_cells {}
ot_ci_tree_preserve_hard ck u_recip/clk ot_qkh_recip_leaf
if {$::net ne "ROOT" || $::ot_ci_tree_seen ne "IT"} {error "ROOT_OR_CENSUS_CHANGED"}
if {![catch {ot_ci_tree_finish} msg] || ![string match *UNASSIGNED_CLOCK_SINK* $msg]} {error "UNASSIGNED_FF_DROPPED"}
foreach mode {wrong_root nonclock nonblock duplicate wrongmaster} {
 set ::net ROOT;set ::typed 1;set ::block 1;set ::ot_ci_tree_seen {}
 switch $mode {wrong_root {set ::net WRONG} nonclock {set ::typed 0} nonblock {set ::block 0} duplicate {set ::ot_ci_tree_seen IT}}
 set master [expr {$mode eq "wrongmaster" ? "wrong_master" : "ot_qkh_recip_leaf"}]
 if {![catch {ot_ci_tree_preserve_hard ck u_recip/clk $master} msg]} {error "MUTANT_ESCAPED $mode"}
 puts "PRESERVED_CLOCK_MUTANT_CAUGHT $mode"
}
puts PRESERVED_CLOCK_RUNTIME_PASS
'''
    r = subprocess.run(['tclsh'], input=Path(CI.__file__).with_suffix('.tcl').read_text()+'\n'+mocks,
                       text=True, capture_output=True)
    assert r.returncode == 0 and not r.stderr, r.stdout+r.stderr
    assert 'PRESERVED_CLOCK_RUNTIME_PASS' in r.stdout
    assert r.stdout.count('PRESERVED_CLOCK_MUTANT_CAUGHT') == 5
