from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator
import pytest

from compiler.frontend.deepseek_v4_graph import (
    CONVERT_SOURCE_SHA256,
    ENCODING_SOURCE_SHA256,
    GENERATE_SOURCE_SHA256,
    INFERENCE_CONFIG_SHA256,
    KERNEL_SOURCE_SHA256,
    MODEL_SOURCE_SHA256,
    MODEL_CARD_SHA256,
    TOKENIZER_SHA256,
    DeepSeekV4GraphError,
    _GraphBuilder,
    build_official_graph_contract,
    load_official_inference_config,
)


ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "compiler/models/deepseek-v4-flash-0731"


@pytest.fixture(scope="module")
def graph_contract() -> dict:
    return build_official_graph_contract()


def test_official_inference_config_and_sources_are_content_pinned() -> None:
    inference = load_official_inference_config()
    source = json.loads((TARGET / "checkpoint_source.json").read_text())
    expected = {record["path"]: record["sha256"] for record in source["expected_files"]}

    assert inference["n_layers"] == 43
    assert inference["n_mtp_layers"] == 3
    assert inference["compress_ratios"][-3:] == [0, 0, 0]
    assert expected["inference/config.json"] == INFERENCE_CONFIG_SHA256
    assert expected["inference/model.py"] == MODEL_SOURCE_SHA256
    assert expected["inference/kernel.py"] == KERNEL_SOURCE_SHA256
    assert expected["inference/convert.py"] == CONVERT_SOURCE_SHA256
    assert expected["inference/generate.py"] == GENERATE_SOURCE_SHA256
    assert expected["README.md"] == MODEL_CARD_SHA256
    assert expected["encoding/encoding_dsv4.py"] == ENCODING_SOURCE_SHA256
    assert expected["tokenizer.json"] == TOKENIZER_SHA256


def test_graph_is_deterministic_complete_but_explicitly_not_executable(
    graph_contract: dict,
) -> None:
    second = build_official_graph_contract()
    assert second == graph_contract
    assert graph_contract["graph_contract_id"] == (
        "8357b3d82b443750c7849047997048438325a078cb9a8284408eb6ea2c05f27a"
    )
    assert graph_contract["coverage"] == {
        "catalog_kind_count": 46,
        "consumed_tensor_role_count": 63,
        "execution_status": "blocked_pending_reference_and_service_engine",
        "missing_cost_class_count": 0,
        "missing_lowering_count": 0,
        "missing_reference_owner_count": 0,
        "node_count": 2136,
        "pending_reference_kind_count": 14,
        "pending_rtl_kind_count": 46,
        "pending_service_engine_kind_count": 46,
        "unknown_kind_count": 0,
        "unmapped_tensor_role_count": 0,
    }
    assert graph_contract["tensor_assignment"] == {
        "assigned_tensor_count": 72_317,
        "assignment_sha256": (
            "23d29fcdaee370b461756c02978bdc2a528218f36fe9a5d9c06cde03ed13d46a"
        ),
        "maximum_consumers_per_tensor": 3,
        "multi_consumer_tensor_count": 11,
        "unassigned_tensor_count": 0,
    }


def test_graph_is_topological_and_phase_safe(graph_contract: dict) -> None:
    values = {
        "request.input_ids": {"prefill", "decode"},
        "request.session_ids": {"prefill", "decode"},
        "request.start_pos": {"prefill", "decode"},
    }
    value_guards: dict[str, str | None] = {value: None for value in values}
    predicate_values: set[str] = set()
    assert graph_contract["graph_inputs"] == sorted(values)
    node_ids: set[str] = set()
    for node in graph_contract["nodes"]:
        assert node["id"] not in node_ids
        node_ids.add(node["id"])
        phases = set(node["phases"])
        assert phases
        assert phases <= {"prefill", "decode"}
        assert all(value in values for value in node["inputs"])
        assert all(phases <= values[value] for value in node["inputs"])
        guard = node["guard"]
        if guard is not None:
            assert guard in values
            assert guard in predicate_values
            assert value_guards[guard] is None
            assert phases <= values[guard]
        optional_inputs = node["optional_inputs"]
        assert len(optional_inputs) == len(set(optional_inputs))
        assert set(optional_inputs) <= set(node["inputs"])
        for value in node["inputs"]:
            value_guard = value_guards[value]
            if value_guard is not None and guard != value_guard:
                assert value in optional_inputs
                assert value_guard in node["inputs"]

        output_guards = node["optional_output_guards"]
        assert set(output_guards) <= set(node["outputs"])
        assert not (guard is not None and output_guards)
        predicate_outputs = node["predicate_outputs"]
        assert len(predicate_outputs) == len(set(predicate_outputs))
        assert set(predicate_outputs) <= set(node["outputs"])
        assert not (guard is not None and predicate_outputs)
        assert not (set(predicate_outputs) & set(output_guards))
        for output_guard in output_guards.values():
            assert output_guard in predicate_values or output_guard in predicate_outputs
        for output in node["outputs"]:
            assert output not in values
            values[output] = phases
        for output in node["outputs"]:
            output_guard = guard or output_guards.get(output)
            if output_guard is not None:
                assert output_guard in values
            value_guards[output] = output_guard
        predicate_values.update(predicate_outputs)
    assert all(output in values for output in graph_contract["graph_outputs"])


def _predicate_builder() -> tuple[_GraphBuilder, str]:
    builder = _GraphBuilder()
    (predicate,) = builder.add(
        "predicate",
        "COMPRESS_STATE_UPDATE",
        ("request.start_pos",),
        ("ready",),
        predicate_outputs=("ready",),
    )
    return builder, predicate


