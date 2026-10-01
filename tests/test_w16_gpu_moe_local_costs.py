import copy
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w16_gpu_moe_local_costs as M


@pytest.fixture(scope='module')
def built():
    return M.build()


def test_local_phases_leave_all40_upstream_reads_pending(built):
    r,_,g,S,hc=built
    assert len(r['node_costs'])==160
    assert all('.operand_read_credit_wait' not in n for n in r['node_costs'])
    result=S.schedule(g,r,evidence_reader=lambda commit,path:(M.ROOT/path).read_bytes())
    assert result['status']=='BLOCKED_MISSING_KERNEL_OR_SERVICE_COSTS'
    assert sum(n['cost_key']=='local:moe_sum:operand_read_credit_wait' for n in result['missing_costs'])==40
    assert not r['physical_admission'] and r['headline_rate'] is None
    assert r['validated_progress_bound'] is False
    with pytest.raises(ValueError,match='REFUSED_NO_SOURCE_DESTINATION_PROGRESS_DEADLINES'):
        M.C.require_progress_bound(r)


def test_packed_loads_RMW_and_RF_allocated(built):
    r,trace,*_=built
    assert len(r['kernel']['bank_accesses'])==9
    assert sum(x['serialized_accesses']==2 for x in r['kernel']['bank_accesses'])==7
    assert r['kernel']['allocation']['spills']==0
    code=M.C.D.address_program(M.C.masked_store_program(M.E.moe_recipe(M.E.provider())))
    reads=[i for i,o in enumerate(code) if o['op']=='LOAD' and o['attributes'].get('source')=='output BF16 pair word']
    stores=[i for i,o in enumerate(code) if o['op']=='STS_PARTIAL']
    for warp in range(2):
        events={e['pc']:e for e in trace if e['warp']==warp}
        assert events[reads[1]]['cycle']>=events[stores[0]]['retire']


def test_all_expert_slots_co_live_and_padding_charged(built):
    r,*_=built
    regions=r['shared_layout']['regions']
    assert all(a['base']+a['bytes']<=b['base'] for a,b in zip(regions,regions[1:]))
    assert regions[-1]['base']+regions[-1]['bytes']==5120
    assert r['endpoint_bytes']['staged_padded_input']==896
    assert r['endpoint_bytes']['source_input_max']==756
    assert r['shared_layout']['producer_location']=='UNBOUND'


def test_composed_HC_plus_local_MoE_replaces_old_kernel_only(built):
    r,_,g,S,hc=built
    merged=copy.deepcopy(hc)
    merged['node_costs'].update(hc['HC_rebound_scenario_costs'])
    merged['node_costs'].update(r['node_costs'])
    merged['resource_capacities']['barrier']=1
    assert len(merged['node_costs'])==3292
    result=S.schedule(g,merged,evidence_reader=lambda commit,path:(M.ROOT/path).read_bytes())
    assert len(result['missing_costs'])==10337


def test_graph_and_capacity_mismatch_refused(built):
    r,_,g,S,_=built
    wrong=copy.deepcopy(r);wrong['graph_sha256']='0'*64
    with pytest.raises(ValueError,match='different graph'):S.schedule(g,wrong)
    wrong=copy.deepcopy(r);wrong['resource_capacities']['staging']=0
    with pytest.raises(ValueError,match='positive integer'):S.schedule(g,wrong)
