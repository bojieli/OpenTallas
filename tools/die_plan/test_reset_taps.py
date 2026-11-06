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


def leaf_hook(tmp_path, sink_x=100, alias=None, leaf_alias=False):
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
    if leaf_alias:
        mock=mock.replace('getName {return rst_n_t1}', 'getName {return rst_n}')
    if alias:
        mock += r'''
rename blk oldblk
proc blk {m args} {if {$m eq "getNets"} {return {n0 n1 a0 a1}}; return [oldblk $m {*}$args]}
rename n0 oldn0
rename n1 oldn1
proc n0 {m} {switch $m {getName {return canonical0} getITerms {return {q0 si ai0}}}}
proc n1 {m} {switch $m {getName {return canonical1} getITerms {return {q1 ai1}}}}
proc a0 {m} {switch $m {getName {return rst_n_t0} getITerms {return ao0}}}
proc a1 {m} {switch $m {getName {return rst_n_t1} getITerms {return ao1}}}
proc ai0 {m} {switch $m {getMTerm {return inp} getNet {return n0} getInst {return alias0}}}
proc ai1 {m} {switch $m {getMTerm {return inp} getNet {return n1} getInst {return alias1}}}
proc ao0 {m} {switch $m {getMTerm {return out} getNet {return a0} getInst {return alias0}}}
proc ao1 {m} {switch $m {getMTerm {return out} getNet {return a1} getInst {return alias1}}}
proc alias0 {m} {switch $m {getMaster {return alias_master} getITerms {return {ai0 ao0}}}}
proc alias1 {m} {switch $m {getMaster {return alias_master} getITerms {return {ai1 ao1}}}}
'''
        mock += f'\nproc alias_master {{m}} {{return {alias}x2}}\n'
    script = (mock + f'\nset sx {sink_x}\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n'
              + f'if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\n'
              + 'puts "FINAL $current"\n')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_reset_leaf_uses_real_launch_and_checks_placed_sink(tmp_path):
    p = leaf_hook(tmp_path)
    assert p.returncode == 0, p.stderr
    assert 'FINAL n1' in p.stdout
    assert 'LEAF 1 sinks, max hop 100.000 um, limit 405 um: PASS' in p.stdout


def test_reset_leaf_overreach_is_advisory_and_named(tmp_path):
    p = leaf_hook(tmp_path, 500)
    assert p.returncode == 0, p.stderr
    assert 'OT_RESET_LEAF advisory' in p.stdout
    assert 'max hop 500.000 um, limit 405 um: OVER' in p.stdout


def single_hook(tmp_path, sink_x=100, launch=True):
    """One terminal (rst_n_t0) through a buffer to a placed control sink: the final hop is still bounded."""
    mock = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
