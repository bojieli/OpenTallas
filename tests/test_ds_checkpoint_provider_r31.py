import gzip
import json
import sys
from pathlib import Path
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import h3_ds_checkpoint_provider_r31 as P

@pytest.fixture(scope='module')
def native():
    with gzip.open('/home/ubuntu/OpenTallas/results/uarch/h3_deepseek_complete_native_20261002/program_final.json.gz', 'rt') as f:
        return json.load(f)

def provider(tmp_path, native):
    m = json.loads((ROOT / 'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_text())
    m.update(journal_root=str(tmp_path), journal_capacity_bytes=16 << 20)
    return P.create_provider(m, native, {}, [])

def test_source_zero_destination_exact_readonly_identity_and_release(tmp_path, native):
    p = provider(tmp_path, native)
    op = native['instructions'][23]
    owned = op['rank_bindings'][0]
    key = owned['template']
    zeros = {n: b for n, b in op['provider_bindings'][key].items() if b['kind'] == 'zero_initial_partial_destination'}
    assert zeros
    views = p._read_one(op, owned, key, zeros, 1)
    for name, value in views.items():
        spec = native['templates'][key]['providers'][name]
        assert list(value['data'].shape) == spec['shape']
        assert value['data'].dtype == np.float32 and not value['data'].flags.writeable
        assert not np.any(value['data'].view(np.uint32))
        assert value['source_binding'] == zeros[name]
        assert value['initialization_bytes'] == zeros[name]['full_elements'] * 4
    p.release_views(op['pc'], owned['rank'], 1, views)
    assert not p.views

@pytest.mark.parametrize('change', ['extent', 'version'])
def test_zero_wrong_extent_or_version_rejected(tmp_path, native, change):
    p = provider(tmp_path, native); op = native['instructions'][23]; owned = op['rank_bindings'][0]; key = owned['template']
    name, source = next((n, b) for n, b in op['provider_bindings'][key].items() if b['kind'] == 'zero_initial_partial_destination')
    wrong = dict(source)
    if change == 'extent': wrong['full_elements'] += 1
    else: wrong['new_version'] = 'not.the.source.destination'
    with pytest.raises(ValueError): p._read_one(op, owned, key, {name: wrong}, 1)
    assert not p.views

def test_actual_checkpoint_BF16_row_payload_exact(tmp_path, native):
    p = provider(tmp_path, native); op = native['instructions'][16]; owned = op['rank_bindings'][0]; key = owned['template']
    source = op['provider_bindings'][key]['weight']; spec = native['templates'][key]['providers']['weight']
    actual = p.weight_view('weight', source, owned, spec)
    expected, dtype = p.checkpoint.tensor(source['logical_tensor'], rows=source['row_intervals'][0])
    assert dtype == 'BF16' and np.array_equal(actual.view(np.uint32), expected.view(np.uint32))
    assert not actual.flags.writeable and list(actual.shape) == spec['shape']
    wrong = dict(owned, row_interval=[0, 1])
    with pytest.raises(ValueError): p.weight_view('weight', source, wrong, spec)

def test_actual_FP8_wo_a_not_silently_cast_or_truncated(tmp_path, native):
    p = provider(tmp_path, native); op = native['instructions'][9]; owned = op['rank_bindings'][0]; key = owned['template']
    with pytest.raises(NotImplementedError, match='conversion/K-view'):
        p.weight_view('weight', op['provider_bindings'][key]['weight'], owned, native['templates'][key]['providers']['weight'])
