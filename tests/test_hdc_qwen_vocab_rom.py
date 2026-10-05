"""Shipped vocabulary endpoints preserve 18-bit token and TP2 row addresses."""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_qwen_int8_image as image  # noqa: E402
import hdc_qwen_vocab_rom as vocab  # noqa: E402
import hdc_golden as G  # noqa: E402


def test_last_lm_head_row_uses_last_engine_group():
    codes = np.arange(4096, dtype=np.int32).reshape(1, 4096).astype(np.int8).view(np.uint8)
    scales = np.array([0x3E80], dtype=np.uint16)
    words, sw, meta = vocab.head_window(codes, scales, 75967)
    assert meta['split'] == 1024 and meta['rounds'] == 99
    assert max(words) == 3163 and max(sw) == 4747
    assert words[3139][5120 * 16 + 15] == codes[0, 0]
    assert words[3163][6143 * 16 + 15] == codes[0, 4095]
    assert sw[4747][15] == scales[0]
    assert sw[4747][0] == 0x3F80


def test_last_embedding_code_word_fits_aw24():
    codes = np.arange(4096, dtype=np.int32).reshape(1, 4096).astype(np.int8).view(np.uint8)
    words, scale, meta = vocab.embed_window(codes, np.array([0x3F20], dtype=np.uint16), 151935)
    assert min(words) == 151935 * 64 and max(words) == 151936 * 64 - 1
    assert max(words) < 1 << 24
    assert scale[151935] == 0x3F20
    assert meta['full_code_words'] == 151936 * 64


def test_real_checkpoint_boundary_window_pins(tmp_path):
    import qwen3_deployment_quality as Q
    try:
        snapshot = Q.find_snapshot()
    except FileNotFoundError:
        pytest.skip('shipped Qwen3-8B checkpoint missing')
    for kind, die, start in (('embedding', None, 151935), ('lm_head', 1, 75967)):
        out = tmp_path / kind
        meta = vocab.write_window(snapshot, out, kind, start, 1, die)
        source = image.shipped_vocab_rows(snapshot, kind, start=start, count=1, die=die)
        assert meta['global_start'] == source['global_start'] == 151935
        assert meta['checkpoint_revision'] == snapshot.name
        for name, digest in meta['source_sha256'].items():
            assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest
        assert meta['code_word_count'] == (64 if kind == 'embedding' else 4)
        if kind == 'embedding':
            lines = (out / 'vm_x_fp32.hex').read_text().splitlines()
            assert lines[0] == '@1000' and len(lines) == 4097
            code = source['codes'].numpy()[0].astype(np.float32)
            scale = source['scales'].float().numpy()[0]
            assert [int(x, 16) for x in lines[1:]] == list(map(int, G.bits(G.mul(code, scale))))
