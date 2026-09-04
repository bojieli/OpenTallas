#!/usr/bin/env python3
"""Build exact ABI 3.0 Qwen PC41 output-projection RTL vectors.

The input row is the retained PC38 context-17 GQA result.  The complete
layer-zero ``o_proj`` BF16 checkpoint tensor is authenticated through the
frozen checkpoint lock but is not copied into Git; the RTL campaign stages it
into a temporary binary file.  Expected words use the optimized ascending-K
binary32-RNE implementation, with independently implemented scalar checks on
32 spread output rows.

This is a bounded intermediate-tensor witness.  The preceding synthetic KV
history remains synthetic, and no token, EOS, architectural tick, or TPOT claim
follows from these vectors.
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

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    LockedCheckpointReader,
    load_checkpoint_lock,
)
from runtime.reference.tensor_accelerator_bf16 import (  # noqa: E402
    dense_bf16_linear_selected_rows_bf16,
)
from runtime.tensor_accelerator.bf16 import dense_bf16_linear_bf16  # noqa: E402
from tools import build_a3_qwen_kv_scatter_vectors as deployment  # noqa: E402


OUTPUT_ROOT = ROOT / "testdata/rtl/a3_qwen_output_projection"
GQA_VECTOR_ROOT = ROOT / "testdata/rtl/a3_qwen_gqa"
GQA_MANIFEST = GQA_VECTOR_ROOT / "index.json"
GQA_EXPECTED = GQA_VECTOR_ROOT / "expected.hex"
GQA_CAMPAIGN = ROOT / "results/rtl/a3_qwen_gqa_campaign.json"
CHECKPOINT_LOCK = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/source/checkpoint.lock.json"
)
CHECKPOINT = Path(
    "~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
).expanduser()
WEIGHT_NAME = "model.layers.0.self_attn.o_proj.weight"

SCHEMA = "opentallas.rtl.a3_qwen_output_projection_vectors.v1"
CASE_WORDS = 32
WIDTH = 4096
INPUT_BASE = 0
WEIGHT_BASE = WIDTH
OUTPUT_BASE = 0
INPUT_READS = WIDTH
WEIGHT_READS = WIDTH * WIDTH
TOTAL_READS = INPUT_READS + WEIGHT_READS
CONTRACT = hashlib.sha256(b"bf16_bf16_fp32_blocked_rne_v1").digest()
EXPECTED_INPUT_SHA256 = (
    "8992e9d1a0b5303b81b2503df2e23170f838f772e79eb8d7c65c1fce4fac93c2"
)
EXPECTED_WEIGHT_SHA256 = (
    "d6fec091373ead7a102c480d4642a9b135e9e2cf0d0c289e0425967c96877ac2"
)
EXPECTED_OUTPUT_SHA256 = (
    "018f52e0834dbe624493704eea505c7d96be52463a82a12e448b8faefd749262"
)
CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)
SCALAR_ROWS = tuple(sorted({0, 1, 2, 3, 127, 128, 255, 256, 511, 512, 1023,
                            1024, 1535, 1536, 2047, 2048, 2559, 2560, 3071,
                            3072, 3583, 3584, 3967, 3968, 4031, 4032, 4063,
                            4064, 4087, 4088, 4094, 4095}))

TRAP_NONE = 0
TRAP_INTEGRITY = 2
TRAP_DESCRIPTOR = 3
TRAP_ENGINE = 8
REFUSAL_NONE = 0
REFUSAL_INTEGRITY = 2
REFUSAL_DESCRIPTOR = 3
REFUSAL_ENGINE = 5

MUTATION_NONE = 0
MUTATION_LATE_WEIGHT_NONFINITE = 1

VECTOR_FILES = (
    "cases.hex",
    "instruction.hex",
    "operator.hex",
    "view0.hex",
    "view1.hex",
    "output.hex",
    "numeric.hex",
    "input.hex",
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


def payload(values: np.ndarray[Any, Any] | list[int]) -> bytes:
    return np.ascontiguousarray(values, dtype="<u2").tobytes(order="C")


def read_profiles() -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = json.loads(deployment.DEPLOYMENT_MANIFEST.read_text())
    descriptors = deployment.read_hex(deployment.DESCRIPTOR_IMAGE)
    programs = deployment.read_hex(deployment.PROGRAM_IMAGE)
    bases = deployment.deployment_bases(manifest)
    profiles: list[dict[str, Any]] = []
    expected = (
        {
            "operator": 134,
            "view0": 130,
            "view1": 131,
            "output": 132,
            "numeric": 57,
            "object0": 45,
            "object1": 12,
            "output_object": 55,
            "wait": 135,
            "schedule": 133,
            "counter": 40,
            "activation_loop": 129,
            "layer_loop": 19,
        },
        {
            "operator": 137,
            "view0": 134,
            "view1": 135,
            "output": 136,
            "numeric": 70,
            "object0": 19,
            "object1": 7,
            "output_object": 20,
            "wait": 138,
            "schedule": 71,
            "counter": 47,
            "activation_loop": 133,
            "layer_loop": 56,
        },
    )
    for target, identity in zip(deployment.TARGETS, expected, strict=True):
        profile = deployment.selected_operation(
            target=target,
            pc=41,
            manifest=manifest,
            descriptors=descriptors,
            programs=programs,
            bases=bases,
        )
        instruction = profile["instruction"]
        op = profile["decoded"]["operator"].payload
        numeric = profile["decoded"]["numeric"].payload
        view0 = profile["decoded"]["view0"].payload
        view1 = profile["decoded"]["view1"].payload
        out = profile["decoded"]["output"].payload
        if (
            profile["deployment"].get("verifier_errors")
            or instruction.mnemonic != "TENSOR.MATMUL"
            or int(instruction.flags) != 12
            or int(instruction.source_operation_id) != 14
            or int(instruction.wait_set_id) != identity["wait"]
            or int(instruction.signal_event_id) != 13
            or profile["ids"]
            != {
                "operator": identity["operator"],
                "view0": identity["view0"],
                "view1": identity["view1"],
                "view2": 0xFFFFFFFF,
                "view3": 0xFFFFFFFF,
                "output": identity["output"],
                "numeric": identity["numeric"],
            }
            or profile["objects"]
            != {
                "view0": identity["object0"],
                "view1": identity["object1"],
                "view2": 0xFFFFFFFF,
                "view3": 0xFFFFFFFF,
                "output": identity["output_object"],
            }
            or int(op["schedule_id"]) != identity["schedule"]
            or int(op["counter_class_id"]) != identity["counter"]
            or [int(view0[f"dim{i}"]) for i in range(2)] != [512, WIDTH]
            or [int(view1[f"dim{i}"]) for i in range(2)] != [WIDTH, WIDTH]
            or [int(out[f"dim{i}"]) for i in range(2)] != [512, WIDTH]
            or [int(view0[f"stride{i}"]) for i in range(2)] != [WIDTH, 1]
            or [int(view1[f"stride{i}"]) for i in range(2)] != [WIDTH, 1]
            or [int(out[f"stride{i}"]) for i in range(2)] != [WIDTH, 1]
            or int(view0["term0_index"]) != identity["activation_loop"]
            or int(view1["term0_index"]) != identity["layer_loop"]
            or int(out["term0_index"]) != identity["activation_loop"]
            or int(view0["term0_stride"]) != 512 * WIDTH
            or int(view1["term0_stride"]) != WIDTH * WIDTH
            or int(out["term0_stride"]) != 512 * WIDTH
            or [int(numeric[name]) for name in (
                "input_dtype", "second_input_dtype", "accumulator_dtype",
                "output_dtype", "rounding_mode", "reduction_order",
                "saturate", "nan_policy", "epsilon_bits", "scale_bits", "flags",
            )] != [16, 16, 18, 16, 0, 2, 0, 0, 0, 0, 0]
            or bytes(numeric["contract_digest"]) != CONTRACT
        ):
            raise RuntimeError(f"{target['key']} PC41 profile changed")
        profile["identity"] = identity
        profiles.append(profile)
    return profiles[0], profiles[1]


def read_input() -> np.ndarray[Any, np.dtype[np.uint16]]:
    manifest = json.loads(GQA_MANIFEST.read_text())
    campaign = json.loads(GQA_CAMPAIGN.read_text())
    if (
        manifest.get("claim_boundary", {}).get("exact_pc38_gqa_arithmetic") is not True
        or manifest.get("claim_boundary", {}).get("model_token_generation") is not False
        or manifest.get("history", {}).get("authentic") is not False
        or campaign.get("status") != "pass"
        or campaign.get("scope", {}).get("exact_pc38_gqa_arithmetic") is not True
        or campaign.get("scope", {}).get("model_token_generation") is not False
        or campaign.get("vector_sha256", {}).get("expected.hex")
        != sha256_file(GQA_EXPECTED)
    ):
        raise RuntimeError("upstream bounded PC38 evidence is not passing")
    values = np.asarray(deployment.read_hex(GQA_EXPECTED), dtype=np.uint16)
    if values.shape != (WIDTH,) or sha256_bytes(payload(values)) != EXPECTED_INPUT_SHA256:
        raise RuntimeError("retained PC38 output changed")
    return values


def read_weight() -> tuple[np.ndarray[Any, np.dtype[np.uint16]], dict[str, Any]]:
    lock = load_checkpoint_lock(CHECKPOINT_LOCK)
    if lock.get("lock_id") != CHECKPOINT_LOCK_ID:
        raise RuntimeError("Qwen checkpoint lock changed")
    raw = bytearray()
    with LockedCheckpointReader(CHECKPOINT, lock) as reader:
        record = reader.consume_tensor_payload(WEIGHT_NAME, raw.extend)
    if (
        record.get("dtype") != "BF16"
        or record.get("shape") != [WIDTH, WIDTH]
        or record.get("size_bytes") != 2 * WIDTH * WIDTH
        or record.get("payload_sha256") != EXPECTED_WEIGHT_SHA256
        or len(raw) != 2 * WIDTH * WIDTH
        or sha256_bytes(raw) != EXPECTED_WEIGHT_SHA256
    ):
        raise RuntimeError("Qwen layer-zero output-projection weight changed")
    return np.frombuffer(raw, dtype="<u2").reshape(WIDTH, WIDTH), {
        **record,
        "checkpoint": str(CHECKPOINT),
        "checkpoint_revision": CHECKPOINT.name,
        "checkpoint_lock": str(CHECKPOINT_LOCK.relative_to(ROOT)),
        "checkpoint_lock_id": CHECKPOINT_LOCK_ID,
        "checkpoint_lock_sha256": sha256_file(CHECKPOINT_LOCK),
        "authentication_boundary": (
            "all 16,777,216 BF16 codes in the complete 32-MiB tensor are "
            "read and authenticated; campaign staging independently re-reads it"
        ),
    }


def exact_output(
    input_codes: np.ndarray[Any, Any], weight_codes: np.ndarray[Any, Any]
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], str]:
    optimized = dense_bf16_linear_bf16(
        input_codes.reshape(1, WIDTH),
        weight_codes,
        input_tile_rows=1,
        output_tile_rows=64,
    )
    if optimized.output_saturated_element_count != 0:
        raise RuntimeError("output projection unexpectedly saturated")
    result = np.ascontiguousarray(optimized.values[0], dtype=np.uint16)
    if sha256_bytes(payload(result)) != EXPECTED_OUTPUT_SHA256:
        raise RuntimeError("output-projection oracle changed")
    scalar = dense_bf16_linear_selected_rows_bf16(
        [input_codes.tolist()],
        weight_codes[list(SCALAR_ROWS)].tolist(),
        output_row_indices=SCALAR_ROWS,
        declared_output_count=WIDTH,
    )
    expected_scalar = tuple(int(result[index]) for index in SCALAR_ROWS)
    if scalar.output_saturated_element_count != 0 or scalar.values != (expected_scalar,):
        raise RuntimeError("independent scalar rows differ from optimized oracle")
    return result, sha256_bytes(struct.pack(f"<{len(SCALAR_ROWS)}H", *expected_scalar))


def success(*, stalls: bool) -> dict[str, int | bool]:
    return {
        "failed": False,
        "trap_class": TRAP_NONE,
        "refusal_reason": REFUSAL_NONE,
        "records_checked": 5,
        "memory_reads": TOTAL_READS,
        "input_reads": INPUT_READS,
        "weight_reads": WEIGHT_READS,
        "macs": WEIGHT_READS,
        "writes": WIDTH,
        "saturations": 0,
        "projection_executed": True,
        "compare_output": True,
        "stall_mode": int(stalls),
        "mutation": MUTATION_NONE,
    }


def refusal(
    trap: int,
    reason: int,
    records: int,
    *,
    reads: int = 0,
    input_reads: int = 0,
    weight_reads: int = 0,
    macs: int = 0,
    mutation: int = MUTATION_NONE,
    stalls: bool = True,
) -> dict[str, int | bool]:
    return {
        "failed": True,
        "trap_class": trap,
        "refusal_reason": reason,
        "records_checked": records,
        "memory_reads": reads,
        "input_reads": input_reads,
        "weight_reads": weight_reads,
        "macs": macs,
        "writes": 0,
        "saturations": 0,
        "projection_executed": False,
        "compare_output": False,
        "stall_mode": int(stalls),
        "mutation": mutation,
    }


def encoded_case(item: dict[str, Any]) -> list[int]:
    profile = item["profile"]
    ids = profile["ids"]
    objects = profile["objects"]
    expected = item["expected"]
    values = [0] * CASE_WORDS
    values[:29] = [
        41,
        int(profile["deployment"]["instruction_count"]),
        int(ids["operator"]),
        int(ids["view0"]),
        int(ids["view1"]),
        int(ids["output"]),
        int(ids["numeric"]),
        int(objects["view0"]),
        int(objects["view1"]),
        int(objects["output"]),
        16,
        17,
        int(expected["mutation"]),
        int(expected["stall_mode"]),
        int(expected["failed"]),
        int(expected["trap_class"]),
        int(expected["refusal_reason"]),
        int(expected["records_checked"]),
        int(expected["memory_reads"]),
        int(expected["input_reads"]),
        int(expected["weight_reads"]),
        int(expected["macs"]),
        int(expected["writes"]),
        int(expected["saturations"]),
        int(expected["projection_executed"]),
        int(expected["compare_output"]),
        int(profile["target"]["profile"]),
        INPUT_BASE,
        WEIGHT_BASE,
    ]
    values[29] = OUTPUT_BASE
    return [value & 0xFFFFFFFF for value in values]


def case(name: str, profile: dict[str, Any], expected: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "profile": profile, "expected": expected}


def build(output: Path = OUTPUT_ROOT) -> dict[str, Any]:
    rom, hbm = read_profiles()
    input_codes = read_input()
    weights, weight_source = read_weight()
    expected_codes, scalar_digest = exact_output(input_codes, weights)

    cases = [
        case("rom_pc41_output_projection_exact", copy.deepcopy(rom), success(stalls=False)),
        case("hbm_pc41_output_projection_backpressure", copy.deepcopy(hbm), success(stalls=True)),
        case(
            "rom_pc41_late_weight_nonfinite",
            copy.deepcopy(rom),
            refusal(
                TRAP_ENGINE,
                REFUSAL_ENGINE,
                5,
                reads=TOTAL_READS,
                input_reads=INPUT_READS,
                weight_reads=WEIGHT_READS,
                macs=WEIGHT_READS,
                mutation=MUTATION_LATE_WEIGHT_NONFINITE,
                stalls=False,
            ),
        ),
    ]

    wrong_numeric = copy.deepcopy(hbm)
    numeric = copy.deepcopy(wrong_numeric["decoded"]["numeric"])
    digest = bytearray(numeric.payload["contract_digest"])
    digest[-1] ^= 1
    numeric.payload["contract_digest"] = bytes(digest)
    wrong_numeric["records"]["numeric"] = numeric.encode()
    cases.append(
        case(
            "hbm_pc41_wrong_numeric_valid_crc",
            wrong_numeric,
            refusal(TRAP_DESCRIPTOR, REFUSAL_DESCRIPTOR, 5),
        )
    )

    wrong_output = copy.deepcopy(rom)
    output_view = copy.deepcopy(wrong_output["decoded"]["output"])
    output_view.payload["dim1"] = WIDTH - 1
    wrong_output["records"]["output"] = output_view.encode()
    cases.append(
        case(
            "rom_pc41_wrong_output_shape_valid_crc",
            wrong_output,
            refusal(TRAP_DESCRIPTOR, REFUSAL_DESCRIPTOR, 5),
        )
    )

    corrupt_instruction = copy.deepcopy(rom)
    damaged = bytearray(corrupt_instruction["instruction_record"])
    damaged[-1] ^= 1
    corrupt_instruction["instruction_record"] = bytes(damaged)
    cases.append(
        case(
            "rom_pc41_instruction_crc_corrupt",
            corrupt_instruction,
            refusal(TRAP_INTEGRITY, REFUSAL_INTEGRITY, 0),
        )
    )

    output.mkdir(parents=True, exist_ok=True)
    images: dict[str, str] = {
        "cases.hex": deployment.hex_lines(
            [word for item in cases for word in encoded_case(item)]
        ),
        "instruction.hex": deployment.hex_lines(
            [
                int.from_bytes(item["profile"]["instruction_record"], "little")
                for item in cases
            ],
            256,
        ),
        "input.hex": deployment.hex_lines([int(value) for value in input_codes]),
        "expected.hex": deployment.hex_lines([int(value) for value in expected_codes]),
    }
    for name in ("operator", "view0", "view1", "output", "numeric"):
        images[f"{name}.hex"] = deployment.hex_lines(
            [
                int.from_bytes(
                    deployment.padded_record(item["profile"]["records"][name]),
                    "little",
                )
                for item in cases
            ],
            1536,
        )
    for name, contents in images.items():
        (output / name).write_text(contents, encoding="ascii")

    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "request": {
            "pc": 41,
            "position_start": 16,
            "context_length": 17,
            "input_shape": [1, WIDTH],
            "weight_shape": [WIDTH, WIDTH],
            "output_shape": [1, WIDTH],
            "input_base_words": INPUT_BASE,
            "weight_base_words": WEIGHT_BASE,
            "output_base_words": OUTPUT_BASE,
        },
        "numeric": {
            "contract": "bf16_bf16_fp32_blocked_rne_v1",
            "contract_sha256": CONTRACT.hex(),
            "executed_association": "single_lane_strictly_ascending_k_v1",
            "product_rounding": "binary32_rne",
            "accumulation_rounding": "binary32_rne_after_each_add",
            "output_rounding": "bf16_rne_once",
        },
        "input": {
            "source": "retained exact PC38 bounded GQA output",
            "bf16_sha256": EXPECTED_INPUT_SHA256,
            "word_count": WIDTH,
            "authentic_current_qkv": True,
            "authentic_prior_context_kv": False,
            "upstream_manifest": str(GQA_MANIFEST.relative_to(ROOT)),
            "upstream_manifest_sha256": sha256_file(GQA_MANIFEST),
            "upstream_campaign": str(GQA_CAMPAIGN.relative_to(ROOT)),
            "upstream_campaign_sha256": sha256_file(GQA_CAMPAIGN),
        },
        "weight": weight_source,
        "oracle": {
            "implementation": "runtime/tensor_accelerator/bf16.py",
            "expected_bf16_sha256": EXPECTED_OUTPUT_SHA256,
            "word_count": WIDTH,
            "independent_scalar_implementation": (
                "runtime/reference/tensor_accelerator_bf16.py"
            ),
            "independent_scalar_row_indices": list(SCALAR_ROWS),
            "independent_scalar_row_count": len(SCALAR_ROWS),
            "independent_scalar_expected_sha256": scalar_digest,
            "full_output_independently_scalar_checked": False,
        },
        "profiles": [
            {
                "target": profile["target"]["key"],
                "deployment_sha256": profile["deployment"]["deployment_sha256"],
                "ids": profile["ids"],
                "objects": profile["objects"],
                "descriptor_sha256": {
                    name: sha256_bytes(record)
                    for name, record in profile["records"].items()
                    if record
                },
            }
            for profile in (rom, hbm)
        ],
        "cases": [
            {
                "name": item["name"],
                "target": item["profile"]["target"]["key"],
                "expected": item["expected"],
            }
            for item in cases
        ],
        "claim_boundary": {
            "exact_rom_and_hbm_pc41_records": True,
            "complete_layer_zero_output_projection": True,
            "complete_checkpoint_weight_tensor_authenticated": True,
            "strictly_ascending_k_association": True,
            "exact_computed_words": True,
            "full_output_independently_scalar_checked": False,
            "independent_scalar_rows_checked": len(SCALAR_ROWS),
            "memory_input_backpressure": True,
            "output_backpressure_and_stability": True,
            "late_fault_zero_writes": True,
            "authentic_prior_context_kv": False,
            "complete_layer": False,
            "model_token_generation": False,
            "eos": False,
            "architectural_token_commit_ticks": False,
            "tpot": False,
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
        "built ABI3 Qwen PC41 output-projection vectors "
        f"cases={len(manifest['cases'])} words={manifest['oracle']['word_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
