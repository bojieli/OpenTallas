"""Regression for the real face-overlap failure at a crowded upper edge."""
import importlib.util
from pathlib import Path

sp = importlib.util.spec_from_file_location('qc_plan_align', Path(__file__).with_name('gen_plan.py'))
g = importlib.util.module_from_spec(sp)
sp.loader.exec_module(g)

class Adjacent:
    parts = {'a': {'orient': 'R0'}, 'b': {'orient': 'R0'}}
    def rect(self, n):
        return (0, 0, 10, 100) if n == 'a' else (10, 0, 20, 100)

def test_upper_edge_legalizer(monkeypatch):
    monkeypatch.setattr(g, 'EDGE', 2)
    monkeypatch.setattr(g, 'GAP', 2)
    monkeypatch.setattr(g, 'qlen', lambda width, *a, **k: width)
    prs = [{'id': n, 'width': 19, 'layers': ['M6'], 'window_um': [0, 1]} for n in ['p', 'q', 'r']]
    assert g._lay_aligned(Adjacent(), 'a', 'b', prs, {'p': (80, 0), 'q': (90, 0), 'r': (96, 0)})
    win = [p['window_um'] for p in prs]
    assert win[0][0] >= 2 and win[-1][1] <= 98
    assert all(a[1] + 2 <= b[0] for a, b in zip(win, win[1:]))

def test_impossible_face_does_not_rewrite(monkeypatch):
    monkeypatch.setattr(g, 'EDGE', 2)
    monkeypatch.setattr(g, 'GAP', 2)
    monkeypatch.setattr(g, 'qlen', lambda width, *a, **k: width)
    prs = [{'id': n, 'width': 59, 'layers': ['M6'], 'window_um': [3, 4]} for n in ['p', 'q']]
    assert not g._lay_aligned(Adjacent(), 'a', 'b', prs, {'p': (80, 0), 'q': (90, 0)})
    assert all(p['window_um'] == [3, 4] for p in prs)
