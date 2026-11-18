"""Actual SOT read/retire encoding carries an opt-in last-q lifetime fence."""
import copy
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lower_svc as L

def source():
    at = {'SOT': 100, 'SMJ_SO': 1000}
    at.update({'SMJ_OP'+str(g): 1045+33*g for g in range(16)})
    last = at['SMJ_OP15']+32
    return SimpleNamespace(owner=0, tag=0, mutant=None, hs=16), dict(at=at, words=[(last, 0)])

def test_fence_reencodes_actual_reads_retires_and_windows():
    job, s = source()
    old = L.sot_booking_for(job, s)
    last = s['words'][-1][0]
    assert old['done']['E'] < last+2
    s['job_last_q_edge'] = last
    new = L.sot_booking_for(job, s)
    assert min(new['done'].values()) >= last+2
    assert new['words'] != old['words']
    assert new['entry_window'][1] >= old['entry_window'][1]
    for head, before in old['heads'].items():
        after = new['heads'][head]
        assert (after['first'], after['last']) == (before['first'], before['last'])
        assert after['read']-before['read'] == after['retire']-before['retire'] >= 0
    for half, price in new['lifetime_fence']['halves'].items():
        assert new['done'][half]-old['done'][half] == price['read_retire_delay_edges']
        assert price['done_after'] == new['done'][half]
    mutant = copy.deepcopy(old)
    mutant['done'] = dict(new['done'])
    assert mutant['words'] != new['words']

def test_absent_fence_preserves_booking_and_fence_can_be_free():
    job, s = source()
    a = L.sot_booking_for(job, s)
    assert 'lifetime_fence' not in a
    s['words'] = []
    s['job_last_q_edge'] = 0
    b = L.sot_booking_for(job, s)
    assert a['words'] == b['words'] and a['done'] == b['done']
    assert all(x['read_retire_delay_edges'] == 0 for x in b['lifetime_fence']['halves'].values())

@pytest.mark.parametrize('bad', [-1, 1.5, True, 10])
def test_bad_or_early_fence_rejected(bad):
    job, s = source()
    s['job_last_q_edge'] = bad
    with pytest.raises(ValueError): L.sot_booking_for(job, s)
