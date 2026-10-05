"""Qwen3-8B semantic-artifact adapter for production Model Graph v2.

The adapter consumes only the Qwen semantic graph, immutable checkpoint lock,
and pinned configuration.  It never reads a ROM/HBM physical map, schedule,
microcode program, or runtime implementation.  The resulting graph therefore
retains source semantics and exact checkpoint payload identities without
inheriting either backend's placement assumptions.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping

from .common import (
    ArtifactError,
    canonical_json_bytes,
    exact_keys,
    load_strict_json,
    require_int,
    require_sha256,
    sha256_bytes,
)
from .production_model import (
    ProductionModelGraph,
    compute_graph_id,
    parse_production_model_graph,
)


QWEN_GRAPH_SCHEMA = "opentallas.qwen3.semantic_graph.v1"
CHECKPOINT_LOCK_SCHEMA = "opentallas.checkpoint_lock.v1"
NUMERIC_PROFILE = "qwen3_bf16_gqa_target_v1"


class Qwen3ProductionAdapterError(ArtifactError):
    """Raised when the Qwen handoff is incomplete or source-inconsistent."""


@dataclass(frozen=True)
class Qwen3ArtifactIdentity:
    """Immutable source and topology identity accepted by one adapter profile."""

    model_id: str
    repository: str
    revision: str
    graph_id: str | None
    checkpoint_lock_id: str | None
    config_sha256: str | None
    layer_count: int
    tensor_count: int
    node_count: int
    payload_bytes: int | None
    hidden_size: int
    intermediate_size: int
    vocabulary_size: int
    attention_heads: int
    key_value_heads: int
    head_dim: int
    maximum_position_embeddings: int
    target_context_tokens: int


PINNED_QWEN3_8B = Qwen3ArtifactIdentity(
    model_id="qwen3-8b",
    repository="Qwen/Qwen3-8B",
    revision="b968826d9c46dd6066d109eabc6255188de91218",
    graph_id="fa8ed910df6506a06334d01a63f68aa592f5c56d7a4659de550f3e570a941a44",
    checkpoint_lock_id=(
        "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
    ),
    config_sha256=(
        "f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30"
    ),
    layer_count=36,
    tensor_count=399,
    node_count=616,
    payload_bytes=16_381_470_720,
    hidden_size=4096,
    intermediate_size=12288,
    vocabulary_size=151936,
    attention_heads=32,
    key_value_heads=8,
    head_dim=128,
    maximum_position_embeddings=40960,
    target_context_tokens=8000,
)


_KINDS = frozenset(
    {
        "TOKEN_EMBEDDING_LOOKUP",
        "RMS_NORM",
        "LINEAR",
        "ROPE",
        "KV_COMMIT",
        "GQA_CAUSAL_ATTENTION",
        "RESIDUAL_ADD",
        "SILU_MUL",
        "LAST_TOKEN_SELECT",
    }
)
_KIND_MAP = {
    "TOKEN_EMBEDDING_LOOKUP": "EMBEDDING_LOOKUP",
    "RMS_NORM": "RMS_NORM",
    "LINEAR": "MATMUL",
    "ROPE": "ROPE",
    "KV_COMMIT": "KV_PREPARE",
    "GQA_CAUSAL_ATTENTION": "ATTENTION",
    "RESIDUAL_ADD": "ADD",
    "SILU_MUL": "SILU_MUL",
    "LAST_TOKEN_SELECT": "LAST_TOKEN_SELECT",
}
_NUMERIC_CONTRACT = {
    "TOKEN_EMBEDDING_LOOKUP": "bf16_payload_lookup_v1",
    "RMS_NORM": "qwen3_rmsnorm_fp32_bf16_v1",
    "LINEAR": "bf16_bf16_fp32_sequential_rne_v1",
    "ROPE": "qwen3_rope_fp32_bf16_v1",
    "KV_COMMIT": "bf16_byte_preserving_state_v1",
    "GQA_CAUSAL_ATTENTION": "qwen3_gqa_fp32_softmax_bf16_v1",
    "RESIDUAL_ADD": "bf16_add_rne_v1",
    "SILU_MUL": "qwen3_silu_mul_bf16_v1",
    "LAST_TOKEN_SELECT": "exact_index_select_v1",
}
_SOURCE_PATH = "transformers/models/qwen3/modeling_qwen3.py"


@dataclass(frozen=True)
class _LockedTensor:
    name: str
    dtype: str
    shape: tuple[int, ...]
    size_bytes: int
    payload_sha256: str


@dataclass(frozen=True)
class _Value:
    dtype: str
    shape: tuple[int | str, ...]


def _load_canonical(path: Path, label: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        value = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise Qwen3ProductionAdapterError(f"cannot load {label}: {exc}") from exc
    if canonical_json_bytes(value) != raw:
        raise Qwen3ProductionAdapterError(f"{label} is not canonically serialized")
    return value


def _body_id(value: Mapping[str, Any], identity_field: str) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            {key: item for key, item in value.items() if key != identity_field}
        )
    )


def _load_config(
    path: Path,
    graph: Mapping[str, Any],
    identity: Qwen3ArtifactIdentity,
) -> dict[str, Any]:
    try:
        payload = path.read_bytes()
        config = load_strict_json(path)
    except (OSError, ArtifactError) as exc:
        raise Qwen3ProductionAdapterError(f"cannot load Qwen config: {exc}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    graph_model = graph.get("model")
    if not isinstance(graph_model, dict) or graph_model.get("config_sha256") != digest:
        raise Qwen3ProductionAdapterError("Qwen graph does not bind the config bytes")
    if identity.config_sha256 is not None and digest != identity.config_sha256:
        raise Qwen3ProductionAdapterError("Qwen config digest differs from the profile")
    expected = {
        "hidden_size": identity.hidden_size,
        "intermediate_size": identity.intermediate_size,
        "vocab_size": identity.vocabulary_size,
        "num_attention_heads": identity.attention_heads,
        "num_key_value_heads": identity.key_value_heads,
        "num_hidden_layers": identity.layer_count,
        "head_dim": identity.head_dim,
        "max_position_embeddings": identity.maximum_position_embeddings,
        "torch_dtype": "bfloat16",
        "tie_word_embeddings": False,
        "use_cache": True,
    }
    for key, expected_value in expected.items():
        if config.get(key) != expected_value:
            raise Qwen3ProductionAdapterError(
                f"Qwen config {key!r} differs from the adapter profile"
            )
    if identity.target_context_tokens > identity.maximum_position_embeddings:
        raise Qwen3ProductionAdapterError("target context exceeds Qwen position bound")
    return config


def _validate_graph(
    graph: dict[str, Any],
    identity: Qwen3ArtifactIdentity,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]], str]:
    exact_keys(
        graph,
        {
            "coverage",
            "execution_contract",
            "graph_id",
            "model",
            "nodes",
            "numeric_contract",
            "operators",
            "schema",
            "source_lock",
        },
        set(),
        "Qwen semantic graph",
    )
    if graph["schema"] != QWEN_GRAPH_SCHEMA:
        raise Qwen3ProductionAdapterError("unsupported Qwen semantic graph schema")
    graph_id = require_sha256(graph["graph_id"], "Qwen graph_id")
    if graph_id != _body_id(graph, "graph_id"):
        raise Qwen3ProductionAdapterError("Qwen graph_id differs from its content")
    if identity.graph_id is not None and graph_id != identity.graph_id:
        raise Qwen3ProductionAdapterError("Qwen graph_id differs from the pinned profile")
    model = graph["model"]
    if not isinstance(model, dict) or (
        model.get("id"), model.get("repository"), model.get("revision")
    ) != (identity.model_id, identity.repository, identity.revision):
        raise Qwen3ProductionAdapterError("Qwen graph model identity differs")
    coverage = graph["coverage"]
    if (
        not isinstance(coverage, dict)
        or coverage.get("node_count") != identity.node_count
        or coverage.get("layer_count") != identity.layer_count
        or coverage.get("tensor_count") != identity.tensor_count
        or coverage.get("operator_kind_count") != len(_KINDS)
        or coverage.get("all_checkpoint_tensors_consumed_once") is not True
        or coverage.get("all_layers_have_kv_commit") is not True
    ):
        raise Qwen3ProductionAdapterError("Qwen graph coverage is incomplete")
    execution = graph["execution_contract"]
    if (
        not isinstance(execution, dict)
        or execution.get("batch_size") != 1
        or execution.get("maximum_total_context_tokens")
        != identity.target_context_tokens
        or execution.get("sliding_window") is not False
    ):
        raise Qwen3ProductionAdapterError("Qwen execution contract differs")
    source_lock = graph["source_lock"]
    if not isinstance(source_lock, dict):
        raise Qwen3ProductionAdapterError("Qwen source lock is malformed")
    modeling_sha256 = require_sha256(
        source_lock.get("modeling_qwen3_sha256"),
        "Qwen modeling_qwen3_sha256",
    )
    operators = graph["operators"]
    if not isinstance(operators, list) or len(operators) != len(_KINDS):
        raise Qwen3ProductionAdapterError("Qwen operator catalog is incomplete")
    by_kind: dict[str, dict[str, str]] = {}
    for index, record in enumerate(operators):
        if not isinstance(record, dict):
            raise Qwen3ProductionAdapterError(f"Qwen operator {index} is malformed")
        exact_keys(
            record,
            {
                "arithmetic",
                "kind",
                "lowering",
                "semantics",
                "source_symbol",
                "state_effect",
            },
            set(),
            f"Qwen operator {index}",
        )
        kind = record["kind"]
        if kind not in _KINDS or kind in by_kind:
            raise Qwen3ProductionAdapterError("Qwen operator kinds differ")
        if any(not isinstance(record[key], str) or not record[key] for key in record):
            raise Qwen3ProductionAdapterError("Qwen operator catalog has empty fields")
        by_kind[kind] = record
    if set(by_kind) != _KINDS:
        raise Qwen3ProductionAdapterError("Qwen operator catalog kinds differ")
    nodes = graph["nodes"]
    if not isinstance(nodes, list) or len(nodes) != identity.node_count:
        raise Qwen3ProductionAdapterError("Qwen graph node count differs")
    return nodes, by_kind, modeling_sha256


def _locked_tensors(
    lock: dict[str, Any],
    identity: Qwen3ArtifactIdentity,
) -> tuple[dict[str, _LockedTensor], str]:
    exact_keys(
        lock,
        {"checkpoint", "files", "lock_id", "schema", "shards", "source"},
        set(),
        "Qwen checkpoint lock",
    )
    if lock["schema"] != CHECKPOINT_LOCK_SCHEMA:
        raise Qwen3ProductionAdapterError("unsupported checkpoint lock schema")
    lock_id = require_sha256(lock["lock_id"], "Qwen checkpoint lock_id")
    if lock_id != _body_id(lock, "lock_id"):
        raise Qwen3ProductionAdapterError("Qwen checkpoint lock_id differs from content")
    if identity.checkpoint_lock_id is not None and lock_id != identity.checkpoint_lock_id:
        raise Qwen3ProductionAdapterError("Qwen checkpoint lock differs from profile")
    source = lock["source"]
    if not isinstance(source, dict) or (
        source.get("repository"), source.get("revision")
    ) != (identity.repository, identity.revision):
        raise Qwen3ProductionAdapterError("Qwen checkpoint source identity differs")
    checkpoint = lock["checkpoint"]
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("tensor_count") != identity.tensor_count
        or (
            identity.payload_bytes is not None
            and checkpoint.get("payload_bytes") != identity.payload_bytes
        )
    ):
        raise Qwen3ProductionAdapterError("Qwen checkpoint summary differs")
    shards = lock["shards"]
    if not isinstance(shards, list) or not shards:
        raise Qwen3ProductionAdapterError("Qwen checkpoint lock has no shards")
    result: dict[str, _LockedTensor] = {}
    total_payload = 0
    for shard_index, shard in enumerate(shards):
        if not isinstance(shard, dict) or not isinstance(shard.get("tensors"), list):
            raise Qwen3ProductionAdapterError(
                f"Qwen checkpoint shard {shard_index} is malformed"
            )
        for tensor_index, raw in enumerate(shard["tensors"]):
            if not isinstance(raw, dict):
                raise Qwen3ProductionAdapterError(
                    f"Qwen locked tensor {shard_index}:{tensor_index} is malformed"
                )
            exact_keys(
                raw,
                {
                    "data_offsets",
                    "dtype",
                    "name",
                    "payload_sha256",
                    "shape",
                    "size_bytes",
                },
                set(),
                f"Qwen locked tensor {shard_index}:{tensor_index}",
            )
            name = raw["name"]
            shape_raw = raw["shape"]
            if (
                not isinstance(name, str)
                or not name
                or name in result
                or raw["dtype"] != "BF16"
                or not isinstance(shape_raw, list)
                or not shape_raw
            ):
                raise Qwen3ProductionAdapterError("Qwen locked tensor metadata differs")
            shape = tuple(
                require_int(
                    value,
                    f"Qwen tensor {name}.shape[{index}]",
                    minimum=1,
                    maximum=1 << 30,
                )
                for index, value in enumerate(shape_raw)
            )
            size = require_int(
                raw["size_bytes"], f"Qwen tensor {name}.size_bytes", minimum=1
            )
            offsets = raw["data_offsets"]
            if (
                size != math.prod(shape) * 2
                or not isinstance(offsets, list)
                or len(offsets) != 2
                or offsets[1] - offsets[0] != size
            ):
                raise Qwen3ProductionAdapterError(
                    f"Qwen tensor {name!r} byte extent differs"
                )
            result[name] = _LockedTensor(
                name,
                "bf16",
                shape,
                size,
                require_sha256(
                    raw["payload_sha256"], f"Qwen tensor {name}.payload_sha256"
                ),
            )
            total_payload += size
    if len(result) != identity.tensor_count or total_payload != checkpoint["payload_bytes"]:
        raise Qwen3ProductionAdapterError("Qwen locked tensor coverage differs")
    return result, lock_id


def _input_tensor() -> dict[str, Any]:
    return {
        "dtype": "i64",
        "id": "input.token_ids",
        "layout": "bs",
        "role": "input",
        "shape": [1, "span_tokens"],
    }


def _weight_tensor(tensor: _LockedTensor, lock_id: str) -> dict[str, Any]:
    return {
        "binding": {
            "checkpoint_lock_id": lock_id,
            "kind": "checkpoint",
            "payload_sha256": tensor.payload_sha256,
            "sources": [
                {
                    "dtype": tensor.dtype,
                    "payload_sha256": tensor.payload_sha256,
                    "shape": list(tensor.shape),
                    "tensor_name": tensor.name,
                }
            ],
            "transform": {"kind": "identity"},
        },
        "dtype": tensor.dtype,
        "id": tensor.name,
        "layout": "row_major",
        "role": "weight",
        "shape": list(tensor.shape),
    }


def _tensor_record(
    tensor_id: str,
    value: _Value,
    *,
    role: str = "activation",
) -> dict[str, Any]:
    return {
        "dtype": value.dtype,
        "id": tensor_id,
        "layout": "bsh" if len(value.shape) == 3 else "scalar",
        "role": role,
        "shape": list(value.shape),
    }


def _infer_outputs(
    kind: str,
    inputs: tuple[_Value, ...],
    weights: tuple[_LockedTensor, ...],
    output_count: int,
    identity: Qwen3ArtifactIdentity,
) -> tuple[_Value, ...]:
    if kind == "TOKEN_EMBEDDING_LOOKUP":
        if len(inputs) != 1 or len(weights) != 1 or len(weights[0].shape) != 2:
            raise Qwen3ProductionAdapterError("Qwen embedding operands differ")
        result = (_Value("bf16", (*inputs[0].shape, weights[0].shape[1])),)
    elif kind == "RMS_NORM":
        if (
            len(inputs) != 1
            or len(weights) != 1
            or len(weights[0].shape) != 1
            or not isinstance(inputs[0].shape[-1], int)
            or inputs[0].shape[-1] % weights[0].shape[0]
        ):
            raise Qwen3ProductionAdapterError("Qwen RMSNorm operands differ")
        result = (inputs[0],)
    elif kind == "LINEAR":
        if (
            len(inputs) != 1
            or len(weights) != 1
            or len(weights[0].shape) != 2
            or weights[0].shape[1] != inputs[0].shape[-1]
        ):
            raise Qwen3ProductionAdapterError("Qwen linear operands differ")
        result = (_Value("bf16", (*inputs[0].shape[:-1], weights[0].shape[0])),)
    elif kind == "ROPE":
        if len(inputs) != 2 or len(weights) != 0:
            raise Qwen3ProductionAdapterError("Qwen RoPE operands differ")
        result = inputs
    elif kind == "KV_COMMIT":
        if (
            len(inputs) != 2
            or len(weights) != 0
            or inputs[0].shape != inputs[1].shape
            or inputs[0].shape[-1] != identity.key_value_heads * identity.head_dim
        ):
            raise Qwen3ProductionAdapterError("Qwen KV operands differ")
        result = (_Value("u32", (1,)),)
    elif kind == "GQA_CAUSAL_ATTENTION":
        if (
            len(inputs) != 2
            or inputs[0].shape[-1] != identity.attention_heads * identity.head_dim
            or inputs[1] != _Value("u32", (1,))
        ):
            raise Qwen3ProductionAdapterError("Qwen GQA operands differ")
        result = (_Value("bf16", (*inputs[0].shape[:-1], identity.hidden_size)),)
    elif kind in {"RESIDUAL_ADD", "SILU_MUL"}:
        if len(inputs) != 2 or inputs[0] != inputs[1] or weights:
            raise Qwen3ProductionAdapterError(f"Qwen {kind} operands differ")
        result = (inputs[0],)
    elif kind == "LAST_TOKEN_SELECT":
        if len(inputs) != 1 or weights or len(inputs[0].shape) != 3:
            raise Qwen3ProductionAdapterError("Qwen last-token operands differ")
        result = (_Value(inputs[0].dtype, (inputs[0].shape[0], 1, inputs[0].shape[2])),)
    else:  # pragma: no cover - caller validates the kind first.
        raise Qwen3ProductionAdapterError(f"unknown Qwen operation {kind!r}")
    if len(result) != output_count:
        raise Qwen3ProductionAdapterError(f"Qwen {kind} output arity differs")
    return result


def _entrypoint_predicate(*, decode: bool, context: int) -> dict[str, Any]:
    terms: list[dict[str, Any]] = [
        {
            "kind": "affine",
            "operator": "eq",
            "terms": [
                {"coefficient": 1, "symbol": "position_end"},
                {"coefficient": -1, "symbol": "position_start"},
                {"coefficient": -1, "symbol": "span_tokens"},
            ],
            "value": 0,
        },
        {
            "kind": "compare",
            "operator": "le",
            "symbol": "position_end",
            "value": context,
        },
    ]
    if decode:
        terms.append(
            {
                "kind": "compare",
                "operator": "eq",
                "symbol": "span_tokens",
                "value": 1,
            }
        )
    return {"kind": "all", "terms": terms}


def export_qwen3_production_graph(
    semantic_graph_path: Path,
    checkpoint_lock_path: Path,
    config_path: Path,
    *,
    identity: Qwen3ArtifactIdentity = PINNED_QWEN3_8B,
) -> ProductionModelGraph:
    """Export a complete pinned Qwen handoff into production Model Graph v2."""

    try:
        graph = _load_canonical(Path(semantic_graph_path), "Qwen semantic graph")
        lock = _load_canonical(Path(checkpoint_lock_path), "Qwen checkpoint lock")
        nodes, operator_catalog, modeling_sha256 = _validate_graph(graph, identity)
        _load_config(Path(config_path), graph, identity)
        locked, lock_id = _locked_tensors(lock, identity)
    except Qwen3ProductionAdapterError:
        raise
    except ArtifactError as exc:
        raise Qwen3ProductionAdapterError(str(exc)) from exc

    used_weights = Counter(
        name
        for node in nodes
        if isinstance(node, dict)
        for name in node.get("tensors", [])
    )
    if set(used_weights) != set(locked) or any(count != 1 for count in used_weights.values()):
        raise Qwen3ProductionAdapterError(
            "Qwen graph does not consume every locked tensor exactly once"
        )

    values: dict[str, _Value] = {
        "input.token_ids": _Value("i64", (1, "span_tokens"))
    }
    tensors: list[dict[str, Any]] = [_input_tensor()]
    tensors.extend(_weight_tensor(locked[name], lock_id) for name in sorted(locked))
    operations: list[dict[str, Any]] = []
    state_ids = tuple(f"kv.layer.{layer}" for layer in range(identity.layer_count))
    kv_counts: Counter[int] = Counter()
    kind_counts: Counter[str] = Counter()

    for expected_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise Qwen3ProductionAdapterError(f"Qwen node {expected_index} is malformed")
        exact_keys(
            node,
            {"index", "inputs", "kind", "layer", "node_id", "outputs", "tensors"},
            set(),
            f"Qwen node {expected_index}",
        )
        if node["index"] != expected_index or node["node_id"] != f"node.{expected_index:04d}":
            raise Qwen3ProductionAdapterError("Qwen node identity/order differs")
        kind = node["kind"]
        if kind not in _KINDS:
            raise Qwen3ProductionAdapterError(f"Qwen node has unknown kind {kind!r}")
        kind_counts[kind] += 1
        raw_inputs = node["inputs"]
        raw_outputs = node["outputs"]
        raw_weights = node["tensors"]
        if (
            not isinstance(raw_inputs, list)
            or not raw_inputs
            or not isinstance(raw_outputs, list)
            or not raw_outputs
            or not isinstance(raw_weights, list)
            or any(name not in locked for name in raw_weights)
        ):
            raise Qwen3ProductionAdapterError(f"Qwen node {expected_index} operands differ")
        try:
            input_values = tuple(values[name] for name in raw_inputs)
        except KeyError as exc:
            raise Qwen3ProductionAdapterError(
                f"Qwen node {expected_index} reads an unavailable value"
            ) from exc
        weight_values = tuple(locked[name] for name in raw_weights)
        inferred = _infer_outputs(
            kind,
            input_values,
            weight_values,
            len(raw_outputs),
            identity,
        )
        for name, value in zip(raw_outputs, inferred, strict=True):
            if name in values or name in locked:
                raise Qwen3ProductionAdapterError(f"Qwen value {name!r} is redefined")
            values[name] = value
            tensors.append(_tensor_record(name, value))

        layer = node["layer"]
        if layer is not None and (
            isinstance(layer, bool)
            or not isinstance(layer, int)
            or not 0 <= layer < identity.layer_count
        ):
            raise Qwen3ProductionAdapterError(f"Qwen node {expected_index} layer differs")
        effects: list[dict[str, str]] = []
        if kind == "KV_COMMIT":
            if layer is None:
                raise Qwen3ProductionAdapterError("Qwen KV prepare lacks a layer")
            kv_counts[layer] += 1
            effects = [
                {"action": "read_committed", "state": state_ids[layer]},
                {"action": "prepare", "state": state_ids[layer]},
            ]
        elif kind == "GQA_CAUSAL_ATTENTION":
            if layer is None:
                raise Qwen3ProductionAdapterError("Qwen attention lacks a layer")
            effects = [{"action": "read_prepared", "state": state_ids[layer]}]

        attributes: dict[str, Any] = {"source_kind": kind}
        if layer is not None:
            attributes["layer"] = layer
        if raw_weights:
            attributes["weight_ids"] = list(raw_weights)
        if kind == "LINEAR":
            attributes["transpose_weight"] = True
        elif kind == "RMS_NORM":
            attributes.update(
                {
                    "epsilon": 1e-6,
                    "normalization_width": weight_values[0].shape[0],
                }
            )
        elif kind == "GQA_CAUSAL_ATTENTION":
            attributes.update(
                {
                    "head_dim": identity.head_dim,
                    "key_value_heads": identity.key_value_heads,
                    "query_heads": identity.attention_heads,
                    "scale_denominator_sqrt": identity.head_dim,
                }
            )
        elif kind == "ROPE":
            attributes.update({"head_dim": identity.head_dim, "position_symbol": "position_start"})
        operations.append(
            {
                "attributes": attributes,
                "effects": effects,
                "id": node["node_id"],
                "inputs": [*raw_inputs, *raw_weights],
                "kind": _KIND_MAP[kind],
                "numeric_contract": _NUMERIC_CONTRACT[kind],
                "outputs": list(raw_outputs),
                "phases": ["prefill", "decode"],
                "predicate": {"kind": "always"},
                "source_anchor": {
                    "path": _SOURCE_PATH,
                    "source_sha256": modeling_sha256,
                    "symbol": operator_catalog[kind]["source_symbol"],
                },
            }
        )

    if kv_counts != Counter({layer: 1 for layer in range(identity.layer_count)}):
        raise Qwen3ProductionAdapterError("Qwen graph does not prepare every KV layer once")
    if set(kind_counts) != _KINDS:
        raise Qwen3ProductionAdapterError("Qwen graph does not exercise every operator kind")
    logits = "output.logits"
    if logits not in values or values[logits] != _Value(
        "bf16", (1, 1, identity.vocabulary_size)
    ):
        raise Qwen3ProductionAdapterError("Qwen graph does not produce complete logits")
    # The source graph's logits become an internal value because durable state
    # is committed only after every model-forward operation has succeeded.
    for tensor in tensors:
        if tensor["id"] == logits:
            tensor["role"] = "activation"
            break
    committed_logits = "output.committed_logits"
    tensors.append(_tensor_record(committed_logits, values[logits], role="output"))
    operations.append(
        {
            "attributes": {"atomic_state_count": identity.layer_count},
            "effects": [
                {"action": "commit", "state": state_id} for state_id in state_ids
            ],
            "id": "state.commit",
            "inputs": [logits],
            "kind": "STATE_COMMIT",
            "numeric_contract": "bf16_byte_preserving_state_v1",
            "outputs": [committed_logits],
            "phases": ["prefill", "decode"],
            "predicate": {"kind": "always"},
            "source_anchor": {
                "path": _SOURCE_PATH,
                "source_sha256": modeling_sha256,
                "symbol": "Qwen3ForCausalLM.forward:successful request boundary",
            },
        }
    )

    source_identity = {
        "checkpoint_lock_id": lock_id,
        "config_sha256": graph["model"]["config_sha256"],
        "semantic_graph_id": graph["graph_id"],
        "upstream_source_lock": graph["source_lock"],
    }
    raw: dict[str, Any] = {
        "entrypoints": [
            {
                "inputs": ["input.token_ids"],
                "outputs": [committed_logits],
                "phase": "prefill",
                "predicate": _entrypoint_predicate(
                    decode=False, context=identity.target_context_tokens
                ),
                "states": list(state_ids),
            },
            {
                "inputs": ["input.token_ids"],
                "outputs": [committed_logits],
                "phase": "decode",
                "predicate": _entrypoint_predicate(
                    decode=True, context=identity.target_context_tokens
                ),
                "states": list(state_ids),
            },
        ],
        "graph_id": "0" * 64,
        "model_id": identity.model_id,
        "numeric_profile": NUMERIC_PROFILE,
        "operations": operations,
        "schema": "opentallas.model_graph.v2",
        "source": {
            "repository": identity.repository,
            "revision": identity.revision,
            "source_lock_id": sha256_bytes(canonical_json_bytes(source_identity)),
        },
        "state_resources": [
            {
                "class": "kv_cache",
                "dtype": "bf16",
                "id": state_id,
                "initialization": "zero",
                "layout": "kvbhsd",
                "shape": [
                    2,
                    1,
                    identity.key_value_heads,
                    "context_capacity",
                    identity.head_dim,
                ],
                "transaction": "prepare_commit",
            }
            for state_id in state_ids
        ],
        "symbols": [
            {
                "binding": {"kind": "compile_time"},
                "default": identity.target_context_tokens,
                "id": "context_capacity",
                "maximum": identity.target_context_tokens,
                "minimum": identity.target_context_tokens,
                "multiple_of": identity.target_context_tokens,
            },
            {
                "binding": {"field": "position_end", "kind": "request"},
                "default": 1,
                "id": "position_end",
                "maximum": identity.target_context_tokens,
                "minimum": 1,
                "multiple_of": 1,
            },
            {
                "binding": {"field": "position_start", "kind": "request"},
                "default": 0,
                "id": "position_start",
                "maximum": identity.target_context_tokens - 1,
                "minimum": 0,
                "multiple_of": 1,
            },
            {
                "binding": {"field": "span_tokens", "kind": "request"},
                "default": 1,
                "id": "span_tokens",
                "maximum": identity.target_context_tokens,
                "minimum": 1,
                "multiple_of": 1,
            },
        ],
        "tensors": tensors,
    }
    raw["graph_id"] = compute_graph_id(raw)
    try:
        return parse_production_model_graph(raw)
    except ArtifactError as exc:
        raise Qwen3ProductionAdapterError(
            f"Qwen production graph failed neutral-IR admission: {exc}"
        ) from exc


def publish_qwen3_production_graph(
    semantic_graph_path: Path,
    checkpoint_lock_path: Path,
    config_path: Path,
    output_path: Path,
    *,
    identity: Qwen3ArtifactIdentity = PINNED_QWEN3_8B,
) -> ProductionModelGraph:
    """Atomically publish one canonical v2 graph without overwriting a file."""

    graph = export_qwen3_production_graph(
        semantic_graph_path,
        checkpoint_lock_path,
        config_path,
        identity=identity,
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_json_bytes(graph.to_dict())
    descriptor, temporary_name = tempfile.mkstemp(
        dir=output.parent,
        prefix=f".{output.name}.",
        suffix=".tmp",
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, output)
        except FileExistsError as exc:
            raise Qwen3ProductionAdapterError(
                f"output already exists and will not be overwritten: {output}"
            ) from exc
    finally:
        temporary.unlink(missing_ok=True)
    return graph


__all__ = [
    "NUMERIC_PROFILE",
    "PINNED_QWEN3_8B",
    "Qwen3ArtifactIdentity",
    "Qwen3ProductionAdapterError",
    "export_qwen3_production_graph",
    "publish_qwen3_production_graph",
]
