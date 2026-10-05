import csv
import gzip
import importlib.util
import io
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('duty',ROOT/'tools/w10_clock_duty_ledger.py')
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
INPUT=ROOT/m.PREFIX


def raw(case):return gzip.decompress((INPUT/(case+'.csv.gz')).read_bytes())


def mutant(data,column,old,new):
    rows=list(csv.DictReader(io.StringIO(data.decode())))
    row=next(r for r in rows if r[column]==str(old))
    row[column]=str(new)
    out=io.StringIO();writer=csv.DictWriter(out,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)
    return out.getvalue().encode()


def test_actual_fullsize_duty_not_family_selective():
    a,b=m.inspect_trace(raw('bf16_router_gate'),['e0','e1'])
    assert a['root_rising_edges']==b['root_rising_edges']==1710
    assert a['each_of_eight_leaf_rising_edges']==1673
    assert b['each_of_eight_leaf_rising_edges']==1484
    assert a['root_active_fraction']=='1'
    assert a['leaf_fraction_exact']=='1673/1710'


def test_reset_drain_and_real_sleep():
    r=m.inspect_trace(raw('exact'),['dut'])[0]
    assert r['root_rising_edges']==20778
    assert r['each_of_eight_leaf_rising_edges']==16804
    assert r['reset_root_edges']==8
    assert r['drain_only_edges']>700 and r['stopped_intervals']
    assert r['wake_register_transitions']>5


def test_collapsed_or_divergent_leaf_trace_fails():
    with pytest.raises(AssertionError,match='leaf divergence'):
        m.inspect_trace(mutant(raw('exact'),'dut_leaf_mask',255,254),['dut'])


def test_wrong_registered_wake_fails():
    with pytest.raises(AssertionError,match='wake recurrence'):
        m.inspect_trace(mutant(raw('exact'),'dut_wake_post',1,0),['dut'])


def test_wrong_latch_phase_fails():
    with pytest.raises(AssertionError,match='latch phase'):
        m.inspect_trace(mutant(raw('exact'),'dut_wake_pre',1,0),['dut'])


def test_baseline_reconciliation_and_no_false_power_delta():
    r=m.build(INPUT)
    base=r['baseline_reconciliation']
    assert base['historical_pair_clock_floor_W']=='0.08328'
    assert base['embedded_clock_tree']['reported_total_W']=='0.0237'
    assert base['embedded_clock_tree']['switching_W']=='0.0108'
    assert base['wire_only_baseline_fF'] is None
    assert base['numerical_candidate_wire_delta_fF'] is None
    assert not base['old_wire_baseline_reconciled']
    assert all(v is None for v in r['remaining'].values())
    assert not r['physical_admission'] and not r['adopted']
    assert len(r['records'])==14
    for rec in r['records']:
        for e in rec['measured']:
            gs=e['nine_group_projection']
            if rec['case'].startswith('bf16_'):
                assert len(gs)==9 and sum(g['buffers'] for g in gs)==3873
                assert gs[-1]['active_cycles']==e['root_rising_edges']
                assert all(g['active_cycles']==e['each_of_eight_leaf_rising_edges'] for g in gs[:-1])
                assert all(g['net_wire_delta_fF_cycles'] is None for g in gs)
            else:
                assert not gs and not e['candidate_3873_buffer_ledger_applies']
