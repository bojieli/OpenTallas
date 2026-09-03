"""Mutation tests for the independent Qwen W10 acceptance gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_qwen3_w10_acceptance",
    REPO / "tools/check_qwen3_w10_acceptance.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)
FROZEN_ORACLE = tool.ORACLE


def _prefill_association(prompt_token_count: int) -> dict:
    configured_chunk_tokens = 512
    association = {
        "schema": tool.PREFILL_ASSOCIATION_SCHEMA,
        "association_policy": tool.PREFILL_ASSOCIATION_POLICY,
        "producer": {
            "tool": tool.ORACLE_TOOL,
            "tool_version": tool.ORACLE_TOOL_VERSION,
            "source_sha256": hashlib.sha256(
                (REPO / tool.ORACLE_TOOL).read_bytes()
            ).hexdigest(),
        },
        "framework": {
            "python_version": "3.12.3",
            "torch_version": "2.10.0+cu128",
            "transformers_version": "4.57.1",
        },
        "attention": {
            "requested_implementation": "sdpa",
            "model_config_implementation": "sdpa",
            "sdpa_kernel_flags": {
                "flash_sdp_enabled": True,
                "math_sdp_enabled": True,
                "mem_efficient_sdp_enabled": True,
                "cudnn_sdp_enabled": True,
            },
        },
        "device": {
            "placement_policy": "auto",
            "model_device": "cuda:0",
            "model_device_map": {"": "cuda:0"},
            "hardware": [
                {"type": "cpu", "name": "test-cpu", "machine": "x86_64"},
                {
                    "type": "cuda",
                    "index": 0,
                    "name": "test-gpu",
                    "compute_capability": [8, 0],
                },
            ],
        },
        "backend": {
            "cuda_runtime_version": "12.8",
            "cudnn_version": "90000",
            "cpu_capability": "AVX512",
            "torch_build_config_sha256": "1" * 64,
            "torch_num_threads": 8,
            "torch_num_interop_threads": 1,
            "thread_environment": {
                "OMP_NUM_THREADS": "8",
                "OPENBLAS_NUM_THREADS": "8",
                "MKL_NUM_THREADS": "8",
            },
        },
        "numeric": {
            "dtype": "bfloat16",
            "allow_tf32": False,
            "float32_matmul_precision": "highest",
        },
        "model_class": "transformers.Qwen3ForCausalLM",
        "prefill": {
            "mode": "chunked_forward_kv_cache",
            "configured_chunk_tokens": configured_chunk_tokens,
            "effective_chunk_tokens": configured_chunk_tokens,
            "chunk_count": (
                prompt_token_count + configured_chunk_tokens - 1
            )
            // configured_chunk_tokens,
            "prompt_token_count": prompt_token_count,
            "cache_transport": "past_key_values",
        },
    }
    association["identity_sha256"] = tool._prefill_association_digest(association)
    return association


@pytest.fixture(autouse=True)
def _oracle_with_prefill_provenance(tmp_path, monkeypatch) -> None:
    oracle = json.loads(FROZEN_ORACLE.read_text())
    frozen_tokens = {
        workload_id: copy.deepcopy(result["generated_token_ids"])
        for workload_id, result in oracle["results"].items()
    }
    oracle["transformers_version"] = "4.57.1"
    oracle["attention_implementation"] = "sdpa"
    for result in oracle["results"].values():
        result["prefill_association"] = _prefill_association(
            result["prompt_token_count"]
        )
    assert {
        workload_id: result["generated_token_ids"]
        for workload_id, result in oracle["results"].items()
    } == frozen_tokens
    oracle_path = tmp_path / FROZEN_ORACLE.name
    oracle_path.write_text(json.dumps(oracle))
    monkeypatch.setattr(tool, "ORACLE", oracle_path)


def test_cli_help_renders_for_the_fixed_record_pair() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO / "tools/check_qwen3_w10_acceptance.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "{natural,stress} RECORD RECORD" in completed.stdout


def test_oracle_cli_help_exposes_association_controls() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO / tool.ORACLE_TOOL), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "--attention-implementation {sdpa,eager}" in completed.stdout
    assert "association provenance" in " ".join(completed.stdout.split())


def _identity(path: Path) -> dict:
    return {
        "path": tool._relative(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _association(implementation: dict, *, calls: int = 1) -> dict:
    body = {
        "schema": tool.ASSOCIATION_SCHEMA,
        "association_policy": tool.ASSOCIATION_POLICY,
        "implementation_identity": copy.deepcopy(implementation),
        "entries": [
            {
                "numeric_contract": tool.BLOCKED_CONTRACT,
                "activation_shape": [512, 4096],
                "weight_shape": [4096, 4096],
                "output_shape": [512, 4096],
                "call_count": calls,
            }
        ],
        "distinct_association_count": 1,
        "blocked_call_count": calls,
    }
    body["manifest_sha256"] = tool._association_digest(body)
    return body


def _record(mode: str, backend: str) -> dict:
    spec = tool.NATURAL if mode == "natural" else tool.STRESS
    workload = json.loads(spec.workload_path.read_text())
    oracle_body = json.loads(tool.ORACLE.read_text())
    oracle = oracle_body["results"][spec.workload_id]
    prompt = list(workload["token_ids"])
    generated = list(oracle["generated_token_ids"])
    capability_path = tool.CAPABILITIES[backend]
    capability = tool.Capability.from_dict(json.loads(capability_path.read_text()))
    graph = json.loads(tool.KERNEL_IR.read_text())
    implementation = {
        "backend": "numpy",
        "library": "numpy",
        "library_version": "2.2.6",
        "device": "host",
        "device_name": "test-host",
        "blocked_association": "shape and thread pinned",
        "flags": {
            "OMP_NUM_THREADS": "8",
            "OPENBLAS_NUM_THREADS": "8",
            "MKL_NUM_THREADS": "8",
            "allow_tf32": False,
            "float32_matmul_precision": "highest",
        },
    }
    policy = {
        "selection_mode": 0,
        "tie_rule": 0,
        "eos_count": 2,
        "eos_token_0": 151645,
        "eos_token_1": 151643,
        "eos_token_2": 4294967295,
        "eos_token_3": 4294967295,
        "eos_token_4": 4294967295,
        "eos_token_5": 4294967295,
        "eos_token_6": 4294967295,
        "eos_token_7": 4294967295,
        "vocabulary_size": 151936,
        "rng_seed_hi": 0,
        "rng_seed_lo": 0,
        "max_new_tokens": 8256,
        "counter_class_id": 1,
        "token_ring_object_id": 1,
    }
    steps = [
        {
            "step": index,
            "transaction_id": index + 1,
            "phase": "prefill" if index == 0 else "decode",
            "status": "SUCCESS",
            "trap": "NONE",
            "produced_tokens": [token],
            "final_token_id": token,
            "eos_reason": 0,
            "instructions_retired": 7,
            "retired_work": 7,
            "instructions_predicated_off": 0,
            "wall_seconds": 1.0,
        }
        for index, token in enumerate(generated)
    ]
    prompt_digest = tool.digest_of(prompt)
    deployment = ("1" if backend == "hbm_sram" else "2") * 64
    counters = {
        "selection.tokens_selected": len(generated),
        "selection.tokens_appended": len(generated),
        "selection.vocabulary_elements": len(generated) * 151936,
        "state.prepares": len(generated),
        "state.commits": len(generated),
        "state.rows_committed": len(prompt) + len(generated) - 1,
        "state.bytes_read": 10,
        "state.bytes_written": 10,
        "instructions.issued": len(generated),
        "instructions.retired": len(generated) * 7,
        "tensor.multiplications": 99,
        "hbm.bytes_read": 100 if backend == "hbm_sram" else 2,
        "rom.bytes_read": 0 if backend == "hbm_sram" else 100,
        "sram.bytes_read": 0 if backend == "hbm_sram" else 3,
    }
    return {
        "schema": tool.RECORD_SCHEMA,
        "status": "pass",
        "evidence_class": "functional_artifact_only",
        "tool": "tools/run_accelerator_tokens.py",
        "backend": backend,
        "target": {
            "target_id": "hbm-sram-abi3-single_chip" if backend == "hbm_sram" else "qwen3-8b-rom-single-chip",
            "backend": tool.TARGET_BACKENDS[backend],
            "topology_class": 0,
            "node_count": 1,
            "capability": str(capability_path.relative_to(REPO)),
            "capability_digest": capability.digest,
            "deployment_digest": deployment,
            "technology_view": capability.technology_view,
        },
        "workload": {
            "workload_id": spec.workload_id,
            "workload_digest": spec.workload_digest,
            "prompt_token_ids": prompt,
            "prompt_token_count": len(prompt),
            "max_new_tokens": spec.cap,
            "rendered_text_sha256": workload["rendered_text_sha256"],
            "prompt_token_ids_sha256": prompt_digest,
            "tokenizer_sha256": tool.TOKENIZER_SHA256,
        },
        "model": {
            "model_id": "qwen3-8b",
            "graph_id": graph["graph_id"],
            "numeric_profile": "qwen3_bf16_gqa_target_v1",
            "checkpoint_root": "/checkpoint",
        },
        "generation_policy": policy,
        "generation_policy_digest": tool.digest_of(policy),
        "verification": {
            "admitted": True,
            "checks": {"deployment_digest": True, "proved_work_bound": True},
            "errors": [],
            "proved_retired_work": 42,
            "declared_retired_work": 42,
        },
        "implementation_identity": implementation,
        "executed_association": _association(implementation),
        "inputs": {
            "kernel_ir": _identity(tool.KERNEL_IR),
            "capability": _identity(capability_path),
            "workload": {
                **_identity(spec.workload_path),
                "declared_workload_digest": spec.workload_digest,
                "prompt_token_ids_sha256": prompt_digest,
                "tokenizer_sha256": tool.TOKENIZER_SHA256,
            },
            "reference": _identity(tool.ORACLE),
            "checkpoint_root": {
                "path": "/checkpoint",
                "kind": "directory",
                "content_binding": "authenticated deployment object segment SHA-256 values",
                "deployment_digest_binding": deployment,
            },
        },
        "source_sha256": {
            relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
            for relative in sorted(tool._expected_sources(backend))
        },
        "generated_token_ids": generated,
        "generated_token_count": len(generated),
        "stop_reason": "max_new_tokens",
        "failure": None,
        "token_legitimacy_problems": [],
        "oracle": {
            "artifact": tool._relative(tool.ORACLE),
            "artifact_sha256": hashlib.sha256(tool.ORACLE.read_bytes()).hexdigest(),
            "evidence_class": "external_reference_comparator",
            "generated_token_ids": generated,
            "agreement": True,
            "first_divergence_index": None,
            "compared_tokens": len(generated),
            "oracle_token_count": len(generated),
        },
        "terminal_acceptance": {
            "contract": spec.terminal_contract,
            "accepted": True,
            "terminal_kind": "cap",
            "failed_checks": [],
        },
        "counters": counters,
        "counter_scope": {
            "aggregate": "cluster_total",
            "per_node": "engine_work_by_node_id",
            "node_count": 1,
            "node_counters_index": "NODE_ID",
        },
        "node_counters": [
            {
                "selection.tokens_selected": len(generated),
                "selection.tokens_appended": len(generated),
            }
        ],
        "per_step": steps,
    }


def _write_pair(tmp_path: Path, left: dict, right: dict) -> list[Path]:
    paths = [tmp_path / "left.json", tmp_path / "right.json"]
    for path, body in zip(paths, (left, right)):
        path.write_text(json.dumps(body))
    return paths


def test_two_complete_natural_hbm_records_pass(tmp_path):
    left = _record("natural", "hbm_sram")
    right = copy.deepcopy(left)
    # Independent captures have distinct observed timings even though all
    # architecture and token evidence must agree.
    right["per_step"][0]["wall_seconds"] = 1.25
    result = tool.validate("natural", _write_pair(tmp_path, left, right))
    assert result["status"] == "pass"
    assert all(result["pair_checks"].values())


def test_same_capture_path_cannot_satisfy_natural_repeatability(tmp_path):
    record = _record("natural", "hbm_sram")
    path = _write_pair(tmp_path, record, copy.deepcopy(record))[0]
    result = tool.validate("natural", [path, path])
    assert result["status"] == "fail"
    assert result["pair_checks"]["capture_paths_distinct"] is False
    assert result["pair_checks"]["capture_artifacts_distinct"] is False


def test_byte_identical_capture_copy_cannot_satisfy_natural_repeatability(
    tmp_path,
):
    record = _record("natural", "hbm_sram")
    result = tool.validate(
        "natural", _write_pair(tmp_path, record, copy.deepcopy(record))
    )
    assert result["status"] == "fail"
    assert result["pair_checks"]["capture_paths_distinct"] is True
    assert result["pair_checks"]["capture_artifacts_distinct"] is False


def test_complete_stress_hbm_rom_pair_passes_with_storage_counter_differences(tmp_path):
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "pass"
    assert result["pair_checks"]["architectural_counters_identical"] is True


def _rewrite_stress_prefill_association(mutator) -> None:
    oracle = json.loads(tool.ORACLE.read_text())
    association = oracle["results"][tool.STRESS.workload_id][
        "prefill_association"
    ]
    mutator(association)
    association["identity_sha256"] = tool._prefill_association_digest(association)
    tool.ORACLE.write_text(json.dumps(oracle))


def test_stress_refuses_oracle_without_prefill_provenance(tmp_path):
    oracle = json.loads(tool.ORACLE.read_text())
    del oracle["results"][tool.STRESS.workload_id]["prefill_association"]
    tool.ORACLE.write_text(json.dumps(oracle))
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert "frozen oracle lacks required prefill association provenance" in result[
        "problems"
    ]


def test_stress_refuses_inconsistent_prefill_chunk_geometry(tmp_path):
    _rewrite_stress_prefill_association(
        lambda association: association["prefill"].__setitem__("chunk_count", 1)
    )
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert "frozen oracle chunked-prefill identity is inconsistent" in result[
        "problems"
    ]


@pytest.mark.parametrize(
    ("section", "field", "expected"),
    [
        ("framework", "transformers_version", "framework versions are missing"),
        ("attention", None, "attention identity is missing"),
        ("device", "hardware", "hardware identity is missing"),
        ("backend", "torch_build_config_sha256", "PyTorch build identity is missing"),
    ],
)
def test_stress_refuses_incomplete_oracle_execution_identity(
    tmp_path, section, field, expected
):
    def remove_field(association):
        if field is None:
            association.pop(section)
        else:
            association[section].pop(field)

    _rewrite_stress_prefill_association(remove_field)
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any(expected in problem for problem in result["problems"])


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda body: body["source_sha256"].__setitem__("runtime/sim/backend.py", "0" * 64), "source is not current"),
        (lambda body: body["verification"].__setitem__("proved_retired_work", 41), "exactly prove"),
        (lambda body: body["per_step"][3].__setitem__("status", "FAILED"), "did not complete successfully"),
        (lambda body: body["counters"].__setitem__("state.commits", 31), "state.commits"),
        (lambda body: body["workload"]["prompt_token_ids"].__setitem__(0, 7), "frozen prompt"),
    ],
)
def test_single_record_mutations_fail_closed(tmp_path, mutate, expected):
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    mutate(left)
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any(expected in problem for problem in result["problems"])


def test_short_oracle_prefix_is_not_natural_acceptance(tmp_path):
    left = _record("natural", "hbm_sram")
    right = copy.deepcopy(left)
    for body in (left, right):
        body["generated_token_ids"].pop()
        body["generated_token_count"] -= 1
    result = tool.validate("natural", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any("not exactly the frozen oracle" in problem for problem in result["problems"])


def test_empty_association_manifest_is_refused(tmp_path):
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    left["executed_association"]["entries"] = []
    left["executed_association"]["distinct_association_count"] = 0
    left["executed_association"]["blocked_call_count"] = 0
    left["executed_association"]["manifest_sha256"] = tool._association_digest(left["executed_association"])
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any("no entries" in problem for problem in result["problems"])


def test_individually_valid_but_different_association_manifests_are_refused(tmp_path):
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    right["executed_association"] = _association(right["implementation_identity"], calls=2)
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert "pair check failed: executed_association_manifests_identical" in result["problems"]


def test_stress_token_divergence_is_refused_even_when_metadata_claims_agreement(tmp_path):
    left = _record("stress", "hbm_sram")
    right = _record("stress", "rom_qwen3")
    right["generated_token_ids"][2] += 1
    right["per_step"][2]["produced_tokens"] = [right["generated_token_ids"][2]]
    right["per_step"][2]["final_token_id"] = right["generated_token_ids"][2]
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any("not exactly the frozen oracle" in problem for problem in result["problems"])


def test_natural_repeat_requires_architectural_counter_equality(tmp_path):
    left = _record("natural", "hbm_sram")
    right = copy.deepcopy(left)
    right["counters"]["tensor.multiplications"] += 1
    result = tool.validate("natural", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert "pair check failed: architectural_counters_identical" in result["problems"]
