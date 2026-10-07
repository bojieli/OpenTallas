import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_s81_fulldie as F
import dsrom_s81_geometry_gate as G


def test_thin_bank_bundle_spacing_keeps_real_pins(monkeypatch):
    master = F.Q.Master('bank', 60.456, 6.456, 3, 'test')
    master.face('i', 512, 'S', 'M5', 30., 1)
    master.face('o', 512, 'N', 'M5', 30., 1)
    monkeypatch.setattr(F, 'GEOMETRY_FIX', False)
    real_before = F.pin_rects(master, 1, dict(i=512, o=512))
    bundled_before = F.pin_rects(master, 16, dict(i=32, o=32))
    monkeypatch.setattr(F, 'GEOMETRY_FIX', True)
    assert F.pin_rects(master, 1, dict(i=512, o=512)) == real_before
    after = F.pin_rects(master, 16, dict(i=32, o=32))
    def gap(rs):
        return min(r[2][1] for r in rs if r[0].startswith('o')) - max(
            r[2][3] for r in rs if r[0].startswith('i'))
    assert gap(bundled_before) < .024 * 16
    assert gap(after) >= .024 * 16
    assert [(p, l) for p, l, _ in bundled_before] == [(p, l) for p, l, _ in after]


@pytest.mark.parametrize('horizontal', [False, True])
def test_partial_trunk_model_matches_emitted_signature(monkeypatch, horizontal):
    monkeypatch.setattr(F, 'GEOMETRY_FIX', True)
    w, h = F.stn_dims([F.CRET + 2] * 3, horizontal)
    insts = [F.Inst(f's{j}', F.stn_master([F.CRET + 2] * 3, horizontal), 0, j*100, w, h)
             for j in range(3)]
    chains = SimpleNamespace(run=lambda *a, **kw: [(it, j*100, 100) for j, it in enumerate(insts)])
    result = F._run_multi(chains, 'r', [(0, 0), (0, 300)], [], [0, 100, 200], 3)
    for it, _, n in result:
        assert (it.w, it.h) == F.stn_dims([F.CRET + 2] * n, horizontal)
        assert it.w <= w and it.h <= h


def test_snap_axis_uses_site_and_track_lattice():
    assert G.snap_axis(24, 54, [(48, {0})]) == 0
    assert G.snap_axis(432 + 24, 54, [(48, {0})]) == 432
    assert G.snap_axis(216, 54, [(48, {0})]) == 0  # same tie break as Tcl
    with pytest.raises(ValueError):
        G.snap_axis(0, 54, [(48, {1})])


@pytest.mark.parametrize('orient', ['R0', 'MX', 'MY', 'R180'])
def test_snap_model_detects_emitted_footprint_overlap(monkeypatch, orient):
    monkeypatch.setattr(F, 'REAL_FILES', {})
    master = F.Q.Master('m', 1.704, 2.136, 3, 'test')
    # Model claims a small footprint; the actual LEF overlaps its neighbour.
    m = dict(insts=[F.Inst('a', 'm', 0, 0, .4, 2.136, orient),
                    F.Inst('b', 'm', .864, 0, .4, 2.136, orient)])
    report = G.snap_model(m, {'m': master}, {'m': [('i', 'M5', (0., 0., .024, .192))]})
    assert len(report['dimension_mismatches']) == 2
    assert report['legality']['overlaps'] == 1
    assert report['track_errors'] == []
