from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from compiler.frontend.checkpoint import load_checkpoint_source
from compiler.qwen3.adapter import (
    PAYLOAD_BYTES,
    TENSOR_COUNT,
    TENSOR_STRUCTURE_SHA256,
    Qwen3AdapterError,
    build_official_tensor_contract,
    build_tensor_specs,
    load_official_config,
    tensor_structure_sha256,
)
from compiler.qwen3.constants import (
    CONFIG_SHA256,
    DEFAULT_SOURCE,
    INDEX_SHA256,
    PARAMETER_COUNT,
    REVISION,
    TARGET_CONTEXT_TOKENS,
    TRANSFORMERS_CONFIG_SOURCE_SHA256,
    TRANSFORMERS_MODEL_SOURCE_SHA256,
    TRANSFORMERS_MODULAR_SOURCE_SHA256,
)
from compiler.qwen3.graph import build_graph_nodes, build_official_graph_contract
from compiler.qwen3.checking import Qwen3CheckError, verify_schedule
from compiler.qwen3.isa import (
    Qwen3MicrocodeError,
    assemble,
    decode,
    encode,
    verify,
)
from compiler.qwen3.schedule import build_schedule


ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "compiler/models/qwen3-8b"
SCHEMA_DIR = ROOT / "schemas/compiler/qwen3"


@pytest.fixture(scope="module")
def config() -> dict:
    return load_official_config()


def test_source_lock_covers_every_official_file_and_reference_source() -> None:
    source = load_checkpoint_source(DEFAULT_SOURCE)
    expected = {item["path"]: item for item in source["expected_files"]}
    reference = json.loads(
        (MODEL_DIR / "reference_sources.json").read_text(encoding="utf-8")
    )
    reference_files = {item["path"]: item for item in reference["files"]}

    assert source["repository"] == "Qwen/Qwen3-8B"
    assert source["revision"] == REVISION
    assert source["remote_code_policy"] == "disabled"
    assert len(expected) == 15
    assert expected["config.json"]["sha256"] == CONFIG_SHA256
    assert expected["model.safetensors.index.json"]["sha256"] == INDEX_SHA256
    assert len([name for name in expected if name.endswith(".safetensors")]) == 5
    assert reference["version"] == "4.51.0"
    assert (
        reference_files["src/transformers/models/qwen3/modeling_qwen3.py"]["sha256"]
        == TRANSFORMERS_MODEL_SOURCE_SHA256
    )
    assert (
        reference_files["src/transformers/models/qwen3/modular_qwen3.py"]["sha256"]
        == TRANSFORMERS_MODULAR_SOURCE_SHA256
    )
    assert (
        reference_files["src/transformers/models/qwen3/configuration_qwen3.py"][
            "sha256"
        ]
        == TRANSFORMERS_CONFIG_SOURCE_SHA256
    )


def test_adapter_recovers_all_399_tensors_and_every_parameter(config: dict) -> None:
    specs = build_tensor_specs(config)
    layers = Counter(spec.layer for spec in specs if spec.layer is not None)
    roles = Counter(spec.role for spec in specs)

    assert len(specs) == TENSOR_COUNT == 399
    assert len({spec.name for spec in specs}) == TENSOR_COUNT
    assert sum(spec.parameter_count for spec in specs) == PARAMETER_COUNT
    assert sum(spec.size_bytes for spec in specs) == PAYLOAD_BYTES
    assert tensor_structure_sha256(specs) == TENSOR_STRUCTURE_SHA256
    assert layers == Counter({layer: 11 for layer in range(36)})
    assert roles == {
        "decoder_weight": 396,
        "final_norm": 1,
        "input_embedding": 1,
        "output_head": 1,
    }
    assert specs[0].name == "model.embed_tokens.weight"
    assert specs[-1].name == "lm_head.weight"


def test_adapter_rejects_even_shape_compatible_config_drift(config: dict) -> None:
    changed = copy.deepcopy(config)
    changed["rope_theta"] = 10_000
    with pytest.raises(Qwen3AdapterError, match="differing=.*rope_theta"):
        build_tensor_specs(changed)

    changed = copy.deepcopy(config)
    changed["unknown_future_switch"] = False
    with pytest.raises(Qwen3AdapterError, match="unknown"):
        build_tensor_specs(changed)


