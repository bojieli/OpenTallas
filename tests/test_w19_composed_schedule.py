import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_composed_schedule as W


def toy():
    return dict(graph_sha256='toy',programme_operations=2,nodes=[
        dict(id='a',cost_key='a',resource='simt',depends_on=[]),
        dict(id='b',cost_key='b',resource='simt',depends_on=[])])


def costs():
    c=dict(cycles=9,clock_hz=900000000,resource_units=1,
           finite_waits_included=True,exact_gpu_lowering_bound=True,
           evidence=dict(path='test-only-fixture',sha256='0'*64))
    return dict(graph_sha256='toy',scope='GPU_SIMT_FULL_TOKEN_MODEL',
                resource_capacities={'simt':1},node_costs={'a':c,'b':copy.deepcopy(c)})


def test_missing_kernel_fails_closed():
    r=W.schedule(toy(),{})
    assert r['status'].startswith('BLOCKED') and r['full_token_cycles'] is None
    assert r['full_token_time_ps'] is None and not r['connected_rate_credit']


def test_finite_shared_resource_waits():
    r=W.schedule(toy(),costs())
    assert r['timeline'][1]['start_ps']=='10000'
    assert r['modeled_token_time_ps']=='20000' and r['full_token_cycles'] is None


def test_capacity_two_allows_independent_work():
    c=costs();c['resource_capacities']['simt']=2
    assert W.schedule(toy(),c)['modeled_token_time_ps']=='10000'


@pytest.mark.parametrize('field,value',[('finite_waits_included',False),('exact_gpu_lowering_bound',False),('resource_units',2)])
def test_unbound_or_overcapacity_rejected(field,value):
    c=costs();c['node_costs']['a'][field]=value
    with pytest.raises(ValueError):W.schedule(toy(),c)


def test_unproved_free_service_rejected():
    c=costs();c['node_costs']['a']['cycles']=0
    with pytest.raises(ValueError):W.schedule(toy(),c)


def test_wrong_graph_and_hcp_scope_rejected():
    c=costs();c['graph_sha256']='different'
    with pytest.raises(ValueError):W.schedule(toy(),c)
    c=costs();c['scope']='HCP_REFERENCE'
    with pytest.raises(ValueError):W.schedule(toy(),c)


def test_actual_full_program_state_fences_and_head():
    root=Path(__file__).resolve().parents[1]
    p=json.loads(subprocess.check_output(['git','show',f'{W.PIN}:{W.PROGRAM}'],cwd=root))
    g=W.graph(p,{})
    assert g['programme_operations']==2213
    assert len([o for o in g['operations'] if o.get('fn')=='hc_mixes'])==80
    assert len([n for n in g['nodes'] if n['phase']=='state_write_commit_fence'])==44
    assert g['nodes'][-1]['id']=='L-1.O3.collective_delivery_barrier'
    assert len({n['id'] for n in g['nodes']})==len(g['nodes'])
    for prev,node in zip(g['nodes'],g['nodes'][1:]):
        assert node['depends_on']==[prev['id']]
    assert len(W.schedule(g,{})['missing_costs'])==len(g['nodes'])