def test_graph_builder_rejects_nonpredicate_and_nested_node_guards() -> None:
    builder = _GraphBuilder()
    with pytest.raises(DeepSeekV4GraphError, match="not a declared predicate"):
        builder.add(
            "nonpredicate_guard",
            "RMS_NORM",
            ("request.input_ids",),
            guard="request.input_ids",
        )

    builder, predicate = _predicate_builder()
    (guarded_value,) = builder.add(
        "guarded",
        "RMS_NORM",
        ("request.input_ids",),
        guard=predicate,
    )
    builder.predicate_values.add(guarded_value)
    with pytest.raises(DeepSeekV4GraphError, match="itself guarded"):
        builder.add(
            "nested_guard",
            "RMS_NORM",
            ("request.input_ids",),
            guard=guarded_value,
        )


def test_graph_builder_rejects_invalid_predicate_declarations() -> None:
    builder = _GraphBuilder()
    with pytest.raises(DeepSeekV4GraphError, match="invalid or duplicate output names"):
        builder.add(
            "duplicate_outputs",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("ready", "ready"),
        )
    with pytest.raises(DeepSeekV4GraphError, match="invalid predicate outputs"):
        builder.add(
            "unknown_predicate",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("payload",),
            predicate_outputs=("ready",),
        )
    with pytest.raises(DeepSeekV4GraphError, match="invalid optional-output guards"):
        builder.add(
            "invalid_output_guard_mapping",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("payload",),
            optional_output_guards={"payload": 1},  # type: ignore[dict-item]
        )

    builder, predicate = _predicate_builder()
    with pytest.raises(DeepSeekV4GraphError, match="produce predicates under a guard"):
        builder.add(
            "guarded_predicate",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("ready",),
            guard=predicate,
            predicate_outputs=("ready",),
        )


def test_graph_builder_rejects_self_circular_and_nonpredicate_output_guards() -> None:
    builder = _GraphBuilder()
    with pytest.raises(DeepSeekV4GraphError, match="cannot guard itself"):
        builder.add(
            "self_guard",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("ready",),
            optional_output_guards={"ready": "ready"},
            predicate_outputs=("ready",),
        )
    with pytest.raises(DeepSeekV4GraphError, match="circularly guarded"):
        builder.add(
            "circular_guards",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("left", "right"),
            optional_output_guards={"left": "right", "right": "left"},
            predicate_outputs=("left", "right"),
        )
    with pytest.raises(DeepSeekV4GraphError, match="is itself guarded"):
        builder.add(
            "nested_output_guards",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("payload", "inner", "root"),
            optional_output_guards={"payload": "inner", "inner": "root"},
            predicate_outputs=("inner", "root"),
        )
    with pytest.raises(DeepSeekV4GraphError, match="not a declared predicate"):
        builder.add(
            "nonpredicate_output_guard",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("payload", "ordinary"),
            optional_output_guards={"payload": "ordinary"},
        )


def test_graph_builder_accepts_only_phase_available_unguarded_predicates() -> None:
    builder, predicate = _predicate_builder()
    (payload,) = builder.add(
        "externally_guarded_output",
        "COMPRESS_STATE_UPDATE",
        ("request.start_pos",),
        ("payload",),
        optional_output_guards={"payload": predicate},
    )
    assert builder.value_guards[payload] == predicate

    prefill_builder = _GraphBuilder()
    (prefill_predicate,) = prefill_builder.add(
        "prefill_predicate",
        "COMPRESS_STATE_UPDATE",
        ("request.start_pos",),
        ("ready",),
        phases=("prefill",),
        predicate_outputs=("ready",),
    )
    with pytest.raises(DeepSeekV4GraphError, match="phase-unavailable output guard"):
        prefill_builder.add(
            "decode_output",
            "COMPRESS_STATE_UPDATE",
            ("request.start_pos",),
            ("payload",),
            phases=("decode",),
            optional_output_guards={"payload": prefill_predicate},
        )


