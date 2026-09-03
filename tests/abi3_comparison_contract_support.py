"""Small source-locked comparison materials for focused W11.2 tests."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from compiler.ir.v3.kernel_ir import Entrypoint, KernelGraph
from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import StorageClass
from runtime.abi3.descriptors import Phase, Symbol
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.cycle.machine import CostTable
from runtime.driver import GenerationDriver
from tools.abi3_comparison_boundary import (
    CONTRACT_PATHS,
    REQUEST_TRAJECTORY_SCHEMA,
    boundary_digest,
    build_boundary,
    comparison_workload_digest,
    legacy_workload_digest,
    request_trajectory_digest,
    validate_comparison_contract,
)

ROOT = Path(__file__).resolve().parents[1]
COMPARISON_ID = "qwen3_rom_single_chip_vs_hbm_single_chip"
DEEPSEEK_COMPARISON_ID = "deepseek_v4_rom_wafer_vs_hbm_cluster_32"
FUNCTIONAL_COMMON_SOURCES = (
    "tools/run_accelerator_tokens.py",
    "compiler/backends/numeric_contracts.py",
    "compiler/ir/v3/kernel_ir.py",
    "compiler/ir/v3/lowering.py",
    "compiler/ir/v3/numeric.py",
    "runtime/abi3/builder.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/layout.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "runtime/driver.py",
    "runtime/evidence.py",
    "runtime/reference/compression_pool.py",
    "runtime/reference/formats.py",
    "runtime/reference/hadamard.py",
    "runtime/reference/hyper_connection.py",
    "runtime/reference/normalization.py",
    "runtime/reference/quantization.py",
    "runtime/reference/sparse_attention.py",
    "runtime/reference/sqrt_softplus.py",
    "runtime/reference/swiglu.py",
    "runtime/reference/transcendental.py",
    "runtime/sim/backend.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/memory.py",
    "runtime/tensor_accelerator/attention.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/elementwise.py",
    "runtime/tensor_accelerator/rmsnorm.py",
    "runtime/tensor_accelerator/rope.py",
    "runtime/tensor_accelerator/sparse_attention.py",
)
FUNCTIONAL_ENGINE_SOURCES = tuple(
    path.relative_to(ROOT).as_posix()
    for path in sorted((ROOT / "runtime/sim/engines").glob("*.py"))
)
FUNCTIONAL_BACKEND_SOURCES = {
    (COMPARISON_ID, "rom"): (
        "compiler/backends/rom/qwen3.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
    (DEEPSEEK_COMPARISON_ID, "rom"): (
        "compiler/backends/rom/deepseek_v4.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
    (COMPARISON_ID, "hbm"): (
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
    (DEEPSEEK_COMPARISON_ID, "hbm"): (
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
}
ORACLE_PRODUCERS = {
    COMPARISON_ID: "tools/run_qwen3_reference_oracle.py",
    DEEPSEEK_COMPARISON_ID: "tools/run_deepseek_v4_reference_oracle.py",
}


def functional_source_paths(comparison_id: str, role: str) -> tuple[str, ...]:
    return (
        *FUNCTIONAL_COMMON_SOURCES,
        *FUNCTIONAL_ENGINE_SOURCES,
        *FUNCTIONAL_BACKEND_SOURCES[(comparison_id, role)],
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, body: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


def semantic_digest(body: Any) -> str:
    return hashlib.sha256(canonical_json(body)).hexdigest()


def policy_identity(contract: dict[str, Any], role: str) -> dict[str, Any]:
    policy = contract["policy"]
    target = contract["targets"][role]
    return {
        "schema": "opentallas.abi3.comparison_cost_policy.v1",
        "comparison_id": contract["comparison_id"],
        "target_role": role,
        "policy_id": target["cost_policy"]["policy_id"],
        "technology_view": policy["technology_view"],
        "pvt": policy["pvt"],
        "clock": policy["clock"],
        "evidence_class": policy["evidence_class"],
        "latency_boundary": policy["latency_boundary"],
        "state_boundary": policy["state_boundary"],
        "external_memory_policy": policy["external_memory_policy"],
        "external_fabric_policy": policy["external_fabric_policy"],
    }


def _locked(path: str, digest: str, source_sha256: str) -> dict[str, Any]:
    return {
        "status": "locked",
        "path": path,
        "digest": digest,
        "source_sha256": source_sha256,
    }


def _deployment(storage: StorageClass, capability, backend: str, graph_id: str):
    original_finish = DeploymentBuilder.finish

    def finish_with_graph(builder, **kwargs):
        builder.source_identity["graph_id"] = graph_id
        return original_finish(builder, **kwargs)

    with patch.object(DeploymentBuilder, "finish", finish_with_graph):
        return build_fixture(
            storage_class=storage,
            capability=capability,
            backend=backend,
        )


def governed_request(
    contract: dict[str, Any], deployment, generation_index: int
) -> dict[str, Any]:
    """Construct the exact request the generation driver issues at one step."""

    phase = Phase.PREFILL if generation_index == 0 else Phase.DECODE
    entrypoint = next(
        entry for entry in deployment.entrypoints if entry["phase"] == int(phase)
    )
    _topology = deployment.topology_class
    node_count = next(
        descriptor.payload["node_count"]
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type.name == "TOPOLOGY"
    )
    driver = GenerationDriver(
        SimpleNamespace(deployment=deployment, node_count=node_count)
    )
    named_deployment_symbols = {
        Symbol(symbol_id).name: value
        for symbol_id, value in driver.deployment_symbols.items()
    }
    prompt_count = contract["workload"]["prompt_token_count"]
    max_new_tokens = contract["execution"]["generation"]["max_new_tokens"]
    if generation_index == 0:
        span_tokens = prompt_count
        position_start = 0
        span_last_index = prompt_count - 1
    else:
        span_tokens = 1
        position_start = prompt_count + generation_index - 1
        span_last_index = 0
    return {
        "entrypoint_id": entrypoint["entrypoint_id"],
        "generation_policy_id": entrypoint["generation_policy_id"],
        "transactions": 1,
        "label": "",
        "symbols": {
            **named_deployment_symbols,
            "SPAN_TOKENS": span_tokens,
            "POSITION_START": position_start,
            "POSITION_END": position_start + span_tokens,
            "CONTEXT_LENGTH": position_start + span_tokens,
            "PHASE": int(phase),
            "MAX_NEW_TOKENS": max_new_tokens,
            "BATCH": contract["execution"]["batch"],
            "GENERATION_INDEX": generation_index,
            "SPAN_LAST_INDEX": span_last_index,
        },
    }


def request_trajectory_rows(
    bundle: dict[str, Any], role: str, generated_count: int
) -> list[dict[str, Any]]:
    deployment = bundle["roles"][role]["deployment"]
    return [
        {
            "transaction_id": index + 1,
            "phase": "prefill" if index == 0 else "decode",
            "request": governed_request(bundle["contract"], deployment, index),
        }
        for index in range(generated_count)
    ]


def make_locked_repository(
    repo: Path,
    *,
    comparison_id: str = COMPARISON_ID,
    namespace: str = "fixture",
    max_new_tokens: int = 3,
    oracle_generated_token_ids: list[int] | None = None,
    oracle_stop_reason: str = "eos",
) -> dict[str, Any]:
    """Create one tiny but fully source-revalidated registered contract."""

    repo.mkdir(parents=True, exist_ok=True)
    generation = {
        "eos_token_ids": [7],
        "include_eos_in_output": True,
        "maximum_new_tokens": max_new_tokens,
        "policy_id": "fixture_greedy_v1",
        "selection_mode": "greedy_argmax_lowest_id",
        "stop_condition": "first_official_eos_or_maximum_new_tokens",
        "tie_rule": "lowest_token_id",
        "vocabulary_size": 8,
    }
    graph = KernelGraph(
        model_id="abi3-fixture",
        source={"exporter": f"w11.2-focused-test-{namespace}"},
        symbols=(),
        tensors=(),
        states=(),
        kernels=(),
        entrypoints=(
            Entrypoint("prefill", (), (), (), "fixture_greedy_v1"),
            Entrypoint("decode", (), (), (), "fixture_greedy_v1"),
        ),
        numeric_profile=f"{namespace}_bf16_v1",
        generation_policy=generation,
    )
    graph_path = repo / f"build/ir-v3/abi3-{namespace}/kernel_ir.v3.json"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph.write(graph_path)

    rendered_text = "one two three"
    workload = {
        "workload_id": f"TA-W11-2-{namespace.upper()}-1",
        "kind": "contract_test",
        "token_ids": [1, 2, 3],
        "prompt_token_count": 3,
        "max_new_tokens": max_new_tokens,
        "rendered_text": rendered_text,
        "rendered_text_sha256": hashlib.sha256(rendered_text.encode()).hexdigest(),
    }
    workload["digest"] = legacy_workload_digest(workload)
    workload_path = (
        repo
        / f"build/workloads/abi3-{namespace}/TA-W11-2-{namespace.upper()}-1.json"
    )
    write_json(workload_path, workload)

    tokenizer_sha256 = "2" * 64
    index = {
        "schema": "opentallas.abi3.workload_index.v1",
        "model_id": graph.model_id,
        "tokenizer_sha256": tokenizer_sha256,
        "workloads": {
            workload["workload_id"]: {
                "digest": workload["digest"],
                "kind": workload["kind"],
                "prompt_token_count": workload["prompt_token_count"],
                "max_new_tokens": workload["max_new_tokens"],
                "path": workload_path.name,
            }
        },
    }
    index_path = repo / f"build/workloads/abi3-{namespace}/index.json"
    write_json(index_path, index)

    template_path = repo / f"configs/abi3/templates/{namespace}_prompt_v1.txt"
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text("{prompt}\n", encoding="utf-8")

    frequency_hz = 57_959_000
    contract: dict[str, Any] = {
        "schema": "opentallas.abi3.comparison_contract.v1",
        "version": "1.0.0",
        "comparison_id": comparison_id,
        "model": {
            "model_id": graph.model_id,
            "kernel_ir_path": graph_path.relative_to(repo).as_posix(),
            "kernel_ir_source_sha256": sha256_file(graph_path),
            "graph_id": graph.graph_id,
            "numeric_profile": graph.numeric_profile,
        },
        "workload": {
            "workload_id": workload["workload_id"],
            "kind": workload["kind"],
            "path": workload_path.relative_to(repo).as_posix(),
            "source_sha256": sha256_file(workload_path),
            "digest": workload["digest"],
            "prompt_token_count": workload["prompt_token_count"],
            "max_new_tokens": workload["max_new_tokens"],
            "index_path": index_path.relative_to(repo).as_posix(),
            "index_schema": index["schema"],
            "index_source_sha256": sha256_file(index_path),
            "tokenizer_sha256": tokenizer_sha256,
            "rendered_text_sha256": workload["rendered_text_sha256"],
            "template": {
                "mode": "source_file",
                "template_id": f"{namespace}_prompt_v1",
                "path": template_path.relative_to(repo).as_posix(),
                "source_sha256": sha256_file(template_path),
            },
        },
        "execution": {
            "evidence_scope": "full_workload",
            "phases": ["prefill", "decode"],
            "context_tokens": 3,
            "batch": 1,
            "concurrency": 1,
            "generation": {
                "selection_mode": generation["selection_mode"],
                "tie_rule": generation["tie_rule"],
                "eos_token_ids": generation["eos_token_ids"],
                "include_eos_in_output": generation["include_eos_in_output"],
                "stop_condition": generation["stop_condition"],
                "max_new_tokens": max_new_tokens,
                "vocabulary_size": generation["vocabulary_size"],
            },
        },
        "external_oracle": {
            "evidence_class": "external_reference_comparator",
            "path": f"results/abi3/{namespace}-contract-oracle.json",
            "producer": {
                "source_sha256": None,
                "tool": ORACLE_PRODUCERS[comparison_id],
            },
            "schema": "opentallas.abi3.reference_oracle.v1",
            "source_sha256": None,
            "status": "pending",
        },
        "policy": {
            "technology_view": "asap7",
            "technology_claim": "predictive fixture only",
            "pvt": {
                "corner_id": "asap7_tt_0p70v_25c",
                "process": "TT",
                "voltage_v": 0.7,
                "temperature_c": 25,
            },
            "clock": {
                "policy_id": f"{namespace}_common_clock_v1",
                "same_frequency_required": True,
                "comparison_frequency_hz": frequency_hz,
            },
            "evidence_class": f"{namespace}_characterized_v1",
            "latency_boundary": "host_to_terminal_v1",
            "state_boundary": "fresh_prefill_decode_v1",
            "external_memory_policy": "fixture_memory_v1",
            "external_fabric_policy": "fixture_no_fabric_v1",
        },
        "targets": {},
    }

    role_specs = {
        "rom": (StorageClass.ROM, f"{namespace}.rom", "fixture-rom"),
        "hbm": (StorageClass.HBM, f"{namespace}.hbm", "fixture-hbm"),
    }
    for role, (storage, backend, target_id) in role_specs.items():
        contract["targets"][role] = {
            "role": role,
            "backend": backend,
            "target_id": target_id,
            "storage_class": storage.name,
            "topology_class": 0,
            "node_count": 1,
            "deployment": {
                "status": "pending",
                "path": f"build/abi3/{namespace}-{role}",
                "digest": None,
                "source_sha256": None,
            },
            "capability": {
                "status": "pending",
                "path": (
                    f"configs/hardware/abi3_capability/{namespace}_{role}.json"
                ),
                "digest": None,
                "source_sha256": None,
            },
            "cost_policy": {
                "policy_id": f"{namespace}_{role}_cost_policy_v1",
                "cost_table_id": f"abi3-cost-{namespace}-{role}-v1",
                "lock": {
                    "status": "pending",
                    "path": (
                        f"configs/hardware/abi3_cost_{namespace}_{role}_v1.json"
                    ),
                    "digest": None,
                    "source_sha256": None,
                },
            },
        }

    materials: dict[str, Any] = {}
    baseline = json.loads(
        (ROOT / "configs/hardware/abi3_cost_asap7_v2.json").read_text(
            encoding="utf-8"
        )
    )
    for role, (storage, backend, _target_id) in role_specs.items():
        target = contract["targets"][role]
        capability = fixture_capability()
        capability.technology_view = "asap7"
        capability_path = repo / target["capability"]["path"]
        write_json(capability_path, capability.to_dict())

        deployment = _deployment(storage, capability, backend, graph.graph_id)
        deployment_path = repo / target["deployment"]["path"]
        deployment.write(deployment_path)

        cost_body = copy.deepcopy(baseline)
        cost_body["cost_table_id"] = target["cost_policy"]["cost_table_id"]
        cost_body["technology_view"] = "asap7"
        cost_body["parameters"]["clock.frequency_hz"]["value"] = frequency_hz
        cost_body["comparison_policy"] = policy_identity(contract, role)
        cost_path = repo / target["cost_policy"]["lock"]["path"]
        write_json(cost_path, cost_body)
        cost_table = CostTable.from_dict(cost_body, path=cost_path)

        target["deployment"] = _locked(
            target["deployment"]["path"],
            deployment.deployment_digest.hex(),
            sha256_file(deployment_path / "deployment.json"),
        )
        target["capability"] = _locked(
            target["capability"]["path"],
            capability.digest,
            sha256_file(capability_path),
        )
        target["cost_policy"]["lock"] = _locked(
            target["cost_policy"]["lock"]["path"],
            cost_table.digest,
            sha256_file(cost_path),
        )
        materials[role] = {
            "comparison_id": comparison_id,
            "deployment": deployment,
            "deployment_path": deployment_path,
            "capability": capability,
            "capability_path": capability_path,
            "cost_table": cost_table,
            "cost_table_path": cost_path,
            "workload_path": workload_path,
            "request": governed_request(contract, deployment, 0),
            "repo": repo,
        }

    fixture_sources = {
        "tools/run_abi3_cycle.py",
        ORACLE_PRODUCERS[comparison_id],
        *(path for role in ("rom", "hbm") for path in functional_source_paths(comparison_id, role)),
    }
    for source in sorted(fixture_sources):
        write_json(repo / source, {"fixture_source": source})

    oracle_path = repo / contract["external_oracle"]["path"]
    oracle_generated = list(oracle_generated_token_ids or [4, 5, 7])
    oracle = {
        "schema": "opentallas.abi3.reference_oracle.v1",
        "evidence_class": "external_reference_comparator",
        "model_id": graph.model_id,
        "tokenizer_sha256": tokenizer_sha256,
        "results": {
            workload["workload_id"]: {
                "workload_digest": workload["digest"],
                "prompt_token_count": workload["prompt_token_count"],
                "prompt_token_ids_sha256": semantic_digest(workload["token_ids"]),
                "generated_token_ids": oracle_generated,
                "generated_token_count": len(oracle_generated),
                "stop_reason": oracle_stop_reason,
            }
        },
    }
    write_json(oracle_path, oracle)
    contract["external_oracle"].update(
        source_sha256=sha256_file(oracle_path),
        status="locked",
    )
    oracle_producer_path = repo / contract["external_oracle"]["producer"]["tool"]
    contract["external_oracle"]["producer"]["source_sha256"] = sha256_file(
        oracle_producer_path
    )

    contract_path = repo / CONTRACT_PATHS[comparison_id]
    write_json(contract_path, contract)
    validation = validate_comparison_contract(
        contract,
        repo=repo,
        source_path=contract_path,
    )
    if not validation["ready"]:
        raise AssertionError(validation)
    return {
        "repo": repo,
        "namespace": namespace,
        "contract": contract,
        "contract_path": contract_path,
        "contract_validation": validation,
        "workload": workload,
        "workload_path": workload_path,
        "index_path": index_path,
        "template_path": template_path,
        "graph": graph,
        "graph_path": graph_path,
        "oracle_generated_token_ids": oracle_generated,
        "oracle_stop_reason": oracle_stop_reason,
        "roles": materials,
    }


def make_cycle_measurement(
    bundle: dict[str, Any],
    role: str,
    request: dict[str, Any],
    produced_tokens: list[int],
    transaction_id: int,
) -> dict[str, Any]:
    """Publish one nonempty, source-reopenable cycle result for one request."""

    arguments = dict(bundle["roles"][role])
    arguments["request"] = request
    boundary = build_boundary(**arguments)
    inputs = cycle_inputs(bundle, boundary, request=request)
    total_cycles = 100 + transaction_id
    frequency_hz = bundle["contract"]["policy"]["clock"][
        "comparison_frequency_hz"
    ]
    seconds = total_cycles / frequency_hz
    memory_rows: dict[str, dict[str, Any]] = {}
    active_storage = bundle["contract"]["targets"][role]["storage_class"].lower()
    for storage_class in ("hbm", "sram", "rom", "host"):
        active = storage_class == active_storage
        memory_rows[storage_class] = {
            "accesses": 1 if active else 0,
            "bytes_read": 16 if active else 0,
            "bytes_written": 0,
            "bytes_total": 16 if active else 0,
            "busy_cycles": 2 if active else 0,
            "bandwidth_utilisation": 0.25 if active else 0.0,
        }
    timing = {
        "total_cycles": total_cycles,
        "clock_frequency_hz": frequency_hz,
        "seconds": seconds,
        "transaction_cycles": total_cycles,
        "issue_cycles": 10,
        "stall_cycles": 3,
        "queue_stall_cycles": 1,
        "wait_stall_cycles": 2,
        "memory_stall_cycles": 1,
        "tile_pipeline_stall_cycles": 0,
    }
    timing_counters = {
        f"latency.{name}": value
        for name, value in timing.items()
        if name.endswith("cycles") and type(value) is int
    }
    body = {
        "schema": "opentallas.abi3.cycle_result.v1",
        "producer": {
            "schema": "opentallas.abi3.cycle_producer.v1",
            "tool": "tools/run_abi3_cycle.py",
            "source_sha256": sha256_file(bundle["repo"] / "tools/run_abi3_cycle.py"),
            "evidence_class": "cycle_model_measurement",
        },
        "inputs": inputs,
        "comparison_boundary": boundary,
        "execution": {
            "transactions": 1,
            "status": "SUCCESS",
            "trap_class": "NONE",
            "produced_tokens": produced_tokens,
        },
        "timing": timing,
        "rates": [
            {
                "name": "transactions_per_second",
                "value": 1.0 / seconds,
                "unit": "1/s",
                "provenance": {
                    "class": "characterized",
                    "inputs": {"clock.frequency_hz": "characterized"},
                },
            },
            {
                "name": "tokens_per_second",
                "value": len(produced_tokens) / seconds,
                "unit": "tokens/s",
                "provenance": {
                    "class": "characterized",
                    "inputs": {"clock.frequency_hz": "characterized"},
                },
            },
        ],
        "counters": {
            "architectural": {"instructions.retired": 1},
            "timing": timing_counters,
        },
        "memory": memory_rows,
        "engines": {
            "tensor": {
                "operations": 1,
                "busy_cycles": 10,
                "idle_cycles": total_cycles - 10,
                "utilisation": 10 / total_cycles,
            }
        },
        "provenance": {
            "class": "characterized",
            "counts": {"characterized": 1},
            "parameters": {
                "clock.frequency_hz": {
                    "value": frequency_hz,
                    "unit": "Hz",
                    "provenance": "characterized",
                }
            },
        },
        "schedule_audit": {"complete": True, "findings": []},
        "gaps": [],
        "functional_agreement": {"checked": True, "agrees": True},
    }
    path = (
        bundle["repo"]
        / f"results/abi3/{bundle['namespace']}-{role}-cycle-{transaction_id}.json"
    )
    write_json(path, body)
    return {
        "path": path.relative_to(bundle["repo"]).as_posix(),
        "sha256": sha256_file(path),
        "schema": body["schema"],
    }


def make_functional_evidence(
    bundle: dict[str, Any],
    role: str = "rom",
    *,
    generated_token_ids: list[int] | None = None,
    aggregate_inputs: dict[str, Any] | None = None,
    trajectory_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Publish a complete accelerator artifact plus its external oracle."""

    generated = list(
        generated_token_ids
        if generated_token_ids is not None
        else bundle["oracle_generated_token_ids"]
    )
    repo = bundle["repo"]
    namespace = bundle["namespace"]
    contract = bundle["contract"]
    workload = bundle["workload"]
    target = contract["targets"][role]
    model = contract["model"]
    execution = contract["execution"]
    token_digest = semantic_digest(workload["token_ids"])

    oracle_lock = contract["external_oracle"]
    oracle_path = repo / oracle_lock["path"]
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    source_sha256 = {
        path: sha256_file(repo / path)
        for path in functional_source_paths(contract["comparison_id"], role)
    }

    per_step = [
        {
            "step": index,
            "transaction_id": index + 1,
            "phase": "prefill" if index == 0 else "decode",
            "status": "SUCCESS",
            "trap": "NONE",
            "produced_tokens": [token],
            "final_token_id": token,
        }
        for index, token in enumerate(generated)
    ]
    rows = copy.deepcopy(
        trajectory_rows
        if trajectory_rows is not None
        else request_trajectory_rows(bundle, role, len(generated))
    )
    if aggregate_inputs is None:
        full_boundary = as_full_workload_boundary(
            make_boundary(bundle, role), rows
        )
        aggregate_inputs = cycle_inputs(bundle, full_boundary)
    for row, step in zip(rows, per_step, strict=True):
        row["measurement"] = make_cycle_measurement(
            bundle,
            role,
            row["request"],
            step["produced_tokens"],
            row["transaction_id"],
        )
    functional_path = repo / f"results/abi3/{namespace}-{role}-accelerator.json"
    functional = {
        "schema": "opentallas.abi3.accelerator_tokens.v1",
        "tool": "tools/run_accelerator_tokens.py",
        "source_sha256": source_sha256,
        "status": "pass",
        "evidence_class": "functional_artifact_only",
        "failure": None,
        "comparison_workload_sha256": comparison_workload_digest(contract),
        "model": {
            "model_id": model["model_id"],
            "graph_id": model["graph_id"],
            "numeric_profile": model["numeric_profile"],
        },
        "target": {
            "role": role,
            "backend": target["backend"],
            "target_id": target["target_id"],
            "storage_class": target["storage_class"],
            "topology_class": target["topology_class"],
            "node_count": target["node_count"],
            "technology_view": contract["policy"]["technology_view"],
            "deployment_digest": target["deployment"]["digest"],
            "capability_digest": target["capability"]["digest"],
        },
        "workload": {
            "workload_id": workload["workload_id"],
            "path": contract["workload"]["path"],
            "source_sha256": contract["workload"]["source_sha256"],
            "workload_digest": workload["digest"],
            "prompt_token_ids": workload["token_ids"],
            "prompt_token_ids_sha256": token_digest,
            "prompt_token_count": workload["prompt_token_count"],
            "max_new_tokens": workload["max_new_tokens"],
            "index_path": contract["workload"]["index_path"],
            "index_source_sha256": contract["workload"]["index_source_sha256"],
            "tokenizer_sha256": contract["workload"]["tokenizer_sha256"],
            "rendered_text_sha256": contract["workload"]["rendered_text_sha256"],
            "template": contract["workload"]["template"],
        },
        "comparison_execution": {
            "scope": "full_workload",
            "phases": execution["phases"],
            "batch": execution["batch"],
            "concurrency": execution["concurrency"],
        },
        "generated_token_ids": generated,
        "generated_token_count": len(generated),
        "stop_reason": bundle["oracle_stop_reason"],
        "per_step": per_step,
        "token_legitimacy_problems": [],
        "verification": {"admitted": True},
        "oracle": {
            "artifact": oracle_path.relative_to(repo).as_posix(),
            "artifact_sha256": sha256_file(oracle_path),
            "evidence_class": oracle["evidence_class"],
            "agreement": True,
            "compared_tokens": len(generated),
            "oracle_token_count": len(generated),
            "first_divergence_index": None,
            "generated_token_ids": generated,
        },
    }
    write_json(functional_path, functional)
    return {
        "functional_artifact": {
            "path": functional_path.relative_to(repo).as_posix(),
            "sha256": sha256_file(functional_path),
            "schema": functional["schema"],
            "evidence_class": functional["evidence_class"],
        },
        "external_oracle": {
            "path": oracle_lock["path"],
            "sha256": oracle_lock["source_sha256"],
            "schema": oracle_lock["schema"],
            "evidence_class": oracle_lock["evidence_class"],
        },
        "request_trajectory": {
            "schema": REQUEST_TRAJECTORY_SCHEMA,
            "sha256": request_trajectory_digest(rows),
            "transactions": rows,
        },
    }


