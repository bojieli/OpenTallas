import copy
from clock_landing_plan import clear_generated_landing_infra


def test_recompose_replaces_generated_clocks_and_start_pins_without_dropping_native_clock():
    raw={'clock':{'landing_network':{'edges':['old']}},'partition_types':{'T':{
      'clock':{'edge_clocks':[{'port':'native_clk'},{'port':'fclk_in_x','tap_um':[1,2]},{'port':'fclk_in_x','tap_um':[3,4]}],
               'landing_contract':{'pins':[{'name':'fclk_in_x'},{'name':'cland_tstart_in'}]}},
      'buses':[{'name':'payload'},{'name':'cland_tstart_in'}]}}}
    clear_generated_landing_infra(raw)
    t=raw['partition_types']['T']
    assert t['clock']=={'edge_clocks':[{'port':'native_clk'}]}
    assert t['buses']==[{'name':'payload'}]
    assert raw['clock']=={}
    once=copy.deepcopy(raw);clear_generated_landing_infra(raw);assert raw==once


def test_first_compose_preserves_native_inputs():
    raw={'clock':{},'partition_types':{'T':{'clock':{'edge_clocks':[{'port':'native_clk'}]},'buses':[{'name':'payload'}]}}}
    old=copy.deepcopy(raw);clear_generated_landing_infra(raw);assert raw==old
