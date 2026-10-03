import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w2_nc6_count_utility_closure as m

def tick(x,n=4):
    for _ in range(n):x.tick()

def committed_rows(x,client,n):
    for slot in range(16):
        row=client*16+slot
        value=m.r.Ledger.pack(m.r.ISSUED if slot<n else m.r.FREE,tag=slot)
        x.memory[row]=m.c.seal(value,x.pc,row,0)

def set_count(x,client,n,version=0):
    m.write_record(x.memory,x.pc,'outstanding_cache',client,n|(version<<5))
    committed_rows(x,client,n)

def start(x,client,table_pending=False):
    # Count-unit model harness supplies the current committed rows, not a
    # backend or producer runtime proof. In full NC6 actual row journals own it.
    if not table_pending and not x.busy(client):
        n=x.count(client)[0]+x.pending(client)
        if 0<=n<=16:committed_rows(x,client,n)
    x.start(client,table_pending)

def test_fold_same_client_three_roles_and_secondary_commit():
    x=m.Counts(127);set_count(x,5,3)
    x.accepted(5,alloc=1,read_retire=1,write_retire=1)
    assert x.pending(5)==-1 and x.count(5)==(3,0)
    start(x,5);tick(x,3);assert x.count(5)==(3,0)
    x.tick();assert x.count(5)==(2,1) and x.admission_allowed(5)

def test_six_independent_secondary_writes():
    x=m.Counts()
    for i in range(6):set_count(x,i,10);x.accepted(i,write_retire=1);start(x,i)
    tick(x)
    assert [x.count(i) for i in range(6)]==[(9,1)]*6

def test_late_offered_consumer_preserved_during_active_worker():
    x=m.Counts();set_count(x,0,4)
    x.accepted(0,write_retire=1);start(x,0);tick(x,2)
    x.accepted(0,read_retire=1)
    assert x.pending(0)==-1 and not x.admission_allowed(0)
    tick(x,2);assert x.count(0)==(3,1) and not x.admission_allowed(0)
    start(x,0);tick(x);assert x.count(0)==(2,2) and x.admission_allowed(0)

def test_pending_may_not_start_ahead_of_table_commit():
    x=m.Counts();x.accepted(0,alloc=1)
    with pytest.raises(m.Refusal,match='busy/table'):start(x,0,table_pending=True)
    assert not x.admission_allowed(0,table_pending=True)

def test_cache_alone_does_not_authorize_credit():
    x=m.Counts()
    assert not x.admission_allowed(5,table_pending=True)
    assert not x.admission_allowed(5,reservation_or_query_live=True)
    set_count(x,5,16);assert not x.admission_allowed(5)

def test_under_overflow_and_offer_budget_latch_fault():
    for count,kw in [(0,dict(read_retire=1)),(16,dict(alloc=1))]:
        x=m.Counts();set_count(x,0,count);x.accepted(0,**kw)
        with pytest.raises(m.Refusal,match='over-under'):start(x,0)
        assert x.fault
    x=m.Counts();x.accepted(0,alloc=1)
    with pytest.raises(m.Refusal,match='offer-budget'):x.accepted(0,alloc=1)
    assert x.fault

def test_count_current_fault_blocks_all_secondary_commit():
    x=m.Counts()
    for i in range(6):x.accepted(i,alloc=1);start(x,i)
    before=x.memory[m.ids('outstanding_cache',5)[0]]
    x.memory[m.ids('count_worker',0)[0]]^=3
    tick(x);assert x.fault and x.memory[m.ids('outstanding_cache',5)[0]]==before

def test_stale_version_or_valid_code_target_mutant_refused():
    for mode in ('version','target'):
        x=m.Counts();x.accepted(0,alloc=1);start(x,0)
        if mode=='version':set_count(x,0,0,2)
        else:
            value=m.record(x.memory,x.pc,'count_worker',0)
            index=m.ids('outstanding_cache',0)[0]
            target=m.c.seal(9|(1<<5),x.pc,index,4)
            m.write_record(x.memory,x.pc,'count_worker',0,(value&~((1<<72)-1))|target)
        tick(x);assert x.fault and x.busy(0)

