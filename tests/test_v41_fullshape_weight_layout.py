"""Exact byte placement for the shipped-shape V4.1 FP8 tile gate."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools import v41_fullshape_weight_layout as W


def test_pack_readback_and_scale_broadcast():
    codes = np.arange(32 * 64, dtype=np.uint16).reshape(32, 64).astype(np.uint8)
    codes[codes == 127] = 0
    codes[codes == 255] = 0
    scales = np.array([[113, 114]], dtype=np.uint8)
    image, geom = W.pack_fp8(codes, scales, base_word=11, chunks=8)
    assert geom["useful_bank_words"] == 64
    assert geom["padded_bank_words"] == 192
    W.verify_fp8(image, codes, scales, geom)
    addr, bank = W.bank_slot(31, 1, geom, 11)
    assert image[addr - 11, bank, 32] == 114
    assert image[addr - 11, bank, :32].tolist() == codes[31, 32:].tolist()
    damaged = image.copy()
    damaged[addr - 11, bank, 32] ^= 1
    with pytest.raises(AssertionError, match="readback mismatch"):
        W.verify_fp8(damaged, codes, scales, geom)


def test_rejects_missing_scale_and_nan_code():
    codes = np.zeros((32, 32), np.uint8)
    with pytest.raises(ValueError, match="scale shapes"):
        W.pack_fp8(codes, np.zeros((1, 2), np.uint8))
    codes[0, 0] = 0x7f
    with pytest.raises(ValueError, match="NaN"):
        W.pack_fp8(codes, np.zeros((1, 1), np.uint8))


def test_manifest_fails_closed_on_mutated_source(tmp_path: Path):
    codes = np.zeros((32, 32), np.uint8)
    scales = np.full((1, 1), 127, np.uint8)
    for name, data in (("w.x", codes), ("w.x.scale", scales)):
        (tmp_path / f"{name}.bin").write_bytes(data.tobytes())
    files = {
        "w.x": {"format": "F8_E4M3", "shape": [32, 32],
                "sha256": hashlib.sha256(codes.tobytes()).hexdigest()},
        "w.x.scale": {"format": "F8_E8M0", "shape": [1, 1],
                      "sha256": hashlib.sha256(scales.tobytes()).hexdigest()},
    }
    man = {"schema": "opentallas.rtl.hdc_v41x_fullshape_layers.v1.die_layer_images",
           "files": files, "source_commit": "test", "source_sha256": {},
           "checkpoint": {}, "layer": 0, "rank": 0}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(man))
    result = W.pack_from_manifest(path, tmp_path, "x", tmp_path / "out.bin")
    assert result["matrices"]["x"]["word_count"] == 4
    (tmp_path / "w.x.bin").write_bytes(b"bad")
    with pytest.raises(ValueError, match="source-pinned"):
        W.pack_from_manifest(path, tmp_path, "x", tmp_path / "out.bin")
