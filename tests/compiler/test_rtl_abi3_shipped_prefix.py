"""Focused checks for the shipped ABI 3.0 sequencer/engine prefix witness."""

from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from tools import build_abi3_shipped_prefix_vectors as generator
from tools import rtl_abi3_shipped_prefix_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
VECTOR_JSON = VECTOR_DIR / "abi3_shipped_prefix_vectors.json"
CAMPAIGN_JSON = ROOT / "results/rtl/abi3_shipped_prefix_campaign.json"

TOOLS_AVAILABLE = shutil.which("g++") is not None and (
    shutil.which("verilator") is not None
    or (
        campaign.TOOLS_ROOT
        / f"verilator-{campaign.PINNED_VERILATOR_VERSION}/bin/verilator"
    ).is_file()
)


def _vectors() -> dict:
    return json.loads(VECTOR_JSON.read_text(encoding="utf-8"))


def _retained_campaign() -> dict:
    return json.loads(CAMPAIGN_JSON.read_text(encoding="utf-8"))


def test_vector_builder_reproduces_every_retained_image(tmp_path: Path) -> None:
    assert generator.build(["--output", str(tmp_path)]) == 0
    rebuilt = json.loads(
        (tmp_path / VECTOR_JSON.name).read_text(encoding="utf-8")
    )
    assert rebuilt == _vectors()
    for name in sorted(rebuilt["image_sha256"]):
        assert (tmp_path / name).read_bytes() == (VECTOR_DIR / name).read_bytes()