def test_count_version_wrap_requires_finished_previous_worker():
    x=m.Counts();set_count(x,0,4,15);x.accepted(0,read_retire=1);start(x,0)
    with pytest.raises(m.Refusal,match='busy'):start(x,0)
    tick(x);assert x.count(0)==(3,0)

def test_layout_exact_no_unpriced_writeports():
    x=m.model()
    assert x['storage']['words']==219 and x['storage']['bits_perPC']==15768
    assert x['ports']['maximum_primary_plus_count_writes']==15
    assert x['ports']['pending_delta_writers']==6
    assert not x['readiness']['full_NC6_RTL']

def test_utility_scrub_scheduler_without_mutable_selector():
    x=m.Repair(127);target=m.ids('protected_scheduler',0)[0]
    clean=x.memory[target];x.memory[target]^=1
    assert x.rescue();assert not x.idle(6)
    tick(x,3);assert x.memory[target]!=clean
    x.tick();assert x.memory[target]==clean and x.idle(6)

def test_duplicate_target_and_selfrepair_refused():
    x=m.Repair();x.memory[0]^=1;x.load(0,0)
    with pytest.raises(m.Refusal,match='already-owned'):x.load(6,0)
    own=m.ids('correction_context',6)[0];x.memory[own]^=1
    with pytest.raises(m.Refusal,match='self-repair'):x.load(6,own)

def test_interrupted_engine_rescued_then_four_fresh_edges():
    x=m.Repair();original=x.memory[0];x.memory[0]^=1;x.load(0,0);tick(x,2)
    context=m.ids('correction_context',0)[0];x.memory[context]^=1
    assert x.rescue();tick(x)
    assert not x.fault and ((x.get(0)>>90)&7)==0 and x.memory[0]!=original
    tick(x,3);assert x.memory[0]!=original
    x.tick();assert x.memory[0]==original and x.idle(0)

def test_other_utility_repairs_impaired_utility_context():
    x=m.Repair();x.memory[0]^=1;x.load(6,0);tick(x)
    index=m.ids('correction_context',6)[1];x.memory[index]^=2
    assert x.rescue() and not x.idle(7)
    tick(x);assert not x.fault and ((x.get(6)>>90)&7)==0
    tick(x);assert x.idle(6) and x.idle(7)

def test_both_utilities_impaired_failclosed():
    x=m.Repair()
    for e in (6,7):x.memory[m.ids('correction_context',e)[0]]^=1
    assert not x.rescue() and x.fault

def test_changed_scrub_snapshot_and_due_refused():
    x=m.Repair();x.memory[0]^=1;x.load(0,0);x.memory[0]^=2
    x.tick();assert x.fault
    x=m.Repair();x.memory[0]^=3;assert not x.rescue() and x.fault


def test_offer_epoch_holds_old_outputs_and_rejects_new_roles():
    counts=m.Counts();set_count(counts,0,4);offers=m.Offers(counts)
    for role in range(3):offers.reserve(0,role)
    offers.accept(0,1);start(counts,0)
    with pytest.raises(m.Refusal,match='epoch-closed'):offers.reserve(0,0)
    offers.accept(0,2);offers.accept(0,4)
    assert counts.pending(0)==-2
    with pytest.raises(m.Refusal,match='count-debt'):offers.reopen(0,source_copies_drained=True)
    tick(counts);start(counts,0);tick(counts)
    assert counts.count(0)==(3,2)
    offers.reopen(0,source_copies_drained=True)
    assert offers.get(0)==0

def test_net_zero_delta_still_reserves_count_epoch():
    x=m.Counts();set_count(x,0,2);o=m.Offers(x)
    o.reserve(0,0);o.reserve(0,1);o.accept(0,3)
    assert x.pending(0)==0 and not x.admission_allowed(0)
    start(x,0);tick(x);o.reopen(0,source_copies_drained=True)

def test_stop_only_cancels_unaccepted_request_role():
    x=m.Counts();o=m.Offers(x);o.reserve(0,0);o.cancel_unaccepted_request(0)
    o.reopen(0,source_copies_drained=True)
    o.reserve(0,0);o.accept(0,1)
    with pytest.raises(m.Refusal,match='not-unaccepted'):o.cancel_unaccepted_request(0)

