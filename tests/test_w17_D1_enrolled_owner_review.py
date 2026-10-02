import hashlib,json,copy
from pathlib import Path
import pytest
from tools.w17_D1_enrolled_owner_review import review,qualify,D,C,L,W
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'results/uarch/w17_D1_enrolled_owner_actual_20261002_r1'
def inputs():
    return (B/'gdb.log').read_text(),json.loads((B/'receipt.json').read_text()),json.loads((ROOT/'results/uarch/w17_D1_enrolled_owner_probe_20261002/plan.json').read_text()),json.loads((ROOT/'results/uarch/w17_D1_terminal_program_binding_model_20261002/plan.json').read_text())
def events():return json.loads((B/'attribution.json').read_text())['event_values']
def test_actual_source_owned_first_return_not_universal_bound():
    a=review(*inputs())
    assert a['association']['generation']==1 and a['association']['pos']==127
    assert (a['descriptor_origin_ps'],a['service_origin_ps'],a['reply_ps'])==(141500,143500,196500)
    assert a['observed_request_reply_cycles']==53 and a['reset_qualified_rows']==128
    assert a['service_bound']=='BOUND_MISSING' and a['universal_upper_bound'] is None
    assert a['X_ROM']==0 and not a['fulltoken'] and a['I66_origin'] is None
@pytest.mark.parametrize('kind,key,value',[
 ('DESCRIPTOR',D+'att_packed_desc_accept',0),('DESCRIPTOR',D+'kvd_v',0),
 ('DESCRIPTOR',D+'rst_s',1),('DESCRIPTOR',L+'state',1),('DESCRIPTOR',L+'last_gen',1),
 ('DESCRIPTOR',L+'next_gen',2),('DESCRIPTOR',D+'att_packed_desc_gen',2),
 ('DESCRIPTOR',C+'me_pos',126),('DESCRIPTOR',C+'me_mmode',0),
 ('DESCRIPTOR',D+'step_user',1),('DESCRIPTOR',L+'incoming_rows',127),
 ('DESCRIPTOR',C+'me_pos',127.0),('DESCRIPTOR',D+'kvd_v',True),
 ('READ',L+'active_gen',2),('READ',D+'win_service_gen',2),
 ('READ',L+'active_user',1),('READ',L+'active_pos',128),
 ('READ',L+'active_tiles',16),('READ',L+'state',0),
 ('READ',W+'state',0),('READ',W+'sec',1),('READ',W+'row',1),
 ('READ',W+'active_user',1),('READ',D+'att_packed_desc_accept',1),
 ('READ',D+'win_service_fault',1),('READ','tb_D1_scope_core__DOT__diag_cycle',0),
])
def test_reject_false_admission_stale_phase_wrong_owner_before_mutation(kind,key,value):
    e=events();e[kind][key]=value;before=copy.deepcopy(e)
    with pytest.raises(ValueError):qualify(e['DESCRIPTOR'],e['READ'])
    assert e==before
@pytest.mark.parametrize('before,after',[
 ('D1_REAL_DESCRIPTOR time=142000 generation=1','D1_REAL_DESCRIPTOR time=142000 generation=2'),
 ('D1_REAL_ACCEPT time=144000 address=262144','D1_REAL_ACCEPT time=144000 address=262145'),
 ('D1_SOURCE_EVENT_READ_BEGIN','D1_SOURCE_EVENT_DESCRIPTOR_BEGIN'),
 ('D1_EVENT_104','D1_EVENT_103'),
 ('D1_INFERIOR_EXIT code=0','D1_INFERIOR_EXIT code=1'),
 ('D1_REAL_RESPONSE time=197000 tag=0 beat=0','D1_REAL_RESPONSE time=197000 tag=1 beat=0'),
])
def test_actual_raw_negative_controls_after_rehash(before,after):
    t,r,p,o=inputs();assert before in t;t=t.replace(before,after,1);r['log_SHA256']=hashlib.sha256(t.encode()).hexdigest()
    with pytest.raises(ValueError):review(t,r,p,o)
def test_all_false_sample_cannot_grant_admission():
    e=events();e['DESCRIPTOR']={k:0 for k in e['DESCRIPTOR']}
    with pytest.raises(ValueError):qualify(e['DESCRIPTOR'],e['READ'])
