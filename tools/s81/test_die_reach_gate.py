"""Focused tests of the opt-in measured-reach hop gate (tools/s81/die_reach_gate.py, dsrom_s81_fulldie.py --reach-table)."""
import json
import re
import sys
from collections import namedtuple
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_reach_gate as DRG  # noqa: E402

Inst = namedtuple('Inst', 'name master x y orient')


def lef(macro, w=10.0, h=10.0, bits=2):
    out = [f'MACRO {macro}', f'  SIZE {w} BY {h} ;']
    for b in range(bits):
        y = 1.0 + b
        out += [f'  PIN i[{b}]', '    PORT', '      LAYER M4 ;', f'        RECT 0 {y} 0.1 {y + 0.02} ;', '    END',
                f'  END i[{b}]', f'  PIN o[{b}]', '    PORT', '      LAYER M4 ;', f'        RECT {w - 0.1} {y} {w} {y + 0.02} ;',
                '    END', f'  END o[{b}]']
    out.append(f'END {macro}')
    return '\n'.join(out)


def pslice(p):
    m = re.match(r'^(\w+)(?:\[(\d+)(?::(\d+))?\])?$', p)
    hi = int(m.group(2)) if m.group(2) else None
    lo = int(m.group(3)) if m.group(3) else hi
    return m.group(1), lo, hi


LEFS = [lef('dsfd_rly_63_WE'), lef('dsfd_stnh_70x1'), lef('dsfd_hub_x')]


def table(tmp_path, classes):
    p = tmp_path / 'reach.json'
    p.write_text(json.dumps(dict(classes=classes)))
    return DRG.load_table(p)


def run(tmp_path, gap, classes, a='dsfd_rly_63_WE', b='dsfd_rly_63_WE'):
    insts = [Inst('r0', a, 0.0, 0.0, 'R0'), Inst('r1', b, 10.0 + gap, 0.0, 'R0')]
    buses = [('bus0', 'data', 2, [('r0', 'o[1:0]'), ('r1', 'i[1:0]')])]
    return DRG.gate(insts, buses, LEFS, pslice, table(tmp_path, classes))


def test_within_measured_reach_passes(tmp_path):
    r = run(tmp_path, 300.0, {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=350.0)})
    assert r['verdict'] == 'PASS' and r['bits_judged'] == 2 and r['bits_over_reach'] == 0


def test_over_reach_is_hard_fail(tmp_path):
    r = run(tmp_path, 400.0, {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=350.0)})
    assert r['verdict'] == 'FAIL' and r['bits_over_reach'] == 2
    assert r['worst_over'][0]['limit_um'] == 350.0


def test_limit_is_min_of_both_classes(tmp_path):
    cl = {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=500.0),
          'dsfd_stnh_70x1': dict(status='MEASURED', reach_um=250.0)}
    r = run(tmp_path, 300.0, cl, b='dsfd_stnh_70x1')
    assert r['verdict'] == 'FAIL' and r['worst_over'][0]['limit_um'] == 250.0


def test_hold_floor_is_error(tmp_path):
    r = run(tmp_path, 20.0, {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=350.0, hold_min_um=50.0)})
    assert r['verdict'] == 'FAIL' and r['bits_under_hold_floor'] == 2


def test_unmeasured_or_unusable_relay_fails_closed(tmp_path):
    r = run(tmp_path, 50.0, {'dsfd_rly_63_WE': dict(status='NOT_MEASURED', reason='x')})
    assert r['verdict'] == 'FAIL' and r['bits_unmeasured'] == 2
    r = run(tmp_path, 50.0, {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=350.0, usable_as_die_reach_bound=False)})
    assert r['verdict'] == 'FAIL' and r['unmeasured_masters'] == ['dsfd_rly_63_WE']
    r = run(tmp_path, 50.0, {'dsfd_stnh_70x1': dict(status='MEASURED', reach_um=350.0)})   # rly class absent
    assert r['verdict'] == 'FAIL' and r['bits_unmeasured'] == 2


def test_non_relay_hop_is_outside(tmp_path):
    r = run(tmp_path, 5000.0, {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=350.0)}, a='dsfd_hub_x', b='dsfd_hub_x')
    assert r['verdict'] == 'PASS' and r['bits_outside_relay_family'] == 2 and r['bits_judged'] == 0


def test_gate_reach_override_and_empty_table(tmp_path):
    r = run(tmp_path, 300.0, {'dsfd_rly_63_WE': dict(status='MEASURED', reach_um=500.0, gate_reach_um=200.0)})
    assert r['verdict'] == 'FAIL'
    with pytest.raises(DRG.ReachTableError):
        table(tmp_path, {})


def test_generator_option_is_opt_in():
    src = (Path(__file__).resolve().parents[1] / 'dsrom_s81_fulldie.py').read_text()
    assert "REACH_TABLE = None" in src and "'--reach-table'" in src
    assert 'if REACH_TABLE:\n        reach_gate_run(m, work, bnd)' in src
