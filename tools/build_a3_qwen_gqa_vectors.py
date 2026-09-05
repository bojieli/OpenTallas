#!/usr/bin/env python3
"""Build independent exact vectors for the Qwen ABI 3.0 PC38 GQA RTL.

The current query, key, and value row are retained causal RTL results.  No
authentic earlier-token KV capture exists in the repository, so the earlier
rows are explicit deterministic permutations of the authentic row and are
never called model history.  Expected PC38 words are produced by the
independent scalar target-precision reference, not by the simulator kernel or
the DUT.

The datapath's context length used to be a constant 17, which expressed
exactly the first generated token.  The governed workload's three decode
positions run at contexts 17, 18 and 19, so the positive cases now cover all
three: one independent KV plane and one independently computed expected
output per context, each with the authentic current row at its own position.
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

from runtime.reference.tensor_accelerator_attention import (  # noqa: E402
    gqa_causal_attention_bf16,
    make_kv_snapshot,
    prepare_kv_append,
)
from tools import build_a3_qwen_kv_scatter_vectors as scatter  # noqa: E402


OUTPUT_ROOT = ROOT / "testdata/rtl/a3_qwen_gqa"
SCHEMA = "opentallas.rtl.a3_qwen_gqa_vectors.v1"
CASE_WORDS = 32
# The three decode positions the governed workload runs, and the compile-time
# bound the RTL buffers are sized to.
CONTEXTS = (17, 18, 19)
MAX_CONTEXT = max(CONTEXTS)
QUERY_HEADS = 32
KV_HEADS = 8
HEAD_WIDTH = 128
QUERY_WORDS = QUERY_HEADS * HEAD_WIDTH
KV_ROW_WORDS = KV_HEADS * HEAD_WIDTH
OUTPUT_WORDS = QUERY_HEADS * HEAD_WIDTH
QUERY_BASE = 0
OUTPUT_BASE = 0


def plane_bases() -> dict[int, tuple[int, int]]:
    """One independent key and value plane per context, packed in order."""

    cursor = QUERY_BASE + QUERY_WORDS
    bases: dict[int, tuple[int, int]] = {}
    for context in CONTEXTS:
        key_base = cursor
        cursor += context * KV_ROW_WORDS
        value_base = cursor
        cursor += context * KV_ROW_WORDS
        bases[context] = (key_base, value_base)
    return bases


PLANE_BASES = plane_bases()
SOURCE_WORDS = (
    QUERY_WORDS + 2 * KV_ROW_WORDS * sum(CONTEXTS)
)

TRAP_NONE = 0
TRAP_INTEGRITY = 2
TRAP_DESCRIPTOR = 3
TRAP_ENGINE = 8
REFUSAL_NONE = 0
REFUSAL_INTEGRITY = 2
REFUSAL_DESCRIPTOR = 3
REFUSAL_ENGINE = 5

MUTATION_NONE = 0
MUTATION_LATE_VALUE_NONFINITE = 1

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
    "expected.hex",
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


def read_profile() -> tuple[dict[str, Any], dict[str, Any]]:
    deployment = json.loads(scatter.DEPLOYMENT_MANIFEST.read_text())
    descriptor_image = scatter.read_hex(scatter.DESCRIPTOR_IMAGE)
    program_image = scatter.read_hex(scatter.PROGRAM_IMAGE)
    bases = scatter.deployment_bases(deployment)
    profiles = []
    for target in scatter.TARGETS:
        profile = scatter.selected_operation(
            target=target,
            pc=38,
            manifest=deployment,
            descriptors=descriptor_image,
            programs=program_image,
            bases=bases,
        )
        scatter.assert_profile(profile)
        profiles.append(profile)
    return profiles[0], profiles[1]


def authentic_activations() -> tuple[list[int], list[int], list[int]]:
    prefix = json.loads(scatter.PREFIX_MANIFEST.read_text())
    campaign = json.loads(scatter.PREFIX_CAMPAIGN.read_text())
    if campaign.get("status") != "pass" or not campaign.get(
        "integrated_replay_passed"
    ):
        raise RuntimeError("retained causal prefix is not passing")
    words = scatter.read_hex(scatter.PREFIX_EXPECT)
    cursor = 0
    selected: dict[str, list[int]] = {}
    for case in prefix["cases"]:
        count = int(case["expected"]["result_words"])
        if case["deployment"] == "qwen3-8b-rom-single-chip":
            ranges = scatter.operation_word_ranges(case)
            for name, pc in (("value", 17), ("query", 26), ("key", 29)):
                start, length = ranges[pc]
                selected[name] = words[cursor + start : cursor + start + length]
        cursor += count
    expected = {
        "query": (
            QUERY_WORDS,
            "f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150",
        ),
        "key": (
            KV_ROW_WORDS,
            "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406",
        ),
        "value": (
            KV_ROW_WORDS,
            "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
        ),
    }
    for name, (length, digest) in expected.items():
        values = selected.get(name, [])
        payload = struct.pack(f"<{length}H", *values)
        if len(values) != length or sha256_bytes(payload) != digest:
            raise RuntimeError(f"retained authentic {name} changed")
        if any(value >> 16 for value in values):
            raise RuntimeError(f"retained {name} is not zero-extended BF16")
    return selected["query"], selected["key"], selected["value"]


def rows_from_current(
    current: list[int], *, value_plane: bool, context: int
) -> list[list[int]]:
    """Make context-1 synthetic rows followed by the authentic current row."""

    current_heads = [
        current[head * HEAD_WIDTH : (head + 1) * HEAD_WIDTH]
        for head in range(KV_HEADS)
    ]
    rows: list[list[int]] = []
    for row in range(context - 1):
        transformed: list[int] = []
        for head in range(KV_HEADS):
            source_head = current_heads[(head + row + (1 if value_plane else 0)) % KV_HEADS]
            rotation = (row * (13 if value_plane else 11) + head * 3) % HEAD_WIDTH
            if (row + head) & 1:
                source_head = list(reversed(source_head))
            transformed.extend(
                source_head[(element + rotation) % HEAD_WIDTH]
                for element in range(HEAD_WIDTH)
            )
        rows.append(transformed)
    rows.append(list(current))
    return rows


def reshape_query(flat: list[int]) -> list[list[list[int]]]:
    return [[
        flat[head * HEAD_WIDTH : (head + 1) * HEAD_WIDTH]
        for head in range(QUERY_HEADS)
    ]]


def reshape_kv(rows: list[list[int]]) -> list[list[list[int]]]:
    return [
        [
            row[head * HEAD_WIDTH : (head + 1) * HEAD_WIDTH]
            for head in range(KV_HEADS)
        ]
        for row in rows
    ]


def expected_attention(
    query: list[int],
    key_rows: list[list[int]],
    value_rows: list[list[int]],
    *,
    context: int,
) -> list[int]:
    position = context - 1
    snapshot = make_kv_snapshot(
        resource_id="qwen.layer0.kv",
        generation=position,
        capacity=8192,
        key_values=reshape_kv(key_rows[:-1]),
        value_values=reshape_kv(value_rows[:-1]),
    )
    prepared = prepare_kv_append(
        snapshot,
        transaction_id=0x4154544E00000011,
        expected_generation=position,
        position_start=position,
        key_values=reshape_kv(key_rows[-1:]),
        value_values=reshape_kv(value_rows[-1:]),
    )
    result = gqa_causal_attention_bf16(
        reshape_query(query), snapshot, prepared
    )
    if result.accounting.score_multiplications != context * OUTPUT_WORDS:
        raise RuntimeError("independent score accounting changed")
    if result.accounting.value_multiplications != context * OUTPUT_WORDS:
        raise RuntimeError("independent value accounting changed")
    return [
        code
        for head in result.output_values[0]
        for code in head
    ]


def success(*, stalls: bool, context: int) -> dict[str, int | bool]:
    return {
        "failed": False,
        "trap_class": TRAP_NONE,
        "refusal_reason": REFUSAL_NONE,
        "records_checked": 7,
        "memory_reads": QUERY_WORDS + 2 * context * OUTPUT_WORDS,
        "writes": OUTPUT_WORDS,
        "score_multiplies": context * OUTPUT_WORDS,
        "exponentials": context * QUERY_HEADS,
        "value_multiplies": context * OUTPUT_WORDS,
        "saturations": 0,
        "gqa_executed": True,
        "compare_output": True,
        "stall_mode": int(stalls),
        "context": context,
    }


def refusal(
    trap: int,
    reason: int,
    records: int,
    *,
    memory_reads: int = 0,
    score_multiplies: int = 0,
    exponentials: int = 0,
    value_multiplies: int = 0,
    mutation: int = MUTATION_NONE,
    context: int = CONTEXTS[0],
) -> dict[str, int | bool]:
    return {
        "failed": True,
        "trap_class": trap,
        "refusal_reason": reason,
        "records_checked": records,
        "memory_reads": memory_reads,
        "writes": 0,
        "score_multiplies": score_multiplies,
        "exponentials": exponentials,
        "value_multiplies": value_multiplies,
        "saturations": 0,
        "gqa_executed": False,
        "compare_output": False,
        "stall_mode": 1,
        "mutation": mutation,
        "context": context,
    }


def case(name: str, profile: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "profile": profile, "expected": expected}


def encoded_case(item: dict[str, Any]) -> list[int]:
    profile = item["profile"]
    ids = profile["ids"]
    objects = profile["objects"]
    expected = item["expected"]
    context = int(expected["context"])
    key_base, value_base = PLANE_BASES[context]
    values = [0] * CASE_WORDS
    values[:28] = [
        38,
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
        context - 1,
        context,
        int(expected.get("mutation", MUTATION_NONE)),
        int(expected["stall_mode"]),
        int(expected["failed"]),
        int(expected["trap_class"]),
        int(expected["refusal_reason"]),
        int(expected["records_checked"]),
        int(expected["memory_reads"]),
        int(expected["writes"]),
        int(expected["score_multiplies"]),
        int(expected["exponentials"]),
        int(expected["value_multiplies"]),
        int(expected["gqa_executed"]),
    ]
    values[28] = key_base
    values[29] = value_base
    # The late-fault mutation fires on the last value multiply of its case.
    values[30] = context * OUTPUT_WORDS - 1
    return [value & 0xFFFFFFFF for value in values]


def build(output: Path = OUTPUT_ROOT) -> dict[str, Any]:
    rom, hbm = read_profile()
    query, current_key, current_value = authentic_activations()
    key_planes: dict[int, list[list[int]]] = {}
    value_planes: dict[int, list[list[int]]] = {}
    expected_by_context: dict[int, list[int]] = {}
    for context in CONTEXTS:
        key_planes[context] = rows_from_current(
            current_key, value_plane=False, context=context
        )
        value_planes[context] = rows_from_current(
            current_value, value_plane=True, context=context
        )
        expected_by_context[context] = expected_attention(
            query, key_planes[context], value_planes[context], context=context
        )

    first = CONTEXTS[0]
    cases = [
        case(
            "rom_pc38_gqa_exact",
            copy.deepcopy(rom),
            success(stalls=False, context=first),
        ),
        case(
            "hbm_pc38_gqa_backpressure",
            copy.deepcopy(hbm),
            success(stalls=True, context=first),
        ),
        case(
            "rom_pc38_late_value_nonfinite",
            copy.deepcopy(rom),
            refusal(
                TRAP_ENGINE,
                REFUSAL_ENGINE,
                7,
                memory_reads=QUERY_WORDS + 2 * first * OUTPUT_WORDS,
                score_multiplies=first * OUTPUT_WORDS,
                exponentials=first * QUERY_HEADS,
                value_multiplies=first * OUTPUT_WORDS,
                mutation=MUTATION_LATE_VALUE_NONFINITE,
                context=first,
            ),
        ),
    ]
    # The second and third generated tokens: the same records, the same
    # oracle, one more committed KV row each.  Under the previous constant
    # context these were a DESCRIPTOR refusal and no arithmetic at all.
    for context in CONTEXTS[1:]:
        cases.append(
            case(
                f"rom_pc38_gqa_exact_context{context}",
                copy.deepcopy(rom),
                success(stalls=False, context=context),
            )
        )

    wrong_numeric = copy.deepcopy(hbm)
    descriptor = copy.deepcopy(wrong_numeric["decoded"]["numeric"])
    digest = bytearray(descriptor.payload["contract_digest"])
    digest[-1] ^= 1
    descriptor.payload["contract_digest"] = bytes(digest)
    wrong_numeric["records"]["numeric"] = descriptor.encode()
    cases.append(
        case(
            "hbm_pc38_wrong_numeric_valid_crc",
            wrong_numeric,
            refusal(TRAP_DESCRIPTOR, REFUSAL_DESCRIPTOR, 7),
        )
    )

    corrupt_instruction = copy.deepcopy(rom)
    damaged = bytearray(corrupt_instruction["instruction_record"])
    damaged[-1] ^= 1
    corrupt_instruction["instruction_record"] = bytes(damaged)
    cases.append(
        case(
            "rom_pc38_instruction_crc_corrupt",
            corrupt_instruction,
            refusal(TRAP_INTEGRITY, REFUSAL_INTEGRITY, 0),
        )
    )

    output.mkdir(parents=True, exist_ok=True)
    images: dict[str, str] = {
        "cases.hex": scatter.hex_lines(
            [word for item in cases for word in encoded_case(item)]
        ),
        "instruction.hex": scatter.hex_lines(
            [
                int.from_bytes(item["profile"]["instruction_record"], "little")
                for item in cases
            ],
            256,
        ),
        "source.hex": scatter.hex_lines(
            query
            + [
                word
                for context in CONTEXTS
                for plane in (key_planes[context], value_planes[context])
                for row in plane
                for word in row
            ]
        ),
        "expected.hex": scatter.hex_lines(
            [
                word
                for item in cases
                for word in expected_by_context[int(item["expected"]["context"])]
            ]
        ),
    }
    for name in ("operator", "view0", "view1", "view2", "view3", "output", "numeric"):
        images[f"{name}.hex"] = scatter.hex_lines(
            [
                int.from_bytes(
                    scatter.padded_record(item["profile"]["records"].get(name, b"")),
                    "little",
                )
                for item in cases
            ],
            1536,
        )
    for name, payload in images.items():
        (output / name).write_text(payload, encoding="ascii")

    def payload_digest(values: list[int]) -> str:
        return sha256_bytes(struct.pack(f"<{len(values)}H", *values))

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "request": {
            "pc": 38,
            "contexts": list(CONTEXTS),
            "position_starts": [context - 1 for context in CONTEXTS],
            "query_shape": [1, QUERY_HEADS, HEAD_WIDTH],
            "kv_shapes": {
                str(context): [context, KV_HEADS, HEAD_WIDTH]
                for context in CONTEXTS
            },
            "output_shape": [1, QUERY_HEADS, HEAD_WIDTH],
            "memory_bases": {
                "query": QUERY_BASE,
                "planes": {
                    str(context): {
                        "key": PLANE_BASES[context][0],
                        "value": PLANE_BASES[context][1],
                    }
                    for context in CONTEXTS
                },
                "output": OUTPUT_BASE,
                "source_words": SOURCE_WORDS,
            },
        },
        "authentic_current_activations": {
            "query_pc26_bf16_sha256": payload_digest(query),
            "key_pc29_bf16_sha256": payload_digest(current_key),
            "value_pc17_bf16_sha256": payload_digest(current_value),
        },
        "history": {
            "authentic": False,
            "row_counts": {
                str(context): context - 1 for context in CONTEXTS
            },
            "construction": (
                "deterministic head rotation, element rotation, and reversal "
                "of the authentic current key/value row"
            ),
            "key_bf16_sha256": {
                str(context): payload_digest(
                    [word for row in key_planes[context][:-1] for word in row]
                )
                for context in CONTEXTS
            },
            "value_bf16_sha256": {
                str(context): payload_digest(
                    [word for row in value_planes[context][:-1] for word in row]
                )
                for context in CONTEXTS
            },
        },
        "oracle": {
            "implementation": "runtime/reference/tensor_accelerator_attention.py",
            "independent_of_dut": True,
            "expected_bf16_sha256": {
                str(context): payload_digest(expected_by_context[context])
                for context in CONTEXTS
            },
            "word_count": OUTPUT_WORDS * len(cases),
        },
        "cases": [
            {
                "name": item["name"],
                "target": item["profile"]["target"]["key"],
                "operator_descriptor_id": item["profile"]["ids"]["operator"],
                "expected": item["expected"],
            }
            for item in cases
        ],
        # The exact simulator PASS marker, derived here rather than pinned in
        # the runner: 17 named per-case checks plus one per output word.
        "expected_pass": {
            "cases": len(cases),
            "positive": sum(
                1 for item in cases if item["expected"]["compare_output"]
            ),
            "words": OUTPUT_WORDS * sum(
                1 for item in cases if item["expected"]["compare_output"]
            ),
            "checks": len(cases) * (17 + OUTPUT_WORDS),
        },
        "claim_boundary": {
            "exact_rom_and_hbm_pc38_records": True,
            "exact_pc38_gqa_arithmetic": True,
            "exact_computed_words": True,
            "independent_arithmetic_oracle": True,
            "memory_input_backpressure": True,
            "output_backpressure_and_stability": True,
            "late_fault_zero_writes": True,
            "authentic_current_query_key_value": True,
            "runtime_context_length": True,
            "contexts_covered": list(CONTEXTS),
            "authentic_prior_context_kv": False,
            "complete_layer": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_token_commit_ticks": False,
            "tpot": False,
        },
        "upstream_dependency": {
            "prefix_manifest": str(scatter.PREFIX_MANIFEST.relative_to(ROOT)),
            "prefix_manifest_sha256": sha256_file(scatter.PREFIX_MANIFEST),
            "prefix_expected": str(scatter.PREFIX_EXPECT.relative_to(ROOT)),
            "prefix_expected_sha256": sha256_file(scatter.PREFIX_EXPECT),
            "prefix_campaign": str(scatter.PREFIX_CAMPAIGN.relative_to(ROOT)),
            "prefix_campaign_sha256": sha256_file(scatter.PREFIX_CAMPAIGN),
        },
    }
    manifest["image_sha256"] = {
        name: sha256_file(output / name)
        for name in VECTOR_FILES
        if name != "index.json"
    }
    (output / "index.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
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
        "built ABI3 Qwen GQA vectors "
        f"cases={len(manifest['cases'])} words={manifest['oracle']['word_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
