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
    rebuilt = json.loads((tmp_path / VECTOR_JSON.name).read_text(encoding="utf-8"))
    assert rebuilt == _vectors()
    for name in sorted(rebuilt["image_sha256"]):
        assert (tmp_path / name).read_bytes() == (VECTOR_DIR / name).read_bytes()


def test_witness_is_exactly_the_small_abi3_fail_stop_prefix() -> None:
    vectors = _vectors()
    assert vectors["schema"] == generator.VECTOR_SCHEMA
    assert vectors["abi"] == {"major": 3, "minor": 0}
    assert vectors["state_compat"] == 0
    assert vectors["case_count"] == 4
    assert vectors["real_engine_launch_count"] == 28
    assert vectors["dma_gather_launch_count"] == 6
    assert vectors["embedding_launch_count"] == 4
    assert vectors["rms_norm_launch_count"] == 2
    assert vectors["head_rms_norm_launch_count"] == 4
    assert vectors["rope_launch_count"] == 4
    assert vectors["dma_transfer_launch_count"] == 2
    assert vectors["matmul_launch_count"] == 6
    assert vectors["rope_coefficient_gather_result_word_count"] == 1_024
    assert vectors["rope_result_word_count"] == 10_240
    assert vectors["embedding_result_word_count"] == 16_384
    assert vectors["rms_norm_result_word_count"] == 8_192
    assert vectors["head_rms_norm_result_word_count"] == 10_240
    assert vectors["dma_transfer_result_word_count"] == 32_768
    assert vectors["matmul_result_word_count"] == 12_288
    assert vectors["matmul_mac_count"] == 50_331_648
    assert vectors["selected_embedding_checkpoint_byte_count"] == 32_768
    assert vectors["selected_rms_checkpoint_byte_count"] == 16_384
    assert vectors["selected_head_rms_checkpoint_byte_count"] == 1_024
    assert vectors["selected_matmul_checkpoint_byte_count"] == 100_663_296
    assert vectors["selected_checkpoint_byte_count"] == 100_713_472
    assert vectors["result_word_count"] == 91_136
    assert vectors["resolved_view_count"] == 94
    assert vectors["capability_fault_count"] == 4
    assert [case["name"] for case in vectors["cases"]] == [
        "qwen3-8b-rom-single-chip/decode",
        "qwen3-8b-hbm-single-chip/decode",
        "deepseek-v4-flash-rom-wafer/decode",
        "deepseek-v4-flash-hbm-cluster/decode",
    ]
    assert [case["first_unsupported"] for case in vectors["cases"]] == [
        {
            "pc": 32,
            "family": 16,
            "sub": 3,
            "opcode": "DMA.SCATTER",
            "descriptor_id": 114,
            "trap_class": 4,
        },
        {
            "pc": 32,
            "family": 16,
            "sub": 3,
            "opcode": "DMA.SCATTER",
            "descriptor_id": 114,
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
            50_348_544 if case_index < 2 else 8_192
        )
        assert case["expected"]["wait_events"] == (
            9 if case_index < 2 else (1 if case_index == 2 else 2)
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
        assert (
            "only this selected byte range was re-read and hashed"
            in source["authentication_boundary"]
        )
        if case_index < 2:
            assert [
                entry["base_words"]
                for entry in case["bank_mapping"]["matmul_weight_objects"]
            ] == [0, 16_777_216, 20_971_520]
            rms_norm = next(
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "vector_rms_norm"
            )
            gain = rms_norm["weight_source"]
            assert case["expected"]["rms_norm_launches"] == 1
            assert case["expected"]["head_rms_norm_launches"] == 2
            assert case["expected"]["rope_launches"] == 2
            assert case["expected"]["rope_coefficient_gather_result_words"] == 256
            assert case["expected"]["rope_result_words"] == 5_120
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
            matmuls = [
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "tensor_matmul"
            ]
            assert case["expected"]["matmul_launches"] == 3
            assert case["expected"]["matmul_result_words"] == 6_144
            assert case["expected"]["matmul_mac_count"] == 25_165_824
            assert [matmul["pc"] for matmul in matmuls] == [11, 14, 17]
            assert [matmul["association_scope"]["columns"] for matmul in matmuls] == [
                4_096,
                1_024,
                1_024,
            ]
            assert [matmul["expected_row_sha256"] for matmul in matmuls] == [
                "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff",
                "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403",
                "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
            ]
            assert [matmul["staged_weight_base_words"] for matmul in matmuls] == [
                0,
                16_777_216,
                20_971_520,
            ]
            for matmul in matmuls:
                weight = matmul["weight_source"]
                assert matmul["input_source"] == "prior_rms_norm_result_bank"
                assert matmul["contract_sha256"] == (
                    "7550dc6a773fd9d5773b46182887613fb777bb8e4f01652321c4d93ca0765aa1"
                )
                assert matmul["executed_association"] == (
                    "ot_a3_mac_lane_single_lane_ascending_k_v1"
                )
                assert (
                    weight["selected_matrix_sha256"]
                    == weight["declared_segment_sha256"]
                )
                assert (
                    "complete selected source segment"
                    in weight["authentication_boundary"]
                )
            head_rms_norms = [
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "vector_head_rms_norm"
            ]
            assert case["expected"]["head_rms_norm_result_words"] == 5_120
            assert case["expected"]["selected_head_rms_checkpoint_bytes"] == 512
            assert [operation["pc"] for operation in head_rms_norms] == [20, 23]
            assert [
                (operation["row_count"], operation["row_width"])
                for operation in head_rms_norms
            ] == [(32, 128), (8, 128)]
            assert [
                operation["expected_payload_sha256"] for operation in head_rms_norms
            ] == [
                "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c",
                "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66",
            ]
            assert [
                operation["mean_square_payload_sha256"] for operation in head_rms_norms
            ] == [
                "e10c17ec2a238ecebbad32e5c85a6822babfec8ac7650eb7bba2a67fc0003cb2",
                "b1d45efa4ea83b59c1638bf041adc2e30dfb98c8b4ea2d156c247213ff05f065",
            ]
            assert [
                operation["inverse_rms_payload_sha256"] for operation in head_rms_norms
            ] == [
                "12a8e58463d481658ffee21140fd06ecc6ff799fcd27b2cab650aa7508f89aa9",
                "b088f0e2a9c0cb618be3df9e9752be637198b2eb8e1a457fa7862a12691f1d71",
            ]
            assert [
                operation["weight_source"]["selected_row_file_offset"]
                for operation in head_rms_norms
            ] == [1_588_618_616, 1_546_675_320]
            assert [
                operation["weight_source"]["selected_row_sha256"]
                for operation in head_rms_norms
            ] == [
                "ad88a3013b2d8ecd138c36460751296c56bed2eff2d5d3a66377db04fd9e0799",
                "aaf5042c20082b5c13daed62ad9627f426cda5edc38eca48bd3f956da4eb05cd",
            ]
            assert all(
                operation["contract_sha256"]
                == "999ef86bc4d4c36dfd57db84d49618af46bed2e6c1f0b1bf031a27b5b8c03fda"
                for operation in head_rms_norms
            )
            assert [
                mapping["base_words"]
                for mapping in case["bank_mapping"]["head_input_objects"]
            ] == ([8_448, 12_544] if case_index == 0 else [33_280, 37_376])
            ropes = [
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "vector_rope"
            ]
            assert [operation["pc"] for operation in ropes] == [26, 29]
            assert [operation["descriptor_id"] for operation in ropes] == (
                [98, 106] if case_index == 0 else [101, 107]
            )
            assert [operation["operator_aux_id_0"] for operation in ropes] == (
                [128, 128] if case_index == 0 else [256, 256]
            )
            assert [
                (operation["row_count"], operation["row_width"]) for operation in ropes
            ] == [(32, 128), (8, 128)]
            assert [operation["expected_payload_sha256"] for operation in ropes] == [
                "f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150",
                "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406",
            ]
            assert [operation["input_source"] for operation in ropes] == [
                "prior_query_head_rms_norm_result_bank",
                "prior_key_head_rms_norm_result_bank",
            ]
            assert [operation["multiplication_count"] for operation in ropes] == [
                8_192,
                2_048,
            ]
            assert [operation["addition_count"] for operation in ropes] == [
                4_096,
                1_024,
            ]
            for rope in ropes:
                assert rope["contract_sha256"] == (
                    "34ad155c76b1ab1ee5efb8463a85753eaebd08e169ee93c07ba364759f1836cf"
                )
                assert rope["coefficient_source"] == (
                    "prior_fp32_generated_row_dma_gather_result_bank"
                )
                assert rope["coefficient_fp32_payload_sha256"] == (
                    "d5c65f780aa8e9d6618ffc6dc5e82df124968be09bc0e407df16070cb7cbae21"
                )
                assert rope["coefficient_bf16_payload_sha256"] == (
                    "836c0e4d9ba8556db28ac7d300914b4cb42d15418e59c6550a693558252049f1"
                )
                assert rope["coefficient_narrow_saturated_element_count"] == 0
                assert rope["multiplication_saturated_element_count"] == 0
                assert rope["addition_saturated_element_count"] == 0
                assert rope["oracle_agreement"] == (
                    "optimized_numpy_equals_independent_scalar_all_elements"
                )
                assert rope["input_view"]["dims"] == rope["output_view"]["dims"]
                assert rope["input_view"]["strides"] == rope["output_view"]["strides"]
                assert rope["coefficient_view"]["dims"] == [
                    1,
                    rope["row_count"],
                    256,
                ]
                assert rope["coefficient_view"]["strides"] == [256, 0, 1]
            assert [
                mapping["object_id"]
                for mapping in case["bank_mapping"]["rope_input_objects"]
            ] == [operation["input_view"]["object_id"] for operation in ropes]
            assert [
                mapping["base_words"]
                for mapping in case["bank_mapping"]["rope_input_objects"]
            ] == ([14_592, 18_688] if case_index == 0 else [39_424, 43_520])
            assert case["bank_mapping"]["rope_coefficient_object"] == {
                "object_id": ropes[0]["coefficient_view"]["object_id"],
                "base_words": 0 if case_index == 0 else 24_832,
            }
        else:
            transfer = next(
                operation
                for operation in case["supported_prefix"]
                if operation["kind"] == "dma_transfer"
            )
            assert case["expected"]["rms_norm_launches"] == 0
            assert case["expected"]["head_rms_norm_launches"] == 0
            assert case["expected"]["rope_launches"] == 0
            assert case["expected"]["rope_result_words"] == 0
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
    assert retained["evidence_class"] == ("public_open_tool_rtl_simulation_composite")
    assert retained["evidence_mode"] == (
        "full_integrated_verilator_plus_dual_simulator_mac_lane_and_rope_composition"
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
        "verilator": campaign.EXPECTED_INTEGRATED_CHECKS,
    }
    assert "simulators_agree" not in retained
    assert "simulator_checks" not in retained
    lane = retained["compositional_mac_lane_qualification"]
    assert lane["artifact"] == "results/rtl/abi3_engine_campaign.json"
    assert lane["artifact_sha256"] == campaign.sha256_file(campaign.ENGINE_CAMPAIGN)
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
    assert lane["qualification_contract"] == ("bf16_bf16_fp32_sequential_rne_v1")
    assert "not the full shipped program" in lane["composition_boundary"]
    rope_qualification = retained["compositional_rope_qualification"]
    assert rope_qualification["artifact"] == (
        "results/tensor_accelerator/qwen3_rtl_rope_campaign.json"
    )
    assert rope_qualification["artifact_sha256"] == campaign.sha256_file(
        campaign.ROPE_CAMPAIGN
    )
    assert rope_qualification["status"] == "pass"
    assert rope_qualification["simulators_counted"] == ["iverilog", "verilator"]
    assert rope_qualification["qualified_positions"] == [0, 7_999]
    assert rope_qualification["qualified_element_count_per_position"] == 5_120
    assert rope_qualification["qualified_multiplication_count_per_position"] == (10_240)
    assert rope_qualification["qualified_addition_count_per_position"] == 5_120
    assert rope_qualification["core_source"] == ("rtl/ot_ta_rope_bf16_sram_engine.sv")
    assert rope_qualification["core_source_sha256"] == campaign.sha256_file(
        ROOT / rope_qualification["core_source"]
    )
    assert rope_qualification["qualification_contract"] == ("qwen3_rope_fp32_bf16_v1")
    assert (
        "inactive side is internal zero" in rope_qualification["composition_boundary"]
    )
    assert any(
        "complete integrated shipped-prefix execution under Icarus" in item
        for item in retained["scope"]["does_not_establish"]
    )
    assert any(
        "output-token correctness" in item and "correctness-qualified TPOT" in item
        for item in retained["scope"]["does_not_establish"]
    )
    assert [site["pc"] for site in retained["fault_sites"]] == [32, 32, 13, 14]
    assert [site["descriptor_id"] for site in retained["fault_sites"]] == [
        114,
        114,
        368,
        546,
    ]
    assert [site["opcode"] for site in retained["fault_sites"]] == [
        "DMA.SCATTER",
        "DMA.SCATTER",
        "LINK.MULTICAST",
        "VECTOR.MHC",
    ]
    assert retained["dma_gather_launch_count"] == 6
    assert retained["embedding_launch_count"] == 4
    assert retained["rms_norm_launch_count"] == 2
    assert retained["head_rms_norm_launch_count"] == 4
    assert retained["rope_launch_count"] == 4
    assert retained["dma_transfer_launch_count"] == 2
    assert retained["matmul_launch_count"] == 6
    assert retained["real_engine_launch_count"] == 28
    assert retained["result_word_count"] == 91_136
    assert retained["resolved_view_count"] == 94
    assert retained["rope_coefficient_gather_result_word_count"] == 1_024
    assert retained["rope_result_word_count"] == 10_240
    assert retained["head_rms_norm_result_word_count"] == 10_240
    assert retained["matmul_result_word_count"] == 12_288
    assert retained["matmul_mac_count"] == 50_331_648
    assert retained["selected_matmul_checkpoint_byte_count"] == 100_663_296
    assert retained["selected_head_rms_checkpoint_byte_count"] == 1_024
    assert retained["selected_checkpoint_byte_count"] == 100_713_472
    assert len(retained["checkpoint_rows"]) == 4
    for row in retained["checkpoint_rows"]:
        assert len(row["deployment_sha256"]) == 64
        assert row["deployment_identity_evidence"]["artifact"]
        assert row["source"]["selected_row_bytes"] == 8_192
        assert (
            row["source"]["selected_row_file_range"]["stop_exclusive"]
            - row["source"]["selected_row_file_range"]["start"]
            == 8_192
        )
    assert len(retained["checkpoint_gains"]) == 2
    for gain in retained["checkpoint_gains"]:
        assert gain["source"]["selected_row_bytes"] == 8_192
        assert gain["numeric_contract_sha256"] == (
            "999ef86bc4d4c36dfd57db84d49618af46bed2e6c1f0b1bf031a27b5b8c03fda"
        )
    assert len(retained["checkpoint_head_gains"]) == 4
    for head_gain in retained["checkpoint_head_gains"]:
        assert head_gain["operator_pc"] in {20, 23}
        assert (head_gain["row_count"], head_gain["row_width"]) in {
            (32, 128),
            (8, 128),
        }
        assert head_gain["source"]["selected_row_bytes"] == 256
        assert head_gain["numeric_contract_sha256"] == (
            "999ef86bc4d4c36dfd57db84d49618af46bed2e6c1f0b1bf031a27b5b8c03fda"
        )
        if head_gain["operator_pc"] == 20:
            assert head_gain["expected_payload_sha256"] == (
                "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c"
            )
            assert head_gain["mean_square_payload_sha256"] == (
                "e10c17ec2a238ecebbad32e5c85a6822babfec8ac7650eb7bba2a67fc0003cb2"
            )
            assert head_gain["inverse_rms_payload_sha256"] == (
                "12a8e58463d481658ffee21140fd06ecc6ff799fcd27b2cab650aa7508f89aa9"
            )
        else:
            assert head_gain["expected_payload_sha256"] == (
                "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66"
            )
            assert head_gain["mean_square_payload_sha256"] == (
                "b1d45efa4ea83b59c1638bf041adc2e30dfb98c8b4ea2d156c247213ff05f065"
            )
            assert head_gain["inverse_rms_payload_sha256"] == (
                "b088f0e2a9c0cb618be3df9e9752be637198b2eb8e1a457fa7862a12691f1d71"
            )
    assert len(retained["rope_operations"]) == 4
    assert [operation["operator_pc"] for operation in retained["rope_operations"]] == [
        26,
        29,
        26,
        29,
    ]
    assert [
        operation["operator_descriptor_id"] for operation in retained["rope_operations"]
    ] == [98, 106, 101, 107]
    assert [
        (operation["row_count"], operation["row_width"])
        for operation in retained["rope_operations"]
    ] == [(32, 128), (8, 128), (32, 128), (8, 128)]
    assert [
        operation["operator_aux_id_0"] for operation in retained["rope_operations"]
    ] == [128, 128, 256, 256]
    assert [
        operation["expected_payload_sha256"]
        for operation in retained["rope_operations"]
    ] == [
        "f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150",
        "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406",
        "f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150",
        "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406",
    ]
    assert all(
        operation["numeric_contract_sha256"]
        == "34ad155c76b1ab1ee5efb8463a85753eaebd08e169ee93c07ba364759f1836cf"
        and operation["coefficient_bf16_payload_sha256"]
        == "836c0e4d9ba8556db28ac7d300914b4cb42d15418e59c6550a693558252049f1"
        and operation["coefficient_narrow_saturated_element_count"] == 0
        and operation["oracle_agreement"]
        == "optimized_numpy_equals_independent_scalar_all_elements"
        for operation in retained["rope_operations"]
    )
    assert len(retained["checkpoint_matrices"]) == 6
    for matrix in retained["checkpoint_matrices"]:
        assert matrix["operator_pc"] in {11, 14, 17}
        assert matrix["numeric_contract_sha256"] == (
            "7550dc6a773fd9d5773b46182887613fb777bb8e4f01652321c4d93ca0765aa1"
        )
        assert matrix["executed_association"] == (
            "ot_a3_mac_lane_single_lane_ascending_k_v1"
        )
        assert matrix["expected_row_sha256"] in {
            "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff",
            "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403",
            "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
        }
        assert matrix["source"]["declared_segment_bytes"] in {
            33_554_432,
            8_388_608,
        }
    staged = retained["staged_matmul_weight"]
    assert staged["path"] == "generated/p3_matmul_weight.bin"
    assert staged["bytes"] == 50_331_648
    assert staged["sha256"] == (
        "2c8696111937aa85197cd2042dfed6cb3c5ef7f03fb80eba1fe3b93d40c1b87e"
    )
    assert [
        (
            matrix["pc"],
            matrix["base_words"],
            matrix["bytes"],
            matrix["sha256"],
            matrix["source_offset"],
        )
        for matrix in staged["matrices"]
    ] == [
        (
            11,
            0,
            33_554_432,
            "fd56b85bf301661c8655ed517928304d25df7d6b3ea3d9be85c021159d61bad8",
            1_588_618_872,
        ),
        (
            14,
            16_777_216,
            8_388_608,
            "3ce9fdf6ee30ef2f24ad3629b506415ca91fe40f790e568a9ea3fea2978feee0",
            1_546_675_576,
        ),
        (
            17,
            20_971_520,
            8_388_608,
            "767a6c48457974bb02dd90aeec270f4d68289527a353c3c28964ab2069a966ee",
            1_622_173_304,
        ),
    ]
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
def test_focused_campaign_replays_verilator_and_binds_mac_lane_and_rope(
    tmp_path: Path,
) -> None:
    summary = campaign.run(tmp_path / "build")
    assert summary["status"] == "pass", summary["cases"]
    assert summary["integrated_replay_passed"]
    assert summary["integrated_simulators"] == ["verilator"]
    assert summary["integrated_simulator_checks"] == {
        "verilator": campaign.EXPECTED_INTEGRATED_CHECKS,
    }
    assert "simulators_agree" not in summary
    assert "simulator_checks" not in summary
    assert summary["compositional_mac_lane_qualification"]["simulators_counted"] == [
        "iverilog_vvp",
        "verilator_cpp_executable",
    ]
    assert summary["compositional_rope_qualification"]["simulators_counted"] == [
        "iverilog",
        "verilator",
    ]
    assert summary["post_fault_write_count"] == 0
    assert [case["name"] for case in summary["cases"]] == ["verilator"]
    for simulator in summary["cases"]:
        assert simulator["status"] == "pass"
        assert simulator["compile_returncode"] == 0, simulator["compile_log"]
        assert simulator["run_returncode"] == 0, simulator["run_log"]
        assert simulator["marker_present"]
        assert simulator["observed_cases"] == summary["expected_cases"]
