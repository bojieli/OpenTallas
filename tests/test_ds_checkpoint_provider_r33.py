import gzip
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import h3_ds_checkpoint_provider_r33 as P

@pytest.fixture(scope='module')
def native():
    with gzip.open(ROOT / 'results/uarch/ds_hbm_window_retirement_r33_20261002/inputs/native_fixture_projection.json.gz', 'rt') as f:
        return json.load(f)

def provider(tmp_path, native):
    m = json.loads((ROOT / 'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/checkpoint_input_manifest.json').read_text())
    m.update(journal_root=str(tmp_path), journal_capacity_bytes=16 << 20)
    return P.create_provider(m, native, {}, [])

def source_codec():
    path = ROOT / 'results/uarch/ds_hbm_wo_a_route_bindings_r32_20261002/inputs/hdc_golden_v41.py.source'
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader('pinned_r32_storage_codec', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec); loader.exec_module(module)
    return module

@pytest.mark.parametrize('rank', [0, 7, 8, 63])
def test_actual_wo_a_payload_matches_pinned_storage_codec_and_head_K(tmp_path, native, rank):
    p = provider(tmp_path, native); op = native['instructions'][9]; owned = op['rank_bindings'][rank]
    key = owned['template']; source = op['provider_bindings'][key]['weight']; spec = native['templates'][key]['providers']['weight']
    actual = p.weight_view('weight', source, owned, spec)
    lo, hi = owned['row_interval']; k0 = rank % 8 * 512
    codes, _ = p.checkpoint.tensor(source['logical_tensor'], rows=[lo, hi], cols=[k0, k0+512])
    scales, _ = p.checkpoint.tensor(source['logical_tensor'].removesuffix('.weight')+'.scale', rows=[lo//32,hi//32], cols=[k0//32,k0//32+16])
    original = source_codec()
    expected = original.to_bf16(original._blocked(codes, scales.astype(np.int32)-127, 'actual wo_a selected aligned slice').dense())
    assert np.array_equal(actual.view(np.uint32), expected.view(np.uint32))
    assert not actual.flags.writeable and p.codec_receipts[-1]['K'] == [k0,k0+512]

def test_codec_signed_zero_ties_and_poison_fail_closed():
    codes = np.tile(np.array([0,128,1,129,126,254,3,131],np.uint8), (2,4))
    scales = np.array([[127],[121]],np.uint8)
    value = P.wo_a_payload(codes,scales)
    assert value[0,0].view(np.uint32) == 0 and value[0,1].view(np.uint32) == 0x80000000
    codes[0,0] = 127
    with pytest.raises(ValueError,match='poison'):P.wo_a_payload(codes,scales)
    codes[0,0] = 0; scales[0,0] = 255
    with pytest.raises(ValueError,match='poison'):P.wo_a_payload(codes,scales)

def test_routed_weight_rejects_before_source_fetch_retirement(tmp_path,native):
    p = provider(tmp_path,native);op=native['instructions'][21];owned=op['rank_bindings'][0];key=owned['template']
    with pytest.raises(ValueError,match='fetch must retire'):
        p.weight_view('weight_codes',op['provider_bindings'][key]['weight_codes'],owned,native['templates'][key]['providers']['weight_codes'])

def test_source_route_lifetime_fixture_then_real_checkpoint_selected_rows(tmp_path,native):
    # Explicit lifetime fixture, not actual full-program descriptor acceptance.
    p = provider(tmp_path,native);fetch=native['instructions'][20]
    ids=np.array([0,1,2,3,4,5],np.int64);ids.flags.writeable=False
    for owned in fetch['rank_bindings']:
        p.pending_routes[20,owned['rank']]=dict(ids=ids,layer=0,generation=1,source_version='DeepSeek.19.route_ids.82',descriptor_sha256='fixture_not_source_payload')
    p.retire_operation(20,1)
    assert len(p.routes)==96
    op=native['instructions'][21];owned=op['rank_bindings'][0];key=owned['template'];source=op['provider_bindings'][key]['weight_codes']
    actual=p.weight_view('weight_codes',source,owned,native['templates'][key]['providers']['weight_codes'])
    expected,dt=p.checkpoint.tensor('layers.0.ffn.experts.0.w1.weight',rows=owned['row_interval'])
    assert dt=='I8' and np.array_equal(actual,expected.astype(np.uint32))
    with pytest.raises(ValueError,match='still owned'):p.drain(1)
    for pc in sorted(p.route_consumers[0].copy()):p.retire_operation(pc,1)
    assert not p.routes and not p.route_consumers

def test_fetch_rejects_incomplete_rank_set_preserves_pending(tmp_path,native):
    p=provider(tmp_path,native);p.pending_routes[20,0]=dict(ids=np.arange(6,dtype=np.int64),layer=0,generation=1)
    with pytest.raises(ValueError,match='all source'):p.retire_operation(20,1)
    assert p.pending_routes and not p.routes

@pytest.mark.parametrize('state', ['previous', 'capacity', 'duplicate'])
def test_fetch_backpressure_precedes_new_source_read(tmp_path,native,state):
    p=provider(tmp_path,native);op=native['instructions'][20];owned=op['rank_bindings'][0]
    if state=='previous':p.routes[0,0]={'held_fixture':True}
    elif state=='capacity':p.pending_routes={ (20,r):{'held_fixture':True} for r in range(96) }
    else:p.pending_routes[20,0]={'held_fixture':True}
    before=(len(p.routes),len(p.pending_routes))
    with pytest.raises(ValueError):p.read_views(op,owned,1)
    assert before==(len(p.routes),len(p.pending_routes)) and not p.views
