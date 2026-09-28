"""Source and arithmetic checks for the real Qwen O4 layer-0 ISA oracle."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))

import hdc_golden as G
import qwen3_deployment_quality as Q
from qwen_o4_layer0_oracle import Image

OUT = ROOT / 'results/rtl/qwen_o4_layer0_oracle'


def _bits(die, name):
    path = OUT / f'die{die}_{name}.hex'
    return np.array([int(x, 16) for x in path.read_text().splitlines()], dtype=np.uint32)


def test_oracle_sources_outputs_and_tp_collectives_are_pinned():
    record = json.loads((OUT / 'oracle.json').read_text())
    assert record['status'] == 'ISA_golden_only'
    assert record['emitter_basis_commit'] == '7ed6bb26'
    for name, digest in record['emitter_source_sha256'].items():
        # The oracle is an immutable ISA-golden result from the full-shape
        # branch. The deployment-quality tool has since changed for DFlash;
        # validate the recorded source snapshot rather than silently repin a
        # computation that has not been rerun.
        source = (subprocess.check_output(['git', 'show', f'9a54ff9a:{name}'], cwd=ROOT)
                  if name == 'tools/qwen3_deployment_quality.py'
                  else (ROOT / name).read_bytes())
        assert hashlib.sha256(source).hexdigest() == digest
    assert record['arithmetic'] == {'groups_per_die': 6144, 'su_width': 1024,
                                    'kv_format': 'fp8', 'weight_format': 'signed-int8-per-row-bf16-scale'}
    for name, digest in record['oracle_source_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
    for die in (0, 1):
        for name, item in record['outputs'][f'die{die}'].items():
            path = OUT / f'die{die}_{name}.hex'
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['sha256']
            assert len(_bits(die, name)) == item['elements']
        assert record['outputs'][f'die{die}']['x_final']['nonzero'] == 4096
    # Both die halves receive the same rank-folded T1 and residual X.  Their
    # local KV heads belong to distinct head ranges and therefore differ.
    for name in ('x_initial', 't1_after_o_scale', 't1_after_down_scale', 'x_final'):
        np.testing.assert_array_equal(_bits(0, name), _bits(1, name))
    for name in ('k_pos0', 'v_pos0'):
        assert not np.array_equal(_bits(0, name), _bits(1, name))
        values = _bits(0, name).view(np.float32)
        np.testing.assert_array_equal(G.bits(G.to_fp8(values)), G.bits(values))


def test_initial_x_is_the_signed_int8_embedding_row_zero():
    torch = pytest.importorskip('torch')
    safetensors = pytest.importorskip('safetensors')
    try:
        snapshot = Q.find_snapshot()
    except FileNotFoundError:
        pytest.skip('Qwen3-8B checkpoint unavailable')
    with safetensors.safe_open(str(snapshot / 'model-00001-of-00005.safetensors'),
                               framework='pt', device='cpu') as handle:
        row = handle.get_slice('model.embed_tokens.weight')[0:1]
    codes, scales, _ = Q.quantize_w8(row)
    expected = G.mul(codes[0].float().numpy(), scales[0].float().numpy())
    np.testing.assert_array_equal(_bits(0, 'x_initial'), G.bits(expected))


def test_independent_layer0_arithmetic_matches_isa_trace(monkeypatch):
    """A direct one-position decode checks the ISA interpreter's dataflow."""
    prefixes = ('/tmp/qwen-real-layer0-padded', '/tmp/qwen-real-layer0-compact',
                '/tmp/qwen-real-layer0')
    directories = None
    for prefix in prefixes:
        candidate = [Path(f'{prefix}-d{d}') for d in (0, 1)]
        if all((d / 'layer0_rom.json').is_file() for d in candidate):
            manifests = [json.loads((d / 'layer0_rom.json').read_text()) for d in candidate]
            if all(all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
                       for name, digest in m['source_sha256'].items()) for m in manifests):
                directories = candidate
                break
    if directories is None:
        pytest.skip('full layer-0 emitted images unavailable')
    monkeypatch.setattr(G, 'SU_WIDTH', 1024)
    images = [Image(d) for d in directories]
    x = _bits(0, 'x_initial').view(np.float32)
    r = G.rstd(x, np.float32(1e-6))
    o_partials, values = [], []
    for die, im in enumerate(images):
        meta = im.manifest['matrix_layout'][0]
        codes, scales = im.matrix(meta)
        qkv = G.mul(G.mul(G.matvec(codes.astype(np.float32), x, meta['split']), scales), r)
        k, v = qkv[2048:2560].reshape(4, 128), G.kv_round(qkv[2560:3072].reshape(4, 128))
        values.append(v)
        np.testing.assert_array_equal(G.bits(v.reshape(-1)), _bits(die, 'v_pos0'))
        k_rows = []
        for h in range(4):
            norm_weight = im.crom[4096+2048+h*128:4096+2048+(h+1)*128, 0]
            # RoPE at position zero has cos=1, sin=0, so normalized K is unchanged.
            k_rows.append(G.kv_round(G.mul(G.mul(k[h], G.rstd(k[h], np.float32(1e-6))), norm_weight)))
        np.testing.assert_array_equal(G.bits(np.concatenate(k_rows)), _bits(die, 'k_pos0'))
        attention = np.concatenate([v[h//4] for h in range(16)])
        meta = im.manifest['matrix_layout'][1]
        codes, _ = im.matrix(meta)
        o_partials.append(G.matvec(codes.astype(np.float32), attention, meta['split']))
    o_scale = images[0].matrix(images[0].manifest['matrix_layout'][1])[1]
    o = G.mul(G.fold(o_partials), o_scale)
    np.testing.assert_array_equal(G.bits(o), _bits(0, 't1_after_o_scale'))
    x1 = G.add(x, o)
    r = G.rstd(x1, np.float32(1e-6))
    down_partials = []
    for im in images:
        meta = im.manifest['matrix_layout'][2]
        codes, scales = im.matrix(meta)
        gu = G.mul(G.mul(G.matvec(codes.astype(np.float32), x1, meta['split']), scales), r)
        gu = gu.reshape(48, 2, 128)
        act = G.mul(G.silu(gu[:, 0, :].reshape(-1)), gu[:, 1, :].reshape(-1))
        meta = im.manifest['matrix_layout'][3]
        codes, _ = im.matrix(meta)
        down_partials.append(G.matvec(codes.astype(np.float32), act, meta['split']))
    down_scale = images[0].matrix(images[0].manifest['matrix_layout'][3])[1]
    down = G.mul(G.fold(down_partials), down_scale)
    np.testing.assert_array_equal(G.bits(down), _bits(0, 't1_after_down_scale'))
    np.testing.assert_array_equal(G.bits(G.add(x1, down)), _bits(0, 'x_final'))
