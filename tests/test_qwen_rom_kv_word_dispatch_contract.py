import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import qwen_rom_kv_word_dispatch_contract as P


def fixture():return P.WordDispatch(9,{'word0':{'s0b0','s1b0'},'word1':{'s0b1','s1b1'}})


def test_word_dispatch_can_precede_unrelated_word_without_early_cohort_reuse():
    d=fixture();d.capture(9,'s0b0',True);d.capture(9,'s1b0',True)
    assert d.dispatchable('word0') and not d.dispatchable('word1')
    d.commit(9,'word0',True)
    assert d.grantable('s0b0') and not d.cohort_retirable()
    d.ack(9,'s0b0',True);d.ack(9,'s1b0',True)
    assert not d.cohort_retirable()


def test_backpressure_visibility_and_reader_debt_block_early_ACK():
    d=fixture();d.capture(9,'s0b0',False);assert not d.captured
    d.capture(9,'s0b0',True);d.capture(9,'s1b0',True)
    d.commit(9,'word0',False);assert not d.grantable('s0b0')
    d.commit(9,'word0',True);d.readers['word0']=1
    with pytest.raises(ValueError):d.ack(9,'s0b0',True)
    d.readers['word0']=0;d.ack(9,'s0b0',False);assert not d.acked


def test_stale_duplicate_and_wrong_identity_do_not_mutate_owned_state():
    d=fixture()
    with pytest.raises(ValueError):d.capture(8,'s0b0',True)
    with pytest.raises(ValueError):d.capture(9,'invented',True)
    assert not d.captured
    d.capture(9,'s0b0',True)
    with pytest.raises(ValueError):d.capture(9,'s0b0',True)
    assert d.captured=={'s0b0'}


def test_member_touching_multiple_words_waits_all_visible():
    d=P.WordDispatch(1,{'a':{'shared','one'},'b':{'shared','two'}})
    for member in ['shared','one','two']:d.capture(1,member,True)
    d.commit(1,'a',True);assert not d.grantable('shared')
    d.commit(1,'b',True);assert d.grantable('shared')
    for member in ['shared','one','two']:d.ack(1,member,True)
    assert d.cohort_retirable()


def test_rejection_model_and_unknown_latency_block_physical_delta():
    m=P.build();assert json.loads(json.dumps(m))==P.R.obj(P.OUT/'model-r2.json')
    assert m['rejected']['gain_fraction']<.01
    assert m['rejected']['service_increment_mm2']==pytest.approx(.83974664736)
    assert m['topology']['group_credits']==16 and m['topology']['global_credits']==128
    assert m['topology']['pending_per_PC']==64 and m['topology']['words_per_pool']==80
    assert m['gross_control_price']['known_mm2']>0
    assert m['finite_calendar_s'] is None and m['gain_fraction'] is None
    assert not any(m[k] for k in ['candidate_replayed','dispatch_dependency_source_bound','physical_delta_authorized','build_admission','default_enabled'])
    for p,h in m['source_pins'].items():assert P.R.sha(Path(p))==h
