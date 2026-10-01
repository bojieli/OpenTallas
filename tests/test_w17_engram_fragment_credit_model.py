import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w17_engram_fragment_credit_model import WordLease,RowLease,build

def test_ready_and_complete_storage_are_not_consumer_credit():
    w=WordLease(1,2)
    w.fragment(1,2,0,123)
    with pytest.raises(ValueError):w.store()
    with pytest.raises(ValueError):w.return_credit()
    w.fragment(1,2,1,7)
    with pytest.raises(ValueError):w.return_credit()
    assert w.store()==123|(7<<224)
    with pytest.raises(ValueError):w.stored_ack(1,2)
    w.consumer_accept();w.stored_ack(1,2);w.return_credit()
    with pytest.raises(ValueError):w.return_credit()

def test_stale_duplicate_reorder_and_ack_mutants():
    w=WordLease(4,5)
    with pytest.raises(ValueError):w.fragment(4,4,0,0)
    with pytest.raises(ValueError):w.fragment(4,5,1,0)
    w.fragment(4,5,0,0)
    with pytest.raises(ValueError):w.fragment(4,5,0,0)
    w.fragment(4,5,1,0);w.store();w.consumer_accept()
    with pytest.raises(ValueError):w.stored_ack(4,4)
    w.stored_ack(4,5)
    with pytest.raises(ValueError):w.stored_ack(4,5)

def test_all_eight_words_and_reverse_row_ack_hold_lease():
    row=RowLease(9,100)
    for word in row.words:
        with pytest.raises(ValueError):row.release()
        with pytest.raises(ValueError):row.row_consumer_done()
        word.fragment(word.tag,9,0,word.tag);word.fragment(word.tag,9,1,1)
        word.store();word.consumer_accept();word.stored_ack(word.tag,9);word.return_credit()
    row.row_consumer_done()
    with pytest.raises(ValueError):row.release()
    row.return_row_ack();row.release()
    with pytest.raises(ValueError):RowLease(9,(1<<24)-7)

def test_checker_has_no_physical_provider_or_free_cycle_credit():
    r=build()
    assert not r['physical_events_bound'] and r['physical_deadline'] is None
    assert not r['physical_admission'] and r['full_token_latency'] is None