def test_tensor_contract_is_deterministic_schema_valid_and_bound_to_8k() -> None:
    first = build_official_tensor_contract()
    second = build_official_tensor_contract()
    schema = json.loads((SCHEMA_DIR / "tensor_contract_v1.schema.json").read_text())

    assert first == second
    assert (
        first["contract_id"]
        == "520c6ee7deedd3f3d9af316ad4a9a2cc4b96c2aead80163896e67ee7b308f2d6"
    )
    assert first["model"]["target_context_tokens"] == TARGET_CONTEXT_TOKENS == 8000
    assert first["coverage"]["all_checkpoint_payloads_have_execution_roles"] is True
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(first)


def test_graph_covers_all_layers_operators_and_tensors_once(config: dict) -> None:
    nodes = build_graph_nodes(config)
    graph = build_official_graph_contract()
    kinds = Counter(node.kind for node in nodes)
    tensors = Counter(name for node in nodes for name in node.tensors)

    assert len(nodes) == 616
    assert (
        graph["graph_id"]
        == "fa8ed910df6506a06334d01a63f68aa592f5c56d7a4659de550f3e570a941a44"
    )
    assert kinds == {
        "GQA_CAUSAL_ATTENTION": 36,
        "KV_COMMIT": 36,
        "LAST_TOKEN_SELECT": 1,
        "LINEAR": 253,
        "RESIDUAL_ADD": 72,
        "RMS_NORM": 145,
        "ROPE": 36,
        "SILU_MUL": 36,
        "TOKEN_EMBEDDING_LOOKUP": 1,
    }
    assert len(tensors) == 399
    assert set(tensors.values()) == {1}
    assert graph["coverage"]["matrix_node_count"] == 253
    assert graph["execution_contract"]["maximum_total_context_tokens"] == 8000
    assert graph["nodes"][-1]["outputs"] == ["output.logits"]
    schema = json.loads((SCHEMA_DIR / "semantic_graph_v1.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(graph)


def test_full_graph_microcode_round_trips_and_fails_on_corruption(config: dict) -> None:
    specs = build_tensor_specs(config)
    nodes = build_graph_nodes(config)
    graph = build_official_graph_contract()
    program = assemble(nodes, tuple(spec.name for spec in specs), graph["graph_id"])
    payload = encode(program)
    decoded = decode(payload, program.buffers, program.weights)

    assert len(program.instructions) == 617
    assert len(program.weights) == 399
    assert len(program.buffers) == 653
    assert len(payload) == 19_796
    verify(decoded, nodes)

    corrupted = bytearray(payload)
    corrupted[-1] ^= 1
    with pytest.raises(Qwen3MicrocodeError, match="body CRC32"):
        decode(bytes(corrupted), program.buffers, program.weights)

    corrupted = bytearray(payload)
    corrupted[52 + 31] ^= 1
    # Recompute only the body CRC so the independent per-record CRC must catch it.
    import struct
    import zlib

    body = bytes(corrupted[52:])
    struct.pack_into("<I", corrupted, 16, zlib.crc32(body) & 0xFFFFFFFF)
    with pytest.raises(Qwen3MicrocodeError, match="instruction 0 CRC32"):
        decode(bytes(corrupted), program.buffers, program.weights)


def test_schedule_is_complete_dependency_checked_and_fail_closed(config: dict) -> None:
    import hashlib

    from compiler.ir.model import canonical_json_bytes

    specs = build_tensor_specs(config)
    nodes = build_graph_nodes(config)
    graph = build_official_graph_contract()
    program = assemble(nodes, tuple(spec.name for spec in specs), graph["graph_id"])
    stages = [{"stage": stage, "tensors": []} for stage in range(36)]
    for spec in specs:
        stage = spec.layer
        if spec.name == "model.embed_tokens.weight":
            stage = 0
        elif spec.name in {"model.norm.weight", "lm_head.weight"}:
            stage = 35
        assert stage is not None
        stages[stage]["tensors"].append({"name": spec.name})
    physical = {"physical_map_id": "0" * 64, "stages": stages}

    schedule = build_schedule(program, nodes, physical)
    certificate = verify_schedule(schedule, program, nodes, physical)
    assert len(schedule["slots"]) == 617
    assert schedule["summary"] == {
        "complete_count": 1,
        "kv_commit_count": 36,
        "kv_read_count": 36,
        "matrix_instruction_count": 253,
        "slot_count": 617,
        "stage_transition_count": 35,
    }
    assert certificate["status"] == "pass"
    assert certificate["kv_layer_commit_count"] == 36
    assert certificate["maximum_live_buffers"] >= 4

    corrupted = copy.deepcopy(schedule)
    corrupted["slots"][8]["dependencies"] = []
    body = {key: value for key, value in corrupted.items() if key != "schedule_id"}
    corrupted["schedule_id"] = hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    with pytest.raises(Qwen3CheckError, match="slot 8 differs"):
        verify_schedule(corrupted, program, nodes, physical)


def test_all_qwen_schemas_are_draft_2020_and_top_level_strict() -> None:
    paths = sorted(SCHEMA_DIR.glob("*.schema.json"))
    assert {path.name for path in paths} == {
        "checkpoint_validation_v1.schema.json",
        "deployment_v1.schema.json",
        "deployment_verification_v1.schema.json",
        "determinism_check_v1.schema.json",
        "eos_campaign_v1.schema.json",
        "eos_question_suite_v1.schema.json",
        "execution_report_v1.schema.json",
        "generation_result_v1.schema.json",
        "inverse_report_v1.schema.json",
        "logits_differential_v1.schema.json",
        "official_reference_report_v1.schema.json",
        "physical_map_v1.schema.json",
        "release_gate_v1.schema.json",
        "schedule_certificate_v1.schema.json",
        "schedule_v1.schema.json",
        "semantic_graph_v1.schema.json",
        "tensor_contract_v1.schema.json",
        "terminalbench_agent_campaign_v1.schema.json",
        "terminalbench_task_suite_v1.schema.json",
        "tokens_v1.schema.json",
        "workload_manifest_v1.schema.json",
    }
    for path in paths:
        value = json.loads(path.read_text(encoding="utf-8"))
        assert value["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert value["additionalProperties"] is False
        Draft202012Validator.check_schema(value)


def test_retained_release_gate_proves_full_decode_and_8000_context() -> None:
    report_path = ROOT / "results/compiler/qwen3-8b/release_gate.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    schema = json.loads((SCHEMA_DIR / "release_gate_v1.schema.json").read_text())

    Draft202012Validator(schema).validate(report)
    assert report["passed"] is True
    assert len(report["spans"]) == len(report["generated_token_ids"]) == 32
    assert all(span["all_layer_boundaries_match"] for span in report["spans"])
    assert all(
        span["logits_differential"]["maximum_absolute_error"] == 0
        for span in report["spans"]
    )
    assert report["long_context"]["final_context_tokens"] == 8000
    assert report["long_context"]["layer_boundary_count_compared"] == 36
    assert report["long_context"]["logits_differential"]["maximum_absolute_error"] == 0
    assert report["long_context"]["counter_reconciliation_exact"] is True
    assert report["long_context"]["service_counters"] == {
        "attention_calls": 36,
        "attention_multiply_add_operations": 18_876_727_296_000,
        "embedding_payload_bytes_read": 65_536_000,
        "host_to_device_weight_bytes": 16_381_470_720,
        "instructions_executed": 617,
        "kv_bytes_read": 1_179_648_000,
        "kv_bytes_written": 1_179_648_000,
        "matrix_multiplications": 253,
        "matrix_multiply_add_operations": 111_133_523_443_712,
        "output_logit_elements": 151_936,
        "rom_weight_bytes_addressed": 16_381_470_720,
        "tokens_processed": 8000,
        "vector_elements_processed": 11_239_424_000,
    }
    assert report["snapshot_reverified_against_lock"] is True
    assert [span["final_context_tokens"] for span in report["chunked_prefill"]] == [
        3,
        9,
    ]
    assert all(span["all_layer_boundaries_match"] for span in report["chunked_prefill"])


def test_frozen_workload_manifest_binds_final_evidence_and_open_gates() -> None:
    from compiler.ir.model import canonical_json_bytes

    manifest_path = ROOT / "testdata/compiler/qwen3_8b/workload_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads((SCHEMA_DIR / "workload_manifest_v1.schema.json").read_text())
    release = json.loads(
        (ROOT / "results/compiler/qwen3-8b/release_gate.json").read_text()
    )
    generation = json.loads(
        (ROOT / "results/compiler/qwen3-8b/generation.json").read_text()
    )
    deployment = json.loads(
        (ROOT / "results/compiler/qwen3-8b/deployment_verification.json").read_text()
    )
    determinism = json.loads(
        (ROOT / "results/compiler/qwen3-8b/determinism.json").read_text()
    )

    Draft202012Validator(schema).validate(manifest)
    body = {key: value for key, value in manifest.items() if key != "workload_id"}
    assert (
        manifest["workload_id"]
        == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    )
    assert manifest["generation_policy"] == {
        "batch_size": 1,
        "eos_token_ids": [151645, 151643],
        "generated_tokens": 32,
        "mode": "greedy",
        "speculative": False,
    }
    model = manifest["model"]
    assert (
        model["build_id"]
        == release["build_id"]
        == generation["build_id"]
        == deployment["build_id"]
        == determinism["build_id"]
    )
    assert model["checkpoint_lock_id"] == release["checkpoint_lock_id"]

    short = manifest["short_differential"]
    assert short["evidence_id"] == release["report_id"]
    assert short["expected_generated_token_ids"] == release["generated_token_ids"]
    assert short["expected_span_count"] == len(release["spans"]) == 32
    assert (
        short["expected_context_tokens_committed"]
        == release["spans"][-1]["final_context_tokens"]
    )
    assert (
        short["prompt_token_sha256"]
        == hashlib.sha256(canonical_json_bytes(short["prompt_token_ids"])).hexdigest()
    )
    assert short["prompt_token_sha256"] == release["spans"][0]["input_token_sha256"]

    chat = manifest["short_chat"]
    assert chat["evidence_id"] == generation["result_id"]
    assert chat["expected_generated_token_ids"] == generation["generated_token_ids"]
    assert chat["expected_generated_text"] == generation["generated_text"]
    assert chat["expected_span_count"] == len(generation["spans"]) == 32
    assert (
        chat["expected_context_tokens_committed"]
        == generation["context_tokens_committed"]
    )
    assert (
        chat["prompt_token_sha256"]
        == hashlib.sha256(canonical_json_bytes(chat["prompt_token_ids"])).hexdigest()
    )
    prompt_path = ROOT / chat["prompt_path"]
    assert (
        chat["prompt_file_sha256"]
        == hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    )

    long_context = manifest["long_context"]
    retained_long = release["long_context"]
    generated_long_tokens = [long_context["token_generator"]["token_id"]] * int(
        long_context["token_generator"]["repeat_count"]
    )
    assert len(generated_long_tokens) == long_context["context_tokens"] == 8000
    assert (
        long_context["input_token_sha256"]
        == hashlib.sha256(canonical_json_bytes(generated_long_tokens)).hexdigest()
    )
    assert long_context["input_token_sha256"] == retained_long["input_token_sha256"]
    assert (
        long_context["expected_logits_sha256"]
        == retained_long["logits_differential"]["service_sha256"]
    )
    assert (
        long_context["expected_argmax_token_id"]
        == retained_long["service_argmax_token_id"]
    )
    assert long_context["expected_counters"] == retained_long["service_counters"]
    assert long_context["release_report_id"] == release["report_id"]

    assert set(manifest["evidence_boundary"]["open_system_gates"]) == {
        "shared-hbm-sram-backend",
        "data-bearing-cycle-simulation",
        "rtl-correlation",
        "target-node-physical-implementation",
        "ppa-power-thermal-manufacturability",
    }


def test_eos_question_suite_is_content_bound_and_requires_the_8k_ceiling() -> None:
    from compiler.ir.model import canonical_json_bytes

    suite = json.loads(
        (ROOT / "testdata/compiler/qwen3_8b/eos_questions.json").read_text()
    )
    schema = json.loads((SCHEMA_DIR / "eos_question_suite_v1.schema.json").read_text())

    Draft202012Validator(schema).validate(suite)
    body = {key: value for key, value in suite.items() if key != "suite_id"}
    assert suite["suite_id"] == hashlib.sha256(canonical_json_bytes(body)).hexdigest()
    assert suite["maximum_new_tokens"] == 8000
    assert suite["warning_token_threshold"] == 800
    assert suite["eos_token_ids"] == [151645, 151643]
    assert len(suite["questions"]) == 6
    assert len({question["id"] for question in suite["questions"]}) == 6
    assert any(question["enable_thinking"] for question in suite["questions"])
    assert any(not question["enable_thinking"] for question in suite["questions"])
