import copy
from types import SimpleNamespace
import pytest
import start_provider_plan as SP


def fixture():
    pin=dict(name='cland_tstart_in',xy_um=[100,0])
    p=SimpleNamespace(ptype=lambda n:dict(clock=dict(landing_contract=dict(pins=[pin]))),to_die=lambda n,q:q,
       clock=dict(landing_network=dict(start_tree=dict(uses=[dict(part='real',pin='cland_tstart_in',net='pst_r')]))))
    nodes=[dict(id='a',region='st:a',rect_um=[0,0,4,1],clock_node='ba',clock_node_xy_um=[0,0],clock_port='ca',flops=3,parent=None,root=True),
           dict(id='b',region='st:b',rect_um=[50,0,54,1],clock_node='bb',clock_node_xy_um=[50,0],clock_port='cb',flops=3,parent='st:a',root=False)]
    def edge(**kw):return dict(max_hop_um=405,source_registered=True,capture_registered=True,**kw)
    edges=[edge(src_stage='a',dst_stage='b',src_rect_um=nodes[0]['rect_um'],dst_rect_um=nodes[1]['rect_um']),
           edge(src_stage='b',part='real',pin='cland_tstart_in',net='pst_r',src_rect_um=nodes[1]['rect_um'],dst_rect_um=[100,0,100,0])]
    return p,dict(form='emitted_start_stage_rows',nodes=nodes,edges=edges)


def test_complete_physical_provider_checks_actual_row_envelope():
    p,c=fixture();r=SP.check(p,c)
    assert not r['errors'] and r['stages']==2 and r['edges']==2 and r['max_hop_um']==55


@pytest.mark.parametrize('mutant',['gap','missing','boundary','fake_rect','wrong_parent','unregistered','reach_waiver'])
def test_provider_contract_fails_actual_geometry_and_graph_mutants(mutant):
    p,c=fixture()
    if mutant=='gap':c['nodes'][1]['rect_um'][:]=[450,0,454,1]
    if mutant=='missing':c['edges'].pop(0)
    if mutant=='boundary':c['edges'][-1]['net']='pst_wrong'
    if mutant=='fake_rect':c['edges'][-1]['dst_rect_um']=[55,0,55,0]
    if mutant=='wrong_parent':c['nodes'][1]['parent']='st:b'
    if mutant=='unregistered':c['edges'][0]['source_registered']=False
    if mutant=='reach_waiver':c['edges'][0]['max_hop_um']=500
    assert SP.check(p,c)['errors']


def relay_fixture():
    """a -> b at 460 um, carried by one REACH relay (R-REACH-1): a -> b#rl1 -> b"""
    p,c=fixture()
    c['nodes'][1]['rect_um'][:]=[460,0,464,1]
    c['edges'][0]['dst_rect_um']=c['nodes'][1]['rect_um'];c['edges'][-1]['src_rect_um']=c['nodes'][1]['rect_um']
    p.ptype=lambda n:dict(clock=dict(landing_contract=dict(pins=[dict(name='cland_tstart_in',xy_um=[500,0])])))
    c['edges'][-1]['dst_rect_um']=[500,0,500,0]
    rl=dict(id='b_rl1',region='st:b#rl1',kind='relay',relay_for='st:b',rect_um=[230,0,231.08,0.27],clock_node='bb',
            clock_node_xy_um=[229,0],clock_port='t_st_b_rl1__clk',flops=1,parent='st:a',root=False)
    c['nodes'].append(rl);c['nodes'][1].update(fed_by='st:b#rl1',relay_cycles=1)
    e0=c['edges'][0]
    c['edges'][0]=dict(e0,dst_stage='b_rl1',dst_rect_um=rl['rect_um'])
    c['edges'].insert(1,dict(e0,src_stage='b_rl1',src_rect_um=rl['rect_um']))
    return p,c


def test_relay_chain_carries_long_parent_edge():
    p,c=relay_fixture();r=SP.check(p,c)
    assert not r['errors'] and r['relays']==1 and r['max_hop_um']<=405
    p,c=relay_fixture();c['nodes'].pop();c['nodes'][1].pop('fed_by');c['nodes'][1].pop('relay_cycles')
    c['edges'][0]=dict(c['edges'][0],dst_stage='b',dst_rect_um=c['nodes'][1]['rect_um']);c['edges'].pop(1)
    assert any('exceeds405' in e for e in SP.check(p,c)['errors'])      # without the relay the hop fails


@pytest.mark.parametrize('mutant',['cycles','relay_for','orphan','no_fed_by','relay_root'])
def test_relay_chain_mutants_fail(mutant):
    p,c=relay_fixture()
    if mutant=='cycles':c['nodes'][1]['relay_cycles']=2
    if mutant=='relay_for':c['nodes'][2]['relay_for']='st:a'
    if mutant=='orphan':c['nodes'].append(dict(c['nodes'][2],id='x_rl1',region='st:x#rl1'))
    if mutant=='no_fed_by':c['nodes'][1].pop('fed_by')
    if mutant=='relay_root':c['nodes'][2]['root']=True
    assert SP.check(p,c)['errors']
