import copy,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_parallel_owner_binding as B
import dsrom_full_owner_compiler as C
import dsrom_native_weight_address_join as J
import dsrom_owner_cfg_interface_export as E


def first():
    return next(C.readrows(J.JOURNAL)),next(C.readrows(J.PHASES))


def test_compiled_site_bijection_and_exact_BF_mask_all_padding():
    sites=[B.site(g) for g in range(4096)]
    assert len({(x['shard'],x['local_site']) for x in sites})==4096
    assert all(x['global_return_region']==64*x['shard']+x['local_return_region'] for x in sites)
    bf={i*4096//724 for i in range(724)}
    for s in (0,1):assert {x%2048 for x in bf if x//2048==s}=={i*2048//362 for i in range(362)}
    assert (2*2048)//64==(2*4096)//128==64
    # Simply changing NP with originalR128 changes the source ordered tree.
    assert (2*2048)//128!=64


@pytest.mark.parametrize('g',[-1,4096,2048.0,True])
def test_invalid_global_site(g):
    with pytest.raises(ValueError):B.site(g)


def test_actual_first_phase_code_scale_address_and_global_row_cfg():
    m,p=first();r=B.bind_phase(m,p,None)
    assert [s['output_rows'] for s in r['shards']]==[192,128]
    assert r['row_cross_shard_K_reductions']==0
    for row in [0,127,128,319]:
        a=B.address(m,p,3,row,m['K']-1)
        assert a['shard']==((row//2)%128)//64
        assert a['scale_physical_bit_range']==[256,264]
        assert a['physical_row']<4096
        for w in range(25):assert B.cfg_word(m,a['shard'],a['local_site'],w)==E.config_word(m,a['pair'],w)


def test_wrong_plan_and_wrong_return_region_rejected():
    m,p=first();m=copy.deepcopy(m);m['plans'][0][1]=2048
    with pytest.raises(ValueError,match='plan hash'):B.bind_phase(m,p,None)
    p=copy.deepcopy(p);p['payload_plan_sha256']=J.digest(m['plans'])
    with pytest.raises(ValueError,match='region'):B.bind_phase(m,p,None)


def test_sidecar_cross_shard_boundary_exact_bits_and_address():
    p=dict(bits=8388608,pairs=[0,2048])
    a=B.ecc_runs(p,4194296,16,0)
    assert [(x['data_bits'],x['remote_from_code_owner']) for x in a]==[(8,False),(8,True)]
    assert sum(x['data_bits'] for x in a)==16
    with pytest.raises(ValueError):B.ecc_runs(p,8388600,16,0)


def test_immutable_HE_provider_address_preserves_native_word():
    p=next(C.readrows(E.OUT/'export_r1/immutable_provider_directory.jsonl.gz'))
    a=B.provider_address(p,'hc_ffn_fn',23,20479)
    assert a['stage']==0 and a['native_bank']==7 and a['shard']==0
    assert a['physical_row']<4096 and a['bit_range']==[224,256]


def event(t,bits=108,deadline=100,beat=0):
    return dict(arrival_cycle=t,bits=bits,original_deadline_cycle=deadline,identity=[0,0,1,0,0,0,'root',beat])


def test_finite_serialization_and_visibility_edges_not_constantfit():
    r=B.finite_calendar([event(3,108,8),event(3,108,9,1)],width_bits=64,latency_cycles=2,slots=2)
    assert [x['visible_cycle'] for x in r['journal']]==[7,9]
    assert r['no_loss_on_supplied_fixed_source_calendar'] and not r['full_token_no_loss_proven']
    r=B.finite_calendar([event(3,108,6)],width_bits=64,latency_cycles=2,slots=1)
    assert r['journal'][0]['exposed_cycles']==1 and not r['no_loss_on_supplied_fixed_source_calendar']


def test_held_remote_full_capture_overflow_is_negative():
    with pytest.raises(ValueError,match='overflow'):
        B.finite_calendar([event(0),event(0,beat=1)],width_bits=1,latency_cycles=50,slots=1)


def test_same_edge_terminal_releases_slot_before_next_arrival():
    r=B.finite_calendar([event(0,64),event(2,64,beat=1)],width_bits=64,latency_cycles=1,slots=1)
    assert r['peak_capture_slots']==1 and r['terminal_visible_cycle']==4


@pytest.mark.parametrize('mutant',['duplicate','shard','phase','sequence','era','short','order'])
def test_identity_and_source_order_mutants_fail(mutant):
    a=event(0);b=event(1,beat=1)
    if mutant=='duplicate':b['identity']=a['identity'].copy()
    if mutant=='shard':b['identity'][2]=2
    if mutant=='phase':b['identity'][3]=1024
    if mutant=='sequence':b['identity'][5]=8192
    if mutant=='era':b['identity'][4]=2
    if mutant=='short':b['identity'].pop()
    if mutant=='order':a['arrival_cycle']=2
    with pytest.raises(ValueError):B.finite_calendar([a,b],width_bits=64,latency_cycles=1,slots=2)


def test_runtime_expert_fullwidth_selector_preserved():
    p=dict(stage=3,phase=10,source_key_word=2**31+99,alias='exp383.w1',shards=[dict(shard=0,output_rows=128),dict(shard=1,output_rows=128)])
    choices=[dict(stage=3,phase=10,source_key_word=2**31+99,alias='exp383.w1') for _ in range(384)]
    b=dict(address_bound=True,selector_slot=5,phase_choices=choices)
    assert B.map_selection(b,{(3,10):p},[0,1,2,3,4,383])['required_shards']==[0,1]
    for ids in [[0,1,2,3,4,384],[0,1,2,3,4,512],[0,1,2,3,4,262144],[0,1,2,3,4,4]]:
        with pytest.raises(ValueError):B.map_selection(b,{(3,10):p},ids)


def test_wrong_owner_alias_phase_and_unbound_head_never_map_as_layer_phase():
    b=dict(address_bound=True,selector_slot=None,phase_choices=[dict(stage=1,phase=9,source_key_word=2**31,alias='wq_a')])
    p=dict(source_key_word=2**31,alias='wq_a',shards=[dict(shard=0,output_rows=1),dict(shard=1,output_rows=0)])
    assert B.map_selection(b,{(1,9):p})['required_shards']==[0]
    p['alias']='exp0.w1'
    with pytest.raises(ValueError,match='owner'):B.map_selection(b,{(1,9):p})
    with pytest.raises(ValueError,match='unbound'):B.map_selection(dict(address_bound=False),{})


def test_source_root_full_burst_needs_64_capture_slots_not4416_link_assumption():
    events=[event(0,108,1000,i) for i in range(64)]
    r=B.finite_calendar(events,width_bits=64,latency_cycles=2,slots=64)
    assert r['peak_capture_slots']==64 and r['terminal_visible_cycle']==130
    with pytest.raises(ValueError,match='overflow'):B.finite_calendar(events,width_bits=64,latency_cycles=2,slots=63)
    # Header overhead + finite serialized service, independent of source4416wirewidth.
    assert sum(x['bits'] for x in events)==6912