def test_operator_ledger_has_no_implicit_or_zero_cost_kind(
    graph_contract: dict,
) -> None:
    catalog = {record["kind"]: record for record in graph_contract["operator_catalog"]}
    counts = {
        record["kind"]: record["node_count"]
        for record in graph_contract["operator_counts"]
    }

    assert set(catalog) == set(counts)
    assert sum(counts.values()) == 2136
    assert counts["HASH_ROUTE"] == 3
    assert counts["BIASED_TOPK_ROUTE"] == 43
    assert counts["FP4_QDQ"] == 42
    assert counts["FP8_QDQ"] == 90
    assert counts["HADAMARD_ROTATE"] == 42
    assert counts["INDEX_SCORE"] == 21
    assert counts["MXFP4_SWIGLU"] == 46
    assert counts["INDEX_TOPK"] == 21
    assert counts["COMPRESSED_DENSE_INDEX"] == 20
    assert counts["COMPRESS_PROJECT"] == 62
    assert counts["COMPRESS_STATE_UPDATE"] == 62
    assert counts["COMPRESS_POOL"] == 62
    assert counts["BINARY32_TO_BF16"] == 62
    assert counts["COMPRESS_KV_WRITE"] == 62
    assert counts["COMPRESSED_KV_VALID_VIEW"] == 62
    assert counts["ATTENTION_KV_VIEW"] == 46
    assert counts["DSPARK_PREFILL_KV"] == 3
    assert counts["MARKOV_AUTOREGRESSIVE_LOOP"] == 1
    qualified_references = {
        "BIASED_TOPK_ROUTE": ("runtime.reference.selection.biased_topk_route_indices"),
        "BF16_LINEAR": "runtime.reference.matrix.bf16_linear_bf16",
        "BINARY32_TO_BF16": (
            "runtime.reference.conversion.binary32_tensor_to_bf16_rne"
        ),
        "CONFIDENCE_SCORE": "runtime.reference.confidence.confidence_score_bf16",
        "COMPRESS_KV_WRITE": (
            "runtime.reference.compressed_kv.compressed_kv_write_bf16"
        ),
        "COMPRESSED_KV_VALID_VIEW": (
            "runtime.reference.compressed_kv.compressed_kv_valid_view_bf16"
        ),
        "COMPRESS_POOL": "runtime.reference.compression_pool.compress_pool_f32",
        "COMPRESS_PROJECT": "runtime.reference.compression.compress_project_bf16",
        "COMPRESS_STATE_UPDATE": (
            "runtime.reference.compression_state.compress_state_update_f32"
        ),
        "COMPRESSED_DENSE_INDEX": (
            "runtime.reference.indexing.compressed_dense_indices"
        ),
        "DSPARK_NOISE_EMBED": ("runtime.reference.structural.dspark_noise_embed_bf16"),
        "DSPARK_WINDOW_INDEX": "runtime.reference.indexing.dspark_window_indices",
        "EXPERT_DISPATCH": ("runtime.reference.dispatch.dispatch_routed_experts_bf16"),
        "EXPERT_REDUCE": ("runtime.reference.dispatch.reduce_expert_outputs_bf16"),
        "FP4_QDQ": "runtime.reference.quantization.fp4_qdq_bf16",
        "FP8_QDQ": "runtime.reference.quantization.fp8_qdq_bf16",
        "FP8_LINEAR": "runtime.reference.matrix.dense_fp8_linear_bf16",
        "HADAMARD_ROTATE": ("runtime.reference.hadamard.hadamard_rotate_128_bf16"),
        "HASH_ROUTE": "runtime.reference.lookup.hash_route_indices",
        "HC_EXPAND": "runtime.reference.structural.hc_expand_bf16",
        "HC_POST": "runtime.reference.vector.hc_post_bf16",
        "HEAD_RMS_NORM": "runtime.reference.normalization.head_rms_norm_bf16",
        "INDEX_SCORE": "runtime.reference.index_score.index_score_bf16",
        "INDEX_TOPK": "runtime.reference.selection.index_topk_indices",
        "RMS_NORM": "runtime.reference.normalization.rms_norm_bf16",
        "ROUTER_SCORE": "runtime.reference.routing.router_score_bf16",
        "ROUTER_WEIGHT_NORMALIZE": (
            "runtime.reference.routing.normalize_routed_weight_codes"
        ),
        "SAMPLE": "runtime.reference.sampling.deepseek_v4_sample_binary32",
        "SPARSE_ATTENTION": (
            "runtime.reference.sparse_attention.sparse_attention_bf16"
        ),
        "TARGET_HIDDEN_CAPTURE": (
            "runtime.reference.vector.target_hidden_capture_bf16"
        ),
        "TOKEN_EMBED": "runtime.reference.lookup.bf16_token_embedding",
        "WINDOW_INDEX": "runtime.reference.indexing.window_indices",
    }
    for kind, requirement in catalog.items():
        assert requirement["cost_class"]
        assert not requirement["cost_class"].startswith("zero")
        assert requirement["lowering_class"]
        if kind in qualified_references:
            assert requirement["reference_owner"] == qualified_references[kind]
            assert requirement["reference_status"] == "implemented_unit_qualified"
        else:
            assert requirement["reference_owner"].startswith(
                "compiler.reference.deepseek_v4."
            )
            assert requirement["reference_status"] == "pending_implementation"
        assert requirement["service_engine_status"] == "pending_implementation"
        assert requirement["rtl_status"] == "pending_implementation"


def test_sampling_contract_exposes_exact_and_blocked_numeric_boundaries(
    graph_contract: dict,
) -> None:
    (node,) = [node for node in graph_contract["nodes"] if node["kind"] == "SAMPLE"]
    assert node["id"] == "main.sample"
    assert node["attributes"] == {
        "greedy_policy": "finite_binary32_first_index_argmax_exact",
        "official_stochastic_replay": (
            "blocked_unpinned_torch_cuda_rng_exponential_softmax_backend"
        ),
        "policy": "runtime_temperature_gumbel_or_argmax",
        "target_stochastic_adaptation": (
            "explicit_positive_binary32_exponential_draws_cr32_exp_balanced_softmax"
        ),
    }
    assert node["inputs"] == ["main.lm_head.output"]
    assert node["state_reads"] == node["state_writes"] == []


def test_weighted_rms_norm_profile_and_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [node for node in graph_contract["nodes"] if node["kind"] == "RMS_NORM"]
    assert len(nodes) == 251
    assert Counter(node["attributes"]["width"] for node in nodes) == {
        128: 21,
        512: 90,
        1024: 46,
        4096: 94,
    }
    for node in nodes:
        width = node["attributes"]["width"]
        assert node["attributes"] == {
            "checkpoint_weight_dtype": "bf16",
            "epsilon": 1e-6,
            "epsilon_binary32": "0x358637bd",
            "input_dtype": "bf16",
            "intermediate_overflow": "poison",
            "operation_rounding": "binary32_rne_each_operation",
            "output_dtype": "bf16",
            "output_zero": "canonical_positive",
            "reduction_tree": "num_6_1_balanced_binary32_rne",
            "rsqrt_rounding": "correct_binary32_rne",
            "subnormal_policy": "preserve",
            "weight_compute_dtype": "binary32_exact_bf16_widen",
            "width": width,
        }


def test_head_rms_norm_profile_and_bf16_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "HEAD_RMS_NORM"
    ]
    assert len(nodes) == 46
    for node in nodes:
        assert node["attributes"] == {
            "epsilon": 1e-6,
            "epsilon_add_rounding": "bf16_rne",
            "epsilon_bf16": "0x3586",
            "head_dim": 512,
            "input_dtype": "bf16",
            "intermediate_overflow": "poison",
            "mean_conversion": "binary32_rne_divide_then_bf16_rne",
            "output_dtype": "bf16",
            "output_zero": "canonical_positive",
            "pointwise_multiply_rounding": "bf16_rne",
            "reduction_tree": "num_6_1_balanced_binary32_rne",
            "rsqrt_rounding": "correct_bf16_rne",
            "square_rounding": "bf16_rne",
            "subnormal_policy": "preserve",
        }


