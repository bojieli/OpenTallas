"""Exercise hierarchical reset-net discovery with a small OpenDB interface mock."""
import shutil
import subprocess
from pathlib import Path

import pytest

HOOK = Path(__file__).with_name('reset_taps.tcl')


def run_hook(tmp_path, names):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    nets = ' '.join(f'n{i}' for i in range(len(names)))
    mock = ['namespace eval ord {}', 'proc ord::get_db_block {} {return blk}',
            'proc ord::get_db_tech {} {return tech}',
            'proc tech {method} {return 1000}',
            f'proc blk {{method args}} {{switch $method {{getNets {{return {{{nets}}}}} getBTerms {{return {{}}}} findNet {{return NULL}}}}}}']
    for i, name in enumerate(names):
        mock.append(f'proc n{i} {{method}} {{return {{{name}}}}}')
    script = '\n'.join(mock) + f'\nsource {{{HOOK}}}\nputs "RES [rt_tapnet blk 0] [rt_tapnet blk 20]"\n'
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


@pytest.mark.parametrize('prefix', ['', 'u_bound.', 'u_bound/'])
def test_reset_tap_flat_and_bound_names(tmp_path, prefix):
    p = run_hook(tmp_path, [prefix + 'rst_n_t0', prefix + 'rst_n_t20'])
    assert not p.stderr, p.stderr
    assert 'RES n0 n1' in p.stdout


def test_reset_tap_zero_alias(tmp_path):
    p = run_hook(tmp_path, ['u_bound.rst_n', 'u_bound.rst_n_t20'])
    assert not p.stderr, p.stderr
    assert 'RES n0 n1' in p.stdout


def test_reset_tap_ambiguous_nested_partitions(tmp_path):
    p = run_hook(tmp_path, ['a.rst_n_t20', 'b.rst_n_t20'])
    assert 'ambiguous synchroniser net for tap 20' in p.stderr


def leaf_hook(tmp_path, sink_x=100):
    """Clock pins point to the wrong leaf; actual reset launch flops decide."""
    mock = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
proc blk {m args} {switch $m {getNets {return {n0 n1}} getBTerms {return {b0 b1}} getInsts {return sink}}}
proc b0 {m} {switch $m {getName {return clk} getBBox {return box0}}}
proc b1 {m} {switch $m {getName {return clk_t1} getBBox {return box1}}}
proc box0 {m} {if {$m in {xMin xMax}} {return 400}; return 0}
proc box1 {m} {if {$m in {xMin xMax}} {return 600}; return 0}
proc n0 {m} {switch $m {getName {return rst_n_t0} getITerms {return {q0 si}}}}
proc n1 {m} {switch $m {getName {return rst_n_t1} getITerms {return q1}}}
proc q0 {m} {switch $m {getMTerm {return out} getInst {return launch0}}}
proc q1 {m} {switch $m {getMTerm {return out} getInst {return launch1}}}
proc out {m} {if {$m eq "getIoType"} {return OUTPUT}; return Q}
proc inp {m} {if {$m eq "getIoType"} {return INPUT}; return RESETN}
proc dff {m} {return DFFHQNx1}
proc launch0 {m} {switch $m {getMaster {return dff} getLocation {return {1000 0}}}}
proc launch1 {m} {switch $m {getMaster {return dff} getLocation {return {0 0}}}}
proc sink {m} {global sx; switch $m {getMaster {return dff} getLocation {return [list $sx 0]} getName {return u_epoch/eq} getPlacementStatus {return PLACED} getITerms {return si}}}
set current n0
proc si {m args} {global current; switch $m {getMTerm {return inp} getNet {return $current} getInst {return sink} disconnect {} connect {set current [lindex $args 0]}}}
set rt_postplace 1
set rt_leaf_reach_um 405
'''
    script = (mock + f'\nset sx {sink_x}\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n'
              + f'if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\n'
              + 'puts "FINAL $current"\n')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_reset_leaf_uses_real_launch_and_checks_placed_sink(tmp_path):
    p = leaf_hook(tmp_path)
    assert p.returncode == 0, p.stderr
    assert 'FINAL n1' in p.stdout
    assert 'LEAF 1 sinks, max hop 100.000 um, limit 405 um: PASS' in p.stdout


def test_reset_leaf_overreach_mutant_fails_closed(tmp_path):
    p = leaf_hook(tmp_path, 500)
    assert p.returncode != 0
    assert 'OT_RESET_LEAF unreachable control sinks' in p.stderr
    assert 'max hop 500.000 um, limit 405 um: FAIL' in p.stdout