def test_witness_is_exactly_the_small_abi3_fail_stop_prefix() -> None:
    vectors = _vectors()
    assert vectors["schema"] == generator.VECTOR_SCHEMA
    assert vectors["abi"] == {"major": 3, "minor": 0}
    assert vectors["state_compat"] == 0
    assert vectors["case_count"] == 4
    assert vectors["real_engine_launch_count"] == 16
    assert vectors["dma_gather_launch_count"] == 6
    assert vectors["embedding_launch_count"] == 4
    assert vectors["rms_norm_launch_count"] == 2
    assert vectors["dma_transfer_launch_count"] == 2
    assert vectors["matmul_launch_count"] == 2
    assert vectors["rope_result_word_count"] == 1_024
    assert vectors["embedding_result_word_count"] == 16_384
    assert vectors["rms_norm_result_word_count"] == 8_192
    assert vectors["dma_transfer_result_word_count"] == 32_768
    assert vectors["matmul_result_word_count"] == 8_192
    assert vectors["matmul_mac_count"] == 33_554_432
    assert vectors["selected_embedding_checkpoint_byte_count"] == 32_768
    assert vectors["selected_rms_checkpoint_byte_count"] == 16_384
    assert vectors["selected_matmul_checkpoint_byte_count"] == 67_108_864
    assert vectors["selected_checkpoint_byte_count"] == 67_158_016
    assert vectors["result_word_count"] == 66_560
    assert vectors["resolved_view_count"] == 58
    assert vectors["capability_fault_count"] == 4
    assert [case["name"] for case in vectors["cases"]] == [
        "qwen3-8b-rom-single-chip/decode",
        "qwen3-8b-hbm-single-chip/decode",
        "deepseek-v4-flash-rom-wafer/decode",
        "deepseek-v4-flash-hbm-cluster/decode",
    ]
    assert [case["first_unsupported"] for case in vectors["cases"]] == [
        {
            "pc": 14,
            "family": 32,
            "sub": 0,
            "opcode": "TENSOR.MATMUL",
            "descriptor_id": 67,
            "trap_class": 4,
        },
        {
            "pc": 14,
            "family": 32,
            "sub": 0,
            "opcode": "TENSOR.MATMUL",
            "descriptor_id": 78,
            "trap_class": 4,
        },
        {
            "pc": 13,
            "family": 144,
            "sub": 3,
            "opcode": "LINK.MULTICAST",
            "descriptor_id": 368,
            "trap_class": 4,
        },
        {
            "pc": 14,
            "family": 48,
            "sub": 9,
            "opcode": "VECTOR.MHC",
            "descriptor_id": 546,
            "trap_class": 4,
        },
    ]
    for case_index, case in enumerate(vectors["cases"]):
        assert not case["expected"]["complete"]
        assert case["expected"]["state_compat"] == 0
        assert case["expected"]["embedding_launches"] == 1
        assert case["expected"]["embedding_result_words"] == 4_096
        assert case["expected"]["selected_checkpoint_bytes"] == (
            33_570_816 if case_index < 2 else 8_192
        )
        assert case["expected"]["wait_events"] == (
            3 if case_index < 2 else (1 if case_index == 2 else 2)
        )
        assert case["expected"]["retired"] + 1 == case["expected"]["fetched"]

        embedding = next(
            operation
            for operation in case["supported_prefix"]
            if operation["kind"] == "tensor_embed_lookup"
        )
        source = embedding["source"]
        assert embedding["token_id"] == 0
        assert embedding["source_view"]["dims"][1] == 4_096
        assert source["selected_token_id"] == 0
        assert source["selected_row_bytes"] == 8_192
        assert source["selected_row_logical_offset"] == 0
        assert source["selected_row_segment_offset"] == 0
        assert source["selected_row_file_range"] == {
            "start": source["selected_row_file_offset"],
            "stop_exclusive": source["selected_row_file_offset"] + 8_192,
        }
        assert len(source["declared_segment_sha256"]) == 64
        assert len(source["selected_row_sha256"]) == 64
        assert "only this selected byte range was re-read and hashed" in source[
            "authentication_boundary"
        ]
        if case_index < 2:
            assert case["bank_mapping"]["matmul_weight_base"] == 0
            rms_norm = next(
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "vector_rms_norm"
            )
            gain = rms_norm["weight_source"]
            assert case["expected"]["rms_norm_launches"] == 1
            assert case["expected"]["dma_transfer_launches"] == 0
            assert rms_norm["input_source"] == "prior_embedding_result_bank"
            assert rms_norm["contract_sha256"] == (
                "999ef86bc4d4c36dfd57db84d49618af46bed2e6c1f0b1bf031a27b5b8c03fda"
            )
            assert rms_norm["expected_row_sha256"] == (
                "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58"
            )
            assert rms_norm["mean_square_code"] == 0x3A5BF2CA
            assert rms_norm["inverse_rms_code"] == 0x420A0297
            assert gain["object_content_sha256"] == (
                "579d67ccd61b48d4b026755a6187d3e9ae690baa03b9e11ab4ece0fe6c8add44"
            )
            assert gain["selected_row_file_offset"] == 1_244_669_048
            assert gain["selected_row_bytes"] == 8_192
            assert gain["selected_row_sha256"] == (
                "00695bad97c2abc77a9d1ce57e4d4a5e5c2b574387fcb4029ef5ce12239b2530"
            )
            matmul = next(
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "tensor_matmul"
            )
            weight = matmul["weight_source"]
            assert case["expected"]["matmul_launches"] == 1
            assert case["expected"]["matmul_result_words"] == 4_096
            assert case["expected"]["matmul_mac_count"] == 16_777_216
            assert matmul["input_source"] == "prior_rms_norm_result_bank"
            assert matmul["contract_sha256"] == (
                "7550dc6a773fd9d5773b46182887613fb777bb8e4f01652321c4d93ca0765aa1"
            )
            assert matmul["executed_association"] == (
                "ot_a3_mac_lane_single_lane_ascending_k_v1"
            )
            assert matmul["expected_row_sha256"] == (
                "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff"
            )
            assert weight["declared_segment_bytes"] == 33_554_432
            assert weight["declared_segment_sha256"] == (
                "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
            )
            assert weight["selected_matrix_shape"] == [4_096, 4_096]
            assert weight["selected_matrix_sha256"] == weight[
                "declared_segment_sha256"
            ]
            assert "complete selected source segment" in weight[
                "authentication_boundary"
            ]
        else:
            transfer = next(
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "dma_transfer"
            )
            assert case["expected"]["rms_norm_launches"] == 0
            assert case["expected"]["dma_transfer_launches"] == 1
            assert transfer["contract_sha256"] == (
                "4ae1e59ac03a9c23abf11fe7e8193a6496e2dd4169e9369260202d2a7a0f1894"
            )
            assert transfer["input_view"]["strides"] == [4_096, 0, 1]
            assert transfer["output_view"]["strides"] == [16_384, 4_096, 1]
            assert transfer["lowering"] == {
                "operation": "four_row_gather",
                "indices": [0, 0, 0, 0],
                "slots": 4,
                "trailing": 4_096,
                "extent": 1,
                "source": "prior_embedding_result_bank",
            }