def test_index_head_bf16_linear_profile_and_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [node for node in graph_contract["nodes"] if node["kind"] == "BF16_LINEAR"]
    assert len(nodes) == 21
    for node in nodes:
        assert node["attributes"] == {
            "accumulation_order": "increasing_reduction_index",
            "accumulation_rounding": "binary32_rne_each_fused_product_add",
            "accumulator_dtype": "binary32",
            "bias": "none",
            "checkpoint_weight_dtype": "bf16",
            "in_features": 4096,
            "input_dtype": "bf16",
            "intermediate_overflow": "poison",
            "out_features": 64,
            "output_dtype": "bf16",
            "output_rounding": "bf16_rne_once",
            "output_zero": "canonical_positive",
            "product": "exact_bf16_product",
            "subnormal_policy": "preserve",
        }


def test_router_score_profile_and_binary32_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [node for node in graph_contract["nodes"] if node["kind"] == "ROUTER_SCORE"]
    assert len(nodes) == 46
    for node in nodes:
        assert node["attributes"] == {
            "accumulation_order": "increasing_reduction_index",
            "accumulation_rounding": "binary32_rne_each_fused_product_add",
            "accumulator_dtype": "binary32",
            "bias": "none",
            "checkpoint_weight_dtype": "bf16",
            "experts": 256,
            "in_features": 4096,
            "input_compute_dtype": "binary32_exact_bf16_widen",
            "input_dtype": "bf16",
            "intermediate_overflow": "poison",
            "output_dtype": "binary32",
            "product": "exact_bf16_product",
            "subnormal_policy": "preserve",
            "weight_compute_dtype": "binary32_exact_bf16_widen",
        }


def test_expert_reduce_profile_and_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "EXPERT_REDUCE"
    ]
    assert len(nodes) == 46
    for node in nodes:
        prefix = node["id"].removesuffix(".expert_reduce")
        assert node["inputs"] == [
            f"{prefix}.expert_dispatch.output",
            f"{prefix}.routed_experts.output",
            f"{prefix}.shared_expert.output",
        ]
        assert node["attributes"] == {
            "distinct_expert_order": "ascending_logical_expert_id",
            "duplicate_slot_order": "ascending_selected_slot",
            "duplicate_slot_policy": "preserve_all",
            "intermediate_overflow": "poison",
            "output_dtype": "bf16",
            "output_rounding": "bf16_rne_once",
            "output_saturation": "sticky_count",
            "output_zero": "canonical_positive",
            "reduction_tree": "num_6_1_balanced_binary32_rne",
            "routed_alignment": "expert_dispatch_groups_one_to_one",
            "routed_input_dtype": "bf16",
            "shared_add_order": "after_routed_reduction",
            "shared_add_rounding": "binary32_rne_once",
            "shared_input_dtype": "bf16",
            "subnormal_policy": "preserve",
        }


def test_dspark_confidence_profile_and_binary32_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "CONFIDENCE_SCORE"
    ]
    assert len(nodes) == 1
    node = nodes[0]
    assert node["id"] == "dspark.confidence"
    assert node["phases"] == ["decode"]
    assert node["tensor_roles"] == ["dspark.confidence_head.weight"]
    assert node["attributes"] == {
        "accumulation_order": "increasing_reduction_index",
        "accumulation_rounding": "binary32_rne_each_fused_product_add",
        "accumulator_dtype": "binary32",
        "bias": "none",
        "block_size": 5,
        "checkpoint_weight_dtype": "bf16",
        "concatenation_order": "hidden_then_markov",
        "hidden_input_dtype": "bf16",
        "hidden_width": 4096,
        "input_compute_dtype": "binary32_exact_bf16_widen",
        "input_width": 4352,
        "intermediate_overflow": "poison",
        "markov_input_dtype": "bf16",
        "markov_width": 256,
        "output_count": 1,
        "output_dtype": "binary32",
        "output_zero": "canonical_positive",
        "product": "exact_bf16_product",
        "subnormal_policy": "preserve",
        "weight_compute_dtype": "binary32_exact_bf16_widen",
    }


def test_compressor_projection_profiles_and_binary32_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "COMPRESS_PROJECT"
    ]
    assert len(nodes) == 62
    assert Counter(
        (
            node["attributes"]["projection_scope"],
            node["attributes"]["ratio"],
            node["attributes"]["output_features"],
        )
        for node in nodes
    ) == {
        ("indexer", 4, 256): 21,
        ("main", 4, 1024): 21,
        ("main", 128, 512): 20,
    }
    for node in nodes:
        attributes = node["attributes"]
        assert attributes == {
            "accumulation_order": "increasing_reduction_index",
            "accumulation_rounding": "binary32_rne_each_fused_product_add",
            "accumulator_dtype": "binary32",
            "activation_quantization": "none",
            "bias": "none",
            "checkpoint_weight_dtype": "bf16",
            "in_features": 4096,
            "input_compute_dtype": "binary32_exact_bf16_widen",
            "input_dtype": "bf16",
            "intermediate_overflow": "poison",
            "output_conversion": "none",
            "output_dtypes": {"kv": "binary32", "scores": "binary32"},
            "output_features": attributes["output_features"],
            "output_zero": "canonical_positive",
            "overlap": attributes["ratio"] == 4,
            "product": "exact_bf16_product",
            "projection_arithmetic": "independent",
            "projection_order": "kv_then_gate",
            "projection_scope": attributes["projection_scope"],
            "ratio": attributes["ratio"],
            "subnormal_policy": "preserve",
            "weight_compute_dtype": "binary32_exact_bf16_widen",
            "weight_layout": "output_by_input",
        }
        assert node["tensor_roles"] in (
            [
                "attention.compressor.wkv.weight",
                "attention.compressor.wgate.weight",
            ],
            [
                "attention.indexer.compressor.wkv.weight",
                "attention.indexer.compressor.wgate.weight",
            ],
        )


