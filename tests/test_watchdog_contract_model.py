import importlib.util
from pathlib import Path
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('watchdog_contract',ROOT/'tools/watchdog_contract_model.py')
M=importlib.util.module_from_spec(spec);sys.modules[spec.name]=M;spec.loader.exec_module(M)


def budget(n=1,response=10):
    return M.Budget(n,3,response,1,2,2,'test-only serial composition',('no competitor','one credit'))


def samples(pc=24,busy=0): return [M.Sample(pc,busy) for _ in range(4)]


def events(rank,kind,identity='op0/request0'): return [M.Event(rank,kind,identity)]


def test_rank_starvation_masked_by_other_rank_pc():
    trace=[(c,(24,c,24,24)) for c in range(32)]
    assert M.legacy_pc_timeout(trace,5) is None
    m=M.Watchdog([budget()]*4,diagnostic_pc_dwell=5)
    v=[]
    for c,pcs in trace:
        v=m.advance(c,[M.Sample(p) for p in pcs])
    assert (0,'OPERATION_DEADLINE') in v
    assert (0,'NO_OBSERVED_PROGRESS') in v
    assert (1,'OPERATION_DEADLINE') in v # PC movement cannot slide deadline


def test_spurious_busy_is_not_progress():
    m=M.Watchdog([None]*4,diagnostic_pc_dwell=5)
    for c in range(8): v=m.advance(c,samples(busy=c%2))
    assert (0,'NO_OBSERVED_PROGRESS') in v
    assert (0,'BOUND_MISSING') in v


def test_absent_response_age_is_not_reset_by_pc_progress():
    m=M.Watchdog([budget()]*4)
    m.advance(0,samples(),events(0,'offer')+events(0,'accept'))
    assert (0,'RESPONSE_DEADLINE') not in m.advance(10,samples(25))
    assert (0,'RESPONSE_DEADLINE') in m.advance(11,samples(26))


def test_late_response_cannot_erase_age_violation():
    m=M.Watchdog([budget()]*4)
    m.advance(0,samples(),events(0,'offer')+events(0,'accept'))
    assert (0,'RESPONSE_DEADLINE') in m.advance(11,samples(),events(0,'response'))


def test_request_not_admitted():
    m=M.Watchdog([budget()]*4)
    m.advance(0,samples(),events(0,'offer'))
    assert (0,'ADMISSION_DEADLINE') not in m.advance(3,samples())
    assert (0,'ADMISSION_DEADLINE') in m.advance(4,samples())


def test_long_healthy_refill_exceeds_pc_dwell_with_matched_progress():
    b=budget(n=30,response=4)
    m=M.Watchdog([b]*4,diagnostic_pc_dwell=5)
    for i in range(30):
        for c,kind in ((i*5,'offer'),(i*5+1,'accept'),(i*5+4,'response')):
            es=[M.Event(r,kind,f'op0/request{i}') for r in range(4)]
            assert m.advance(c,samples(),es)==[]
    assert m.advance(150,samples(),[M.Event(r,'complete') for r in range(4)])==[]
    assert M.legacy_pc_timeout([(c,(24,)*4) for c in range(151)],5)==6


def test_acceptance_heartbeats_do_not_extend_operation():
    b=M.Budget(2,1,8,0,0,0,'synthetic',('one credit',))
    m=M.Watchdog([b],diagnostic_pc_dwell=2)
    m.advance(0,[M.Sample(24)],[M.Event(0,'offer','a'),M.Event(0,'accept','a')])
    m.advance(8,[M.Sample(24)],[M.Event(0,'response','a')])
    m.advance(17,[M.Sample(24)],[M.Event(0,'offer','b'),M.Event(0,'accept','b')])
    v=m.advance(19,[M.Sample(25)])
    assert (0,'OPERATION_DEADLINE') in v
    assert (0,'RESPONSE_DEADLINE') not in v


def test_faults_checked_even_when_all_done():
    m=M.Watchdog([None]*4)
    ss=[M.Sample(0,done=True) for _ in range(4)];ss[2]=M.Sample(0,fault=1,done=True)
    assert (2,'FAULT') in m.advance(0,ss)


def test_done_rank_exempt_from_silence():
    m=M.Watchdog([None]*4,diagnostic_pc_dwell=1)
    s=samples();s[0]=M.Sample(24,done=True)
    m.advance(0,s)
    assert not any(r==0 for r,_ in m.advance(10,s))


@pytest.mark.parametrize('bad',[True,1.1,-1])
def test_invalid_budget_types(bad):
    with pytest.raises(ValueError): M.Budget(1,bad,1,1,1,1,'test',('condition',))


