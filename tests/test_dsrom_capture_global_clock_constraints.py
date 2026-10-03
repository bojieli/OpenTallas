import sys,copy,json
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_global_clock_constraints as G

def toy():
    return dict(shard=0,node_count=2,sites=[dict(bbox_DBU=[0,0,378,270],orientation='R0'),dict(bbox_DBU=[1000,0,1378,270],orientation='R0')],RC_fF_per_um={'M8':.103962,'M9':.0928446},tasks=[dict(node_ids=[0,1],source_contact_DBU=[0,135],sink_contact_DBU=[2000,135],first_metal_budget_fF=.3)])

def test_full_joint_sat_with_independent_edge_audit():
    p=toy();s,v=G.encoding([p]);assert s.check()==G.z3.sat;m=s.model();a=[dict(node=i,**p['sites'][m.eval(x).as_long()]) for i,x in enumerate(v[0])]
    assert G.audit_assignment(p,a)['all_enclosed_contact_edges_checked']==3

def test_impossible_final_hop_not_firsthop_pass():
    p=toy();p['tasks'][0]['sink_contact_DBU']=[100000,135];s,_=G.encoding([p]);assert s.check()==G.z3.unsat

def test_global_distinct_not_per_branch_only():
    p=toy();p['node_count']=3;s,_=G.encoding([p]);assert s.check()==G.z3.unsat

def test_contact_erosion_rejects_optimistic_thin_pin():
    pin={'point_DBU':[5,5],'literal_rectangles':[{'layer':'M1','bbox_DBU':[0,0,100,18]}]}
    with pytest.raises(ValueError):G.contact(pin,[-9,-11,9,11])
    pin['literal_rectangles'].append({'layer':'M1','bbox_DBU':[0,0,18,40]});assert G.contact(pin,[-9,-11,9,11])==[9,11]

def test_complete_input_counts_include_padding():
    m=json.loads((G.BASE/'model.json').read_text());assert [m['cases'][str(s)]['nodes'] for s in (0,1)]==[38383,30231]
    for s in (0,1):
        p=G.load(G.BASE/f'shard{s}_problem.json.gz')
        assert sum(len(t['node_ids']) for t in p['tasks'])==p['node_count']
        assert sum(t['pad_count'] for t in p['tasks'])>0
        assert any(not t['relay_count'] and t['node_ids'] for t in p['tasks'])
        assert p['upstream_root_driver'] is None and p['supply_current_provider'] is None
    assert not m['locked_first_hops'] and not m['physical_build_admitted']

@pytest.mark.parametrize('kind',['missing','duplicate','wrong_contact'])
def test_independent_rejection(kind):
    p=toy();a=[dict(node=i,**p['sites'][i]) for i in range(2)]
    if kind=='missing':a.pop()
    elif kind=='duplicate':a[1]=dict(a[0],node=1)
    else:p['tasks'][0]['sink_contact_DBU']=[100000,135]
    with pytest.raises(ValueError):G.audit_assignment(p,a)
