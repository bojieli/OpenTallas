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
FROZEN_STRESS_ORACLE = tool.STRESS_ORACLE


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
    stress_oracle = json.loads(FROZEN_STRESS_ORACLE.read_text())
    frozen_tokens = {
        workload_id: copy.deepcopy(result["generated_token_ids"])
        for workload_id, result in stress_oracle["results"].items()
    }
    stress_oracle["transformers_version"] = "4.57.1"
    stress_oracle["attention_implementation"] = "sdpa"
    for result in stress_oracle["results"].values():
        result["prefill_association"] = _prefill_association(
            result["prompt_token_count"]
        )
    assert {
        workload_id: result["generated_token_ids"]
        for workload_id, result in stress_oracle["results"].items()
    } == frozen_tokens
    stress_path = tmp_path / FROZEN_STRESS_ORACLE.name
    stress_path.write_text(json.dumps(stress_oracle))

    # Structural acceptance tests use a small synthetic independent-oracle
    # record.  No release artifact receives these tokens; the governed natural
    # oracle remains absent until an actual vendor-model run is performed.
    def oracle_identity(path: Path, sha256: str) -> dict:
        return {
            "path": tool._relative(path),
            "size_bytes": path.stat().st_size,
            "sha256": sha256,
        }

    natural_oracle = {
        **{key: value for key, value in stress_oracle.items() if key != "results"},
        "snapshot": str(tool.QWEN_SNAPSHOT),
        "producer": {
            "tool": tool.ORACLE_TOOL,
            "tool_version": tool.ORACLE_TOOL_VERSION,
            "command_argv": [tool.ORACLE_TOOL, "--gate-1-production"],
            "selected_workload_ids": [tool.NATURAL.workload_id],
        },
        "input_identity": {
            "workload_index": oracle_identity(
                tool.NATURAL_WORKLOAD_INDEX,
                tool.NATURAL_WORKLOAD_INDEX_SHA256,
            ),
            "workload_sources": {
                tool.NATURAL.workload_id: oracle_identity(
                    tool.NATURAL_WORKLOAD,
                    tool.NATURAL_WORKLOAD_SHA256,
                )
            },
            "exact_8k_construction": oracle_identity(
                tool.NATURAL_CONSTRUCTION,
                tool.NATURAL_CONSTRUCTION_SHA256,
            ),
            "checkpoint_lock": oracle_identity(
                tool.QWEN_CHECKPOINT_LOCK,
                tool.QWEN_CHECKPOINT_LOCK_SHA256,
            ),
        },
        "production_checkpoint_preflight": {
            "completed_before_model_framework_import": True,
            "full_byte_hash_verified": True,
            "lock_id": tool.QWEN_CHECKPOINT_LOCK_ID,
            "lock_source_sha256": tool.QWEN_CHECKPOINT_LOCK_SHA256,
            "payload_bytes": 16_381_470_720,
            "shard_count": 5,
            "tensor_count": 399,
        },
        "production_launch": {
            "explicitly_requested": True,
            "contract": {
                "schema": tool.GATE_1_LAUNCH_SCHEMA,
                "profile_id": tool.GATE_1_PROFILE_ID,
                "workload_id": tool.NATURAL.workload_id,
                "prompt_token_count": tool.NATURAL.prompt_count,
                "max_new_tokens": tool.NATURAL.cap,
                "selection": "greedy_lowest_token_id_argmax",
                "terminal": {
                    "eos_token_ids": [151645, 151643],
                    "include_eos_in_output": True,
                    "rule": "first_official_eos_or_exact_cap",
                },
                "prefill": {
                    "mode": "chunked_forward_kv_cache",
                    "chunk_tokens": 512,
                },
                "numeric": {
                    "dtype": "bfloat16",
                    "attention_implementation": "sdpa",
                },
                "placement": {
                    "policy": "auto",
                    "gpu_memory_gib": 8,
                    "cpu_memory_gib": 80,
                },
            },
        },
        "results": {
            tool.NATURAL.workload_id: {
                "kind": "long_natural_chat",
                "workload_digest": tool.NATURAL.workload_digest,
                "prompt_token_count": tool.NATURAL.prompt_count,
                "generated_token_ids": [18, 24, 16, 151645],
                "generated_token_count": 4,
                "stop_reason": "eos",
                "raw_decoded_text": "391<|im_end|>",
                "visible_decoded_text": "391",
                "wall_seconds": 1.0,
                "prefill_association": _prefill_association(
                    tool.NATURAL.prompt_count
                ),
            }
        },
    }
    natural_path = tmp_path / "qwen3_reference_oracle_exact_8k_chat.json"
    natural_path.write_text(json.dumps(natural_oracle))
    monkeypatch.setattr(tool.NATURAL, "oracle_path", natural_path)
    monkeypatch.setattr(tool.STRESS, "oracle_path", stress_path)


