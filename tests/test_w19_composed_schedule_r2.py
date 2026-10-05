import copy
import json
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_composed_schedule_r2 as W


def toy():
    return dict(graph_sha256='toy',programme_operations=2,nodes=[
        dict(id='a',cost_key='a',resource='simt',depends_on=[]),
        dict(id='b',cost_key='b',resource='simt',depends_on=[])])


def costs():
    c=dict(cycles=9,clock_hz=900000000,resource_units=1,
           finite_waits_included=True,exact_gpu_lowering_bound=True,
           evidence=dict(commit='a'*40,path='test-only-fixture',sha256=W.sha(b'fixture')))
    return dict(graph_sha256='toy',scope='GPU_SIMT_FULL_TOKEN_MODEL',
                resource_capacities={'simt':1},node_costs={'a':c,'b':copy.deepcopy(c)})


def run(g,c):
    return W.schedule(g,c,evidence_reader=lambda commit,path:b'fixture')


def test_missing_kernel_fails_closed():
    r=W.schedule(toy(),{})
    assert r['status'].startswith('BLOCKED') and r['full_token_cycles'] is None
    assert r['full_token_time_ps'] is None and not r['connected_rate_credit']


def test_finite_shared_resource_waits():
    r=run(toy(),costs())
    assert r['timeline'][1]['start_ps']=='10000'
    assert r['modeled_token_time_ps']=='20000' and r['full_token_cycles'] is None


def test_capacity_two_allows_independent_work():
    c=costs();c['resource_capacities']['simt']=2
    assert run(toy(),c)['modeled_token_time_ps']=='10000'


@pytest.mark.parametrize('field,value',[('finite_waits_included',False),('exact_gpu_lowering_bound',False),('resource_units',2)])
def test_unbound_or_overcapacity_rejected(field,value):
    c=costs();c['node_costs']['a'][field]=value
    with pytest.raises(ValueError):run(toy(),c)


def test_unproved_free_service_rejected():
    c=costs();c['node_costs']['a']['cycles']=0
    with pytest.raises(ValueError):run(toy(),c)


def test_wrong_graph_and_hcp_scope_rejected():
    c=costs();c['graph_sha256']='different'
    with pytest.raises(ValueError):run(toy(),c)
    c=costs();c['scope']='HCP_REFERENCE'
    with pytest.raises(ValueError):run(toy(),c)


def test_service_source_drift_rejected():
    c=costs();c['node_costs']['a']['evidence']['sha256']='0'*64
    with pytest.raises(ValueError,match='source drift'):run(toy(),c)


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