proc blk {m args} {switch $m {getNets {return {n0 nb}} getBTerms {return {b0}} getInsts {return {buf0 sink}}}}
proc b0 {m} {switch $m {getName {return clk} getBBox {return box0}}}
proc box0 {m} {return 0}
proc n0 {m} {global LAUNCH; switch $m {getName {return rst_n_t0} getITerms {if {$LAUNCH} {return {q0 bi}}; return bi}}}
proc nb {m} {switch $m {getName {return rst_buf} getITerms {return {bo si}}}}
proc q0 {m} {switch $m {getMTerm {return out} getInst {return launch0}}}
proc bi {m} {switch $m {getMTerm {return inp} getInst {return buf0} getNet {return n0}}}
proc bo {m} {switch $m {getMTerm {return out} getInst {return buf0} getNet {return nb}}}
proc out {m} {if {$m eq "getIoType"} {return OUTPUT}; return Q}
proc inp {m} {if {$m eq "getIoType"} {return INPUT}; return RESETN}
proc dff {m} {return DFFHQNx1}
proc bufm {m} {return BUFx2}
proc launch0 {m} {switch $m {getMaster {return dff} getLocation {return {0 0}} getName {return u_rrl_3/q}}}
proc buf0 {m} {switch $m {getMaster {return bufm} getLocation {return {50 0}} getName {return rbuf} getPlacementStatus {return PLACED} getITerms {return {bi bo}}}}
proc sink {m} {global sx; switch $m {getMaster {return dff} getLocation {return [list $sx 0]} getName {return u_epoch/eq} getPlacementStatus {return PLACED} getITerms {return si}}}
proc si {m args} {switch $m {getMTerm {return inp} getNet {return nb} getInst {return sink}}}
set rt_postplace 1
set rt_leaf_reach_um 405
'''
    script = (mock + f'\nset sx {sink_x}\nset LAUNCH {int(launch)}\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n'
              + f'if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\n')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_reset_leaf_single_terminal_bounded(tmp_path):
    p = single_hook(tmp_path)
    assert p.returncode == 0, p.stderr
    assert 'LEAF 1 sinks (single terminal 0), max hop 100.000 um, limit 405 um: PASS' in p.stdout


def test_reset_leaf_single_terminal_overreach_is_advisory(tmp_path):
    p = single_hook(tmp_path, 500)
    assert p.returncode == 0, p.stderr
    assert 'OT_RESET_LEAF advisory' in p.stdout
    assert 'limit 405 um: OVER' in p.stdout


def test_reset_leaf_single_terminal_without_launch_flop_fails(tmp_path):
    p = single_hook(tmp_path, launch=False)
    assert p.returncode != 0
    assert 'has no single reset launch flop' in p.stderr


@pytest.mark.parametrize('alias', ['BUF','INV','CKBUF','CKINVDC'])
def test_dangling_preserved_terminal_alias_still_counts_functional_sinks(tmp_path, alias):
    p=leaf_hook(tmp_path,alias=alias)
    assert p.returncode==0,p.stderr
    assert 'LEAF 1 sinks, max hop 100.000 um' in p.stdout
    assert 'FINAL n1' in p.stdout
    # The alias must not turn a real geometry failure into PASS with zero sinks.
    p=leaf_hook(tmp_path,sink_x=500,alias=alias)
    assert p.returncode==0,p.stderr
    assert 'LEAF 1 sinks, max hop 500.000 um' in p.stdout
    assert 'OT_RESET_LEAF advisory' in p.stdout


def test_shared_leaf_alias_maps_to_nonzero_missing_terminal(tmp_path):
    p=leaf_hook(tmp_path,leaf_alias=True)
    assert p.returncode==0,p.stderr
    assert 'LEAF 1 sinks, max hop 100.000 um' in p.stdout
    assert 'FINAL n1' in p.stdout


def test_reset_tap_sourced_inside_proc(tmp_path):
    """ORFS sources PRE_CTS / PRE_GLOBAL_PLACE hooks inside a proc (cts.tcl): rt_tapnet's global table must resolve."""
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    mock = ['namespace eval ord {}', 'proc ord::get_db_block {} {return blk}',
            'proc ord::get_db_tech {} {return tech}', 'proc tech {method} {return 1000}',
            'proc blk {method args} {switch $method {getNets {return {n0 n1}} getBTerms {return {}} findNet {return NULL}}}',
            'proc n0 {method} {return rst_n_t0}', 'proc n1 {method} {return rst_n_t20}']
    script = '\n'.join(mock) + (f'\nproc orfs_hook {{}} {{ source {{{HOOK}}}; puts "RES [rt_tapnet blk 0] [rt_tapnet blk 20]" }}'
                                '\norfs_hook\n')
    p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert not p.stderr, p.stderr
    assert 'RES n0 n1' in p.stdout


@pytest.mark.parametrize('listed,final', [(True, 'n1'), (False, 'n0')])
def test_repoint_only_landed_line_moved_flops(tmp_path, listed, final):
    """AUTOBUILD-PIPE-2 (S81 slice_station t14/t26): the landed line moves stations after the pre-GPL re-point;
    landing_placement.tcl re-sources this hook with rt_repoint_only = the moved flops, which then take the reset of
    their nearest terminal at the final site; flops outside the list are untouched."""
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    src = Path(__file__).read_text().split("def leaf_hook", 1)[1].split("mock = r'''", 1)[1].split("'''", 1)[0]
    src = (src.replace('getPlacementStatus {return PLACED}', 'getPlacementStatus {return FIRM}')
              .replace('set rt_postplace 1\n', '').replace('set rt_leaf_reach_um 405\n', ''))
    only = 'u_epoch/eq 1' if listed else 'other/eq 1'
    script = (src + f'\nset sx 100\nset ::env(RESULTS_DIR) {{{tmp_path}}}\nset rt_repoint_only [dict create {only}]\n'
              + f'if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\nputs "FINAL $current"\n')
    r = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    assert f'FINAL {final}' in r.stdout
    assert not (Path(tmp_path) / 'ot_face_flops.txt').read_text()      # (1) skipped: nothing appended


def port_hook(tmp_path, sink_x=600, port=True):
    """FLOW-20 11-01: a hard wrapper (wire rst_n = arst_n) has no rst_n / rst_n_t<i> net; the port-delivered reset
    hop is measured from the arst_n pin and reported (INFO) when gen_phys names the port, else the old error."""
    mock = r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {m} {return 1}
proc blk {m args} {switch $m {getNets {return {np nb}} getBTerms {return {b0 bp}} getInsts {return {buf0 sink}} findBTerm {if {[lindex $args 0] eq "arst_n"} {return bp}; return NULL}}}
proc b0 {m} {switch $m {getName {return clk} getBBox {return box0}}}
proc bp {m} {switch $m {getName {return arst_n} getBBox {return boxp} getNet {return np}}}
proc box0 {m} {return 0}
proc boxp {m} {return 0}
proc np {m} {switch $m {getName {return arst_n} getITerms {return bi}}}
proc nb {m} {switch $m {getName {return rst_buf} getITerms {return {bo si}}}}
proc bi {m} {switch $m {getMTerm {return inp} getInst {return buf0} getNet {return np}}}
proc bo {m} {switch $m {getMTerm {return out} getInst {return buf0} getNet {return nb}}}
proc out {m} {if {$m eq "getIoType"} {return OUTPUT}; return Q}
proc inp {m} {if {$m eq "getIoType"} {return INPUT}; return RESETN}
proc dff {m} {return DFFHQNx1}
proc bufm {m} {return BUFx2}
proc buf0 {m} {switch $m {getMaster {return bufm} getLocation {return {50 0}} getName {return rbuf} getPlacementStatus {return PLACED} getITerms {return {bi bo}}}}
proc sink {m} {global sx; switch $m {getMaster {return dff} getLocation {return [list $sx 0]} getName {return u_phy/q} getPlacementStatus {return PLACED} getITerms {return si}}}
proc si {m args} {switch $m {getMTerm {return inp} getNet {return nb} getInst {return sink}}}
set rt_postplace 1
set rt_leaf_reach_um 405
'''
    if port:
        mock += 'set rt_port_reset arst_n\n'
    script = (mock + f'\nset sx {sink_x}\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n'
              + f'if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\n')
    return subprocess.run(['tclsh'], input=script, text=True, capture_output=True)


