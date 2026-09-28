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


def test_fp4_sparse_expert_uses_absolute_id_and_per_row_scales():
    packed = np.arange(32 * 32, dtype=np.uint16).reshape(32, 32).astype(np.uint8)
    scales = np.tile(np.array([113, 114], dtype=np.uint8), (32, 1))
    image, geom = W.pack_fp4(packed, scales, base_word=110 * 4, chunks=8)
    W.verify_fp4(image, packed, scales, geom)
    assert geom["word_count"] == 4
    assert geom["base_word"] == 440
    address, bank = W.bank_slot(31, 1, geom, 440)
    assert image[address - 440, bank, 16] == 114
    damaged = image.copy()
    damaged[address - 440, bank, 0] ^= 1
    with pytest.raises(AssertionError, match="readback mismatch"):
        W.verify_fp4(damaged, packed, scales, geom)


def test_real_constant_manifest_bf16_to_fp32(tmp_path: Path):
    source = W.ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
    image_dir = Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0")
    if not (image_dir / "w.attn_norm.bin").is_file():
        pytest.skip("source-pinned full-shape scratch image not present")
    rec = W.pack_constant_from_manifest(source, image_dir, "attn_norm", tmp_path / "crom.bin")
    words = np.fromfile(tmp_path / "crom.bin", dtype="<u4").reshape(-1, 2)
    raw = np.fromfile(image_dir / "w.attn_norm.bin", dtype="<u2")
    assert len(words) == len(raw) == 5120
    assert np.array_equal(words[:, 0], raw.astype(np.uint32) << 16)
    assert not words[:, 1].any()
    assert rec["constants"]["attn_norm"]["word_count"] == 5120


def test_combine_rejects_overlap_and_preserves_sparse_expert_flag(tmp_path: Path):
    base = {"schema": W.SCHEMA, "source_image_manifest_sha256": "same", "layer": 0, "rank": 0}
    dense = dict(base, matrices={"wq_a": {"engine": "qe", "base_word": 0,
        "word_count": 8, "format": "F8_E4M3_UE8M0_32x32",
        "expert_id_base": None, "expert_stride_words": None}})
    sparse = dict(base, matrices={"exp110.w1": {"engine": "qe", "base_word": 8 + 110 * 2,
        "word_count": 2, "format": "F4_E2M1_UE8M0_rowx32",
        "expert_id_base": 8, "expert_stride_words": 2,
        "expert_reserved_end_word_exclusive": 8 + 384 * 2,
        "all_experts_materialized": False}})
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(dense))
    b.write_text(json.dumps(sparse))
    merged = W.combine_layout_records([a, b])
    assert merged["reserved_bytes"] == 8 * 64 * 33 + 384 * 2 * 64 * 17
    assert merged["all_experts_materialized"] is False
    sparse["matrices"]["exp110.w1"]["expert_id_base"] = 7
    b.write_text(json.dumps(sparse))
    with pytest.raises(ValueError, match="overlap"):
        W.combine_layout_records([a, b])


def test_me_he_bank_row_order_and_roundtrip():
    me = np.arange(8 * 32, dtype=np.uint16).reshape(8, 32)
    me_image, me_geom = W.pack_me_bf16(me, base_word=17)
    W.verify_me(me_image, me, me_geom)
    assert me_geom["plg"] == 2  # RTL ME adapter: ceil(log2(ceil(32/8)))
    address, bank = W.bank_slot(7, 31, me_geom, 17)
    assert me_image[address - 17, bank] == np.uint32(me[7, 31]) << 16
    he = np.arange(3 * 64, dtype=np.uint32).reshape(3, 64)
    he_image, he_geom = W.pack_he_fp32(he, base_word=23)
    W.verify_he(he_image, he, he_geom)
    assert he_geom["word_count"] == 3
    assert he_image[2, 7, 7] == he[2, 63]


def test_me_full_gate_uses_rtl_selected_segment_level():
    bits = np.zeros((96, 5120), dtype=np.uint16)
    _, geom = W.pack_me_bf16(bits)
    assert geom["plg"] == 3
    assert geom["nbeat"] == 80 and geom["rows_per_group"] == 1


def test_real_wo_a_fp8_to_bf16_matches_golden():
    from tools import hdc_golden as G
    from tools import hdc_golden_v41 as V

    image_dir = Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0")
    if not (image_dir / "w.wo_a.bin").is_file():
        pytest.skip("source-pinned full-shape scratch image not present")
    codes = np.fromfile(image_dir / "w.wo_a.bin", dtype=np.uint8).reshape(2048, 4096)[:32]
    scales = np.fromfile(image_dir / "w.wo_a.scale.bin", dtype=np.uint8).reshape(64, 128)[:1]
    ours = W.wo_a_fp8_to_bf16(codes, scales)
    golden = G.to_bf16(V._blocked(codes, scales.astype(np.int32) - 127, "wo_a").dense())
    assert np.array_equal(ours, (G.bits(golden) >> 16).astype(np.uint16))


def test_generated_pre0_has_exact_low_half_and_zero_high(tmp_path: Path):
    source = W.ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
    rec = W.pack_pre0_constant(source, tmp_path / "pre0.bin", 23)
    words = np.fromfile(tmp_path / "pre0.bin", dtype="<u4").reshape(4, 2)
    assert words.tolist() == [[0x3f800000, 0], [0, 0], [0, 0], [0, 0]]
    assert rec["constants"]["pre0"]["base_word"] == 23
