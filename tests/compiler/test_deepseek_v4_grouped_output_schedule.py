from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import os
from pathlib import Path
from typing import Any

import pytest

from compiler.checking.deepseek_v4_grouped_output import (
    CERTIFICATE_STATUS,
    FROZEN_MAPPING_HASHES,
    FROZEN_PROGRAM_CONTRACT_IDS,
    FROZEN_PROGRAM_SHA256,
    FROZEN_SOURCE_CONTRACT_ID,
    LOGICAL_CERTIFICATE_SCHEMA,
    OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA,
    DeepSeekV4GroupedOutputCheckError,
    verify_deepseek_v4_grouped_output_logical_schedule,
    verify_deepseek_v4_grouped_output_logical_schedule_certificate,
    verify_deepseek_v4_grouped_output_official_evidence,
)
from compiler.ir.model import canonical_json_bytes
from compiler.microcode.deepseek_v4_grouped_output import (
    TENSOR_PARALLEL_WORLD_SIZES,
    assemble,
)
from compiler.scheduling.deepseek_v4_grouped_output import (
    LOGICAL_SCHEDULE_SCHEMA,
    LOGICAL_SCHEDULE_STATUS,
    DeepSeekV4GroupedOutputScheduleError,
    build_deepseek_v4_grouped_output_logical_schedule,
)


SCHEDULE_IDS = {
    (1, 0): "d339e5775a5db73f152b492bad41ae6359592993fadd105cc5ce194e932b2adf",
    (2, 0): "d3205498478d790fc9118d42113c8b02c628b52c6fd19a630fe2d0b6a428e591",
    (2, 1): "1ee1dcdb76e3dc5334c1904bd1693373d24f1493b90cbd75528bb7e739418383",
    (4, 0): "d31f979672a1debb673147a788535ce7745d783208750d5249f0305612f9097b",
    (4, 1): "ff1b4625021c215c15125d624aff939af36933344b3706bd32f61e341a68dde1",
    (4, 2): "de1576e020f4b5d913f742cdac7c9fb559c2ed378d86c5c94416df48c0c7d310",
    (4, 3): "6ae53f0048ec7e16037114d29cff9df4f9e34bf115c177c04f024fa763fffad9",
    (8, 0): "b1b953367e5576e6bdac2a2a3e643aa1a1c44ddcb85697113a52b8973c512e8a",
    (8, 1): "30f6c58c052f8450a7faa65c55909ce75a69d8b49be52904d4b35007096b4c8f",
    (8, 2): "7f96f3bf2b07960d550b4de6d4fbfbed056197926d17287fccb7c4c1be89128d",
    (8, 3): "54049802d1f931679d22e040e5fd790da116321761be32c61ae471ee4ed3f7bd",
    (8, 4): "418f8374183cfddac0c773348ffb5a58322bb6ff61f8da53bac9d4c0838d77a7",
    (8, 5): "924a663fb31ec049ede9333df335a1fb9a0001d20fca60e983ae24360791704e",
    (8, 6): "9fd8d98a6a06630826c2b86838319c8c3283da549bb6d62449635efb64a8c151",
    (8, 7): "d077d4bc7f1df7880877de0a269bd48e2261a84a44eb7b4c8622ffe629e75c33",
}
CERTIFICATE_IDS = {
    (1, 0): "52993126bae893ceafe13e63bab7eef65b159b30831583bd53463544c4d0624a",
    (2, 0): "19f536934865b6817603bcb0b69f9789f2ad8d9c4bbb5b6eac5594f806a13e0d",
    (2, 1): "499b95dbd112adccbdf3110b3d4c86438d88f317887033dffaf008ef7b0a71b2",
    (4, 0): "b4ef23150a6fc25fd031593f6652defa14c95b652aff16e9e2fe41f117566741",
    (4, 1): "3db318c72b093f18c9c66f56d52cfa86638f40dcfe158abbd3db393e5f8a3a04",
    (4, 2): "aa50d8c605e2b427e3d8471991e86e5ac164503e5c17ac09b82e36aa46ddf02a",
    (4, 3): "ee5fab204198c1a8808173a2799169c7740a652b18782bd6924eae494ccfe352",
    (8, 0): "08b80b7a0de2dc2691927ed225ee2e043e3cdb81385d19a3c2030f4bd0452ad6",
    (8, 1): "727712cdbffc0df70de6586144fa71c599316d6072ae9cb256233b2731fdfa8f",
    (8, 2): "37e653c6754dd25707b10bbb787ae1ec077ff2b59cf2a097af4f2a2e599f8a6c",
    (8, 3): "fddf2eaeb5d837620150c5820540973d2b3375ede8d46169263b047c58f8fdce",
    (8, 4): "51677d12a3565ec87fee7e4848b1e5c3fae836ee58f340fd7a54312cccddecfc",
    (8, 5): "163a44132cfc6a8177d5f77b1eb88980570cf3522bfeff78079920c5674417db",
    (8, 6): "b77208e27066500a4ad587f4b2aaf2ac3e2fc9e96c72d5d69a7882e7ab06ed86",
    (8, 7): "323b50d3bdedb87ec6c12f63920c48dcb07a6c39cdc83d01d0a63f32b8e9238f",
}


