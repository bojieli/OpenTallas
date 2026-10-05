import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).parents[1]/'tools'))
import dsrom_I66_terminal_destination_review as M

def fixture():
    def e(k,n,a=-1,b=-1,c=0):return dict(M.IDENTITY,kind=k,edge=n,a=a,b=b,c=c)
    rows=[e('op_accept',10),e('EID_VM_read_accept',11),e('phase_accept',15)]
    rows += [e('root_row_accept',414,r%128,r,M.ORACLE) for r in range(576)]
    rows += [e('VM_write_accept',415,r%128,398720+r,M.ORACLE) for r in range(576)]
    rows += [e('final_destination_visible',415,398720+r,c=M.ORACLE) for r in range(576)]
    rows += [e('phase_retire',422),e('all_source_root_writer_drained',462,102400,576,576)]
    return rows

R=dict(source_commit=M.SOURCE,finish_monotonic=1,stages=[dict(name='runtime',returncode=0)],result='FAIL',calibration=dict(result='FAIL'))

def test_original_failed_wrapper_preserved():
    r=M.review(fixture(),R)
    assert r['original_wrapper_verdict']=='FAIL'
    assert r['op_to_adapter_retire_edges']==412
    assert not r['prediction_calendar_admitted']

@pytest.mark.parametrize('kind',['root_row_accept','VM_write_accept','final_destination_visible'])
def test_missing_dependency_rejected(kind):
    with pytest.raises(ValueError):M.review([e for e in fixture() if e['kind']!=kind],R)

def test_wrong_nonzero_oracle_rejected():
    rows=fixture();next(e for e in rows if e['kind']=='final_destination_visible')['c']=0
    with pytest.raises(ValueError):M.review(rows,R)

def test_wrong_owner_rejected():
    rows=fixture();rows[0]['rank']=1
    with pytest.raises(ValueError):M.review(rows,R)

def test_retire_before_sink_rejected():
    rows=fixture();rows.insert(3,dict(M.IDENTITY,kind='phase_retire',edge=20))
    with pytest.raises(ValueError):M.review(rows,R)
