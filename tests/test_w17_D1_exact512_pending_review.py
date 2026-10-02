import copy,hashlib,json
from pathlib import Path
import pytest
from tools.w17_D1_exact512_pending_review import review
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'results/uarch/w17_D1_exact512_pending_actual_20261002_r1'
def inputs():
    return (B/'gdb.log').read_text(),json.loads((B/'receipt.json').read_text()),json.loads((ROOT/'results/uarch/w17_D1_exact512_pending_probe_20261002/plan.json').read_text())
def test_actual_exact_endpoint_not_descriptor_or_completion():
    t,r,p=inputs();a=review(t,r,p)
    assert a['fulltoken'] is False and a['first_return_bound']=='BOUND_MISSING'
    assert a['marker_counts']==dict(D1_REAL_DESCRIPTOR=0,D1_REAL_ACCEPT=0,D1_REAL_RESPONSE=0)
    assert a['ledger']==dict(reads=0,returns=0,writes=0,acks=0,pending=0)
@pytest.mark.parametrize('field,value',[('GDB_exit',1),('actual_argv',['other']),('cwd','/other'),('default_prog_still_absent',False),('input_postchecks',{'binary':False})])
def test_bad_execution_or_binding_cannot_qualify(field,value):
    t,r,p=inputs();r[field]=value
    with pytest.raises(ValueError):review(t,r,p)
@pytest.mark.parametrize('before,after',[
    ('D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=512','D1_PREFIX_CYCLE_CAP_NO_COMPLETION_CREDIT cycles=513'),
    ('time_ps=516000 cycles=512','time_ps=516001 cycles=512'),
    ('D1_INFERIOR_EXIT code=0','D1_INFERIOR_EXIT code=1'),
    ('D1_OWNER_000 value=512','D1_OWNER_000 value=511'),
    ('D1_OWNER_001','D1_OWNER_000'),
    ('D1_QUALIFIED_PRIME time_ps=7501 row=0 rn=1','D1_QUALIFIED_PRIME time_ps=7501 row=0 rn=0'),
])
def test_changed_actual_trace_rejects_after_rehash(before,after):
    t,r,p=inputs();assert before in t;t=t.replace(before,after,1);r['log_SHA256']=hashlib.sha256(t.encode()).hexdigest()
    with pytest.raises(ValueError):review(t,r,p)
def test_late_actual_fault_overrides_snapshot():
    t,r,p=inputs();t+='\nD1_SOURCE_OR_LEDGER_FAULT\n';r['log_SHA256']=hashlib.sha256(t.encode()).hexdigest()
    with pytest.raises(ValueError):review(t,r,p)
