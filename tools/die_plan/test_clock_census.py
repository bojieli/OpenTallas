"""Clock census preserves fixed macro terminals and uniform type geometry."""
from types import SimpleNamespace
import pytest
import die_clock as D
import gen_phys


def test_hard_macro_clock_is_fixed_even_inside_buffer_keepout(monkeypatch):
    P = SimpleNamespace(parts={'phy': {'type': 'hard'}}, types={'hard': {
        'hard': True, 'outline_um': [100, 100],
        'clock': {'tap_um': [50, 4.32], 'keepouts_um': [[0, 0, 100, 100]]}}})
    P.to_die = lambda n, xy: (xy[0]+10, xy[1]+20)
    monkeypatch.setattr(gen_phys, 'clock_pins', lambda *a: pytest.fail('must not legalize macro terminal'))
    assert D.plan_taps(P) == [('phy', 'clk', 60.0, 24.32, 0.0)]


@pytest.mark.parametrize('xy', [None, [-1, 4], [101, 4], [float('nan'), 4]])
def test_hard_macro_terminal_requires_valid_explicit_geometry(xy):
    P=SimpleNamespace(parts={'phy': {'type': 'hard'}},types={'hard': {
        'hard':True, 'outline_um':[100,100], 'clock':{'tap_um':xy}}})
    with pytest.raises(ValueError,match='hard type hard'):
        D.plan_taps(P)


def test_soft_type_geometry_is_identical_across_instances(monkeypatch):
    P=SimpleNamespace(parts={'a':{'type':'soft'},'b':{'type':'soft'}},types={'soft':{}})
    P.to_die=lambda n,xy: (xy[0]+(100 if n=='b' else 0),xy[1])
    calls=[]
    monkeypatch.setattr(gen_phys,'clock_pins',lambda p,t: calls.append(t) or [('clk',10,20)])
    monkeypatch.setattr(gen_phys,'core_tap_pins',lambda p,t: [])
    assert D.plan_taps(P)==[('a','clk',10,20,0.),('b','clk',110,20,0.)]
    assert calls==['soft']