def test_compressor_state_pool_conversion_and_commit_are_explicit(
    graph_contract: dict,
) -> None:
    state_nodes = [
        node
        for node in graph_contract["nodes"]
        if node["kind"] == "COMPRESS_STATE_UPDATE"
    ]
    pool_nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "COMPRESS_POOL"
    ]
    conversion_nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "BINARY32_TO_BF16"
    ]
    write_nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "COMPRESS_KV_WRITE"
    ]
    view_nodes = [
        node
        for node in graph_contract["nodes"]
        if node["kind"] == "COMPRESSED_KV_VALID_VIEW"
    ]
    assert len(state_nodes) == len(pool_nodes) == len(conversion_nodes) == 62
    assert len(write_nodes) == len(view_nodes) == 62
    profile_counts = {
        ("indexer", 4, 128): 21,
        ("main", 4, 512): 21,
        ("main", 128, 512): 20,
    }
    assert (
        Counter(
            (
                node["attributes"]["projection_scope"],
                node["attributes"]["ratio"],
                node["attributes"]["head_dim"],
            )
            for node in state_nodes
        )
        == profile_counts
    )
    assert (
        Counter(
            (
                node["attributes"]["projection_scope"],
                node["attributes"]["ratio"],
                node["attributes"]["head_dim"],
            )
            for node in write_nodes
        )
        == profile_counts
    )

    for node in state_nodes:
        attributes = node["attributes"]
        ratio = attributes["ratio"]
        width = attributes["head_dim"]
        overlap = ratio == 4
        assert attributes == {
            "ape_checkpoint_dtype": "binary32",
            "ape_shape": [ratio, (2 if overlap else 1) * width],
            "candidate_input_dtype": "binary32",
            "counter_scope": "logical_raw_state_reads_and_writes",
            "decode_sequence_length": 1,
            "head_dim": width,
            "intermediate_overflow": "poison",
            "new_session_prefill": "reset_all_active_raw_slots_then_apply",
            "output": "optional_pool_kv_pool_scores_and_should_compress_predicate",
            "overlap": overlap,
            "positional_score_add_rounding": "binary32_rne",
            "projection_scope": attributes["projection_scope"],
            "ratio": ratio,
            "session_identity": "per_active_batch_lowercase_sha256",
            "session_prefill_transition": "fresh_identity_reset_then_apply",
            "state_dtype": "binary32",
            "state_metadata": "session_id_next_position_monotonic_version",
            "state_slots": (2 if overlap else 1) * ratio,
            "state_transaction": (
                "causal_validate_prepare_immutable_commit_target_adaptation"
            ),
        }
        assert node["inputs"][-2:] == [
            "request.start_pos",
            "request.session_ids",
        ]
        assert node["outputs"][-1].endswith(".should_compress")
        assert node["optional_output_guards"] == {
            node["outputs"][0]: node["outputs"][2],
            node["outputs"][1]: node["outputs"][2],
        }
        assert node["state_reads"] == node["state_writes"]
        assert len(node["state_reads"]) == 1
        if attributes["projection_scope"] == "indexer":
            assert node["state_reads"][0].endswith(".index_compressor")
            assert node["tensor_roles"] == [
                "attention.indexer.compressor.position_weight"
            ]
        else:
            assert node["state_reads"][0].endswith(".compressor")
            assert node["tensor_roles"] == ["attention.compressor.position_weight"]

    assert Counter(
        (
            node["attributes"]["ratio"],
            node["attributes"]["head_dim"],
        )
        for node in pool_nodes
    ) == {(4, 128): 21, (4, 512): 21, (128, 512): 20}
    for node in pool_nodes:
        attributes = node["attributes"]
        ratio = attributes["ratio"]
        width = attributes["head_dim"]
        overlap = ratio == 4
        assert attributes == {
            "candidate_count": 2 * ratio if overlap else ratio,
            "candidate_input_dtype": "binary32",
            "first_overlap_padding": (
                "positive_zero_kv_and_negative_infinity_score"
                if overlap
                else "not_applicable"
            ),
            "head_dim": width,
            "intermediate_overflow": "poison",
            "maximum": "per_dimension_finite_binary32_numeric_value",
            "output_dtype": "binary32",
            "output_zero": "canonical_positive",
            "overlap": overlap,
            "probability_division_rounding": "binary32_rne",
            "predicate": "execute_only_when_compress_state_should_compress",
            "ratio": ratio,
            "reduction_tree": "num_6_1_balanced_binary32_rne",
            "score_exponential": "correctly_rounded_binary32",
            "score_subtraction_rounding": "binary32_rne",
            "subnormal_policy": "preserve",
            "weighted_value_multiply_rounding": "binary32_rne",
        }
        assert node["inputs"][0].endswith(".pool_kv")
        assert node["inputs"][1].endswith(".pool_scores")
        assert node["inputs"][2].endswith(".should_compress")
        assert node["guard"] == node["inputs"][2]
        assert node["tensor_roles"] == []

    assert Counter(node["attributes"]["width"] for node in conversion_nodes) == {
        128: 21,
        512: 41,
    }
    for node in conversion_nodes:
        width = node["attributes"]["width"]
        assert node["attributes"] == {
            "counter_scope": "logical_binary32_reads_and_bf16_writes",
            "finite_input_required": True,
            "finite_saturation": "sticky_count",
            "input_dtype": "binary32",
            "input_rank": 3,
            "intermediate_overflow": "poison",
            "output_dtype": "bf16",
            "output_zero": "canonical_positive",
            "predicate": "execute_only_when_compress_state_should_compress",
            "rounding": "round_to_nearest_ties_to_even_once",
            "subnormal_policy": "preserve_gradual_underflow",
            "transaction": "validate_prepare_atomic_immutable_commit",
            "width": width,
        }
        assert node["inputs"][0].endswith("compress_pool.output")
        assert node["inputs"][1].endswith(".should_compress")
        assert node["guard"] == node["inputs"][1]

    for node in write_nodes:
        attributes = node["attributes"]
        assert attributes == {
            "cache_slot": "completed_absolute_position_floor_div_ratio",
            "committed_input_dtype": (
                "bf16_after_normalize_position_transform_and_qdq"
            ),
            "decode_sequence_length": 1,
            "head_dim": attributes["head_dim"],
            "kv_head_count": 1,
            "layer": attributes["layer"],
            "new_session_prefill": "invalidate_then_commit_complete_prefix",
            "optional_payload": "present_exactly_when_should_compress",
            "projection_scope": attributes["projection_scope"],
            "ratio": attributes["ratio"],
            "retired_lane_identity": (
                "preserved_tombstone_prevents_session_resurrection"
            ),
            "session_identity": "per_active_batch_lowercase_sha256",
            "session_reuse": ("fresh_prefill_identity_not_retained_by_any_lane"),
            "scope": attributes["scope"],
            "state_metadata": (
                "session_id_next_position_valid_prefix_monotonic_version"
            ),
            "state_transaction": (
                "causal_valid_prefix_validate_prepare_immutable_commit_target_adaptation"
            ),
        }
        assert node["inputs"][1].endswith(".should_compress")
        assert node["inputs"][2] == "request.start_pos"
        assert node["inputs"][3] == "request.session_ids"
        assert node["optional_inputs"] == [node["inputs"][0]]
        assert node["outputs"][0].endswith(".committed_state")
        assert node["state_reads"] == node["state_writes"]
        if attributes["projection_scope"] == "indexer":
            assert node["state_reads"][0].endswith(".index_compressed_kv")
        else:
            assert node["state_reads"][0].endswith(".compressed_kv")

    assert (
        Counter(
            (
                node["attributes"]["projection_scope"],
                node["attributes"]["ratio"],
                node["attributes"]["head_dim"],
            )
            for node in view_nodes
        )
        == profile_counts
    )
    for node in view_nodes:
        attributes = node["attributes"]
        assert attributes == {
            "capacity_rows_exposed": False,
            "head_dim": attributes["head_dim"],
            "kv_head_count": 1,
            "output": "active_batch_contiguous_valid_prefix_only",
            "payload_dtype": "bf16",
            "projection_scope": attributes["projection_scope"],
            "ratio": attributes["ratio"],
            "session_identity": "per_active_batch_lowercase_sha256",
            "stale_invalid_payload": "never_exposed",
            "validation": ("session_cursor_prefix_and_payload_before_immutable_view"),
        }
        assert node["inputs"][0].endswith(".committed_state")
        assert node["inputs"][1] == "request.session_ids"
        assert node["state_reads"] == node["state_writes"] == []

    by_id = {node["id"]: node for node in graph_contract["nodes"]}
    assert by_id["main.layer02.compress_bf16"]["inputs"] == [
        "main.layer02.compress_pool.output",
        "main.layer02.compress_state.should_compress",
    ]
    assert by_id["main.layer02.compress_norm"]["inputs"] == [
        "main.layer02.compress_bf16.output"
    ]
    assert by_id["main.layer02.index_score"]["inputs"][1] == (
        "main.layer02.index_compress_kv_valid_view.output"
    )
    assert by_id["main.layer02.attention_kv_view"]["inputs"][2] == (
        "main.layer02.compress_kv_valid_view.output"
    )
    assert by_id["main.layer03.attention_kv_view"]["inputs"][2] == (
        "main.layer03.compress_kv_valid_view.output"
    )
    assert by_id["main.layer02.sparse_attention"]["inputs"][1] == (
        "main.layer02.attention_kv_view.output"
    )


