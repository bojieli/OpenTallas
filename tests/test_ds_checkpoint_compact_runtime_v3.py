"""Independent actual compact-component subprocess, never a production prefix."""
from pathlib import Path
import subprocess
import sys
import json
import pytest

ROOT=Path(__file__).resolve().parents[1]

SCRIPT=r'''
import sys,json,copy
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'tools'),str(Path.cwd()/'tests')]
import test_ds_producer_checkpoint_resume_v3 as T
import ds_producer_checkpoint_resume_v3 as C
import ds_hbm_additive_endpoint_join_r54 as J
import hbm_bound_event_journal_r30 as journal
import h3_ds_checkpoint_provider_r30 as base
import h3_ds_query_provider_r36 as query
import h4_hbm_w19_pc10_endpoints as endpoint
calendar=J.verify_calendar()
receipt=J.install([journal,base,query,endpoint])
assert receipt['original_constructor_object_retained']
root=Path(sys.argv[1]);mode=sys.argv[2]
p,e,w=T.constructor(root,'old',shared=True,run_stop=10)
for op in e.native['instructions']:
 e.execute_operation(op);w.seen.add((op['pc'],'v'+str(op['pc']),0,1,'data'))
memory=e.groups.shared(dict(PC=10,rank=0,SM=3,generation=1,tile=0,template='actual_component'))
payload=bytes(range(32));memory.transact(0,write=True,payload=payload,length=32)
assert memory.transact(0,write=False,payload=b'',length=32)==payload
proof=C.scope_role_proof(p,e)
assert proof['compact_runtime_source_sha256']
if mode=='live':
 memory.p.events.validator.live[0]=['unretired']
 try:C.quiescent(p,e)
 except ValueError:print('PASS_COMPACT_LIVE_REFUSAL');sys.exit(0)
 raise AssertionError('live validator accepted')
if mode=='fault':
 memory.p.events.fault='source fault retained'
 try:C.quiescent(p,e)
 except ValueError:print('PASS_COMPACT_FAULT_REFUSAL');sys.exit(0)
 raise AssertionError('faulted stream accepted')
if mode=='counter':
 memory.p.events.validator.generations[0]+=1
 try:C.quiescent(p,e)
 except ValueError:print('PASS_COMPACT_COUNTER_REFUSAL');sys.exit(0)
 raise AssertionError('wrong watermark accepted')
projection=C.project_checkpoint(e,p,w,boundary_pc=10,destination=root/'saved')
assert projection['old_journal_bytes']>p.journal_budget.path.stat().st_size
contract={'identity':C.identity(p,e)}
seal=C.capture_quiescent(e,p,w,boundary_pc=10,destination=root/'saved',source_contract=contract)
closure=json.loads((root/'saved/state.json').read_text())
assert closure['historical_journal_inventory']['hashes_complete']
assert any(r['path'].endswith('.events') for r in closure['historical_journal_inventory']['files'])
assert any(r['path'].endswith('.index') for r in closure['historical_journal_inventory']['files'])
assert sum(f.stat().st_size for f in (root/'saved').iterdir())<=projection['filesystem_reservation_bytes']
if mode in ('tamper','extra'):
 file=next((root/'old').glob('*.events'))
 if mode=='tamper':
  with file.open('ab') as f:f.write(b'tampered')
 else:
  (root/'old'/'99999999.events').write_bytes(b'')
  (root/'old'/'99999999.index').write_bytes(b'')
 try:C.verify_checkpoint(root/'saved',source_contract=contract,next_pc=11,
  constructor_contract={'identity':contract['identity'],'checkpoint_receipt':seal})
 except ValueError:print('PASS_COMPACT_JOURNAL_TAMPER_REFUSAL');sys.exit(0)
 raise AssertionError('changed historic journal accepted')
old_state=C.lifecycle_state(memory.p)
p2,e2,w2=T.constructor(root,'new',shared=True,run_stop=10)
verified=C.verify_checkpoint(root/'saved',source_contract=contract,next_pc=11,
 constructor_contract={'identity':C.identity(p2,e2),'checkpoint_receipt':seal})
C.restore_quiescent(verified,e2,p2,w2)
m=e2.groups.shared.memories[0,3]
assert len(m.p.events)==0 and C.lifecycle_state(m.p)==old_state
assert m.serial==memory.serial and m.p.generations==memory.p.generations
stale=copy.deepcopy(m.p.events.validator)
old_request=next(ev for ev in memory.p.events if ev['event']=='request_accept')
try:stale.accept(old_request)
except ValueError:pass
else:raise AssertionError('old request accepted after saved watermark')
assert m.transact(0,write=False,payload=b'',length=32)==payload
assert m.p.events.validator.generations[0]==m.p.generations[0]
print(json.dumps({'status':'PASS_ACTUAL_COMPACT_CAPTURE_RESTORE_COMPONENT',
 'payload_bytes':projection['payload_bytes'],'typed_metadata_bytes':projection['typed_state_metadata_bytes'],
 'metadata_peak_envelope_bytes':projection['metadata_serialization_peak_envelope_bytes'],
 'checkpoint_reservation_bytes':projection['filesystem_reservation_bytes'],
 'journal_total_bytes':projection['old_journal_bytes'],'journal_files':len(projection['old_journal_inventory']['files']),
 'events_replayed_as_data':False,'hardware_qualified':False},sort_keys=True))
'''


@pytest.mark.parametrize('mode',['success','live','fault','counter','tamper','extra'])
def test_actual_compact_component_and_refusals(tmp_path,mode):
    r=subprocess.run([sys.executable,'-c',SCRIPT,str(tmp_path),mode],cwd=ROOT,capture_output=True,text=True)
    assert r.returncode==0,r.stdout+r.stderr
    assert 'PASS_' in r.stdout
    (tmp_path/'component_receipt.log').write_text(r.stdout+r.stderr)


def test_compact_source_pin_mutant_refused(monkeypatch):
    sys.path.insert(0,str(ROOT/'tools'))
    import ds_producer_checkpoint_resume_v3 as C
    monkeypatch.setattr(C,'CALENDAR_PIN','0'*64)
    with pytest.raises(ValueError,match='enrollment'):C.compact_runtime()
