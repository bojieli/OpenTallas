from __future__ import annotations

from collections import Counter
import hashlib
from pathlib import Path

import pytest

from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.qwen3_adapter import (
    Qwen3ArtifactIdentity,
    Qwen3ProductionAdapterError,
    export_qwen3_production_graph,
    publish_qwen3_production_graph,
)


HASH = "3" * 64


def _identity() -> Qwen3ArtifactIdentity:
    return Qwen3ArtifactIdentity(
        model_id="qwen3-mini-fixture",
        repository="example/Qwen3-Mini",
        revision="0123456789abcdef",
        graph_id=None,
        checkpoint_lock_id=None,
        config_sha256=None,
        layer_count=1,
        tensor_count=14,
        node_count=21,
        payload_bytes=None,
        hidden_size=4,
        intermediate_size=6,
        vocabulary_size=8,
        attention_heads=2,
        key_value_heads=1,
        head_dim=2,
        maximum_position_embeddings=16,
        target_context_tokens=8,
    )


def _weights() -> dict[str, tuple[int, ...]]:
    return {
        "lm_head.weight": (8, 4),
        "model.embed_tokens.weight": (8, 4),
        "model.layers.0.input_layernorm.weight": (4,),
        "model.layers.0.mlp.down_proj.weight": (4, 6),
        "model.layers.0.mlp.gate_proj.weight": (6, 4),
        "model.layers.0.mlp.up_proj.weight": (6, 4),
        "model.layers.0.post_attention_layernorm.weight": (4,),
        "model.layers.0.self_attn.k_norm.weight": (2,),
        "model.layers.0.self_attn.k_proj.weight": (2, 4),
        "model.layers.0.self_attn.o_proj.weight": (4, 4),
        "model.layers.0.self_attn.q_norm.weight": (2,),
        "model.layers.0.self_attn.q_proj.weight": (4, 4),
        "model.layers.0.self_attn.v_proj.weight": (2, 4),
        "model.norm.weight": (4,),
    }


