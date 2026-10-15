"""Diagnostic export must preserve exact endpoint lengths and missing-pin coverage."""
import gzip
import json
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import hbm_die_sta_plan as P


def test_export_preserves_missing_pins_and_actual_points(tmp_path, monkeypatch):
    insts = [SimpleNamespace(name=n, master=n, kind='tile', x=0, y=0, w=10, h=10, orient='R0')
             for n in ('a', 'b', 'c')]
    points = {('a', 'q'): (10, 20), ('b', 'd'): (40, 60)}
    monkeypatch.setattr(P.H, 'pin_points', lambda model, k: lambda *end: points.get(end))
    monkeypatch.setattr(P.H, 'REAL', {'a': {}})
    model = dict(insts=insts, buses=[('bus', 'data', 64, [('a', 'q'), ('b', 'd'), ('c', 'd')])])
    r = P.plan_dump(model, tmp_path)
    plan = json.load(gzip.open(tmp_path / 'plan.json.gz', 'rt'))
    assert r['hops'] == 2
    assert plan['hops'][0][-1] == 70.0
    assert plan['hops'][1][-1] is None
    assert json.loads((tmp_path / 'clock_delivery.json').read_text())['tiles']['a']['view'] == 'real'
