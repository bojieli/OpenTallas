"""The reduced INT8 image matches the deployed quantizer and RTL row addresses."""
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402
import hdc_program as P  # noqa: E402
from hdc_qwen_int8_image import Int8Layout, write_images  # noqa: E402


@pytest.mark.skipif(not G.CHECKPOINT.exists(), reason="reduced Qwen checkpoint missing")
def test_tp2_int8_image_addresses_and_quantizer(tmp_path):
    layout = Int8Layout(G.Model(P.GR, 2), 2, 0)
    assert len(layout.quantized) == 17
    assert len(layout.code_words) == layout.emb_word == 10240
    rng = np.random.default_rng(20260928)
    for base, (codes, scales, _) in layout.quantized.items():
        for _ in range(32):
            row = int(rng.integers(codes.shape[0]))
            column = int(rng.integers(codes.shape[1]))
            assert layout.matrix_code(base, row, column) == codes[row, column]
            assert layout.scale_words[base + row // P.W][row % P.W] == scales[row]
    meta = write_images(layout, tmp_path)
    assert meta["matrix_words"] == 10240
    assert meta["embedding_rows"] == 4096
    first_code_word = int((tmp_path / "matrix_int8.hex").read_text().splitlines()[0], 16)
    first_scale_word = int((tmp_path / "matrix_scale_bf16.hex").read_text().splitlines()[0], 16)
    assert first_code_word == P.pack_lanes(layout.code_words[0], 8)
    assert first_scale_word == P.pack_lanes(layout.scale_words[0], 16)
    assert layout.embed_codes.shape == (4096, 128)