def test_index_score_profile_and_bf16_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [node for node in graph_contract["nodes"] if node["kind"] == "INDEX_SCORE"]
    assert len(nodes) == 21
    for node in nodes:
        assert node["attributes"] == {
            "candidate_axis": "may_be_empty",
            "finite_saturation": "sticky_count_at_each_bf16_boundary",
            "head_dim": 128,
            "head_reduction_order": "ascending_logical_head",
            "head_reduction_tree": "num_6_1_balanced_binary32_rne",
            "head_weight_input_dtype": "bf16",
            "head_weight_scale_binary32": "0x3c3504f3",
            "head_weight_scale_rounding": ("direct_binary32_factor_to_bf16_rne_once"),
            "heads": 64,
            "intermediate_overflow": "poison",
            "kv_input_dtype": "bf16",
            "mask_and_topk": "separate_index_topk_operator",
            "output_dtype": "bf16",
            "output_rounding": "bf16_rne_once",
            "output_zero": "canonical_positive",
            "qk_accumulation_order": "increasing_head_dimension",
            "qk_accumulation_rounding": ("binary32_rne_each_fused_product_add"),
            "qk_accumulator_dtype": "binary32",
            "qk_output_rounding": "bf16_rne_once",
            "query_input_dtype": "bf16",
            "ratio": 4,
            "relu": "bf16_nonpositive_to_positive_zero",
            "score_weight_product_rounding": ("direct_bf16_product_to_bf16_rne_once"),
            "subnormal_policy": "preserve",
            "tensor_parallel_reduction": (
                "contiguous_logical_head_partitions_compose_global_tree"
            ),
        }
        assert node["tensor_roles"] == []


