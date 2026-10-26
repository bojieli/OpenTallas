#!/usr/bin/env python3
"""H-D4G 10-17: die_case_v16 reset reachability gate (die standard: regional reset; as the Qwen generator 27309ba59).
A buried reset sink, a die-wide por fan-out beyond the reach and an over-reach forest leaf FAIL the case, also under
OT_RESET_GATE=warn; only OT_RESET_GATE=diag continues (FAIL_DIAG)."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_case_v16 as D  # noqa: E402

PL = {'hb_ckgen': dict(x=0, y=0, w=100, h=100, o='R0'),
      'a': dict(x=200, y=0, w=100, h=100, o='R0'),          # reset pin 20 um inside 'big' -> buried
      'big': dict(x=150, y=0, w=600, h=600, o='R0'),
      'far': dict(x=3000, y=0, w=100, h=100, o='R0'),
      'near': dict(x=100, y=300, w=40, h=50, o='R0'),
      'rrf_leaf': dict(x=100, y=360, w=20, h=20, o='R0')}
CELL = {n: n for n in PL}
VXY = {'hb_ckgen': {'por_stream': (100, 50)}, 'a': {'rst_n': (50, 50)}, 'far': {'rst_n': (0, 50)}, 'big': {},
       'near': {'rst_n': (0, 0)}, 'rrf_leaf': {'rst_n': (10, 10)}}
MASTER = {'rrf_leaf': 'hbfd_rrl_hop'}


def gate(rst, nets, mode):
    return D.reset_reach_gate(rst, nets, PL, VXY, CELL, lambda n: MASTER.get(n, 'x'), 405.0, mode=mode)


@pytest.mark.parametrize('mode', [None, '', 'warn'])
def test_buried_and_far_fail(mode, monkeypatch):
    monkeypatch.delenv('OT_RESET_GATE', raising=False)
    with pytest.raises(ValueError, match='reachability gate FAIL'):
        gate({'stream': [('a', 'rst_n'), ('far', 'rst_n')]}, {}, mode or '')


def test_kinds_and_diag():
    rec = gate({'stream': [('a', 'rst_n'), ('far', 'rst_n'), ('near', 'rst_n')]}, {}, 'diag')
    assert rec['reach_gate'] == 'FAIL_DIAG'
    assert rec['kinds'] == {'sink_unreachable': 1, 'no_regional_tree': 1}


def test_forest_leaf_over_reach():
    nets = {('rrf_leaf', 'rst_n'): [('rrf_leaf', 'rst_n'), ('near', 'rst_n'), ('far', 'rst_n')]}
    rec = gate({}, nets, 'diag')
    assert rec['kinds'] == {'sink_unreachable': 1} and rec['forest_sinks'] == 2


def test_pass():
    rec = gate({'stream': [('near', 'rst_n')]}, {}, 'warn')
    assert rec['reach_gate'] == 'PASS'
