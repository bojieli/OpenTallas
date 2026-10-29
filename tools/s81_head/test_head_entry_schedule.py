import copy
import pytest
from head_entry_schedule import compile_entry


def fixture():
    inventory=dict(stages=81,TP=4,head_dies=4)
    job=dict(rank=3,tid=37,user=0,position=0,token=7,epoch=1,programme=9,
             host_word_count=417,plen=1,glen=0,group=4,rbase=97024,
             issue_offset=20,issue_period=10357,merge_deadline=10000)
    timing=dict(scope="PROVIDER_PIN_ENTRY",reset_deassert_edge=8,host_counter_zero_edge=10,
                link_ready_edge=24,peer_to_hbc_input=0,peer_frame_period=4,
                peer_launch_modulus=2,peer_launch_residue=0,peer_to_ctl_settled=37,
                commit_to_context_valid=1,ctl_start_offset=0)
    return inventory,job,timing


def test_static_slots_rank_body_and_start_order():
    i,j,t=fixture();r=compile_entry(i,j,t)
    assert r['host_params']['LOCAL_STAGE']==81 and r['host_params']['LOCAL_RANK']==3
    assert 'HBC_VARIABLE_WORDS' not in r['host_params']
    assert len(r['frames'])==11 and not r['production_transport_qualified']
    assert next(f['value'] for f in r['frames'] if f.get('address')==2)==3
    body=(next(f['frame'] for f in r['frames'] if f['kind']=='HBC_BODY')>>16)&((1<<512)-1)
    assert (body>>272)&1023==417 # HOST book, not activation data
    assert r['authority']['start_global_edge'] is None # no fabricated XB/residency source
    assert all(f['edge']%2==0 for f in r['frames'])
    assert r['full_head_token'] is False


def test_actual_activation_stream_is_counted_separately():
    i,j,t=fixture();j['host_word_count']=417;j['activation_beats']=list(range(80))
    t.update(xb_first_edge=400,xb_period=1,xb_pin_to_resident_edges=3)
    r=compile_entry(i,j,t)
    assert 'HBC_VARIABLE_WORDS' not in r['host_params']
    assert r['source_counts']==dict(HBC_setup_records=3,CSR_records=8,ordinary_HFWD_records=0,
                                   activation_K_XB_records=80,activation_halfwords512=160,
                                   activation_BF16_values=5120,total_source_records=91)
    assert r['activation_resident_edge']==482 and r['authority']['start_global_edge']>482
    assert all((f['lepk_i0']>>1)&7==2 for f in r['xb_records'])


def test_rejects_incompatible_source_phase_and_stage_allocation():
    for kind in ('phase','stage','rank','period'):
        i,j,t=fixture()
        if kind=='phase':t['peer_launch_modulus']=3
        if kind=='stage':i['stages']=241
        if kind=='rank':j['rank']=4
        if kind=='period':j['issue_period']=0
        with pytest.raises(ValueError):compile_entry(i,j,t)
