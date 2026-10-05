import copy
from collections import Counter
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w16_gpu_hc_dot_schedule as D
import w16_gpu_hc_simt_contract_r2 as R2


def test_actual_register_assignment_and_last_use():
    code,a=D.lower(D.W.chunk_program(),D.assumptions())
    assert a['spills']==0 and a['peak_value_registers']<=28
    assert a['control_registers']==[28,29,30,31]
    for x in a['bindings']:
        assert 0<=x['register']<28 and x['definition']<=x['last_use']
    assert code[28]['physical_src'][0]=='@F32_POS_ZERO'  # first+0 add is not omitted


def test_replay_RF_shared_dependencies_and_retirement():
    r,trace=D.replay(D.W.chunk_program(),32,D.assumptions())
    issues=Counter((x['cycle'],x['partition']) for x in trace)
    assert max(issues.values())==1
    shared=Counter(x['cycle'] for x in trace if x['shared'])
    assert max(shared.values())==1
    writes=Counter((x['retire'],x['partition']) for x in trace if x['dst'] is not None)
    assert max(writes.values())==1
    last={(w,reg):0 for w in range(32) for reg in (28,30)}
    for x in trace:
        for reg in x['src']:
            if isinstance(reg,int):assert last[(x['warp'],reg)]<=x['cycle']
        if x['dst'] is not None:last[(x['warp'],x['dst'])]=x['retire']
    assert r['cycles']>=max(x['retire'] for x in trace)
    assert r['instructions']['FADD']==32*13
    assert r['instructions']['IADDR']==32*13*6


def test_tree_barrier_and_latency_sensitivity():
    p=D.assumptions();tree=D.final_tree(p)
    assert tree['barrier_cycles']==16 and tree['cycles']>94
    a,_=D.replay(D.W.chunk_program(),32,p)
    p['add_latency']*=2
    b,_=D.replay(D.W.chunk_program(),32,p)
    assert b['cycles']>a['cycles']


@pytest.mark.parametrize('key,value',[('barrier_latency',0),('RF_words_thread',16),('RF_read_ports_lane',1),
    ('shared_banks',64),('loaded_HBM_ns',0),('bounded_credit_wait_cycles',0),('measured',True)])
def test_unpriced_or_free_cost_refused(key,value):
    p=copy.deepcopy(D.assumptions());p[key]=value
    with pytest.raises(ValueError):D.validate(p)


def test_full_HC22_has_no_missing_cost_or_lost_transpose():
    r,_=D.build()
    assert len(r['phases_cycles'])==22 and len(r['node_costs'])==1760
    assert min(r['phases_cycles'].values())>0
    assert r['preserved_transpose_cycles']==35248
    assert sum(v for k,v in r['phases_cycles'].items() if k.endswith('shared_fill'))==35248+960+sum(w['tile_service']['NoC_transfer_serial_cycles']+w['tile_service']['buffer_reuse_fence_cycles'] for w in r['waves'])
    assert all(w['tile_service']['landing_lines_per_controller']<=4096 for w in r['waves'])
    assert all(w['tile_service']['coefficient_raw_buffer_live_bytes_SM']<=2048 and w['tile_service']['activation_raw_buffer_live_bytes_SM']<=1024 for w in r['waves'])
    assert r['HC80_conditional_time_us']>80*(35248+7007)/900
    assert r['nonlinear_input']['primitive_F32_element_counts']['div']==649
    assert r['nonlinear_input']['proof_boundaries']==1500
    assert r['Euler_input']['bank_layout']['bank_count']==8
    assert r['Euler_input']['storage_bytes_rank']==5346800
    assert r['Euler_input']['actual_current_line_request_bytes_second_controller']==153600000000
    assert r['norm_calendar_input']['HC_mix_denominator']==20480
    assert r['TC16_consequence']['connected_token_price'] is None
    assert not r['physical_qualified'] and r['headline_rate'] is None


def test_resource_r2_roundtrip_and_refusal(monkeypatch):
    r=json.loads(json.dumps(R2.build()))
    original=D.subprocess.check_output
    def source_reader(command,**kwargs):
        if command[:2]==['git','show'] and command[2].endswith(':tools/w16_gpu_hc_dot_schedule.py'):
            return (D.ROOT/'tools/w16_gpu_hc_dot_schedule.py').read_bytes()
        return original(command,**kwargs)
    monkeypatch.setattr(D.subprocess,'check_output',source_reader)
    R2.check(r)
    assert r['preserved_transpose_cycles_operator']==35248
    r['costs']['pins']['tools/w16_gpu_hc_dot_schedule.py']='0'*64
    with pytest.raises(ValueError,match='cost evidence commit drift|pin drift'):R2.check(r)


def test_HC_subgraph_composes_and_full_token_refuses_unbound_others():
    import types
    import subprocess
    blob=subprocess.check_output(['git','show',D.GRAPH_COMMIT+':tools/w19_composed_schedule.py'],cwd=D.ROOT)
    S=types.ModuleType('expanded');S.__file__=str(D.ROOT/'tools/w19_composed_schedule.py');exec(compile(blob,'expanded.py','exec'),S.__dict__)
    r,_=D.build()
    full=S.graph(D.R.read(D.PROGRAM),r['expanded_graph_source_pins'])
    refused=S.schedule(full,r,evidence_reader=lambda commit,path:(D.ROOT/path).read_bytes())
    assert refused['status']=='BLOCKED_MISSING_KERNEL_OR_SERVICE_COSTS'
    assert not any(n['node'] in r['node_costs'] for n in refused['missing_costs'])
    hc=copy.deepcopy(full);hc['nodes']=[n for n in hc['nodes'] if n['id'] in r['node_costs']]
    for i,n in enumerate(hc['nodes']):n['depends_on']=[] if i==0 else [hc['nodes'][i-1]['id']]
    result=S.schedule(hc,r,evidence_reader=lambda commit,path:(D.ROOT/path).read_bytes())
    assert result['status']=='COMPLETE_MODELED_SCHEDULE_NOT_CONNECTED_RTL'
    assert not result['missing_costs'] and result['full_token_cycles'] is None
