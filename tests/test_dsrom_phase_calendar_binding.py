import copy,gzip,json,sys
from pathlib import Path
from fractions import Fraction
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_phase_calendar_binding as J
import dsrom_provider_first_event_join as E

@pytest.fixture(scope='module')
def inputs():return J.load()

@pytest.fixture(scope='module')
def joined(inputs):
    d=json.loads(gzip.decompress((J.BASE/'demand-r7.json.gz').read_bytes()))
    return J.compose(d,inputs)

def test_full_phase_key_provider_conservation(inputs):
    index,providers=J.validate_directories(inputs)
    assert len(index)==46509 and len(providers)==80
    assert sum(p['format']=='fp4' for p in index.values())==46080
    assert max(p['stage'] for p in index.values())==53
    assert {p['stage'] for p in inputs['cfg_ECC_directory.jsonl.gz']}==set(range(58))

@pytest.mark.parametrize('fault',['phase','BFflag','key','issue','provider','ECC','unused'])
def test_source_identity_faults_refused(inputs,fault):
    x=copy.deepcopy(inputs)
    if fault=='phase':x['cfg_phase_directory.jsonl.gz'][0]['phase']=1
    elif fault=='BFflag':x['cfg_phase_directory.jsonl.gz'][0]['format']='bf16'
    elif fault=='key':x['cfg_key_tables.jsonl.gz'][0]['words'][0]^=1
    elif fault=='issue':x['issue']['records'][0]['issue_cycles_LAT8_condition']=0
    elif fault=='provider':x['cfg_provider_directory.jsonl.gz'][0]['stage']=1
    elif fault=='ECC':x['cfg_ECC_directory.jsonl.gz'].pop()
    else:x['cfg_key_tables.jsonl.gz'][57]['words'][1000]=1<<31
    with pytest.raises(ValueError):J.validate_directories(x)

def test_actual_descriptor_not_resident_phase_cadence(joined):
    assert joined['rank_event_count']==19548
    assert len(joined['templates'])==4887
    assert joined['known_call_costs']['field_cfg_calls_per_rank']==1149
    assert joined['known_call_costs']['generic_cfg_work_cycles_per_rank']==31023
    assert len(joined['phase_selector_tables'])==120
    assert all(len(t)==384 for t in joined['phase_selector_tables'].values())
    assert sum(t['owner']['kind']=='dense_field' for t in joined['templates'].values())==429
    assert all('exact_phase' in t['cfg'] for t in joined['templates'].values() if t['owner']['kind']=='dense_field')

def test_complete_symbolic_costs_no_missing_as_zero(joined):
    assert len(joined['finite_calendar_equations'])==19548
    assert all(len(e['required_positive_symbols'])==3 for e in joined['finite_calendar_equations'])
    assert not joined['full_token_cycles_evaluated'] and not joined['build_admitted']
    with pytest.raises(ValueError,match='coverage'):J.price(joined,{}, {}, {})

def test_72bit_provider_budget_no_packed_credit(joined):
    assert joined['cfg_provider']['prospective_macro_instances']==28672
    assert joined['exact_cfg_instances_all58x4']==6651904
    assert joined['exact_cfg_pins_all58x4']==585367552
    assert joined['cfg_bits_all58x4']==1167694233600
    assert joined['whole_area_ledger_mm2']['conservative_no_containment_credit_die_total']==924.2886185238459
    assert joined['whole_area_ledger_mm2']['already_inside_inherited_named_service_proxy_do_not_add_again']==90.44685198583997
    assert joined['old24d_failure_record_unchanged'] and joined['no_274bit_cfg_provider_credit']

