"""ROM-WEIGHTS-1119: S81 weights-only stage fixtures + stage image readback (decoders, spec rules, raw block words)."""
from __future__ import annotations

import json
import random
import struct
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
for p in ('tools', 'tools/s81_dv', 'tools/s81_dv/layer_prog', 'tools/s81_static_control'):
    sys.path.insert(0, str(ROOT / p))

import stage_fixtures as SF  # noqa: E402
import stage_images as SI  # noqa: E402


def test_viamap_decoder_inverts_writer(tmp_path):
    from rtl_v41_rom_array import viamap
    rng = random.Random(3)
    words = {a: rng.getrandbits(274) for a in rng.sample(range(8192), 300)}
    for par in (0, 1):
        bank = {a // 2: w for a, w in words.items() if a % 2 == par}
        p = tmp_path / f'e3_{par}.viamap.hex'
        viamap(bank, p)
        p.write_text(''.join(p.read_text().splitlines(keepends=True)[:512]))
    got = {}
    for par in (0, 1):
        for a, w in SI._vm_words(tmp_path / f'e3_{par}.viamap.hex', 548).items():
            got[2 * a + par] = w
    assert got == {a: w for a, w in words.items() if w}


def test_cfg_bank_decoder_inverts_encode_bank72(tmp_path):
    import xs_place as XP
    rng = random.Random(5)
    words = [rng.getrandbits(72) if rng.random() < 0.3 else 0 for _ in range(4096)]
    p = tmp_path / 'b.viamap.hex'
    p.write_text(''.join(f'{w:0144x}\n' for w in XP.encode_bank72(words)))
    got = SI._vm_words(p, 144)
    assert got == {a: w for a, w in enumerate(words) if w}


@pytest.mark.parametrize('half,dense,keep_wq_b,shared', [('A', 0, False, False), ('B', 0, True, True), ('X', None, False, False)])
def test_stage_spec_rules(half, dense, keep_wq_b, shared):
    import xs_capacity as XC
    s = dict(stage='R9', spec='t', dense_layer=dense, dense_split2=half, n_experts=3, experts=[[0, 5, 7]], layers=[0],
             capacity=dict(dense_split2_rows=224))
    spec = SF.stage_spec(s)
    assert spec['dense_split2'] == half and spec['experts'] == 3
    xs, bf, _ = XC.spec_ops(spec)
    assert ('attn.wq_b' in xs) == keep_wq_b
    assert SF.dense_keep(spec, 'wq_a') == (dense is not None)
    assert SF.dense_keep(spec, 'wq_b') == keep_wq_b
    assert SF.stage_experts(s) == [(0, 5), (0, 6), (0, 7)]


def _safetensors(path, tensors):
    hdr, off, blobs = {}, 0, []
    for name, (dt, shape, b) in tensors.items():
        hdr[name] = dict(dtype=dt, shape=shape, data_offsets=[off, off + len(b)])
        off += len(b)
        blobs.append(b)
    h = json.dumps(hdr).encode()
    path.write_bytes(struct.pack('<Q', len(h)) + h + b''.join(blobs))


def test_expect_block_words_from_raw_checkpoint(tmp_path):
    rng = np.random.default_rng(1)
    w8 = rng.integers(0, 256, (64, 512), dtype=np.uint8)            # FP8 rows x K
    s8 = rng.integers(100, 140, (2, 16), dtype=np.uint8)            # 32 x 32 block scales
    w4 = rng.integers(0, 256, (8, 256), dtype=np.uint8)             # FP4 packed: K = 512
    s4 = rng.integers(100, 140, (8, 16), dtype=np.uint8)            # per-row
    _safetensors(tmp_path / 'm.safetensors', {'a.w': ('F8_E4M3', [64, 512], w8.tobytes()),
                                               'a.s': ('F8_E8M0', [2, 16], s8.tobytes()),
                                               'b.w': ('I8', [8, 256], w4.tobytes()),
                                               'b.s': ('F8_E8M0', [8, 16], s4.tobytes())})
    (tmp_path / 'model.safetensors.index.json').write_text(json.dumps(
        {'weight_map': {k: 'm.safetensors' for k in ('a.w', 'a.s', 'b.w', 'b.s')}}))
    files = {'weights/A.bin': dict(tensor='a.w', rows=[32, 64], cols=None), 'weights/A.scale.bin': dict(tensor='a.s'),
             'weights/B.bin': dict(tensor='b.w', rows=[4, 8], cols=None), 'weights/B.scale.bin': dict(tensor='b.s')}
    ex = SI.Expect(SI.Raw(tmp_path), files)
    # fp8: fixture row 3 = checkpoint row 35, chunk 1, b 2 -> block 10 -> cols 320..352, scale [35 // 32, 10]
    want = int.from_bytes(w8[35, 320:352].tobytes(), 'little') | (int(s8[1, 10]) << 256)
    assert ex.block('fp8', 'A', 3, 1, 2) == want
    # fp4: fixture row 1 = checkpoint row 5, chunk 0, b 3 -> block 3 -> bytes 48..64, per-row scale [5, 3]
    want4 = int.from_bytes(w4[5, 48:64].tobytes(), 'little') | (int(s4[5, 3]) << 128)
    assert ex.block('fp4', 'B', 1, 0, 3) == want4
    # and the image writer's own word for the same block agrees (rtl_v41_rom_array.Mat.block_word through FMat)
    import xs_place as XP
    fm = XP.FMat('A', 'fp8', w8[32:64], s8[1:2], [3], 'x')
    assert fm.block_word(0, 1, 2) == want
    fm4 = XP.FMat('B', 'fp4', w4[4:8], s4[4:8], [1], 'x')
    assert fm4.block_word(0, 0, 3) == want4
