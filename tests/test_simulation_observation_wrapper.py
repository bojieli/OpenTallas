import hashlib
import importlib.util
import subprocess
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import prepare_simulation_observation_wrapper as prep
from simulation_observation_api import State, encode, decode, observe


def frame(cycle=0, **kw):
    for prefix in ['window_']+[f'ckv{i}_' for i in range(4)]:
        if kw.get(prefix+'req_take'): kw.setdefault(prefix+'req_ready',1)
    return encode(dict(epoch=1,rank=0,cycle=cycle,**kw))


def test_source_bound_copy_exact_inverse():
    src=prep.original(ROOT)
    copy=(ROOT/prep.COPY).read_text()
    assert copy==prep.render(src)
    assert prep.inverse(copy)==src
    assert hashlib.sha256(src.encode()).hexdigest()=='43803b86e4bbdf5cbd68fb682a19611156d8595b7c9c71afd83f0898e9bf8d65'


def test_real_hierarchy_and_qualifiers():
    die=subprocess.check_output(['git','show',prep.SOURCE+':rtl/chip/ckvsel/ot_chip_v41x_die.sv'],cwd=ROOT).decode()
    source=subprocess.check_output(['git','show',prep.SOURCE+':rtl/chip/ot_chip_v41x_window_attn_source.sv'],cwd=ROOT).decode()
    ckv=subprocess.check_output(['git','show',prep.SOURCE+':rtl/chip/ot_chip_v41x_ckv_die_service.sv'],cwd=ROOT).decode()
    for anchor in ['begin : g_packed_kv','begin : g_window_hbm_attention','begin : g_ckv','u_source (','u_ckv (']:
        assert anchor in die
    assert 'wire grant = m_rdy[WIN_STACK] && m_v[WIN_STACK];' in subprocess.check_output(['git','show',prep.SOURCE+':rtl/chip/ot_chip_v41x_window_kv_prefetch.sv'],cwd=ROOT).decode()
    assert 'assign issue_ready=merge_start_ready && stream_go && staged_sent;' in source
    assert 'if (sel_v && !rd_act)' in ckv
    assert 'if (job_v && rel_ok)' in ckv
    assert 'assign job_done = m_done;' in ckv


@pytest.mark.parametrize('bad',[True,1.0,-1,1<<prep.BITS,'0',None])
def test_invalid_packet(bad):
    with pytest.raises(ValueError): decode(bad)


@pytest.mark.parametrize('field,bad',[('rank',4),('source_first',1<<21),('desc_gen',1<<16),('epoch',-1),('cycle',True),('ckv_collect_take',32)])
def test_invalid_fields(field,bad):
    with pytest.raises(ValueError): encode({field:bad})


def test_layout_roundtrip_top_bits_no_truncation():
    values={f['name']:(1<<f['width'])-1 for f in prep.layout()}
    assert decode(encode(values))==values
    assert sum(f['width'] for f in prep.layout())==prep.BITS


def window_trace():
    s,e=observe(State(),frame(source_accept=1,source_gen=7))
    s,e=observe(s,frame(1,window_prefetch_accept=1,window_prefetch_row=127))
    # Seventeen accepted and matched sectors; scale sector publishes row.
    for sector in range(17):
        s,e=observe(s,frame(2+2*sector,window_state=5,window_req_take=1,window_req_offer=1,window_req_tag=sector,window_sector=sector,window_row=127))
        s,e=observe(s,frame(3+2*sector,window_state=6,window_rsp_take=1,window_rsp_tag=sector,window_sector=sector,window_row=127,window_reply_ok=1,window_row_publish=int(sector==16)))
        assert not any(event.causal_certificate for event in e)
    s,e=observe(s,frame(36,staged=1,active_gen=7))
    assert s.source is not None and s.refill is None
    s,e=observe(s,frame(37,merge_accept=1,active_gen=7))
    s,e=observe(s,frame(38,stage_req_take=1,stage_req_user=0,stage_req_first=127,stage_req_mask=15))
    s,e=observe(s,frame(39,stage_rsp_take=1,stage_rsp_first=127,stage_rsp_mask=15,stage_rsp_valid=15))
    s,e=observe(s,frame(40,stream_take=1,stream_mask=15,active_gen=7))
    s,e=observe(s,frame(41,merge_done=1))
    s,e=observe(s,frame(42,source_done=1))
    assert s.source is None and not s.requests
    return s


