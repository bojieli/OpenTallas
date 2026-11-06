"""Explicit registered U-turns preserve distinct pin interfaces and station latency."""
import copy
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema
import gen_rtl


def fixture():
    root = Path(__file__).resolve().parent
    p = json.loads((root / 'examples/tiny_plan.json').read_text())
    t = copy.deepcopy(next(t for t in p['partition_types'].values() if t.get('ft_slots')))
    t['module'] = 'turn_fixture'
    s = t['ft_slots'][0]
    t['ft_slots'] = [s]
    s.update(in_face='N', out_face='N', in_window_um=[100,120], out_window_um=[300,320],
             in_layers=['M7'], out_layers=['M7'])
    p['partition_types']['turn_fixture'] = t
    return p, s


def test_same_face_still_needs_explicit_turnaround():
    p, s = fixture()
    assert any('in_face == out_face' in e for e in schema.validate(p))
    s['turnaround'] = False
    assert any('in_face == out_face' in e for e in schema.validate(p))


def test_explicit_disjoint_turnaround_valid():
    p, s = fixture()
    s['turnaround'] = True
    assert schema.validate(p) == []


def test_ambiguous_turnaround_windows_refused():
    p, s = fixture()
    s['turnaround'] = True
    s['out_window_um'] = [110,130]
    assert any('turnaround needs disjoint' in e for e in schema.validate(p))
    del s['out_window_um']
    assert any('turnaround needs disjoint' in e for e in schema.validate(p))


def test_turnaround_keeps_distinct_rtl_interfaces(tmp_path):
    p, s = fixture()
    s['turnaround'] = True
    before = copy.deepcopy(s)
    gen_rtl.write_rtl(p, str(tmp_path), types=['turn_fixture'])
    sv = (tmp_path / 'turn_fixture.sv').read_text()
    assert 'fx_i' in sv and 'fx_o' in sv
    assert sum(f'u_ft_fx_s{i} ' in sv for i in range(s.get('stations',1))) == s.get('stations',1)
    assert '.d(fx_i[' in sv and '.q(fx_o[' in sv
    assert s == before
