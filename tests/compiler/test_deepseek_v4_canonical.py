from __future__ import annotations

import copy
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from compiler.canonical import (
    CanonicalTransformError,
    build_official_canonical_plan,
    canonicalize_source_name,
    dequantize_fp8_e8m0_matrix_to_bf16,
    fp8_e8m0_to_bf16_code,
    slice_row_major_payload,
    validate_native_mxfp4_pair,
)
from compiler.canonical.deepseek_v4 import partition_axis, routed_expert_id
from compiler.canonical.plan import DEFAULT_SOURCE
from compiler.checking import (
    DeepSeekV4TransformCheckError,
    verify_dequantized_fp8_e8m0_bf16,
    verify_native_mxfp4_identity,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json, write_canonical_json
from runtime.reference.formats import (
    NumericReferenceError,
    binary32_bits_to_bf16_rne,
    decode_e4m3fn,
    decode_e8m0,
    encode_binary32_rne,
)


ROOT = Path(__file__).resolve().parents[2]
PLAN_SCHEMA = (
    ROOT / "schemas/compiler/deepseek_v4_canonical_plan_v1.schema.json"
)
CHECK_SCHEMA = (
    ROOT / "schemas/compiler/deepseek_v4_transform_check_v1.schema.json"
)
PLAN_ID = "7b87ee6168e13cf9be7c5e812a13490b6f264bda78a96ceb2e7c02580c49b3a7"


def _reference_bf16_code(weight_code: int, scale_code: int) -> int:
    weight = decode_e4m3fn(weight_code)
    scale = decode_e8m0(scale_code)
    if (
        not weight.finite
        or weight.value is None
        or not scale.finite
        or scale.value is None
    ):
        raise NumericReferenceError("non-finite source")
    binary32 = encode_binary32_rne(weight.value * scale.value)
    bf16 = binary32_bits_to_bf16_rne(binary32)
    if bf16.saturated:
        raise NumericReferenceError("finite BF16 overflow")
    if bf16.code == 0 and weight_code & 0x80:
        return 0x8000
    return bf16.code


def _validate_check_report(report: dict[str, object]) -> None:
    schema = load_strict_json(CHECK_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report)
    body = dict(report)
    check_id = body.pop("check_id")
    assert check_id == hashlib.sha256(canonical_json_bytes(body)).hexdigest()


def test_scalar_dequantization_exhaustively_matches_independent_reference() -> None:
    accepted = 0
    rejected = 0
    for scale_code in range(0xFF):
        for weight_code in range(0x100):
            try:
                expected = _reference_bf16_code(weight_code, scale_code)
            except NumericReferenceError:
                with pytest.raises(CanonicalTransformError):
                    fp8_e8m0_to_bf16_code(weight_code, scale_code)
                rejected += 1
            else:
                assert (
                    fp8_e8m0_to_bf16_code(weight_code, scale_code)
                    == expected
                )
                accepted += 1
    assert accepted == 64_210
    assert rejected == 1_070


def test_scalar_conversion_preserves_signed_zero_and_bf16_boundaries() -> None:
    assert fp8_e8m0_to_bf16_code(0x00, 0x7F) == 0x0000
    assert fp8_e8m0_to_bf16_code(0x80, 0x7F) == 0x8000
    assert fp8_e8m0_to_bf16_code(0x01, 0x00) == 0x0000
    assert fp8_e8m0_to_bf16_code(0x81, 0x00) == 0x8000
    assert fp8_e8m0_to_bf16_code(0x08, 0x00) == 0x0001
    assert fp8_e8m0_to_bf16_code(0x08, 0x07) == 0x0080

    with pytest.raises(CanonicalTransformError, match="NaN"):
        fp8_e8m0_to_bf16_code(0x7F, 0x7F)
    with pytest.raises(CanonicalTransformError, match="reserved E8M0"):
        fp8_e8m0_to_bf16_code(0x00, 0xFF)
    with pytest.raises(CanonicalTransformError, match="overflows finite BF16"):
        fp8_e8m0_to_bf16_code(0x7E, 0xFE)


@pytest.mark.parametrize("shape", [(128, 128), (256, 256)])
def test_matrix_dequantization_matches_every_independently_checked_byte(
    shape: tuple[int, int],
) -> None:
    rows, columns = shape
    weights = bytes(
        ((index * 37) % 0x7F) | (0x80 if index & 1 else 0)
        for index in range(rows * columns)
    )
    scale_shape = (rows // 128, columns // 128)
    scales = bytes(
        0x78 + index % 8 for index in range(scale_shape[0] * scale_shape[1])
    )
    output = dequantize_fp8_e8m0_matrix_to_bf16(
        weights, scales, shape, scale_shape
    )
    report = verify_dequantized_fp8_e8m0_bf16(
        weights, scales, output, shape, scale_shape
    )
    assert report["checked_element_count"] == rows * columns
    assert report["status"] == "full_payload_match"
    _validate_check_report(report)

    tampered = bytearray(output)
    tampered[-1] ^= 0x01
    with pytest.raises(DeepSeekV4TransformCheckError, match="BF16 mismatch"):
        verify_dequantized_fp8_e8m0_bf16(
            weights, scales, tampered, shape, scale_shape
        )


def test_matrix_dequantization_rejects_invalid_source_encodings() -> None:
    shape = (128, 128)
    zeros = bytes(128 * 128)
    with pytest.raises(CanonicalTransformError, match="reserved E8M0"):
        dequantize_fp8_e8m0_matrix_to_bf16(
            zeros, b"\xff", shape, (1, 1)
        )

    nan_weights = bytearray(zeros)
    nan_weights[37] = 0x7F
    with pytest.raises(CanonicalTransformError, match="NaN or BF16 overflow"):
        dequantize_fp8_e8m0_matrix_to_bf16(
            nan_weights, b"\x7f", shape, (1, 1)
        )

    overflow_weights = bytearray(zeros)
    overflow_weights[91] = 0x7E
    with pytest.raises(CanonicalTransformError, match="NaN or BF16 overflow"):
        dequantize_fp8_e8m0_matrix_to_bf16(
            overflow_weights, b"\xfe", shape, (1, 1)
        )


def test_row_major_slicing_is_exact_on_both_converter_axes() -> None:
    payload = bytes(range(24))
    axis_zero, shape_zero = slice_row_major_payload(
        payload, (3, 4), "U16", axis=0, start=1, stop=3
    )
    assert shape_zero == (2, 4)
    assert axis_zero == payload[8:24]

    axis_one, shape_one = slice_row_major_payload(
        payload, (3, 4), "U16", axis=1, start=1, stop=3
    )
    assert shape_one == (3, 2)
    assert axis_one == payload[2:6] + payload[10:14] + payload[18:22]

    with pytest.raises(CanonicalTransformError, match="payload has"):
        slice_row_major_payload(payload[:-1], (3, 4), "U16", 0, 0, 1)
    with pytest.raises(CanonicalTransformError, match="stop"):
        slice_row_major_payload(payload, (3, 4), "U16", 0, 1, 1)


def test_native_mxfp4_profile_proves_packed_and_scale_byte_identity() -> None:
    weight_shape = (2, 32)
    scale_shape = (2, 2)
    weights = bytes(range(64))
    scales = bytes((0x70, 0x71, 0x72, 0x73))
    validate_native_mxfp4_pair(weights, scales, weight_shape, scale_shape)
    report = verify_native_mxfp4_identity(
        weights, scales, weights, scales, weight_shape, scale_shape
    )
    assert report["checked_weight_byte_count"] == 64
    assert report["checked_scale_byte_count"] == 4
    _validate_check_report(report)

    changed = bytearray(weights)
    changed[17] ^= 0x10
    with pytest.raises(DeepSeekV4TransformCheckError, match="packed bytes"):
        verify_native_mxfp4_identity(
            weights, scales, changed, scales, weight_shape, scale_shape
        )

    poisoned_scales = b"\x70\xff\x72\x73"
    with pytest.raises(CanonicalTransformError, match="reserved E8M0"):
        validate_native_mxfp4_pair(
            weights, poisoned_scales, weight_shape, scale_shape
        )
    with pytest.raises(DeepSeekV4TransformCheckError, match="reserved"):
        verify_native_mxfp4_identity(
            weights,
            poisoned_scales,
            weights,
            poisoned_scales,
            weight_shape,
            scale_shape,
        )


def test_official_converter_name_partition_and_expert_rules_are_exact() -> None:
    fixtures = {
        "model.embed.weight": "embed.weight",
        "model.layers.0.self_attn.wq_b.weight": (
            "layers.0.attn.wq_b.weight"
        ),
        "model.layers.3.mlp.experts.64.w1.weight": (
            "layers.3.ffn.experts.64.w1.weight"
        ),
        "model.layers.4.mlp.gate.e_score_correction_bias": (
            "layers.4.ffn.gate.bias"
        ),
        "model.layers.5.self_attn.compressor.ape": (
            "layers.5.attn.compressor.ape"
        ),
        "mtp.2.markov_head.markov_w1.weight": (
            "mtp.2.markov_head.markov_w1.weight"
        ),
    }
    assert {
        source: canonicalize_source_name(source) for source in fixtures
    } == fixtures
    assert canonicalize_source_name("mtp.0.embedding.weight") is None
    assert canonicalize_source_name("mtp.0.head.weight") is None
    assert partition_axis("layers.0.attn.wq_b.weight") == 0
    assert partition_axis("layers.0.attn.wo_b.weight") == 1
    assert partition_axis("layers.0.attn.wkv.weight") is None
    assert routed_expert_id("layers.3.ffn.experts.64.w1.weight") == 64
    assert routed_expert_id("layers.3.ffn.shared_experts.w1.weight") is None
    with pytest.raises(CanonicalTransformError, match="safe string"):
        canonicalize_source_name("layers.0\x00bad.weight")


def test_complete_mp4_plan_covers_every_official_tensor_and_assignment() -> None:
    plan = build_official_canonical_plan()
    assert plan["plan_id"] == PLAN_ID
    assert plan["status"] == (
        "complete_transform_plan_pending_full_payload_application"
    )
    assert plan["coverage"] == {
        "consumed_source_tensor_count": 46,
        "input_payload_bytes": 166_878_536_440,
        "input_tensor_count": 72_317,
        "omitted_duplicate_tensor_count": 0,
        "output_assignment_count": 77_116,
        "output_payload_bytes_across_ranks": 175_539_889_120,
        "transform_source_tensor_counts": {
            "consume_wo_a_scale": 46,
            "replicate_identity": 1_272,
            "route_and_reinterpret_native_mxfp4": 35_328,
            "route_whole_tensor_to_expert_rank": 35_328,
            "slice_then_dequantize_wo_a_to_bf16": 46,
            "tensor_parallel_slice_axis_0": 205,
            "tensor_parallel_slice_axis_1": 92,
        },
    }
    assert plan["profile"] == {
        "expert_storage": "native_mxfp4_e2m1_x2_with_e8m0",
        "model_parallel": 4,
        "output_a_storage": "bf16_dequantized_from_fp8_e8m0",
        "routed_experts_per_rank": 64,
    }
    assert plan["rank_summaries"] == [
        {
            "payload_bytes": 43_884_972_280,
            "rank": 0,
            "tensor_count": 19_279,
            "tensor_names_sha256": (
                "4a4a74b66f72dcb429da86d035ec63b1285bf1e1b1c324bf37b534c9f7c0f614"
            ),
        },
        {
            "payload_bytes": 43_884_972_280,
            "rank": 1,
            "tensor_count": 19_279,
            "tensor_names_sha256": (
                "bee7cde146c258533c6022c46fbdf746190f5c6c19082952e5a32df872565a49"
            ),
        },
        {
            "payload_bytes": 43_884_972_280,
            "rank": 2,
            "tensor_count": 19_279,
            "tensor_names_sha256": (
                "d9e274b6c20e516d6d99930459668b10521b25dd8fc5fd2ed1fa922aa1f94e6f"
            ),
        },
        {
            "payload_bytes": 43_884_972_280,
            "rank": 3,
            "tensor_count": 19_279,
            "tensor_names_sha256": (
                "ad05b4d4f5a41ac559a6b18ebf8e293b60493b60ef58acb9fabfd7aa8c5cbd0c"
            ),
        },
    ]

    selected_names = {
        "embed.weight",
        "layers.0.attn.wo_a.scale",
        "layers.0.attn.wo_a.weight",
        "layers.3.ffn.experts.0.w1.weight",
        "layers.3.ffn.experts.64.w1.weight",
    }
    selected = {
        record["name"]: record
        for record in plan["inputs"]
        if record["name"] in selected_names
    }
    assert selected.keys() == selected_names
    assert [output["rank"] for output in selected["embed.weight"]["outputs"]] == [
        0,
        1,
        2,
        3,
    ]
    assert selected["layers.0.attn.wo_a.scale"]["outputs"] == []
    assert {
        output["transform"]
        for output in selected["layers.0.attn.wo_a.weight"]["outputs"]
    } == {"dequantize_fp8_e8m0_to_bf16_rne"}
    assert selected["layers.3.ffn.experts.0.w1.weight"]["outputs"][0][
        "rank"
    ] == 0
    assert selected["layers.3.ffn.experts.64.w1.weight"]["outputs"][0][
        "rank"
    ] == 1

    schema = load_strict_json(PLAN_SCHEMA)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(plan)
    body = dict(plan)
    plan_id = body.pop("plan_id")
    assert plan_id == hashlib.sha256(canonical_json_bytes(body)).hexdigest()

    expected_summary = copy.deepcopy(plan["rank_summaries"])
    del body, plan
    gc.collect()
    repeated = build_official_canonical_plan()
    assert repeated["plan_id"] == PLAN_ID
    assert repeated["rank_summaries"] == expected_summary


def test_plan_rejects_illegal_parallelism_and_source_identity_drift(
    tmp_path: Path,
) -> None:
    with pytest.raises(CanonicalTransformError, match="not divisible"):
        build_official_canonical_plan(model_parallel=3)
    with pytest.raises(CanonicalTransformError, match="integer in 1..256"):
        build_official_canonical_plan(model_parallel=True)

    source = load_strict_json(DEFAULT_SOURCE)
    changed = copy.deepcopy(source)
    convert = next(
        record
        for record in changed["expected_files"]
        if record["path"] == "inference/convert.py"
    )
    convert["sha256"] = "0" * 64
    changed_source = tmp_path / "checkpoint-source.json"
    write_canonical_json(changed_source, changed)
    with pytest.raises(CanonicalTransformError, match="convert.py identity"):
        build_official_canonical_plan(source_path=changed_source)


def test_canonical_plan_cli_emits_exact_pending_application_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "canonical-plan.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "describe-deepseek-v4-canonical-plan",
            "--model-parallel",
            "4",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    plan = json.loads(output.read_text(encoding="ascii"))
    assert plan["plan_id"] == PLAN_ID
    assert plan["status"].endswith("pending_full_payload_application")
    assert "planned 72317 official tensors into 77116 assignments" in result.stdout
    assert "across 4 ranks" in result.stdout
