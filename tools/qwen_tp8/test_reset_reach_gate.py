#!/usr/bin/env python3
"""Reset reachability gate (die standard: regional reset; ROOT-2105 10-17).  A reset sink buried under a block
(dv2f11: rst_field 34 sink_unreachable from abutted cluster/slice pins) must FAIL the die build -- also under
OT_RESET_GATE=warn, which stage_build.sh sets -- and only OT_RESET_GATE=diag continues, recording FAIL_DIAG."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import qwen_rom_fulldie as F                     # noqa: E402
import qwen_rom_fulldie_b3r2 as G                # noqa: E402

NETS = [dict(bid='rst_x', dom='rst_x', drv=('d', 'rso', (1900., 1900.)), domain='c',
             sinks=[('a', 'rst_n', (500., 500.)), ('b', 'rst_n', (1800., 1200.)), ('c', 'rst_n', (1200., 1800.))])]
BURIED = [(0., 0., 1000., 1000.)]                # sink a.rst_n sits 500 um inside this block


def _errors(rects):
    return G._rst_tree_build(NETS, rects, 2000., 2000., F.GX, F.GY)[3]


@pytest.mark.parametrize('mode', [None, 'warn', ''])
def test_unreachable_sink_fails(monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv('OT_RESET_GATE', raising=False)
    else:
        monkeypatch.setenv('OT_RESET_GATE', mode)
    e = _errors(BURIED)
    assert [x['kind'] for x in e] == ['sink_unreachable'] and e[0]['pin'] == 'a.rst_n'
    rec = {}
    with pytest.raises(ValueError, match='reachability gate FAIL'):
        G._reset_reach_gate(e, rec)
    assert rec['reach_gate'] == 'FAIL' and rec['reach_gate_kinds'] == {'sink_unreachable': 1}


def test_diag_continues_but_records_fail(monkeypatch):
    monkeypatch.setenv('OT_RESET_GATE', 'diag')
    rec = {}
    G._reset_reach_gate(_errors(BURIED), rec)
    assert rec['reach_gate'] == 'FAIL_DIAG'


def test_reachable_passes(monkeypatch):
    monkeypatch.setenv('OT_RESET_GATE', 'warn')
    e = _errors([])
    rec = {}
    G._reset_reach_gate(e, rec)
    assert e == [] and rec['reach_gate'] == 'PASS'


def test_tree_build_calls_gate():
    src = Path(G.__file__).read_text()
    body = src[src.index('cells, wires, per, errors = _rst_tree_build('):]
    body = body[:body.index('rec[\'partial_unbuilt_nets\']')]
    assert '_reset_reach_gate(errors, rec)' in body and "!= 'warn'" not in body
