"""Filesystem/control tests only: NOT actual PC0-1 smoke admission."""
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_atomic_checkpoint_r67 as R


def staged(root,boundary_pc=0):
    root.mkdir();(root/'payload.bin').write_bytes(bytes(range(64)))
    identity=dict(helper_sha256=R.V3_SHA256,fixture_only=True)
    projection=dict(retired_PCs=list(range(boundary_pc+1)),same_home_restore=True)
    closure=dict(schema='DS_ACTUAL_PRODUCER_QUIESCENT_RESUME_V3',identity=identity,inventory=projection,
        state={'dict':[['retired',{'set':list(range(boundary_pc+1))}]]},
        payload_sha256=R.sha(root/'payload.bin'),payload_bytes=64)
    (root/'state.json').write_bytes(R.canonical(closure))
    seal=dict(payload_sha256=closure['payload_sha256'],state_sha256=R.sha(root/'state.json'),schema=closure['schema'])
    (root/'COMPLETE.json').write_bytes(R.canonical(seal))
    (root/'actual_observations.json').write_bytes(R.canonical(dict(boundary_pc=boundary_pc,projection=projection,source_contract=dict(identity=identity))))
    receipt=dict(producer_seal=seal,actual_observations_sha256=R.sha(root/'actual_observations.json'))
    (root/'RUNNER_COMPLETE.json').write_bytes(R.canonical(receipt))
    return receipt


def test_atomic_publication_and_exact_fresh_process_guard(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC0';receipt=staged(source)
    result=R.publish(source,dest,receipt,boundary_pc=0)
    assert not source.exists() and dest.is_dir()
    with pytest.raises(ValueError,match='distinct cold process'):
        R.require_fresh_restore(result,current_pid=result['producer_pid'])
    with pytest.raises(ValueError,match='actual process PID'):
        R.require_fresh_restore(result,current_pid=result['producer_pid']+1)


def test_corrupt_payload_never_publishes(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source,1)
    (source/'payload.bin').write_bytes(b'wrong')
    with pytest.raises(ValueError,match='checksum'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert source.exists() and not dest.exists()


def test_existing_checkpoint_is_not_overwritten(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source,1);dest.mkdir()
    (dest/'keep').write_text('immutable')
    with pytest.raises(ValueError,match='already exists'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert (dest/'keep').read_text()=='immutable'


def test_partial_checkpoint_never_publishes(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source,1)
    (source/'RUNNER_COMPLETE.json').unlink()
    with pytest.raises(ValueError,match='complete checkpoint'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert source.exists() and not dest.exists()


def test_atomic_capture_default_off_and_original_pin(tmp_path):
    class Helper:__file__=__file__
    for enabled,match in [(False,'default off'),(True,'original V3')]:
        with pytest.raises(ValueError,match=match):
            R.capture_atomic(Helper,None,None,None,boundary_pc=0,destination=tmp_path/'PC0',source_contract={},enabled=enabled)


def test_actual_fresh_subprocess_checks_sealed_files(tmp_path):
    import subprocess
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source,1)
    publication=R.publish(source,dest,receipt,boundary_pc=1)
    record=tmp_path/'publication.json';record.write_text(json.dumps(publication))
    script="import sys,os,json;sys.path.insert(0,sys.argv[1]);import ds_hbm_atomic_checkpoint_r67 as R;v=json.load(open(sys.argv[2]));R.require_fresh_restore(v,current_pid=os.getpid());print('PASS_FILESYSTEM_COLD_PROCESS_ONLY')"
    result=subprocess.run([sys.executable,'-c',script,str(ROOT/'tools'),str(record)],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr
    assert result.stdout.strip()=='PASS_FILESYSTEM_COLD_PROCESS_ONLY'


def test_failed_rename_preserves_complete_staging(tmp_path,monkeypatch):
    source=tmp_path/'stage';dest=tmp_path/'PC0';receipt=staged(source)
    def refuse(*args):raise OSError('injected rename failure')
    monkeypatch.setattr(R.os,'rename',refuse)
    with pytest.raises(OSError,match='rename failure'):
        R.publish(source,dest,receipt,boundary_pc=0)
    assert source.exists() and not dest.exists()
    assert R.verify_payload(source,receipt)['payload.bin']['bytes']==64


def test_supplied_PC0_cannot_label_actual_PC9(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC0';receipt=staged(source,9)
    with pytest.raises(ValueError,match='checkpoint boundary mismatch'):
        R.publish(source,dest,receipt,boundary_pc=0)
    assert source.exists() and not dest.exists()


def test_projected_prefix_cannot_disagree_with_actual_state(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source,1)
    actual=json.loads((source/'actual_observations.json').read_bytes())
    actual['projection']['retired_PCs']=[0]
    (source/'actual_observations.json').write_bytes(R.canonical(actual))
    receipt['actual_observations_sha256']=R.sha(source/'actual_observations.json')
    (source/'RUNNER_COMPLETE.json').write_bytes(R.canonical(receipt))
    with pytest.raises(ValueError,match='projected/actual retired'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert not dest.exists()


def test_resealed_serialized_retirement_mismatch_refused(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source,1)
    closure=json.loads((source/'state.json').read_bytes())
    closure['state']['dict'][0][1]['set']=[0]
    (source/'state.json').write_bytes(R.canonical(closure))
    receipt['producer_seal']['state_sha256']=R.sha(source/'state.json')
    (source/'COMPLETE.json').write_bytes(R.canonical(receipt['producer_seal']))
    (source/'RUNNER_COMPLETE.json').write_bytes(R.canonical(receipt))
    with pytest.raises(ValueError,match='serialized actual retired'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert not dest.exists()