def make_boundary(bundle: dict[str, Any], role: str = "rom") -> dict[str, Any]:
    return build_boundary(**bundle["roles"][role])


def cycle_inputs(
    bundle: dict[str, Any],
    boundary: dict[str, Any],
    *,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    role = boundary["target"]["role"]
    inputs = {
        "model_id": boundary["model_id"],
        "model_digest": boundary["model_digest"],
        "backend": boundary["target"]["backend"],
        "target_id": boundary["target"]["target_id"],
        "topology_class": boundary["target"]["topology_class"],
        "node_count": boundary["target"]["node_count"],
        "deployment_digest": boundary["deployment"]["sha256"],
        "capability_digest": boundary["capability"]["sha256"],
        "capability_technology_view": boundary["capability"]["technology_view"],
        "cost_table": boundary["cost_table"],
        "workload": boundary["workload"],
        "comparison_digest": boundary["comparison_sha256"],
        "comparison_contract_digest": boundary["comparison_contract"]["sha256"],
        "comparison_workload_sha256": boundary["comparison_workload_sha256"],
        "comparison_execution_scope": boundary["execution_scope"],
        "comparison_boundary_digest": boundary["boundary_sha256"],
    }
    if boundary["execution_scope"] == "measurement_slice":
        inputs["request"] = (
            request if request is not None else bundle["roles"][role]["request"]
        )
    else:
        inputs["request_trajectory_sha256"] = boundary[
            "request_trajectory_sha256"
        ]
    return inputs


def as_full_workload_boundary(
    boundary: dict[str, Any],
    transactions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    full = copy.deepcopy(boundary)
    full["execution_scope"] = "full_workload"
    full.pop("request_sha256", None)
    full["request_trajectory_sha256"] = request_trajectory_digest(
        transactions or []
    )
    full["boundary_sha256"] = boundary_digest(full)
    return full
