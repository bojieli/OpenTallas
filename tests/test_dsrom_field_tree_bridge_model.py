import importlib.util,json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import uarch_model_dsrom_field_bridge as B
import dsrom_field_tree_bridge_model as M

@pytest.mark.parametrize('np,roots,nodes,undriven',[(4096,128,8064,127),(2048,64,4032,63)])
def test_fault_exact_source_generated_indices(np,roots,nodes,undriven):
    x=B.fault_coverage(np,roots)
    assert x['levels']==6 and x['node_count']==nodes
    assert x['undriven']==list(range(nodes,2*np-1)) and len(x['undriven'])==undriven
    assert x['tied_zero']==2*np-1 and x['node_fault_driven']==[0,nodes-1]

@pytest.mark.parametrize('np,roots',[(3000,128),(2048,63),(0,64)])
def test_invalid_shape_not_rounded(np,roots):
    with pytest.raises(ValueError):B.fault_coverage(np,roots)

@pytest.mark.parametrize('rows,shards,depth',[(576,[320,256],6),(1280,[640,640],10),(8192,[4096,4096],64)])
def test_full_rows_and_physical_shards(rows,shards,depth):
    counts=[B.root_rows(rows,r) for r in range(128)]
    assert sum(counts)==rows and [sum(counts[:64]),sum(counts[64:])]==shards
    assert max(counts)==depth

def test_inherited_tree_not_charged_as_new_bridge():
    x=B.existing_return_storage()
    assert x['existing_declaration_lower_bound_bits']==69771008
    assert x['bridge_must_not_recharge'] and x['already_charged']

def test_six_position_fullshape_reservation():
    x=B.buffer_price(8192,6)
    assert x['logical_seats']==49152 and x['per_shard_seats']==[24576]*2
    assert x['per_root_depth']==[384]*128 and x['raw_record_bits']==3391488
    assert x['R49_feedback_repaired_raw_record_reservation_mm2']==pytest.approx(5.4392684544)
    assert not x['mapped_area'] and not x['actual_slot_fit']
    assert x['existing_576_capture_or_return_storage_credit_mm2']==0

def test_no_silent_eight_position_capacity():
    with pytest.raises(ValueError):B.buffer_price(8192,8)

def test_unknown_and_nonpositive_provider_fail_closed():
    assert B.phase_service(8192,6,128)['F'] is None
    for d,c in [(0,1),(1,0),(-1,2)]:
        with pytest.raises(ValueError):B.phase_service(8192,6,128,data_cycles=d,credit_cycles=c)

@pytest.mark.parametrize('rows,pos,ports,drain',[(8192,6,128,387),(8192,6,1,49155),(576,1,128,9),(576,1,1,579)])
def test_positive_service_work_not_claimed_token(rows,pos,ports,drain):
    x=B.phase_service(rows,pos,ports,data_cycles=3,credit_cycles=1)
    assert x['drain_if_all_payload_ready_and_all_grants_succeed_cycles']==drain
    assert x['actual_token_exposed_cycles'] is None
    assert not x['field_internal_midphase_backpressure']

def test_existing_fifo_witness_preserves_fault_without_claiming_program_failure():
    x=M.adversarial_witness()
    assert list(x['first_overflow'])==[64,1,'FIFO_OVERFLOW']
    assert x['peak'][1]>64 and not x['current_fullprogram_failure_proven']

def test_real_pinned_source_contract():M.source_check()

def test_committed_census_enrolls_native_w2_and_full_formats():
    m=json.loads((M.OUT/'model.json').read_text());t=m['traffic']
    assert t['phases']==46509 and t['choice_alternatives']==276909
    assert t['formats']=={'bf16':139,'fp4':46080,'fp8':290}
    assert t['potential_singleposition_perrank']['calls']==1149
    assert t['potential_singleposition_perrank']['potential_rows']==1364352
    assert len(t['selected18'])==18
    w2=[x for x in t['selected18'] if x['native_W2']]
    assert len(w2)==6 and all(x['rows']==1280 for x in w2)
    assert t['largest']['rows']==8192
    assert t['actual_accepted_traffic'] is None
    assert not m['build_admitted'] and not m['physical_fit'] and not m['rate_adopted']

def test_all_pinned_inputs_match():
    m=json.loads((M.OUT/'model.json').read_text())
    for p,h in m['source_sha256'].items():assert M.sha(p)==h,p
