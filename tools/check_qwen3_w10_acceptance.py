#!/usr/bin/env python3
"""Fail-closed acceptance gate for the two mandatory Qwen W10 campaigns.

The token producer is deliberately useful for short diagnostic prefixes.  W10
is stricter: it requires two complete natural HBM captures plus a complete ROM
capture, or a complete HBM and ROM stress pair, against the source-current
frozen inputs.  This checker is the independent consumer which refuses prefix
agreement, stale sources, incomplete admission proofs, malformed transaction
evidence, and association manifests that are empty or differ between the
compared executions.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    ABI_MAJOR,
    ABI_MINOR,
    Major,
    Permission,
    StorageClass,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import VerificationReport, verify_deployment  # noqa: E402
from compiler.tensor_accelerator.common import load_strict_json  # noqa: E402
from compiler.tensor_accelerator.qwen_chat import (  # noqa: E402
    EXPLICIT_VOCABULARY_SIZE,
    QwenChatTokenizer,
)
from compiler.workloads.qwen3_exact_8k import (  # noqa: E402
    AuthenticatedWorkloadTokenizer,
    EXPECTED_VISIBLE_ANSWER,
    QwenExact8KError,
    load_construction,
    validate_materialized_workload,
)

SCHEMA = "opentallas.abi3.qwen3_w10_acceptance.v1"
RECORD_SCHEMA = "opentallas.abi3.accelerator_tokens.v1"
ASSOCIATION_SCHEMA = "opentallas.abi3.executed_association.v1"
ASSOCIATION_POLICY = "implementation_and_executed_shape_pinned"
PAIR_POLICY = "same_implementation_and_executed_shape_manifest_v1"
PREFILL_ASSOCIATION_SCHEMA = "opentallas.qwen3.prefill_association.v1"
PREFILL_ASSOCIATION_POLICY = (
    "tool_framework_attention_device_backend_and_chunk_pinned_v1"
)
ORACLE_TOOL = "tools/run_qwen3_reference_oracle.py"
ORACLE_TOOL_VERSION = "qwen3_reference_oracle.py:v2"
TOKENIZER_SHA256 = "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4"
TOKENIZERS_VERSION = "0.22.2"
BLOCKED_CONTRACT = "bf16_bf16_fp32_blocked_rne_v1"
ABI_STATE_PERMISSIONS = int(Permission.STATE_PREPARE | Permission.STATE_COMMIT)

KERNEL_IR = REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json"
NATURAL_ORACLE = (
    REPO / "results/abi3/qwen3_reference_oracle_exact_8k_chat.json"
)
STRESS_ORACLE = REPO / "results/abi3/qwen3_reference_oracle_long.json"
NATURAL_WORKLOAD = REPO / "build/workloads/qwen3-8b/TA-QW-8K-1.json"
NATURAL_WORKLOAD_INDEX = REPO / "build/workloads/qwen3-8b/index.json"
STRESS_WORKLOAD = REPO / "build/workloads/qwen3-8b/TA-QW-STRESS-1.json"
NATURAL_CONSTRUCTION = (
    REPO / "configs/abi3/workloads/qwen3_exact_8k_chat_v1.json"
)
QWEN_CHECKPOINT_LOCK = (
    REPO
    / "results/tensor_accelerator/qwen3_full_model_physical/source/"
    "checkpoint.lock.json"
)
NATURAL_WORKLOAD_INDEX_SHA256 = (
    "ce7ec985a65017e692013f056828adf16695d6ecb7747eb90970cd64978c2ee9"
)
NATURAL_WORKLOAD_SHA256 = (
    "4bd1ca5cad91a6006383c4470a16fd803e18bbfad9ec19fe8ed01373da118217"
)
NATURAL_CONSTRUCTION_SHA256 = (
    "38e4a9acc569fff5ffc23ed2187cb71a551133691acac7131f4b6a7d3c8909ca"
)
QWEN_CHECKPOINT_LOCK_SHA256 = (
    "880782c1a160c466b39e2b4502649704819a96666f1de7abaacda30f090fbaaa"
)
QWEN_CHECKPOINT_LOCK_ID = (
    "fa32932d73c1f605a69db3a803f1f25ef5b022a98cc3c6b5fe42b7f7af024e2a"
)
GATE_1_LAUNCH_SCHEMA = "opentallas.qwen3.gate1_launch.v1"
GATE_1_PROFILE_ID = "qwen3_exact_8k_external_oracle_v1"
QWEN_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)
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
        oracle_path: Path = NATURAL_ORACLE,
    ) -> None:
        self.mode = mode
        self.workload_id = workload_id
        self.workload_digest = workload_digest
        self.prompt_count = prompt_count
        self.cap = cap
        self.workload_path = workload_path
        self.terminal_contract = terminal_contract
        self.repeated_token = repeated_token
        self.oracle_path = oracle_path


NATURAL = WorkloadSpec(
    "natural",
    "TA-QW-8K-1",
    "5c8fce7d61afd1e06b7a061133c0a6d639fac7d65739227f84e199d6c870297e",
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
    STRESS_ORACLE,
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
    "runtime/sim/performance.py",
    "runtime/sim/weight_cache.py",
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


def _sha256_string(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _nonempty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value)


def _available_boolean(value: object) -> bool:
    return isinstance(value, bool) or value == "unavailable"


def _prefill_association_digest(association: Mapping[str, Any]) -> str:
    body = {
        key: value
        for key, value in association.items()
        if key != "identity_sha256"
    }
    return hashlib.sha256(canonical_json(body)).hexdigest()


def _check_prefill_association(
    oracle: Mapping[str, Any],
    result: Mapping[str, Any],
    spec: WorkloadSpec,
) -> list[str]:
    """Require the oracle's association-affecting prefill provenance.

    The expected token list remains the acceptance oracle, but an 8,000-token
    BF16 prefill is not implementation-independent: changing its chunking,
    PyTorch/Transformers implementation, SDPA backend, device, or thread/TF32
    settings can change a legal reduction association and therefore the gold
    sequence.  W10 accepts the sequence only with those choices attached.
    """
    association = result.get("prefill_association")
    if not isinstance(association, dict):
        return ["frozen oracle lacks required prefill association provenance"]

    problems: list[str] = []
    if association.get("schema") != PREFILL_ASSOCIATION_SCHEMA:
        problems.append("frozen oracle prefill association schema is not governed v1")
    if association.get("association_policy") != PREFILL_ASSOCIATION_POLICY:
        problems.append("frozen oracle prefill association policy is not pinned")
    try:
        expected_digest = _prefill_association_digest(association)
    except (TypeError, ValueError):
        expected_digest = None
    if association.get("identity_sha256") != expected_digest:
        problems.append("frozen oracle prefill association digest is invalid")

    producer = association.get("producer")
    if not isinstance(producer, dict):
        problems.append("frozen oracle prefill association producer is missing")
    else:
        if producer.get("tool") != ORACLE_TOOL:
            problems.append("frozen oracle association names the wrong producer")
        if producer.get("tool_version") != ORACLE_TOOL_VERSION:
            problems.append("frozen oracle association tool version is not pinned")
        tool_path = REPO / ORACLE_TOOL
        if producer.get("source_sha256") != _sha256(tool_path):
            problems.append("frozen oracle association producer is not source-current")

    framework = association.get("framework")
    framework_fields = ("python_version", "torch_version", "transformers_version")
    if not isinstance(framework, dict) or any(
        not _nonempty_string(framework.get(name)) for name in framework_fields
    ):
        problems.append("frozen oracle framework versions are missing")
    elif (
        oracle.get("torch_version") != framework.get("torch_version")
        or oracle.get("transformers_version") != framework.get("transformers_version")
    ):
        problems.append("frozen oracle framework identity is internally inconsistent")

    attention = association.get("attention")
    if not isinstance(attention, dict):
        problems.append("frozen oracle attention identity is missing")
    else:
        requested = attention.get("requested_implementation")
        actual = attention.get("model_config_implementation")
        if requested not in {"sdpa", "eager"} or actual != requested:
            problems.append("frozen oracle attention implementation is not pinned")
        if oracle.get("attention_implementation") != requested:
            problems.append("frozen oracle attention identity is internally inconsistent")
        flags = attention.get("sdpa_kernel_flags")
        required_flags = {
            "flash_sdp_enabled",
            "math_sdp_enabled",
            "mem_efficient_sdp_enabled",
            "cudnn_sdp_enabled",
        }
        if (
            not isinstance(flags, dict)
            or set(flags) != required_flags
            or any(not _available_boolean(value) for value in flags.values())
        ):
            problems.append("frozen oracle SDPA backend identity is incomplete")

    device = association.get("device")
    if not isinstance(device, dict):
        problems.append("frozen oracle device identity is missing")
    else:
        device_map = device.get("model_device_map")
        hardware = device.get("hardware")
        if device.get("placement_policy") not in {"cpu", "auto"}:
            problems.append("frozen oracle device placement policy is invalid")
        if not _nonempty_string(device.get("model_device")):
            problems.append("frozen oracle model device is missing")
        if (
            not isinstance(device_map, dict)
            or not device_map
            or any(
                not isinstance(name, str) or not _nonempty_string(value)
                for name, value in device_map.items()
            )
        ):
            problems.append("frozen oracle model device map is missing")
        if not isinstance(hardware, list) or not hardware:
            problems.append("frozen oracle hardware identity is missing")
        else:
            for index, entry in enumerate(hardware):
                valid = (
                    isinstance(entry, dict)
                    and entry.get("type") in {"cpu", "cuda"}
                    and _nonempty_string(entry.get("name"))
                )
                if valid and entry["type"] == "cpu":
                    valid = _nonempty_string(entry.get("machine"))
                elif valid:
                    capability = entry.get("compute_capability")
                    valid = _integer(entry.get("index")) and (
                        isinstance(capability, list)
                        and len(capability) == 2
                        and all(_integer(value) for value in capability)
                    )
                if not valid:
                    problems.append(
                        f"frozen oracle hardware identity {index} is invalid"
                    )

    backend = association.get("backend")
    if not isinstance(backend, dict):
        problems.append("frozen oracle backend identity is missing")
    else:
        for name in ("cuda_runtime_version", "cudnn_version", "cpu_capability"):
            if not _nonempty_string(backend.get(name)):
                problems.append(f"frozen oracle backend {name} is missing")
        if not _sha256_string(backend.get("torch_build_config_sha256")):
            problems.append("frozen oracle PyTorch build identity is missing")
        for name in ("torch_num_threads", "torch_num_interop_threads"):
            if not _integer(backend.get(name), minimum=1):
                problems.append(f"frozen oracle backend {name} is invalid")
        environment = backend.get("thread_environment")
        required_environment = {
            "OMP_NUM_THREADS",
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
        }
        if (
            not isinstance(environment, dict)
            or set(environment) != required_environment
            or any(not isinstance(value, str) for value in environment.values())
        ):
            problems.append("frozen oracle backend thread environment is incomplete")

    numeric = association.get("numeric")
    if (
        not isinstance(numeric, dict)
        or numeric.get("dtype") != "bfloat16"
        or not _available_boolean(numeric.get("allow_tf32"))
        or not _nonempty_string(numeric.get("float32_matmul_precision"))
    ):
        problems.append("frozen oracle numeric backend identity is incomplete")
    elif oracle.get("dtype") != numeric.get("dtype"):
        problems.append("frozen oracle numeric identity is internally inconsistent")
    if not _nonempty_string(association.get("model_class")):
        problems.append("frozen oracle model implementation class is missing")

    prefill = association.get("prefill")
    if not isinstance(prefill, dict):
        problems.append("frozen oracle prefill chunk identity is missing")
    else:
        mode = prefill.get("mode")
        configured = prefill.get("configured_chunk_tokens")
        effective = prefill.get("effective_chunk_tokens")
        chunks = prefill.get("chunk_count")
        prompt = prefill.get("prompt_token_count")
        if prompt != spec.prompt_count:
            problems.append("frozen oracle prefill prompt extent differs from W10")
        if not _integer(configured) or not _integer(effective, minimum=1):
            problems.append("frozen oracle prefill chunk extent is invalid")
        elif mode == "generate_single_prefill":
            if (
                configured != 0
                or effective != spec.prompt_count
                or chunks != 1
                or prefill.get("cache_transport") != "transformers_generate_cache"
            ):
                problems.append("frozen oracle single-prefill identity is inconsistent")
        elif mode == "chunked_forward_kv_cache":
            expected_chunks = (
                (spec.prompt_count + configured - 1) // configured
                if configured
                else 0
            )
            if (
                configured < 1
                or effective != min(configured, spec.prompt_count)
                or chunks != expected_chunks
                or prefill.get("cache_transport") != "past_key_values"
            ):
                problems.append("frozen oracle chunked-prefill identity is inconsistent")
        else:
            problems.append("frozen oracle prefill call path is not a W10 path")
    return problems


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
    if not expected_path.is_file():
        return [f"source-current {label} is unavailable: {_relative(expected_path)}"]
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
    problems += _check_file_identity(
        inputs.get("reference"), spec.oracle_path, "reference"
    )
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
    # W10 is an artifact-execution claim, so the exact bundle that was written,
    # read back, admitted, and executed is mandatory evidence.  A producer may
    # omit --publish for a diagnostic prefix; that diagnostic is intentionally
    # ineligible for W10.
    published = inputs.get("published_deployment")
    if not isinstance(published, dict):
        problems.append("inputs.published_deployment is required for W10")
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


def _check_published_deployment(
    record: Mapping[str, Any],
    backend: str,
    capability: Capability,
    graph: Mapping[str, Any],
) -> tuple[Deployment | None, VerificationReport | None, list[str]]:
    """Reopen and independently admit the exact serialized W10 bundle.

    This is deliberately stricter than trusting the producer's verification
    dictionary.  ``Deployment.read`` re-decodes ``program.bin`` and
    ``descriptors.bin`` and checks every digest edge.  We then inspect the
    decoded ABI surface and run the independent verifier again.

    Qwen's live KV cache is an ordinary read/write HBM object in the final,
    simple ABI 3.0 design.  A STATE descriptor, STATE instruction, STATE
    storage object, or prepare/commit permission is therefore a regression to
    the superseded transactional representation, not additional robustness.
    """

    inputs = record.get("inputs")
    published = inputs.get("published_deployment") if isinstance(inputs, dict) else None
    root = (
        _resolved_record_path(published.get("path"))
        if isinstance(published, dict)
        else None
    )
    if root is None:
        return None, None, ["serialized deployment cannot be reopened"]

    problems: list[str] = []
    try:
        manifest = _load(root / "deployment.json")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return None, None, [
            f"serialized deployment manifest cannot be decoded: {type(exc).__name__}: {exc}"
        ]
    if manifest.get("abi") != {"major": ABI_MAJOR, "minor": ABI_MINOR}:
        problems.append("serialized deployment is not ABI 3.0")

    try:
        deployment = Deployment.read(root)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return None, None, problems + [
            f"serialized deployment failed authenticated readback: {type(exc).__name__}: {exc}"
        ]

    target = record.get("target") if isinstance(record.get("target"), dict) else {}
    source_identity = (
        deployment.source_identity
        if isinstance(deployment.source_identity, Mapping)
        else {}
    )
    identity_checks = {
        "digest": deployment.deployment_digest.hex()
        == target.get("deployment_digest"),
        "target id": deployment.target_id == TARGET_IDS[backend],
        "backend": deployment.backend == TARGET_BACKENDS[backend],
        "model id": deployment.model_id == "qwen3-8b",
        "capability digest": deployment.capability_digest == capability.digest,
        "topology class": deployment.topology_class == 0,
        "graph id": source_identity.get("graph_id") == graph.get("graph_id"),
    }
    for name, passed in identity_checks.items():
        if not passed:
            problems.append(f"serialized deployment {name} differs from the W10 record")

    try:
        header, body = split_program(deployment.program)
        instructions = decode_body(body)
    except (ValueError, KeyError, TypeError) as exc:
        return deployment, None, problems + [
            f"serialized deployment program cannot be decoded: {type(exc).__name__}: {exc}"
        ]
    if header.abi_major != ABI_MAJOR or header.abi_minor != ABI_MINOR:
        problems.append("serialized program header is not ABI 3.0")
    if manifest.get("descriptor_count") != len(deployment.table):
        problems.append("serialized manifest descriptor count is inconsistent")
    if manifest.get("instruction_count") != len(instructions):
        problems.append("serialized manifest instruction count is inconsistent")
    if manifest.get("entrypoints") != [dict(entry) for entry in deployment.entrypoints]:
        problems.append("serialized manifest entrypoints are inconsistent")
    if header.entrypoint_count != len(deployment.entrypoints):
        problems.append("serialized program entrypoint count is inconsistent")

    entrypoints = list(deployment.entrypoints)
    entries_are_mappings = all(isinstance(entry, Mapping) for entry in entrypoints)
    phases = [entry.get("phase") for entry in entrypoints] if entries_are_mappings else []
    ids = [entry.get("entrypoint_id") for entry in entrypoints] if entries_are_mappings else []
    valid_entrypoint_identity = (
        len(entrypoints) == 2
        and entries_are_mappings
        and all(type(value) is int for value in phases + ids)
        and sorted(phases) == [0, 1]
        and sorted(ids) == [0, 1]
    )
    if not valid_entrypoint_identity:
        problems.append("serialized deployment lacks exact prefill/decode entrypoints")
    for entry in entrypoints if entries_are_mappings else ():
        policy_id = entry.get("generation_policy_id")
        if not _integer(policy_id) or policy_id >= len(deployment.table):
            problems.append("serialized entrypoint has an invalid generation policy")
            continue
        if (
            deployment.table[int(policy_id)].descriptor_type
            != int(ExtendedDescriptorType.GENERATION_POLICY)
        ):
            problems.append("serialized entrypoint does not name a generation policy")

    state_descriptors = deployment.table.ids_of_type(ExtendedDescriptorType.STATE)
    state_instructions = [
        instruction for instruction in instructions if instruction.major == int(Major.STATE)
    ]
    memory_objects = [
        descriptor
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
    ]
    state_storage = [
        descriptor
        for descriptor in memory_objects
        if int(descriptor.payload["storage_class"]) == int(StorageClass.STATE)
    ]
    state_permissions = [
        descriptor
        for descriptor in deployment.table.descriptors()
        if int(descriptor.permissions) & ABI_STATE_PERMISSIONS
    ]
    live_hbm = [
        descriptor
        for descriptor in memory_objects
        if int(descriptor.payload["storage_class"]) == int(StorageClass.HBM)
        and int(descriptor.permissions) & int(Permission.READ)
        and int(descriptor.permissions) & int(Permission.WRITE)
    ]
    if state_descriptors:
        problems.append("Qwen deployment contains an ABI STATE descriptor")
    if state_instructions:
        problems.append("Qwen deployment contains an ABI STATE instruction")
    if state_storage:
        problems.append("Qwen deployment contains a STATE storage object")
    if state_permissions:
        problems.append("Qwen deployment contains prepare/commit permissions")
    if not live_hbm:
        problems.append("Qwen deployment contains no ordinary read/write HBM buffer")

    try:
        independent = verify_deployment(deployment, capability)
    except (ValueError, KeyError, TypeError) as exc:
        return deployment, None, problems + [
            f"serialized deployment independent admission failed: {type(exc).__name__}: {exc}"
        ]
    if not independent.admitted:
        problems.append("serialized deployment fails independent admission")
    if independent.state_resources != 0:
        problems.append("independent admission found nonzero ABI STATE resources")
    producer_report = record.get("verification")
    if producer_report != independent.to_dict():
        problems.append("producer verification differs from independent readback admission")
    return deployment, independent, problems


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
    # The executed-association manifest is owned by the blocked GEMM backend.
    # The token record also carries identities for other functional helpers at
    # the top level.  Those helpers neither participate in, nor are emitted by,
    # the GEMM backend's association manifest.  Compare the exact backend-owned
    # projection while retaining the auxiliary identities elsewhere in the
    # independently authenticated record.
    expected_identity.pop("device_memory_bytes", None)
    expected_identity.pop("deepseek_ordered_product_add", None)
    if not expected_identity or "unavailable" in expected_identity:
        problems.append("implementation identity is unavailable")
    if manifest.get("implementation_identity") != expected_identity:
        problems.append("association implementation identity differs from record")
    return problems


def _oracle_input_identity(
    identity: object,
    expected_path: Path,
    expected_sha256: str,
    label: str,
) -> list[str]:
    if not isinstance(identity, dict):
        return [f"frozen natural oracle {label} identity is missing"]
    problems: list[str] = []
    if _resolved_record_path(identity.get("path")) != expected_path.resolve():
        problems.append(f"frozen natural oracle {label} path is not pinned")
    if identity.get("sha256") != expected_sha256:
        problems.append(f"frozen natural oracle {label} SHA-256 is not pinned")
    if not expected_path.is_file():
        problems.append(f"frozen natural oracle {label} source is unavailable")
    elif identity.get("size_bytes") != expected_path.stat().st_size:
        problems.append(f"frozen natural oracle {label} size is not pinned")
    return problems


def _check_natural_oracle_governance(oracle: Mapping[str, Any]) -> list[str]:
    """Require proof that Gate 1 authenticated inputs before model loading."""

    problems: list[str] = []
    if oracle.get("snapshot") != str(QWEN_SNAPSHOT):
        problems.append("frozen natural oracle snapshot is not the pinned release")

    producer = oracle.get("producer")
    if not isinstance(producer, dict):
        problems.append("frozen natural oracle producer record is missing")
    else:
        if producer.get("tool") != ORACLE_TOOL:
            problems.append("frozen natural oracle producer tool differs")
        if producer.get("tool_version") != ORACLE_TOOL_VERSION:
            problems.append("frozen natural oracle producer version differs")
        if producer.get("selected_workload_ids") != [NATURAL.workload_id]:
            problems.append("frozen natural oracle selection is not exact Gate 1")
        argv = producer.get("command_argv")
        if (
            not isinstance(argv, list)
            or not all(isinstance(item, str) for item in argv)
            or "--gate-1-production" not in argv
        ):
            problems.append("frozen natural oracle command did not request Gate 1")

    inputs = oracle.get("input_identity")
    if not isinstance(inputs, dict):
        problems.append("frozen natural oracle input identity is missing")
    else:
        problems += _oracle_input_identity(
            inputs.get("workload_index"),
            NATURAL_WORKLOAD_INDEX,
            NATURAL_WORKLOAD_INDEX_SHA256,
            "workload index",
        )
        workload_sources = inputs.get("workload_sources")
        workload_source = (
            workload_sources.get(NATURAL.workload_id)
            if isinstance(workload_sources, dict)
            else None
        )
        if not isinstance(workload_sources, dict) or set(workload_sources) != {
            NATURAL.workload_id
        }:
            problems.append("frozen natural oracle workload source set differs")
        problems += _oracle_input_identity(
            workload_source,
            NATURAL_WORKLOAD,
            NATURAL_WORKLOAD_SHA256,
            "workload",
        )
        problems += _oracle_input_identity(
            inputs.get("exact_8k_construction"),
            NATURAL_CONSTRUCTION,
            NATURAL_CONSTRUCTION_SHA256,
            "construction",
        )
        problems += _oracle_input_identity(
            inputs.get("checkpoint_lock"),
            QWEN_CHECKPOINT_LOCK,
            QWEN_CHECKPOINT_LOCK_SHA256,
            "checkpoint lock",
        )

    preflight = oracle.get("production_checkpoint_preflight")
    if not isinstance(preflight, dict):
        problems.append("frozen natural oracle checkpoint preflight is missing")
    else:
        expected = {
            "completed_before_model_framework_import": True,
            "full_byte_hash_verified": True,
            "lock_id": QWEN_CHECKPOINT_LOCK_ID,
            "lock_source_sha256": QWEN_CHECKPOINT_LOCK_SHA256,
            "payload_bytes": 16_381_470_720,
            "shard_count": 5,
            "tensor_count": 399,
        }
        if preflight != expected:
            problems.append("frozen natural oracle checkpoint preflight differs")

    production = oracle.get("production_launch")
    contract = production.get("contract") if isinstance(production, dict) else None
    expected_contract = {
        "schema": GATE_1_LAUNCH_SCHEMA,
        "profile_id": GATE_1_PROFILE_ID,
        "workload_id": NATURAL.workload_id,
        "prompt_token_count": NATURAL.prompt_count,
        "max_new_tokens": NATURAL.cap,
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
    }
    if (
        not isinstance(production, dict)
        or production.get("explicitly_requested") is not True
        or contract != expected_contract
    ):
        problems.append("frozen natural oracle production launch contract differs")
    return problems


def _frozen_inputs(spec: WorkloadSpec) -> tuple[dict[str, Any], dict[str, Any], list[int], list[int], list[str]]:
    problems: list[str] = []
    workload = _load(spec.workload_path)
    if spec is NATURAL:
        try:
            construction = load_construction(NATURAL_CONSTRUCTION)
            chat = QwenChatTokenizer(
                QWEN_SNAPSHOT, load_strict_json(QWEN_CHECKPOINT_LOCK)
            )
            validate_materialized_workload(
                workload,
                AuthenticatedWorkloadTokenizer(chat),
                construction,
                construction_path=NATURAL_CONSTRUCTION,
            )
        except (OSError, QwenExact8KError, ValueError) as exc:
            problems.append(
                "frozen natural workload is not the canonical exact-8K "
                f"official-chat construction: {exc}"
            )
    try:
        oracle = _load(spec.oracle_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        oracle = {}
        problems.append(
            "external exact-8K oracle is pending or unavailable: "
            f"{type(exc).__name__}: {exc}"
        )
    prompt = workload.get("token_ids")
    if not isinstance(prompt, list) or not all(_integer(token) for token in prompt):
        prompt = []
        problems.append("frozen workload has an invalid prompt token list")
    if workload.get("workload_id") != spec.workload_id or workload.get("digest") != spec.workload_digest:
        problems.append("frozen workload id/digest differs from the W10 contract")
    if len(prompt) != spec.prompt_count or workload.get("max_new_tokens") != spec.cap:
        problems.append("frozen workload length/budget differs from the W10 contract")
    rendered = workload.get("rendered_text")
    if not isinstance(rendered, str) or not rendered:
        problems.append("frozen workload has no rendered input text")
    elif hashlib.sha256(rendered.encode("utf-8")).hexdigest() != workload.get(
        "rendered_text_sha256"
    ):
        problems.append("frozen workload rendered input text digest is invalid")
    if spec.repeated_token is not None and prompt != [spec.repeated_token] * spec.prompt_count:
        problems.append("frozen stress prompt is not 8,000 copies of token 151644")
    if oracle.get("schema") != "opentallas.abi3.reference_oracle.v1" or oracle.get("model_id") != "qwen3-8b":
        problems.append("frozen oracle has the wrong schema/model")
    if oracle.get("tokenizer_sha256") != TOKENIZER_SHA256:
        problems.append("frozen oracle tokenizer is not the pinned tokenizer")
    if spec is NATURAL:
        problems += _check_natural_oracle_governance(oracle)
    result = (oracle.get("results") or {}).get(spec.workload_id, {})
    if not isinstance(result, dict):
        result = {}
    problems += _check_prefill_association(oracle, result, spec)
    gold = result.get("generated_token_ids") if isinstance(result, dict) else None
    if not isinstance(gold, list) or not all(
        _integer(token) and token < EXPLICIT_VOCABULARY_SIZE for token in gold
    ):
        gold = []
        problems.append("frozen oracle has no legal explicit-vocabulary gold sequence")
    if result.get("workload_digest") != spec.workload_digest:
        problems.append("frozen oracle workload digest differs from W10")
    if result.get("kind") != workload.get("kind"):
        problems.append("frozen oracle workload kind differs from W10")
    if result.get("prompt_token_count") != spec.prompt_count:
        problems.append("frozen oracle prompt token count differs from W10")
    if result.get("generated_token_count") != len(gold):
        problems.append("frozen oracle generated token count is inconsistent")
    if spec is STRESS and (len(gold) != spec.cap or result.get("stop_reason") != "max_new_tokens"):
        problems.append("frozen stress oracle is not the exact 32-token cap sequence")
    return workload, result, list(prompt), list(gold), problems


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _check_token_text(
    record: Mapping[str, Any],
    spec: WorkloadSpec,
    workload: Mapping[str, Any],
    oracle_result: Mapping[str, Any],
    prompt: Sequence[int],
    generated: Sequence[int],
) -> tuple[dict[str, Any], list[str]]:
    """Decode token IDs independently and publish human-auditable text.

    The functional simulator returns IDs, which is the architectural output.
    This independent pass uses the checkpoint's hash-pinned tokenizer to prove
    those IDs are also a legitimate continuation of the exact displayed input.
    No decoded string is fed back into execution.
    """

    problems: list[str] = []
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    checkpoint = (
        inputs.get("checkpoint_root")
        if isinstance(inputs.get("checkpoint_root"), dict)
        else {}
    )
    root = _resolved_record_path(checkpoint.get("path"))
    tokenizer_path = root / "tokenizer.json" if root is not None else None
    evidence: dict[str, Any] = {
        "tokenizer": {
            "path": _relative(tokenizer_path) if tokenizer_path is not None else None,
            "sha256": None,
            "library": "tokenizers",
            "library_version": None,
        }
    }
    if tokenizer_path is None or not tokenizer_path.is_file():
        return evidence, ["checkpoint tokenizer.json is unavailable"]
    actual_hash = _sha256(tokenizer_path)
    evidence["tokenizer"]["sha256"] = actual_hash
    if actual_hash != TOKENIZER_SHA256:
        problems.append("checkpoint tokenizer.json is not the pinned Qwen tokenizer")

    try:
        library_version = importlib.metadata.version("tokenizers")
    except importlib.metadata.PackageNotFoundError:
        return evidence, problems + ["pinned tokenizers library is unavailable"]
    evidence["tokenizer"]["library_version"] = library_version
    if library_version != TOKENIZERS_VERSION:
        problems.append(
            f"tokenizers library is {library_version}, expected {TOKENIZERS_VERSION}"
        )
    try:
        from tokenizers import Tokenizer

        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        prompt_text = tokenizer.decode(list(prompt), skip_special_tokens=False)
        raw_output = tokenizer.decode(list(generated), skip_special_tokens=False)
        visible_output = tokenizer.decode(list(generated), skip_special_tokens=True)
        prompt_round_trip = tokenizer.encode(
            str(workload.get("rendered_text", "")), add_special_tokens=False
        ).ids
        output_round_trip = tokenizer.encode(
            raw_output, add_special_tokens=False
        ).ids
    except (OSError, TypeError, ValueError) as exc:
        return evidence, problems + [
            f"checkpoint tokenizer cannot decode W10 tokens: {type(exc).__name__}: {exc}"
        ]

    rendered = workload.get("rendered_text")
    if prompt_text != rendered:
        problems.append("decoded prompt does not equal the frozen rendered input text")
    if list(prompt_round_trip) != list(prompt):
        problems.append("rendered input text does not round-trip to the frozen prompt IDs")
    if raw_output != oracle_result.get("raw_decoded_text"):
        problems.append("decoded raw output does not equal the frozen oracle text")
    if visible_output != oracle_result.get("visible_decoded_text"):
        problems.append("decoded visible output does not equal the frozen oracle text")
    if spec is NATURAL and list(output_round_trip) != list(generated):
        problems.append("natural decoded output does not round-trip to generated IDs")
    if spec is NATURAL and visible_output.strip() != EXPECTED_VISIBLE_ANSWER:
        problems.append(
            "natural decoded output does not answer the canonical arithmetic "
            f"query with {EXPECTED_VISIBLE_ANSWER!r}"
        )
    if not visible_output.strip():
        problems.append("decoded visible output is empty or whitespace-only")
    if "\ufffd" in raw_output or "\ufffd" in visible_output:
        problems.append("decoded output contains a Unicode replacement character")

    evidence.update(
        {
            "input": {
                "token_count": len(prompt),
                "token_ids_sha256": digest_of(list(prompt)),
                "rendered_text": prompt_text,
                "rendered_text_sha256": _text_sha256(prompt_text),
                "decode_matches_frozen_text": prompt_text == rendered,
                "encode_round_trip_matches_ids": list(prompt_round_trip)
                == list(prompt),
            },
            "output": {
                "token_count": len(generated),
                "token_ids_sha256": digest_of(list(generated)),
                "raw_decoded_text": raw_output,
                "raw_decoded_text_sha256": _text_sha256(raw_output),
                "visible_decoded_text": visible_output,
                "visible_decoded_text_sha256": _text_sha256(visible_output),
                "raw_matches_frozen_oracle": raw_output
                == oracle_result.get("raw_decoded_text"),
                "visible_matches_frozen_oracle": visible_output
                == oracle_result.get("visible_decoded_text"),
                "encode_round_trip_matches_ids": (
                    list(output_round_trip) == list(generated)
                    if spec is NATURAL
                    else "not_required_for_stress"
                ),
            },
        }
    )
    return evidence, problems


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
    if report.get("state_resources") != 0:
        problems.append("Qwen admission reports nonzero ABI STATE resources")
    return problems


def _check_steps_and_counters(
    record: Mapping[str, Any], generated: Sequence[int], terminal: str
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
        "instructions.retired": retired,
    }
    for name, expected in required.items():
        if counters.get(name) != expected:
            problems.append(f"counter {name} is {counters.get(name)!r}, expected {expected}")
    if counters.get("selection.invalid_tokens", 0) != 0:
        problems.append("selection.invalid_tokens is nonzero")
    for name in (
        "instructions.issued",
        "dma.scatter_elements",
        "attention.kv_bytes_read",
        "hbm.bytes_written",
    ):
        if not _integer(counters.get(name), minimum=1):
            problems.append(f"counter {name} is missing or not positive")
    for name, value in counters.items():
        if (name.startswith("state.") or name == "engine.state.descriptors") and value != 0:
            problems.append(
                f"counter {name} is nonzero in the ordinary live-buffer design"
            )
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


def _host_functional_performance(
    record: Mapping[str, Any], generated: Sequence[int]
) -> tuple[dict[str, Any], list[str]]:
    """Summarise measured host execution speed without implying RTL speed."""

    problems: list[str] = []
    wall = record.get("wall_seconds")
    steps = record.get("per_step")
    valid_wall = (
        isinstance(wall, (int, float)) and not isinstance(wall, bool) and wall > 0
    )
    if not valid_wall:
        problems.append("host functional-simulator wall_seconds is missing or invalid")
        wall = 0.0
    step_walls: list[float] = []
    if isinstance(steps, list):
        for index, step in enumerate(steps):
            value = step.get("wall_seconds") if isinstance(step, dict) else None
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or value <= 0
            ):
                problems.append(f"per_step[{index}] host wall_seconds is invalid")
            else:
                step_walls.append(float(value))
    first = step_walls[0] if len(step_walls) == len(generated) and step_walls else 0.0
    decode_walls = step_walls[1:] if len(step_walls) == len(generated) else []
    decode_wall = sum(decode_walls)
    return {
        "measurement_class": "host_functional_simulator_observation",
        "not_rtl_or_hardware_performance": True,
        "wall_seconds": float(wall),
        "prompt_plus_first_token_seconds": first,
        "generated_token_count": len(generated),
        "generated_tokens_per_wall_second": (
            len(generated) / float(wall) if valid_wall else None
        ),
        "post_prefill_decode_token_count": max(len(generated) - 1, 0),
        "post_prefill_decode_seconds": decode_wall,
        "post_prefill_decode_tokens_per_second": (
            len(decode_walls) / decode_wall if decode_wall > 0 else None
        ),
    }, problems


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
    inputs = record.get("inputs") if isinstance(record.get("inputs"), dict) else {}
    checkpoint = (
        inputs.get("checkpoint_root")
        if isinstance(inputs.get("checkpoint_root"), dict)
        else {}
    )
    if (
        not isinstance(model, dict)
        or _resolved_record_path(model.get("checkpoint_root"))
        != _resolved_record_path(checkpoint.get("path"))
    ):
        problems.append("model checkpoint root differs from the loaded input boundary")
    generated = record.get("generated_token_ids")
    if not isinstance(generated, list) or not generated or not all(
        _integer(token) and token < EXPLICIT_VOCABULARY_SIZE
        for token in generated
    ):
        generated = []
        problems.append("generated token sequence is empty or illegitimate")
    if record.get("generated_token_count") != len(generated):
        problems.append("generated_token_count is inconsistent")
    if generated != list(gold):
        problems.append("generated tokens are not exactly the frozen oracle sequence")
    if record.get("failure") is not None or record.get("token_legitimacy_problems") != []:
        problems.append("record carries a failure or legitimacy problem")
    oracle = record.get("oracle")
    oracle_sha256 = (
        _sha256(spec.oracle_path) if spec.oracle_path.is_file() else None
    )
    if not isinstance(oracle, dict) or oracle.get("artifact_sha256") != oracle_sha256 or _resolved_record_path(oracle.get("artifact")) != spec.oracle_path.resolve() or oracle.get("evidence_class") != "external_reference_comparator" or oracle.get("generated_token_ids") != list(gold) or oracle.get("agreement") is not True or oracle.get("first_divergence_index") is not None or oracle.get("compared_tokens") != len(generated) or oracle.get("oracle_token_count") != len(gold):
        problems.append("oracle evidence is not exact and source-current")
    terminal, terminal_problems = _terminal_kind(record, spec, generated, gold, oracle_result)
    problems += terminal_problems
    problems += _check_verification(record)
    problems += _check_inputs(record, spec, expected_backend, prompt_digest)
    _deployment, _independent_report, deployment_problems = (
        _check_published_deployment(
            record, expected_backend, capability, graph
        )
    )
    problems += deployment_problems
    problems += _check_source_lock(record, expected_backend)
    problems += _check_association(record)
    problems += _check_steps_and_counters(
        record, generated, terminal or "invalid"
    )
    text_evidence, text_problems = _check_token_text(
        record, spec, workload, oracle_result, prompt, generated
    )
    problems += text_problems
    performance, performance_problems = _host_functional_performance(
        record, generated
    )
    problems += performance_problems
    return {
        "path": _relative(path),
        "sha256": _sha256(path),
        "backend": expected_backend,
        "generated_token_ids": generated,
        "terminal_kind": terminal,
        "association_manifest_sha256": (record.get("executed_association") or {}).get("manifest_sha256"),
        "text_evidence": text_evidence,
        "host_functional_simulator": performance,
        "record": record,
        "problems": problems,
        "passes": not problems,
    }


def _without_timing(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_timing(item)
            for key, item in value.items()
            if key
            not in {"wall_seconds", "lowering_seconds", "completion_timestamp"}
        }
    if isinstance(value, list):
        return [_without_timing(item) for item in value]
    return value


def _non_storage(counters: Mapping[str, Any]) -> dict[str, Any]:
    return {name: value for name, value in counters.items() if not name.startswith(("hbm.", "rom.", "sram."))}


def validate(mode: str, paths: Sequence[Path]) -> dict[str, Any]:
    spec = NATURAL if mode == "natural" else STRESS
    workload, oracle_result, prompt, gold, problems = _frozen_inputs(spec)
    required_records = 3 if mode == "natural" else 2
    if len(paths) != required_records:
        problems.append(
            f"{mode} acceptance requires exactly {required_records} records"
        )
        rows: list[dict[str, Any]] = []
    else:
        backends = (
            ["hbm_sram", "hbm_sram", "rom_qwen3"]
            if mode == "natural"
            else ["hbm_sram", "rom_qwen3"]
        )
        rows = [_check_record(path, spec, backend, workload, oracle_result, prompt, gold) for path, backend in zip(paths, backends)]
        for row in rows:
            problems.extend(f"{Path(row['path']).name}: {problem}" for problem in row["problems"])
    pair_checks: dict[str, bool] = {}
    if len(rows) == required_records:
        records = [row["record"] for row in rows]
        left, right = records[0], records[1]
        all_associations = [record.get("executed_association") for record in records]
        all_implementations = [record.get("implementation_identity") for record in records]
        all_text = [row["text_evidence"] for row in rows]
        all_sequences = [row["generated_token_ids"] for row in rows]
        all_steps = [_without_timing(record.get("per_step")) for record in records]
        counters_match = (
            left.get("counters") == right.get("counters")
            and all(
                _non_storage(record.get("counters") or {})
                == _non_storage(left.get("counters") or {})
                for record in records[1:]
            )
            if mode == "natural"
            else _non_storage(left.get("counters") or {})
            == _non_storage(right.get("counters") or {})
        )
        pair_checks = {
            # A repeatability gate needs two independently materialised
            # captures.  Without these checks, passing the same path twice (or
            # copying one JSON byte-for-byte under a second name) satisfies
            # every semantic comparison below while providing no repeat-run
            # evidence at all.  Distinct digests are expected because the
            # producer records observed wall times for the run and each step;
            # those timing fields are deliberately removed only from the
            # architectural equality comparison.
            "capture_paths_distinct": len({path.resolve() for path in paths})
            == required_records,
            "capture_artifacts_distinct": len({row["sha256"] for row in rows})
            == required_records,
            "full_token_sequences_identical": all(
                sequence == list(gold) for sequence in all_sequences
            ),
            "decoded_text_evidence_identical": all(
                evidence == all_text[0] for evidence in all_text[1:]
            ),
            "executed_association_manifests_identical": all(
                association == all_associations[0]
                for association in all_associations[1:]
            ),
            "implementation_identities_identical": all(
                identity == all_implementations[0]
                for identity in all_implementations[1:]
            ),
            "architectural_counters_identical": counters_match,
            "per_step_architecture_identical": all(
                steps == all_steps[0] for steps in all_steps[1:]
            ),
        }
        for name, passed in pair_checks.items():
            if not passed:
                problems.append(f"pair check failed: {name}")
    accepted = not problems
    document = {
        "schema": SCHEMA,
        "status": "pass" if accepted else "fail",
        "mode": mode,
        "workload_id": spec.workload_id,
        "association_pair_policy": PAIR_POLICY,
        "records": [{key: row[key] for key in ("path", "sha256", "backend", "terminal_kind", "association_manifest_sha256", "passes", "problems")} for row in rows],
        "pair_checks": pair_checks,
        "abi_profile": {
            "version": "3.0",
            "execution_state": "ordinary_live_hbm_sram_buffers",
            "abi_state_descriptors": 0,
            "abi_state_instructions": 0,
            "durable_journal_or_rollback": False,
            "run_failure_model": "uninterrupted_fail_stop",
        },
        "text_evidence": rows[0]["text_evidence"] if rows else {},
        "host_functional_simulator": [
            {
                "record": row["path"],
                **row["host_functional_simulator"],
            }
            for row in rows
        ],
        "problems": problems,
        "claim_boundary": {
            "acceptance_established": accepted,
            "required_execution_scope": (
                "full_causal_model_execution_from_serialized_abi3_artifacts"
            ),
            "oracle_token_injection": False,
            "host_functional_timing_reported": True,
            "cycle_accurate_rtl_timing_or_hardware_performance": False,
            "rtl_or_silicon_correctness": False,
        },
    }
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("natural", "stress"))
    parser.add_argument(
        "records",
        type=Path,
        nargs="+",
        metavar="RECORD",
        help="natural: HBM run 1/run 2/ROM; stress: HBM/ROM",
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
