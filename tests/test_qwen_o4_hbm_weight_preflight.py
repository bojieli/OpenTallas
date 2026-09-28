"""Check the O4 HBM address and traffic boundary against the adopted model."""
import sys
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from qwen_o4_hbm_weight_preflight import evaluate, matrix_traffic  # noqa: E402


def test_o4_hbm_address_and_controller_contract():
    gate = evaluate()
    assert gate["status"] == "pass"
    assert gate["configuration"]["int8_word_bytes"] == 98_304
    assert gate["package"]["minimum_sector_address_bits"] >= 28
    assert not gate["existing_wstream_incompatibilities"]["default_hbm_sector_address_bits_sufficient_for_resident_layout"]
    assert gate["existing_wstream_incompatibilities"]["minimum_prefetch_bytes_for_longest_unstalled_op_at_stated_hbm_bw"] > gate["existing_wstream_incompatibilities"]["default_window_bytes_if_scaled_to_full_o4_word"]
    assert gate["package"]["rom_word_identical_weight_and_kv_bytes_per_token"] > gate["package"]["model_hbm_bytes_per_token_including_kv"]
    assert gate["sector_roundtrip"]["code_endpoints"] == [-128, -1, 0, 1, 127]
    area = gate["staging_area_sensitivity"]
    assert area["code_window_bytes_per_die"] == 512 * 98_304
    assert area["code_window_mib_per_die"] == 48
    assert 46 < area["minimum_starting_prefetch_mib_for_unstalled_round_with_perfect_streaming"] < 47
    assert 16 < area["code_window_mm2_at_kv_buffer_density"] < 17
    assert area["status"] == "conditional_unpriced"


def test_padding_changes_with_actual_tiling():
    down = matrix_traffic("down", 4096, 6144, 36)
    assert down["k_split"] == 2048
    assert down["padding_bytes"] == 36 * 786_432
    qkv = matrix_traffic("qkv", 3072, 4096, 36)
    assert qkv["padding_bytes"] == 0
    assert qkv["code_sectors"] * 32 == qkv["identical_rom_word_bytes"]


def test_committed_record_is_source_pinned():
    record = json.loads((ROOT / "results/rtl/qwen_o4_hbm_weight_preflight.json").read_text())
    assert record["status"] == "pass"
    assert record["package"]["minimum_sector_address_bits"] == 28
    for name, digest in record["input_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