def test_offer_duplicate_and_unreserved_ready_never_mint_delta():
    x=m.Counts();o=m.Offers(x);o.reserve(0,0)
    with pytest.raises(m.Refusal,match='unoffered'):o.accept(0,2)
    o.accept(0,1)
    with pytest.raises(m.Refusal,match='unoffered/duplicate'):o.accept(0,1)
    assert x.pending(0)==1

def test_full_count_does_not_block_existing_matched_completion_offer():
    x=m.Counts();set_count(x,5,16);o=m.Offers(x)
    with pytest.raises(m.Refusal,match='full'):o.reserve(5,0)
    o.reserve(5,2);o.accept(5,4);start(x,5);tick(x)
    o.reopen(5,source_copies_drained=True);assert x.count(5)==(15,1)

def test_repaired_count_target_restarts_four_quiet_edges():
    x=m.Counts();x.accepted(0,alloc=1);start(x,0);tick(x,2)
    repair=m.Repair();repair.memory=x.memory
    index=m.ids('count_worker',0)[0];x.memory[index]^=1
    assert repair.rescue();tick(repair)
    assert not repair.fault
    assert ((m.record(x.memory,x.pc,'count_worker',0)>>89)&7)==0
    tick(x,3);assert x.count(0)==(0,0)
    x.tick();assert x.count(0)==(1,1)


def test_ce_other_control_blocks_ready_acceptance_without_erasing_debt():
    x=m.Counts();o=m.Offers(x);o.reserve(0,0)
    index=m.ids('round_robin',0)[0];clean=x.memory[index];x.memory[index]^=1
    with pytest.raises(m.Refusal,match='quarantine'):o.accept(0,1)
    assert not x.fault and x.pending(0)==0 and o.get(0)&1
    repair=m.Repair();repair.memory=x.memory;assert repair.rescue();tick(repair)
    assert x.memory[index]==clean
    o.accept(0,1);assert x.pending(0)==1

def test_due_other_control_blocks_normal_phase_and_offer():
    x=m.Counts();o=m.Offers(x);o.reserve(0,0);o.accept(0,1);start(x,0)
    old=m.record(x.memory,x.pc,'count_worker',0)
    x.memory[m.ids('round_robin',0)[0]]^=3;x.tick()
    assert x.fault and m.record(x.memory,x.pc,'count_worker',0)==old


def test_no_hidden_before72_snapshot_needed_for_table_journals():
    old=m.r.Ledger.pack(m.r.FREE,tag=123,gen=15,version=4,lock=1)
    target=m.r.Ledger.pack(m.r.ISSUED,tag=456,gen=0,version=4)
    assert m.table_before_qualifies(old,target,4,'issue')
    assert not m.table_before_qualifies(old,target,3,'issue')
    for direction,role in [(0,'read'),(1,'write')]:
        issued=m.r.Ledger.pack(m.r.ISSUED,7,15,direction,15)
        held=m.r.Ledger.pack(m.r.WR_HELD if direction else m.r.RD_HELD,7,15,direction,15)
        free=m.r.Ledger.pack(m.r.FREE,7,15,direction,0)
        assert m.table_before_qualifies(issued,held,15,role+'_held')
        assert m.table_before_qualifies(held,free,15,role+'_retire')
        assert not m.table_before_qualifies(issued,free,15,role+'_retire')

def test_router_cost_counts_real_feedback_sources():
    x=m.model();router=x['price']['FF_write_router']
    assert router['maximum_table_data_fanin']==7 and router['table_input_sources_including_hold']==8
    assert router['utility_word_destinations']==438
    assert x['price']['body_mm2_perPC_ASSUMED']>m.c.model()['cell_price']['gross_body_mm2_perPC_ASSUMED']


