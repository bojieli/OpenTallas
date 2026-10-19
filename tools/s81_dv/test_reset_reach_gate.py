"""S81-DV dv_bind reset reachability gate (die standard: regional reset; as Qwen 27309ba59 / HBM die_case_v16).
A block reset pin or relay station whose cell has no street and no tree station within the reach FAILS the bind, also
under OT_RESET_GATE=warn; only OT_RESET_GATE=diag continues (FAIL_DIAG)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dv_bind as D  # noqa: E402


def plan(blocks):
    return {'facts': {'die_um': [2000.0, 2000.0]}, 'blocks': blocks}


OPEN = [dict(name='a', x=100.0, y=100.0, w=200.0, h=200.0)]
# one block covers the whole west 1600 um: the station inside it (x 200) is ~1.4 mm from the nearest street
WALL = [dict(name='big', x=0.0, y=0.0, w=1600.0, h=2000.0), dict(name='b', x=1700.0, y=900.0, w=200.0, h=200.0)]


def run(blocks, pts, monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv('OT_RESET_GATE', raising=False)
    else:
        monkeypatch.setenv('OT_RESET_GATE', mode)
    reg = {b['name']: 'r0' for b in blocks}
    return D.reset_tree(plan(blocks), reg, pts, {})


def test_reachable_passes(monkeypatch):
    r = run(OPEN, {'l0': [(800.0, 800.0)]}, monkeypatch, None)
    assert r['summary']['reach_gate']['reach_gate'] == 'PASS'


@pytest.mark.parametrize('mode', [None, 'warn'])
def test_station_under_block_fails(monkeypatch, mode):
    with pytest.raises(ValueError, match='reachability gate FAIL'):
        run(WALL, {'l0': [(200.0, 1000.0)]}, monkeypatch, mode)


def test_diag_records(monkeypatch):
    r = run(WALL, {'l0': [(200.0, 1000.0)]}, monkeypatch, 'diag')
    g = r['summary']['reach_gate']
    assert g['reach_gate'] == 'FAIL_DIAG' and g['kinds'].get('sink_unreachable', 0) >= 1
    assert any(e['pin'] == 'l0[0].rs' for e in g['first'])


def test_narrow_strip_reaches(monkeypatch):
    # S81-DIE5: a 20-um block-free strip between two blocks (a slice-column margin) holds reset stations: a lane station
    # 1.4 mm up the strip is reachable (p4j failed 727 sinks this way)
    blocks = [dict(name='l', x=0.0, y=400.0, w=990.0, h=1600.0), dict(name='r', x=1010.0, y=400.0, w=990.0, h=1600.0)]
    r = run(blocks, {'l0': [(1000.0, 1800.0)]}, monkeypatch, None)
    assert r['summary']['reach_gate']['reach_gate'] == 'PASS'
