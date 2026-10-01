import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w17_engram_fragment_credit_model import WordLease,RowLease,build
OWNER=dict(source_home=0,consumer_rank=0,layer=1,column=0,row=123,image_sha256="0"*64)

def test_ready_and_complete_storage_are_not_consumer_credit():
    w=WordLease(1,2,OWNER)
    w.fragment(1,2,0,123)
    with pytest.raises(ValueError):w.store()
    with pytest.raises(ValueError):w.return_credit(w.tag,w.epoch,OWNER)
    w.fragment(1,2,1,7)
    with pytest.raises(ValueError):w.return_credit(w.tag,w.epoch,OWNER)
    assert w.store()==123|(7<<224)
    with pytest.raises(ValueError):w.stored_ack(1,2,OWNER)
    w.consumer_accept();w.stored_ack(1,2,OWNER);w.return_credit(w.tag,w.epoch,OWNER)
    with pytest.raises(ValueError):w.return_credit(w.tag,w.epoch,OWNER)

def test_stale_duplicate_reorder_and_ack_mutants():
    w=WordLease(4,5,OWNER)
    with pytest.raises(ValueError):w.fragment(4,4,0,0)
    with pytest.raises(ValueError):w.fragment(4,5,1,0)
    w.fragment(4,5,0,0)
    with pytest.raises(ValueError):w.fragment(4,5,0,0)
    w.fragment(4,5,1,0);w.store();w.consumer_accept()
    with pytest.raises(ValueError):w.stored_ack(4,4,OWNER)
    w.stored_ack(4,5,OWNER)
    with pytest.raises(ValueError):w.stored_ack(4,5,OWNER)

def test_all_eight_words_and_reverse_row_ack_hold_lease():
    row=RowLease(9,100,OWNER)
    for word in row.words:
        with pytest.raises(ValueError):row.release(9,100,OWNER)
        with pytest.raises(ValueError):row.row_consumer_done()
        word.fragment(word.tag,9,0,word.tag);word.fragment(word.tag,9,1,1)
        word.store();word.consumer_accept();word.stored_ack(word.tag,9,OWNER);word.return_credit(word.tag,9,OWNER)
    row.row_consumer_done()
    with pytest.raises(ValueError):row.release(9,100,OWNER)
    row.return_row_ack(9,100,OWNER);row.release(9,100,OWNER)
    with pytest.raises(ValueError):RowLease(9,(1<<24)-7,OWNER)

def test_checker_has_no_physical_provider_or_free_cycle_credit():
    r=build()
    assert not r['physical_events_bound'] and r['physical_deadline'] is None
    assert not r['physical_admission'] and r['full_token_latency'] is None

def test_row_ack_and_reverse_credit_require_actual_expected_identity():
    row=RowLease(9,100,OWNER)
    for word in row.words:
        word.fragment(word.tag,9,0,0);word.fragment(word.tag,9,1,0)
        word.store();word.consumer_accept();word.stored_ack(word.tag,9,OWNER)
        with pytest.raises(ValueError):word.return_credit(word.tag,8,OWNER)
        with pytest.raises(ValueError):word.return_credit(word.tag,9,dict(OWNER,consumer_rank=1))
        word.return_credit(word.tag,9,OWNER)
    row.row_consumer_done()
    for epoch,tag,owner in [(8,100,OWNER),(9,101,OWNER),(9,100,dict(OWNER,source_home=1)),
                            (9,100,dict(OWNER,row=124)),(9,100,dict(OWNER,image_sha256='1'*64))]:
        with pytest.raises(ValueError):row.return_row_ack(epoch,tag,owner)
    row.return_row_ack(9,100,OWNER)
    with pytest.raises(ValueError):row.release(8,100,OWNER)
    row.release(9,100,OWNER)
