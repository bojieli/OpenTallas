"""Filesystem/control tests only: NOT actual PC0-1 smoke admission."""
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_atomic_checkpoint_r66 as R


def staged(root):
    root.mkdir();(root/'payload.bin').write_bytes(bytes(range(64)))
    closure=dict(payload_sha256=R.sha(root/'payload.bin'),payload_bytes=64)
    (root/'state.json').write_bytes(R.canonical(closure))
    seal=dict(payload_sha256=closure['payload_sha256'],state_sha256=R.sha(root/'state.json'),schema='fixture-only')
    (root/'COMPLETE.json').write_bytes(R.canonical(seal))
    (root/'actual_observations.json').write_bytes(b'{}')
    receipt=dict(producer_seal=seal,actual_observations_sha256=R.sha(root/'actual_observations.json'))
    (root/'RUNNER_COMPLETE.json').write_bytes(R.canonical(receipt))
    return receipt


def test_atomic_publication_and_exact_fresh_process_guard(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC0';receipt=staged(source)
    result=R.publish(source,dest,receipt,boundary_pc=0)
    assert not source.exists() and dest.is_dir()
    with pytest.raises(ValueError,match='distinct cold process'):
        R.require_fresh_restore(result,current_pid=result['producer_pid'])
    assert R.require_fresh_restore(result,current_pid=result['producer_pid']+1)['payload.bin']['bytes']==64


def test_corrupt_payload_never_publishes(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source)
    (source/'payload.bin').write_bytes(b'wrong')
    with pytest.raises(ValueError,match='checksum'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert source.exists() and not dest.exists()


def test_existing_checkpoint_is_not_overwritten(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source);dest.mkdir()
    (dest/'keep').write_text('immutable')
    with pytest.raises(ValueError,match='already exists'):
        R.publish(source,dest,receipt,boundary_pc=1)
    assert (dest/'keep').read_text()=='immutable'


def test_partial_checkpoint_never_publishes(tmp_path):
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source)
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
    source=tmp_path/'stage';dest=tmp_path/'PC1';receipt=staged(source)
    publication=R.publish(source,dest,receipt,boundary_pc=1)
    record=tmp_path/'publication.json';record.write_text(json.dumps(publication))
    script="import sys,os,json;sys.path.insert(0,sys.argv[1]);import ds_hbm_atomic_checkpoint_r66 as R;v=json.load(open(sys.argv[2]));R.require_fresh_restore(v,current_pid=os.getpid());print('PASS_FILESYSTEM_COLD_PROCESS_ONLY')"
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
