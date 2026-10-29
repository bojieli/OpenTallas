from types import SimpleNamespace
import pytest
import gen_phys as GP
import die_trial as DT


def plan(heights=None):
    return SimpleNamespace(name='p',layer_budget={'partition_signal_max':'M7'},
        types={'t':dict(module='m',outline_um=[100,100],clock={
            **({'tap_pin_heights_um':heights} if heights is not None else {})})})


def test_default_and_only_declared_clock_pin_changes():
    p=plan({'clk':.8})
    assert GP.tap_pin_height(plan(),'t','clk')==.768
    assert GP.tap_pin_height(p,'t','clk')==.8
    assert GP.tap_pin_height(p,'t','arst_n')==.768


@pytest.mark.parametrize('value',[.76,float('nan'),float('inf')])
def test_shrink_or_nonfinite_is_not_a_valid_access_fix(value):
    with pytest.raises(ValueError):GP.tap_pin_height(plan({'clk':value}),'t','clk')


def test_actual_io_and_abstract_emit_identical_extended_metal(monkeypatch):
    p=plan({'clk':.8})
    monkeypatch.setattr(GP,'tap_pins',lambda p,t:[('clk',10,20),('arst_n',30,40)])
    monkeypatch.setattr(GP,'type_pins',lambda p,t:[])
    monkeypatch.setattr(GP,'reset_out_pins',lambda p,t:[])
    monkeypatch.setattr(GP,'strap_pin_sites',lambda p,t:[])
    text=GP.io_tcl(p,'t',[])
    assert '-pin_name clk -layer M7 -location {10.0000 20.0000} -pin_size {0.0320 0.8000}' in text
    assert '-pin_name arst_n -layer M7 -location {30.0000 40.0000} -pin_size {0.0320 0.7680}' in text
    lef,_=DT.abstract_lef(p,'t')
    assert 'RECT 9.9840 19.6000 10.0160 20.4000' in lef