def test_cli_help_renders_for_the_fixed_record_pair() -> None:
    completed = subprocess.run(
        [sys.executable, str(REPO / "tools/check_qwen3_w10_acceptance.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0
    assert "{natural,stress} RECORD [RECORD ...]" in completed.stdout


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


def _record(mode: str, backend: str, deployment_root: Path) -> dict:
    spec = tool.NATURAL if mode == "natural" else tool.STRESS
    workload = json.loads(spec.workload_path.read_text())
    oracle_body = json.loads(spec.oracle_path.read_text())
    oracle = oracle_body["results"][spec.workload_id]
    prompt = list(workload["token_ids"])
    generated = list(oracle["generated_token_ids"])
    capability_path = tool.CAPABILITIES[backend]
    capability = tool.Capability.from_dict(json.loads(capability_path.read_text()))
    graph = json.loads(tool.KERNEL_IR.read_text())
    if backend == "hbm_sram":
        from compiler.backends.hbm_sram.lower import lower_to_abi3
    else:
        from compiler.backends.rom.qwen3 import lower_to_abi3
    from compiler.ir.v3.kernel_ir import KernelGraph
    from runtime.abi3.verifier import verify_deployment

    serialized = lower_to_abi3(KernelGraph.read(tool.KERNEL_IR), capability)
    serialized.write(deployment_root)
    verification = verify_deployment(serialized, capability).to_dict()
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
    terminal = oracle["stop_reason"]
    steps = [
        {
            "step": index,
            "transaction_id": index + 1,
            "phase": "prefill" if index == 0 else "decode",
            "status": "SUCCESS",
            "trap": "NONE",
            "produced_tokens": [token],
            "final_token_id": token,
            "eos_reason": (
                1 if terminal == "eos" and index == len(generated) - 1 else 0
            ),
            "instructions_retired": 7,
            "retired_work": 7,
            "instructions_predicated_off": 0,
            "wall_seconds": 1.0,
        }
        for index, token in enumerate(generated)
    ]
    prompt_digest = tool.digest_of(prompt)
    deployment = serialized.deployment_digest.hex()
    checkpoint_root = REPO / "build/qwen3-8b/deployment-final/tokenizer"
    counters = {
        "selection.tokens_selected": len(generated),
        "selection.tokens_appended": len(generated),
        "selection.vocabulary_elements": len(generated) * 151936,
        "dma.scatter_elements": len(prompt) + len(generated),
        "attention.kv_bytes_read": 10 * len(generated),
        "instructions.issued": len(generated),
        "instructions.retired": len(generated) * 7,
        "tensor.multiplications": 99,
        "hbm.bytes_read": 100 if backend == "hbm_sram" else 2,
        "hbm.bytes_written": 64,
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
            "checkpoint_root": tool._relative(checkpoint_root),
        },
        "generation_policy": policy,
        "generation_policy_digest": tool.digest_of(policy),
        "verification": verification,
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
            "reference": _identity(spec.oracle_path),
            "checkpoint_root": {
                "path": tool._relative(checkpoint_root),
                "kind": "directory",
                "content_binding": "authenticated deployment object segment SHA-256 values",
                "deployment_digest_binding": deployment,
            },
            "published_deployment": {
                "path": tool._relative(deployment_root),
                "manifest": _identity(deployment_root / "deployment.json"),
                "descriptors": _identity(deployment_root / "descriptors.bin"),
                "program": _identity(deployment_root / "program.bin"),
            },
        },
        "source_sha256": {
            relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
            for relative in sorted(tool._expected_sources(backend))
        },
        "generated_token_ids": generated,
        "generated_token_count": len(generated),
        "stop_reason": terminal,
        "failure": None,
        "token_legitimacy_problems": [],
        "oracle": {
            "artifact": tool._relative(spec.oracle_path),
            "artifact_sha256": hashlib.sha256(
                spec.oracle_path.read_bytes()
            ).hexdigest(),
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
            "terminal_kind": "eos" if terminal == "eos" else "cap",
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
        "wall_seconds": float(len(generated) * 2),
    }


def _write_records(tmp_path: Path, *bodies: dict) -> list[Path]:
    paths = [tmp_path / f"record-{index}.json" for index in range(len(bodies))]
    for path, body in zip(paths, bodies, strict=True):
        path.write_text(json.dumps(body))
    return paths


def _write_pair(tmp_path: Path, left: dict, right: dict) -> list[Path]:
    return _write_records(tmp_path, left, right)


def _natural_triplet(tmp_path: Path) -> tuple[dict, dict, dict]:
    first = _record("natural", "hbm_sram", tmp_path / "hbm-deployment-a")
    second = copy.deepcopy(first)
    # A repeat capture must be a distinct observation even when its
    # architecture and complete token sequence are identical.
    second["per_step"][0]["wall_seconds"] = 1.25
    rom = _record("natural", "rom_qwen3", tmp_path / "rom-deployment")
    return first, second, rom


def test_complete_natural_hbm_repeat_and_rom_records_pass(tmp_path):
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)
    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )
    assert result["status"] == "pass"
    assert all(result["pair_checks"].values())
    assert result["abi_profile"] == {
        "version": "3.0",
        "execution_state": "ordinary_live_hbm_sram_buffers",
        "abi_state_descriptors": 0,
        "abi_state_instructions": 0,
        "durable_journal_or_rollback": False,
        "run_failure_model": "uninterrupted_fail_stop",
    }
    assert result["text_evidence"]["input"]["rendered_text"] == json.loads(
        tool.NATURAL.workload_path.read_text()
    )["rendered_text"]
    assert result["text_evidence"]["output"]["raw_decoded_text"] == json.loads(
        tool.NATURAL.oracle_path.read_text()
    )["results"][tool.NATURAL.workload_id]["raw_decoded_text"]
    assert result["claim_boundary"]["acceptance_established"] is True
    assert all(
        row["generated_tokens_per_wall_second"] > 0
        for row in result["host_functional_simulator"]
    )


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("kind", "long_natural", "oracle workload kind differs"),
        ("prompt_token_count", 7_999, "oracle prompt token count differs"),
        ("generated_token_count", 3, "oracle generated token count is inconsistent"),
    ],
)
def test_natural_refuses_inconsistent_oracle_result_metadata(
    tmp_path, field, value, expected
):
    oracle = json.loads(tool.NATURAL.oracle_path.read_text())
    oracle["results"][tool.NATURAL.workload_id][field] = value
    tool.NATURAL.oracle_path.write_text(json.dumps(oracle))
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)

    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )

    assert result["status"] == "fail"
    assert any(expected in problem for problem in result["problems"])


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (
            lambda oracle: oracle["production_checkpoint_preflight"].__setitem__(
                "full_byte_hash_verified", False
            ),
            "checkpoint preflight differs",
        ),
        (
            lambda oracle: oracle["input_identity"]["workload_index"].__setitem__(
                "sha256", "0" * 64
            ),
            "workload index SHA-256 is not pinned",
        ),
        (
            lambda oracle: oracle["production_launch"].__setitem__(
                "explicitly_requested", False
            ),
            "production launch contract differs",
        ),
    ],
)
def test_natural_refuses_unauthenticated_oracle_launch(
    tmp_path, mutation, expected
):
    oracle = json.loads(tool.NATURAL.oracle_path.read_text())
    mutation(oracle)
    tool.NATURAL.oracle_path.write_text(json.dumps(oracle))
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)

    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )

    assert result["status"] == "fail"
    assert any(expected in problem for problem in result["problems"])


