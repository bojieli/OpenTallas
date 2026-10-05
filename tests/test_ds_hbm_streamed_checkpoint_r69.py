"""Complete producer-state component fixture, not released full-size PC01 smoke.

Uses original source Provider, native Machine, port ownership and V3 snapshot.
No monkeypatched quiescence/identity/project/restore or expected-data stimulus.
"""
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tests'))
import test_ds_producer_checkpoint_resume_v3 as fixture
import ds_producer_checkpoint_resume_v3 as base
import ds_hbm_streamed_checkpoint_r69 as candidate
import ds_checkpoint_streamed_state_r2 as stream

def produced(root):
    p, e, w = fixture.constructor(root, 'producer', run_stop=2)
    e.last_use = {'v0': 2212, 'v1': 2212}
    e.execute_operation(e.native['instructions'][0])
    w.seen.add((0, 'v0', 0, 1, 'data'))
    contract = dict(identity=base.identity(p, e), checkpoint_selection=candidate.selection(base))
    return p, e, w, contract

def test_complete_snapshot_payload_and_closure_equal_original(tmp_path):
    p, e, w, contract = produced(tmp_path)
    old = tmp_path / 'original'; new = tmp_path / 'streamed'
    original = base.capture_quiescent(e, p, w, boundary_pc=0,
        destination=old, source_contract=contract)
    result = candidate.capture_atomic(base, e, p, w, boundary_pc=0,
        destination=new, source_contract=contract, enabled=True)
    for name in ('payload.bin', 'state.json', 'COMPLETE.json'):
        assert (old / name).read_bytes() == (new / name).read_bytes()
    assert result['checkpoint_receipt']['producer_seal'] == original['producer_seal']
    assert not result['stream_metrics']['full_encoded_container_tree_created']
    projection = json.loads((new / 'actual_observations.json').read_text())['projection']
    assert projection['serialization_workspace_envelope_bytes'] > 0
    assert projection['metadata_python_tree_bytes'] > 0  # original project is priced
    assert sum(f.stat().st_size for f in new.iterdir()) <= projection['filesystem_reservation_bytes']
    assert e.last_use['v0'] == 2212

def test_actual_fresh_subprocess_restore_and_native_continuation(tmp_path):
    p, e, w, contract = produced(tmp_path)
    cp = tmp_path / 'checkpoint'
    result = candidate.capture_atomic(base, e, p, w, boundary_pc=0,
        destination=cp, source_contract=contract, enabled=True)
    with pytest.raises(ValueError, match='distinct cold process'):
        candidate.restore_cold(base, cp, contract, result['checkpoint_receipt'], p, e, w,
                               next_pc=1, enabled=True)
    run = subprocess.run([sys.executable, str(Path(__file__)), '--fixture-restore',
                          str(tmp_path), str(cp)], text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr
    record = json.loads((tmp_path / 'fresh_restore.json').read_text())
    assert record['retired'] == [0, 1] and record['source_last_use'] == 2212
    assert record['actual_restored_v0_sha'] == base.hashlib.sha256(p.restore('v0', 0).tobytes()).hexdigest()

def test_default_off_before_any_producer_read(tmp_path):
    with pytest.raises(ValueError, match='default off'):
        candidate.capture_atomic(None, None, None, None, boundary_pc=0,
            destination=tmp_path / 'never', source_contract={})
    assert not (tmp_path / 'never').exists()

def test_wrong_selection_refuses_before_write(tmp_path):
    p, e, w, contract = produced(tmp_path)
    contract['checkpoint_selection']['stream_helper_sha256'] = 'wrong'
    with pytest.raises(ValueError, match='source contract'):
        candidate.capture_atomic(base, e, p, w, boundary_pc=0,
            destination=tmp_path / 'wrong', source_contract=contract, enabled=True)
    assert not (tmp_path / 'wrong').exists()

def test_live_debt_and_missing_observation_refuse(tmp_path):
    p, e, w, contract = produced(tmp_path)
    p.views = {'live': 'owner'}
    with pytest.raises(ValueError, match='live'):
        candidate.capture_atomic(base, e, p, w, boundary_pc=0,
            destination=tmp_path / 'live', source_contract=contract, enabled=True)
    p.views.clear(); w.seen.clear()
    with pytest.raises(ValueError, match='observation'):
        candidate.capture_atomic(base, e, p, w, boundary_pc=0,
            destination=tmp_path / 'unseen', source_contract=contract, enabled=True)

def test_full_shared_owner_serial_and_raw_payload_equal_original(tmp_path):
    p, e, w = fixture.constructor(tmp_path, 'shared', shared=True)
    for op in e.native['instructions']:
        e.execute_operation(op); w.seen.add((op['pc'], 'v'+str(op['pc']), 0, 1, 'data'))
    owner = dict(PC=10, rank=0, SM=3, generation=1, tile=7, template='source_component')
    memory = e.groups.shared(owner)
    data = bytes(range(256)) * 2
    memory.transact(0, write=True, payload=data, length=len(data))
    e.groups.completed.add((10, 0, 1))
    contract = dict(identity=base.identity(p, e), checkpoint_selection=candidate.selection(base))
    old, new = tmp_path / 'old', tmp_path / 'new'
    base.capture_quiescent(e, p, w, boundary_pc=10, destination=old, source_contract=contract)
    candidate.capture_atomic(base, e, p, w, boundary_pc=10, destination=new,
                             source_contract=contract, enabled=True)
    assert (old / 'state.json').read_bytes() == (new / 'state.json').read_bytes()
    assert (old / 'payload.bin').read_bytes() == (new / 'payload.bin').read_bytes()
    assert base.inventory(p, e)['retained_shared_homes'] == 1

def fixture_restore(root, cp):
    p, e, w = fixture.constructor(root, 'fresh', run_stop=2)
    e.last_use = {'v0': 2212, 'v1': 2212}
    actual = json.loads((cp / 'actual_observations.json').read_text())
    receipt = json.loads((cp / 'RUNNER_COMPLETE.json').read_text())
    result = candidate.restore_cold(base, cp, actual['source_contract'], receipt,
                                    p, e, w, next_pc=1, enabled=True)
    restored_sha = base.hashlib.sha256(p.restore('v0', 0).tobytes()).hexdigest()
    e.execute_operation(e.native['instructions'][1])
    (root / 'fresh_restore.json').write_text(json.dumps(dict(retired=sorted(e.retired),
        source_last_use=e.last_use['v0'], actual_restored_v0_sha=restored_sha,
        restore=result, fixture_only=True)))

if __name__ == '__main__':
    if sys.argv[1] != '--fixture-restore':
        raise ValueError('component fixture restore only')
    fixture_restore(Path(sys.argv[2]), Path(sys.argv[3]))
