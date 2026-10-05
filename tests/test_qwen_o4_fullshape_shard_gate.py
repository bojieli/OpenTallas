"""Gate acceptance and rejection with independently written synthetic shards."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import qwen_o4_fullshape_shard_gate as gate  # noqa: E402


def make_pair(tmp_path, bit_flip=False):
    golden_dir, rtl_dir = tmp_path / 'golden', tmp_path / 'rtl'
    golden_dir.mkdir()
    rtl_dir.mkdir()
    source = ROOT / 'tools/hdc_program.py'
    pin = {'tools/hdc_program.py': hashlib.sha256(source.read_bytes()).hexdigest()}
    for die in (0, 1):
        arrays = {'h_in': np.arange(4096, dtype=np.float32),
                  'h_out': np.arange(4096, dtype=np.float32) + 1}
        identity = {'context': 128, 'layer': 0, 'die': die, 'tp': 2, 'position': 127}
        golden = dict(identity, schema='opentallas.qwen-o4-fullshape-shard.v1',
                      config_sha256=gate.sha(ROOT / gate.CONFIG),
                      checkpoint_lock_sha256=gate.sha(ROOT / gate.LOCK),
                      source_sha256=pin,
                      array_sha256={name: gate.array_sha(value) for name, value in arrays.items()})
        rtl = dict(identity, cycles=100 + die, source_sha256=pin,
                   golden_input_sha256=golden['array_sha256']['h_in'])
        stem = f'ctx128_L00_D{die}'
        (golden_dir / (stem + '.json')).write_text(json.dumps(golden))
        np.savez(golden_dir / (stem + '.npz'), **arrays)
        (rtl_dir / (stem + '.json')).write_text(json.dumps(rtl))
        actual = {key: value.copy() for key, value in arrays.items()}
        if die == 1 and bit_flip:
            actual['h_out'].view(np.uint32)[0] ^= 1
        np.savez(rtl_dir / (stem + '.npz'), **actual)
    return golden_dir, rtl_dir


def test_matching_shards_are_scoped(tmp_path):
    golden, rtl = make_pair(tmp_path)
    result = gate.compare(golden, rtl, 128, [0], ROOT)
    assert result['status'] == 'bit_exact_supplied_shards'
    assert len(result['shards']) == 2
    assert 'no full token' in result['claim_boundary']


def test_one_bit_rejected(tmp_path):
    golden, rtl = make_pair(tmp_path, bit_flip=True)
    with pytest.raises(ValueError, match='bit mismatch'):
        gate.compare(golden, rtl, 128, [0], ROOT)


def test_stale_source_pin_rejected(tmp_path):
    golden, rtl = make_pair(tmp_path)
    path = rtl / 'ctx128_L00_D0.json'
    meta = json.loads(path.read_text())
    meta['source_sha256']['tools/hdc_program.py'] = '0' * 64
    path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='stale source pin'):
        gate.compare(golden, rtl, 128, [0], ROOT)


def test_cross_die_hidden_state_disagreement_rejected(tmp_path):
    golden, rtl = make_pair(tmp_path)
    stem = 'ctx128_L00_D1'
    with np.load(golden / (stem + '.npz')) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays['h_out'][0] += 1
    np.savez(golden / (stem + '.npz'), **arrays)
    np.savez(rtl / (stem + '.npz'), **arrays)
    path = golden / (stem + '.json')
    meta = json.loads(path.read_text())
    meta['array_sha256']['h_out'] = gate.array_sha(arrays['h_out'])
    path.write_text(json.dumps(meta))
    with pytest.raises(ValueError, match='TP2 dies disagree'):
        gate.compare(golden, rtl, 128, [0], ROOT)


def test_preflight_names_first_missing_artifacts(tmp_path):
    result = gate.preflight(tmp_path / 'golden', tmp_path / 'rtl', 128, [0], ROOT,
                            tmp_path / 'missing-checkpoint')
    assert result['status'] == 'blocked'
    assert 'golden missing ctx128_L00_D0.json' in result['blockers']
    assert any('shipped checkpoint missing' in x for x in result['blockers'])