def test_same_capture_path_cannot_satisfy_natural_repeatability(tmp_path):
    hbm_a, _hbm_b, rom = _natural_triplet(tmp_path)
    hbm_path, rom_path = _write_records(tmp_path, hbm_a, rom)
    result = tool.validate("natural", [hbm_path, hbm_path, rom_path])
    assert result["status"] == "fail"
    assert result["pair_checks"]["capture_paths_distinct"] is False
    assert result["pair_checks"]["capture_artifacts_distinct"] is False


def test_byte_identical_capture_copy_cannot_satisfy_natural_repeatability(
    tmp_path,
):
    record = _record("natural", "hbm_sram", tmp_path / "hbm-deployment")
    rom = _record("natural", "rom_qwen3", tmp_path / "rom-deployment")
    result = tool.validate(
        "natural", _write_records(tmp_path, record, copy.deepcopy(record), rom)
    )
    assert result["status"] == "fail"
    assert result["pair_checks"]["capture_paths_distinct"] is True
    assert result["pair_checks"]["capture_artifacts_distinct"] is False


def test_complete_stress_hbm_rom_pair_passes_with_storage_counter_differences(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "pass"
    assert result["pair_checks"]["architectural_counters_identical"] is True


def _rewrite_stress_prefill_association(mutator) -> None:
    oracle = json.loads(tool.STRESS.oracle_path.read_text())
    association = oracle["results"][tool.STRESS.workload_id][
        "prefill_association"
    ]
    mutator(association)
    association["identity_sha256"] = tool._prefill_association_digest(association)
    tool.STRESS.oracle_path.write_text(json.dumps(oracle))


def test_stress_refuses_oracle_without_prefill_provenance(tmp_path):
    oracle = json.loads(tool.STRESS.oracle_path.read_text())
    del oracle["results"][tool.STRESS.workload_id]["prefill_association"]
    tool.STRESS.oracle_path.write_text(json.dumps(oracle))
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert "frozen oracle lacks required prefill association provenance" in result[
        "problems"
    ]


def test_stress_refuses_inconsistent_prefill_chunk_geometry(tmp_path):
    _rewrite_stress_prefill_association(
        lambda association: association["prefill"].__setitem__("chunk_count", 1)
    )
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
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
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any(expected in problem for problem in result["problems"])


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda body: body["source_sha256"].__setitem__("runtime/sim/backend.py", "0" * 64), "source is not current"),
        (lambda body: body["verification"].__setitem__("proved_retired_work", 41), "exactly prove"),
        (lambda body: body["per_step"][3].__setitem__("status", "FAILED"), "did not complete successfully"),
        (
            lambda body: body["counters"].__setitem__("state.prepares", 1),
            "ordinary live-buffer design",
        ),
        (lambda body: body["workload"]["prompt_token_ids"].__setitem__(0, 7), "frozen prompt"),
    ],
)
def test_single_record_mutations_fail_closed(tmp_path, mutate, expected):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    mutate(left)
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any(expected in problem for problem in result["problems"])


