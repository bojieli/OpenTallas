"""Exact current-core QE stream words from real FP8/FP4 checkpoint slices."""

from pathlib import Path

import numpy as np
import pytest

from tools import v41_fullshape_qe_stream_image as Q


def test_fp8_round_block_slot_lane_order_and_final_tile_padding():
    codes = np.arange(160 * 64, dtype=np.uint16).reshape(160, 64).astype(np.uint8)
    codes[(codes == 127) | (codes == 255)] = 0
    scales = np.full((160 // 32, 2), 127, np.uint8)
    scales[4, 1] = 109
    logical, physical, geom = Q.pack_stream(codes, scales, False)
    assert geom["word_count"] == 32
    assert geom["padded_rows"] == 96
    idx = (1 * 2 + 1) * 8
    assert logical[idx, 0, :32].tolist() == codes[128, 32:64].tolist()
    assert int.from_bytes(logical[idx, 0, 32:].tobytes(), "little", signed=True) == -18
    assert not logical[idx + 2:].any()
    assert np.array_equal(logical, physical)
    Q.verify_stream(logical, physical, codes, scales, geom)
    logical[idx, 0, 0] ^= 1
    with pytest.raises(AssertionError, match="lane mismatch"):
        Q.verify_stream(logical, physical, codes, scales, geom)


def test_fp4_low_nibble_first_and_per_row_exponent():
    codes = np.zeros((16, 16), np.uint8)
    codes[0, 0] = 0xA3
    scales = np.full((16, 1), 127, np.uint8)
    scales[0, 0] = 121
    logical, physical, geom = Q.pack_stream(codes, scales, True)
    assert geom["word_count"] == 8
    assert logical[0, 0, :2].tolist() == [3, 10]
    assert physical[0, 0, 0] == 0xA3
    assert int.from_bytes(logical[0, 0, 32:].tobytes(), "little", signed=True) == -6
    assert logical[0, 1, 32:].tolist() == [0, 0]
    assert not logical[1:].any()
    Q.verify_stream(logical, physical, codes, scales, geom)
    physical[0, 0, 16] ^= 1
    with pytest.raises(AssertionError, match="physical exponent"):
        Q.verify_stream(logical, physical, codes, scales, geom)


def test_real_checkpoint_wq_a_and_expert_stream_address(tmp_path: Path):
    folder = Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0")
    if not (folder / "w.wq_a.bin").is_file():
        pytest.skip("source-pinned checkpoint scratch not available")
    manifest = Q.ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json"
    rec = Q.build(manifest, folder, tmp_path, ("wq_a", "exp110.w1"))
    wq = rec["matrices"]["wq_a"]
    exp = rec["matrices"]["exp110.w1"]
    assert wq["word_count"] == 3840
    assert exp["word_count"] == 6400
    assert exp["base_word"] == exp["expert_id_base"] + 110 * exp["expert_stride_words"]
    assert wq["sectors_per_word"] == 17 and exp["sectors_per_word"] == 9
    assert wq["image_bytes"] == 3840 * 544
    assert exp["image_bytes"] == 6400 * 288
    assert exp["adapter_required"] and not wq["adapter_required"]
    assert rec["token_runnable"] is False


def test_source_hash_mismatch_fails_closed(tmp_path: Path):
    folder = Path("/tmp/codex_v41_fullshape_golden/images/ctx200000_L00_r0")
    if not (folder / "w.wq_a.bin").is_file():
        pytest.skip("source-pinned checkpoint scratch not available")
    import json
    manifest = json.loads((Q.ROOT / "results/rtl/hdc_v41x_fullshape_200k_l0_rank0_image.json").read_text())
    manifest["files"]["w.wq_a"]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="source-pinned hash"):
        Q.source_matrix(manifest, folder, "wq_a")


def test_record_covers_selected_experts_and_capacity():
    import json
    record = json.loads((Q.ROOT / "results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json").read_text())
    assert record["layout_tool_sha256"] == Q.digest(Path(Q.__file__))
    assert record["source_image_manifest_sha256"] == Q.digest(
        Q.ROOT / record["source_image_manifest"])
    assert set(record["matrices"]) == set(Q.FULL_NAMES)
    assert record["logical_qrom_words"] == 7_191_680
    assert record["packed_die_bytes_reserved"] <= record["rom_capacity_bytes"]
    assert record["direct_expanded_fits_die"] is False
    assert record["numeric_lut_elements_checked"] == 25 * 27
    for family in Q.FAMILY_ORDER:
        selected = [record["matrices"][f"exp{i}.{family}"] for i in Q.SELECTED]
        assert all(m["base_word"] == m["expert_id_base"] + i * m["expert_stride_words"]
                   for i, m in zip(Q.SELECTED, selected))
        assert all(m["sectors_per_word"] == 9 and m["adapter_required"] for m in selected)
    assert record["all_experts_materialized"] is False
    assert record["token_runnable"] is False
