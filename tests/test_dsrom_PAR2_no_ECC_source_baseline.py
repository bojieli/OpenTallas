import json,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_PAR2_no_ECC_source_baseline as N

def event(kind,edge,word=0,PP=0,row=64,owner=(0,0,1,10,0x80000000,0,0)):
    return dict(kind=kind,edge=edge,request_id=[13,word],owner_context=list(owner),main_word_address=dict(local_pair=13,PP=PP,row=row,MBs=[0,1]))

def test_source_capture_and_implicit_consume():
    f=N.NoECCSourceFlow(event('',0)['owner_context'])
    for kind,edge in [('main_CE_accept',0),('bank_capture',2),('lane_consumer_sample',3)]:f.step(event(kind,edge))
    assert f.report()['drained'] and f.report()['source_lane_pair_consumers']==1
    assert f.report()['new_global_ECC_request_seats']==0 and not f.report()['new_owner_ACK_wire']

@pytest.mark.parametrize('edge',[0,1,3,4])
def test_wrong_capture_edge_preserves_debt(edge):
    f=N.NoECCSourceFlow(event('',0)['owner_context']);f.step(event('main_CE_accept',0))
    with pytest.raises(ValueError):f.step(event('bank_capture',edge))
    assert len(f.pending)==1

@pytest.mark.parametrize('edge',[1,2,4])
def test_consumer_needs_actual_capture_and_i3(edge):
    f=N.NoECCSourceFlow(event('',0)['owner_context']);f.step(event('main_CE_accept',0))
    if edge>=2:f.step(event('bank_capture',2))
    with pytest.raises(ValueError):f.step(event('lane_consumer_sample',edge))
    assert len(f.pending)==1

def test_pingpong_allows_original_accept_capture_overlap():
    f=N.NoECCSourceFlow(event('',0)['owner_context'])
    schedule=[event('main_CE_accept',0),event('main_CE_accept',1,1,1),event('main_CE_accept',2,2,0,65),event('bank_capture',2),event('bank_capture',3,1,1),event('lane_consumer_sample',3),event('bank_capture',4,2,0,65),event('lane_consumer_sample',4,1,1),event('lane_consumer_sample',5,2,0,65)]
    for e in schedule:f.step(e)
    assert f.report()['drained'] and f.report()['source_lane_pair_consumers']==3

@pytest.mark.parametrize('fault',['bank','address','owner','order','ECC_event'])
def test_noECC_retains_source_identity_and_order_guards(fault):
    f=N.NoECCSourceFlow(event('',0)['owner_context']);f.step(event('main_CE_accept',0))
    if fault=='bank':e=event('main_CE_accept',1,1,0,65)
    elif fault=='address':e=event('bank_capture',2,row=65)
    elif fault=='owner':e=event('bank_capture',2,owner=(0,0,1,10,0x80000000,1,0))
    elif fault=='order':e=event('main_CE_accept',1,2,1)
    else:e=event('raw_check_terminal',2)
    with pytest.raises((ValueError,KeyError)):f.step(e)
    assert (13,0) in f.pending

@pytest.mark.parametrize('ordinal,reads',[(10,10240),(11,10240),(12,12800)])
def test_full_current_phase_conservation(ordinal,reads):
    phases={p['matrix_journal_ordinal']:p for p in N.C.readrows(N.J.PHASES)}
    m=next(x for i,x in enumerate(N.C.readrows(N.J.JOURNAL)) if i==ordinal)
    requests,p=N.case(m,phases[ordinal]);f=p['source_flow']
    assert f['main_CE_pair_requests']==f['matching_pair_captures']==f['source_lane_pair_consumers']==reads
    assert f['main_MB_reads']==reads*2 and f['drained'] and f['new_global_ECC_request_seats']==0
    assert f['maximum_registered_native_pipeline_tags_after_edge']<f['maximum_boundary_obligations_including_sameedge_departure']
    assert all(r['source_lane_consumer_edge']-r['source_CE_accept_edge']==3 for r in requests)
    assert not p['actual_parent_cfg_VM_accepted_absolute_origin_bound']

def test_removed_roles_no_active_only_macro_area_credit():
    rows,c=N.removal_census()
    assert len(rows)==58 and c['original_role_macros_all58xTP4']==c['mirror_role_macros_all58xTP4']==95584
    assert c['current_weight_macros_per_die']==8192 and c['physical_macro_count_area_credit_currently_taken']==0
    assert c['original_sidecar_data_bits_per_rank']==c['duplicate_mirror_bits_per_rank']==17616076800
