from types import SimpleNamespace
import pytest
import schema as S
import taps
from placement_obstacles import placement_boxes
from test_density_taps import _plan,_no_pins


def reuse_type():
    return dict(outline_um=[250.,250.],contents=[dict(inst='reuse',origin_um=[40.,40.],outline_um=[100.,100.])],clock={})


def test_grid_legalizer_cannot_ignore_reuse_leaf_without_lef():
    t=reuse_type()
    assert S.placed_macro_boxes(t)=={}
    x,y=S.tap_clear(t,80.,80.)
    assert not (40.-8.64<x<140.+8.64 and 40.-8.64<y<140.+8.64)


def test_explicit_clock_endpoint_rejects_same_reuse_obstacle():
    t=reuse_type();t['clock'].update(taps=[dict(name='clk',xy=[80.,80.])])
    with pytest.raises(ValueError,match='outline/halo'):
        taps.explicit_tap_sites(SimpleNamespace(types={'t':t}),'t')


def test_split_container_clock_street_remains_open():
    t=dict(outline_um=[250.,250.],contents=[dict(inst='bank',origin_um=[0.,0.],outline_um=[250.,250.])],
           hard_cores=[dict(inst='bank_left',origin_um=[0.,0.],outline_um=[50.,250.]),dict(inst='bank_right',origin_um=[200.,0.],outline_um=[50.,250.])],
           clock=dict(taps=[dict(name='clk',xy=[125.,125.])]))
    assert set(placement_boxes(t))=={'bank_left','bank_right'}
    assert taps.explicit_tap_sites(SimpleNamespace(types={'t':t}),'t')==[('clk',125.,125.)]


def test_density_uses_real_reuse_body_without_dropping_sink_load(monkeypatch):
    _no_pins(monkeypatch)
    P=_plan([[100,350,10],[350,100,10],[350,500,10]],cores=[],tap_min_sinks=1,tap_radius_um=600)
    P.types['hd']['contents']=[dict(inst='reuse',origin_um=[300.,200.],outline_um=[100.,200.])]
    result=taps.density_taps(P,'hd')
    assert sum(row[3] for row in result)==30
    assert all(not (300-8.64<x<400+8.64 and 200-8.64<y<400+8.64) for _,x,y,_,_ in result)