def test_port_delivered_reset_is_reported_not_failed(tmp_path):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    p = port_hook(tmp_path)
    assert p.returncode == 0, p.stderr
    assert 'LEAF 1 sinks (port-delivered arst_n, no in-kit terminal), max hop 600.000 um, limit 405 um: INFO (1 beyond' in p.stdout


def test_missing_terminal_without_port_reset_still_errors(tmp_path):
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    p = port_hook(tmp_path, port=False)
    assert p.returncode != 0
    assert 'OT_RESET_LEAF no reset terminal net' in p.stderr


@pytest.mark.parametrize('pol', ['q', 'qn'])
def test_unnamed_tap_bound_by_relay_identity(tmp_path, pol):
    """DIE-QC-61 11-01 (GEOM-107 tt_ctlm): Yosys kept a load port's name for tap 0 (u_bound.u_core.rst_n[0]); the
    tap had no named net and no FIRM flop was re-pointed (0 re-pointed, r2r 955.8 um).  reset_tree.tcl's relay
    identity (::rtr_qnets rst_n_t0) names it; a QN relay output resolves through its inverter."""
    if not shutil.which('tclsh'):
        pytest.skip('tclsh unavailable')
    mock_extra = {'q': 'set ::rtr_qnets {rst_n_t0 n0}; set ::rtr_qpol {rst_n_t0 q}',
                  'qn': ('set ::rtr_qnets {rst_n_t0 qn0}; set ::rtr_qpol {rst_n_t0 qn}\n'
                         'proc qn0 {m} {switch $m {getName {return u_rrl_6_qn} getITerms {return {qo0 ii0}}}}\n'
                         'proc qo0 {m} {switch $m {getMTerm {return out} getInst {return launch0} getNet {return qn0}}}\n'
                         'proc ii0 {m} {switch $m {getMTerm {return inp} getInst {return inv0} getNet {return qn0}}}\n'
                         'proc io0 {m} {switch $m {getMTerm {return out} getInst {return inv0} getNet {return n0}}}\n'
                         'proc invm {m} {return INVx1}\n'
                         'proc inv0 {m} {switch $m {getMaster {return invm} getITerms {return {ii0 io0}}}}')}[pol]
    for with_identity, final in ((False, 'n0'), (True, 'n1')):
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
proc n0 {m} {switch $m {getName {return {u_bound.u_core.rst_n[0]}} getITerms {return {q0 si}}}}
proc n1 {m} {switch $m {getName {return u_bound.rst_n_t1} getITerms {return q1}}}
proc q0 {m} {switch $m {getMTerm {return out} getInst {return launch0}}}
proc q1 {m} {switch $m {getMTerm {return out} getInst {return launch1}}}
proc out {m} {if {$m eq "getIoType"} {return OUTPUT}; return Q}
proc inp {m} {if {$m eq "getIoType"} {return INPUT}; return RESETN}
proc dff {m} {return DFFHQNx1}
proc launch0 {m} {switch $m {getMaster {return dff} getLocation {return {1000 0}}}}
proc launch1 {m} {switch $m {getMaster {return dff} getLocation {return {0 0}}}}
proc sink {m} {switch $m {getMaster {return dff} getLocation {return {100 0}} getName {return u_bout_tl/eq} getPlacementStatus {return FIRM} getITerms {return si}}}
set current n0
proc si {m args} {global current; switch $m {getMTerm {return inp} getNet {return $current} getInst {return sink} disconnect {} connect {set current [lindex $args 0]}}}
'''
        if pol == 'qn':
            # the QN relay drives an inverter whose output is the terminal net n0 (launch walks back through it)
            mock = mock.replace('getITerms {return {q0 si}}', 'getITerms {return {io0 si}}')
        if with_identity:
            mock += '\n' + mock_extra + '\n'
        elif pol == 'qn':
            mock += '\n' + mock_extra.split('\n', 1)[1] + '\n'
        script = (mock + f'\nset ::env(RESULTS_DIR) {{{tmp_path}}}\n'
                  + f'if {{[catch {{source {{{HOOK}}}}} msg]}} {{puts stderr $msg; exit 1}}\n' + 'puts "FINAL $current"\n')
        p = subprocess.run(['tclsh'], input=script, text=True, capture_output=True)
        assert p.returncode == 0, p.stderr
        assert f'FINAL {final}' in p.stdout, (with_identity, p.stdout)
        if with_identity:
            assert 'relay identity rst_n_t0 -> u_bound.u_core.rst_n[0] (tap 0)' in p.stdout
            assert '1 re-pointed' in p.stdout