def _keys() -> tuple[tuple[int, int], ...]:
    return tuple(
        (world_size, rank)
        for world_size in TENSOR_PARALLEL_WORLD_SIZES
        for rank in range(world_size)
    )


def _rehash_schedule(schedule: dict[str, Any]) -> None:
    body = {key: value for key, value in schedule.items() if key != "schedule_id"}
    schedule["schedule_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def _rehash_certificate(certificate: dict[str, Any]) -> None:
    body = {key: value for key, value in certificate.items() if key != "certificate_id"}
    certificate["certificate_id"] = hashlib.sha256(
        canonical_json_bytes(body)
    ).hexdigest()


@pytest.mark.parametrize(("world_size", "rank"), _keys())
def test_all_fifteen_schedules_are_deterministic_and_independently_certified(
    world_size: int,
    rank: int,
) -> None:
    first = build_deepseek_v4_grouped_output_logical_schedule(world_size, rank)
    second = build_deepseek_v4_grouped_output_logical_schedule(world_size, rank)
    assert canonical_json_bytes(first) == canonical_json_bytes(second)
    assert first["schema"] == LOGICAL_SCHEDULE_SCHEMA
    assert first["status"] == LOGICAL_SCHEDULE_STATUS
    assert first["schedule_id"] == SCHEDULE_IDS[(world_size, rank)]
    assert (
        first["identity"]["program_sha256"] == FROZEN_PROGRAM_SHA256[(world_size, rank)]
    )
    assert (
        first["identity"]["program_contract_id"]
        == (FROZEN_PROGRAM_CONTRACT_IDS[(world_size, rank)])
    )
    assert first["identity"]["source_contract_id"] == FROZEN_SOURCE_CONTRACT_ID
    certificate = verify_deepseek_v4_grouped_output_logical_schedule(first)
    assert certificate["schema"] == LOGICAL_CERTIFICATE_SCHEMA
    assert certificate["status"] == CERTIFICATE_STATUS
    assert certificate["certificate_id"] == CERTIFICATE_IDS[(world_size, rank)]
    verify_deepseek_v4_grouped_output_logical_schedule_certificate(
        certificate,
        first,
    )


@pytest.mark.parametrize(("world_size", "rank"), _keys())
def test_schedule_topology_resource_alias_and_causality_are_explicit(
    world_size: int,
    rank: int,
) -> None:
    schedule = build_deepseek_v4_grouped_output_logical_schedule(world_size, rank)
    local_groups = 8 // world_size
    assert schedule["topology"] == {
        "global_group_range": [rank * local_groups, (rank + 1) * local_groups],
        "global_row_range": [
            rank * local_groups * 1_024,
            (rank + 1) * local_groups * 1_024,
        ],
        "local_group_count": local_groups,
        "rank": rank,
        "world_size": world_size,
    }
    assert (
        schedule["resources"][0]["content_sha256"]
        == FROZEN_MAPPING_HASHES[(world_size, rank)]
    )
    assert schedule["resources"][0]["size_bytes"] == 67_108_864 // world_size
    assert (
        len(schedule["resources"][0]["segments"])
        == {
            1: 4,
            2: 2,
            4: 1,
            8: 1,
        }[world_size]
    )
    assert schedule["registers"][2]["alias_of_register_name"] == "GROUPED_OUTPUT"
    assert schedule["registers"][1]["producer_slot"] == 0
    assert schedule["registers"][2]["producer_slot"] == 0
    assert schedule["slots"][0]["external_input_register_ids"] == [0]
    assert schedule["slots"][0]["destination_register_ids"] == [1, 2]
    assert schedule["slots"][1]["dependency_slots"] == [0]
    assert schedule["slots"][1]["terminal"] is True


def test_schedule_claim_boundary_excludes_execution_and_physical_claims() -> None:
    schedule = build_deepseek_v4_grouped_output_logical_schedule(4, 0)
    required = set(schedule["required_nonclaims"])
    assert {
        "bandwidth",
        "checkpoint_execution",
        "cycle_latency",
        "end_to_end_model_execution",
        "nvidia_comparison",
        "numeric_correctness",
        "output_b_projection",
        "physical_schedule",
        "ppa",
        "tensor_parallel_collective",
    } <= required
    boundary = schedule["claim_boundary"].lower()
    assert "logical" in boundary
    assert "not execution" in boundary
    assert "not" in boundary and "ppa" in boundary


def test_schedule_checker_rejects_stale_hash_and_extra_fields() -> None:
    schedule = build_deepseek_v4_grouped_output_logical_schedule(4, 0)
    stale = deepcopy(schedule)
    stale["summary"]["instruction_count"] = 3
    with pytest.raises(DeepSeekV4GroupedOutputCheckError):
        verify_deepseek_v4_grouped_output_logical_schedule(stale)

    extra = deepcopy(schedule)
    extra["execution_cycles"] = 1
    _rehash_schedule(extra)
    with pytest.raises(DeepSeekV4GroupedOutputCheckError):
        verify_deepseek_v4_grouped_output_logical_schedule(extra)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("schema",), "opentallas.other.v1"),
        (("status",), "pass"),
        (("claim_boundary",), "execution established"),
        (("ordering_policy", "slot_rule"), "free reorder"),
        (("required_nonclaims",), []),
        (("identity", "program_sha256"), "0" * 64),
        (("identity", "program_contract_id"), "1" * 64),
        (("identity", "source_contract_id"), "2" * 64),
        (("identity", "resource_table_sha256"), "3" * 64),
        (("resources", 0, "content_sha256"), "4" * 64),
        (("resources", 0, "size_bytes"), True),
        (("resources", 0, "segments", 0, "byte_offset"), 1),
        (("registers", 0, "producer_kind"), "slot"),
        (("registers", 1, "producer_slot"), 1),
        (("registers", 2, "alias_of_register_id"), None),
        (("registers", 2, "token_major_shape_suffix"), [2_047]),
        (("slots", 0, "opcode"), "COMPLETE"),
        (("slots", 0, "external_input_register_ids"), []),
        (("slots", 0, "destination_register_ids"), [1]),
        (("slots", 0, "immediates", 0), 8),
        (("slots", 1, "dependency_slots"), []),
        (("slots", 1, "terminal"), False),
        (("summary", "instruction_count"), True),
        (("summary", "canonical_resource_bytes"), 1),
        (("topology", "rank"), 1),
        (("topology", "local_group_count"), 1),
        (("topology", "global_row_range"), [0, 1]),
    ],
)
def test_self_consistent_schedule_mutations_fail_independent_check(
    path: tuple[str | int, ...],
    replacement: object,
) -> None:
    schedule = build_deepseek_v4_grouped_output_logical_schedule(4, 0)
    cursor: Any = schedule
    for component in path[:-1]:
        cursor = cursor[component]
    cursor[path[-1]] = replacement
    _rehash_schedule(schedule)
    with pytest.raises(DeepSeekV4GroupedOutputCheckError):
        verify_deepseek_v4_grouped_output_logical_schedule(schedule)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("schema",), "opentallas.other.v1"),
        (("status",), "fail"),
        (("claim_boundary",), "execution established"),
        (("checks", "wire_program_decode"), False),
        (("counts", "instruction_count"), 3),
        (("program_sha256",), "0" * 64),
        (("program_contract_id",), "1" * 64),
        (("source_contract_id",), "2" * 64),
        (("schedule_id",), "3" * 64),
        (("required_nonclaims",), []),
        (("topology", "rank"), 1),
    ],
)
def test_self_consistent_certificate_mutations_fail_fresh_verification(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    schedule = build_deepseek_v4_grouped_output_logical_schedule(4, 0)
    certificate = verify_deepseek_v4_grouped_output_logical_schedule(schedule)
    cursor: Any = certificate
    for component in path[:-1]:
        cursor = cursor[component]
    cursor[path[-1]] = replacement
    _rehash_certificate(certificate)
    with pytest.raises(DeepSeekV4GroupedOutputCheckError):
        verify_deepseek_v4_grouped_output_logical_schedule_certificate(
            certificate,
            schedule,
        )


def test_builder_rejects_wrong_topology_or_mutated_microcode() -> None:
    exact = assemble(4, 0)
    mutated = (replace(exact[0], immediate3=1_023), exact[1])
    with pytest.raises(DeepSeekV4GroupedOutputScheduleError):
        build_deepseek_v4_grouped_output_logical_schedule(4, 0, mutated)
    with pytest.raises(DeepSeekV4GroupedOutputScheduleError):
        build_deepseek_v4_grouped_output_logical_schedule(4, 0, exact[:1])
    with pytest.raises(DeepSeekV4GroupedOutputScheduleError):
        build_deepseek_v4_grouped_output_logical_schedule(4, 1, exact)


def test_checker_is_independent_of_schedule_builder_and_runtime() -> None:
    checker_source = Path("compiler/checking/deepseek_v4_grouped_output.py").read_text(
        encoding="utf-8"
    )
    scheduler_source = Path(
        "compiler/scheduling/deepseek_v4_grouped_output.py"
    ).read_text(encoding="utf-8")
    assert "compiler.scheduling" not in checker_source
    assert "runtime." not in checker_source
    assert "runtime." not in scheduler_source
    assert "expected_output" not in checker_source
    assert "expected_output" not in scheduler_source


def _official_paths() -> tuple[Path, Path, Path] | None:
    evidence = Path(
        os.environ.get(
            "OPENTALLAS_DEEPSEEK_V4_EVIDENCE_ROOT",
            "/home/ubuntu/.cache/opentallas/deepseek-v4-flash-0731",
        )
    )
    snapshot = Path(
        os.environ.get(
            "OPENTALLAS_DEEPSEEK_V4_SNAPSHOT",
            "/home/ubuntu/.cache/huggingface/hub/"
            "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
            "7872f01b1d1fe23eabc4c98b48bffcef5a386062",
        )
    )
    lock = evidence / "checkpoint.lock.json"
    application = evidence / "canonical-mp4"
    if not (
        snapshot.is_dir()
        and lock.is_file()
        and (application / "canonical_application.json").is_file()
        and (application / "canonical_verification.json").is_file()
    ):
        return None
    return snapshot, lock, application


def test_real_official_source_application_and_all_payload_mappings_when_available() -> (
    None
):
    paths = _official_paths()
    if paths is None:
        pytest.skip("pinned official grouped-output evidence is unavailable")
    certificate = verify_deepseek_v4_grouped_output_official_evidence(*paths)
    assert certificate["schema"] == OFFICIAL_EVIDENCE_CERTIFICATE_SCHEMA
    assert certificate["status"] == CERTIFICATE_STATUS
    assert certificate["certificate_id"] == (
        "57d86552d860aadc779bcfc69a2bffe4fbfdb1908159054661646e1192e02838"
    )
    assert certificate["mapping_payload_sha256"] == {
        f"ws{world_size}-rank{rank}": FROZEN_MAPPING_HASHES[(world_size, rank)]
        for world_size, rank in _keys()
    }
    assert all(certificate["checks"].values())


def test_official_evidence_check_fails_closed_on_missing_lock(tmp_path: Path) -> None:
    with pytest.raises(DeepSeekV4GroupedOutputCheckError):
        verify_deepseek_v4_grouped_output_official_evidence(
            tmp_path,
            tmp_path / "missing.lock.json",
            tmp_path,
        )