def test_short_oracle_prefix_is_not_natural_acceptance(tmp_path):
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)
    for body in (hbm_a, hbm_b, rom):
        body["generated_token_ids"].pop()
        body["generated_token_count"] -= 1
    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )
    assert result["status"] == "fail"
    assert any("not exactly the frozen oracle" in problem for problem in result["problems"])


def test_empty_association_manifest_is_refused(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    left["executed_association"]["entries"] = []
    left["executed_association"]["distinct_association_count"] = 0
    left["executed_association"]["blocked_call_count"] = 0
    left["executed_association"]["manifest_sha256"] = tool._association_digest(left["executed_association"])
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any("no entries" in problem for problem in result["problems"])


def test_individually_valid_but_different_association_manifests_are_refused(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    right["executed_association"] = _association(right["implementation_identity"], calls=2)
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert "pair check failed: executed_association_manifests_identical" in result["problems"]


def test_stress_token_divergence_is_refused_even_when_metadata_claims_agreement(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    right["generated_token_ids"][2] += 1
    right["per_step"][2]["produced_tokens"] = [right["generated_token_ids"][2]]
    right["per_step"][2]["final_token_id"] = right["generated_token_ids"][2]
    result = tool.validate("stress", _write_pair(tmp_path, left, right))
    assert result["status"] == "fail"
    assert any("not exactly the frozen oracle" in problem for problem in result["problems"])


def test_natural_repeat_requires_architectural_counter_equality(tmp_path):
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)
    hbm_b["counters"]["tensor.multiplications"] += 1
    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )
    assert result["status"] == "fail"
    assert "pair check failed: architectural_counters_identical" in result["problems"]


def test_missing_serialized_deployment_is_not_w10_evidence(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    del left["inputs"]["published_deployment"]

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("published_deployment is required" in p for p in result["problems"])


def test_corrupted_serialized_program_is_refused_on_readback(tmp_path):
    root = tmp_path / "hbm-deployment"
    left = _record("stress", "hbm_sram", root)
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    program = root / "program.bin"
    body = bytearray(program.read_bytes())
    body[-1] ^= 1
    program.write_bytes(body)

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("authenticated readback" in p for p in result["problems"])


def test_substituted_serialized_deployment_is_refused(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    rom_root = tmp_path / "rom-deployment"
    left["inputs"]["published_deployment"] = {
        "path": tool._relative(rom_root),
        "manifest": _identity(rom_root / "deployment.json"),
        "descriptors": _identity(rom_root / "descriptors.bin"),
        "program": _identity(rom_root / "program.bin"),
    }

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("serialized deployment digest" in p for p in result["problems"])
    assert any("serialized deployment backend" in p for p in result["problems"])


def test_stale_checkpoint_tokenizer_is_refused(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    source = REPO / "build/qwen3-8b/deployment-final/tokenizer/tokenizer.json"
    bad_root = tmp_path / "bad-checkpoint"
    bad_root.mkdir()
    (bad_root / "tokenizer.json").write_bytes(source.read_bytes() + b"\n")
    for body in (left, right):
        body["inputs"]["checkpoint_root"]["path"] = tool._relative(bad_root)
        body["model"]["checkpoint_root"] = tool._relative(bad_root)

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("not the pinned Qwen tokenizer" in p for p in result["problems"])


def test_oracle_decoded_text_mismatch_is_refused(tmp_path):
    oracle = json.loads(tool.STRESS.oracle_path.read_text())
    oracle["results"][tool.STRESS.workload_id]["raw_decoded_text"] += " altered"
    tool.STRESS.oracle_path.write_text(json.dumps(oracle))
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("decoded raw output" in p for p in result["problems"])


def test_producer_state_resource_claim_is_refused(tmp_path):
    left = _record("stress", "hbm_sram", tmp_path / "hbm-deployment")
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    left["verification"]["state_resources"] = 1

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("nonzero ABI STATE resources" in p for p in result["problems"])


def test_serialized_state_descriptor_regression_is_refused(tmp_path):
    from runtime.abi3.constants import (
        CommitPolicy,
        DType,
        NO_ID,
        Permission,
        StateClass,
        StorageClass,
    )
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType
    from runtime.abi3.verifier import verify_deployment

    helper_spec = importlib.util.spec_from_file_location(
        "abi3_test_helpers", REPO / "tests/abi3/__init__.py"
    )
    helpers = importlib.util.module_from_spec(helper_spec)
    assert helper_spec.loader is not None
    helper_spec.loader.exec_module(helpers)

    root = tmp_path / "hbm-deployment"
    left = _record("stress", "hbm_sram", root)
    right = _record("stress", "rom_qwen3", tmp_path / "rom-deployment")
    capability = tool.Capability.from_dict(
        json.loads(tool.CAPABILITIES["hbm_sram"].read_text())
    )
    deployment = Deployment.read(root)
    live_object = next(
        descriptor.descriptor_id
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
        and descriptor.payload["storage_class"] == int(StorageClass.HBM)
        and descriptor.permissions & int(Permission.WRITE)
    )
    deployment.table.add(
        Descriptor(
            descriptor_id=NO_ID,
            descriptor_type=ExtendedDescriptorType.STATE,
            payload={
                "state_class": int(StateClass.KV_CACHE),
                "commit_policy": int(CommitPolicy.UNSTAGED),
                "element_dtype": int(DType.BF16),
                "session_binding_id": 0,
                "committed_object_id": live_object,
                "prepared_object_id": live_object,
                "row_bytes": 2,
                "capacity_rows": 1,
                "initial_cursor_rows": 0,
                "generation_bits": 64,
                "counter_class_id": NO_ID,
                "view_descriptor_id": NO_ID,
                "node_id": 0,
                "initial_digest": bytes(32),
            },
            primary_object_id=live_object,
            secondary_object_id=live_object,
            permissions=int(
                Permission.READ
                | Permission.STATE_PREPARE
                | Permission.STATE_COMMIT
            ),
        )
    )
    helpers.restamp(deployment)
    deployment.write(root)
    left["target"]["deployment_digest"] = deployment.deployment_digest.hex()
    left["inputs"]["checkpoint_root"]["deployment_digest_binding"] = (
        deployment.deployment_digest.hex()
    )
    left["inputs"]["published_deployment"] = {
        "path": tool._relative(root),
        "manifest": _identity(root / "deployment.json"),
        "descriptors": _identity(root / "descriptors.bin"),
        "program": _identity(root / "program.bin"),
    }
    left["verification"] = verify_deployment(deployment, capability).to_dict()

    result = tool.validate("stress", _write_pair(tmp_path, left, right))

    assert result["status"] == "fail"
    assert any("contains an ABI STATE descriptor" in p for p in result["problems"])


def test_invalid_eos_placement_is_refused(tmp_path):
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)
    for body in (hbm_a, hbm_b, rom):
        body["generated_token_ids"][-1] = 1
        body["per_step"][-1]["produced_tokens"] = [1]
        body["per_step"][-1]["final_token_id"] = 1

    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )

    assert result["status"] == "fail"
    assert any("first-EOS-or-exact-cap" in p for p in result["problems"])


def test_prompt_decode_and_encode_round_trip_are_required(tmp_path, monkeypatch):
    workload = json.loads(tool.NATURAL.workload_path.read_text())
    workload["rendered_text"] = "X" + workload["rendered_text"]
    workload["rendered_text_sha256"] = hashlib.sha256(
        workload["rendered_text"].encode("utf-8")
    ).hexdigest()
    path = tmp_path / "changed-natural-workload.json"
    path.write_text(json.dumps(workload))
    monkeypatch.setattr(tool.NATURAL, "workload_path", path)
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)

    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )

    assert result["status"] == "fail"
    assert any("decoded prompt" in p for p in result["problems"])
    assert any("round-trip to the frozen prompt" in p for p in result["problems"])