@pytest.mark.parametrize('bad',[True,0.5,-1])
def test_invalid_time_before_mutation(bad):
    m=M.Watchdog([None]*4)
    before=repr(m.ranks)
    with pytest.raises(ValueError): m.advance(bad,samples())
    assert repr(m.ranks)==before and m.cycle==-1


@pytest.mark.parametrize('k',['busy','cycle_count','state_change','credit','response_offer'])
def test_uncausal_progress_event_rejected(k):
    with pytest.raises(ValueError): M.Event(0,k,'a')


def test_duplicate_response_rejection_is_transactional():
    m=M.Watchdog([budget()]*4)
    m.advance(0,samples(),events(0,'offer')+events(0,'accept'))
    before=repr(m.ranks)
    with pytest.raises(ValueError,match='matching accepted'):
        m.advance(1,samples(),events(0,'response')+events(0,'response'))
    assert repr(m.ranks)==before and m.cycle==0


def test_spent_identity_cannot_be_reused():
    m=M.Watchdog([budget(2)]*4)
    m.advance(0,samples(),events(0,'offer')+events(0,'accept'))
    m.advance(1,samples(),events(0,'response'))
    before=repr(m.ranks)
    with pytest.raises(ValueError,match='spent'): m.advance(2,samples(),events(0,'offer'))
    assert repr(m.ranks)==before


def test_unknown_bound_does_not_become_deadlock_verdict():
    m=M.Watchdog([None]*4,diagnostic_pc_dwell=1)
    m.advance(0,samples())
    v=m.advance(1000000,samples())
    assert set(k for _,k in v)=={'BOUND_MISSING','NO_OBSERVED_PROGRESS'}


def test_single_measurement_cannot_admit_universal_timeout():
    b=M.Budget(2176,0,0,0,124368,0,'attempt9 observation',('cold no competitors',),'conditional')
    assert not b.universal_timeout_admitted
    assert b.operation==124368 # illustrative observation arithmetic only


def test_premature_completion_rejected():
    m=M.Watchdog([budget()]*4)
    with pytest.raises(ValueError,match='declared work'): m.advance(0,samples(),events(0,'complete'))
    assert m.cycle==-1


def test_deadline_verdict_cannot_be_cleared_by_late_completion():
    m=M.Watchdog([budget()])
    m.advance(0,[M.Sample(24)],[M.Event(0,'offer','a'),M.Event(0,'accept','a')])
    v=m.advance(20,[M.Sample(24)],[M.Event(0,'response','a'),M.Event(0,'complete')])
    assert (0,'RESPONSE_DEADLINE') in v and (0,'OPERATION_DEADLINE') in v
    assert (0,'RESPONSE_DEADLINE') in m.advance(21,[M.Sample(25,done=True)])


def test_fault_verdict_is_sticky():
    m=M.Watchdog([None])
    assert (0,'FAULT') in m.advance(0,[M.Sample(24,fault=1)])
    assert (0,'FAULT') in m.advance(1,[M.Sample(25)])


@pytest.mark.parametrize('field,value',[('pc',16384),('busy',32),('fault',256)])
def test_source_interface_widths(field,value):
    with pytest.raises(ValueError,match='interface width'): M.Sample(**{'pc':0,field:value})


def test_missing_scenario_assumptions_rejected():
    with pytest.raises(ValueError,match='conditions'):
        M.Budget(1,1,1,1,1,1,'observation','not a conditions tuple')


def test_connected_evidence_and_counterfactual_scope():
    sys.path.insert(0,str(ROOT/'tools'))
    import derive_watchdog_contract as D
    r=ROOT/'results/rtl/watchdog_contract_4e383_20261001/r1'
    case=D.connected_case((r/'attempt9_record.json').read_bytes(),(r/'attempt9_runtime.log').read_bytes())
    assert case['metrics']['refill']==124368
    assert case['legacy_first_failing_cycle']==112301
    assert case['healthy_reply_checkpoint_after_trigger']['cycle']==119999
    assert case['healthy_reply_checkpoint_after_trigger']['replies']==1886
    assert case['stage_dwell_cycles']==124369
    assert case['constant_pc_is_counterfactual'] is True
    assert case['universal_bound_admitted'] is False


def test_connected_log_hash_mismatch_rejected():
    sys.path.insert(0,str(ROOT/'tools'))
    import derive_watchdog_contract as D
    r=ROOT/'results/rtl/watchdog_contract_4e383_20261001/r1'
    with pytest.raises(ValueError,match='log hash'):
        D.connected_case((r/'attempt9_record.json').read_bytes(),b'fabricated PASS')


def test_done_cannot_hide_missing_declared_responses():
    m=M.Watchdog([budget()])
    assert (0,'DONE_WITH_UNRETIRED_SERVICE') in m.advance(0,[M.Sample(24,done=True)])
