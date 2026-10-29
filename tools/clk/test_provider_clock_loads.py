import copy
import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('PCL',Path(__file__).with_name('provider_clock_loads.py'))
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)

def fixture():
    graph=([dict(name='n1',drv='ck_parent',loads=['ck_child'])],{'root':dict(layer='M9',xy=[0,0])},{})
    row=dict(inst=r'start_provider/$flatten\u_st.$auto$ff',stage='r1',net='ck_n1',master='DFFLQNx1_ASAP7_75t_R',shapes_dbu=[['M1',100,200,118,272]])
    inventory=dict(dbu=1000,loads=[row])
    # A is the selected node-inverter input. It must remain on ck_n1.
    bindings=dict(ports={'t_st_r1__clk':dict(role='clock',net='ck_n1',native_endpoints=[dict(inst='ck_child',pin='A')])})
    return graph,inventory,bindings

def test_real_m1_added_without_changing_original_graph_or_input_tap():
    g,i,b=fixture();before=copy.deepcopy((g,i,b))
    nets,ports,ends,r=P.extend(*g,i,b)
    assert (g,i,b)==before
    assert nets[0]['drv']=='ck_parent' and nets[0]['loads']==['ck_child','port:provider_clk_00000']
    assert r['loads']==1 and r['added_cells']==r['cycles_added']==0
    ep=ends['provider_clk_00000'];assert ep['layer']=='M1' and ep['xy']==[.109,.236]
    assert ep['net']=='ck_n1' and ep['pin']=='CLK'
    text=P.rewrite_endpoint_tcl('$e addBTerm [BT provider_clk_00000]',ends)
    assert r'[IT {start_provider/$flatten\u_st.$auto$ff} {CLK}]' in text

@pytest.mark.parametrize('fault',['unknown_binding','missing_tree','duplicate','bad_pin'])
def test_no_fabricated_clock_or_pin(fault):
    g,i,b=fixture()
    if fault=='unknown_binding':i['loads'][0]['net']='ck_n2'
    if fault=='missing_tree':g[0][0]['name']='different'
    if fault=='duplicate':i['loads']*=2
    if fault=='bad_pin':i['loads'][0]['shapes_dbu']=[['M1',100,200,117,220]]
    with pytest.raises(ValueError):P.extend(*g,i,b)

def test_encoder_missing_endpoint_and_unsafe_name_fail_closed():
    g,i,b=fixture();_,_,ends,_=P.extend(*g,i,b)
    with pytest.raises(ValueError):P.rewrite_endpoint_tcl('',ends)
    with pytest.raises(ValueError):P.tcl_word('bad}name')


def test_native_prefixed_net_is_preserved():
    g,i,b=fixture();g[0][0]['name']='ck_n1'
    nets,_,_,report=P.extend(*g,i,b)
    assert nets[0]['name']=='ck_n1' and report['rows'][0]['raw_net']=='ck_n1'


def test_selected_access_must_remain_on_the_actual_m1_pin():
    g,i,b=fixture();i['loads'][0]['entry_xy_dbu']=[109,220]
    _,_,e,_=P.extend(*g,i,b);assert e['provider_clk_00000']['xy']==[.109,.220]
    i['loads'][0]['entry_xy_dbu']=[1000,1000]
    with pytest.raises(ValueError,match='outside actual M1'):P.extend(*g,i,b)
