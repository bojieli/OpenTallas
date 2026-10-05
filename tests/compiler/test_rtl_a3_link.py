"""Focused evidence checks for the ABI 3.0 COMMUNICATION RTL boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from runtime.abi3.crc import record_crc
from runtime.abi3.descriptors import DESCRIPTOR_HEADER, Descriptor
from tools import build_a3_link_vectors as generator
from tools import rtl_a3_link_campaign as campaign


ROOT = Path(__file__).resolve().parents[2]
VECTOR_ROOT = ROOT / "testdata/rtl/a3_link"
CAMPAIGN_JSON = ROOT / "results/rtl/a3_link_campaign.json"


def _words(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line]


def _word_record(words: list[int]) -> bytes:
    return b"".join(word.to_bytes(4, "little") for word in words)


def test_certificates_lock_current_qwen_and_deepseek_bundles() -> None:
    sources = generator.load_certified_sources()
    assert {
        name: source["deployment"].deployment_digest.hex()
        for name, source in sources.items()
    } == {
        "deepseek_rom":
            "fa907792d8eb73ec1237525468581e47945a9077e5a247f4f88c43fbb5042394",
        "deepseek_hbm":
            "2943197b3055d6198899d402efd927810cd307c09287f9d250b1b1afb2695275",
        "qwen_rom":
            "274e4bc4664817be07ed97479c6bd77555e494d294a0b6f692ff4ac6195bbaed",
        "qwen_hbm":
            "679a41be63817459bacc61a7cdbdfb5793f034e82d5c51f66d0e2f9345bd25b3",
    }
    assert {name: len(source["communication_ids"])
            for name, source in sources.items()} == {
        "deepseek_rom": 18,
        "deepseek_hbm": 37,
        "qwen_rom": 0,
        "qwen_hbm": 0,
    }


def test_exact_deepseek_records_are_not_reconstructed() -> None:
    sources = generator.load_certified_sources()
    configs = generator.default_configurations(sources)
    cfg = next(c for c in configs if c["name"] == "mesh8x4_vec32_credit32_hop1")
    cases = {case["label"]: case for case in cfg["cases"]}

    for label in (
        "certified_hbm_sum_exact",
        "certified_hbm_sum_exact_decode_repeat",
        "certified_hbm_barrier_exact",
        "certified_hbm_all_gather_refused",
        "certified_hbm_concat_refused",
        "certified_rom_p2p_refused",
    ):
        case = cases[label]
        source = sources[case["source"]]
        raw = source["records"][case["source_descriptor_id"]]
        assert case["record"] == raw
        assert case["exact_source_record"]
        assert case["source_record_sha256"] == hashlib.sha256(raw).hexdigest()

    exact_sum = cases["certified_hbm_sum_exact"]
    assert exact_sum["record_valid"]
    assert exact_sum["numeric_record_valid"]
    assert not exact_sum["numeric_semantics_supported"]
    assert not exact_sum["command_admitted"]
    assert exact_sum["refusal_reason"] == generator.REFUSE["data_extent"]
    assert exact_sum["numeric_descriptor_id"] == 1040
    assert exact_sum["numeric_record"] == sources["deepseek_hbm"]["records"][1040]
    exact_barrier = cases["certified_hbm_barrier_exact"]
    assert exact_barrier["record_valid"]
    assert not exact_barrier["command_admitted"]
    assert exact_barrier["refusal_reason"] == generator.REFUSE[
        "control_metadata"
    ]
    for label in (
        "certified_hbm_all_gather_refused",
        "certified_hbm_concat_refused",
        "certified_rom_p2p_refused",
        "reduce_scatter_refused",
    ):
        assert cases[label]["record_valid"]
        assert not cases[label]["command_admitted"]

    built = generator.build_config(cfg)
    built_cases = {case["label"]: case for case in built["cases"]}
    exact_sum = built_cases["certified_hbm_sum_exact"]
    assert exact_sum["functional_model_messages"] == 1_984
    assert exact_sum["functional_model_payload_bytes"] == 1_560_281_088
    barrier = built_cases["certified_hbm_barrier_exact"]
    assert barrier["functional_model_messages"] == 160
    assert barrier["functional_model_payload_bytes"] == 0
    assert barrier["expected_engine_flits"] == 0
    assert barrier["expected_wire_crossings"] == 0
    assert barrier["expected_serial_traversals"] == 0
    assert barrier["functional_oracle"] == "certified_topology_barrier_messages"
    synthetic_barrier = built_cases["synthetic_barrier"]
    assert synthetic_barrier["command_admitted"]
    assert synthetic_barrier["execution_class"] == "synthetic_bounded_probe"
    assert not synthetic_barrier["exact_source_record"]
    assert synthetic_barrier["expected_engine_flits"] == 160
    assert synthetic_barrier["functional_model_messages"] == 160
    assert synthetic_barrier["functional_oracle"] == (
        "standalone_dissemination_barrier_messages"
    )
    synthetic_record = synthetic_barrier["record"]
    for offset in (16, 20, 80, 84, 128):
        assert int.from_bytes(synthetic_record[offset:offset + 4], "little") \
            == generator.NO_ID
    assert int.from_bytes(synthetic_record[140:144], "little") == 0


def test_all_frozen_fields_use_the_canonical_python_offsets() -> None:
    source = generator.load_certified_sources()["deepseek_hbm"]
    descriptor_id = generator.select_communication(
        source, subopcode=6, collective_op=1, zero_extent=False
    )
    raw = source["records"][descriptor_id]
    descriptor = Descriptor.decode(raw, descriptor_id)
    header = DESCRIPTOR_HEADER.decode(raw[:64])
    words = generator.decoded_words(raw)

    header_map = {
        generator.CW_MAGIC: int.from_bytes(raw[:4], "little"),
        generator.CW_DESCRIPTOR_TYPE: header["descriptor_type"],
        generator.CW_TYPE_MAJOR: header["type_major"],
        generator.CW_TYPE_MINOR: header["type_minor"],
        generator.CW_TOTAL_BYTES: header["total_bytes"],
        generator.CW_HEADER_FLAGS: header["flags"],
        generator.CW_PRIMARY_OBJECT: header["primary_object_id"],
        generator.CW_SECONDARY_OBJECT: header["secondary_object_id"],
        generator.CW_NUMERIC_PROFILE: header["numeric_profile_id"],
        generator.CW_SCHEDULE: header["schedule_id"],
        generator.CW_PERMISSIONS: header["permissions"],
        generator.CW_OWNER_SCOPE: header["owner_scope_id"],
        generator.CW_PAYLOAD_OFFSET: header["payload_offset"],
        generator.CW_PAYLOAD_BYTES: header["payload_bytes"],
        generator.CW_SUPPLIED_CRC: header["record_crc"],
        generator.CW_CALCULATED_CRC: record_crc(raw, 48),
    }
    assert {index: words[index] for index in header_map} == header_map

    payload_fields = (
        ("collective_op", generator.CW_COLLECTIVE_OP),
        ("ordering", generator.CW_ORDERING),
        ("integrity_mode", generator.CW_INTEGRITY_MODE),
        ("virtual_channel", generator.CW_VIRTUAL_CHANNEL),
        ("source_node", generator.CW_SOURCE_NODE),
        ("destination_node", generator.CW_DESTINATION_NODE),
        ("group_id", generator.CW_GROUP_ID),
        ("route_class", generator.CW_ROUTE_CLASS),
        ("local_object_id", generator.CW_LOCAL_OBJECT),
        ("remote_object_id", generator.CW_REMOTE_OBJECT),
        ("credit_bound", generator.CW_CREDIT_BOUND),
        ("retry_bound", generator.CW_RETRY_BOUND),
        ("timeout_class", generator.CW_TIMEOUT_CLASS),
        ("completion_event_id", generator.CW_COMPLETION_EVENT),
        ("reduction_numeric_id", generator.CW_REDUCTION_NUMERIC),
        ("counter_class_id", generator.CW_COUNTER_CLASS),
        ("participant_count", generator.CW_PARTICIPANT_COUNT),
        ("chunk_bytes", generator.CW_CHUNK_BYTES),
        ("participant_scope", generator.CW_PARTICIPANT_SCOPE),
    )
    for field, index in payload_fields:
        assert words[index] == descriptor.payload[field]
    for field, lo, hi in (
        ("local_offset", generator.CW_LOCAL_OFFSET_LO,
         generator.CW_LOCAL_OFFSET_HI),
        ("remote_offset", generator.CW_REMOTE_OFFSET_LO,
         generator.CW_REMOTE_OFFSET_HI),
        ("byte_extent", generator.CW_BYTE_EXTENT_LO,
         generator.CW_BYTE_EXTENT_HI),
    ):
        assert words[lo] | words[hi] << 32 == descriptor.payload[field]


def test_vector_image_preserves_exact_positive_bytes() -> None:
    index = json.loads((VECTOR_ROOT / "index.json").read_text())
    cfg = next(c for c in index["configurations"]
               if c["name"] == "mesh8x4_vec32_credit32_hop1")
    words = _words(VECTOR_ROOT / cfg["name"] / "communication.hex")
    sources = generator.load_certified_sources()
    for case_index, case in enumerate(cfg["cases"]):
        if not case["exact_source_record"]:
            continue
        begin = case_index * generator.DESCRIPTOR_WORDS
        encoded = _word_record(words[begin:begin + generator.DESCRIPTOR_WORDS])
        raw = sources[case["source"]]["records"][case["source_descriptor_id"]]
        assert encoded == raw, case["label"]

    numeric_words = _words(VECTOR_ROOT / cfg["name"] / "numeric.hex")
    for case_index, case in enumerate(cfg["cases"]):
        if not case["numeric_exact_source_record"]:
            continue
        begin = case_index * generator.NUMERIC_WORDS
        encoded = _word_record(
            numeric_words[begin:begin + generator.NUMERIC_WORDS]
        )
        raw = sources[case["numeric_source"]]["records"][
            case["numeric_source_descriptor_id"]
        ]
        assert encoded == raw, case["label"]


def test_only_synthetic_capacity_exact_data_commands_are_admitted() -> None:
    sources = generator.load_certified_sources()
    for cfg in generator.default_configurations(sources):
        built = generator.build_config(cfg)
        for case in built["cases"]:
            if not case["command_admitted"] or case["engine_op"] == generator.OP_BARRIER:
                continue
            record = case["record"]
            assert case["execution_class"] == "synthetic_bounded_probe"
            assert not case["exact_source_record"]
            assert int.from_bytes(record[104:112], "little") == cfg["vec_len"] * 4
            assert int.from_bytes(record[140:144], "little") == 4
            assert record[144] == 0  # NODE
            assert int.from_bytes(record[72:76], "little") == generator.NO_ID
            assert int.from_bytes(record[88:104], "little") == 0
            if case["engine_op"] in (1, 2, 3):
                assert case["numeric_record_valid"]
                assert case["numeric_semantics_supported"]
                assert case["numeric_record"][64:68] == bytes([18, 18, 18, 18])
                assert not any(case["numeric_record"][96:128])


def test_membership_extent_chunk_and_numeric_adversaries_fail_closed() -> None:
    sources = generator.load_certified_sources()
    cfg = generator.default_configurations(sources)[0]
    cases = {case["label"]: case for case in cfg["cases"]}
    expected = {
        "synthetic_tile_scope_refused": "scope_support",
        "synthetic_selected_group_refused": "group_support",
        "synthetic_broadcast_root_out_of_range_refused": "source_node",
        "synthetic_extent_mismatch_refused": "data_extent",
        "synthetic_chunk_mismatch_refused": "chunk_bytes",
        "synthetic_data_offset_refused": "data_offset",
        "synthetic_control_metadata_refused": "control_metadata",
        "synthetic_algorithm_unregistered_refused": "algorithm",
        "synthetic_numeric_stale_crc_refused": "numeric_record",
        "synthetic_numeric_sideband_order_mismatch_refused": "numeric_binding",
    }
    for label, reason in expected.items():
        case = cases[label]
        assert case["record_valid"]
        assert not case["command_admitted"]
        assert case["refusal_reason"] == generator.REFUSE[reason]
    stale = cases["synthetic_numeric_stale_crc_refused"]
    assert not stale["numeric_record_valid"]
    assert record_crc(stale["numeric_record"], 48) != int.from_bytes(
        stale["numeric_record"][48:52], "little"
    )

    hbm_cfg = generator.default_configurations(sources)[-1]
    hbm_cases = {case["label"]: case for case in hbm_cfg["cases"]}
def test_arithmetic_faults_and_signed_zero_have_directed_expectations() -> None:
    sources = generator.load_certified_sources()
    built = generator.build_config(generator.default_configurations(sources)[0])
    cases = {case["label"]: case for case in built["cases"]}
    for label in (
        "synthetic_sum_overflow_trap",
        "synthetic_max_nonfinite_trap",
        "synthetic_min_nonfinite_trap",
    ):
        case = cases[label]
        assert case["command_admitted"]
        assert case["expected_trap_class"] == 6
        assert case["expected_steps_per_node"] == 0
        assert case["expected_engine_flits"] == built["nodes"] * built["vec_len"]
        assert case["expected_serial_traversals"] == 0
    for label in ("synthetic_max_signed_zero", "synthetic_min_signed_zero"):
        result = generator.codes(cases[label]["expected"])
        assert set(int(code) for code in result[:, 0]) == {0}


def test_negative_mutations_are_fail_closed_and_crc_disciplined() -> None:
    sources = generator.load_certified_sources()
    cfg = next(c for c in generator.default_configurations(sources)
               if c["name"] == "mesh8x4_vec32_credit32_hop1")
    cases = {case["label"]: case for case in cfg["cases"]}
    structural = {
        "bad_magic": "magic",
        "bad_type": "type",
        "bad_version": "version",
        "bad_total_bytes": "total_bytes",
        "bad_payload_geometry": "payload_geometry",
        "header_reserved_nonzero": "header_reserved",
        "payload_reserved_nonzero": "payload_reserved",
        "stale_record_crc": "record_crc",
        "permissions_reserved": "permissions",
        "collective_op_unregistered": "collective_op",
        "ordering_unregistered": "ordering",
        "integrity_mode_unregistered": "integrity_mode",
        "participant_scope_unregistered": "participant_scope",
    }
    for label, reason in structural.items():
        case = cases[label]
        assert not case["record_valid"]
        assert not case["command_admitted"]
        assert case["refusal_reason"] == generator.REFUSE[reason]
    assert record_crc(cases["stale_record_crc"]["record"], 48) != int.from_bytes(
        cases["stale_record_crc"]["record"][48:52], "little"
    )
    for label, case in cases.items():
        if case["mutations"] and label != "stale_record_crc":
            assert record_crc(case["record"], 48) == int.from_bytes(
                case["record"][48:52], "little"
            )


def test_campaign_artifact_locks_every_input_and_states_limits() -> None:
    artifact = json.loads(CAMPAIGN_JSON.read_text())
    assert artifact["status"] == "pass"
    assert artifact["claim_boundary"][
        "implements_the_full_abi3_communication_descriptor_decode"
    ]
    assert artifact["canonical_complete"]
    assert artifact["claim_boundary"][
        "loads_or_decodes_referenced_numeric_descriptors"
    ]
    assert not artifact["claim_boundary"][
        "executes_exact_hbm_sum_descriptor_1044"
    ]
    assert artifact["claim_boundary"][
        "executes_only_synthetic_bounded_data_probes"
    ]
    assert not artifact["claim_boundary"]["executes_exact_hbm_barrier"]
    assert artifact["claim_boundary"][
        "barrier_timing_uses_only_synthetic_neutral_probe"
    ]
    assert artifact["claim_boundary"][
        "command_admitted_means_full_abi_execution"
    ]
    assert not artifact["claim_boundary"][
        "command_admitted_means_standalone_link_data_plane"
    ]
    assert not artifact["claim_boundary"][
        "executes_concat_all_gather_or_reduce_scatter"
    ]
    for relative, digest in artifact["source_sha256"].items():
        assert campaign.sha256(ROOT / relative) == digest, relative


def _case_line(index: int) -> str:
    return (
        f"CASE {index} op=1 alg=0 order=1 cycles=1 traversals=1 "
        "engine_flits=1 crossings=1 retries=0 crc_errors=0 "
        "credit_stalls=0 replayed=0 trap=0 trap_class=0 record_valid=1 "
        "numeric_valid=1 numeric_supported=1 admitted=1 reason=0"
    )


def test_campaign_parser_rejects_missing_duplicate_and_out_of_order_cases() -> None:
    with pytest.raises(ValueError, match="parsed 1 CASE lines"):
        campaign.parse_cases(_case_line(0), 2)
    with pytest.raises(ValueError, match="CASE indices"):
        campaign.parse_cases("\n".join((_case_line(0), _case_line(0))), 2)
    with pytest.raises(ValueError, match="CASE indices"):
        campaign.parse_cases("\n".join((_case_line(1), _case_line(0))), 2)


def test_campaign_rejects_nonzero_status_even_with_exact_pass_marker() -> None:
    marker = "PASS: exact marker"
    result = {
        "run_returncode": 9,
        "run_log": f"{_case_line(0)}\n{marker}",
    }
    parsed = campaign.evaluate_simulator_result(result, marker, 1)
    assert len(parsed) == 1
    assert result["marker_present"]
    assert result["status"] == "fail"


def test_campaign_marker_must_be_a_complete_line_and_temp_is_scrubbed() -> None:
    marker = "PASS: exact marker"
    result = {
        "run_returncode": 0,
        "run_log": f"{_case_line(0)}\nprefix {marker} suffix",
    }
    campaign.evaluate_simulator_result(result, marker, 1)
    assert not result["marker_present"]
    assert result["status"] == "fail"
    assert campaign.scrub("/tmp/work/run", Path("/tmp/work")) == "<TMP>/run"


def test_canonical_only_and_empty_selection_are_refused() -> None:
    canonical = subprocess.run(
        [sys.executable, str(ROOT / "tools/rtl_a3_link_campaign.py"),
         "--only", "mesh2x2_vec4_hop1"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert canonical.returncode != 0
    assert "--only cannot write the canonical" in canonical.stderr

    empty = subprocess.run(
        [sys.executable, str(ROOT / "tools/rtl_a3_link_campaign.py"),
         "--only", "does-not-exist", "--output", "/tmp/a3-noncanonical.json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert empty.returncode != 0
    assert "configuration selection is empty" in empty.stderr
