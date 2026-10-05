import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('d1',ROOT/'tools/w17_D1_PC24_inputs.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def event(kind,cycle):return dict(kind=kind,cycle=cycle,row=0,sector=16)
@pytest.mark.parametrize('cut,req,rsp,rows',[(9,0,0,0),(10,1,0,0),(11,1,0,0),(12,1,1,1)])
def test_preedge_cut_does_not_backdate_reply(cut,req,rsp,rows):
    x=m.summary([event('request',10),event('reply',12)],cut)
    assert (x['requests'],x['replies'],x['rows_scale_returned'])==(req,rsp,rows)
    assert x['pending']==req-rsp
    assert not x['is_original_live_observation']
def test_exact_prior_calendar_and_scope():
    x=m.build()
    assert x['calendar']['metrics']['refill']==124368
    assert x['calendar']['metrics']['staged']==136669
    assert x['calendar']['last_scale_response']==136667
    assert x['watchdog']['last_ANY_rank_PC_change_inferred_from_tickwise_host']==12356
    assert x['conditional_fixture_at_original_terminal_cycle']['replies']==1752
    assert x['whole_L0_prediction'] is None
    assert not x['original_causal_deadlock_proof']
    assert x['fixture_binding']['writes']==0
    assert x['fixture_binding']['original_postwriter_bank_queue_state_not_reconstructed']
