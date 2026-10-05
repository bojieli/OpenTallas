import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w2_nc6_protection_reconciliation as m

def advance(l,n=4):
    for _ in range(n):l.tick()

def issued(direction=0):
    l=m.Ledger(127);r=l.reserve(5,0xffffffff,15,direction)
    l.accept_request(r,0xffffffff,15,direction);advance(l)
    return l,r

def test_pending_issue_conserves_debt_and_stalls_early_return():
    l=m.Ledger();r=l.reserve(5,10,2,0)
    assert l.debts()==set()
    l.accept_request(r,10,2,0)
    assert l.debts()=={r}
    for _ in range(3):
        with pytest.raises(m.Refusal,match='bank-commit-stall'):l.match_return(5,10,2,0)
        assert l.debts()=={r};l.tick()
    l.tick();assert l.match_return(5,10,2,0)==r

def test_pending_duplicate_is_not_hidden_by_free_table():
    l=m.Ledger();r=l.reserve(5,10,2,0);l.accept_request(r,10,2,0)
    with pytest.raises(m.Refusal,match='duplicate-pending'):l.reserve(5,10,2,0)

def test_release_waits_for_commit_not_consumer_handshake():
    l,r=issued();l.match_return(5,0xffffffff,15,0);advance(l)
    assert l.current(r)['state']==m.RD_HELD
    l.consume(r,0);assert l.debts()=={r}
    advance(l,3);assert l.debts()=={r}
    l.tick();assert not l.debts()
    with pytest.raises(m.Refusal,match='not-held'):l.consume(r,0)

def test_direction_generation_client_and_duplicate_refusal():
    l,r=issued(1)
    for args in [(5,0xffffffff,15,0),(5,0xffffffff,0,1),(6,0xffffffff,15,1)]:
        with pytest.raises(m.Refusal):l.match_return(*args)
    l.match_return(5,0xffffffff,15,1);advance(l);l.consume(r,1);advance(l)
    with pytest.raises(m.Refusal,match='nonunique'):l.match_return(5,0xffffffff,15,1)

def test_unaccepted_cancel_cannot_cancel_accepted_journal():
    l=m.Ledger();r=l.reserve(0,1,0,0);l.cancel_unaccepted(r)
    assert not l.reserved and not l.debts()
    r=l.reserve(0,1,0,0);l.accept_request(r,1,0,0)
    with pytest.raises(m.Refusal,match='accepted-debt'):l.cancel_unaccepted(r)

def test_sixteen_and_disjoint_nine_journal_limit():
    l=m.Ledger()
    for k in range(16):
        r=l.reserve(5,k,0,0);l.accept_request(r,k,0,0);advance(l)
    with pytest.raises(m.Refusal,match='full'):l.reserve(5,99,0,0)
    l=m.Ledger()
    for k in range(9):
        r=l.reserve(k%6,k,0,0);l.accept_request(r,k,0,0)
    r=l.reserve(0,100,0,0)
    with pytest.raises(m.Refusal,match='journal-full'):l.accept_request(r,100,0,0)
    assert r in l.reserved and len(l.journals)==9 and len(l.debts())==9

def test_current_fault_blocks_entire_commit_batch_and_credit():
    l=m.Ledger()
    for k in range(2):
        r=l.reserve(k,k,0,0);l.accept_request(r,k,0,0)
    saved=l.rows[16];l.rows[0]^=3;advance(l)
    assert l.fault and l.rows[16]==saved and len(l.journals)==2

def test_snapshot_and_row_version_aba_query_blocks_reuse():
    l,r=issued();l.match_return(5,0xffffffff,15,0);advance(l)
    l.query(r)
    with pytest.raises(m.Refusal,match='live-copy'):l.consume(r,0)
    l.drop_query(r);l.consume(r,0);advance(l)
    assert l.current(r)['version']==1
    l.query(r)
    r2=l.reserve(5,1,0,0);assert r2!=r

def test_new_fault_or_write_before_commit_refuses():
    l=m.Ledger();r=l.reserve(0,1,0,0);l.accept_request(r,1,0,0)
    l.rows[r]=m.codec.seal(m.Ledger.pack(m.FREE,version=1),0,r,0)
    advance(l);assert l.fault and len(l.journals)==1

def test_rearm_requires_all_local_and_external_copies():
    l,r=issued()
    with pytest.raises(m.Refusal,match='local-debt'):l.rearm(True,True,True)
    l.match_return(5,0xffffffff,15,0);advance(l);l.consume(r,0);advance(l)
    for fences in [(False,True,True),(True,False,True),(True,True,False)]:
        with pytest.raises(m.Refusal,match='external-copy'):l.rearm(*fences)
    assert l.rearm(True,True,True)

def test_source_bound_early_calendar_is_additive_not_old_rewrite():
    x=m.model()
    assert x['early_return_calendar']['extra_bank_stall_edges']==3
    assert x['early_return_calendar']['early_read_edges']==11
    assert x['early_return_calendar']['minimum_clean_request_edges']==8
    assert x['early_return_calendar']['selected_request_read_write_delta_from_unprotected']==[7,6,6]
    assert x['protected_bits']==13608
    assert not x['readiness']['engine_RTL_admitted']
