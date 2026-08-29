"""Complete semantic decode graph for the pinned Qwen3-8B checkpoint."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
from typing import Any, Iterable, Mapping

from compiler.ir.model import canonical_json_bytes

from .adapter import TensorSpec, build_tensor_specs, load_official_config
from .constants import (
    CONFIG_SHA256,
    LAYER_COUNT,
    MODEL_ID,
    REPOSITORY,
    REVISION,
    TARGET_CONTEXT_TOKENS,
    TRANSFORMERS_CONFIG_SOURCE_SHA256,
    TRANSFORMERS_MODEL_SOURCE_SHA256,
    TRANSFORMERS_MODULAR_SOURCE_SHA256,
    TRANSFORMERS_VERSION,
)


GRAPH_SCHEMA = "opentallas.qwen3.semantic_graph.v1"


class Qwen3GraphError(RuntimeError):
    """Raised when graph construction leaves a semantic or payload gap."""


@dataclass(frozen=True)
class OperatorRequirement:
    kind: str
    semantics: str
    source_symbol: str
    lowering: str
    state_effect: str
    arithmetic: str

    def record(self) -> dict[str, str]:
        return {
            "arithmetic": self.arithmetic,
            "kind": self.kind,
            "lowering": self.lowering,
            "semantics": self.semantics,
            "source_symbol": self.source_symbol,
            "state_effect": self.state_effect,
        }


_OPERATORS = (
    OperatorRequirement(
        "TOKEN_EMBEDDING_LOOKUP",
        "Gather one BF16 hidden vector for every validated token ID.",
        "Qwen3Model.forward:embed_tokens",
        "ROM_LOOKUP",
        "none",
        "exact BF16 payload lookup",
    ),
    OperatorRequirement(
        "RMS_NORM",
        "Accumulate mean square in FP32, apply rsqrt(eps=1e-6), cast to the input dtype, then multiply by BF16 weight.",
        "Qwen3RMSNorm.forward",
        "RMSNORM",
        "none",
        "FP32 reduction and rsqrt; BF16 output multiply",
    ),
    OperatorRequirement(
        "LINEAR",
        "Bias-free matrix projection using the declared BF16 row-major weight.",
        "Qwen3Attention.forward;Qwen3MLP.forward;Qwen3ForCausalLM.forward",
        "ROM_MATMUL",
        "none",
        "BF16 matrix multiplication with backend-declared accumulation",
    ),
    OperatorRequirement(
        "ROPE",
        "Apply default half-rotation RoPE to normalized Q and K using FP32 frequencies and BF16 cos/sin at the absolute cache positions.",
        "Qwen3RotaryEmbedding.forward;apply_rotary_pos_emb",
        "ROPE",
        "none",
        "FP32 frequency construction; BF16 rotate/multiply/add",
    ),
    OperatorRequirement(
        "KV_COMMIT",
        "Append the current rotated K and unrotated V exactly once to the addressed layer cache after all context bounds pass.",
        "Qwen3Attention.forward:past_key_values.update",
        "KV_COMMIT",
        "mutable_kv",
        "byte-preserving BF16 state write",
    ),
    OperatorRequirement(
        "GQA_CAUSAL_ATTENTION",
        "Repeat each KV head across four query heads, apply 1/sqrt(128) scaled causal attention, FP32 softmax semantics, and value reduction.",
        "Qwen3Attention.forward;eager_attention_forward;repeat_kv",
        "ATTEND",
        "reads_committed_kv",
        "BF16 QK/AV with FP32 softmax reference boundary",
    ),
    OperatorRequirement(
        "RESIDUAL_ADD",
        "Add the attention or MLP result to its exact pre-branch residual.",
        "Qwen3DecoderLayer.forward",
        "RESIDUAL",
        "none",
        "BF16 elementwise add",
    ),
    OperatorRequirement(
        "SILU_MUL",
        "Apply SiLU to the gate projection and multiply by the independent up projection.",
        "Qwen3MLP.forward",
        "SILU;GATE",
        "none",
        "backend SiLU followed by BF16 elementwise multiply",
    ),
    OperatorRequirement(
        "LAST_TOKEN_SELECT",
        "Select the final position of the current prefill/decode span before the untied vocabulary projection.",
        "Qwen3ForCausalLM.forward:logits_to_keep",
        "GATHER",
        "none",
        "exact index selection",
    ),
)
OPERATOR_CATALOG = {item.kind: item for item in _OPERATORS}


@dataclass(frozen=True)
class GraphNode:
    index: int
    kind: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    tensors: tuple[str, ...] = ()
    layer: int | None = None

    @property
    def node_id(self) -> str:
        return f"node.{self.index:04d}"

    def record(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "inputs": list(self.inputs),
            "kind": self.kind,
            "layer": self.layer,
            "node_id": self.node_id,
            "outputs": list(self.outputs),
            "tensors": list(self.tensors),
        }


class _Builder:
    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []

    def add(
        self,
        kind: str,
        inputs: Iterable[str],
        outputs: Iterable[str],
        *,
        tensors: Iterable[str] = (),
        layer: int | None = None,
    ) -> None:
        if kind not in OPERATOR_CATALOG:
            raise Qwen3GraphError(f"unknown operator kind {kind!r}")
        self.nodes.append(
            GraphNode(
                len(self.nodes),
                kind,
                tuple(inputs),
                tuple(outputs),
                tuple(tensors),
                layer,
            )
        )


def build_graph_nodes(config: Mapping[str, Any]) -> tuple[GraphNode, ...]:
    """Build the complete 36-layer prefill/decode graph in source order."""

    specs = build_tensor_specs(config)
    expected_names = {spec.name for spec in specs}
    builder = _Builder()
    builder.add(
        "TOKEN_EMBEDDING_LOOKUP",
        ("input.token_ids",),
        ("hidden.0",),
        tensors=("model.embed_tokens.weight",),
    )
    hidden = "hidden.0"
    for layer in range(int(config["num_hidden_layers"])):
        base = f"model.layers.{layer}"
        prefix = f"layer.{layer}"
        builder.add(
            "RMS_NORM",
            (hidden,),
            (f"{prefix}.attention_norm",),
            tensors=(f"{base}.input_layernorm.weight",),
            layer=layer,
        )
        for projection, output in (
            ("q_proj", "q_raw"),
            ("k_proj", "k_raw"),
            ("v_proj", "v"),
        ):
            builder.add(
                "LINEAR",
                (f"{prefix}.attention_norm",),
                (f"{prefix}.{output}",),
                tensors=(f"{base}.self_attn.{projection}.weight",),
                layer=layer,
            )
        builder.add(
            "RMS_NORM",
            (f"{prefix}.q_raw",),
            (f"{prefix}.q_norm",),
            tensors=(f"{base}.self_attn.q_norm.weight",),
            layer=layer,
        )
        builder.add(
            "RMS_NORM",
            (f"{prefix}.k_raw",),
            (f"{prefix}.k_norm",),
            tensors=(f"{base}.self_attn.k_norm.weight",),
            layer=layer,
        )
        builder.add(
            "ROPE",
            (f"{prefix}.q_norm", f"{prefix}.k_norm"),
            (f"{prefix}.q_rotary", f"{prefix}.k_rotary"),
            layer=layer,
        )
        builder.add(
            "KV_COMMIT",
            (f"{prefix}.k_rotary", f"{prefix}.v"),
            (f"state.kv.{layer}",),
            layer=layer,
        )
        builder.add(
            "GQA_CAUSAL_ATTENTION",
            (f"{prefix}.q_rotary", f"state.kv.{layer}"),
            (f"{prefix}.attention",),
            layer=layer,
        )
        builder.add(
            "LINEAR",
            (f"{prefix}.attention",),
            (f"{prefix}.attention_projected",),
            tensors=(f"{base}.self_attn.o_proj.weight",),
            layer=layer,
        )
        builder.add(
            "RESIDUAL_ADD",
            (hidden, f"{prefix}.attention_projected"),
            (f"{prefix}.post_attention",),
            layer=layer,
        )
        builder.add(
            "RMS_NORM",
            (f"{prefix}.post_attention",),
            (f"{prefix}.mlp_norm",),
            tensors=(f"{base}.post_attention_layernorm.weight",),
            layer=layer,
        )
        builder.add(
            "LINEAR",
            (f"{prefix}.mlp_norm",),
            (f"{prefix}.gate",),
            tensors=(f"{base}.mlp.gate_proj.weight",),
            layer=layer,
        )
        builder.add(
            "LINEAR",
            (f"{prefix}.mlp_norm",),
            (f"{prefix}.up",),
            tensors=(f"{base}.mlp.up_proj.weight",),
            layer=layer,
        )
        builder.add(
            "SILU_MUL",
            (f"{prefix}.gate", f"{prefix}.up"),
            (f"{prefix}.gated_mlp",),
            layer=layer,
        )
        builder.add(
            "LINEAR",
            (f"{prefix}.gated_mlp",),
            (f"{prefix}.mlp_projected",),
            tensors=(f"{base}.mlp.down_proj.weight",),
            layer=layer,
        )
        hidden = f"hidden.{layer + 1}"
        builder.add(
            "RESIDUAL_ADD",
            (f"{prefix}.post_attention", f"{prefix}.mlp_projected"),
            (hidden,),
            layer=layer,
        )
    builder.add(
        "RMS_NORM",
        (hidden,),
        ("hidden.final_norm",),
        tensors=("model.norm.weight",),
    )
    builder.add(
        "LAST_TOKEN_SELECT",
        ("hidden.final_norm",),
        ("hidden.last_token",),
    )
    builder.add(
        "LINEAR",
        ("hidden.last_token",),
        ("output.logits",),
        tensors=("lm_head.weight",),
    )
    nodes = tuple(builder.nodes)
    _validate_nodes(nodes, expected_names)
    return nodes


def _validate_nodes(nodes: tuple[GraphNode, ...], expected_tensors: set[str]) -> None:
    if not nodes:
        raise Qwen3GraphError("Qwen3 graph is empty")
    available = {"input.token_ids"}
    producers: set[str] = set()
    tensor_uses: Counter[str] = Counter()
    layer_kv_commits: Counter[int] = Counter()
    for expected_index, node in enumerate(nodes):
        if node.index != expected_index:
            raise Qwen3GraphError("graph node indices are not contiguous")
        missing_inputs = sorted(set(node.inputs) - available)
        if missing_inputs:
            raise Qwen3GraphError(
                f"{node.node_id} reads unavailable values {missing_inputs}"
            )
        if not node.outputs or any(output in producers for output in node.outputs):
            raise Qwen3GraphError(f"{node.node_id} has empty or duplicate outputs")
        available.update(node.outputs)
        producers.update(node.outputs)
        tensor_uses.update(node.tensors)
        if node.kind == "KV_COMMIT":
            if node.layer is None:
                raise Qwen3GraphError("KV_COMMIT lacks a layer")
            layer_kv_commits[node.layer] += 1
    if set(tensor_uses) != expected_tensors:
        raise Qwen3GraphError(
            "graph tensor coverage differs: "
            f"missing={sorted(expected_tensors - set(tensor_uses))[:8]}, "
            f"extra={sorted(set(tensor_uses) - expected_tensors)[:8]}"
        )
    duplicated = sorted(name for name, count in tensor_uses.items() if count != 1)
    if duplicated:
        raise Qwen3GraphError(
            f"checkpoint tensors do not have one consumer: {duplicated[:8]}"
        )
    if layer_kv_commits != Counter({layer: 1 for layer in range(LAYER_COUNT)}):
        raise Qwen3GraphError("every layer must have exactly one KV commit")
    if "output.logits" not in available:
        raise Qwen3GraphError("graph does not produce final logits")


def _sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def build_official_graph_contract() -> dict[str, Any]:
    """Emit the deterministic operator-complete semantic graph contract."""

    config = load_official_config()
    specs: tuple[TensorSpec, ...] = build_tensor_specs(config)
    nodes = build_graph_nodes(config)
    kinds = Counter(node.kind for node in nodes)
    matrix_nodes = kinds["LINEAR"]
    body = {
        "coverage": {
            "all_checkpoint_tensors_consumed_once": True,
            "all_layers_have_kv_commit": True,
            "layer_count": LAYER_COUNT,
            "matrix_node_count": matrix_nodes,
            "node_count": len(nodes),
            "operator_kind_count": len(kinds),
            "operator_kind_counts": dict(sorted(kinds.items())),
            "tensor_count": len(specs),
        },
        "execution_contract": {
            "batch_size": 1,
            "cache_commit": "one atomic append per layer after request bounds validation",
            "context_overflow": "fail before graph execution or KV mutation",
            "decode_boundary": "last-position logits followed by host token selection",
            "maximum_total_context_tokens": TARGET_CONTEXT_TOKENS,
            "prefill": "one or more uncached tokens with causal attention",
            "sliding_window": False,
        },
        "model": {
            "config_sha256": CONFIG_SHA256,
            "id": MODEL_ID,
            "repository": REPOSITORY,
            "revision": REVISION,
        },
        "nodes": [node.record() for node in nodes],
        "numeric_contract": {
            "attention_scale": "1/sqrt(128)",
            "checkpoint_storage": "BF16",
            "linear_compute": "BF16 operands; backend accumulation reported at execution",
            "rms_norm": "FP32 mean-square and rsqrt, BF16 normalized value and weight multiply",
            "rope": "FP32 frequency/matmul/trigonometry, then BF16 rotation",
            "softmax": "FP32 reference semantics with BF16 attention output",
        },
        "operators": [item.record() for item in _OPERATORS],
        "schema": GRAPH_SCHEMA,
        "source_lock": {
            "configuration_qwen3_sha256": TRANSFORMERS_CONFIG_SOURCE_SHA256,
            "modeling_qwen3_sha256": TRANSFORMERS_MODEL_SOURCE_SHA256,
            "modular_qwen3_sha256": TRANSFORMERS_MODULAR_SOURCE_SHA256,
            "transformers_version": TRANSFORMERS_VERSION,
        },
    }
    return {**body, "graph_id": _sha256(body)}


__all__ = [
    "GRAPH_SCHEMA",
    "GraphNode",
    "OPERATOR_CATALOG",
    "OperatorRequirement",
    "Qwen3GraphError",
    "build_graph_nodes",
    "build_official_graph_contract",
]
