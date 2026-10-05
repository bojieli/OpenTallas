import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('w2pc',ROOT/'tools/w2_pc_exact_completion_model.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def event(client=0,tag=1,generation=7,write=0,**extra):
    return dict(client=client,tag=tag,generation=generation,write=write,**extra)


def service(limit=16):
    s=M.Service(nc=6,limit=limit);s.rearm(7,provider_fenced=True,reset_fenced=True);return s


def test_registered_read_timing_and_held_data():
    s=service();q=event()
    assert s.tick(request=q)['request_accept']
    cap=s.tick(read=event(data=123));assert cap['read_accept']
    assert s.tick(read_ready=[False]*6)['read_delivery'] is None
    saved=s.rd.copy()
    for _ in range(8):
        x=s.tick(read_ready=[False]*6);assert x['outstanding'][0]==1 and s.rd==saved
    x=s.tick();assert x['read_delivery']['data']==123 and x['outstanding'][0]==0


def test_write_minimum_three_edges_and_ready_hold():
    s=service();q=event(write=1)
    s.tick(request=q);cap=s.tick(write=q)['edge']
    assert not s.tick()['write_deliveries']
    assert not s.tick()['write_deliveries']
    x=s.tick();assert x['edge']==cap+3 and len(x['write_deliveries'])==1
    assert x['outstanding'][0]==0
    s=service();s.tick(request=q);s.tick(write=q)
    for _ in range(12):
        x=s.tick(write_ready=[False]*6);assert x['outstanding'][0]==1 and not x['write_deliveries']
    assert len(s.tick()['write_deliveries'])==1


@pytest.mark.parametrize('wrong',['tag','generation','client','direction'])
def test_bad_return_does_not_release_credit_and_fault_stops_new_admission(wrong):
    s=service();s.tick(request=event());bad=event(data=22)
    bad[{'direction':'write'}.get(wrong,wrong)]+=1
    s.tick(read=bad);x=s.tick(request=event(tag=2))
    assert x['fault'] and not x['request_accept'] and x['outstanding'][0]==1
    assert x['read_delivery'] is None
    assert not s.tick(request=event(tag=3))['request_accept']


def test_live_duplicate_request_rejected_but_direction_is_part_of_identity():
    s=service();s.tick(request=event());x=s.tick(request=event())
    assert x['fault'] and x['outstanding'][0]==1
    s=service();s.tick(request=event());x=s.tick(request=event(write=1))
    assert x['request_accept'] and not x['fault'] and x['outstanding'][0]==2


def test_duplicate_write_completion_held_does_not_double_retire():
    s=service();q=event(write=1);s.tick(request=q);s.tick(write=q)
    s.tick(write=q,write_ready=[False]*6)
    x=s.tick(write_ready=[False]*6)
    assert x['fault'] and x['outstanding'][0]==1
    assert not s.tick()['write_deliveries']
    assert s.tick()['outstanding'][0]==1


def test_out_of_order_matching_same_client_and_simultaneous_read_write():
    s=service();s.tick(request=event(tag=1));s.tick(request=event(tag=2,write=1))
    s.tick(request=event(tag=3));s.tick(read=event(tag=3,data=33),write=event(tag=2,write=1))
    s.tick();x=s.tick();assert x['read_delivery']['key'][1]==3
    x=s.tick();assert x['write_deliveries'][0]['key'][1]==2
    s.tick(read=event(tag=1,data=11));s.tick();x=s.tick()
    assert x['read_delivery']['data']==11 and x['outstanding'][0]==0 and not x['fault']


def test_full_credit_held_write_terminal_and_no_same_edge_reuse():
    s=service(limit=1);q=event(write=1);s.tick(request=q);s.tick(write=q);s.tick();s.tick()
    x=s.tick(request=event(tag=2,write=1));assert len(x['write_deliveries'])==1
    assert not x['request_accept']
    assert s.tick(request=event(tag=2,write=1))['request_accept']


def test_all_sixteen_write_terminal_seats_already_reserved():
    s=service();ready=[False]*6
    for tag in range(16):assert s.tick(request=event(tag=tag,write=1),write_ready=ready)['request_accept']
    for tag in reversed(range(16)):s.tick(write=event(tag=tag,write=1),write_ready=ready)
    for _ in range(3):s.tick(write_ready=ready)
    assert s.tick(write_ready=ready)['outstanding'][0]==16 and not s.fault
    assert not s.tick(request=event(tag=16,write=1),write_ready=ready)['request_accept']
    retired=[]
    for _ in range(40):retired+=s.tick()['write_deliveries']
    assert len(retired)==16 and len({r['key'] for r in retired})==16
    assert not any(s.tick()['outstanding'])


def test_local_reset_cannot_erase_debt_and_stale_reset_generation_rejected():
    s=service();s.tick(request=event())
    with pytest.raises(ValueError,match='debt'):s.rearm(8,True,True)
    assert s.fault and s.entries[0][0] is not None
    s=service();s.rearm(8,True,True);s.tick(request=event(generation=8))
    s.tick(read=event(generation=7,data=111));x=s.tick()
    assert x['fault'] and x['outstanding'][0]==1


def test_namespace_reuse_is_environment_obligation_not_hidden_tombstone_hardware():
    s=service();s.tick(request=event());s.tick(read=event(data=1));s.tick();s.tick()
    with pytest.raises(ValueError,match='environment violation'):s.tick(request=event())
    assert not s.fault
    with pytest.raises(ValueError,match='fences'):s.rearm(7,False,True)
    s.rearm(7,True,True);assert s.tick(request=event())['request_accept']


def test_zero_causal_backend_latency_is_rejected():
    s=service();s.tick(request=event(write=1),write=event(write=1));x=s.tick()
    assert x['fault'] and x['outstanding'][0]==1


def test_model_source_binding_state_and_nonadmission():
    m=M.model();z=m['full_wrapper_variant']
    assert z['state_bits_per_PC']==4779 and z['table_entries_per_PC']==96
    assert z['geometry']['backend_tag_plus_generation_bits']==39
    assert z['incremental_state_bits_per_PC_over_counter_only']==4745
    assert z['state_bits_all_PCs']==611712
    assert z['request_frontend_proposal']['registered_holder_bits']==335
    assert z['geometry']['AW']==34
    assert m['GENW_model_frozen'] and m['production_rate'] is None
    assert not m['generation_wrap_source_qualified']
    assert z['comparator_loaded_SS_path_ps'] is None and z['latency_ns'] is None
    assert not z['hardware_admitted'] and not m['resource_preparation']['build_now']
    assert m['successor']['table_entries_per_PC']==80
    assert m['minimum_row38']['NC5_raw_bits']==3040
    assert m['minimum_row38']['NC6_raw_bits']==3648
    assert m['occupied_client5_KV_not_a_free_directory_lane']


def test_generations_are_per_transaction_not_one_global_epoch():
    s=service();assert s.tick(request=event(tag=1,generation=3))['request_accept']
    assert s.tick(request=event(tag=1,generation=4))['request_accept']
    s.tick(read=event(tag=1,generation=4,data=4));s.tick();x=s.tick()
    assert x['read_delivery']['key'][2]==4 and x['outstanding'][0]==1


def test_fault_discovery_blocks_other_good_terminal_release():
    s=service();s.tick(request=event(write=1));s.tick(write=event(write=1))
    s.tick();s.tick()
    s.tick(read=event(tag=99,data=1),write_ready=[False]*6)
    x=s.tick();assert x['fault'] and not x['write_deliveries'] and x['outstanding'][0]==1


def test_full_modulo16_reuse_needs_all_copy_fence_not_run_cap():
    s=service(limit=1)
    for gen in range(16):
        q=event(generation=gen,write=1);s.tick(request=q);s.tick(write=q);s.tick();s.tick();s.tick()
    with pytest.raises(ValueError,match='environment violation'):s.tick(request=event(generation=0,write=1))
    s.rearm(0,True,True)
    assert s.tick(request=event(generation=0,write=1))['request_accept']


def test_read_channel_cannot_retire_write_entry():
    s=service();s.tick(request=event(write=1));s.tick(read=event(write=0,data=1));x=s.tick()
    assert x['fault'] and x['outstanding'][0]==1 and x['read_delivery'] is None


def test_full_source_tag_upper_bits_preserved_and_checked():
    s=service();q=event(tag=(1<<31)+9,write=1);s.tick(request=q)
    s.tick(write=q);s.tick();s.tick();x=s.tick()
    assert x['write_deliveries'][0]['key'][1]==(1<<31)+9
    s=service();s.tick(request=q);s.tick(write=event(tag=9,write=1));x=s.tick()
    assert x['fault'] and x['outstanding'][0]==1


def test_KV_phase_and_track_capacity_not_silently_completed():
    m=M.model();z=m['successor']
    assert z['geometry']['NC']==5 and z['table_entry_bits']==39
    assert z['port_signal_bits']['backend_write_completion']==41
    assert z['source_boundary_signal_track_floor']['channel_capacity'] is None
    assert m['KV_followon_contract']['pending_raw_bits']==79
    assert not m['KV_followon_contract']['full_price_and_build_admitted']


def test_canonical_owner46_retains_all_source_fields():
    for pc in [0,4,127]:
        for client in [0,4,5]:
            for gen in [0,7,15]:
                tag=0xf123abcd
                x=M.owner46(pc,client,tag,gen)
                assert M.decode_owner46(x)==dict(physical_pc=pc,client=client,original_tag=tag,generation=gen)
    assert M.owner46(0,0,1,0)!=M.owner46(1,0,1,0)
    assert M.owner46(0,0,1,0)!=M.owner46(0,0,1,1)


def test_mutable_protection_is_priced_not_ROM_waived():
    m=M.model()
    a=m['successor']['protected_storage'];b=m['full_wrapper_variant']['protected_storage']
    assert a['bits_per_PC']==7848 and b['bits_per_PC']==9144
    assert a['bits_by_section']['table']==80*72
    assert b['bits_by_section']['table']==96*72
    assert a['gross_body_mm2_per_PC_ASSUMED']>m['successor']['gross_body_mm2_per_PC']
    assert not a['exact_checker_encoder_cell_map_and_loaded_timing']


def test_R14_mapping_witness_refuses_direct_connected_build():
    m=M.model();j=m['actual_route_join']
    assert j['concrete_mismatch_witness']==dict(sector=4,Qwen_low7_PC=4,R14_local_PC=1)
    assert not j['chosen_leaf_on_Popper_route'] and not j['connected_build_admitted']
    assert m['canonical_fullwidth']['owner_bits']==46
    assert m['canonical_fullwidth']['W4_and_W6_identity_bits_with_RFslot9']==55
    assert m['prospective_latency_sensitivity'][2]['earliest_write_client_accept_after_backend_capture_edges']==5


def test_joint_read_write_terminal_retirement_same_client_has_no_underflow():
    s=service();s.tick(request=event(tag=1,write=1));s.tick(request=event(tag=2))
    s.tick(write=event(tag=1,write=1));s.tick(read=event(tag=2,data=99))
    s.tick();x=s.tick()
    assert x['read_delivery']['data']==99 and len(x['write_deliveries'])==1
    assert x['outstanding'][0]==0 and not x['fault']


def test_live_duplicate_request_fault_blocks_same_edge_held_terminal_release():
    s=service();q=event(write=1);s.tick(request=q);s.tick(write=q);s.tick();s.tick()
    x=s.tick(request=q)
    assert x['fault'] and not x['write_deliveries'] and x['outstanding'][0]==1
