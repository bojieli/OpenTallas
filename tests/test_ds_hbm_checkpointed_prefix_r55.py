"""Real source endpoints + primitive arithmetic exercise the R55 restore adapter.
Component tests only: no released-checkpoint prefix or physical admission.
"""
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=r'''
import sys,copy,json
from pathlib import Path
sys.path[:0]=[str(Path.cwd()/'tools'),str(Path.cwd()/'tests')]
import test_ds_producer_checkpoint_resume_v3 as T
import ds_producer_checkpoint_resume_v3 as C
import ds_hbm_checkpointed_prefix_r55 as R
import ds_hbm_additive_endpoint_join_r54 as J
import hbm_bound_event_journal_r30 as journal
import h3_ds_checkpoint_provider_r30 as base
import h3_ds_query_provider_r36 as query
import h4_hbm_w19_pc10_endpoints as endpoint
J.install([journal,base,query,endpoint])
root=Path(sys.argv[1]);mode=sys.argv[2]
p,e,w=T.constructor(root,'producer',shared=True,run_stop=0)
e.execute_operation(e.native['instructions'][0]);w.seen.add((0,'v0',0,1,'data'))
contract={'identity':C.identity(p,e),'runner_extension':'priced arbitrary source metadata'*8}
dest=root/'saved'
projection=C.project_checkpoint(e,p,w,boundary_pc=0,destination=dest)
raw=projection['filesystem_reservation_bytes']
extra=len(C.canonical(contract))
if mode=='budget':
 try:R.charged_projection(C,projection,contract,checkpoint_upper=raw+extra-1)
 except ValueError:pass
 else:raise AssertionError('uncharged source contract accepted')
 assert not dest.exists()
 priced=R.charged_projection(C,projection,contract,checkpoint_upper=raw+extra)
 assert priced['filesystem_reservation_bytes']==raw+extra
 assert projection['filesystem_reservation_bytes']==raw
 print('PASS_SOURCE_CONTRACT_BOUNDARY');sys.exit(0)
actual=p.restore('v0',0).tobytes()
receipt=C.capture_quiescent(e,p,w,boundary_pc=0,destination=dest,source_contract=contract)
if mode=='old_mutation':
 e.execute_operation(e.native['instructions'][1])
 p2,e2,w2=T.constructor(root,'continuation',shared=True,run_stop=10)
 try:R.restore_cold(C,checkpoint=dest,source_contract=contract,checkpoint_receipt=receipt,
  provider=p2,engine=e2,witness=w2,next_pc=1)
 except ValueError:pass
 else:raise AssertionError('mutated sealed journal restored')
 assert not e2.retired and not w2.seen
 print('PASS_OLD_CAPTURE_THEN_CONTINUE_REFUSAL');sys.exit(0)
p2,e2,w2=T.constructor(root,'continuation',shared=True,run_stop=10,journal_capacity=16777216)
if mode=='payload':
 f=dest/'payload.bin';f.write_bytes(f.read_bytes()+b'changed')
 try:R.restore_cold(C,checkpoint=dest,source_contract=contract,checkpoint_receipt=receipt,
  provider=p2,engine=e2,witness=w2,next_pc=1)
 except ValueError:pass
 else:raise AssertionError('changed actual payload accepted')
 assert not e2.retired and not w2.seen
 print('PASS_PAYLOAD_REFUSAL');sys.exit(0)
verified,restored=R.restore_cold(C,checkpoint=dest,source_contract=contract,checkpoint_receipt=receipt,
 provider=p2,engine=e2,witness=w2,next_pc=1)
assert restored['retired']==[0] and e2.retired=={0}
assert w2.seen=={(0,'v0',0,1,'data')}
assert sum(len(port.events) for port in p2.rf.values())==0
assert verified['run_scope_transition']['old_run_scope']['journal_root']!=verified['run_scope_transition']['new_run_scope']['journal_root']
assert p2.restore('v0',0).tobytes()==actual
C.execute_remaining(e2,stop_after=2)
R.verify_sealed(C,verified)
# Independent unchanged primitive arithmetic; not execution stimulus or restore.
import numpy as np
expected=(np.arange(32,dtype=np.float32)+np.float32(1.25)+np.float32(1.25))*np.float32(1.25)
assert p2.restore('v2',0).tobytes()==expected.tobytes()
assert (root/'continuation'/'checkpoint_restore_scope.json').exists()
assert any(len(port.events)>0 for port in p2.rf.values())
R.verify_sealed(C,verified)
print('PASS_ACTUAL_COLD_RESTORE_SEALED_HISTORY_AND_FRESH_ENDPOINTS')
'''