def test_valid_window_complete_lifetimes(): window_trace()


def ckv_trace():
    s,e=observe(State(),frame(ckv_available=1,ckv_select_accept=1,ckv_select_vmword=128))
    selection=s.selection
    s,e=observe(s,frame(1,ckv_available=1,ckv_fetch_accept=1))
    # All four ports accept concurrently, and retain independently matched tags.
    s,e=observe(s,frame(2,ckv_available=1,**{f'ckv{i}_'+k:v for i in range(4) for k,v in [('req_take',1),('req_offer',1),('req_tag',i<<4)]}))
    assert len([x for x in e if x.kind=='request'])==4
    s,e=observe(s,frame(3,ckv_available=1,**{f'ckv{i}_rsp_take':1 for i in range(4)},**{f'ckv{i}_rsp_tag':i<<4 for i in range(4)}))
    s,e=observe(s,frame(4,ckv_available=1,ckv_fetch_done=1,ckv_collect_take=31,ckv_collect_rank=sum(i<<(i*10) for i in range(5)),ckv_collect_gid=sum((128+i)<<(i*21) for i in range(5))))
    assert len([x for x in e if x.kind=='collector_observed'])==5
    for cycle,generation in [(5,19),(8,20)]:
        s,e=observe(s,frame(cycle,ckv_available=1,ckv_job_accept=1,ckv_job_gen=generation))
        op=s.replay
        assert op.selection==selection.serial
        s,e=observe(s,frame(cycle+1,ckv_available=1,ckv_stream_take=1,ckv_job_gen=generation,ckv_stream_mask=15,ckv_rows_ready=1))
        assert s.replay==op and s.selection==selection
        s,e=observe(s,frame(cycle+2,ckv_available=1,ckv_job_done=1))
    assert s.selection==selection
    return s


def test_qk_pv_distinct_jobs_same_selection(): ckv_trace()


@pytest.mark.parametrize('mutant',['wrong_generation','early_retire','repeated_step','replacement_selection'])
def test_real_negative_controls_before_mutation(mutant):
    s,_=observe(State(),frame(ckv_available=1,ckv_select_accept=1))
    s,_=observe(s,frame(1,ckv_available=1,ckv_job_accept=1,ckv_job_gen=19))
    if mutant=='wrong_generation': bad=frame(2,ckv_available=1,ckv_stream_take=1,ckv_job_gen=20)
    elif mutant=='early_retire':
        s,_=observe(s,frame(2,ckv_available=1,ckv_fetch_accept=1))
        s,_=observe(s,frame(3,ckv_available=1,ckv0_req_take=1,ckv0_req_offer=1))
        bad=frame(4,ckv_available=1,ckv_fetch_done=1)
    elif mutant=='repeated_step': bad=frame(1,ckv_available=1,ckv_job_accept=1,ckv_job_gen=19)
    else: bad=frame(2,ckv_available=1,ckv_select_accept=1)
    before=repr(s)
    with pytest.raises(ValueError): observe(s,bad)
    assert repr(s)==before


def test_one_request_on_accept_not_offer_or_eval():
    s,_=observe(State(),frame(window_prefetch_accept=1))
    events=[]
    for cycle,ready in [(1,0),(2,0),(3,1)]:
        s,e=observe(s,frame(cycle,window_state=5,window_req_offer=1,window_req_ready=ready,window_req_take=bool(ready)*1))
        events.extend(e)
    assert sum(x.kind=='request' for x in events)==1
    with pytest.raises(ValueError): observe(s,frame(3,window_state=5,window_req_offer=1,window_req_take=1))


@pytest.mark.parametrize('kw',[dict(window_row_publish=1),dict(source_done=1),dict(ckv_rows_ready=1),dict(stage_rsp_take=1),dict(window_rsp_take=1)])
def test_unowned_and_unavailable_events(kw):
    with pytest.raises(ValueError): observe(State(),frame(**kw))


