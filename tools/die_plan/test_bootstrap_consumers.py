"""Mixed transport/mission wrappers must boot without releasing computation."""
import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import gen_rtl
import reset_tree as RT
import schema as S

HERE = Path(__file__).parent


def mixed():
    p = json.loads((HERE/'examples/tiny_plan.json').read_text())
    p['reset'].update(release='wavefront', start='broadcast')
    for ty in p['partition_types'].values():
        ty.pop('sources', None)
    p['partition_types']['mid']['reset'].update(bootstrap_buses=['fx_i', 'fx_o'])
    p['partition_types']['src']['reset'].update(bootstrap_contents=['u_core'])
    return p


def test_raw_transport_has_same_depth_and_mission_gate_survives():
    p = S.Plan(mixed()); t = RT.for_type(p, 'mid')
    rel = {r['q']: r for r in RT.start_relays(t)}
    for i in t['bootstrap_taps']:
        mission, boot = rel[f'rst_n_t{i}'], rel[f'rst_boot_t{i}']
        assert mission['role'] == 'gated' and 'run' in mission
        assert boot['role'] == 'bootstrap_transport' and 'run' not in boot
        assert boot['d'] == mission['d'] and boot['depth'] == mission['depth']
    w = RT.wf_plan(p)
    assert w['types']['mid']['bootstrap_buses'] == ['fx_i', 'fx_o']
    assert w['types']['mid']['start_role'] == 'mission'


def test_wrapper_uses_raw_only_for_declared_transport_and_content(tmp_path):
    p = mixed()
    gen_rtl.write_rtl(p, tmp_path)
    mid = (tmp_path/(p['partition_types']['mid']['module']+'.sv')).read_text()
    assert re.search(r'u_ft_fx_s0.*?\.rst_n\(rst_boot_t', mid)
    assert re.search(r'u_ft_fr_s0.*?\.rst_n\(rst_n_t', mid)
    src = (tmp_path/(p['partition_types']['src']['module']+'.sv')).read_text()
    assert re.search(r'\.rst_n\(rst_boot_t', src)
    assert 'wire rst_n = rst_n_t' in src


@pytest.mark.parametrize('field,value', [('bootstrap_buses',['unknown']), ('bootstrap_contents',['missing'])])
def test_unknown_consumers_fail_closed(field, value):
    p = mixed(); p['partition_types']['mid']['reset'][field] = value
    with pytest.raises(RT.ResetError, match='unknown bootstrap consumers'):
        RT.for_type(S.Plan(p), 'mid')


def test_declaration_without_broadcast_fails_closed():
    p = mixed(); p['reset']['start'] = 'none'
    with pytest.raises(RT.ResetError, match='START-broadcast'):
        RT.for_type(S.Plan(p), 'mid')


def test_placed_bootstrap_sink_retargets_only_to_bootstrap_terminal(tmp_path):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    mock = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
proc blk {m args} {switch $m {getNets {return {m0 m1 b0n b1n}} getBTerms {return {c0 c1}} getInsts {return sink}}}
proc c0 {m} {switch $m {getName {return clk} getBBox {return box0}}}
proc c1 {m} {switch $m {getName {return clk_t1} getBBox {return box1}}}
proc box0 {m} {return 0}
proc box1 {m} {if {$m in {xMin xMax}} {return 100}; return 0}
proc m0 {m} {switch $m {getName {return rst_n_t0} getITerms {return qm0}}}
proc m1 {m} {switch $m {getName {return rst_n_t1} getITerms {return qm1}}}
proc b0n {m} {switch $m {getName {return rst_boot_t0} getITerms {return {qb0 si}}}}
proc b1n {m} {switch $m {getName {return rst_boot_t1} getITerms {return qb1}}}
proc qm0 {m} {switch $m {getMTerm {return out} getInst {return lm0}}}
proc qm1 {m} {switch $m {getMTerm {return out} getInst {return lm1}}}
proc qb0 {m} {switch $m {getMTerm {return out} getInst {return lb0}}}
proc qb1 {m} {switch $m {getMTerm {return out} getInst {return lb1}}}
proc out {m} {return OUTPUT}
proc inp {m} {if {$m eq "getIoType"} {return INPUT}; return RESETN}
proc dff {m} {return DFFHQNx1}
proc lm0 {m} {switch $m {getMaster {return dff} getLocation {return {0 0}}}}
proc lm1 {m} {switch $m {getMaster {return dff} getLocation {return {100 0}}}}
proc lb0 {m} {switch $m {getMaster {return dff} getLocation {return {0 0}}}}
proc lb1 {m} {switch $m {getMaster {return dff} getLocation {return {100 0}}}}
proc sink {m} {switch $m {getMaster {return dff} getLocation {return {100 0}} getName {return u_ft_hu_s0/eq} getPlacementStatus {return PLACED} getITerms {return si}}}
set current b0n
proc si {m args} {global current; switch $m {getMTerm {return inp} getNet {return $current} getInst {return sink} disconnect {} connect {set current [lindex $args 0]}}}
set rt_postplace 1
set rt_leaf_reach_um 405
'''
    mock += f'\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n'
    mock += f'if {{[catch {{source {{{HERE/"reset_taps.tcl"}}}}} msg]}} {{puts stderr $msg; exit 1}}\n'
    mock += 'puts "FINAL $current"\n'
    result = subprocess.run(['tclsh'], input=mock, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert 'role bootstrap_transport' in result.stdout
    assert 'FINAL b1n' in result.stdout, result.stdout
