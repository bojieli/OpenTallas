#!/usr/bin/env python3
"""Build exact ABI 3.0 Qwen KV-scatter continuation vectors.

The vectors are extracted from the retained four-deployment images.  Key and
value payloads come from the already-qualified PC29 RoPE and PC17 V-projection
result words; they are activations, never oracle tokens.  A small independent
Python scatter constructs the expected active 17-row logical K/V planes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import NO_ID  # noqa: E402
from runtime.abi3.descriptors import DESCRIPTOR_HEADER, Descriptor  # noqa: E402
from runtime.abi3.records import Instruction  # noqa: E402


DEPLOYMENT_ROOT = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_MANIFEST = DEPLOYMENT_ROOT / "abi3_deployment_rtl_vectors.json"
DESCRIPTOR_IMAGE = DEPLOYMENT_ROOT / "a3_descriptor.hex"
PROGRAM_IMAGE = DEPLOYMENT_ROOT / "a3_program.hex"
PREFIX_ROOT = ROOT / "testdata/compiler/abi3_shipped_prefix"
PREFIX_MANIFEST = PREFIX_ROOT / "abi3_shipped_prefix_vectors.json"
PREFIX_EXPECT = PREFIX_ROOT / "p3_expect.hex"
# The golden WRITE stream: address then value, one pair per word the engines
# write, in launch order.  Results are placed by object, so the retained image
# holds only each object's LAST value and an operator whose buffer a later one
# rewrites is not in it.  Everything below that asks "what did the operator at
# PC n produce" therefore has to read this and not the image.
PREFIX_WRITES = PREFIX_ROOT / "p3_writes.hex"
PREFIX_CAMPAIGN = ROOT / "results/rtl/abi3_shipped_prefix_campaign.json"
OUTPUT_ROOT = ROOT / "testdata/rtl/a3_qwen_kv_scatter"

SCHEMA = "opentallas.rtl.a3_qwen_kv_scatter_vectors.v1"
CASE_WORDS = 32
DESCRIPTOR_BYTES = 192
ACTIVE_ROWS = 17
TRAILING = 1024
ACTIVE_WORDS = ACTIVE_ROWS * TRAILING
POSITION = 16

TRAP_NONE = 0
TRAP_INTEGRITY = 2
TRAP_DESCRIPTOR = 3
TRAP_CAPABILITY = 4
TRAP_ENGINE = 8
REFUSAL_NONE = 0
REFUSAL_INTEGRITY = 2
REFUSAL_DESCRIPTOR = 3
REFUSAL_CAPABILITY = 4
REFUSAL_ENGINE = 5

TARGETS = (
    {"key": "qwen3-8b-rom-single-chip", "profile": 0},
    {"key": "qwen3-8b-hbm-single-chip", "profile": 1},
)
PCS = (32, 35, 38)
VECTOR_FILES = (
    "cases.hex",
    "instruction.hex",
    "operator.hex",
    "view0.hex",
    "view1.hex",
    "view2.hex",
    "view3.hex",
    "output.hex",
    "numeric.hex",
    "source.hex",
    "index.json",
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


def read_hex(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line.strip()]


def hex_lines(values: list[int], bits: int = 32) -> str:
    width = bits // 4
    mask = (1 << bits) - 1
    return "".join(f"{value & mask:0{width}x}\n" for value in values)


def padded_record(record: bytes) -> bytes:
    if len(record) > DESCRIPTOR_BYTES:
        raise RuntimeError("selected descriptor exceeds the retained RTL beat")
    return record + bytes(DESCRIPTOR_BYTES - len(record))


def descriptor_record(image: list[int], base: int, descriptor_id: int) -> bytes:
    padded = image[base + descriptor_id].to_bytes(DESCRIPTOR_BYTES, "little")
    header = DESCRIPTOR_HEADER.decode(padded[:64])
    total = int(header["total_bytes"])
    if total not in (128, 192):
        raise RuntimeError(
            f"descriptor {descriptor_id} has unsupported fixed size {total}"
        )
    if any(padded[total:]):
        raise RuntimeError(f"descriptor {descriptor_id} has nonzero beat padding")
    record = padded[:total]
    Descriptor.decode(record, descriptor_id)
    return record


def deployment_bases(manifest: dict[str, Any]) -> dict[str, tuple[int, int]]:
    descriptor_base = 0
    program_base = 0
    bases: dict[str, tuple[int, int]] = {}
    for deployment in manifest["deployments"]:
        bases[deployment["key"]] = (descriptor_base, program_base)
        descriptor_base += int(deployment["descriptor_count"])
        program_base += int(deployment["instruction_count"])
    return bases


def selected_operation(
    *,
    target: dict[str, Any],
    pc: int,
    manifest: dict[str, Any],
    descriptors: list[int],
    programs: list[int],
    bases: dict[str, tuple[int, int]],
) -> dict[str, Any]:
    descriptor_base, program_base = bases[target["key"]]
    instruction_record = programs[program_base + pc].to_bytes(32, "little")
    instruction = Instruction.decode(instruction_record)
    operator_id = int(instruction.descriptor_id)
    operator_record = descriptor_record(descriptors, descriptor_base, operator_id)
    operator = Descriptor.decode(operator_record, operator_id)
    payload = operator.payload
    ids = {
        "operator": operator_id,
        "view0": int(payload["input_view_0"]),
        "view1": int(payload["input_view_1"]),
        "view2": int(payload["input_view_2"]),
        "view3": int(payload["input_view_3"]),
        "output": int(payload["output_view_0"]),
        "numeric": int(payload["numeric_profile_id"]),
    }
    records: dict[str, bytes] = {"operator": operator_record}
    decoded: dict[str, Descriptor] = {"operator": operator}
    for name in ("view0", "view1", "view2", "view3", "output", "numeric"):
        descriptor_id = ids[name]
        if descriptor_id == NO_ID:
            records[name] = b""
            continue
        record = descriptor_record(descriptors, descriptor_base, descriptor_id)
        records[name] = record
        decoded[name] = Descriptor.decode(record, descriptor_id)
    objects = {
        name: (
            int(decoded[name].primary_object_id) if name in decoded else NO_ID
        )
        for name in ("view0", "view1", "view2", "view3", "output")
    }
    return {
        "target": target,
        "deployment": next(
            item for item in manifest["deployments"] if item["key"] == target["key"]
        ),
        "pc": pc,
        "instruction": instruction,
        "instruction_record": instruction_record,
        "ids": ids,
        "objects": objects,
        "records": records,
        "decoded": decoded,
    }


def assert_profile(profile: dict[str, Any]) -> None:
    pc = profile["pc"]
    instruction: Instruction = profile["instruction"]
    op = profile["decoded"]["operator"]
    views = profile["decoded"]
    if len(profile["deployment"].get("verifier_errors", [])) != 0:
        raise RuntimeError("selected deployment is not admitted")
    if instruction.flags != 12 or instruction.source_operation_id != {32: 11, 35: 12, 38: 13}[pc]:
        raise RuntimeError(f"PC {pc} instruction control metadata changed")
    expected_mnemonic = "DMA.SCATTER" if pc in (32, 35) else "ATTENTION.GQA"
    if instruction.mnemonic != expected_mnemonic:
        raise RuntimeError(f"PC {pc} is {instruction.mnemonic}, expected {expected_mnemonic}")
    if op.payload["engine_family"] != instruction.major or op.payload["engine_sub"] != instruction.sub:
        raise RuntimeError(f"PC {pc} operator opcode differs")
    numeric = views["numeric"].payload
    expected_contract = {
        32: "55f39bccbda65baf6238cfcd93d7bf9959330984af837979870cc019be00e16f",
        35: "55f39bccbda65baf6238cfcd93d7bf9959330984af837979870cc019be00e16f",
        38: "623af598461a17f0b15fb564380a7b8de0bf3f8c89a0833947ad9ed8872ce181",
    }[pc]
    if bytes(numeric["contract_digest"]).hex() != expected_contract:
        raise RuntimeError(f"PC {pc} numeric contract changed")
    if pc in (32, 35):
        index = views["view0"].payload
        source = views["view1"].payload
        output = views["output"].payload
        if (
            [index["dtype"], index["rank"], index["dim0"], index["stride0"]]
            != [4, 1, 512, 1]
            or [source[f"dim{i}"] for i in range(3)] != [512, 8, 128]
            or [source[f"stride{i}"] for i in range(3)] != [1024, 128, 1]
            or [output[f"dim{i}"] for i in range(3)] != [8256, 8, 128]
            or [output[f"stride{i}"] for i in range(3)] != [2048, 128, 1]
            or output["element_offset"] != (0 if pc == 32 else 1024)
        ):
            raise RuntimeError(f"PC {pc} scatter geometry changed")
        resolved_index = POSITION + 0 * int(index["term1_stride"])
        resolved_source = 0 + 0 * int(source["term0_stride"])
        resolved_output = int(output["element_offset"]) + 0 * int(
            output["term0_stride"]
        )
        if (resolved_index, resolved_source, resolved_output) != (
            POSITION,
            0,
            0 if pc == 32 else 1024,
        ):
            raise RuntimeError(f"PC {pc} resolved offsets changed")
    else:
        q = views["view0"].payload
        key = views["view1"].payload
        value = views["view2"].payload
        position = views["view3"].payload
        output = views["output"].payload
        if (
            [q[f"dim{i}"] for i in range(3)] != [512, 32, 128]
            or [key[f"dim{i}"] for i in range(3)] != [8256, 8, 128]
            or [value[f"dim{i}"] for i in range(3)] != [8256, 8, 128]
            or position["dtype"] != 4
            or [output[f"dim{i}"] for i in range(3)] != [512, 32, 128]
            or numeric["scale_bits"] != 1_035_272_192
        ):
            raise RuntimeError("PC 38 GQA geometry changed")


def prefix_write_values(path: Path = PREFIX_WRITES) -> list[int]:
    """The values of the golden write stream, in launch order.

    ``operation_word_ranges`` below is a cursor over the words each operation
    WRITES, which is exactly this stream's ordering -- and is no longer the
    ordering of the retained image.
    """
    words = read_hex(path)
    if len(words) % 2:
        raise RuntimeError("the golden write stream is not address/value pairs")
    return [words[index * 2 + 1] for index in range(len(words) // 2)]


def operation_word_ranges(prefix_case: dict[str, Any]) -> dict[int, tuple[int, int]]:
    cursor = 0
    result: dict[int, tuple[int, int]] = {}
    for operation in prefix_case["supported_prefix"]:
        kind = operation["kind"]
        if kind == "dma_gather":
            count = int(operation["source_view"]["dims"][1])
        elif kind in ("tensor_embed_lookup", "vector_rms_norm"):
            count = 4096
        elif kind == "tensor_matmul":
            count = int(operation["association_scope"]["columns"])
        elif kind in ("vector_head_rms_norm", "vector_rope"):
            count = int(operation["row_count"]) * int(operation["row_width"])
        elif kind == "dma_transfer":
            count = 16384
        else:
            raise RuntimeError(f"unknown retained prefix operation {kind}")
        result[int(operation["pc"])] = (cursor, count)
        cursor += count
    if cursor != int(prefix_case["expected"]["result_words"]):
        raise RuntimeError("retained prefix result cursor differs")
    return result


def extract_sources(prefix: dict[str, Any], words: list[int]) -> dict[str, list[int]]:
    cursor = 0
    per_target: dict[str, dict[str, list[int]]] = {}
    for case in prefix["cases"]:
        count = int(case["expected"]["result_words"])
        if case["deployment"] in {target["key"] for target in TARGETS}:
            ranges = operation_word_ranges(case)
            value_start, value_count = ranges[17]
            key_start, key_count = ranges[29]
            if value_count != TRAILING or key_count != TRAILING:
                raise RuntimeError("retained Qwen K/V row width changed")
            per_target[case["deployment"]] = {
                "key": words[cursor + key_start : cursor + key_start + key_count],
                "value": words[
                    cursor + value_start : cursor + value_start + value_count
                ],
            }
        cursor += count
    if cursor != len(words):
        raise RuntimeError("retained prefix expected image length changed")
    rom = per_target[TARGETS[0]["key"]]
    hbm = per_target[TARGETS[1]["key"]]
    if rom != hbm:
        raise RuntimeError("ROM and HBM upstream K/V result words differ")
    for name, expected in {
        "key": "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406",
        "value": "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
    }.items():
        if any(value >> 16 for value in rom[name]):
            raise RuntimeError(f"retained {name} words are not zero-extended BF16")
        payload = struct.pack(f"<{TRAILING}H", *rom[name])
        if sha256_bytes(payload) != expected:
            raise RuntimeError(f"retained {name} activation digest changed")
    return rom


def prior_word(index: int, plane: int) -> int:
    seed = 0x1357 if plane == 0 else 0x2468
    return ((index * 251 + seed) % 0x7F7E) + 1


def scatter_expected(source: list[int], plane: int) -> list[int]:
    output = [prior_word(index, plane) for index in range(ACTIVE_WORDS)]
    base = POSITION * TRAILING
    output[base : base + TRAILING] = source
    return output


def encoded_case(case: dict[str, Any]) -> list[int]:
    profile = case["profile"]
    ids = profile["ids"]
    objects = profile["objects"]
    expected = case["expected"]
    values = [0] * CASE_WORDS
    values[:28] = [
        int(profile["pc"]),
        int(profile["deployment"]["instruction_count"]),
        int(ids["operator"]),
        int(ids["view0"]),
        int(ids["view1"]),
        int(ids["view2"]),
        int(ids["view3"]),
        int(ids["output"]),
        int(ids["numeric"]),
        int(objects["view0"]),
        int(objects["view1"]),
        int(objects["view2"]),
        int(objects["view3"]),
        int(objects["output"]),
        POSITION,
        ACTIVE_ROWS,
        int(case["index_value"]),
        int(case["plane"]),
        int(expected["failed"]),
        int(expected["trap_class"]),
        int(expected["refusal_reason"]),
        int(expected["records_checked"]),
        int(expected["moved_elements"]),
        int(expected["indices_checked"]),
        int(expected["write_count"]),
        int(expected["gqa_boundary"]),
        int(expected["compare_output"]),
        int(profile["target"]["profile"]),
    ]
    return [value & 0xFFFFFFFF for value in values]


def case_record(
    name: str,
    profile: dict[str, Any],
    *,
    plane: int,
    index_value: int = POSITION,
    expected: dict[str, Any],
    mutation: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "profile": profile,
        "plane": plane,
        "index_value": index_value,
        "expected": expected,
        "mutation": mutation,
    }


def scatter_pass() -> dict[str, Any]:
    return {
        "failed": False,
        "trap_class": TRAP_NONE,
        "refusal_reason": REFUSAL_NONE,
        "records_checked": 5,
        "moved_elements": TRAILING,
        "indices_checked": 1,
        "write_count": ACTIVE_WORDS + TRAILING,
        "gqa_boundary": False,
        "compare_output": True,
    }


def refusal(
    trap: int,
    reason: int,
    records: int,
    *,
    indices: int = 0,
    gqa: bool = False,
) -> dict[str, Any]:
    return {
        "failed": True,
        "trap_class": trap,
        "refusal_reason": reason,
        "records_checked": records,
        "moved_elements": 0,
        "indices_checked": indices,
        "write_count": 0,
        "gqa_boundary": gqa,
        "compare_output": False,
    }


def public_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "target": profile["target"],
        "deployment": profile["deployment"],
        "pc": profile["pc"],
        "instruction": {
            "mnemonic": profile["instruction"].mnemonic,
            "sha256": sha256_bytes(profile["instruction_record"]),
            "flags": int(profile["instruction"].flags),
            "source_operation_id": int(profile["instruction"].source_operation_id),
        },
        "ids": profile["ids"],
        "objects": profile["objects"],
        "descriptor_sha256": {
            name: sha256_bytes(record)
            for name, record in profile["records"].items()
            if record
        },
    }


def serializable_case(case: dict[str, Any]) -> dict[str, Any]:
    profile = case["profile"]
    return {
        "name": case["name"],
        "target": profile["target"]["key"],
        "profile": profile["target"]["profile"],
        "pc": profile["pc"],
        "plane": case["plane"],
        "index_value": case["index_value"],
        "expected": case["expected"],
        "mutation": case["mutation"],
    }


def build(output: Path = OUTPUT_ROOT) -> dict[str, Any]:
    deployment = json.loads(DEPLOYMENT_MANIFEST.read_text())
    if deployment.get("schema") != "opentallas.rtl.abi3_deployment_vectors.v1":
        raise RuntimeError("retained deployment vector manifest has the wrong schema")
    for name, path in (
        ("a3_descriptor.hex", DESCRIPTOR_IMAGE),
        ("a3_program.hex", PROGRAM_IMAGE),
    ):
        if sha256_file(path) != deployment["image_sha256"][name]:
            raise RuntimeError(f"retained deployment image changed: {name}")

    prefix = json.loads(PREFIX_MANIFEST.read_text())
    campaign = json.loads(PREFIX_CAMPAIGN.read_text())
    if (
        prefix.get("schema") != "opentallas.rtl.abi3_shipped_prefix_vectors.v1"
        or campaign.get("status") != "pass"
        or not campaign.get("integrated_replay_passed")
        or campaign["vector_set"]["sha256"] != sha256_file(PREFIX_MANIFEST)
        or sha256_file(PREFIX_EXPECT) != prefix["image_sha256"]["p3_expect.hex"]
        or sha256_file(PREFIX_WRITES) != prefix["image_sha256"]["p3_writes.hex"]
    ):
        raise RuntimeError("retained upstream RTL result witness is not current")

    descriptor_image = read_hex(DESCRIPTOR_IMAGE)
    program_image = read_hex(PROGRAM_IMAGE)
    bases = deployment_bases(deployment)
    profiles: dict[tuple[int, int], dict[str, Any]] = {}
    for target in TARGETS:
        for pc in PCS:
            profile = selected_operation(
                target=target,
                pc=pc,
                manifest=deployment,
                descriptors=descriptor_image,
                programs=program_image,
                bases=bases,
            )
            assert_profile(profile)
            profiles[(target["profile"], pc)] = profile

    sources = extract_sources(prefix, prefix_write_values())
    expected_planes = {
        "key": scatter_expected(sources["key"], 0),
        "value": scatter_expected(sources["value"], 1),
    }

    cases: list[dict[str, Any]] = []
    for target in TARGETS:
        tag = "rom" if target["profile"] == 0 else "hbm"
        cases.extend(
            [
                case_record(
                    f"{tag}_pc32_key_scatter",
                    copy.deepcopy(profiles[(target["profile"], 32)]),
                    plane=0,
                    expected=scatter_pass(),
                ),
                case_record(
                    f"{tag}_pc35_value_scatter",
                    copy.deepcopy(profiles[(target["profile"], 35)]),
                    plane=1,
                    expected=scatter_pass(),
                ),
                case_record(
                    f"{tag}_pc38_gqa_boundary",
                    copy.deepcopy(profiles[(target["profile"], 38)]),
                    plane=2,
                    expected=refusal(
                        TRAP_CAPABILITY,
                        REFUSAL_CAPABILITY,
                        7,
                        gqa=True,
                    ),
                ),
            ]
        )

    corrupt_instruction = copy.deepcopy(profiles[(0, 32)])
    damaged = bytearray(corrupt_instruction["instruction_record"])
    damaged[31] ^= 0x01
    corrupt_instruction["instruction_record"] = bytes(damaged)
    cases.append(
        case_record(
            "rom_pc32_instruction_crc_corrupt",
            corrupt_instruction,
            plane=0,
            expected=refusal(TRAP_INTEGRITY, REFUSAL_INTEGRITY, 0),
            mutation="instruction byte 31 bit 0 flipped without CRC repair",
        )
    )

    wrong_object = copy.deepcopy(profiles[(1, 32)])
    descriptor = copy.deepcopy(wrong_object["decoded"]["view1"])
    descriptor.primary_object_id += 1000
    wrong_object["records"]["view1"] = descriptor.encode()
    cases.append(
        case_record(
            "hbm_pc32_wrong_source_object_valid_crc",
            wrong_object,
            plane=0,
            expected=refusal(TRAP_DESCRIPTOR, REFUSAL_DESCRIPTOR, 5),
            mutation="source-view primary object changed and descriptor CRC repaired",
        )
    )

    wrong_shape = copy.deepcopy(profiles[(0, 35)])
    descriptor = copy.deepcopy(wrong_shape["decoded"]["view1"])
    descriptor.payload["dim2"] = 127
    wrong_shape["records"]["view1"] = descriptor.encode()
    cases.append(
        case_record(
            "rom_pc35_wrong_source_shape_valid_crc",
            wrong_shape,
            plane=1,
            expected=refusal(TRAP_DESCRIPTOR, REFUSAL_DESCRIPTOR, 5),
            mutation="source-view head width changed to 127 and descriptor CRC repaired",
        )
    )

    wrong_contract = copy.deepcopy(profiles[(1, 35)])
    descriptor = copy.deepcopy(wrong_contract["decoded"]["numeric"])
    digest = bytearray(descriptor.payload["contract_digest"])
    digest[0] ^= 0x01
    descriptor.payload["contract_digest"] = bytes(digest)
    wrong_contract["records"]["numeric"] = descriptor.encode()
    cases.append(
        case_record(
            "hbm_pc35_wrong_numeric_contract_valid_crc",
            wrong_contract,
            plane=1,
            expected=refusal(TRAP_DESCRIPTOR, REFUSAL_DESCRIPTOR, 5),
            mutation="numeric contract bit flipped and descriptor CRC repaired",
        )
    )

    late_crc = copy.deepcopy(profiles[(0, 32)])
    damaged = bytearray(late_crc["records"]["output"])
    damaged[-1] ^= 0x80
    late_crc["records"]["output"] = bytes(damaged)
    cases.append(
        case_record(
            "rom_pc32_output_record_late_crc_corrupt",
            late_crc,
            plane=0,
            expected=refusal(TRAP_INTEGRITY, REFUSAL_INTEGRITY, 3),
            mutation="last byte of fourth descriptor flipped without CRC repair",
        )
    )

    cases.append(
        case_record(
            "rom_pc32_out_of_active_context_index",
            copy.deepcopy(profiles[(0, 32)]),
            plane=0,
            index_value=ACTIVE_ROWS,
            expected=refusal(
                TRAP_ENGINE, REFUSAL_ENGINE, 5, indices=1
            ),
            mutation="index equals active-row extent 17",
        )
    )

    output.mkdir(parents=True, exist_ok=True)
    images: dict[str, str] = {
        "cases.hex": hex_lines(
            [word for case in cases for word in encoded_case(case)]
        ),
        "instruction.hex": hex_lines(
            [
                int.from_bytes(case["profile"]["instruction_record"], "little")
                for case in cases
            ],
            256,
        ),
        "source.hex": hex_lines(sources["key"] + sources["value"]),
    }
    for name in ("operator", "view0", "view1", "view2", "view3", "output", "numeric"):
        images[f"{name}.hex"] = hex_lines(
            [
                int.from_bytes(
                    padded_record(case["profile"]["records"].get(name, b"")),
                    "little",
                )
                for case in cases
            ],
            1536,
        )
    for name, payload in images.items():
        (output / name).write_text(payload, encoding="ascii")

    source_binding = {
        name: {
            "producer_pc": 29 if name == "key" else 17,
            "word_count": TRAILING,
            "bf16_payload_sha256": sha256_bytes(
                struct.pack(f"<{TRAILING}H", *values)
            ),
            "word_payload_sha256": sha256_bytes(
                struct.pack(f"<{TRAILING}I", *values)
            ),
        }
        for name, values in sources.items()
    }
    plane_binding = {
        name: {
            "prior_word_payload_sha256": sha256_bytes(
                struct.pack(
                    f"<{ACTIVE_WORDS}I",
                    *[prior_word(index, plane) for index in range(ACTIVE_WORDS)],
                )
            ),
            "expected_word_payload_sha256": sha256_bytes(
                struct.pack(f"<{ACTIVE_WORDS}I", *expected_planes[name])
            ),
            "preserved_word_count": ACTIVE_WORDS - TRAILING,
            "replaced_word_count": TRAILING,
        }
        for name, plane in (("key", 0), ("value", 1))
    }
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "request": {
            "phase": "decode",
            "position_start": POSITION,
            "context_length": ACTIVE_ROWS,
            "active_rows": ACTIVE_ROWS,
            "kv_heads": 8,
            "head_width": 128,
            "plane_words": TRAILING,
        },
        "profiles": {
            f"{profile['target']['key']}/pc{pc}": public_profile(profile)
            for (_, pc), profile in sorted(profiles.items())
        },
        "cases": [serializable_case(case) for case in cases],
        "positive_scatter_case_count": 4,
        "gqa_boundary_case_count": 2,
        "negative_case_count": len(cases) - 6,
        "source_binding": source_binding,
        "plane_binding": plane_binding,
        "upstream_dependency": {
            "campaign": str(PREFIX_CAMPAIGN.relative_to(ROOT)),
            "campaign_sha256": sha256_file(PREFIX_CAMPAIGN),
            "campaign_status": campaign["status"],
            "integrated_replay_passed": campaign["integrated_replay_passed"],
            "vector_manifest": str(PREFIX_MANIFEST.relative_to(ROOT)),
            "vector_manifest_sha256": sha256_file(PREFIX_MANIFEST),
            "expected_image": str(PREFIX_EXPECT.relative_to(ROOT)),
            "expected_image_sha256": sha256_file(PREFIX_EXPECT),
        },
        "claim_boundary": {
            "exact_rom_and_hbm_pc32_pc35_instruction_records": True,
            "exact_operator_tensor_view_numeric_records": True,
            "descriptor_crc_before_write": True,
            "exact_upstream_key_from_pc29_rope": True,
            "exact_upstream_value_from_pc17_projection": True,
            "all_active_plane_words_compared": True,
            "unchanged_rows_preserved": True,
            "row_16_replaced": True,
            "exact_pc38_gqa_metadata_admitted": True,
            "gqa_arithmetic": False,
            "authentic_prior_context_kv": False,
            "complete_layer": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_timing": False,
            "tpot": False,
            "verification_cycles_are_tpot": False,
        },
    }
    index_payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    (output / "index.json").write_text(index_payload, encoding="utf-8")
    manifest["image_sha256"] = {
        name: sha256_file(output / name) for name in VECTOR_FILES if name != "index.json"
    }
    (output / "index.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    return result


def main() -> int:
    args = parser().parse_args()
    manifest = build(args.output)
    print(
        "built ABI3 Qwen KV-scatter vectors "
        f"cases={len(manifest['cases'])} scatters={manifest['positive_scatter_case_count']} "
        "next_pc=38"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
