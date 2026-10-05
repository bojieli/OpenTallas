"""Raw file binding only; explicit bit fixtures, no numerical oracle."""
import json
from pathlib import Path

import numpy as np
import pytest

from tools.runtime.qwen_combined.frozen_history import FrozenHistory, KV_WORDS, sha


def fixture(tmp_path, *, dtype='<u4', shape=(KV_WORDS,)):
    root = tmp_path / 'oracle'
    kv = root / 'P255/kv_pre'
    kv.mkdir(parents=True)
    pins = {}
    for rank in range(4):
        path = kv / f'L0_die{rank}.npy'
        a = np.lib.format.open_memmap(path, mode='w+', dtype=dtype, shape=shape)
        # Transport signatures distinguish rank and preserve the high bit.
        a[0], a[-1] = rank + 1, (0x80000000 if dtype == '<u4' else 7)
        a.flush()
        pins[f'L0_die{rank}'] = sha(path)
    record = dict(schema='opentallas.qwen-rom-tp4-position-oracle.v1', status='ISA_golden_only',
                  tp=4, groups=6144, kv_format='fp8', layers=1, positions=[255],
                  per_position={'255': dict(token=6280, kv_pre_sha256=pins)})
    (root / 'oracle.json').write_text(json.dumps(record))
    return root, sha(root / 'oracle.json')


def test_exact_bytes_all_ranks_and_reuse_existing(tmp_path):
    root, pin = fixture(tmp_path)
    binding = FrozenHistory(root, oracle_sha256=pin, position=255, token=6280)
    result = binding.export(tmp_path / 'raw', layers=[0])
    before = {}
    for rank in range(4):
        row = result[f'L0_die{rank}']
        raw = np.memmap(row['raw'], mode='r', dtype='<u4')
        assert raw.shape == (KV_WORDS,)
        assert (raw[0], raw[-1]) == (rank + 1, 0x80000000)
        before[row['raw']] = Path(row['raw']).stat().st_mtime_ns
    assert binding.export(tmp_path / 'raw', layers=[0]) == result
    assert all(Path(p).stat().st_mtime_ns == m for p, m in before.items())


def test_frozen_run_pin_does_not_follow_later_oracle_manifest(tmp_path):
    root, pin = fixture(tmp_path)
    m = json.loads((root / 'oracle.json').read_text())
    record = dict(status='pass', source_stable=True, configuration='REAL_MEM',
                  design_point=dict(tp=4, groups_per_die=6144, su_width=64),
                  oracle_json_sha256=pin, position=255, token=6280,
                  kv_history_sha256=m['per_position']['255']['kv_pre_sha256'])
    baseline = tmp_path / 'baseline.json'
    baseline.write_text(json.dumps(record))
    assert FrozenHistory.from_baseline(root, baseline).source(0, 3)[2][0] == 4
    m['positions'].append(1023)
    (root / 'oracle.json').write_text(json.dumps(m))
    with pytest.raises(ValueError, match='identity'):
        FrozenHistory.from_baseline(root, baseline)


@pytest.mark.parametrize('dtype,shape', [('<f4', (KV_WORDS,)), ('>u4', (KV_WORDS,)), ('<u4', (KV_WORDS - 1,))])
def test_wrong_raw_contract_refused(tmp_path, dtype, shape):
    root, pin = fixture(tmp_path, dtype=dtype, shape=shape)
    binding = FrozenHistory(root, oracle_sha256=pin, position=255, token=6280)
    with pytest.raises(ValueError, match='bitwords'):
        binding.source(0, 0)


def test_position_token_rank_layer_and_pin_refusals(tmp_path):
    root, pin = fixture(tmp_path)
    with pytest.raises(ValueError, match='identity'):
        FrozenHistory(root, oracle_sha256='0' * 64, position=255, token=6280)
    with pytest.raises(ValueError, match='position'):
        FrozenHistory(root, oracle_sha256=pin, position=256, token=6280)
    with pytest.raises(ValueError, match='token'):
        FrozenHistory(root, oracle_sha256=pin, position=255, token=0)
    binding = FrozenHistory(root, oracle_sha256=pin, position=255, token=6280)
    with pytest.raises(ValueError, match='rank'):
        binding.source(0, 4)
    with pytest.raises(ValueError, match='covered'):
        binding.export(tmp_path / 'missing36', layers=range(36))
    assert not (tmp_path / 'missing36').exists()


def test_drift_and_existing_failure_bytes_preserved(tmp_path):
    root, pin = fixture(tmp_path)
    binding = FrozenHistory(root, oracle_sha256=pin, position=255, token=6280)
    out = tmp_path / 'raw'
    out.mkdir()
    target = out / 'L0_die0.bin'
    target.write_bytes(b'old failure')
    with pytest.raises(ValueError, match='existing'):
        binding.export(out, layers=[0])
    assert target.read_bytes() == b'old failure'
    (root / 'P255/kv_pre/L0_die0.npy').write_bytes(b'drift')
    with pytest.raises(ValueError, match='hash'):
        binding.source(0, 0)