def test_sparse_attention_profile_numeric_and_kv_traffic_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "SPARSE_ATTENTION"
    ]
    assert len(nodes) == 46
    assert {node["attributes"]["ratio"] for node in nodes} == {0, 4, 128}
    for node in nodes:
        ratio = node["attributes"]["ratio"]
        assert node["attributes"] == {
            "attention_sink_dtype": "binary32",
            "av_accumulation_order": "ascending_source_slot_within_each_block",
            "av_accumulation_rounding": ("binary32_rne_each_fused_product_add"),
            "block_order": "ascending_64_slot_source_blocks",
            "block_size": 64,
            "counter_scope": (
                "logical_source_work_separates_valid_kv_reads_from_padding"
            ),
            "duplicate_index_policy": "preserve_every_source_slot",
            "final_division_rounding": "binary32_rne",
            "finite_saturation": "sticky_count_at_final_bf16_boundary",
            "first_block_valid_policy": "at_least_one_valid_index_required",
            "head_dim": 512,
            "heads": 64,
            "index_dtype": "int32",
            "intermediate_overflow": "poison",
            "kv_input_dtype": "bf16",
            "kv_read_bytes_per_valid_slot": 1024,
            "online_denominator_update": ("separate_binary32_multiply_then_add"),
            "online_max": "maximum_by_finite_binary32_numeric_value",
            "online_rescale_exp": "correctly_rounded_binary32",
            "output_dtype": "bf16",
            "output_rounding": "bf16_rne_once",
            "output_zero": "canonical_positive",
            "padding_index": -1,
            "probability_dtype": "bf16",
            "probability_rounding": "binary32_to_bf16_rne_once_before_av",
            "qk_accumulation_order": "increasing_head_dimension",
            "qk_accumulation_rounding": ("binary32_rne_each_fused_product_add"),
            "qk_accumulator_dtype": "binary32",
            "query_input_dtype": "bf16",
            "ratio": ratio,
            "score_reduction_tree": ("num_6_1_balanced_64_lane_binary32_rne"),
            "score_scale_binary32": "0x3d3504f3",
            "score_scale_rounding": "binary32_rne_multiply",
            "sink_denominator_order": "after_all_selected_blocks",
            "sink_exp": "general_cr32_finite_overflow_poison",
            "subnormal_policy": "preserve",
            "tail_padding": "implicit_negative_one_to_64_slot_block",
        }
        assert node["tensor_roles"] == ["attention.sink"]
        assert node["inputs"][1].endswith(".attention_kv_view.output")
        assert node["state_reads"] == []
        assert node["state_writes"] == []


def test_layer_classes_and_mutable_state_sites_are_explicit(
    graph_contract: dict,
) -> None:
    by_id = {node["id"]: node for node in graph_contract["nodes"]}

    assert "main.layer00.compress_pool" not in by_id
    assert by_id["main.layer02.compress_pool"]["attributes"]["overlap"] is True
    assert by_id["main.layer02.compress_pool"]["attributes"]["ratio"] == 4
    assert "main.layer02.index_topk" in by_id
    assert by_id["main.layer03.compress_pool"]["attributes"]["overlap"] is False
    assert by_id["main.layer03.compress_pool"]["attributes"]["ratio"] == 128
    assert "main.layer03.compressed_dense_indices" in by_id
    assert "main.layer03.index_topk" not in by_id
    assert by_id["main.layer00.route_select"]["kind"] == "HASH_ROUTE"
    assert by_id["main.layer03.route_select"]["kind"] == "BIASED_TOPK_ROUTE"
    assert by_id["main.layer40.target_hidden"]["attributes"] == {
        "hc_mult": 4,
        "hc_reduce": "mean",
        "layer": 40,
    }
    assert by_id["main.layer41.target_hidden"]["attributes"]["hc_mult"] == 4
    assert by_id["main.layer42.target_hidden"]["attributes"]["hc_mult"] == 4
    fp4_nodes = [node for node in graph_contract["nodes"] if node["kind"] == "FP4_QDQ"]
    assert len(fp4_nodes) == 42
    assert all(node["attributes"] == {"block_size": 32} for node in fp4_nodes)
    fp8_nodes = [node for node in graph_contract["nodes"] if node["kind"] == "FP8_QDQ"]
    assert len(fp8_nodes) == 90
    assert all(
        node["attributes"]
        == {
            "block_size": 64,
            "dimensions": "non_rope",
            "inplace": True,
            "quantized_width": 448,
            "rope_width": 64,
            "scale_format": "ue8m0",
            "scale_storage": "e8m0",
        }
        for node in fp8_nodes
    )
    hadamard_nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "HADAMARD_ROTATE"
    ]
    assert len(hadamard_nodes) == 42
    assert all(
        node["attributes"]
        == {
            "arithmetic": "binary32_rne",
            "butterfly_order": "ascending_stride_1_to_64",
            "input_dtype": "bf16",
            "normalization_scale_binary32": "0x3db504f3",
            "output_dtype": "bf16",
            "stages": 7,
            "subnormal_policy": "preserve",
            "width": 128,
        }
        for node in hadamard_nodes
    )
    assert by_id["dspark.layer00.prefill_kv"]["phases"] == ["prefill"]
    assert by_id["dspark.layer00.hc_attn_pre"]["phases"] == ["decode"]
    assert by_id["dspark.layer00.window_kv_write"]["inputs"][0] == (
        "dspark.layer00.main_kv_fp8_qdq.output"
    )
    assert by_id["dspark.layer00.sparse_attention"]["inputs"][1] == (
        "dspark.layer00.attention_kv_view.output"
    )
    assert by_id["dspark.layer00.attention_kv_view"]["inputs"] == [
        "dspark.layer00.main_kv_fp8_qdq.output",
        "dspark.layer00.window_kv_write.committed_window",
        "request.start_pos",
        "request.session_ids",
    ]
    mutable_nodes = [
        node
        for node in graph_contract["nodes"]
        if node["state_reads"] or node["state_writes"]
    ]
    assert mutable_nodes
    assert all(node["state_reads"] == node["state_writes"] for node in mutable_nodes)
    assert {node["kind"] for node in mutable_nodes} == {
        "COMPRESS_KV_WRITE",
        "COMPRESS_STATE_UPDATE",
        "DSPARK_PREFILL_KV",
        "KV_WINDOW_WRITE",
    }


