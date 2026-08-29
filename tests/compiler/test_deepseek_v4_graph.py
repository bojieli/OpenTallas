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
        "df2bf6671cafbfbcbb9f135a70d5c9231b1ec1e3204e963f2cdf629178cd8e7e"
    )
    assert graph_contract["coverage"] == {
        "catalog_kind_count": 43,
        "consumed_tensor_role_count": 63,
        "execution_status": "blocked_pending_reference_and_service_engine",
        "missing_cost_class_count": 0,
        "missing_lowering_count": 0,
        "missing_reference_owner_count": 0,
        "node_count": 1924,
        "pending_reference_kind_count": 19,
        "pending_rtl_kind_count": 43,
        "pending_service_engine_kind_count": 43,
        "unknown_kind_count": 0,
        "unmapped_tensor_role_count": 0,
    }
    assert graph_contract["tensor_assignment"] == {
        "assigned_tensor_count": 72_317,
        "assignment_sha256": (
            "3ec76a4a9beb92f0a89f83552557a83cda47e4278890c3c0cf85ec421da0fc17"
        ),
        "maximum_consumers_per_tensor": 3,
        "multi_consumer_tensor_count": 11,
        "unassigned_tensor_count": 0,
    }


def test_graph_is_topological_and_phase_safe(graph_contract: dict) -> None:
    values = {
        "request.input_ids": {"prefill", "decode"},
        "request.start_pos": {"prefill", "decode"},
    }
    node_ids: set[str] = set()
    for node in graph_contract["nodes"]:
        assert node["id"] not in node_ids
        node_ids.add(node["id"])
        phases = set(node["phases"])
        assert phases
        assert phases <= {"prefill", "decode"}
        assert all(value in values for value in node["inputs"])
        assert all(phases <= values[value] for value in node["inputs"])
        for output in node["outputs"]:
            assert output not in values
            values[output] = phases
    assert all(output in values for output in graph_contract["graph_outputs"])


def test_operator_ledger_has_no_implicit_or_zero_cost_kind(
    graph_contract: dict,
) -> None:
    catalog = {record["kind"]: record for record in graph_contract["operator_catalog"]}
    counts = {record["kind"]: record["node_count"] for record in graph_contract["operator_counts"]}

    assert set(catalog) == set(counts)
    assert sum(counts.values()) == 1924
    assert counts["HASH_ROUTE"] == 3
    assert counts["BIASED_TOPK_ROUTE"] == 43
    assert counts["FP4_QDQ"] == 42
    assert counts["FP8_QDQ"] == 90
    assert counts["HADAMARD_ROTATE"] == 42
    assert counts["MXFP4_SWIGLU"] == 46
    assert counts["INDEX_TOPK"] == 21
    assert counts["COMPRESSED_DENSE_INDEX"] == 20
    assert counts["DSPARK_PREFILL_KV"] == 3
    assert counts["MARKOV_AUTOREGRESSIVE_LOOP"] == 1
    qualified_references = {
        "BIASED_TOPK_ROUTE": (
            "runtime.reference.selection.biased_topk_route_indices"
        ),
        "BF16_LINEAR": "runtime.reference.matrix.bf16_linear_bf16",
        "CONFIDENCE_SCORE": "runtime.reference.confidence.confidence_score_bf16",
        "COMPRESS_PROJECT": "runtime.reference.compression.compress_project_bf16",
        "COMPRESSED_DENSE_INDEX": (
            "runtime.reference.indexing.compressed_dense_indices"
        ),
        "DSPARK_NOISE_EMBED": (
            "runtime.reference.structural.dspark_noise_embed_bf16"
        ),
        "DSPARK_WINDOW_INDEX": "runtime.reference.indexing.dspark_window_indices",
        "EXPERT_DISPATCH": (
            "runtime.reference.dispatch.dispatch_routed_experts_bf16"
        ),
        "EXPERT_REDUCE": (
            "runtime.reference.dispatch.reduce_expert_outputs_bf16"
        ),
        "FP4_QDQ": "runtime.reference.quantization.fp4_qdq_bf16",
        "FP8_QDQ": "runtime.reference.quantization.fp8_qdq_bf16",
        "FP8_LINEAR": "runtime.reference.matrix.dense_fp8_linear_bf16",
        "HADAMARD_ROTATE": (
            "runtime.reference.hadamard.hadamard_rotate_128_bf16"
        ),
        "HASH_ROUTE": "runtime.reference.lookup.hash_route_indices",
        "HC_EXPAND": "runtime.reference.structural.hc_expand_bf16",
        "HC_POST": "runtime.reference.vector.hc_post_bf16",
        "HEAD_RMS_NORM": "runtime.reference.normalization.head_rms_norm_bf16",
        "INDEX_TOPK": "runtime.reference.selection.index_topk_indices",
        "RMS_NORM": "runtime.reference.normalization.rms_norm_bf16",
        "ROUTER_SCORE": "runtime.reference.routing.router_score_bf16",
        "ROUTER_WEIGHT_NORMALIZE": (
            "runtime.reference.routing.normalize_routed_weight_codes"
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


def test_weighted_rms_norm_profile_and_numeric_contract_are_explicit(
    graph_contract: dict,
) -> None:
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "RMS_NORM"
    ]
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
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "BF16_LINEAR"
    ]
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
    nodes = [
        node for node in graph_contract["nodes"] if node["kind"] == "ROUTER_SCORE"
    ]
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
        node
        for node in graph_contract["nodes"]
        if node["kind"] == "CONFIDENCE_SCORE"
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
        node
        for node in graph_contract["nodes"]
        if node["kind"] == "COMPRESS_PROJECT"
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


