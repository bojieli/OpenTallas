import copy, importlib.util, json
from pathlib import Path
import pytest

_s = importlib.util.spec_from_file_location('hg_wstreet', Path(__file__).with_name('hg_wstreet.py'))
ws = importlib.util.module_from_spec(_s)
_s.loader.exec_module(ws)


def _plan():
    core = lambda i, x, y: dict(inst=i, module='m', origin_um=[x, y], outline_um=[216.0, 216.0], orient='R0')
    t = dict(outline_um=[1278.72, 1520.64], note='',
             hard_cores=[core('head0_e0', 17.28, 17.28), core('head0_e2', 17.28, 336.96), core('head0_e1', 336.96, 17.28)],
             clock=dict(taps=[dict(name='head0_e0', kind='core', xy=[120.0, 120.0]), dict(name='g0', xy=[290.0, 400.0])],
                        die_islands_um=[[100.0, 100.0, 102.7, 100.81], [250.0, 150.0, 252.7, 150.81], [20.0, 280.0, 22.7, 280.81]],
                        landing_contract=dict(bands=dict(b=dict(rect_um=[246.24, 17.28, 330.48, 25.92])))))
    return dict(partition_types=dict(kv3_hg_v1=t, kv3_pc_v1=copy.deepcopy(t)))


def test_moves_column_and_own_taps_only():
    p, rep, rs = ws.apply(_plan(), 43.2)
    t = p['partition_types']['kv3_hg_v1']
    xs = {h['inst']: h['origin_um'][0] for h in t['hard_cores']}
    assert xs == {'head0_e0': 60.48, 'head0_e2': 60.48, 'head0_e1': 336.96}
    taps = {tp['name']: tp['xy'] for tp in t['clock']['taps']}
    assert taps['head0_e0'] == [163.2, 120.0] and taps['g0'] == [290.0, 400.0]
    assert p['partition_types']['kv3_pc_v1']['hard_cores'][0]['origin_um'] == [17.28, 17.28]
    assert rep[0]['col12_street_um'] == 60.48


def test_band_listed_island_removed():
    p, rep, rs = ws.apply(_plan(), 43.2)
    kinds = sorted(r['kind'] for r in rs)
    assert kinds == ['die_clock_island', 'landing_band']
    assert p["partition_types"]["kv3_hg_v1"]["clock"]["die_islands_um"] == [[100.0, 100.0, 102.7, 100.81], [20.0, 280.0, 22.7, 280.81]]


def test_foreign_tap_fails_closed():
    p = _plan()
    p['partition_types']['kv3_hg_v1']['clock']['taps'][1]['xy'] = [250.0, 400.0]
    with pytest.raises(ValueError, match='clock_tap'):
        ws.apply(p, 43.2)


def test_bad_dx_and_outline():
    with pytest.raises(ValueError):
        ws.apply(_plan(), 40.0)
    with pytest.raises(ValueError):
        ws.apply(_plan(), 8.64 * 200)
