"""Physical landing and count pins must be counted by the normal exact port gate."""
from types import SimpleNamespace
import pytest
import gen_phys as G
import port_bind_gate as B


def vehicle():
    return SimpleNamespace(types={'t':dict(clock=dict(landing_contract=dict(pins=[
        dict(name='fclk_in_x',dir='in',kind='clock',layer='M7',xy_um=[1,2]),
        dict(name='fclk_out_x',dir='out',kind='clock',layer='M7',xy_um=[3,2]),
        dict(name='cland_up_ready_x',dir='out',kind='ctl',layer='M7',xy_um=[3,3])])),
        count_straps=[dict(name='strap_ca_k_x',width=2,layer='M5',sites_um=[[1,1],[2,1]])])})


def test_landing_and_physical_count_pins_pass_exact_gate(monkeypatch):
    p=vehicle()
    monkeypatch.setattr(G,'tap_pins',lambda *_:[('clk',1,4),('fclk_in_x',1,2)])
    monkeypatch.setattr(G,'reset_out_pins',lambda *_:[])
    pins=G.port_bind_pin_records(p,'t',[])
    assert len(pins)==6  # forwarded input also in tap inventory, counted once
    text=('module top(clk,fclk_in_x,strap_ca_k_x,fclk_out_x,cland_up_ready_x);\n'
          'input clk;\ninput fclk_in_x;\ninput [1:0] strap_ca_k_x;\n'
          'output fclk_out_x;\noutput cland_up_ready_x;\nendmodule\n')
    assert B.check(text,'top',pins,['strap_ca_k_x'])['verdict']=='PASS'
    old=[v for v in pins if not v['bus'].startswith(('cland_','strap_')) and v['bus']!='fclk_out_x']
    assert B.check(text,'top',old)['verdict']=='FAIL'
    rogue=text.replace('output fclk_out_x;', 'output rogue;\noutput fclk_out_x;')
    assert B.check(rogue,'top',pins,['strap_ca_k_x'])['extra']==1


def test_count_sites_require_exact_width():
    p=vehicle(); p.types['t']['count_straps'][0]['sites_um'].pop()
    with pytest.raises(ValueError,match='exactly 2'):
        G.strap_pin_sites(p,'t')