def test_head_split_products_not_naive_global_n():
    op=dict(kind='mv',fmt='bf16',n=8192,k=512,rows=[[1024*(h//8),1024*(h//8+1)] if h<64 else [0,0] for h in range(96)])
    r=W.operation_requirements(op)
    assert r['active_ranks']==64 and r['products_all_ranks']==64*1024*512
    assert r['products_all_ranks']!=op['n']*op['k']
    assert r['active_AR_matrix_columns']==1
    assert r['independent_output_row_waves_floor']==32
    assert r['ideal_rank_matrix_issue_floor_cycles']==256


def test_index_ownership_and_finite_loops():
    r=W.operation_requirements(dict(kind='local',fn='index_scores',n=1048576,src=20))
    assert r['rows_per_rank']==[10928]*32+[10920]*64
    assert r['bounded_1024row_loops_per_rank']==[11]*96
    assert r['physical_service_cycles'] is None


def test_reduce_inputs_and_rounding_boundary():
    r=W.operation_requirements(dict(kind='all_reduce',bytes=32768,dest='all'))
    assert r['input_fp32_partial_bytes_all_ranks']==262144
    assert r['final_bf16_vector_bytes']==16384
    assert r['golden_pairwise_add_levels']==3 and r['physical_noc_link_bytes'] is None


def test_partial_costs_are_validated_before_blocked():
    c=costs();del c['node_costs']['b']
    r=run(toy(),c)
    assert r['bound_local_model_cost_nodes']==1 and r['full_token_cycles'] is None
    c['node_costs']['a']['evidence']['sha256']='0'*64
    with pytest.raises(ValueError,match='source drift'):run(toy(),c)


def test_partial_costs_cannot_hide_free_service_or_wrong_graph():
    c=costs();del c['node_costs']['b'];c['node_costs']['a']['cycles']=0
    with pytest.raises(ValueError,match='zero-cost'):run(toy(),c)
    c=costs();del c['node_costs']['b'];c['graph_sha256']='wrong'
    with pytest.raises(ValueError,match='different graph'):run(toy(),c)


def test_actual_hc_nonzero_calendar_does_not_complete_transport():
    root=Path(__file__).resolve().parents[1]
    p=json.loads(subprocess.check_output(['git','show',f'{W.PIN}:{W.PROGRAM}'],cwd=root))
    blob=subprocess.check_output(['git','show',f'{W.KERNEL_COMMIT}:{W.KERNEL}'],cwd=root)
    g=W.graph(p,{})
    c=W.kernel_cost_contract(g,json.loads(blob),W.sha(blob))
    assert len(g['nodes'])==13629 and len(c['node_costs'])==720
    assert sum(v['cycles'] for v in c['node_costs'].values())==7007*80
    assert all(v['cycles']>0 for v in c['node_costs'].values())
    r=W.schedule(g,c)
    assert r['status'].startswith('BLOCKED') and len(r['missing_costs'])==12909
    assert r['full_token_cycles'] is None and not r['hardware_adopted']
    assert r['physical_admission'] is False and r['maximum_qualified_clock_hz'] is None
    missing={n['node'] for n in r['missing_costs']}
    assert any('transpose_noc_credit_wait' in n for n in missing)
    assert any('state_write_commit_fence' in n for n in missing)


def test_norm_bindings_keep_collect_broadcast_and_handoff_missing():
    root=Path(__file__).resolve().parents[1]
    p=json.loads(subprocess.check_output(['git','show',f'{W.PIN}:{W.PROGRAM}'],cwd=root))
    path='results/rtl/w19_checkpoint_production_20261001/gpu-norm-calendar-r1.json'
    blob=subprocess.check_output(['git','show',f'5a55e676b:{path}'],cwd=root)
    k=json.loads(blob);g=W.graph(p,{})
    c=W.norm_cost_contract(g,k,W.sha(blob))
    assert len(c)==485
    assert c['L-1.O0.pre_kernel']['cycles']==122
    assert c['L-1.O0.norm_scalar_kernel']['cycles']==155
    assert sum(v['cycles'] for v in c.values())==81*558+80*530
    assert all(v['cycles']>0 for v in c.values())
    result=W.schedule(g,dict(graph_sha256=g['graph_sha256'],scope='GPU_SIMT_FULL_TOKEN_MODEL',
        node_costs=c,resource_capacities={'simt':32}))
    assert result['full_token_cycles'] is None
    phases={n['phase'] for n in g['nodes'] if n['id'] not in c}
    assert {'norm_partial_collect_credit_wait','norm_scalar_broadcast_credit_wait','pre_norm_handoff_barrier'}<=phases
    k['source_graph_binding']=[]
    with pytest.raises(ValueError,match='programme mismatch'):W.norm_cost_contract(g,k,W.sha(blob))


def test_moe_calendar_only_prices_local_kernel():
    root=Path(__file__).resolve().parents[1]
    p=json.loads(subprocess.check_output(['git','show',f'{W.PIN}:{W.PROGRAM}'],cwd=root))
    path='results/quality/w16_w19_composed_schedule_20261001/moe_sum_calendar.json'
    blob=subprocess.check_output(['git','show',f'01088553b:{path}'],cwd=root)
    k=json.loads(blob);g=W.graph(p,{})
    c=W.elementwise_cost_contract(g,k,W.sha(blob))
    assert len(c)==40 and all(v['cycles']==85 and v['resource_units']==1 for v in c.values())
    assert all(n.endswith('.gpu_simt_kernel') for n in c)
    k['source_graph_binding']=[]
    with pytest.raises(ValueError,match='programme mismatch'):W.elementwise_cost_contract(g,k,W.sha(blob))
