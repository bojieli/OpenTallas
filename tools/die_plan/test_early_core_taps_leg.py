"""S81-TYPES-7-CTAP 11-08 CORE-TAP-LATE: opt-in grid-leg rule and merge of existing core taps."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import early_core_taps as E
import cores


def core(inst, x, rise):
    return dict(inst=inst, module='m', lef='m.lef', lib='m.lib', origin_um=[x, 100.0], outline_um=[40.0, 40.0],
                _rise=rise)


def typ(cores_, taps=()):
    return dict(outline_um=[600.0, 400.0], hard_cores=list(cores_), clock=dict(core_taps='early', taps=list(taps)))


def patch(monkeypatch):
    monkeypatch.setattr(E, 'lef_pins', lambda path, macro=None: {})
    monkeypatch.setattr(E, 'resolve', lambda p, root=None: Path(p))
    monkeypatch.setattr(E, 'clock_pins', lambda c, root=None: {'clk': dict(rise=c['_rise'])})


OLD = dict(name='u_old.clk', kind='core', xy=[20.0, 20.0], insertion_ps=374.0)


def test_default_rule_and_replace_unchanged(monkeypatch):
    patch(monkeypatch)
    t = typ([core('u_ln', 100, 246.0), core('u_big', 300, 290.0)], [OLD])
    taps = E.add(t)
    assert [a['name'] for a in taps] == ['u_big.clk']
    assert t['clock']['taps'] == taps            # legacy replace kept as default


def test_leg_rule_adds_246_core_and_merges(monkeypatch):
    patch(monkeypatch)
    t = typ([core('u_ln', 100, 246.0), core('u_rxsb', 200, 165.0), core('u_big', 300, 290.0)], [OLD])
    taps = E.add(t, leg_ps=60.0, window_ps=20.0, merge=True)
    # 246 + 60 > 230 and 290 + 60 > 230 get early taps; 165 + 60 = 225 does not
    assert [a['name'] for a in taps] == ['u_ln.clk', 'u_big.clk']
    names = [a['name'] for a in t['clock']['taps']]
    assert names == ['u_old.clk', 'u_ln.clk', 'u_big.clk']   # clk_c0 stays the old tap
    assert cores.core_tap_of(t, 'u_old', 'clk') == 'clk_c0' and cores.core_tap_of(t, 'u_big', 'clk') == 'clk_c2'
    # second run is idempotent: no duplicate taps
    assert E.add(t, leg_ps=60.0, window_ps=20.0, merge=True) == []
    assert [a['name'] for a in t['clock']['taps']] == names


def test_merge_keeps_clearance_from_existing_taps(monkeypatch):
    patch(monkeypatch)
    t = typ([core('u_ln', 0.0, 246.0)], [dict(OLD, xy=[20.0, 100.0])])
    t['hard_cores'][0]['origin_um'] = [0.0, 100.0]
    taps = E.add(t, leg_ps=60.0, window_ps=20.0, merge=True)
    (x, y), (ox, oy) = taps[0]['xy'], OLD['xy'] and (20.0, 100.0)
    assert ((x - ox) ** 2 + (y - oy) ** 2) ** 0.5 >= 4.32 - 1e-9