def _nodes() -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []

    def add(
        kind: str,
        inputs: list[str],
        outputs: list[str],
        *,
        tensors: list[str] | None = None,
        layer: int | None = None,
    ) -> None:
        index = len(nodes)
        nodes.append(
            {
                "index": index,
                "inputs": inputs,
                "kind": kind,
                "layer": layer,
                "node_id": f"node.{index:04d}",
                "outputs": outputs,
                "tensors": tensors or [],
            }
        )

    add(
        "TOKEN_EMBEDDING_LOOKUP",
        ["input.token_ids"],
        ["hidden.0"],
        tensors=["model.embed_tokens.weight"],
    )
    add(
        "RMS_NORM",
        ["hidden.0"],
        ["layer.0.attention_norm"],
        tensors=["model.layers.0.input_layernorm.weight"],
        layer=0,
    )
    for projection, output in (("q", "q_raw"), ("k", "k_raw"), ("v", "v")):
        add(
            "LINEAR",
            ["layer.0.attention_norm"],
            [f"layer.0.{output}"],
            tensors=[f"model.layers.0.self_attn.{projection}_proj.weight"],
            layer=0,
        )
    add(
        "RMS_NORM",
        ["layer.0.q_raw"],
        ["layer.0.q_norm"],
        tensors=["model.layers.0.self_attn.q_norm.weight"],
        layer=0,
    )
    add(
        "RMS_NORM",
        ["layer.0.k_raw"],
        ["layer.0.k_norm"],
        tensors=["model.layers.0.self_attn.k_norm.weight"],
        layer=0,
    )
    add(
        "ROPE",
        ["layer.0.q_norm", "layer.0.k_norm"],
        ["layer.0.q_rotary", "layer.0.k_rotary"],
        layer=0,
    )
    add(
        "KV_COMMIT",
        ["layer.0.k_rotary", "layer.0.v"],
        ["state.kv.0"],
        layer=0,
    )
    add(
        "GQA_CAUSAL_ATTENTION",
        ["layer.0.q_rotary", "state.kv.0"],
        ["layer.0.attention"],
        layer=0,
    )
    add(
        "LINEAR",
        ["layer.0.attention"],
        ["layer.0.attention_projected"],
        tensors=["model.layers.0.self_attn.o_proj.weight"],
        layer=0,
    )
    add(
        "RESIDUAL_ADD",
        ["hidden.0", "layer.0.attention_projected"],
        ["layer.0.post_attention"],
        layer=0,
    )
    add(
        "RMS_NORM",
        ["layer.0.post_attention"],
        ["layer.0.mlp_norm"],
        tensors=["model.layers.0.post_attention_layernorm.weight"],
        layer=0,
    )
    add(
        "LINEAR",
        ["layer.0.mlp_norm"],
        ["layer.0.gate"],
        tensors=["model.layers.0.mlp.gate_proj.weight"],
        layer=0,
    )
    add(
        "LINEAR",
        ["layer.0.mlp_norm"],
        ["layer.0.up"],
        tensors=["model.layers.0.mlp.up_proj.weight"],
        layer=0,
    )
    add(
        "SILU_MUL",
        ["layer.0.gate", "layer.0.up"],
        ["layer.0.gated_mlp"],
        layer=0,
    )
    add(
        "LINEAR",
        ["layer.0.gated_mlp"],
        ["layer.0.mlp_projected"],
        tensors=["model.layers.0.mlp.down_proj.weight"],
        layer=0,
    )
    add(
        "RESIDUAL_ADD",
        ["layer.0.post_attention", "layer.0.mlp_projected"],
        ["hidden.1"],
        layer=0,
    )
    add(
        "RMS_NORM",
        ["hidden.1"],
        ["hidden.final_norm"],
        tensors=["model.norm.weight"],
    )
    add("LAST_TOKEN_SELECT", ["hidden.final_norm"], ["hidden.last_token"])
    add(
        "LINEAR",
        ["hidden.last_token"],
        ["output.logits"],
        tensors=["lm_head.weight"],
    )
    return nodes


def _operators() -> list[dict[str, str]]:
    kinds = (
        "TOKEN_EMBEDDING_LOOKUP",
        "RMS_NORM",
        "LINEAR",
        "ROPE",
        "KV_COMMIT",
        "GQA_CAUSAL_ATTENTION",
        "RESIDUAL_ADD",
        "SILU_MUL",
        "LAST_TOKEN_SELECT",
    )
    return [
        {
            "arithmetic": f"{kind} arithmetic",
            "kind": kind,
            "lowering": f"ROM_{kind}",
            "semantics": f"{kind} source semantics",
            "source_symbol": f"Qwen3.{kind}",
            "state_effect": "mutable_kv" if kind == "KV_COMMIT" else "none",
        }
        for kind in kinds
    ]


