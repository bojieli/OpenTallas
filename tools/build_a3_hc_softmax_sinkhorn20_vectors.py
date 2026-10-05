#!/usr/bin/env python3
"""Build exact independent vectors for composed HC softmax/Sinkhorn RTL.

The input corpus is the already retained set of affine combination logits.  It
contains every matrix from the first T=512 and final T=320 blocks of the exact
200,000-token DeepSeek workload, a T=1 witness, and directed refusal/boundary
cases.  Expected outputs are recomputed by composing two independent exact
oracles: Fraction/integer-RNE stable softmax with exact-interval CR32 exp, then
the Fraction/integer-RNE 20-stage Sinkhorn sequence.

No service-engine or RTL arithmetic is imported.  The first 512 final matrices
must also reproduce the separately retained authenticated HC_PRE functional
output.  This is operator arithmetic evidence only, never token or TPOT proof.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_a3_hc_numeric_vectors as numeric_vectors  # noqa: E402
from tools import build_a3_hc_stable_softmax_vectors as softmax_vectors  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    DESCRIPTOR_HEADER,
    Descriptor,
)
from runtime.abi3.records import Instruction  # noqa: E402


SOFTMAX_VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_stable_softmax"
DEPLOYMENT_VECTOR_ROOT = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_MANIFEST = DEPLOYMENT_VECTOR_ROOT / "abi3_deployment_rtl_vectors.json"
DESCRIPTOR_IMAGE = DEPLOYMENT_VECTOR_ROOT / "a3_descriptor.hex"
PROGRAM_IMAGE = DEPLOYMENT_VECTOR_ROOT / "a3_program.hex"
QUALIFIED_T512_COMBINATION = (
    ROOT
    / "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le"
)
QUALIFICATION_RESULT = (
    ROOT / "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json"
)
QUALIFICATION_VECTOR = (
    ROOT / "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json"
)
DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_hc_softmax_sinkhorn20"

SCHEMA = "opentallas.rtl.a3_hc_softmax_sinkhorn20_vectors.v1"
MAGIC = 0xA3C5_2020
VERSION = 1
ERR_NONE = 0
EXPECTED_WORDS = 17
DESCRIPTOR_PREFIX_BYTES = 192
GENERATED_VECTOR_FILES = ("meta.hex", "matrix_expected.hex", "index.json")


def canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def u32le(values: Iterable[int]) -> bytes:
    return b"".join(struct.pack("<I", int(value)) for value in values)


def hex_image(values: Iterable[int]) -> bytes:
    return "".join(f"{int(value) & 0xFFFFFFFF:08x}\n" for value in values).encode(
        "ascii"
    )


def validate_vector_id(manifest: dict[str, Any], label: str) -> None:
    expected = manifest.get("vector_set_id")
    body = dict(manifest)
    body.pop("vector_set_id", None)
    if expected != sha256_bytes(canonical(body)):
        raise ValueError(f"{label} vector-set identity drift")


def validate_record_digest(
    record: dict[str, Any], field: str, label: str
) -> None:
    expected = record.get(field)
    body = dict(record)
    body.pop(field, None)
    encoded = json.dumps(
        body, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    if expected != sha256_bytes(encoded):
        raise ValueError(f"{label} {field} drift")


def repository_path(relative: Any, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} lacks a repository-relative path")
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT) or not path.is_file():
        raise ValueError(f"{label} is not a retained repository file: {relative}")
    return path


def read_hex(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line.strip()]


def descriptor_record(image: list[int], base: int, descriptor_id: int) -> bytes:
    prefix = image[base + descriptor_id].to_bytes(DESCRIPTOR_PREFIX_BYTES, "little")
    header = DESCRIPTOR_HEADER.decode(prefix[:64])
    total = int(header["total_bytes"])
    if total > DESCRIPTOR_PREFIX_BYTES:
        raise ValueError(
            f"descriptor {descriptor_id} exceeds the retained prefix"
        )
    return prefix[:total]


def deployment_bases(manifest: dict[str, Any]) -> dict[str, tuple[int, int]]:
    descriptor_base = 0
    program_base = 0
    result: dict[str, tuple[int, int]] = {}
    for deployment in manifest["deployments"]:
        result[deployment["key"]] = (descriptor_base, program_base)
        descriptor_base += int(deployment["descriptor_count"])
        program_base += int(deployment["instruction_count"])
    return result


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {key: json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def load_descriptor_binding(
    checkpoint_manifest: dict[str, Any], qualified_t512: bytes
) -> tuple[dict[str, Any], bytes, tuple[Path, ...]]:
    manifest_bytes = DEPLOYMENT_MANIFEST.read_bytes()
    manifest = json.loads(manifest_bytes)
    if manifest.get("schema") != "opentallas.rtl.abi3_deployment_vectors.v1":
        raise ValueError("current ABI deployment-vector schema drift")
    for filename, path in (
        ("a3_descriptor.hex", DESCRIPTOR_IMAGE),
        ("a3_program.hex", PROGRAM_IMAGE),
    ):
        if sha256_file(path) != manifest["image_sha256"][filename]:
            raise ValueError(f"current ABI deployment image drift: {filename}")

    descriptor_image = read_hex(DESCRIPTOR_IMAGE)
    program_image = read_hex(PROGRAM_IMAGE)
    bases = deployment_bases(manifest)
    expected_sites = {
        "deepseek-v4-flash-hbm-cluster": (1, 14, 545),
        "deepseek-v4-flash-rom-wafer": (0, 15, 381),
    }
    selected: dict[str, Any] = {}
    evidence_paths: set[Path] = set()
    common_numeric_payload: dict[str, Any] | None = None
    for name, (profile_id, pc, operator_id) in expected_sites.items():
        deployment = next(
            (item for item in manifest["deployments"] if item["key"] == name),
            None,
        )
        if deployment is None or deployment.get("admitted") is not True:
            raise ValueError(f"current deployment omits admitted profile {name}")
        identity_evidence = deployment.get("deployment_identity_evidence")
        if not isinstance(identity_evidence, dict):
            raise ValueError(f"current deployment lacks identity evidence: {name}")
        identity_path = repository_path(
            identity_evidence.get("artifact"), f"{name} identity evidence"
        )
        if sha256_file(identity_path) != identity_evidence.get("artifact_sha256"):
            raise ValueError(f"current deployment identity evidence drift: {name}")
        evidence_paths.add(identity_path)
        descriptor_base, program_base = bases[name]
        instruction_bytes = program_image[program_base + pc].to_bytes(32, "little")
        instruction = Instruction.decode(instruction_bytes)
        if int(instruction.descriptor_id) != operator_id:
            raise ValueError(f"current HC_PRE target site drift: {name}")
        operator_bytes = descriptor_record(
            descriptor_image, descriptor_base, operator_id
        )
        operator = Descriptor.decode(operator_bytes, operator_id)
        operator_payload = operator.payload
        numeric_id = int(operator_payload["numeric_profile_id"])
        output_id = int(operator_payload["output_view_1"])
        numeric_bytes = descriptor_record(descriptor_image, descriptor_base, numeric_id)
        output_bytes = descriptor_record(descriptor_image, descriptor_base, output_id)
        numeric = Descriptor.decode(numeric_bytes, numeric_id)
        output = Descriptor.decode(output_bytes, output_id)
        numeric_payload = numeric.payload
        output_payload = output.payload
        if (
            int(operator_payload["engine_family"]) != 48
            or int(operator_payload["engine_sub"]) != 9
            or int(operator_payload["aux_id_0"]) != 0
            or int(operator_payload["aux_id_1"]) != 20
            or int(operator_payload["aux_id_2"]) != 4
        ):
            raise ValueError(f"HC_PRE operator contract drift: {name}")
        if (
            int(numeric_payload["epsilon_bits"]) != softmax_vectors.EPSILON
            or int(numeric_payload["rounding_mode"]) != 0
            or int(numeric_payload["reduction_order"]) != 1
            or int(numeric_payload["nan_policy"]) != 0
            or int(numeric_payload["output_dtype"]) != 18
        ):
            raise ValueError(f"HC_PRE numeric contract drift: {name}")
        if (
            int(output_payload["rank"]) != 3
            or int(output_payload["dim1"]) != 4
            or int(output_payload["dim2"]) != 4
            or int(output_payload["stride1"]) != 4
            or int(output_payload["stride2"]) != 1
            or int(output_payload["dtype"]) != 18
        ):
            raise ValueError(f"HC_PRE combination output-view drift: {name}")
        if common_numeric_payload is None:
            common_numeric_payload = json_value(numeric_payload)
        elif json_value(numeric_payload) != common_numeric_payload:
            raise ValueError("ROM and HBM HC_PRE numeric descriptors differ")
        selected[name] = {
            "profile": profile_id,
            "program_counter": pc,
            "operator_descriptor_id": operator_id,
            "deployment_sha256": deployment["deployment_sha256"],
            "descriptor_table_sha256": deployment["descriptor_table_sha256"],
            "program_sha256": deployment["program_sha256"],
            "deployment_identity_evidence": deployment[
                "deployment_identity_evidence"
            ],
            "deployment_identity_evidence_hash_verified": True,
            "instruction_sha256": sha256_bytes(instruction_bytes),
            "operator_descriptor_sha256": sha256_bytes(operator_bytes),
            "numeric_descriptor_id": numeric_id,
            "numeric_descriptor_sha256": sha256_bytes(numeric_bytes),
            "combination_output_descriptor_id": output_id,
            "combination_output_descriptor_sha256": sha256_bytes(output_bytes),
            "combination_capacity_tokens": output_payload["dim0"],
        }

    qualification_bytes = QUALIFICATION_RESULT.read_bytes()
    qualification = json.loads(qualification_bytes)
    if (
        qualification.get("schema")
        != "opentallas.abi3.deepseek_hbm_hc_pre_t512_qualification.v1"
        or qualification.get("status") != "pass"
    ):
        raise ValueError("retained HC_PRE functional qualification is not passing")
    validate_record_digest(
        qualification,
        "record_sha256",
        "retained HC_PRE functional qualification",
    )

    qualification_vector_bytes = QUALIFICATION_VECTOR.read_bytes()
    qualification_vector = json.loads(qualification_vector_bytes)
    if (
        qualification_vector.get("schema")
        != "opentallas.abi3.deepseek_hbm_hc_pre_t512_vector.v1"
    ):
        raise ValueError("retained HC_PRE qualification-vector schema drift")
    validate_record_digest(
        qualification_vector,
        "manifest_sha256",
        "retained HC_PRE qualification vector",
    )
    if qualification.get("vector_manifest") != str(
        QUALIFICATION_VECTOR.relative_to(ROOT)
    ) or qualification.get("vector_manifest_sha256") != sha256_bytes(
        qualification_vector_bytes
    ):
        raise ValueError("retained HC_PRE qualification-vector link drift")

    claims = qualification.get("claims", {})
    if claims.get("all_pc14_output_words_bitwise_compared") is not True:
        raise ValueError("retained HC_PRE qualification lacks all-word comparison")
    for claim in (
        "rtl_execution",
        "model_token_generation",
        "end_to_end_decode",
        "eos",
        "architectural_timing",
        "tpot",
    ):
        if claims.get(claim) is not False:
            raise ValueError(f"retained HC_PRE qualification overclaims {claim}")

    expected_checkpoint = {
        "repository": checkpoint_manifest["checkpoint"]["repository"],
        "revision": checkpoint_manifest["checkpoint"]["revision"],
    }
    for label, record in (
        ("qualification", qualification),
        ("qualification vector", qualification_vector),
    ):
        observed_checkpoint = record.get("checkpoint", {})
        if any(
            observed_checkpoint.get(key) != value
            for key, value in expected_checkpoint.items()
        ):
            raise ValueError(f"retained HC_PRE {label} checkpoint identity drift")

    workload_fields = (
        "workload_id",
        "workload_digest",
        "prompt_token_count",
        "file_sha256",
        "rendered_text_sha256",
    )
    expected_workload = checkpoint_manifest["workload"]
    for label, record in (
        ("qualification", qualification),
        ("qualification vector", qualification_vector),
    ):
        observed_workload = record.get("workload", {})
        if any(
            observed_workload.get(field) != expected_workload[field]
            for field in workload_fields
        ):
            raise ValueError(f"retained HC_PRE {label} workload identity drift")

    first_segment = checkpoint_manifest["segments"][0]
    for label, record in (
        ("qualification", qualification),
        ("qualification vector", qualification_vector),
    ):
        observed_workload = record["workload"]
        if (
            observed_workload.get("first_issue_token_count")
            != first_segment["token_count"]
            or observed_workload.get("first_issue_token_ids_u32le_sha256")
            != first_segment["token_ids_u32le_sha256"]
        ):
            raise ValueError(f"retained HC_PRE {label} first-issue identity drift")

    combination = qualification_vector.get("expected_outputs", {}).get(
        "combination", {}
    )
    combination_relative = QUALIFICATION_VECTOR.parent.relative_to(ROOT) / str(
        combination.get("path")
    )
    combination_path = repository_path(
        str(combination_relative),
        "retained HC_PRE expected combination",
    )
    qualified_t512_sha256 = sha256_bytes(qualified_t512)
    if (
        combination_path != QUALIFIED_T512_COMBINATION.resolve()
        or combination.get("dtype") != "u32le"
        or combination.get("shape") != [512, 4, 4]
        or combination.get("bytes") != len(qualified_t512)
        or combination.get("sha256") != qualified_t512_sha256
        or sha256_file(combination_path) != qualified_t512_sha256
    ):
        raise ValueError("retained HC_PRE expected combination identity drift")
    comparison = qualification.get("comparison", {})
    if (
        comparison.get("combination_bitwise_equal") is not True
        or comparison.get("combination_u32le_sha256") != qualified_t512_sha256
        or comparison.get("combination_word_count") != 512 * 4 * 4
        or comparison.get("mismatched_words") != 0
    ):
        raise ValueError("retained HC_PRE combination qualification drift")

    evidence_paths.update((QUALIFICATION_RESULT, QUALIFICATION_VECTOR))
    qualification_binding = {
        "path": str(QUALIFICATION_RESULT.relative_to(ROOT)),
        "sha256": sha256_bytes(qualification_bytes),
        "record_sha256": qualification["record_sha256"],
        "vector_manifest": {
            "path": str(QUALIFICATION_VECTOR.relative_to(ROOT)),
            "sha256": sha256_bytes(qualification_vector_bytes),
            "manifest_sha256": qualification_vector["manifest_sha256"],
        },
        "checkpoint": expected_checkpoint,
        "workload": {field: expected_workload[field] for field in workload_fields},
        "combination_output_sha256": qualified_t512_sha256,
        "all_output_words_bitwise_compared": True,
        "model_token_generation": False,
        "eos": False,
        "tpot": False,
    }

    return {
        "abi": {"major": 3, "minor": 0},
        "current_deployment_vector_manifest": {
            "path": str(DEPLOYMENT_MANIFEST.relative_to(ROOT)),
            "sha256": sha256_bytes(manifest_bytes),
            "descriptor_image_sha256": manifest["image_sha256"][
                "a3_descriptor.hex"
            ],
            "program_image_sha256": manifest["image_sha256"]["a3_program.hex"],
        },
        "profiles": selected,
        "numeric_contract": common_numeric_payload,
        "authenticated_functional_qualification": qualification_binding,
    }, manifest_bytes, tuple(sorted(evidence_paths))


def build(
    output: Path = DEFAULT_OUTPUT,
    softmax_root: Path = SOFTMAX_VECTOR_DIR,
) -> dict[str, Any]:
    checkpoint_matrices, checkpoint_manifest = softmax_vectors.load_checkpoint_inputs(
        softmax_root
    )
    softmax_manifest_path = softmax_root / "index.json"
    softmax_manifest_bytes = softmax_manifest_path.read_bytes()
    softmax_manifest = json.loads(softmax_manifest_bytes)
    if softmax_manifest.get("schema") != softmax_vectors.SCHEMA:
        raise ValueError("stable-softmax vector schema drift")
    if softmax_manifest.get("status") != "independent_exact_vectors":
        raise ValueError("stable-softmax vector set is not qualified input evidence")
    validate_vector_id(softmax_manifest, "stable-softmax")

    cases: list[tuple[str, str, tuple[int, ...]]] = []
    for index, matrix in enumerate(checkpoint_matrices):
        segment = "checkpoint_first_t512" if index < 512 else "checkpoint_final_t320"
        position = index if index < 512 else index - 512
        cases.append((f"{segment}_{position}", segment, matrix))
    cases.extend(softmax_vectors.directed_matrices())

    input_words = [word for _, _, matrix in cases for word in matrix]
    retained_input_path = softmax_root / "matrix_input.hex"
    retained_input = retained_input_path.read_bytes()
    if retained_input != hex_image(input_words):
        raise ValueError("composed corpus differs from retained stable-softmax input")
    if sha256_bytes(retained_input) != softmax_manifest["files"]["matrix_input.hex"]:
        raise ValueError("retained stable-softmax input hash drift")

    results: list[tuple[int, ...]] = []
    errors: list[int] = []
    categories: Counter[str] = Counter()
    error_counts: Counter[int] = Counter()
    stable_successes = 0
    sinkhorn_successes = 0
    sinkhorn_divisions = 0
    checkpoint_outputs: list[int] = []

    for _, category, matrix in cases:
        categories[category] += 1
        stable_result, stable_error, _ = softmax_vectors.stable_softmax_oracle(matrix)
        if stable_error != ERR_NONE:
            final_result = (0,) * 16
            final_error = stable_error
        else:
            stable_successes += 1
            final_result, final_error, divisions = numeric_vectors.sinkhorn_oracle(
                stable_result
            )
            if final_error == ERR_NONE:
                sinkhorn_successes += 1
                sinkhorn_divisions += len(divisions)
        results.append(final_result)
        errors.append(final_error)
        error_counts[final_error] += 1
        if category.startswith("checkpoint_"):
            checkpoint_outputs.extend(final_result)

    checkpoint_count = len(checkpoint_matrices)
    if any(errors[:checkpoint_count]):
        raise ValueError("checkpoint-reachable composed arithmetic refused")
    if stable_successes != sinkhorn_successes:
        raise ValueError("a valid stable-softmax result failed exact Sinkhorn")
    if sinkhorn_divisions != sinkhorn_successes * 624:
        raise ValueError("composed Sinkhorn division count drift")

    qualified_t512 = QUALIFIED_T512_COMBINATION.read_bytes()
    first_payload = u32le(checkpoint_outputs[: 512 * 16])
    final_payload = u32le(checkpoint_outputs[512 * 16 :])
    checkpoint_payload = u32le(checkpoint_outputs)
    if first_payload != qualified_t512:
        raise ValueError("independent composed T=512 output differs from qualification")

    descriptor_binding, deployment_manifest_bytes, deployment_evidence_paths = (
        load_descriptor_binding(checkpoint_manifest, qualified_t512)
    )
    expected_words = [
        word
        for result, error in zip(results, errors, strict=True)
        for word in (*result, error)
    ]
    meta_words = (
        MAGIC,
        VERSION,
        len(cases),
        checkpoint_count,
        len(cases) - checkpoint_count,
        error_counts[ERR_NONE],
        len(cases) - error_counts[ERR_NONE],
        0,  # First authenticated checkpoint position is the T=1 witness.
    )

    output.mkdir(parents=True, exist_ok=True)
    (output / "meta.hex").write_bytes(hex_image(meta_words))
    (output / "matrix_expected.hex").write_bytes(hex_image(expected_words))

    source_paths = (
        Path(__file__).resolve(),
        ROOT / "tools/build_a3_hc_stable_softmax_vectors.py",
        ROOT / "tools/build_a3_hc_numeric_vectors.py",
        ROOT / "runtime/reference/hyper_connection.py",
    )
    evidence_paths = (
        softmax_manifest_path,
        DEPLOYMENT_MANIFEST,
        DESCRIPTOR_IMAGE,
        PROGRAM_IMAGE,
        QUALIFIED_T512_COMBINATION,
        *deployment_evidence_paths,
    )
    body: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "descriptor_bound_independent_exact_vectors",
        "input_words_per_case": 16,
        "expected_words_per_case": EXPECTED_WORDS,
        "counts": {
            "cases": len(cases),
            "checkpoint_cases": checkpoint_count,
            "directed_cases": len(cases) - checkpoint_count,
            "successful_cases": error_counts[ERR_NONE],
            "refused_cases": len(cases) - error_counts[ERR_NONE],
            "errors": {str(key): value for key, value in sorted(error_counts.items())},
            "categories": dict(sorted(categories.items())),
            "stable_softmax_successes": stable_successes,
            "sinkhorn_successes": sinkhorn_successes,
            "successful_sinkhorn_divisions": sinkhorn_divisions,
        },
        "input_binding": {
            "path": str(retained_input_path.relative_to(ROOT)),
            "sha256": sha256_bytes(retained_input),
            "stable_softmax_manifest_path": str(
                softmax_manifest_path.relative_to(ROOT)
            ),
            "stable_softmax_manifest_sha256": sha256_bytes(
                softmax_manifest_bytes
            ),
            "stable_softmax_vector_set_id": softmax_manifest["vector_set_id"],
        },
        "checkpoint_binding": {
            "repository": checkpoint_manifest["checkpoint"]["repository"],
            "revision": checkpoint_manifest["checkpoint"]["revision"],
            "workload_id": checkpoint_manifest["workload"]["workload_id"],
            "workload_digest": checkpoint_manifest["workload"]["workload_digest"],
            "prompt_token_count": checkpoint_manifest["workload"][
                "prompt_token_count"
            ],
            "segments": checkpoint_manifest["segments"],
            "checkpoint_output_u32le_sha256": sha256_bytes(checkpoint_payload),
            "first_t512_output": {
                "sha256": sha256_bytes(first_payload),
                "qualified_path": str(QUALIFIED_T512_COMBINATION.relative_to(ROOT)),
                "qualified_sha256": sha256_bytes(qualified_t512),
                "byte_identical_to_authenticated_functional_output": True,
            },
            "final_t320_output_u32le_sha256": sha256_bytes(final_payload),
            "t1_shape_witness": {
                "case_index": 0,
                "position": 0,
                "token_id": numeric_vectors.CHECKPOINT_TOKEN_IDS[0],
                "output_u32le_sha256": sha256_bytes(u32le(results[0])),
            },
        },
        "descriptor_binding": descriptor_binding,
        "numeric_contract": {
            "stable_softmax": "source-major row max; RN32 subtraction; CR32 nonpositive exp; balanced RN32 four-sum; RN32 divide; RN32 epsilon addition",
            "sinkhorn": "initial column normalization then nineteen row/column pairs; balanced RN32 four-sum; RN32 epsilon denominator; RN32 divide",
            "epsilon_binary32": f"{softmax_vectors.EPSILON:08x}",
            "rounding": "binary32 round-to-nearest ties-to-even after every named operation",
            "atomicity": "all sixteen final coefficients commit together or all zero with nonzero error",
        },
        "oracle": {
            "stable_softmax_binary32": "self-contained exact Fraction arithmetic and integer RNE encoding",
            "exponential": "independent exact-rational adaptive interval",
            "sinkhorn_binary32": "self-contained exact Fraction arithmetic and integer RNE encoding",
            "host_floating_point": False,
            "service_arithmetic_imported": False,
            "rtl_implementation_imported": False,
        },
        "files": {
            "meta.hex": sha256_file(output / "meta.hex"),
            "matrix_expected.hex": sha256_file(output / "matrix_expected.hex"),
        },
        "source_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in source_paths
        },
        "evidence_sha256": {
            str(path.relative_to(ROOT)): sha256_file(path) for path in evidence_paths
        },
        "current_deployment_manifest_sha256": sha256_bytes(
            deployment_manifest_bytes
        ),
        "claim_boundary": {
            "stable_softmax_sinkhorn20_composition_vectors": True,
            "first_t512_and_final_t320_checkpoint_blocks": True,
            "t1_shape_witness": True,
            "descriptor_identity_bound": True,
            "full_200k_checkpoint_domain": False,
            "full_hc_pre": False,
            "descriptor_execution": False,
            "model_token_generation": False,
            "token_correctness": False,
            "eos": False,
            "architectural_timing": False,
            "technology_timing": False,
            "tpot": False,
        },
    }
    body["vector_set_id"] = sha256_bytes(canonical(body))
    (output / "index.json").write_text(
        json.dumps(body, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--softmax-root", type=Path, default=SOFTMAX_VECTOR_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = build(args.output, args.softmax_root)
    print(
        "built composed HC softmax/Sinkhorn vectors: "
        f"{result['counts']['cases']} cases, "
        f"{result['counts']['checkpoint_cases']} checkpoint-derived, "
        f"{result['counts']['refused_cases']} refused"
    )


if __name__ == "__main__":
    main()
