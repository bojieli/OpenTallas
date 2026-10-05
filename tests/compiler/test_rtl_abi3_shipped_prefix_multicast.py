"""Focused checks for the frozen shipped-prefix wafer-multicast overlay."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from tools import build_abi3_shipped_prefix_multicast_vectors as generator
from tools import rtl_abi3_shipped_prefix_campaign as base_campaign
from tools import rtl_abi3_shipped_prefix_multicast_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix_multicast"
VECTOR_JSON = VECTOR_DIR / "abi3_shipped_prefix_multicast_vectors.json"
CAMPAIGN_JSON = ROOT / "results/rtl/abi3_shipped_prefix_multicast_campaign.json"

TOOLS_AVAILABLE = (
    all(shutil.which(name) is not None for name in ("iverilog", "vvp", "g++"))
    and (
        campaign.TOOLS_ROOT
        / f"verilator-{campaign.PINNED_VERILATOR_VERSION}/bin/verilator"
    ).is_file()
)


def vectors() -> dict:
    return json.loads(VECTOR_JSON.read_text(encoding="utf-8"))


def test_overlay_builder_reproduces_every_retained_image(tmp_path: Path) -> None:
    rebuilt = generator.build(tmp_path)
    assert rebuilt == vectors()
    for name in sorted(rebuilt["image_sha256"]):
        assert (tmp_path / name).read_bytes() == (VECTOR_DIR / name).read_bytes()


def test_overlay_preserves_source_current_identity_and_advances_only_rom() -> None:
    body = vectors()
    assert body["schema"] == generator.SCHEMA
    assert body["status"] == "source_current_rtl_integration_only"
    assert body["promotion_status"] == "source_current_bounded_prefix_only"
    assert "architectural token commit" in body["promotion_blocker"]
    assert body["base_vector_set"]["sha256"] == (
        "cd72fa9e711340095da1f8698abc7a810d2a82750d6bde43ec0144257a53b09d"
    )
    assert body["real_launch_count"] == 29
    assert body["multicast_launch_count"] == 1
    assert body["result_word_count"] == 91_136
    assert body["resolved_view_count"] == 100
    assert body["capability_fault_count"] == 4
    assert body["issue_count"] == 33
    assert body["exact_multicast"]["next_unsupported"] == {
        "pc": 15,
        "family": 48,
        "sub": 9,
        "opcode": "VECTOR.MHC",
        "descriptor_id": 381,
        "trap_class": 4,
    }
    expected = body["expected_cases"]
    assert [case["launches"] for case in expected] == [10, 10, 5, 4]
    assert [case["multicast_launches"] for case in expected] == [0, 0, 1, 0]
    assert [case["fault"] for case in expected] == [32, 32, 15, 14]
    assert [case["responses"] for case in expected] == [11, 11, 6, 5]
    assert [case["views"] for case in expected] == [33, 33, 17, 17]
    assert all(
        "decoded-token correctness" in body["does_not_establish"][1] for _ in [0]
    )
    assert any("architectural TPOT" in item for item in body["does_not_establish"])


def test_exact_records_payload_and_qualification_are_bound() -> None:
    body = vectors()
    qualification = body["multicast_qualification"]
    assert qualification["adapter_source_sha256"] == (
        "baf8bd310fdc7a25b4dfa9d464932f87a4a9c8f4c7e7074102488aeb5922b8bb"
    )
    assert qualification["geometry"] == {
        "participants": 256,
        "rounds": 8,
        "messages": 255,
        "bytes_per_message": 65_536,
        "payload_bytes": 16_711_680,
        "words_per_message": 16_384,
        "payload_flits": 4_177_920,
        "remote_writes_including_root": 4_194_304,
    }
    assert qualification["exact_case"] == {
        "index": 0,
        "label": "exact_pc13_multicast_crc_replay",
        "admitted": True,
        "refusal_reason": 0,
        "inject_crc": True,
    }
    source_words = generator.read_hex(VECTOR_DIR / "p3_multicast_source.hex")
    assert len(source_words) == 16_384
    assert source_words == [generator.payload_word(index) for index in range(16_384)]
    retained = campaign.load_multicast_qualification(body)
    assert retained["status"] == "pass"
    assert retained["simulators_agree"]
    assert retained["checks_per_simulator"] == 12_583_553
    assert retained["exact_case"]["replayed"] == 4


def test_campaign_loads_source_current_overlay() -> None:
    base = base_campaign.load_vectors()
    assert campaign.load_extension(base) == vectors()


def test_campaign_refuses_to_overwrite_existing_artifact(tmp_path: Path) -> None:
    target = tmp_path / "campaign.json"
    target.write_text("{}\n", encoding="utf-8")
    assert campaign.main(["--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "{}\n"


def test_retained_campaign_is_current_and_non_promotable() -> None:
    retained = json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))
    assert CAMPAIGN_JSON.read_bytes() == (
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    assert retained["status"] == "pass"
    assert retained["promotion_status"] == "source_current_bounded_prefix_only"
    assert retained["integrated_replay_passed"]
    assert retained["simulator_correlation"] == {
        "verilator_cases_match": True,
        "deepseek_rom_cases_agree": True,
        "exact_check_counts_match_retained_constants": True,
    }
    assert (
        retained["next_unsupported"] == vectors()["exact_multicast"]["next_unsupported"]
    )
    assert retained["real_launch_count"] == 29
    assert retained["multicast_launch_count"] == 1
    assert retained["result_word_count"] == 91_136
    assert retained["resolved_view_count"] == 100
    assert retained["scope"]["architectural_tpot_claim"] is False
    assert retained["scope"]["decoded_token_correctness_claim"] is False
    assert (
        retained["compositional_multicast_qualification"]["checks_per_simulator"]
        == 12_583_553
    )
    assert retained["compositional_rope_qualification"]["status"] == "pass"
    assert retained["compositional_rope_qualification"]["qualified_positions"] == [
        0,
        7_999,
    ]
    for path, record in retained["source"].items():
        source = ROOT / path
        assert source.stat().st_size == record["bytes"]
        assert campaign.sha256_file(source) == record["sha256"]


@pytest.mark.skipif(
    not TOOLS_AVAILABLE,
    reason="Icarus, vvp, pinned Verilator, and g++ are required",
)
def test_focused_dual_simulator_campaign(tmp_path: Path) -> None:
    summary = campaign.run(tmp_path / "build")
    assert summary["status"] == "pass", summary["cases"]
    assert summary["integrated_replay_passed"]
    assert summary["simulator_correlation"] == {
        "verilator_cases_match": True,
        "deepseek_rom_cases_agree": True,
        "exact_check_counts_match_retained_constants": True,
    }
    assert summary["integrated_simulator_checks"] == {
        "verilator_full_four_case": campaign.EXPECTED_VERILATOR_CHECKS,
        "iverilog_deepseek_rom_only": campaign.EXPECTED_IVERILOG_CHECKS,
    }
    assert [case["status"] for case in summary["cases"]] == ["pass", "pass"]