def _write_handoff(root: Path) -> tuple[Path, Path, Path, Qwen3ArtifactIdentity]:
    root.mkdir(parents=True, exist_ok=True)
    identity = _identity()
    config = {
        "head_dim": identity.head_dim,
        "hidden_size": identity.hidden_size,
        "intermediate_size": identity.intermediate_size,
        "max_position_embeddings": identity.maximum_position_embeddings,
        "num_attention_heads": identity.attention_heads,
        "num_hidden_layers": identity.layer_count,
        "num_key_value_heads": identity.key_value_heads,
        "tie_word_embeddings": False,
        "torch_dtype": "bfloat16",
        "use_cache": True,
        "vocab_size": identity.vocabulary_size,
    }
    config_path = root / "config.json"
    write_canonical_json(config_path, config)
    config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()

    weights = _weights()
    tensor_records: list[dict[str, object]] = []
    cursor = 0
    for name, shape in sorted(weights.items()):
        size = 2
        for dimension in shape:
            size *= dimension
        digest = hashlib.sha256(name.encode("ascii")).hexdigest()
        tensor_records.append(
            {
                "data_offsets": [cursor, cursor + size],
                "dtype": "BF16",
                "name": name,
                "payload_sha256": digest,
                "shape": list(shape),
                "size_bytes": size,
            }
        )
        cursor += size
    lock: dict[str, object] = {
        "checkpoint": {
            "payload_bytes": cursor,
            "tensor_count": len(tensor_records),
        },
        "files": [],
        "lock_id": "0" * 64,
        "schema": "opentallas.checkpoint_lock.v1",
        "shards": [{"tensors": tensor_records}],
        "source": {
            "repository": identity.repository,
            "revision": identity.revision,
        },
    }
    lock["lock_id"] = hashlib.sha256(
        canonical_json_bytes({key: value for key, value in lock.items() if key != "lock_id"})
    ).hexdigest()
    lock_path = root / "checkpoint.lock.json"
    write_canonical_json(lock_path, lock)

    nodes = _nodes()
    counts = Counter(node["kind"] for node in nodes)
    graph: dict[str, object] = {
        "coverage": {
            "all_checkpoint_tensors_consumed_once": True,
            "all_layers_have_kv_commit": True,
            "layer_count": identity.layer_count,
            "node_count": len(nodes),
            "operator_kind_count": len(counts),
            "tensor_count": len(tensor_records),
        },
        "execution_contract": {
            "batch_size": 1,
            "maximum_total_context_tokens": identity.target_context_tokens,
            "sliding_window": False,
        },
        "graph_id": "0" * 64,
        "model": {
            "config_sha256": config_sha256,
            "id": identity.model_id,
            "repository": identity.repository,
            "revision": identity.revision,
        },
        "nodes": nodes,
        "numeric_contract": {},
        "operators": _operators(),
        "schema": "opentallas.qwen3.semantic_graph.v1",
        "source_lock": {
            "configuration_qwen3_sha256": "1" * 64,
            "modeling_qwen3_sha256": HASH,
            "modular_qwen3_sha256": "2" * 64,
            "transformers_version": "fixture",
        },
    }
    graph["graph_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in graph.items() if key != "graph_id"}
        )
    ).hexdigest()
    graph_path = root / "graph.json"
    write_canonical_json(graph_path, graph)
    return graph_path, lock_path, config_path, identity


def _export(root: Path):
    graph, lock, config, identity = _write_handoff(root)
    return export_qwen3_production_graph(
        graph,
        lock,
        config,
        identity=identity,
    )


def test_qwen_adapter_exports_complete_backend_neutral_transactional_graph(
    tmp_path: Path,
) -> None:
    graph = _export(tmp_path)
    assert len(graph.state_resources) == 1
    assert len(graph.tensors) == 38
    assert len(graph.operations) == 22
    assert sum(tensor.role == "weight" for tensor in graph.tensors) == 14
    assert graph.operations[-1].operation_id == "state.commit"
    assert graph.operations[-1].effects[0].action == "commit"
    prepare = next(operation for operation in graph.operations if operation.kind == "KV_PREPARE")
    attention = next(operation for operation in graph.operations if operation.kind == "ATTENTION")
    assert [effect.action for effect in prepare.effects] == [
        "read_committed",
        "prepare",
    ]
    assert [effect.action for effect in attention.effects] == ["read_prepared"]
    assert graph.entrypoints[1].predicate["terms"][-1] == {
        "kind": "compare",
        "operator": "eq",
        "symbol": "span_tokens",
        "value": 1,
    }
    encoded = canonical_json_bytes(graph.to_dict())
    for forbidden in (b"ROM_", b"HBM_", b"SRAM_", b"physical_map", b"microcode"):
        assert forbidden not in encoded


