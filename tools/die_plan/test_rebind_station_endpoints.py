import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import rebind_station_endpoints as R


def fixture(tmp_path,cores,ports=None,old=None,cc=None):
    (tmp_path/'pins.json').write_text(json.dumps(ports or [dict(name='d[0]',x=.019,y=10),dict(name='d[1]',x=.019,y=14)]))
    rr=R.Resolver.__new__(R.Resolver);rr.pd=tmp_path;rr.cache={};rr.types={'t':dict(hard_cores=cores)};rr.old=old;rr.cc={'t':cc or {}};rr.changed={'t':{h['inst'] for h in cores}}
    return rr


def hc(inst='u_a',orient='R0',x=0):return dict(inst=inst,origin_um=[x,0],outline_um=[100,50],orient=orient,pins_file='pins.json')


def test_longest_hierarchical_instance_and_real_physical_group(tmp_path):
    h=hc('u_a.child',orient='MY',x=200);h['pin_select']={'in':'d'};rr=fixture(tmp_path,[hc('u_a'),h])
    s=dict(launch='u_a.child.in',capture='none',from_um=[200,12],to_um=[0,0])
    xy,d=rr.resolve('t',s,0,0)
    assert xy==[299.981,12] and d['core']=='u_a.child' and d['physical_group']=='d'
    with pytest.raises(ValueError,match='no actual pins'):rr.group(h,'missing')


def test_segment_selects_actual_replica_not_nearest(tmp_path):
    rr=fixture(tmp_path,[hc('u_a__q0'),hc('u_a__q1',x=200)])
    s=dict(launch='u_a.d',capture='none',from_um=[0,12],to_um=[0,0],r9_segments=[1,0])
    xy,d=rr.resolve('t',s,0,0)
    assert xy==[200.019,12] and d['core']=='u_a__q1'
    s['r9_segments']=[2,0]
    with pytest.raises(ValueError,match='no matching actual replica'):rr.resolve('t',s,0,0)


def test_nearest_baseline_and_tie_refusal(tmp_path):
    rr=fixture(tmp_path,[hc('u_a__q0'),hc('u_a__q1',x=200)])
    s=dict(launch='u_a.d',capture='none',from_um=[260,12],to_um=[0,0])
    assert rr.resolve('t',s,0,0)[1]['core']=='u_a__q1'
    s['from_um']=[150,12]
    with pytest.raises(ValueError,match='tied'):rr.resolve('t',s,0,0)


def test_bare_peer_refused_even_when_heuristic_peer_graph_is_unique(tmp_path):
    rr=fixture(tmp_path,[hc('u_a'),hc('u_b',x=200)],cc={'u_b':{'d':['core:u_a'],'other':['core:u_a']}})
    s=dict(launch='u_a.d',capture='u_b',from_um=[0,12],to_um=[200,12])
    with pytest.raises(ValueError,match='2 peer-graph diagnostic candidate ports'):rr.resolve('t',s,1,0)
    rr.cc={'t':{'u_b':{'d':['core:u_a']}}}
    with pytest.raises(ValueError,match='1 peer-graph diagnostic candidate ports'):rr.resolve('t',s,1,0)
    assert rr.resolve('t',s,1,0,dict(core='u_b',ports=['d']))[1]['method']=='explicit_bundle'


def test_multiface_port_refuses_average_inside_macro(tmp_path):
    rr=fixture(tmp_path,[hc()],ports=[dict(name='d[0]',x=.019,y=10),dict(name='d[1]',x=99.981,y=10)])
    with pytest.raises(ValueError,match='spans faces'):rr.group(hc(),'d')
    assert rr.group(hc(),'d[1]')[0]==[99.981,10]


def test_unchanged_baseline_soft_anchor_remains_declared(tmp_path):
    rr=fixture(tmp_path,[hc()],old={'partition_types':{'t':dict(hard_cores=[hc()])}})
    s=dict(launch='soft_legacy',capture='u_a.d',from_um=[120,20],to_um=[0,12])
    xy,d=rr.resolve('t',s,0,0)
    assert xy==[120,20] and d['method']=='unchanged_baseline_anchor'
    rr.old=None
    with pytest.raises(ValueError,match='no actual hard core'):rr.resolve('t',s,0,0)


def test_wide_group_adds_priced_signal_guard_instead_of_centre_only_pass():
    t=dict(outline_um=[1200,1200],hard_cores=[dict(origin_um=[0,0],outline_um=[100,600])])
    s=dict(from_um=[99.981,300],to_um=[700,300],regs_um=[[400,300]])
    row=dict(endpoints=[dict(field='launch',pin_group_extremes_um=[[99.981,0],[99.981,600]])])
    fixed,receipt=R.guard_endpoint_groups(t,s,row,405)
    assert fixed is not None and receipt['guard_added_cycles']==1 and len(fixed['regs_um'])==2
    assert receipt['max_endpoint_hop_um']<=405 and s['regs_um']==[[400,300]]


def test_group_too_wide_requires_split():
    t=dict(outline_um=[1200,1200],hard_cores=[dict(origin_um=[0,0],outline_um=[100,900])])
    s=dict(from_um=[99.981,450],to_um=[700,450],regs_um=[[400,450]])
    row=dict(endpoints=[dict(field='launch',pin_group_extremes_um=[[99.981,0],[99.981,900]])])
    fixed,receipt=R.guard_endpoint_groups(t,s,row,405)
    assert fixed is None and 'split/replan' in receipt['reason']
