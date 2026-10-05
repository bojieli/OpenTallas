import ast
import inspect
import subprocess
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_hbm_additive_endpoint_join_r54 as a


def test_exact_calendar_and_original_executor_AST():
    c=a.verify_calendar()
    assert a.successor_source_mismatch(c.execute_ds_provider_group128) is False
    with pytest.raises(ValueError,match='runtime executor object'):
        a.successor_source_mismatch(lambda:None)


def test_guard_is_only_endpoint_change():
    def method(cls):
        module=inspect.getmodule(cls);tree=ast.parse(Path(module.__file__).read_bytes())
        owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls.__name__)
        return next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
    fn=method(a.Original);before=ast.dump(fn,include_attributes=False)
    a.endpoint_transform(fn)
    guards=[n for n in fn.body if isinstance(n,ast.If) and 'successor_source_mismatch' in ast.unparse(n.test)]
    assert len(guards)==1 and before!=ast.dump(fn,include_attributes=False)
    assert a.SuccessorPC10.ready is a.ProductionPC10.ready
    assert a.SuccessorPC10.identity is a.ProductionPC10.identity


def test_default_off_and_physical_refusal():
    class Prefix:pass
    assert a.engine_class(Prefix).__name__=='Engine'
    with pytest.raises(ValueError,match='port-bound'):
        a.engine_class(Prefix,finite_pc10=True,physical_backend=True)


def test_actual_constructor_shared_bytes_and_helper_role(tmp_path):
    script='''
import sys
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path.cwd()/'tools'))
import ds_hbm_additive_endpoint_join_r54 as a
import hbm_bound_event_journal_r30 as journal
import h4_hbm_w19_pc10_endpoints as endpoint
import ds_producer_checkpoint_resume_v2 as helper
c=a.verify_calendar()
receipt=a.install([journal,endpoint])
assert receipt['original_constructor_object_retained']
assert journal.BoundSectorProvider.__init__ is a.OriginalSectorProvider.__init__
assert a.verify_installed_provider(journal.BoundSectorProvider)
class Forged(a.OriginalSectorProvider):
 __init__=a.OriginalSectorProvider.__init__
try:a.verify_installed_provider(Forged)
except ValueError:pass
else:raise AssertionError('unbound logger accepted')
budget=c.CompactJournalBudget(Path(sys.argv[1])/'events',1<<24)
factory=endpoint.ProductionSharedFactory(budget)
owner=dict(PC=10,rank=3,SM=7,generation=1,tile=0,template='source')
memory=factory(owner)
payload=bytes(range(32))
memory.transact(0,write=True,payload=payload,length=32)
assert memory.transact(0,write=False,payload=b'',length=32)==payload
assert not memory.p.live and not memory.p.queue and not memory.p.calendar and not memory.p.resident
rows=list(memory.p.events)
assert sum(e['event']=='validated_reverse_grant' for e in rows)==2
assert any(e.get('payload_sha256') for e in rows if e['event']=='software_read_capture')
p=SimpleNamespace(journal_budget=budget)
e=SimpleNamespace(groups=SimpleNamespace(shared=factory))
assert helper.shared_factory(p,e) is factory
try:helper.scope_role_proof(p,e)
except KeyError as err:
 assert err.args==('h3_complete_native_calendar_successor_r1.py',)
 print('PRESERVED_COMPACT_V2_ROLE_ENROLLMENT_REFUSAL')
else:raise AssertionError('legacy role unexpectedly accepted compact backend')
print('PASS_ACTUAL_SHARED_CONSTRUCTOR_BYTES_REVERSE_COMPONENT')
'''
    r=subprocess.run([sys.executable,'-c',script,str(tmp_path)],cwd=a.ROOT,capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'PASS_ACTUAL_SHARED' in r.stdout
    assert 'PRESERVED_COMPACT_V2' in r.stdout
