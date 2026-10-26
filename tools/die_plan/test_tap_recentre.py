"""PATH-KV-SYSC2 (GEOM F2): clock.tap_recentre 'sinks' re-centres displaced R4 taps on their sinks and drops dead ones."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S
import taps as T


class _P:
    def __init__(self, t):
        self.types = {"x": t}
        self.budgets = {}


def _plan(recentre, sinks):
    t = dict(outline_um=[1200.0, 400.0],
             contents=[dict(inst="u_phy", lef="phy.lef", origin_um=[400.0, 10.0], outline_um=[400.0, 380.0])],
             clock=dict(keepouts_um=[[390.0, 0.0, 810.0, 400.0]], sink_sites_um=sinks))
    if recentre:
        t["clock"]["tap_recentre"] = "sinks"
    return _P(t)


def test_default_grid_unchanged(monkeypatch):
    monkeypatch.setattr(T, "planned_sinks", lambda P, tn, bit_sites=False: [])
    T._CACHE.clear()
    g = S.tap_grid(_plan(False, [[820.0, 300.0, 50]]), "x")
    assert [n for n, _, _ in g] == ["clk", "clk_t1", "clk_t2"]
    assert g[0][1:] == (200.0, 200.0) and g[2][1:] == (1000.0, 200.0)
    assert g[1][1] < 390 - 8.6 or g[1][1] > 810 + 8.6        # pushed to the keepout edge (old behaviour)


def test_displaced_tap_moves_to_its_sinks(monkeypatch):
    monkeypatch.setattr(T, "planned_sinks", lambda P, tn, bit_sites=False: [])
    T._CACHE.clear()
    g = S.tap_grid(_plan(True, [[370.0, 380.0, 50], [366.0, 376.0, 50]]), "x")
    assert len(g) == 3
    x, y = g[1][1:]
    assert x <= 390 - 8.64 and abs(x - 368) < 3 and abs(y - 378) < 3   # on its sink cluster, clear of the keepout


def test_dead_tap_dropped(monkeypatch):
    monkeypatch.setattr(T, "planned_sinks", lambda P, tn, bit_sites=False: [])
    T._CACHE.clear()
    g = S.tap_grid(_plan(True, [[100.0, 100.0, 5], [1100.0, 100.0, 5]]), "x")
    assert [n for n, _, _ in g] == ["clk", "clk_t1"]          # the PHY cell's tap had no sink and no free area
    assert {(x, y) for _, x, y in g} == {(200.0, 200.0), (1000.0, 200.0)}
