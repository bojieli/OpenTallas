"""Clock budget consumer must use the physically distributed FT bit sites."""
from types import SimpleNamespace
import pytest
import gen_phys
import taps


def distributed_bank(monkeypatch):
    pins=[('ft_i',0,'M4',0.,100.,'W'),('ft_i',1,'M4',0.,110.,'W'),
          ('ft_o',0,'M4',1000.,100.,'E'),('ft_o',1,'M4',1000.,110.,'E')]
    monkeypatch.setattr(gen_phys,'type_pins',lambda P,tn:pins)
    typ=dict(module='m',outline_um=[1000.,300.],
             ft_slots=[dict(name='ft',stations=2,in_face='W',out_face='E',
                            bit_site_cell_um=[2.,2.],bit_sites_um=[[[199.,99.],[799.,99.]]])],
             clock=dict(tap_mode='explicit',tap_max_sinks=3,tap_radius_um=220.,
                        taps=[dict(name='clk',xy=[200.,100.]),dict(name='clk_t1',xy=[800.,100.])]))
    return SimpleNamespace(types={'t':typ})


def test_actual_distributed_sites_fill_taps_nominal_centres_leave_empty(monkeypatch):
    P=distributed_bank(monkeypatch)
    nominal=[(x,y,1.)for x,y,_ in taps.planned_sinks(P,'t',bit_sites=False)]
    actual=taps.sink_sites(P,'t')
    assert (200.,100.,1.)in actual and (800.,100.,1.)in actual
    assert (800.,100.,1.)not in nominal
    endpoints=[('clk',200.,100.),('clk_t1',800.,100.)]
    nominal_load,nominal_far,_=taps.assign(endpoints,nominal,3,220.,max_distance_um=220.)
    assert nominal_load[1]==0 and max(nominal_far)>220.
    qualified=taps.explicit_taps(P,'t')
    assert [x[3]for x in qualified]==[3.,1.]
    assert max(x[4]for x in qualified)<=220.


def test_actual_bit_outside_reach_still_fails_no_nominal_fallback(monkeypatch):
    P=distributed_bank(monkeypatch)
    P.types['t']['ft_slots'][0]['bit_sites_um'][0][1]=[499.,99.]
    with pytest.raises(ValueError,match='radius='):
        taps.explicit_taps(P,'t')