def test_vector_and_deployment_images_are_fresh() -> None:
    vectors = campaign.load_vectors()
    assert vectors == _vectors()
    for name, expected in vectors["image_sha256"].items():
        assert campaign.sha256_file(VECTOR_DIR / name) == expected
    source = vectors["input_deployment_vectors"]
    assert campaign.sha256_file(ROOT / source["path"]) == source["sha256"]
    for name, expected in source["images"].items():
        assert campaign.sha256_file(campaign.DEPLOYMENT_VECTOR_DIR / name) == expected


def test_retained_campaign_is_current_and_states_the_simple_boundary() -> None:
    retained = _retained_campaign()
    assert CAMPAIGN_JSON.read_bytes() == (
        json.dumps(retained, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    assert retained["status"] == "pass"
    assert retained["evidence_class"] == (
        "public_open_tool_rtl_simulation_composite"
    )
    assert retained["evidence_mode"] == (
        "full_integrated_verilator_plus_dual_simulator_mac_lane_composition"
    )
    assert retained["abi"] == {"major": 3, "minor": 0}
    assert retained["state_compat"] == 0
    assert retained["state_activity"] == {
        "compatibility_controller_elaborated": False,
        "configured_state_descriptor_count": 0,
        "prepare_count": 0,
        "commit_count": 0,
        "discard_count": 0,
        "read_count": 0,
        "generation_advance_count": 0,
        "commit_apply_count": 0,
        "rows_committed": 0,
        "bytes_written": 0,
        "apply_overflow_count": 0,
    }
    assert retained["post_fault_write_count"] == 0
    assert retained["integrated_replay_passed"]
    assert retained["integrated_simulators"] == ["verilator"]
    assert retained["integrated_simulator_checks"] == {
        "verilator": 136_496,
    }
    assert "simulators_agree" not in retained
    assert "simulator_checks" not in retained
    lane = retained["compositional_mac_lane_qualification"]
    assert lane["artifact"] == "results/rtl/abi3_engine_campaign.json"
    assert lane["artifact_sha256"] == campaign.sha256_file(
        campaign.ENGINE_CAMPAIGN
    )
    assert lane["status"] == "pass"
    assert lane["simulators_counted"] == [
        "iverilog_vvp",
        "verilator_cpp_executable",
    ]
    assert lane["checks_per_simulator"] == {
        "iverilog": 40_878,
        "verilator": 40_878,
    }
    assert lane["qualified_mac_count"] == 59_868
    assert lane["lane_source"] == "rtl/abi3/ot_a3_mac_lane.sv"
    assert lane["lane_source_sha256"] == campaign.sha256_file(
        ROOT / lane["lane_source"]
    )
    assert lane["qualification_contract"] == (
        "bf16_bf16_fp32_sequential_rne_v1"
    )
    assert "not the full shipped program" in lane["composition_boundary"]
    assert any(
        "complete integrated shipped-prefix execution under Icarus" in item
        for item in retained["scope"]["does_not_establish"]
    )
    assert [site["pc"] for site in retained["fault_sites"]] == [14, 14, 13, 14]
    assert [site["descriptor_id"] for site in retained["fault_sites"]] == [
        67,
        78,
        368,
        546,
    ]
    assert [site["opcode"] for site in retained["fault_sites"]] == [
        "TENSOR.MATMUL",
        "TENSOR.MATMUL",
        "LINK.MULTICAST",
        "VECTOR.MHC",
    ]
    assert retained["dma_gather_launch_count"] == 6
    assert retained["embedding_launch_count"] == 4
    assert retained["rms_norm_launch_count"] == 2
    assert retained["dma_transfer_launch_count"] == 2
    assert retained["matmul_launch_count"] == 2
    assert retained["real_engine_launch_count"] == 16
    assert retained["result_word_count"] == 66_560
    assert retained["resolved_view_count"] == 58
    assert retained["matmul_result_word_count"] == 8_192
    assert retained["matmul_mac_count"] == 33_554_432
    assert retained["selected_matmul_checkpoint_byte_count"] == 67_108_864
    assert retained["selected_checkpoint_byte_count"] == 67_158_016
    assert len(retained["checkpoint_rows"]) == 4
    for row in retained["checkpoint_rows"]:
        assert len(row["deployment_sha256"]) == 64
        assert row["deployment_identity_evidence"]["artifact"]
        assert row["source"]["selected_row_bytes"] == 8_192
        assert row["source"]["selected_row_file_range"]["stop_exclusive"] - row[
            "source"
        ]["selected_row_file_range"]["start"] == 8_192
    assert len(retained["checkpoint_gains"]) == 2
    for gain in retained["checkpoint_gains"]:
        assert gain["source"]["selected_row_bytes"] == 8_192
        assert gain["numeric_contract_sha256"] == (
            "999ef86bc4d4c36dfd57db84d49618af46bed2e6c1f0b1bf031a27b5b8c03fda"
        )
    assert len(retained["checkpoint_matrices"]) == 2
    for matrix in retained["checkpoint_matrices"]:
        assert matrix["operator_pc"] == 11
        assert matrix["numeric_contract_sha256"] == (
            "7550dc6a773fd9d5773b46182887613fb777bb8e4f01652321c4d93ca0765aa1"
        )
        assert matrix["executed_association"] == (
            "ot_a3_mac_lane_single_lane_ascending_k_v1"
        )
        assert matrix["expected_row_sha256"] == (
            "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff"
        )
        assert matrix["source"]["declared_segment_bytes"] == 33_554_432
        assert matrix["source"]["declared_segment_sha256"] == (
            "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
        )
    assert retained["staged_matmul_weight"] == {
        "path": "generated/p3_matmul_weight.bin",
        "bytes": 33_554_432,
        "sha256": (
            "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8"
        ),
        "source_checkpoint_revision": (
            "b968826d9c46dd6066d109eabc6255188de91218"
        ),
        "source_shard": "model-00001-of-00005.safetensors",
        "source_offset": 1_588_618_872,
    }
    for path, record in retained["source"].items():
        source_path = ROOT / path
        assert source_path.stat().st_size == record["bytes"]
        assert campaign.sha256_file(source_path) == record["sha256"], path
    assert retained["vector_set"]["sha256"] == campaign.sha256_file(VECTOR_JSON)


def test_campaign_refuses_to_overwrite_an_existing_artifact(
    tmp_path: Path,
) -> None:
    target = tmp_path / "campaign.json"
    target.write_text("{}\n", encoding="utf-8")
    assert campaign.main(["--output", str(target)]) == 2
    assert target.read_text(encoding="utf-8") == "{}\n"


@pytest.mark.skipif(
    not TOOLS_AVAILABLE,
    reason="Verilator and a C++ compiler are required",
)
def test_focused_campaign_replays_verilator_and_binds_mac_lane(
    tmp_path: Path,
) -> None:
    summary = campaign.run(tmp_path / "build")
    assert summary["status"] == "pass", summary["cases"]
    assert summary["integrated_replay_passed"]
    assert summary["integrated_simulators"] == ["verilator"]
    assert summary["integrated_simulator_checks"] == {
        "verilator": 136_496,
    }
    assert "simulators_agree" not in summary
    assert "simulator_checks" not in summary
    assert summary["compositional_mac_lane_qualification"][
        "simulators_counted"
    ] == ["iverilog_vvp", "verilator_cpp_executable"]
    assert summary["post_fault_write_count"] == 0
    assert [case["name"] for case in summary["cases"]] == ["verilator"]
    for simulator in summary["cases"]:
        assert simulator["status"] == "pass"
        assert simulator["compile_returncode"] == 0, simulator["compile_log"]
        assert simulator["run_returncode"] == 0, simulator["run_log"]
        assert simulator["marker_present"]
        assert simulator["observed_cases"] == summary["expected_cases"]