@pytest.mark.parametrize('mode',['success','old_mutation','payload','budget'])
def test_real_restore_and_negative_controls(tmp_path,mode):
    result=subprocess.run([sys.executable,'-c',SCRIPT,str(tmp_path),mode],cwd=ROOT,capture_output=True,text=True)
    (tmp_path/'receipt.log').write_text(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'PASS_' in result.stdout


def test_ram_coexistence_headroom_not_process_cap():
    sys.path.insert(0,str(ROOT/'tools'))
    import ds_hbm_checkpointed_prefix_r55 as R
    got=R.memory_admission(available_bytes=4096,serialization_workspace_bytes=2048,cold_and_restore_new_bytes=4096)
    assert got['producer_retained'] and got['incremental_peak_bytes']==4096
    assert got['process_memory_cap'] is False
    with pytest.raises(ValueError,match='headroom'):
        R.memory_admission(available_bytes=4095,serialization_workspace_bytes=2048,cold_and_restore_new_bytes=4096)
    with pytest.raises(ValueError,match='positive'):
        R.memory_admission(available_bytes=4096,serialization_workspace_bytes=2048,cold_and_restore_new_bytes=0)

@pytest.mark.parametrize('mutant',['missing_RAM','double_journal','insufficient_disk'])
def test_source_gate_requires_complete_phase_and_RAM_proof(tmp_path,monkeypatch,mutant):
    import json
    sys.path.insert(0,str(ROOT/'tools'))
    import ds_hbm_checkpointed_prefix_r55 as R
    monkeypatch.setattr(R,'ROOT',tmp_path)
    names=['tools/ds_hbm_checkpointed_prefix_r55.py','tools/ds_hbm_additive_endpoint_join_r54.py',
           'tools/h3_complete_native_calendar_successor_r1.py','tools/ds_producer_checkpoint_resume_v3.py',
           'tools/h3_complete_native_calendar.py','tools/ds_producer_checkpoint_resume.py']
    pins={}
    for name in names:
        p=tmp_path/name;p.parent.mkdir(exist_ok=True);p.write_text('explicit test source '+name)
        pins[name]=R.sha(p)
    proof=dict(projection_complete=True,source_sha256=pins,journal_new_bytes=8192,
               producer_journal_new_bytes=4096,continuation_journal_new_bytes=4096,
               checkpoint_new_bytes=4096,other_new_bytes=1024,cold_and_restore_new_RAM_bytes=2048,
               producer_new_RAM_bytes=2048,serialization_workspace_RAM_bytes=1024)
    if mutant=='missing_RAM':del proof['cold_and_restore_new_RAM_bytes']
    if mutant=='double_journal':proof['continuation_journal_new_bytes']=8192
    path=tmp_path/'proof.json';path.write_text(json.dumps(proof))
    plan=dict(schema='DS_PC0_10_ACTUAL_CHECKPOINT_LAUNCH_PLAN_R55',status='PASS_SOURCE_AND_STORAGE_REVIEW',
              stop=10,checkpoint_boundary=9,helper_module='ds_producer_checkpoint_resume_v3',source_sha256=pins,
              storage_proof={'path':'proof.json','sha256':R.sha(path)})
    with pytest.raises(ValueError):
        R.source_gate(plan,available_bytes=13311 if mutant=='insufficient_disk' else 65536)