def test_valid_code_cache_mutation_cannot_forge_table_count():
    x=m.Counts();set_count(x,0,4)
    # Real committed table has five issued rows after accepted allocation.
    x.accepted(0,alloc=1);committed_rows(x,0,5)
    m.write_record(x.memory,x.pc,'outstanding_cache',0,2)
    with pytest.raises(m.Refusal,match='table-count-conservation'):x.start(0)
    assert x.fault and not x.busy(0)

def test_quiet_source_edge_count_drain_and_reopen_calendar():
    x=m.Counts();set_count(x,0,3);o=m.Offers(x)
    for role in range(3):o.reserve(0,role)
    o.accept(0,7) # actual all-three ready at edge0; net -1
    trace=[]
    for edge in range(1,10):
        if edge==4:committed_rows(x,0,2) # accepted table journals reach commit
        if edge==5:x.start(0) # current rows visible, coded worker load
        else:x.tick()
        trace.append((edge,x.count(0)[0],x.busy(0)))
    assert trace[-2]==(8,3,True) and trace[-1]==(9,2,False)
    o.reopen(0,source_copies_drained=True)
    o.reserve(0,0) # next registered capture at edge10 -> backend edge18
    assert m.model()['calendar']['sameclient_backend_accept_II_min_quiet']==18

@pytest.mark.parametrize('engine',range(8))
@pytest.mark.parametrize('chunk',range(3))
def test_all_engine_context_word_classes_rescue(engine,chunk):
    x=m.Repair(113);target=engine*16 if engine<6 else 0
    clean=x.memory[target];x.memory[target]^=1;x.load(engine,target);tick(x,2)
    index=m.ids('correction_context',engine)[chunk];x.memory[index]^=1<<71
    assert x.rescue();tick(x)
    assert not x.fault and ((x.get(engine)>>90)&7)==0
    tick(x);assert x.memory[target]==clean and x.idle(engine)


def test_mutant_unchecked_ce_accept_is_detected(monkeypatch):
    x=m.Counts();o=m.Offers(x);o.reserve(0,0)
    x.memory[m.ids('round_robin',0)[0]]^=1
    monkeypatch.setattr(x,'normal_gate',lambda:None)
    o.accept(0,1)
    with pytest.raises(AssertionError):assert not (o.get(0)&8) # mutant consumed through quarantine

def test_mutant_missing_five_secondary_ports_is_detected():
    x=m.Counts()
    for i in range(6):set_count(x,i,5);x.accepted(i,read_retire=1);start(x,i)
    tick(x,3);before=[x.memory[m.ids('outstanding_cache',i)[0]] for i in range(5)]
    x.tick()
    for i in range(5):x.memory[m.ids('outstanding_cache',i)[0]]=before[i]
    with pytest.raises(AssertionError):assert [x.count(i)[0] for i in range(6)]==[4]*6

def test_mutant_utility_phase_not_restarted_is_detected(monkeypatch):
    x=m.Repair();clean=x.memory[0];x.memory[0]^=1;x.load(0,0);tick(x,2)
    index=m.ids('correction_context',0)[0];x.memory[index]^=1
    assert x.rescue()
    original=m.write_record
    def stale_phase(memory,pc,name,instance,value):
        if name=='correction_context' and instance==0 and value>>95 and ((value>>90)&7)==0:
            value|=2<<90
        original(memory,pc,name,instance,value)
    monkeypatch.setattr(m,'write_record',stale_phase)
    tick(x);tick(x,2)
    with pytest.raises(AssertionError):assert x.memory[0]!=clean # illegal early completion

def test_invalid_record_client_cannot_turn_empty_lookup_into_zero():
    x=m.Counts();o=m.Offers(x)
    with pytest.raises(m.Refusal,match='record-bounds'):o.reserve(6,0)


def test_source_bound_nine_table_ports_uses_mutually_exclusive_read_role():
    source=m.r.SOURCE.read_text()
    assert 'wire rd_take=rdv&&c_rsp_v[rdc]&&c_rsp_rdy[rdc];' in source
    assert 'if(rqv&&!rdv)' in source
    for rdv in (0,1):
        for rqv in (0,1):
            for rdy in (0,1):
                assert not (bool(rdv and rdy) and bool(rqv and not rdv))
    assert m.model()['ports']['primary_table_writers']==9
