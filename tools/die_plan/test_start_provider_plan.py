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