def test_qwen_adapter_is_deterministic_and_binds_every_checkpoint_payload(
    tmp_path: Path,
) -> None:
    first = _export(tmp_path / "first")
    second = _export(tmp_path / "second")
    assert first == second
    assert first.graph_id == second.graph_id
    lock_ids = {
        tensor.binding.checkpoint_lock_id
        for tensor in first.tensors
        if tensor.binding is not None
    }
    assert len(lock_ids) == 1
    assert all(
        tensor.binding.sources[0].payload_sha256 == tensor.binding.payload_sha256
        for tensor in first.tensors
        if tensor.binding is not None
    )


def test_qwen_adapter_rejects_graph_tamper_unknown_kind_and_payload_extent(
    tmp_path: Path,
) -> None:
    graph_path, lock_path, config_path, identity = _write_handoff(tmp_path)
    graph = load_strict_json(graph_path)
    graph["nodes"][0]["kind"] = "UNKNOWN"
    write_canonical_json(graph_path, graph)
    with pytest.raises(Qwen3ProductionAdapterError, match="graph_id differs"):
        export_qwen3_production_graph(
            graph_path, lock_path, config_path, identity=identity
        )

    graph["graph_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in graph.items() if key != "graph_id"}
        )
    ).hexdigest()
    write_canonical_json(graph_path, graph)
    with pytest.raises(Qwen3ProductionAdapterError, match="unknown kind"):
        export_qwen3_production_graph(
            graph_path, lock_path, config_path, identity=identity
        )

    graph_path, lock_path, config_path, identity = _write_handoff(tmp_path / "extent")
    lock = load_strict_json(lock_path)
    lock["shards"][0]["tensors"][0]["size_bytes"] += 2
    lock["lock_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in lock.items() if key != "lock_id"}
        )
    ).hexdigest()
    write_canonical_json(lock_path, lock)
    with pytest.raises(Qwen3ProductionAdapterError, match="byte extent differs"):
        export_qwen3_production_graph(
            graph_path, lock_path, config_path, identity=identity
        )


def test_qwen_adapter_rejects_config_and_weight_coverage_drift(tmp_path: Path) -> None:
    graph_path, lock_path, config_path, identity = _write_handoff(tmp_path)
    config = load_strict_json(config_path)
    config["hidden_size"] = 8
    write_canonical_json(config_path, config)
    graph = load_strict_json(graph_path)
    graph["model"]["config_sha256"] = hashlib.sha256(config_path.read_bytes()).hexdigest()
    graph["graph_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in graph.items() if key != "graph_id"}
        )
    ).hexdigest()
    write_canonical_json(graph_path, graph)
    with pytest.raises(Qwen3ProductionAdapterError, match="hidden_size"):
        export_qwen3_production_graph(
            graph_path, lock_path, config_path, identity=identity
        )

    graph_path, lock_path, config_path, identity = _write_handoff(tmp_path / "weights")
    graph = load_strict_json(graph_path)
    graph["nodes"][-1]["tensors"] = ["model.norm.weight"]
    graph["graph_id"] = hashlib.sha256(
        canonical_json_bytes(
            {key: value for key, value in graph.items() if key != "graph_id"}
        )
    ).hexdigest()
    write_canonical_json(graph_path, graph)
    with pytest.raises(Qwen3ProductionAdapterError, match="exactly once"):
        export_qwen3_production_graph(
            graph_path, lock_path, config_path, identity=identity
        )


def test_qwen_adapter_publication_is_canonical_atomic_and_nonoverwriting(
    tmp_path: Path,
) -> None:
    graph_path, lock_path, config_path, identity = _write_handoff(tmp_path / "source")
    output = tmp_path / "published/model_graph.v2.json"
    graph = publish_qwen3_production_graph(
        graph_path,
        lock_path,
        config_path,
        output,
        identity=identity,
    )
    assert output.read_bytes() == canonical_json_bytes(graph.to_dict())
    before = output.read_bytes()
    with pytest.raises(Qwen3ProductionAdapterError, match="will not be overwritten"):
        publish_qwen3_production_graph(
            graph_path,
            lock_path,
            config_path,
            output,
            identity=identity,
        )
    assert output.read_bytes() == before
    assert not list(output.parent.glob(".*.tmp"))