def test_native_he_packing_exact_coordinate_join():
    K=20480
    for k in (0,7,8,63,64,2559):
        mapped=[J.he_address(j*3+l,c*(K//8)+k) for j in range(8) for l in range(3) for c in range(8)]
        assert {b for b,w,l in mapped}=={k%8}
        assert len({w for b,w,l in mapped})==192
        assert len(set(mapped))==192
        for b,w,lane in mapped:
            row=w//320;col=(w%320)*64+lane*8+b
            assert 0<=row<24 and col%2560==k
    m=J.he_transpose()
    assert m['source_unique_reads_per_bank_per_block']==[192]*8
    assert m['pingpong_buffer_bytes']==98304
    assert m['native_issue_serial_cycles']==20480 and m['source_tree_serial_cycles']==15
    assert m['conditional_one_read_per_bank_stream_cycles_per_block']==192
    assert m['no_change_to_golden_order'] and not m['provider_implemented']

def miniature():
    p=dict(stage=0,phase=0,source_key_word=1<<31,matrix_journal_ordinal=0,issue_cycles_LAT8_condition=8)
    t=dict(id='L0.I0',kind='field_adapter',node_sha256='synthetic-only',source_unit=1,source_collective_input_bits=0,
           owner=dict(kind='dense_field',stage=0),cfg=dict(exact_phase=p))
    joined=dict(templates={'L0.I0':t},events=[dict(id='L0.I0.R0',template='L0.I0',rank=0,previous_acceptance=None,required_completion_dependencies=[])])
    b=dict(node_sha256='synthetic-only',source_receipts=['synthetic-only'],native_provider_ABI_receipts=['synthetic-only'],
           owner_stage=0,provider='test-engine',cfg_acceptance_source_receipts=['synthetic-only'],
           cfg_delivery_fence_receipts=['synthetic-only'],cfg_phase_identity={k:p[k] for k in ('stage','phase','source_key_word','matrix_journal_ordinal')},
           latency_evidence_kind='provisional',cost_assumption_receipts=['synthetic-only'],frontend_or_transport_owner_receipts=['synthetic-only'],
           native_service_and_visibility_ns='1',resource_coverage_receipts=['synthetic-only'],
           resource_claims=[dict(resource='field',order=0,demand_bits=0,release='complete')],
           calendar=dict(domain='streaming',accept_cycles=1,complete_cycles=40,issue_interval_cycles=27,completion_dependencies=[],source_receipts=['synthetic-only']))
    resource=dict(kind='field_cfg_matrix',scope='rank',domain='streaming',ownership='synthetic-only',source_receipts=['synthetic-only'],owner_stage=0,minimum_issue_cycles=27,issue_interval_cycles=27)
    return joined,{'L0.I0.R0':b},{'field':resource}

def test_evaluates_only_explicit_positive_finite_model():
    j,b,r=miniature();out,_=J.price(j,b,r,{})
    assert out['L0.I0.R0'][2]==Fraction(100,3)

@pytest.mark.parametrize('fault',['zero','low','phase','fence','parent','II','evidence'])
def test_calendar_lower_cost_or_identity_optimism_refused(fault):
    j,b,r=miniature();x=b['L0.I0.R0']
    if fault=='zero':x['native_service_and_visibility_ns']=0
    elif fault=='low':x['calendar']['complete_cycles']=35
    elif fault=='phase':x['cfg_phase_identity']['phase']=1
    elif fault=='fence':x['cfg_delivery_fence_receipts']=[]
    elif fault=='parent':x['frontend_or_transport_owner_receipts']=[]
    elif fault=='II':r['field']['minimum_issue_cycles']=1
    else:x['latency_evidence_kind']=''
    with pytest.raises(ValueError):J.price(j,b,r,{})

def test_optin_address_patches_are_native_words_not_callbacks(joined):
    a=joined['descriptor_address_and_native_admission']
    assert a['patches']==1149 and a['runtime_expert_stride_patch_count']==720
    for p in a['patch_recipes']:
        assert p['source_opcode_rounding_and_operand_versions_unchanged']
        assert int(p['optin_native_ISA_word_hex'],16)>0
        if 'qe_istride' in p['changes']:assert p['changes']['qe_istride']==4096
    assert not a['runtime_image_or_stage_packet_emitted']
    assert not a['all_native_descriptors_admitted']

def test_native_me_m_ok_failures_are_preserved(joined):
    a=joined['descriptor_address_and_native_admission']
    assert len(a['layer_ME_m_ok_failures'])==6
    assert all(f['failed_predicates']==['m_round'] for f in a['layer_ME_m_ok_failures'])
    assert all(f['original_fields']['me_round']==0 and f['must_not_force_round_or_change_reduction_order'] for f in a['layer_ME_m_ok_failures'])
    assert len(a['head_ME_m_ok_failures'])==1

def test_native_me_predicate_fault_cannot_receive_free_admission():
    j,b,r=miniature();j['descriptor_address_and_native_admission']={'layer_ME_m_ok_failures':[{'node_id':'L0.I0'}]}
    with pytest.raises(ValueError,match='native m_ok'):J.price(j,b,r,{})
