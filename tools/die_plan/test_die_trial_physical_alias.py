from types import SimpleNamespace
import pytest
import die_trial as D


def plan():
    return SimpleNamespace(name='die',types={
        'nw':dict(module='hub',outline_um=[20,30],hard_cores=[dict(origin_um=[1,2],outline_um=[3,4],obs_max='M5')]),
        'ne':dict(module='hub',outline_um=[40,50],hard_cores=[dict(origin_um=[10,20],outline_um=[4,5],obs_max='M7')]),
        'other':dict(module='other',outline_um=[1,2])},
        parts={'NW_hub':dict(type='nw'),'NE_hub':dict(type='ne'),'x':dict(type='other')},
        layer_budget={'partition_signal_max':'M7'})


def test_shared_rtl_types_have_distinct_physical_masters(monkeypatch):
    P=plan()
    monkeypatch.setattr(D.gen_phys,'type_pins',lambda *a: [])
    monkeypatch.setattr(D.gen_phys,'tap_pins',lambda *a: [])
    monkeypatch.setattr(D,'lef_top_layer',lambda *a: None)
    names=D.standin_module_names(P)
    a,_=D.abstract_lef(P,'nw',module_name=names['nw'])
    b,_=D.abstract_lef(P,'ne',module_name=names['ne'])
    assert 'MACRO hub__nw' in a and 'SIZE 20.0000 BY 30.0000' in a
    assert 'MACRO hub__ne' in b and 'SIZE 40.0000 BY 50.0000' in b
    assert 'RECT 1.0000 2.0000 4.0000 6.0000' in a
    assert 'RECT 10.0000 20.0000 14.0000 25.0000' in b
    top,n=D.route_netlist(P,{tn:{} for tn in P.types})
    assert 'hub__nw NW_hub (' in top and 'hub__ne NE_hub (' in top
    assert 'other x (' in top
    # Unique module's emitted abstract remains byte-identical.
    assert D.abstract_lef(P,'other')[0] == D.abstract_lef(P,'other',module_name=names['other'])[0]


def test_closed_lef_alias_preserves_geometry_and_pin_names():
    lef='MACRO hub\n SIZE 10 BY 20 ;\n PIN hub_clk\n END hub_clk\nEND hub\nEND LIBRARY\n'
    alias=D.retarget_lef_macro(lef,'hub','hub__nw')
    assert alias.replace('hub__nw','hub') == lef
    with pytest.raises(ValueError,match='expected one MACRO'):
        D.retarget_lef_macro(lef,'absent','new')
    with pytest.raises(ValueError,match='expected one END'):
        D.retarget_lef_macro('MACRO hub\nEND other\n','hub','new')
