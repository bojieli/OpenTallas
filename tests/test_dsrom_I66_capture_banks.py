import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_banks as C

@pytest.fixture(scope='module')
def allocation(): return C.allocation()
def test_all_phases(allocation):
    plans,depths=allocation
    assert len(plans)==768
    assert all(len(p['rows'])==576 for p in plans)
    assert all(sum(d)==576 and d.count(6)==32 and d.count(4)==96 for d in depths.values())
def test_padding(allocation):
    for d in allocation[1].values():
        assert sum(1<<(n-1).bit_length() for n in d)==640
        assert sum(d)*69==39744

def bank(allocation):
    p=allocation[0][0]; b=C.Banks(p['rows'],allocation[1][p['stage']]); return b,p
@pytest.mark.parametrize('seats,visible,exclusive,drained',[(575,True,True,True),(576,False,True,True),(576,True,False,True),(576,True,True,False)])
def test_reservation_rejects(allocation,seats,visible,exclusive,drained):
    b,p=bank(allocation)
    with pytest.raises(ValueError): b.reserve(1,0,seats,visible,exclusive,drained)
@pytest.mark.parametrize('mutation',['noreserve','sameedge','stale','badroot','duplicate','doubleport'])
def test_capture_negative(allocation,mutation):
    b,p=bank(allocation); root=p['rows'][0]
    if mutation!='noreserve': b.reserve(1,0,576,True,True,True)
    if mutation in ['duplicate','doubleport']: b.capture(0,root,1,1)
    with pytest.raises(ValueError):
        if mutation=='sameedge': b.capture(0,root,0,1)
        elif mutation=='stale': b.capture(0,root,1,2)
        elif mutation=='badroot': b.capture(0,(root+1)%128,1,1)
        elif mutation=='duplicate': b.capture(0,root,2,1)
        elif mutation=='doubleport':
            row=next(r for r,v in p['rows'].items() if v==root and r!=0)
            b.capture(row,root,1,1)
        else: b.capture(0,root,1,1)
def test_scalar_and_NBA_limits(allocation):
    b,p=bank(allocation); b.reserve(1,0,576,True,True,True)
    root=p['rows'][0]; b.capture(0,root,1,1)
    with pytest.raises(ValueError): b.drain(root,1)
    assert b.drain(root,2)==0
    with pytest.raises(ValueError): b.drain(root,2)
def test_drain_held_nooverflow(allocation):
    b,p=bank(allocation); b.reserve(1,0,576,True,True,True)
    # arbitrary arrival ordering, all accepted with no drains until complete
    for edge,row in enumerate(reversed(range(576)),1): b.capture(row,p['rows'][row],edge,1)
    assert sum(map(len,b.queues))==576
    with pytest.raises(ValueError): b.release(True,True,True,True)
    edge=577
    for root in range(128):
        while b.queues[root]: b.drain(root,edge); edge+=1
    with pytest.raises(ValueError): b.release(True,True,False,True)
    b.release(True,True,True,True)
    b.reserve(2,edge,576,True,True,True)
def test_trace_and_scope():
    m=C.model(); assert m['local_trace']['peak_writers_per_edge']==128
    assert m['local_trace']['scalar_drain_last']==998
    assert m['local_trace']['full_program_consumer_deadline'] is None
    assert not m['timeout']['proposed_4096_selected']
    assert not m['hardware_or_remote_or_token_credit']
def test_overflow_capacity_mutant(allocation):
    b,p=bank(allocation); b.depths=list(b.depths); root=p['rows'][0]; b.depths[root]=1
    b.reserve(1,0,576,True,True,True)
    rows=[r for r,v in p['rows'].items() if v==root]
    b.capture(rows[0],root,1,1)
    with pytest.raises(ValueError): b.capture(rows[1],root,2,1)
def test_mapping_omitted_plan():
    entry=next(C.records(C.OUT/'inputs/selected_matrix_plans.jsonl.gz')); m=copy.deepcopy(entry['matrix']); m['plans'].pop()
    with pytest.raises(ValueError): C.mapping(m)
def test_mapping_wrong_compiledNP():
    m=next(C.records(C.OUT/'inputs/selected_matrix_plans.jsonl.gz'))['matrix']; m['compiled_NP']=2048
    with pytest.raises(ValueError): C.mapping(m)
