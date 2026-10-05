#!/usr/bin/env python3
"""Build exact descriptor-bound DeepSeek HC_PRE tile-scheduler vectors.

The vectors are derived from the retained four-deployment RTL images, then the
selected HBM descriptor records and instruction are byte-compared with the
already authenticated T=512 functional qualification.  Only semantic schedule
coordinates are generated: no HC_PRE result is precomputed for, or injected
into, RTL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.descriptors import DESCRIPTOR_HEADER, Descriptor  # noqa: E402
from runtime.abi3.records import Instruction  # noqa: E402


DEPLOYMENT_VECTOR_ROOT = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_MANIFEST = DEPLOYMENT_VECTOR_ROOT / "abi3_deployment_rtl_vectors.json"
DESCRIPTOR_IMAGE = DEPLOYMENT_VECTOR_ROOT / "a3_descriptor.hex"
PROGRAM_IMAGE = DEPLOYMENT_VECTOR_ROOT / "a3_program.hex"
FUNCTIONAL_RESULT = (
    ROOT / "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json"
)
FUNCTIONAL_VECTOR = (
    ROOT / "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json"
)
OUTPUT_ROOT = ROOT / "testdata/rtl/a3_mhc_pre_tiles"

SCHEMA = "opentallas.rtl.a3_mhc_pre_tile_vectors.v1"
CONFIG_WORDS = 128
CASE_WORDS = 144
DESCRIPTOR_PREFIX_BYTES = 192

PROFILE_ROM = 0
PROFILE_HBM = 1
ERR_NONE = 0
ERR_INSTRUCTION = 16
ERR_OPERATOR = 17
ERR_NUMERIC = 18
ERR_VIEW = 19
ERR_SCHEDULE = 20

TARGETS = (
    {
        "key": "deepseek-v4-flash-rom-wafer",
        "profile": PROFILE_ROM,
        "pc": 15,
        "active_tokens": 1,
        "functional": False,
    },
    {
        "key": "deepseek-v4-flash-hbm-cluster",
        "profile": PROFILE_HBM,
        "pc": 14,
        "active_tokens": 512,
        "functional": True,
    },
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def read_hex(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line.strip()]


def descriptor_record(image: list[int], base: int, descriptor_id: int) -> bytes:
    prefix = image[base + descriptor_id].to_bytes(DESCRIPTOR_PREFIX_BYTES, "little")
    header = DESCRIPTOR_HEADER.decode(prefix[:64])
    total = int(header["total_bytes"])
    if total > DESCRIPTOR_PREFIX_BYTES:
        raise RuntimeError(
            f"descriptor {descriptor_id} is {total} bytes, beyond the retained prefix"
        )
    return prefix[:total]


def deployment_bases(manifest: dict[str, Any]) -> dict[str, tuple[int, int]]:
    descriptor_base = 0
    program_base = 0
    bases: dict[str, tuple[int, int]] = {}
    for deployment in manifest["deployments"]:
        bases[deployment["key"]] = (descriptor_base, program_base)
        descriptor_base += int(deployment["descriptor_count"])
        program_base += int(deployment["instruction_count"])
    return bases


def selected_profile(
    target: dict[str, Any],
    manifest: dict[str, Any],
    descriptors: list[int],
    programs: list[int],
    bases: dict[str, tuple[int, int]],
) -> dict[str, Any]:
    key = target["key"]
    deployment = next(item for item in manifest["deployments"] if item["key"] == key)
    descriptor_base, program_base = bases[key]
    instruction_bytes = programs[program_base + target["pc"]].to_bytes(32, "little")
    instruction = Instruction.decode(instruction_bytes)
    # THE OPERATOR IS IDENTIFIED BY WHAT IT IS, NOT BY ITS ID.
    #
    # This used to pin ``target["operator"]`` and refuse the program when the
    # instruction named anything else, which is how it read as
    # ``deepseek-v4-flash-hbm-cluster PC 14 does not name the expected MHC``: the
    # HBM operator descriptor had moved 545 -> 547 in a renumbering that changed
    # no semantics at all -- its views are still 539..542 and 543/544, over the
    # same objects 239, 1, 3, 2, 240, 241, with the same dtypes and permissions.
    # A descriptor id is a position in a table that every earlier removal shifts,
    # so pinning one makes this builder refuse after any unrelated change, and
    # pinning a NEW one only moves the next failure.
    #
    # What identifies this operator is that the instruction at the pinned program
    # counter dispatches VECTOR.MHC in its PRE form.  That is checked here and the
    # id is then read off the instruction.
    operator_id = int(instruction.descriptor_id)
    operator_record = descriptor_record(descriptors, descriptor_base, operator_id)
    operator = Descriptor.decode(operator_record, operator_id)
    if (
        int(operator.payload["engine_family"]) != 0x30
        or int(operator.payload["engine_sub"]) != 0x09
        or int(operator.payload["aux_id_1"]) != 20
    ):
        raise RuntimeError(
            f"{key} PC {target['pc']} names descriptor {operator_id}, which is not "
            "a VECTOR.MHC in its PRE form (aux_id_1 == 20)"
        )
    ids = {
        "counter": int(operator.payload["counter_class_id"]),
        "numeric": int(operator.payload["numeric_profile_id"]),
        "schedule": int(operator.payload["schedule_id"]),
        "input0": int(operator.payload["input_view_0"]),
        "input1": int(operator.payload["input_view_1"]),
        "input2": int(operator.payload["input_view_2"]),
        "input3": int(operator.payload["input_view_3"]),
        "output0": int(operator.payload["output_view_0"]),
        "output1": int(operator.payload["output_view_1"]),
        "wait": int(instruction.wait_set_id),
    }
    decoded: dict[str, Descriptor] = {"operator": operator}
    records: dict[str, bytes] = {"operator": operator_record}
    for name, descriptor_id in ids.items():
        record = descriptor_record(descriptors, descriptor_base, descriptor_id)
        records[name] = record
        decoded[name] = Descriptor.decode(record, descriptor_id)

    return {
        "target": target,
        "operator_id": operator_id,
        "deployment": deployment,
        "instruction": instruction,
        "instruction_bytes": instruction_bytes,
        "ids": ids,
        "descriptors": decoded,
        "records": records,
    }


def view_words(descriptor: Descriptor) -> list[int]:
    payload = descriptor.payload
    return [
        int(descriptor.primary_object_id),
        int(descriptor.permissions),
        int(payload["dtype"]),
        int(payload["rank"]),
        int(payload["dim0"]),
        int(payload["dim1"]),
        int(payload["dim2"]),
        int(payload["stride0"]),
        int(payload["stride1"]),
        int(payload["stride2"]),
    ]


def config_words(profile: dict[str, Any], active_tokens: int) -> list[int]:
    target = profile["target"]
    instruction: Instruction = profile["instruction"]
    descriptors: dict[str, Descriptor] = profile["descriptors"]
    operator = descriptors["operator"].payload
    counter = descriptors["counter"].payload
    numeric = descriptors["numeric"].payload
    schedule = descriptors["schedule"].payload
    wait = descriptors["wait"].payload

    words = [0] * CONFIG_WORDS
    words[0:10] = [
        int(target["profile"]),
        active_tokens,
        int(target["pc"]),
        int(instruction.flags),
        int(instruction.descriptor_id),
        int(instruction.wait_set_id),
        int(wait["producer_0"]),
        int(instruction.signal_event_id),
        int(instruction.control_id),
        int(instruction.source_operation_id),
    ]
    words[10:28] = [
        int(operator["engine_family"]),
        int(operator["engine_sub"]),
        int(operator["flags"]),
        int(operator["source_graph_operation_id"]),
        int(operator["source_kernel_id"]),
        int(operator["counter_class_id"]),
        int(operator["numeric_profile_id"]),
        int(operator["schedule_id"]),
        int(operator["input_view_0"]),
        int(operator["input_view_1"]),
        int(operator["input_view_2"]),
        int(operator["input_view_3"]),
        int(operator["output_view_0"]),
        int(operator["output_view_1"]),
        int(operator["aux_id_0"]),
        int(operator["aux_id_1"]),
        int(operator["aux_id_2"]),
        int(operator["aux_id_3"]),
    ]
    words[28:33] = [
        int(counter["group"]),
        int(counter["event_count"]),
        int(counter["counter_0"]),
        int(counter["counter_1"]),
        int(counter["counter_2"]),
    ]
    words[33:44] = [
        int(numeric["input_dtype"]),
        int(numeric["second_input_dtype"]),
        int(numeric["accumulator_dtype"]),
        int(numeric["output_dtype"]),
        int(numeric["rounding_mode"]),
        int(numeric["reduction_order"]),
        int(numeric["saturate"]),
        int(numeric["nan_policy"]),
        int(numeric["epsilon_bits"]),
        int(numeric["scale_bits"]),
        int(numeric["flags"]),
    ]
    digest = bytes(numeric["contract_digest"])
    if len(digest) != 32:
        raise RuntimeError("HC_PRE numeric contract digest is not 256 bits")
    words[44:52] = [
        int.from_bytes(digest[offset : offset + 4], "little")
        for offset in range(0, 32, 4)
    ]
    words[52:64] = [
        int(schedule["engine_family"]),
        int(schedule["queue_index"]),
        int(schedule["issue_window"]),
        int(schedule["tile_rows"]),
        int(schedule["tile_cols"]),
        int(schedule["tile_depth"]),
        int(schedule["bank_mask"]),
        int(schedule["port_mask"]),
        int(schedule["noc_route_class"]),
        int(schedule["resource_bound"]),
        int(schedule["max_outstanding"]),
        int(schedule["priority"]),
    ]
    for slot, name in enumerate(
        ("input0", "input1", "input2", "input3", "output0", "output1")
    ):
        words[64 + slot * 10 : 74 + slot * 10] = view_words(descriptors[name])
    return [value & 0xFFFFFFFF for value in words]


def ceil_div(value: int, divisor: int) -> int:
    return (value + divisor - 1) // divisor


def expected_counts(words: list[int]) -> dict[str, int]:
    tokens = words[1]
    tile_rows = words[55]
    tile_cols = words[56]
    tile_depth = words[57]
    row_tiles = ceil_div(tokens, tile_rows)
    projection_tiles = row_tiles * ceil_div(24, tile_cols) * ceil_div(16384, tile_depth)
    commit_tiles = row_tiles * (ceil_div(8, tile_cols) + ceil_div(16, tile_cols))
    return {
        "projection_tiles": projection_tiles,
        "commit_tiles": commit_tiles,
        "total_tiles": projection_tiles + commit_tiles,
        "logical_fmas": tokens * 24 * 16384,
        "logical_output_words": tokens * 24,
    }


def case_record(
    name: str,
    words: list[int],
    *,
    expected_error: int = ERR_NONE,
    scope: str,
    mutation: str | None = None,
) -> dict[str, Any]:
    admitted = expected_error == ERR_NONE
    counts = (
        expected_counts(words)
        if admitted
        else {
            "projection_tiles": 0,
            "commit_tiles": 0,
            "total_tiles": 0,
            "logical_fmas": 0,
            "logical_output_words": 0,
        }
    )
    return {
        "name": name,
        "config": words,
        "config_sha256": sha256_bytes(
            b"".join(value.to_bytes(4, "little") for value in words)
        ),
        "expected": {
            "admitted": admitted,
            "error_code": expected_error,
            **counts,
        },
        "scope": scope,
        "mutation": mutation,
    }


def add_mutation(
    cases: list[dict[str, Any]],
    base: list[int],
    name: str,
    word: int,
    value: int,
    error: int,
) -> None:
    changed = list(base)
    changed[word] = value & 0xFFFFFFFF
    cases.append(
        case_record(
            name,
            changed,
            expected_error=error,
            scope="fail_closed_descriptor_mutation",
            mutation=f"config[{word}]={value & 0xFFFFFFFF:#010x}",
        )
    )


def encoded_case(case: dict[str, Any]) -> list[int]:
    expected = case["expected"]
    values = list(case["config"])
    values.extend(
        [
            int(expected["admitted"]),
            int(expected["error_code"]),
            int(expected["projection_tiles"]) & 0xFFFFFFFF,
            int(expected["projection_tiles"]) >> 32,
            int(expected["commit_tiles"]) & 0xFFFFFFFF,
            int(expected["commit_tiles"]) >> 32,
            int(expected["total_tiles"]) & 0xFFFFFFFF,
            int(expected["total_tiles"]) >> 32,
            int(expected["logical_fmas"]) & 0xFFFFFFFF,
            int(expected["logical_fmas"]) >> 32,
            int(expected["logical_output_words"]) & 0xFFFFFFFF,
            int(expected["logical_output_words"]) >> 32,
            int(case["config"][64 + 4]),
            int(case["config"][0]),
            0,
            0,
        ]
    )
    if len(values) != CASE_WORDS:
        raise RuntimeError(
            f"case encoding is {len(values)} words, expected {CASE_WORDS}"
        )
    return values


def build(output: Path = OUTPUT_ROOT) -> dict[str, Any]:
    manifest_bytes = DEPLOYMENT_MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != "opentallas.rtl.abi3_deployment_vectors.v1":
        raise RuntimeError("retained deployment vector manifest has the wrong schema")
    for name, path in (
        ("a3_descriptor.hex", DESCRIPTOR_IMAGE),
        ("a3_program.hex", PROGRAM_IMAGE),
    ):
        if sha256_file(path) != manifest["image_sha256"][name]:
            raise RuntimeError(f"retained deployment image changed: {name}")

    descriptor_image = read_hex(DESCRIPTOR_IMAGE)
    program_image = read_hex(PROGRAM_IMAGE)
    bases = deployment_bases(manifest)
    profiles = {
        target["profile"]: selected_profile(
            target, manifest, descriptor_image, program_image, bases
        )
        for target in TARGETS
    }

    qualification_bytes = FUNCTIONAL_RESULT.read_bytes()
    qualification = json.loads(qualification_bytes)
    vector_bytes = FUNCTIONAL_VECTOR.read_bytes()
    vector = json.loads(vector_bytes)
    if qualification.get("status") != "pass":
        raise RuntimeError("the retained T=512 functional qualification is not passing")
    if qualification.get("vector_manifest_sha256") != sha256_bytes(vector_bytes):
        raise RuntimeError("the functional qualification does not bind its vector")

    # The current deployment removed one earlier HBM descriptor, shifting the
    # HC_PRE bundle down by one relative to the authenticated functional
    # qualification.  Prove exact semantic equivalence after only that explicit
    # reference renumbering; all arithmetic, geometry and schedule fields must
    # remain identical.
    hbm = profiles[PROFILE_HBM]
    qualified_descriptors = {
        int(item["descriptor_id"]): item
        for item in qualification["shipped_artifact"]["descriptors"]
    }
    qualified_ids = {
        "operator": 546,
        "counter": 536,
        "numeric": 544,
        "schedule": 545,
        "input0": 538,
        "input1": 539,
        "input2": 540,
        "input3": 541,
        "output0": 542,
        "output1": 543,
        "wait": 547,
    }
    # THE RENUMBERING OFFSET IS DERIVED, NOT WRITTEN DOWN.
    #
    # This comparison exists to say the current descriptors carry the SEMANTICS the
    # functional qualification authenticated, allowing for the fact that the table
    # has been renumbered since.  It applied a hardcoded ``+ 1`` to every
    # id-bearing field, which was the offset when it was written and is not the
    # offset now: the operator moved 545 -> 547 while the qualified artifact holds
    # 546, so the shift is -1 where the code assumed +1.
    #
    # A literal offset has to be re-edited after every renumbering and is silent
    # about whether the renumbering was uniform, which is the part that matters --
    # a uniform shift is a table rewrite, a non-uniform one means some descriptor
    # is now a different thing.  So the offset is measured once from the operator
    # and then required to hold for every other id below.
    offset = qualified_ids["operator"] - hbm["operator_id"]
    for name in hbm["records"]:
        descriptor_id = (
            hbm["operator_id"]
            if name == "operator"
            else hbm["ids"][name]
        )
        expected = qualified_descriptors.get(qualified_ids[name])
        if expected is None:
            raise RuntimeError(
                f"functional qualification omits prior descriptor {qualified_ids[name]}"
            )
        decoded = hbm["descriptors"][name]
        observed_payload = json_value(decoded.payload)
        if name == "operator":
            for field in (
                "counter_class_id",
                "numeric_profile_id",
                "schedule_id",
                "input_view_0",
                "input_view_1",
                "input_view_2",
                "input_view_3",
                "output_view_0",
                "output_view_1",
            ):
                observed_payload[field] += offset
        elif name.startswith("input") or name.startswith("output"):
            for slot in range(4):
                field = f"term{slot}_index"
                if slot < int(observed_payload["dynamic_term_count"]):
                    observed_payload[field] += offset
        if observed_payload != expected["payload"]:
            raise RuntimeError(
                f"current descriptor {descriptor_id} is not the qualified "
                f"semantics of prior descriptor {qualified_ids[name]}"
            )
    qualified_instruction = qualification["shipped_artifact"]
    if (
        int(hbm["instruction"].descriptor_id) + offset != qualified_ids["operator"]
        or int(hbm["instruction"].wait_set_id) + offset != qualified_ids["wait"]
        or int(hbm["instruction"].signal_event_id) != 4
        or int(hbm["instruction"].flags) != 12
        or qualified_instruction["program_pc"] != 14
    ):
        raise RuntimeError(
            "current HBM PC14 is not the qualified instruction semantics under a "
            f"uniform descriptor offset of {offset}"
        )

    output_records = vector["expected_outputs"]
    output_payloads: list[bytes] = []
    output_binding: dict[str, Any] = {}
    for name in ("weights", "combination"):
        record = output_records[name]
        path = FUNCTIONAL_VECTOR.parent / record["path"]
        payload = path.read_bytes()
        if len(payload) != record["bytes"] or sha256_bytes(payload) != record["sha256"]:
            raise RuntimeError(f"functional output changed: {name}")
        output_payloads.append(payload)
        output_binding[name] = {
            **record,
            "path": str(path.relative_to(ROOT)),
        }
    combined_output = b"".join(output_payloads)
    if len(combined_output) != 12_288 * 4:
        raise RuntimeError("functional HC_PRE output is not exactly 12,288 FP32 words")

    rom_words = config_words(profiles[PROFILE_ROM], 1)
    hbm_words = config_words(profiles[PROFILE_HBM], 512)
    cases = [
        case_record(
            "rom_pc15_decode_t1",
            rom_words,
            scope="exact_shipped_rom_descriptor_decode_extent",
        ),
        case_record(
            "hbm_pc14_authenticated_t512",
            hbm_words,
            scope="exact_authenticated_full_shape_functional_extent",
        ),
        case_record(
            "hbm_pc14_final_block_t320",
            config_words(profiles[PROFILE_HBM], 320),
            scope="descriptor_parameterization_schedule_only",
        ),
        case_record(
            "hbm_pc14_decode_t1",
            config_words(profiles[PROFILE_HBM], 1),
            scope="descriptor_parameterization_schedule_only",
        ),
    ]
    add_mutation(cases, rom_words, "bad_profile", 0, 2, ERR_INSTRUCTION)
    add_mutation(cases, rom_words, "rom_bad_pc", 2, 14, ERR_INSTRUCTION)
    add_mutation(cases, hbm_words, "hbm_bad_wait_event", 6, 2, ERR_INSTRUCTION)
    add_mutation(cases, hbm_words, "hbm_bad_signal", 7, 5, ERR_INSTRUCTION)
    add_mutation(cases, hbm_words, "bad_operator_id", 4, 546, ERR_INSTRUCTION)
    add_mutation(cases, hbm_words, "bad_mhc_selector", 24, 1, ERR_OPERATOR)
    add_mutation(cases, hbm_words, "bad_sinkhorn_iterations", 25, 19, ERR_OPERATOR)
    add_mutation(cases, hbm_words, "bad_counter", 30, 0x05000002, ERR_OPERATOR)
    add_mutation(cases, hbm_words, "bad_numeric_epsilon", 41, 0, ERR_NUMERIC)
    add_mutation(cases, hbm_words, "bad_numeric_digest", 44, 0, ERR_NUMERIC)
    add_mutation(cases, hbm_words, "zero_active_tokens", 1, 0, ERR_VIEW)
    add_mutation(cases, hbm_words, "active_tokens_over_capacity", 1, 513, ERR_VIEW)
    add_mutation(cases, hbm_words, "bad_hidden_multiplier", 69, 3, ERR_VIEW)
    add_mutation(cases, hbm_words, "bad_projection_width", 79, 16383, ERR_VIEW)
    add_mutation(cases, hbm_words, "bad_output_permission", 105, 1, ERR_VIEW)
    add_mutation(cases, hbm_words, "bad_schedule_rows", 55, 32, ERR_SCHEDULE)
    add_mutation(cases, hbm_words, "bad_schedule_depth", 57, 2, ERR_SCHEDULE)
    add_mutation(cases, rom_words, "rom_bad_schedule_ports", 59, 3, ERR_SCHEDULE)

    encoded = [word for case in cases for word in encoded_case(case)]
    case_payload = "".join(f"{word:08x}\n" for word in encoded).encode("ascii")

    profile_records: dict[str, Any] = {}
    for profile in profiles.values():
        target = profile["target"]
        profile_records[target["key"]] = {
            "profile": target["profile"],
            "program_counter": target["pc"],
            "operator_descriptor_id": profile["operator_id"],
            "deployment_sha256": profile["deployment"]["deployment_sha256"],
            "descriptor_table_sha256": profile["deployment"]["descriptor_table_sha256"],
            "instruction_sha256": sha256_bytes(profile["instruction_bytes"]),
            "authenticated_prior_descriptor_id": (
                qualified_ids["operator"]
                if target["profile"] == PROFILE_HBM
                else profile["operator_id"]
            ),
            "selected_descriptors": {
                name: {
                    "descriptor_id": (
                        profile["operator_id"]
                        if name == "operator"
                        else profile["ids"][name]
                    ),
                    "descriptor_type": int(descriptor.descriptor_type),
                    "permissions": int(descriptor.permissions),
                    "primary_object_id": int(descriptor.primary_object_id),
                    "payload": json_value(descriptor.payload),
                    "sha256": sha256_bytes(profile["records"][name]),
                }
                for name, descriptor in profile["descriptors"].items()
            },
        }

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "descriptor_bound_tiling_vectors",
        "abi": {"major": 3, "minor": 0},
        "config_words": CONFIG_WORDS,
        "case_words": CASE_WORDS,
        "case_count": len(cases),
        "positive_case_count": sum(case["expected"]["admitted"] for case in cases),
        "negative_case_count": sum(not case["expected"]["admitted"] for case in cases),
        "cases": [
            {key: value for key, value in case.items() if key != "config"}
            for case in cases
        ],
        "profiles": profile_records,
        "tiling_contract": {
            "projection": "[active_tokens,16384] x [24,16384]^T",
            "enumeration": "increasing token tile, parameter tile, then K tile",
            "accumulator_rule": "one output accumulator remains live across consecutive increasing-K depth tiles; split-K and reassociation are forbidden",
            "weight_output": "[active_tokens,2,4] FP32, flattened field width 8",
            "combination_output": "[active_tokens,4,4] FP32 source-major, flattened field width 16",
            "backpressure": "all tile metadata and counters remain stable until ready",
        },
        "functional_output_binding": {
            "qualification": {
                "path": str(FUNCTIONAL_RESULT.relative_to(ROOT)),
                "sha256": sha256_bytes(qualification_bytes),
                "record_sha256": qualification["record_sha256"],
                "status": qualification["status"],
            },
            "vector": {
                "path": str(FUNCTIONAL_VECTOR.relative_to(ROOT)),
                "sha256": sha256_bytes(vector_bytes),
                "manifest_sha256": vector["manifest_sha256"],
            },
            "outputs": output_binding,
            "concatenation_order": ["weights", "combination"],
            "combined_bytes": len(combined_output),
            "combined_words": len(combined_output) // 4,
            "combined_sha256": sha256_bytes(combined_output),
            "all_functional_words_bitwise_compared": qualification["claims"][
                "all_pc14_output_words_bitwise_compared"
            ],
        },
        "source": {
            str(path.relative_to(ROOT)): {
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in (
                DEPLOYMENT_MANIFEST,
                DESCRIPTOR_IMAGE,
                PROGRAM_IMAGE,
                FUNCTIONAL_RESULT,
                FUNCTIONAL_VECTOR,
                Path(__file__).resolve(),
            )
        },
        "selected_record_identity_rule": (
            "the current HBM HC_PRE bundle is the authenticated functional "
            "bundle shifted down by one descriptor ID; all non-reference "
            "payload fields are identical and every shifted reference is "
            "checked explicitly"
        ),
        "claim_boundary": {
            "exact_instruction_operator_numeric_view_schedule_admission": True,
            "exact_projection_and_output_coordinate_tiling": True,
            "full_functional_output_digest_bound": True,
            "full_hc_pre_rtl_arithmetic": False,
            "correctly_rounded_sigmoid_rtl": False,
            "correctly_rounded_exponential_rtl": False,
            "stable_softmax_frontend_rtl": False,
            "projection_mac_rtl_in_this_block": False,
            "shipped_prefix_integration": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
        },
    }

    output.mkdir(parents=True, exist_ok=True)
    (output / "cases.hex").write_bytes(case_payload)
    body["image_sha256"] = {"cases.hex": sha256_bytes(case_payload)}
    payload_without_id = canonical_json(body)
    body["vector_set_id"] = sha256_bytes(payload_without_id)
    (output / "index.json").write_bytes(
        json.dumps(body, indent=2, sort_keys=True).encode("ascii") + b"\n"
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    result = build(args.output)
    print(
        "built A3 MHC_PRE tile vectors: "
        f"{result['positive_case_count']} positive, "
        f"{result['negative_case_count']} fail-closed"
    )


if __name__ == "__main__":
    main()
