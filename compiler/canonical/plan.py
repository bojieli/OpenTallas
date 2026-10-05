"""Complete deterministic transform plan for the official V4 Flash tensors."""

from __future__ import annotations

from collections import Counter
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping

from compiler.canonical.deepseek_v4 import (
    CANONICAL_PLAN_SCHEMA,
    CONVERT_SOURCE_SHA256,
    CanonicalTransformError,
    canonicalize_source_name,
    dtype_bytes,
    partition_axis,
    routed_expert_id,
)
from compiler.frontend.checkpoint import load_checkpoint_source
from compiler.frontend.deepseek_v4 import (
    MODEL_ID,
    PAYLOAD_BYTES,
    REPOSITORY,
    REVISION,
    TENSOR_COUNT,
    TENSOR_STRUCTURE_SHA256,
    TensorSpec,
    build_official_tensor_specs,
    load_official_config,
)
from compiler.ir.model import canonical_json_bytes


DEFAULT_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "deepseek-v4-flash-0731"
    / "checkpoint_source.json"
)


def _model_parallel(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 256:
        raise CanonicalTransformError(
            "model_parallel must be an integer in 1..256"
        )
    return value


def _slice_descriptor(
    spec: TensorSpec, rank: int, model_parallel: int
) -> tuple[dict[str, int] | None, tuple[int, ...]]:
    axis = partition_axis(spec.name)
    if axis is None:
        return None, spec.shape
    if axis >= len(spec.shape):
        raise CanonicalTransformError(
            f"partition axis {axis} is outside tensor {spec.name!r}"
        )
    extent = spec.shape[axis]
    if extent % model_parallel:
        raise CanonicalTransformError(
            f"tensor {spec.name!r} axis {axis} extent {extent} is not divisible "
            f"by model_parallel={model_parallel}"
        )
    size = extent // model_parallel
    start = rank * size
    output_shape = list(spec.shape)
    output_shape[axis] = size
    return {"axis": axis, "start": start, "stop": start + size}, tuple(output_shape)


def _output_ranks(
    spec: TensorSpec, model_parallel: int, local_experts: int
) -> tuple[int, ...]:
    expert = routed_expert_id(spec.name)
    if expert is not None:
        if spec.expert != expert:
            raise CanonicalTransformError(
                f"expert metadata differs from tensor name {spec.name!r}"
            )
        rank = expert // local_experts
        if not 0 <= rank < model_parallel:
            raise CanonicalTransformError(
                f"expert {expert} is outside model-parallel assignment"
            )
        return (rank,)
    return tuple(range(model_parallel))


def _source_action(spec: TensorSpec, consumed_scales: set[str]) -> str:
    if spec.name in consumed_scales:
        return "consume_wo_a_scale"
    if spec.name.endswith(".wo_a.weight"):
        return "slice_then_dequantize_wo_a_to_bf16"
    if (
        spec.storage_dtype == "I8"
        and spec.logical_dtype == "MXFP4_E2M1_X2"
        and spec.name.endswith(".weight")
    ):
        return "route_and_reinterpret_native_mxfp4"
    if routed_expert_id(spec.name) is not None:
        return "route_whole_tensor_to_expert_rank"
    axis = partition_axis(spec.name)
    if axis is not None:
        return f"tensor_parallel_slice_axis_{axis}"
    return "replicate_identity"


def _output_record(
    spec: TensorSpec,
    *,
    rank: int,
    model_parallel: int,
    specs_by_name: Mapping[str, TensorSpec],
) -> dict[str, Any]:
    source_slice, sliced_shape = _slice_descriptor(spec, rank, model_parallel)
    transform = "identity"
    output_dtype = spec.storage_dtype
    output_logical_dtype = spec.logical_dtype
    scale_source = None
    scale_source_slice = None
    if spec.name.endswith(".wo_a.weight"):
        transform = "dequantize_fp8_e8m0_to_bf16_rne"
        output_dtype = "BF16"
        output_logical_dtype = "BF16"
        scale_source = spec.name[: -len(".weight")] + ".scale"
        scale_spec = specs_by_name.get(scale_source)
        if scale_spec is None or scale_spec.scale_for != spec.name:
            raise CanonicalTransformError(
                f"wo_a weight {spec.name!r} lacks its exact scale tensor"
            )
        scale_source_slice, _ = _slice_descriptor(
            scale_spec, rank, model_parallel
        )
    elif (
        spec.storage_dtype == "I8"
        and spec.logical_dtype == "MXFP4_E2M1_X2"
        and spec.name.endswith(".weight")
    ):
        transform = "reinterpret_i8_bytes_as_native_mxfp4_low_nibble_first"
        output_dtype = "U8"
    return {
        "logical_dtype": output_logical_dtype,
        "name": spec.name,
        "payload_bytes": math.prod(sliced_shape) * dtype_bytes(output_dtype),
        "rank": rank,
        "scale_source": scale_source,
        "scale_source_slice": scale_source_slice,
        "shape": list(sliced_shape),
        "source_slice": source_slice,
        "storage_dtype": output_dtype,
        "transform": transform,
    }


def build_official_canonical_plan(
    *,
    model_parallel: int = 4,
    source_path: Path = DEFAULT_SOURCE,
) -> dict[str, Any]:
    """Plan every released tensor for the native-MXFP4 compiler profile."""

    model_parallel = _model_parallel(model_parallel)
    source = load_checkpoint_source(source_path)
    if (
        source["repository"] != REPOSITORY
        or source["revision"] != REVISION
        or source["remote_code_policy"] != "disabled"
    ):
        raise CanonicalTransformError(
            "canonical plan source is not the pinned local-only V4 Flash release"
        )
    convert_records = [
        record
        for record in source["expected_files"]
        if record["path"] == "inference/convert.py"
    ]
    if (
        len(convert_records) != 1
        or convert_records[0]["sha256"] != CONVERT_SOURCE_SHA256
    ):
        raise CanonicalTransformError("official convert.py identity differs")
    config = load_official_config(source_path=source_path)
    expert_count = config["n_routed_experts"]
    if expert_count % model_parallel:
        raise CanonicalTransformError(
            f"{expert_count} experts are not divisible by "
            f"model_parallel={model_parallel}"
        )
    local_experts = expert_count // model_parallel
    specs = build_official_tensor_specs(config)
    specs_by_name = {spec.name: spec for spec in specs}
    if len(specs_by_name) != TENSOR_COUNT:
        raise CanonicalTransformError("official tensor contract has duplicate names")

    consumed_scales = {
        spec.name for spec in specs if spec.name.endswith(".wo_a.scale")
    }
    wo_a_weights = {
        spec.name for spec in specs if spec.name.endswith(".wo_a.weight")
    }
    if len(consumed_scales) != 46 or len(wo_a_weights) != 46:
        raise CanonicalTransformError(
            "expected 46 main and DSpark wo_a weight-scale pairs"
        )
    if {specs_by_name[name].scale_for for name in consumed_scales} != wo_a_weights:
        raise CanonicalTransformError("wo_a scale ownership is incomplete")

    inputs: list[dict[str, Any]] = []
    rank_names: list[set[str]] = [set() for _ in range(model_parallel)]
    rank_counts = [0] * model_parallel
    rank_bytes = [0] * model_parallel
    action_counts: Counter[str] = Counter()
    assignment_count = 0
    omitted_duplicate_count = 0
    for spec in specs:
        canonical_name = canonicalize_source_name(spec.name)
        if canonical_name is None:
            action = "omit_duplicate_mtp_embedding_or_head"
            outputs: list[dict[str, Any]] = []
            omitted_duplicate_count += 1
        else:
            if canonical_name != spec.name:
                raise CanonicalTransformError(
                    f"official tensor {spec.name!r} is not canonically named"
                )
            action = _source_action(spec, consumed_scales)
            if spec.name in consumed_scales:
                outputs = []
            else:
                outputs = [
                    _output_record(
                        spec,
                        rank=rank,
                        model_parallel=model_parallel,
                        specs_by_name=specs_by_name,
                    )
                    for rank in _output_ranks(
                        spec, model_parallel, local_experts
                    )
                ]
                for output in outputs:
                    rank = output["rank"]
                    if output["name"] in rank_names[rank]:
                        raise CanonicalTransformError(
                            f"rank {rank} receives duplicate tensor "
                            f"{output['name']!r}"
                        )
                    rank_names[rank].add(output["name"])
                    rank_counts[rank] += 1
                    rank_bytes[rank] += output["payload_bytes"]
                    assignment_count += 1
        action_counts[action] += 1
        inputs.append(
            {
                "action": action,
                "logical_dtype": spec.logical_dtype,
                "name": spec.name,
                "outputs": outputs,
                "semantic_role": spec.semantic_role,
                "shape": list(spec.shape),
                "size_bytes": spec.size_bytes,
                "storage_dtype": spec.storage_dtype,
            }
        )

    input_payload_bytes = sum(spec.size_bytes for spec in specs)
    if len(specs) != TENSOR_COUNT or input_payload_bytes != PAYLOAD_BYTES:
        raise CanonicalTransformError(
            "canonical plan input coverage differs from the official release"
        )
    body: dict[str, Any] = {
        "coverage": {
            "consumed_source_tensor_count": len(consumed_scales),
            "input_payload_bytes": input_payload_bytes,
            "input_tensor_count": len(specs),
            "omitted_duplicate_tensor_count": omitted_duplicate_count,
            "output_assignment_count": assignment_count,
            "output_payload_bytes_across_ranks": sum(rank_bytes),
            "transform_source_tensor_counts": dict(sorted(action_counts.items())),
        },
        "inputs": inputs,
        "profile": {
            "expert_storage": "native_mxfp4_e2m1_x2_with_e8m0",
            "model_parallel": model_parallel,
            "output_a_storage": "bf16_dequantized_from_fp8_e8m0",
            "routed_experts_per_rank": local_experts,
        },
        "rank_summaries": [
            {
                "payload_bytes": rank_bytes[rank],
                "rank": rank,
                "tensor_count": rank_counts[rank],
                "tensor_names_sha256": hashlib.sha256(
                    canonical_json_bytes(sorted(rank_names[rank]))
                ).hexdigest(),
            }
            for rank in range(model_parallel)
        ],
        "schema": CANONICAL_PLAN_SCHEMA,
        "source": {
            "convert_sha256": CONVERT_SOURCE_SHA256,
            "model_id": MODEL_ID,
            "repository": REPOSITORY,
            "revision": REVISION,
            "tensor_count": TENSOR_COUNT,
            "tensor_payload_bytes": PAYLOAD_BYTES,
            "tensor_structure_sha256": TENSOR_STRUCTURE_SHA256,
        },
        "status": "complete_transform_plan_pending_full_payload_application",
    }
    body["plan_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    return body


__all__ = ["DEFAULT_SOURCE", "build_official_canonical_plan"]