def test_natural_output_encode_round_trip_is_required(tmp_path):
    from tokenizers import Tokenizer

    oracle = json.loads(tool.NATURAL.oracle_path.read_text())
    stress_oracle = json.loads(tool.STRESS.oracle_path.read_text())
    stress = stress_oracle["results"][tool.STRESS.workload_id][
        "generated_token_ids"
    ]
    generated = (stress * 8)[: tool.NATURAL.cap]
    tokenizer = Tokenizer.from_file(
        str(REPO / "build/qwen3-8b/deployment-final/tokenizer/tokenizer.json")
    )
    result_body = oracle["results"][tool.NATURAL.workload_id]
    result_body["generated_token_ids"] = generated
    result_body["generated_token_count"] = len(generated)
    result_body["raw_decoded_text"] = tokenizer.decode(
        generated, skip_special_tokens=False
    )
    result_body["visible_decoded_text"] = tokenizer.decode(
        generated, skip_special_tokens=True
    )
    result_body["stop_reason"] = "max_new_tokens"
    tool.NATURAL.oracle_path.write_text(json.dumps(oracle))
    hbm_a, hbm_b, rom = _natural_triplet(tmp_path)

    result = tool.validate(
        "natural", _write_records(tmp_path, hbm_a, hbm_b, rom)
    )

    assert result["status"] == "fail"
    assert any("natural decoded output" in p for p in result["problems"])
