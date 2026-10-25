import importlib.util
from pathlib import Path
import pytest
spec = importlib.util.spec_from_file_location('htree_clock_hard_test', Path(__file__).with_name('htree_clock.py'))
H = importlib.util.module_from_spec(spec)
spec.loader.exec_module(H)

class Plan:
    parts = {'phy': {'type': 'PHY'}}
    def __init__(self, xy):
        self.t = {'hard': True, 'outline_um': [5000, 1000], 'clock': {'keepouts_um': [[0, 0, 5000, 1000]]}}
        if xy is not None:
            self.t['clock']['tap_um'] = xy
    def ptype(self, name):
        return self.t
    def to_die(self, name, xy):
        return (xy[0]+100, xy[1]+200)

def test_fixed_macro_terminal_bypasses_stdcell_grid(monkeypatch):
    def forbidden(*args):
        raise AssertionError('hard PHY terminal was treated as a stdcell site')
    monkeypatch.setattr(H.gen_phys, 'tap_points', forbidden)
    assert H.plan_taps(Plan([4250.88, 4.32])) == [('phy', 'clk', 4350.88, 204.32)]

@pytest.mark.parametrize('xy', [None, [-1, 5], [10, 1001], [float('nan'), 3]])
def test_bad_macro_terminal_fails_closed(xy):
    with pytest.raises(ValueError, match='clock.tap_um'):
        H.plan_taps(Plan(xy))

def test_soft_type_still_uses_legal_grid(monkeypatch):
    p = Plan([1, 2]); p.t['hard'] = False
    monkeypatch.setattr(H.gen_phys, 'tap_points', lambda *a: ([3, 4], [5, 6]))
    monkeypatch.setattr(H.gen_phys, 'clock_pins', lambda *a: [('clk', 3, 4), ('clk_t1', 9, 10)])
    assert H.plan_taps(p) == [('phy', 'clk', 103, 204), ('phy', 'clk_t1', 109, 210)]


def test_hard_assembly_retains_grid_and_declared_core_taps(monkeypatch):
    p = Plan([1, 2])
    p.t['hard_cores'] = [{'inst': 'core0'}]
    p.t['clock']['taps'] = [{'xy': [7, 8]}]
    monkeypatch.setattr(H.gen_phys, 'tap_points', lambda *a: ([3, 4], [5, 6]))
    monkeypatch.setattr(H.gen_phys, 'clock_pins', lambda *a: [('clk', 3, 4), ('clk_t1', 9, 10)])
    assert H.plan_taps(p) == [('phy', 'clk', 103, 204), ('phy', 'clk_t1', 109, 210), ('phy', 'declared_0', 107, 208)]