def test_reset_changes_identity_without_certifying_drain():
    s,_=observe(State(),frame(source_accept=1,source_gen=7))
    old=s.source
    s,e=observe(s,encode(dict(epoch=2,rank=0,cycle=0,source_accept=1,source_gen=7)))
    assert s.source!=old and s.source.epoch==2
    assert not any(x.causal_certificate for x in e)


def test_publication_does_not_retire_source_mutant():
    s,_=observe(State(),frame(source_accept=1,source_gen=7))
    s,e=observe(s,frame(1,staged=1))
    assert s.source is not None
    # Real event mutation adds native source_done while merger is outstanding.
    s,_=observe(s,frame(2,merge_accept=1,active_gen=7))
    with pytest.raises(ValueError): observe(s,frame(3,staged=1,source_done=1))


def test_offer_as_accept_mutant_rejected():
    s,_=observe(State(),frame(window_prefetch_accept=1))
    before=repr(s)
    with pytest.raises(ValueError,match='acceptance qualifier'):
        observe(s,frame(1,window_req_offer=1,window_req_ready=0,window_req_take=1))
    assert repr(s)==before


def test_wrong_native_row_on_owned_request():
    s,_=observe(State(),frame(window_prefetch_accept=1,window_prefetch_row=127,window_prefetch_user=9))
    with pytest.raises(ValueError,match='accepted row/user'):
        observe(s,frame(1,window_state=5,window_req_offer=1,window_req_take=1,window_row=128,window_active_user=9))


def test_code_and_scale_write_ack_before_block_publish():
    s,_=observe(State(),frame(window_blk_accept=1,window_blk_row=127,window_blk_user=9,window_blk_idx=15))
    for cycle,sector,state in [(1,0,1),(3,16,3)]:
        s,e=observe(s,frame(cycle,window_state=state,window_req_offer=1,window_req_take=1,window_req_we=1,window_req_tag=sector,window_sector=sector,window_row=127,window_active_user=9))
        s,e=observe(s,frame(cycle+1,window_state=state+1,window_write_done=1,window_block_publish=int(sector==16)))
    assert s.block is None and not s.requests


def test_source_cannot_complete_during_refill():
    s,_=observe(State(),frame(source_accept=1,source_gen=7,window_prefetch_accept=1))
    with pytest.raises(ValueError): observe(s,frame(1,source_done=1))


def test_sample_gap_reports_event_loss_before_mutation():
    s,_=observe(State(),frame())
    with pytest.raises(ValueError,match='sample gap'): observe(s,frame(2))


def test_reused_ckv_slot_gets_distinct_request_ordinal():
    s,_=observe(State(),frame(ckv_available=1,ckv_select_accept=1,ckv_fetch_accept=1))
    ordinals=[]
    for cycle in [1,3]:
        s,e=observe(s,frame(cycle,ckv_available=1,ckv0_req_take=1,ckv0_req_offer=1,ckv0_req_tag=0))
        ordinals.append(e[0].metadata[3])
        s,e=observe(s,frame(cycle+1,ckv_available=1,ckv0_rsp_take=1,ckv0_rsp_tag=0))
    assert ordinals==[1,2]


def test_all_thirteen_original_source_pins():
    import json
    authority=json.loads((ROOT/'results/rtl/simulation_observation_wrapper_4e383_20261002/hook_authority.json').read_text())
    assert len(authority['hooks'])==33
    for path,sha in authority['source_sha256'].items():
        data=subprocess.check_output(['git','show',prep.SOURCE+':'+path],cwd=ROOT)
        assert hashlib.sha256(data).hexdigest()==sha


def test_simulation_only_defaults_and_no_pc_busy_projection():
    copy=(ROOT/prep.COPY).read_text()
    assert 'parameter bit SIM_OBS_ENABLE = 0' in copy
    assert 'parameter bit SIM_OBS_CKV_SELECTED = 0' in copy
    assert 'simulation observer cannot be synthesized' in copy
    assert not any('pc' in f['expression'].lower() or 'busy' in f['expression'].lower() for f in prep.layout())
