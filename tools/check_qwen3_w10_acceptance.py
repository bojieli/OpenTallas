#!/usr/bin/env python3
"""Fail-closed acceptance gate for the two mandatory Qwen W10 campaigns.

The token producer is deliberately useful for short diagnostic prefixes.  W10
is stricter: it requires two complete natural HBM captures, or a complete HBM
and ROM stress pair, against the source-current frozen inputs.  This checker is
the independent consumer which refuses prefix agreement, stale sources,
incomplete admission proofs, malformed transaction evidence, and association
manifests that are empty or differ between the compared executions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402

SCHEMA = "opentallas.abi3.qwen3_w10_acceptance.v1"
RECORD_SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
ASSOCIATION_SCHEMA = "opentallas.abi3.executed_association.v1"
ASSOCIATION_POLICY = "implementation_and_executed_shape_pinned"
PAIR_POLICY = "same_implementation_and_executed_shape_manifest_v1"
TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
BLOCKED_CONTRACT = "bf16_bf16_fp32_blocked_rne_v1"

KERNEL_IR = REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json"
ORACLE = REPO / "results/abi3/qwen3_reference_oracle_long.json"
NATURAL_WORKLOAD = REPO / "build/workloads/qwen3-8b/TA-QW-8K-1.json"
STRESS_WORKLOAD = REPO / "build/workloads/qwen3-8b/TA-QW-STRESS-1.json"
CAPABILITIES = {
    "hbm_sram": REPO / "configs/hardware/abi3_capability/hbm_sram_single_chip.json",
    "rom_qwen3": REPO / "configs/hardware/abi3_capability/rom_qwen3.json",
}
TARGET_BACKENDS = {
    "hbm_sram": "hbm-sram-abi3",
    "rom_qwen3": "rom.single_chip",
}
TARGET_IDS = {
    "hbm_sram": "hbm-sram-abi3-single_chip",
    "rom_qwen3": "qwen3-8b-rom-single-chip",
}


class WorkloadSpec:
    def __init__(
        self,
        mode: str,
        workload_id: str,
        workload_digest: str,
        prompt_count: int,
        cap: int,
        workload_path: Path,
        terminal_contract: str,
        repeated_token: int | None = None,
    ) -> None:
        self.mode = mode
        self.workload_id = workload_id
        self.workload_digest = workload_digest
        self.prompt_count = prompt_count
        self.cap = cap
        self.workload_path = workload_path
        self.terminal_contract = terminal_contract
        self.repeated_token = repeated_token


NATURAL = WorkloadSpec(
    "natural",
    "TA-QW-8K-1",
    "a25704db14fb0d0d888cf5e076b43bcf94a7713e4dd06ee150bc2304e130c6a5",
    8000,
    256,
    NATURAL_WORKLOAD,
    "exact_eos_or_cap",
)
STRESS = WorkloadSpec(
    "stress",
    "TA-QW-STRESS-1",
    "da3b3d6c6612ce10e2acc851498d19f1b6526c09a5f820fadd9feee7b062f485",
    8000,
    32,
    STRESS_WORKLOAD,
    "exact_cap",
    151644,
)

# Independent non-removable minimum for a governed token capture.  Every extra
# path a producer records is checked too; this list prevents omission from
# turning a changed implementation into a source-current record.
COMMON_SOURCES = (
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
BACKEND_SOURCES = {
    "hbm_sram": (
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
    "rom_qwen3": (
        "compiler/backends/rom/qwen3.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except ValueError:
        return str(path.resolve())


def _resolved_record_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    candidate = Path(value)
    return candidate.resolve() if candidate.is_absolute() else (REPO / candidate).resolve()


def _integer(value: object, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _load(path: Path) -> dict[str, Any]:
    body = json.loads(path.read_text())
    if not isinstance(body, dict):
        raise ValueError(f"{path} is not a JSON object")
    return body


def _expected_sources(backend: str) -> set[str]:
    engines = {
        str(path.relative_to(REPO))
        for path in (REPO / "runtime/sim/engines").glob("*.py")
    }
    return set(COMMON_SOURCES) | set(BACKEND_SOURCES[backend]) | engines


def _check_source_lock(record: Mapping[str, Any], backend: str) -> list[str]:
    problems: list[str] = []
    source_map = record.get("source_sha256")
    if not isinstance(source_map, dict) or not source_map:
        return ["source_sha256 is missing or empty"]
    for relative, expected in sorted(source_map.items(), key=lambda item: str(item[0])):
        if not isinstance(relative, str) or Path(relative).is_absolute() or Path(relative).as_posix() != relative:
            problems.append(f"source path is not normalized repository-relative: {relative!r}")
            continue
        path = (REPO / relative).resolve()
        try:
            path.relative_to(REPO.resolve())
        except ValueError:
            problems.append(f"source path escapes repository: {relative}")
            continue
        if not path.is_file():
            problems.append(f"source file is missing: {relative}")
        elif not isinstance(expected, str) or expected != _sha256(path):
            problems.append(f"source is not current: {relative}")
    for relative in sorted(_expected_sources(backend) - set(source_map)):
        problems.append(f"record does not bind required source {relative}")
    return problems


def _check_file_identity(
    identity: object, expected_path: Path, label: str
) -> list[str]:
    if not isinstance(identity, dict):
        return [f"inputs.{label} is not an object"]
    problems: list[str] = []
    actual_path = _resolved_record_path(identity.get("path"))
    if actual_path != expected_path.resolve():
        problems.append(f"inputs.{label}.path does not name {_relative(expected_path)}")
    if identity.get("sha256") != _sha256(expected_path):
        problems.append(f"inputs.{label}.sha256 is not source-current")
    if identity.get("bytes") != expected_path.stat().st_size:
        problems.append(f"inputs.{label}.bytes is not source-current")
    return problems


def _check_inputs(
    record: Mapping[str, Any], spec: WorkloadSpec, backend: str, prompt_digest: str
) -> list[str]:
    inputs = record.get("inputs")
    if not isinstance(inputs, dict):
        return ["inputs is not an object"]
    problems: list[str] = []
    problems += _check_file_identity(inputs.get("kernel_ir"), KERNEL_IR, "kernel_ir")
    problems += _check_file_identity(inputs.get("capability"), CAPABILITIES[backend], "capability")
    problems += _check_file_identity(inputs.get("workload"), spec.workload_path, "workload")
    problems += _check_file_identity(inputs.get("reference"), ORACLE, "reference")
    workload_identity = inputs.get("workload")
    if isinstance(workload_identity, dict):
        if workload_identity.get("declared_workload_digest") != spec.workload_digest:
            problems.append("inputs.workload declared digest is not frozen")
        if workload_identity.get("prompt_token_ids_sha256") != prompt_digest:
            problems.append("inputs.workload prompt digest is not frozen")
        if workload_identity.get("tokenizer_sha256") != TOKENIZER_SHA256:
            problems.append("inputs.workload tokenizer digest is not frozen")
    checkpoint = inputs.get("checkpoint_root")
    if not isinstance(checkpoint, dict):
        problems.append("inputs.checkpoint_root is not an object")
    else:
        if checkpoint.get("kind") != "directory" or not checkpoint.get("path"):
            problems.append("checkpoint root is not a named directory boundary")
        if checkpoint.get("content_binding") != "authenticated deployment object segment SHA-256 values":
            problems.append("checkpoint root lacks the authenticated object binding")
        target = record.get("target") if isinstance(record.get("target"), dict) else {}
        if checkpoint.get("deployment_digest_binding") != target.get("deployment_digest"):
            problems.append("checkpoint deployment binding differs from target deployment")
    # If a published deployment is retained, every byte named by its identity
    # must still be present and current.  It is optional at producer level.
    published = inputs.get("published_deployment")
    if published is not None:
        if not isinstance(published, dict):
            problems.append("inputs.published_deployment is not an object")
        else:
            root = _resolved_record_path(published.get("path"))
            for name, filename in (("manifest", "deployment.json"), ("descriptors", "descriptors.bin"), ("program", "program.bin")):
                if root is None:
                    problems.append("published deployment has no path")
                    break
                path = root / filename
                if not path.is_file():
                    problems.append(f"published deployment is missing {filename}")
                else:
                    problems += _check_file_identity(published.get(name), path, f"published_deployment.{name}")
    return problems


def _association_without_digest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in manifest.items() if key != "manifest_sha256"}


def _association_digest(manifest: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        _association_without_digest(manifest),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _check_association(record: Mapping[str, Any]) -> list[str]:
    manifest = record.get("executed_association")
    if not isinstance(manifest, dict):
        return ["executed_association is not an object"]
    problems: list[str] = []
    if manifest.get("schema") != ASSOCIATION_SCHEMA:
        problems.append("executed association schema is not governed v1")
    if manifest.get("association_policy") != ASSOCIATION_POLICY:
        problems.append("executed association policy is not shape-pinned")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        problems.append("executed association manifest has no entries")
        entries = []
    calls = 0
    keys: list[tuple[Any, ...]] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            problems.append(f"association entry {index} is not an object")
            continue
        a, w, out = (entry.get("activation_shape"), entry.get("weight_shape"), entry.get("output_shape"))
        if entry.get("numeric_contract") != BLOCKED_CONTRACT:
            problems.append(f"association entry {index} uses the wrong contract")
        if not all(isinstance(shape, list) and len(shape) == 2 and all(_integer(v, minimum=1) for v in shape) for shape in (a, w, out)):
            problems.append(f"association entry {index} has invalid shapes")
        elif a[1] != w[1] or out != [a[0], w[0]]:
            problems.append(f"association entry {index} shapes do not contract")
        call_count = entry.get("call_count")
        if not _integer(call_count, minimum=1):
            problems.append(f"association entry {index} has invalid call_count")
        else:
            calls += int(call_count)
        keys.append((entry.get("numeric_contract"), tuple(a or []), tuple(w or []), tuple(out or [])))
    if len(keys) != len(set(keys)) or keys != sorted(keys):
        problems.append("association entries are not unique canonical order")
    if manifest.get("distinct_association_count") != len(entries):
        problems.append("association distinct count is inconsistent")
    if manifest.get("blocked_call_count") != calls or calls <= 0:
        problems.append("association blocked call count is inconsistent or empty")
    if manifest.get("manifest_sha256") != _association_digest(manifest):
        problems.append("association manifest digest is invalid")
    identity = record.get("implementation_identity")
    expected_identity = dict(identity) if isinstance(identity, dict) else {}
    expected_identity.pop("device_memory_bytes", None)
    if not expected_identity or "unavailable" in expected_identity:
        problems.append("implementation identity is unavailable")
    if manifest.get("implementation_identity") != expected_identity:
        problems.append("association implementation identity differs from record")
    return problems


def _frozen_inputs(spec: WorkloadSpec) -> tuple[dict[str, Any], dict[str, Any], list[int], list[int], list[str]]:
    problems: list[str] = []
    workload = _load(spec.workload_path)
    oracle = _load(ORACLE)
    prompt = workload.get("token_ids")
    if not isinstance(prompt, list) or not all(_integer(token) for token in prompt):
        prompt = []
        problems.append("frozen workload has an invalid prompt token list")
    if workload.get("workload_id") != spec.workload_id or workload.get("digest") != spec.workload_digest:
        problems.append("frozen workload id/digest differs from the W10 contract")
    if len(prompt) != spec.prompt_count or workload.get("max_new_tokens") != spec.cap:
        problems.append("frozen workload length/budget differs from the W10 contract")
    if spec.repeated_token is not None and prompt != [spec.repeated_token] * spec.prompt_count:
        problems.append("frozen stress prompt is not 8,000 copies of token 151644")
    if oracle.get("schema") != "opentallas.abi3.reference_oracle.v1" or oracle.get("model_id") != "qwen3-8b":
        problems.append("frozen oracle has the wrong schema/model")
    if oracle.get("tokenizer_sha256") != TOKENIZER_SHA256:
        problems.append("frozen oracle tokenizer is not the pinned tokenizer")
    result = (oracle.get("results") or {}).get(spec.workload_id, {})
    gold = result.get("generated_token_ids") if isinstance(result, dict) else None
    if not isinstance(gold, list) or not all(_integer(token) for token in gold):
        gold = []
        problems.append("frozen oracle has no valid gold sequence")
    if result.get("workload_digest") != spec.workload_digest:
        problems.append("frozen oracle workload digest differs from W10")
    if spec is STRESS and (len(gold) != spec.cap or result.get("stop_reason") != "max_new_tokens"):
        problems.append("frozen stress oracle is not the exact 32-token cap sequence")
    return workload, result, list(prompt), list(gold), problems


def _check_verification(record: Mapping[str, Any]) -> list[str]:
    report = record.get("verification")
    if not isinstance(report, dict):
        return ["verification is not an object"]
    problems: list[str] = []
    checks = report.get("checks")
    if report.get("admitted") is not True:
        problems.append("deployment was not admitted")
    if report.get("errors") != []:
        problems.append("verification carries errors")
    if not isinstance(checks, dict) or not checks or any(value is not True for value in checks.values()):
        problems.append("verification checks are missing or not all true")
    proved, declared = report.get("proved_retired_work"), report.get("declared_retired_work")
    if not _integer(proved, minimum=1) or proved != declared:
        problems.append("admission did not exactly prove the declared retired work")
    return problems


def _check_steps_and_counters(
    record: Mapping[str, Any], generated: Sequence[int], prompt_count: int, terminal: str
) -> list[str]:
    problems: list[str] = []
    steps = record.get("per_step")
    if not isinstance(steps, list) or len(steps) != len(generated):
        return ["per_step count does not equal generated token count"]
    retired = 0
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append(f"per_step[{index}] is not an object")
            continue
        if step.get("step") != index or step.get("transaction_id") != index + 1:
            problems.append(f"per_step[{index}] has the wrong step/transaction id")
        if step.get("phase") != ("prefill" if index == 0 else "decode"):
            problems.append(f"per_step[{index}] has the wrong phase")
        if step.get("status") != "SUCCESS" or step.get("trap") != "NONE":
            problems.append(f"per_step[{index}] did not complete successfully")
        if step.get("produced_tokens") != [generated[index]] or step.get("final_token_id") != generated[index]:
            problems.append(f"per_step[{index}] does not bind its generated token")
        value = step.get("instructions_retired")
        if not _integer(value, minimum=1) or step.get("retired_work") != value:
            problems.append(f"per_step[{index}] retired-work evidence is invalid")
        else:
            retired += int(value)
        reason = step.get("eos_reason")
        allowed = {1} if terminal == "eos" and index == len(steps) - 1 else ({0, 2} if terminal == "cap" and index == len(steps) - 1 else {0})
        if reason not in allowed:
            problems.append(f"per_step[{index}] has inconsistent EOS reason {reason!r}")
    counters = record.get("counters")
    if not isinstance(counters, dict):
        return problems + ["counters is not an object"]
    required = {
        "selection.tokens_selected": len(generated),
        "selection.tokens_appended": len(generated),
        "selection.vocabulary_elements": len(generated) * 151936,
        "state.prepares": len(generated),
        "state.commits": len(generated),
        "state.rows_committed": prompt_count + max(0, len(generated) - 1),
        "instructions.retired": retired,
    }
    for name, expected in required.items():
        if counters.get(name) != expected:
            problems.append(f"counter {name} is {counters.get(name)!r}, expected {expected}")
    if counters.get("selection.invalid_tokens", 0) != 0:
        problems.append("selection.invalid_tokens is nonzero")
    for name in ("state.bytes_read", "state.bytes_written", "instructions.issued"):
        if not _integer(counters.get(name), minimum=1):
            problems.append(f"counter {name} is missing or not positive")
    scope, nodes = record.get("counter_scope"), record.get("node_counters")
    if not isinstance(scope, dict) or scope.get("aggregate") != "cluster_total" or scope.get("per_node") != "engine_work_by_node_id" or scope.get("node_count") != 1 or scope.get("node_counters_index") != "NODE_ID":
        problems.append("counter scope is not an explicit measured one-node split")
    if not isinstance(nodes, list) or len(nodes) != 1 or not isinstance(nodes[0], dict):
        problems.append("node_counters is not one measured node")
    else:
        for name in ("selection.tokens_selected", "selection.tokens_appended"):
            if nodes[0].get(name) != len(generated):
                problems.append(f"node counter {name} is inconsistent")
    return problems


def _terminal_kind(
    record: Mapping[str, Any], spec: WorkloadSpec, generated: Sequence[int], gold: Sequence[int], oracle_result: Mapping[str, Any]
) -> tuple[str | None, list[str]]:
    problems: list[str] = []
    policy = record.get("generation_policy")
    if not isinstance(policy, dict):
        return None, ["generation_policy is not an object"]
    if record.get("generation_policy_digest") != digest_of(policy):
        problems.append("generation policy digest is invalid")
    semantic = {"selection_mode": 0, "tie_rule": 0, "eos_count": 2, "eos_token_0": 151645, "eos_token_1": 151643, "vocabulary_size": 151936, "rng_seed_hi": 0, "rng_seed_lo": 0}
    for name, expected in semantic.items():
        if policy.get(name) != expected:
            problems.append(f"generation policy {name} is not frozen")
    eos = {151645, 151643}
    stop = record.get("stop_reason")
    terminal: str | None = None
    if stop == "eos" and generated and generated[-1] in eos and not any(token in eos for token in generated[:-1]) and oracle_result.get("stop_reason") == "eos" and len(generated) == len(gold):
        terminal = "eos"
    elif stop == "max_new_tokens" and len(generated) == spec.cap and len(gold) == spec.cap and oracle_result.get("stop_reason") == "max_new_tokens" and not any(token in eos for token in generated):
        terminal = "cap"
    if terminal is None or (spec is STRESS and terminal != "cap"):
        problems.append("terminal state is not the frozen first-EOS-or-exact-cap contract")
    producer = record.get("terminal_acceptance")
    if not isinstance(producer, dict) or producer.get("contract") != spec.terminal_contract or producer.get("accepted") is not True or producer.get("terminal_kind") != terminal or producer.get("failed_checks") != []:
        problems.append("producer terminal_acceptance is absent or inconsistent")
    return terminal, problems


def _check_record(
    path: Path, spec: WorkloadSpec, expected_backend: str, workload: Mapping[str, Any], oracle_result: Mapping[str, Any], prompt: Sequence[int], gold: Sequence[int]
) -> dict[str, Any]:
    record = _load(path)
    problems: list[str] = []
    if record.get("schema") != RECORD_SCHEMA or record.get("status") != "pass":
        problems.append("record is not a passing accelerator_tokens.v1 artifact")
    if record.get("evidence_class") != "functional_artifact_only" or record.get("tool") != "tools/run_accelerator_tokens.py":
        problems.append("record has the wrong evidence boundary or producer")
    if record.get("backend") != expected_backend:
        problems.append(f"record backend is not {expected_backend}")
    target = record.get("target")
    capability = Capability.from_dict(_load(CAPABILITIES[expected_backend]))
    deployment_digest = target.get("deployment_digest") if isinstance(target, dict) else None
    digest_valid = (
        isinstance(deployment_digest, str)
        and len(deployment_digest) == 64
        and all(character in "0123456789abcdef" for character in deployment_digest)
    )
    if (
        not isinstance(target, dict)
        or target.get("target_id") != TARGET_IDS[expected_backend]
        or target.get("backend") != TARGET_BACKENDS[expected_backend]
        or target.get("node_count") != 1
        or target.get("topology_class") != 0
        or target.get("capability_digest") != capability.digest
        or target.get("technology_view") != capability.technology_view
        or _resolved_record_path(target.get("capability"))
        != CAPABILITIES[expected_backend].resolve()
        or not digest_valid
    ):
        problems.append("target is not the source-current governed one-node lane")
    work = record.get("workload")
    prompt_digest = digest_of(list(prompt))
    if not isinstance(work, dict):
        problems.append("workload is not an object")
    else:
        expected = {
            "workload_id": spec.workload_id,
            "workload_digest": spec.workload_digest,
            "prompt_token_count": spec.prompt_count,
            "max_new_tokens": spec.cap,
            "prompt_token_ids_sha256": prompt_digest,
            "tokenizer_sha256": TOKENIZER_SHA256,
            "rendered_text_sha256": workload.get("rendered_text_sha256", ""),
        }
        for name, value in expected.items():
            if work.get(name) != value:
                problems.append(f"workload.{name} is not the frozen value")
        if work.get("prompt_token_ids") != list(prompt):
            problems.append("workload prompt tokens are not the frozen prompt")
    model, graph = record.get("model"), _load(KERNEL_IR)
    if not isinstance(model, dict) or model.get("model_id") != "qwen3-8b" or model.get("numeric_profile") != "qwen3_bf16_gqa_target_v1" or model.get("graph_id") != graph.get("graph_id"):
        problems.append("model identity is not the source-current Qwen graph")
    generated = record.get("generated_token_ids")
    if not isinstance(generated, list) or not generated or not all(_integer(token) and token < 151936 for token in generated):
        generated = []
        problems.append("generated token sequence is empty or illegitimate")
    if record.get("generated_token_count") != len(generated):
        problems.append("generated_token_count is inconsistent")
    if generated != list(gold):
        problems.append("generated tokens are not exactly the frozen oracle sequence")
    if record.get("failure") is not None or record.get("token_legitimacy_problems") != []:
        problems.append("record carries a failure or legitimacy problem")
    oracle = record.get("oracle")
    if not isinstance(oracle, dict) or oracle.get("artifact_sha256") != _sha256(ORACLE) or _resolved_record_path(oracle.get("artifact")) != ORACLE.resolve() or oracle.get("evidence_class") != "external_reference_comparator" or oracle.get("generated_token_ids") != list(gold) or oracle.get("agreement") is not True or oracle.get("first_divergence_index") is not None or oracle.get("compared_tokens") != len(generated) or oracle.get("oracle_token_count") != len(gold):
        problems.append("oracle evidence is not exact and source-current")
    terminal, terminal_problems = _terminal_kind(record, spec, generated, gold, oracle_result)
    problems += terminal_problems
    problems += _check_verification(record)
    problems += _check_inputs(record, spec, expected_backend, prompt_digest)
    problems += _check_source_lock(record, expected_backend)
    problems += _check_association(record)
    problems += _check_steps_and_counters(record, generated, spec.prompt_count, terminal or "invalid")
    return {
        "path": _relative(path),
        "sha256": _sha256(path),
        "backend": expected_backend,
        "generated_token_ids": generated,
        "terminal_kind": terminal,
        "association_manifest_sha256": (record.get("executed_association") or {}).get("manifest_sha256"),
        "record": record,
        "problems": problems,
        "passes": not problems,
    }


def _without_timing(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _without_timing(item) for key, item in value.items() if key not in {"wall_seconds", "lowering_seconds"}}
    if isinstance(value, list):
        return [_without_timing(item) for item in value]
    return value


def _non_storage(counters: Mapping[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in counters.items() if not name.startswith(("hbm.", "rom.", "sram."))}


def validate(mode: str, paths: Sequence[Path]) -> dict[str, Any]:
    spec = NATURAL if mode == "natural" else STRESS
    workload, oracle_result, prompt, gold, problems = _frozen_inputs(spec)
    if len(paths) != 2:
        problems.append(f"{mode} acceptance requires exactly two records")
        rows: list[dict[str, Any]] = []
    else:
        backends = ["hbm_sram", "hbm_sram"] if mode == "natural" else ["hbm_sram", "rom_qwen3"]
        rows = [_check_record(path, spec, backend, workload, oracle_result, prompt, gold) for path, backend in zip(paths, backends)]
        for row in rows:
            problems.extend(f"{Path(row['path']).name}: {problem}" for problem in row["problems"])
    pair_checks: dict[str, bool] = {}
    if len(rows) == 2:
        left, right = rows[0]["record"], rows[1]["record"]
        pair_checks = {
            "full_token_sequences_identical": rows[0]["generated_token_ids"] == rows[1]["generated_token_ids"] == gold,
            "executed_association_manifests_identical": left.get("executed_association") == right.get("executed_association"),
            "implementation_identities_identical": left.get("implementation_identity") == right.get("implementation_identity"),
            "architectural_counters_identical": (left.get("counters") == right.get("counters") if mode == "natural" else _non_storage(left.get("counters") or {}) == _non_storage(right.get("counters") or {})),
            "per_step_architecture_identical": _without_timing(left.get("per_step")) == _without_timing(right.get("per_step")),
        }
        for name, passed in pair_checks.items():
            if not passed:
                problems.append(f"pair check failed: {name}")
    document = {
        "schema": SCHEMA,
        "status": "pass" if not problems else "fail",
        "mode": mode,
        "workload_id": spec.workload_id,
        "association_pair_policy": PAIR_POLICY,
        "records": [{key: row[key] for key in ("path", "sha256", "backend", "terminal_kind", "association_manifest_sha256", "passes", "problems")} for row in rows],
        "pair_checks": pair_checks,
        "problems": problems,
        "claim_boundary": {
            "functional_execution_only": True,
            "timing_or_performance": False,
            "rtl_or_silicon": False,
        },
    }
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("natural", "stress"))
    parser.add_argument(
        "records",
        type=Path,
        nargs=2,
        metavar="RECORD",
        help="natural: HBM run 1/run 2; stress: HBM/ROM",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        document = validate(args.mode, args.records)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for problem in document["problems"]:
        print(f"PROBLEM {problem}")
    print(f"W10 {args.mode}: {document['status']}")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(canonical_json(document))
        print(f"wrote {args.output}")
    return 0 if document["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
