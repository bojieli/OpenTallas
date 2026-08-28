"""First-principles decode operation inventories.

The analytical simulator historically approximated one generated token as
``2 * active_parameters`` operations.  That identity counts a weight matrix
once, but it cannot represent context-linear attention, compressed-KV
construction, mixed arithmetic formats, or unlayered projections such as the
vocabulary head.

This module instead inventories tensor contractions directly from published
operator dimensions.  One multiply plus one add is two operations, matching
the FLOP convention used by accelerator vendors.  Elementwise transforms,
normalization, routing selection, and transcendental evaluations are exposed
as auxiliary counts rather than silently charged at a Tensor Core roof.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .schema import ModelProfile, ValidationError


FP8_X_FP8 = "fp8_e4m3_x_fp8_e4m3"
MXFP4_X_FP8 = "mxfp4_e2m1_x_fp8_e4m3"
BF16_X_BF16 = "bf16_x_bf16"
FP4_X_FP4 = "fp4_e2m1_x_fp4_e2m1"
FP32_X_FP32 = "fp32_x_fp32"


@dataclass(frozen=True)
class OperationComponent:
    """One auditable tensor-contraction term."""

    name: str
    numeric_format: str
    operations: float
    layer_index: int | None
    formula: str
    evidence: str


@dataclass(frozen=True)
class OperationInventory:
    """Decode work for one user token at one context position."""

    model: str
    context_tokens: int
    method: str
    components: tuple[OperationComponent, ...]
    operations_by_format: dict[str, float]
    per_layer_operations_by_format: tuple[dict[str, float], ...]
    unlayered_operations_by_format: dict[str, float]
    auxiliary_counts: dict[str, float]
    evidence: tuple[str, ...]

    @property
    def total_tensor_operations(self) -> float:
        return sum(self.operations_by_format.values())

    def operations_for(self, numeric_format: str) -> float:
        return self.operations_by_format.get(numeric_format, 0.0)

    def named_operations(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for component in self.components:
            totals[component.name] = totals.get(component.name, 0.0) + component.operations
        return totals


def _sum_formats(items: list[dict[str, float]]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for item in items:
        for numeric_format, operations in item.items():
            totals[numeric_format] = totals.get(numeric_format, 0.0) + operations
    return {key: value for key, value in sorted(totals.items()) if value > 0}


def _required_int(config: dict[str, Any], key: str) -> int:
    try:
        value = int(config[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f"DeepSeek operator_config requires integer {key!r}") from exc
    if value <= 0:
        raise ValidationError(f"DeepSeek operator_config[{key!r}] must be positive")
    return value


def _deepseek_v4_inventory(
    model: ModelProfile, context_tokens: int
) -> OperationInventory:
    raw_config = model.metadata.get("operator_config")
    if not isinstance(raw_config, dict):
        raise ValidationError(
            f"{model.name} is a DeepSeek V4 profile without operator_config"
        )
    config: dict[str, Any] = raw_config

    vocab = _required_int(config, "vocab_size")
    dim = _required_int(config, "hidden_size")
    moe_dim = _required_int(config, "moe_intermediate_size")
    heads = _required_int(config, "num_attention_heads")
    head_dim = _required_int(config, "head_dim")
    rope_dim = _required_int(config, "rope_head_dim")
    q_rank = _required_int(config, "q_lora_rank")
    output_groups = _required_int(config, "o_groups")
    output_rank = _required_int(config, "o_lora_rank")
    experts = _required_int(config, "num_routed_experts")
    shared_experts = _required_int(config, "num_shared_experts")
    experts_per_token = _required_int(config, "experts_per_token")
    index_heads = _required_int(config, "index_heads")
    index_dim = _required_int(config, "index_head_dim")
    index_topk = _required_int(config, "index_topk")
    window = _required_int(config, "window_tokens")
    hc_mult = _required_int(config, "hc_mult")
    sinkhorn_iterations = _required_int(config, "hc_sinkhorn_iters")
    ratios_raw = config.get("compress_ratios")
    if not isinstance(ratios_raw, list) or len(ratios_raw) != model.num_layers:
        raise ValidationError(
            "DeepSeek operator_config compress_ratios must cover every layer"
        )
    ratios = tuple(int(value) for value in ratios_raw)
    if any(value < 0 for value in ratios):
        raise ValidationError("compression ratios cannot be negative")
    if dim != model.hidden_size or experts != model.num_experts:
        raise ValidationError("operator_config conflicts with top-level model dimensions")
    if experts_per_token != model.experts_per_token:
        raise ValidationError("operator_config conflicts with top-level routing dimensions")
    if rope_dim >= head_dim:
        raise ValidationError("rope_head_dim must be smaller than head_dim")
    if heads % output_groups:
        raise ValidationError("attention heads must divide evenly into output groups")
    if shared_experts != 1:
        raise ValidationError("the released DeepSeek V4 implementation requires one shared expert")

    components: list[OperationComponent] = []
    per_layer: list[dict[str, float]] = [dict() for _ in range(model.num_layers)]
    unlayered: dict[str, float] = {}
    auxiliary: dict[str, float] = {
        "attention_score_elements": 0.0,
        "compressor_pool_elements": 0.0,
        "index_score_elements": 0.0,
        "normalization_elements": 0.0,
        "nonlinear_elements": 0.0,
        "topk_candidates": 0.0,
        "topk_selected": 0.0,
        "sinkhorn_matrix_elements_per_iteration": 0.0,
    }

    def add(
        name: str,
        numeric_format: str,
        operations: float,
        layer_index: int | None,
        formula: str,
        evidence: str,
    ) -> None:
        if operations < 0 or not math.isfinite(operations):
            raise ValidationError(f"invalid operation count for {name}: {operations}")
        if operations == 0:
            return
        component = OperationComponent(
            name=name,
            numeric_format=numeric_format,
            operations=float(operations),
            layer_index=layer_index,
            formula=formula,
            evidence=evidence,
        )
        components.append(component)
        target = unlayered if layer_index is None else per_layer[layer_index]
        target[numeric_format] = target.get(numeric_format, 0.0) + operations

    official_shapes = (
        "official config and pinned checkpoint tensor shapes; multiply-add = 2 ops"
    )
    official_code = "pinned DeepSeek inference/model.py decode path"

    # These matrices are present in every attention block.  The grouped wo_a
    # contraction covers each head dimension exactly once; it is not multiplied
    # by the number of output groups a second time.
    attention_projection_terms = (
        ("attention_wq_a", 2 * dim * q_rank, "2*d*q_lora_rank"),
        (
            "attention_wq_b",
            2 * q_rank * heads * head_dim,
            "2*q_lora_rank*n_heads*head_dim",
        ),
        ("attention_wkv", 2 * dim * head_dim, "2*d*head_dim"),
        (
            "attention_wo_a_grouped",
            2 * heads * head_dim * output_rank,
            "2*n_heads*head_dim*o_lora_rank",
        ),
        (
            "attention_wo_b",
            2 * output_groups * output_rank * dim,
            "2*o_groups*o_lora_rank*d",
        ),
    )
    shared_expert_ops = 6 * dim * moe_dim * shared_experts
    routed_expert_ops = 6 * dim * moe_dim * experts_per_token
    router_ops = 2 * dim * experts
    mhc_projection_ops = 2 * (2 * (hc_mult * dim) * ((2 + hc_mult) * hc_mult))

    for layer, ratio in enumerate(ratios):
        for name, operations, formula in attention_projection_terms:
            add(name, FP8_X_FP8, operations, layer, formula, official_shapes)

        add(
            "shared_expert_swiglu",
            FP8_X_FP8,
            shared_expert_ops,
            layer,
            "6*d*moe_intermediate*n_shared_experts",
            official_shapes,
        )
        add(
            "routed_expert_swiglu",
            MXFP4_X_FP8,
            routed_expert_ops,
            layer,
            "6*d*moe_intermediate*experts_per_token",
            "DeepSeek report MXFP4 expert weights with FP8 activations and official shapes",
        )
        add(
            "router_projection",
            BF16_X_BF16,
            router_ops,
            layer,
            "2*d*n_routed_experts",
            "pinned BF16 gate tensor; hash layers still compute routing weights",
        )
        add(
            "mhc_pre_projections",
            FP32_X_FP32,
            mhc_projection_ops,
            layer,
            "2 paths * 2*(hc_mult*d)*((2+hc_mult)*hc_mult)",
            "pinned FP32 mHC tensors and official implementation",
        )

        # At decode position L, the current token is inserted before attention,
        # so the reference implementation exposes L+1 positions.  At the long
        # contexts studied here this changes only compression-boundary points.
        visible_tokens = context_tokens + 1
        window_entries = min(window, visible_tokens)
        if ratio == 0:
            compressed_entries = 0
        elif ratio == 4:
            compressed_entries = min(index_topk, visible_tokens // ratio)
        else:
            compressed_entries = visible_tokens // ratio
        attention_entries = window_entries + compressed_entries

        # The shared KV vector participates in both QK and score*V contractions:
        # two multiply-adds, or four operations, per head/dimension/entry.
        nonrope_dim = head_dim - rope_dim
        add(
            "attention_core_nonrope",
            FP8_X_FP8,
            4 * heads * nonrope_dim * attention_entries,
            layer,
            "4*n_heads*(head_dim-rope_dim)*attended_entries",
            "DeepSeek mixed FP8/BF16 KV policy and sparse_attn QK+AV contractions",
        )
        add(
            "attention_core_rope",
            BF16_X_BF16,
            4 * heads * rope_dim * attention_entries,
            layer,
            "4*n_heads*rope_dim*attended_entries",
            "DeepSeek mixed FP8/BF16 KV policy and sparse_attn QK+AV contractions",
        )
        auxiliary["attention_score_elements"] += heads * attention_entries

        if ratio:
            overlap_factor = 2 if ratio == 4 else 1
            add(
                "main_compressor_projections",
                BF16_X_BF16,
                4 * dim * overlap_factor * head_dim,
                layer,
                "2 projections * 2*d*(overlap_factor*head_dim)",
                "pinned BF16 compressor wkv/wgate tensors and official decode path",
            )
            pool_width = ratio * overlap_factor
            auxiliary["compressor_pool_elements"] += (
                pool_width * head_dim / ratio
            )

        if ratio == 4:
            index_entries = visible_tokens // ratio
            add(
                "indexer_query_up_projection",
                FP8_X_FP8,
                2 * q_rank * index_heads * index_dim,
                layer,
                "2*q_lora_rank*index_heads*index_head_dim",
                official_shapes,
            )
            add(
                "indexer_weight_projection",
                BF16_X_BF16,
                2 * dim * index_heads,
                layer,
                "2*d*index_heads",
                "pinned BF16 indexer weights_proj tensor",
            )
            add(
                "indexer_compressor_projections",
                BF16_X_BF16,
                8 * dim * index_dim,
                layer,
                "2 projections * 2*d*(2*index_head_dim)",
                "pinned BF16 overlapping index-compressor tensors",
            )
            add(
                "indexer_qk_scan",
                FP4_X_FP4,
                2 * index_heads * index_dim * index_entries,
                layer,
                "2*index_heads*index_head_dim*floor((context+1)/4)",
                "DeepSeek report: indexer QK cached, loaded, and multiplied entirely in FP4",
            )
            auxiliary["index_score_elements"] += index_heads * index_entries
            auxiliary["topk_candidates"] += index_entries
            auxiliary["topk_selected"] += min(index_topk, index_entries)
            auxiliary["compressor_pool_elements"] += (
                2 * ratio * index_dim / ratio
            )

        # Vector work is reported as element counts because divides, rsqrt,
        # sigmoid, exp, and comparisons do not share one defensible "FLOP" cost.
        auxiliary["normalization_elements"] += (
            2 * dim + q_rank + heads * head_dim + head_dim
        )
        auxiliary["nonlinear_elements"] += (
            (experts_per_token + shared_experts) * moe_dim + experts
        )
        auxiliary["sinkhorn_matrix_elements_per_iteration"] += hc_mult * hc_mult

    add(
        "final_vocabulary_head",
        BF16_X_BF16,
        2 * dim * vocab,
        None,
        "2*d*vocab_size",
        "pinned BF16 head tensor shape",
    )
    add(
        "final_mhc_head_projection",
        FP32_X_FP32,
        2 * (hc_mult * dim) * hc_mult,
        None,
        "2*(hc_mult*d)*hc_mult",
        "pinned FP32 hc_head_fn tensor shape",
    )
    auxiliary["normalization_elements"] += dim
    auxiliary["sinkhorn_iterations"] = float(sinkhorn_iterations)

    operations_by_format = _sum_formats(per_layer + [unlayered])
    return OperationInventory(
        model=model.name,
        context_tokens=context_tokens,
        method="deepseek_v4_official_operator_inventory_v1",
        components=tuple(components),
        operations_by_format=operations_by_format,
        per_layer_operations_by_format=tuple(
            {key: value for key, value in sorted(item.items()) if value > 0}
            for item in per_layer
        ),
        unlayered_operations_by_format={
            key: value for key, value in sorted(unlayered.items()) if value > 0
        },
        auxiliary_counts={key: float(value) for key, value in sorted(auxiliary.items())},
        evidence=(
            str(model.metadata.get("operator_accounting_source", "official DeepSeek sources")),
            "DeepSeek-V4 technical report arithmetic/storage precision policy",
            "no calibration to the report FLOP curve",
        ),
    )


def _active_parameter_fallback(
    model: ModelProfile, context_tokens: int
) -> OperationInventory:
    """Retain an explicit, marked fallback for non-DeepSeek control models."""

    dense_active = max(0.0, min(model.active_parameters, model.dense_parameters))
    routed_active = max(0.0, model.active_parameters - dense_active)
    dense_operations = model.operations_per_active_parameter * dense_active
    routed_operations = model.operations_per_active_parameter * routed_active
    components: list[OperationComponent] = []
    if dense_operations:
        components.append(
            OperationComponent(
                name="active_parameter_dense_fallback",
                numeric_format=model.dense_compute_format,
                operations=dense_operations,
                layer_index=None,
                formula="operations_per_active_parameter*dense_active_parameters",
                evidence="legacy fallback; exact operator inventory unavailable",
            )
        )
    if routed_operations and model.routed_compute_format is not None:
        components.append(
            OperationComponent(
                name="active_parameter_routed_fallback",
                numeric_format=model.routed_compute_format,
                operations=routed_operations,
                layer_index=None,
                formula="operations_per_active_parameter*routed_active_parameters",
                evidence="legacy fallback; exact operator inventory unavailable",
            )
        )
    totals: dict[str, float] = {}
    for component in components:
        totals[component.numeric_format] = (
            totals.get(component.numeric_format, 0.0) + component.operations
        )
    # Evenly partition only for compatibility with the spatial pipeline.  The
    # result remains explicitly tagged as a fallback, never a measured layout.
    per_layer = tuple(
        {key: value / model.num_layers for key, value in totals.items()}
        for _ in range(model.num_layers)
    )
    return OperationInventory(
        model=model.name,
        context_tokens=context_tokens,
        method="active_parameter_fallback",
        components=tuple(components),
        operations_by_format=dict(sorted(totals.items())),
        per_layer_operations_by_format=per_layer,
        unlayered_operations_by_format={},
        auxiliary_counts={},
        evidence=("exact public operator inventory unavailable",),
    )


def operation_inventory(model: ModelProfile, context_tokens: int) -> OperationInventory:
    """Return tensor and auxiliary decode work for one generated user token."""

    if context_tokens < 0:
        raise ValidationError("context_tokens cannot be negative")
    if context_tokens > model.max_context_tokens:
        raise ValidationError("context_tokens exceeds model maximum")
    if model.metadata.get("adapter") == "deepseek_v4":
        return _deepseek_v4_inventory(model, context_tokens)
    return _active_parameter_fallback(model, context_tokens)