def test_system_gaps_include_dspark_acceptance_and_text_frontend(
    graph_contract: dict,
) -> None:
    adaptations = {
        record["decision"]: record for record in graph_contract["adaptations"]
    }
    assert len(adaptations) == 4
    pool_adaptation = adaptations[
        "freeze compressor pooling arithmetic rather than inherit "
        "backend-dependent reduction and exponential behavior"
    ]
    assert "PyTorch softmax" in pool_adaptation["source_behavior"]
    assert "NUM-6.13" in pool_adaptation["target_contract"]
    reset_adaptation = adaptations[
        "make new-session raw compressor-state reset an explicit causal transaction"
    ]
    assert "overwrites only" in reset_adaptation["source_behavior"]
    assert "resets every active raw slot" in reset_adaptation["target_contract"]
    validity_adaptation = adaptations[
        "track a session-bound committed-prefix view for compressed KV"
    ]
    assert "without validity" in validity_adaptation["source_behavior"]
    assert "never exposes stale capacity rows" in validity_adaptation["target_contract"]

    issues = {record["id"]: record for record in graph_contract["open_semantic_issues"]}
    assert set(issues) == {
        "DSV4-SEM-001",
        "DSV4-SEM-003",
        "DSV4-SEM-004",
        "DSV4-SEM-005",
        "DSV4-SEM-006",
        "DSV4-SEM-007",
    }
    assert all(record["severity"] == "blocking" for record in issues.values())
    assert "never invokes forward_spec" in issues["DSV4-SEM-001"]["issue"]
    assert "token IDs" in issues["DSV4-SEM-004"]["issue"]
    assert "exact local tokenizer" in issues["DSV4-SEM-004"]["issue"]
    assert "official 32-value routed" in issues["DSV4-SEM-005"]["issue"]
    assert (
        "thirty-two complete matrix/vector/normalization/structural/index/lookup/selection/routing/attention/conversion/state/control"
        in (issues["DSV4-SEM-005"]["issue"])
    )
    assert "Fourteen" in issues["DSV4-SEM-005"]["issue"]
    assert (
        "immutable causal raw compressor-state updates"
        in issues["DSV4-SEM-006"]["issue"]
    )
    assert "operator-complete executor" in issues["DSV4-SEM-006"]["issue"]
    assert "all 72,317 official tensors" in issues["DSV4-SEM-007"]["issue"]
    assert "atomic hash-locked applicator" in issues["DSV4-SEM-007"]["issue"]
    assert graph_contract["system_scope"]["request_boundary"] == (
        "token_ids_session_ids_and_start_position"
    )
    assert (
        "end-to-end binding of the verified host boundary to checkpoint-derived logits"
    ) in (graph_contract["system_scope"]["unresolved"])
    assert (
        "hash-verified local tokenizer encode and decode behavior"
        in (graph_contract["system_scope"]["covered"])
    )
    assert "atomic hash-locked canonical application" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert (
        "unit-qualified dense FP8 linear, index-head BF16 linear, binary32 router-score, compressor, and DSpark-confidence projections, causal raw compressor-state update, deterministic compressor pool, pooled-binary32 to BF16 conversion, session-bound compressed-KV write and valid-prefix view, learned sparse-index scoring, block-64 sparse attention with learned sink and explicit mutable-KV traffic, weighted RMS normalization, unweighted BF16 head RMS normalization, KV FP8 QDQ, indexer FP4 QDQ"
        in (" ".join(graph_contract["system_scope"]["covered"]))
    )
    assert "block-64 sparse attention" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "indexer Hadamard rotation" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "weighted RMS normalization" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "unweighted BF16 head RMS normalization" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "biased-router top-k" in " ".join(graph_contract["system_scope"]["covered"])
    assert "expert-dispatch" in " ".join(graph_contract["system_scope"]["covered"])
    assert "HC post-mixing" in " ".join(graph_contract["system_scope"]["covered"])
    assert "indexer FP4 QDQ" in " ".join(graph_contract["system_scope"]["covered"])
    assert "DSpark index/noise-embedding" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "routed-weight normalization" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "fail-closed greedy/target-adapted sampling" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert (
        "DSpark target verification and speculative acceptance"
        in (graph_contract["system_scope"]["unresolved"])
    )
    assert (
        "fourteen remaining operator-complete target-precision references"
        in (graph_contract["system_scope"]["unresolved"])
    )


def test_graph_contract_validates_against_strict_schema(graph_contract: dict) -> None:
    schema = json.loads(
        (ROOT / "schemas/compiler/deepseek_v4_graph_contract_v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(graph_contract)


def test_inference_config_drift_fails_closed(tmp_path: Path) -> None:
    config = json.loads((TARGET / "inference_config.json").read_text())
    config["n_mtp_layers"] = 1
    changed = tmp_path / "inference_config.json"
    changed.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(DeepSeekV4GraphError, match="not byte-exact"):
        load_official_inference_config(changed)


def test_graph_cli_emits_open_coverage_ledger(tmp_path: Path) -> None:
    output = tmp_path / "graph-contract.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compiler.cli",
            "describe-deepseek-v4-graph",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    value = json.loads(output.read_text(encoding="ascii"))
    assert value["graph_contract_id"] == (
        "8357b3d82b443750c7849047997048438325a078cb9a8284408eb6ea2c05f27a"
    )
    assert "described 2136 nodes across 46 operator kinds" in result.stdout
    assert "blocked_pending_reference_and_service_engine" in result.stdout
