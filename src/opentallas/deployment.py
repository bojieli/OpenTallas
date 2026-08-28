"""Hardware-required representations derived from released checkpoints."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from .schema import AttentionGroup, ModelProfile, ValidationError


OFFICIAL_PACKED = "official_packed"
A100_BF16_EXPANDED = "a100_bf16_expanded"
A100_PACKED_BF16_EXECUTE = "a100_packed_hbm_bf16_execute"


def _positive_int(mapping: dict[str, Any], key: str) -> int:
    try:
        value = int(mapping[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f"deployment metadata requires integer {key!r}") from exc
    if value <= 0:
        raise ValidationError(f"deployment metadata {key!r} must be positive")
    return value


def deployment_model(model: ModelProfile, policy: str) -> ModelProfile:
    """Return the exact resident/traffic representation for ``policy``.

    The expanded A100 policy performs offline, lossless value expansion.  The
    packed A100 policy instead keeps the released bytes in HBM and performs the
    same lossless value expansion at operand consumption.  Neither policy
    pretends that Ampere supports the checkpoint's FP8/MXFP4 arithmetic.  The
    architecture compute-path table separately maps those logical operations to
    native BF16 execution and records whether conversion cost is bounded or
    measured.
    """

    if policy == OFFICIAL_PACKED:
        return replace(
            model,
            metadata={**model.metadata, "deployment_policy": OFFICIAL_PACKED},
        )
    if policy == A100_PACKED_BF16_EXECUTE:
        if model.metadata.get("adapter") != "deepseek_v4":
            raise ValidationError(
                "A100 packed-to-BF16 execution is currently defined only for DeepSeek V4"
            )
        return replace(
            model,
            metadata={
                **model.metadata,
                "deployment_policy": A100_PACKED_BF16_EXECUTE,
                "deployment_storage_policy": (
                    "official released bytes remain packed in HBM; values are "
                    "expanded losslessly at operand consumption"
                ),
                "kv_cache_policy": (
                    "official packed main/index cache retained in HBM and expanded "
                    "at operand consumption"
                ),
                "kv_cache_policy_status": (
                    "GPU-favorable implementation ceiling; exact MXFP4/FP8 unpack "
                    "kernel cost and throughput are unmeasured on A100"
                ),
            },
        )
    if policy != A100_BF16_EXPANDED:
        raise ValidationError(f"unsupported deployment policy {policy!r}")
    if model.metadata.get("adapter") != "deepseek_v4":
        raise ValidationError("A100 BF16 expansion is currently defined only for DeepSeek V4")

    deployments = model.metadata.get("deployment_storage")
    if not isinstance(deployments, dict):
        raise ValidationError("model profile lacks deployment_storage metadata")
    storage = deployments.get(A100_BF16_EXPANDED)
    if not isinstance(storage, dict):
        raise ValidationError("model profile lacks A100 BF16 expanded storage")
    operator_config = model.metadata.get("operator_config")
    if not isinstance(operator_config, dict):
        raise ValidationError("model profile lacks operator_config metadata")
    head_dim = _positive_int(operator_config, "head_dim")
    index_dim = _positive_int(operator_config, "index_head_dim")

    layer_dense = storage.get("decode_layer_dense_bytes")
    layer_routed = storage.get("decode_layer_routed_bytes")
    if not isinstance(layer_dense, dict) or not isinstance(layer_routed, dict):
        raise ValidationError("expanded deployment lacks per-layer storage")

    groups: list[AttentionGroup] = []
    for group in model.attention_groups:
        updates: dict[str, float] = {"entry_bytes": float(2 * head_dim)}
        if group.kind == "compressed_sparse":
            updates["index_entry_bytes"] = float(2 * index_dim)
        groups.append(replace(group, **updates))

    metadata = dict(model.metadata)
    metadata.update(
        {
            "deployment_policy": A100_BF16_EXPANDED,
            "deployment_storage_policy": storage.get("policy", "derived offline expansion"),
            "kv_cache_policy": (
                "BF16 main and index cache retaining values quantized by the official "
                "FP8/FP4 model policy"
            ),
            "kv_cache_policy_status": (
                "derived A100-compatible expansion; accuracy still requires runtime validation"
            ),
        }
    )
    return replace(
        model,
        checkpoint_bytes=float(storage["checkpoint_bytes"]),
        dense_weight_bytes=float(storage["decode_dense_bytes"]),
        routed_weight_bytes=float(storage["decode_routed_bytes"]),
        draft_dense_weight_bytes=float(storage["draft_dense_bytes"]),
        draft_routed_weight_bytes=float(storage["draft_routed_bytes"]),
        resident_only_weight_bytes=float(storage["resident_only_bytes"]),
        layer_dense_weight_bytes=tuple(
            float(layer_dense.get(str(layer), 0)) for layer in range(model.num_layers)
        ),
        layer_routed_weight_bytes=tuple(
            float(layer_routed.get(str(layer), 0)) for layer in range(model.num_layers)
        ),
        attention_groups=tuple(groups),
        metadata=metadata,
    )
