import ast,inspect,sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import ds_hbm_current_calendar_adapter_r50 as a
from h4_hbm_w19_pc10_endpoints import ProductionPC10 as O

def test_current_source_guard_positive():
 import h3_complete_native_calendar as c
 assert a.current_source_mismatch(c.execute_ds_provider_group128) is False

def test_current_source_mutant_refuses():
 raw=(a.ROOT/'tools/h3_complete_native_calendar.py').read_bytes()
 with pytest.raises(ValueError,match='exact current'):a.verify_current_source(raw+b'\n# mutant',a.inputs()['calendar.py'])

def test_executor_semantics_mutant_refuses():
 raw=(a.ROOT/'tools/h3_complete_native_calendar.py').read_bytes()
 with pytest.raises(ValueError,match='unchanged'):a.verify_current_source(raw,a.inputs()['calendar.py'].replace(b'output=np.empty(8192,np.float32)',b'output=np.empty(4096,np.float32)'))

def test_runtime_function_substitution_refuses():
 with pytest.raises(ValueError,match='runtime executor'):a.current_source_mismatch(lambda:None)

def test_only_one_guard_changed_all_other_endpoint_AST_preserved():
 original=ast.parse(Path(inspect.getmodule(O).__file__).read_bytes());cl=next(n for n in original.body if isinstance(n,ast.ClassDef) and n.name=='ProductionPC10');fn=next(n for n in cl.body if isinstance(n,ast.FunctionDef) and n.name=='execute')
 assert sum(isinstance(n,ast.If) and "inputs()['calendar.py']" in ast.unparse(n.test) for n in fn.body)==1
 assert a.CurrentPC10.ready is a.ProductionPC10.ready
 assert a.CurrentPC10.identity is a.ProductionPC10.identity
 class Prefix:pass
 assert a.engine_class(Prefix).__name__=='Engine'
 with pytest.raises(ValueError,match='port-bound'):a.engine_class(Prefix,finite_pc10=True,physical_backend=True)


def test_compact_shared_source_guard_preserves_original_and_exact_current():
 import h3_complete_native_calendar as c
 assert a.shared_provider_source_mismatch(a.OriginalSectorProvider) is False
 exact=c.compact_sector_provider_class(a.OriginalSectorProvider)
 assert a.shared_provider_source_mismatch(exact) is False
 class Unsupported(a.OriginalSectorProvider):pass
 with pytest.raises(ValueError,match='compact addressed'):a.shared_provider_source_mismatch(Unsupported)

def test_compact_shared_actual_bytes_and_owner_drain(tmp_path,monkeypatch):
 import h3_complete_native_calendar as c
 import hbm_bound_event_journal_r30 as journal
 budget=c.CompactJournalBudget(tmp_path/'journal',1<<24)
 compact=c.compact_sector_provider_class(a.OriginalSectorProvider)
 monkeypatch.setattr(journal,'BoundSectorProvider',compact)
 factory=a.CurrentSharedFactory(budget)
 owner=dict(PC=10,rank=3,SM=7,generation=1,version='DeepSeek.10.z.68')
 memory=factory(owner);payload=bytes(range(32))
 memory.transact(0,write=True,payload=payload,length=32)
 assert memory.transact(0,write=False,payload=b'',length=32)==payload
 assert not memory.p.live and not memory.p.queue and not memory.p.calendar and not memory.p.resident
 memory.p.events.flush();events=list(memory.p.events)
 assert sum(x['event']=='validated_reverse_grant' for x in events)==2
 assert any(x.get('payload_sha256') for x in events if x['event']=='software_read_capture')
 assert a.CurrentSharedFactory.__init__ is a.OriginalSharedFactory.__init__