def test_layer_classes_and_mutable_state_sites_are_explicit(
    graph_contract: dict,
) -> None:
    by_id = {node["id"]: node for node in graph_contract["nodes"]}

    assert "main.layer00.compress_pool" not in by_id
    assert by_id["main.layer02.compress_pool"]["attributes"] == {
        "overlap": True,
        "ratio": 4,
    }
    assert "main.layer02.index_topk" in by_id
    assert by_id["main.layer03.compress_pool"]["attributes"] == {
        "overlap": False,
        "ratio": 128,
    }
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
        "dspark.layer00.kv_fp8_qdq.output"
    )
    mutable_nodes = [
        node
        for node in graph_contract["nodes"]
        if node["state_reads"] or node["state_writes"]
    ]
    assert mutable_nodes
    assert all(node["state_writes"] for node in mutable_nodes if node["kind"] != "SPARSE_ATTENTION")


def test_system_gaps_include_dspark_acceptance_and_text_frontend(
    graph_contract: dict,
) -> None:
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
    assert "twenty-four complete matrix/vector/normalization/structural/index/lookup/selection/routing/conversion" in (
        issues["DSV4-SEM-005"]["issue"]
    )
    assert "all 72,317 official tensors" in issues["DSV4-SEM-007"]["issue"]
    assert "atomic hash-locked applicator" in issues["DSV4-SEM-007"]["issue"]
    assert graph_contract["system_scope"]["request_boundary"] == (
        "token_ids_and_start_position"
    )
    assert (
        "end-to-end binding of the verified host boundary to "
        "checkpoint-derived logits"
    ) in (
        graph_contract["system_scope"]["unresolved"]
    )
    assert "hash-verified local tokenizer encode and decode behavior" in (
        graph_contract["system_scope"]["covered"]
    )
    assert "atomic hash-locked canonical application" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "unit-qualified dense FP8 linear, index-head BF16 linear, binary32 router-score, compressor, and DSpark-confidence projections, weighted RMS normalization, unweighted BF16 head RMS normalization, KV FP8 QDQ, indexer FP4 QDQ" in (
        " ".join(graph_contract["system_scope"]["covered"])
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
    assert "biased-router top-k" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "expert-dispatch" in " ".join(graph_contract["system_scope"]["covered"])
    assert "HC post-mixing" in " ".join(graph_contract["system_scope"]["covered"])
    assert "indexer FP4 QDQ" in " ".join(graph_contract["system_scope"]["covered"])
    assert "DSpark index/noise-embedding" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "routed-weight normalization" in " ".join(
        graph_contract["system_scope"]["covered"]
    )
    assert "DSpark target verification and speculative acceptance" in (
        graph_contract["system_scope"]["unresolved"]
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
        "df2bf6671cafbfbcbb9f135a70d5c9231b1ec1e3204e963f2cdf629178cd8e7e"
    )
    assert "described 1924 nodes across 43 operator kinds" in result.stdout
    assert "blocked_pending_reference_and_service_engine" in result.stdout
