#!/usr/bin/env python3
"""Run a source-bound, closed-loop ABI 3 agent episode.

The model, not this harness, supplies every command.  Each generated turn is
compared exactly with an external oracle turn, parsed fail-closed, executed in
the repository's frozen :class:`runtime.agent.Sandbox`, and rendered back into
the next prompt with the model's official protocol.  A fresh accelerator
session evaluates every fully rendered turn.

This is functional-artifact evidence only.  It is not RTL, cycle, physical,
timing, power, or silicon execution evidence.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import time
from typing import Any, Protocol

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


# The blocked contraction implementation is part of the execution identity.
# Establish the same deterministic default as the governed token runner before
# importing any runtime module that may import NumPy.
for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_variable, "8")

REPO = Path(__file__).resolve().parents[1]
OUTPUT_SCHEMA_PATH = REPO / "schemas/runtime/abi3_agent_episode_v3.schema.json"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import (  # noqa: E402
    Capability,
    canonical_json,
    digest_of,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.agent import (  # noqa: E402
    AgentProtocolError,
    CommandResult,
    Sandbox,
    parse_turn,
    render_agent_context,
    split_thinking,
)
from runtime.driver import DriverError, GenerationDriver, validate_token_ids  # noqa: E402
from runtime.evidence import check_token_legitimacy  # noqa: E402
from runtime.sim.backend import get_backend  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402


SCHEMA = "opentallas.abi3.agent_episode.v3"
ORACLE_SCHEMA = "opentallas.abi3.reference_oracle.v1"
EVIDENCE_CLASS = "functional_artifact_only"
COMMAND_POLICY_ID = "inventory_read_only_shell_v1"
NOT_A_CLAIMS = (
    "rtl_execution",
    "cycle_execution",
    "physical_execution",
    "timing_or_performance",
    "power_or_energy",
    "silicon_execution",
    "general_shell_or_os_network_isolation",
)

BACKENDS = {
    "hbm_sram": "compiler.backends.hbm_sram.lower:lower_to_abi3",
    "rom_qwen3": "compiler.backends.rom.qwen3:lower_to_abi3",
    "rom_deepseek_v4": "compiler.backends.rom.deepseek_v4:lower_to_abi3",
}

MODEL_BACKENDS = {
    "qwen3-8b": frozenset({"hbm_sram", "rom_qwen3"}),
    "deepseek-v4-flash-0731": frozenset({"hbm_sram", "rom_deepseek_v4"}),
}

QWEN_CHECKPOINT_FILES = (
    (
        "config.json",
        728,
        "f7c4eadfbbf522470667b797a3c89be2524832d2d599797248dc304fff447c30",
    ),
    (
        "generation_config.json",
        239,
        "2325da0f15bb848e018c5ae071b7943332e9f871d6b60e2ed22ca97d4cb993d2",
    ),
    (
        "model.safetensors.index.json",
        32878,
        "f9fdbcb91c23971c13ec5d5f2573d2349e8f61f2f049371ec699281748fdb1bc",
    ),
    (
        "tokenizer.json",
        11422654,
        "aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
    ),
    (
        "tokenizer_config.json",
        9732,
        "d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101",
    ),
)

DEEPSEEK_CHECKPOINT_FILES = (
    (
        "config.json",
        1888,
        "6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023",
    ),
    (
        "generation_config.json",
        170,
        "5fccff80f55a4d455bbe516bdd552edf3e9623df95e99fbf2a3c3389fdf91af0",
    ),
    (
        "model.safetensors.index.json",
        5602871,
        "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b",
    ),
    (
        "tokenizer.json",
        6367146,
        "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf",
    ),
    (
        "tokenizer_config.json",
        801,
        "6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547",
    ),
)


@dataclass(frozen=True)
class TargetProfile:
    """Independently anchored identity and topology for one supported lane."""

    profile_id: str
    model_id: str
    backend: str
    graph_id: str
    kernel_ir_sha256: str
    numeric_profile: str
    capability_sha256: str
    topology_class: int
    node_count: int
    deployment_backend: str
    target_id: str
    workload_id: str
    workload_digest: str
    workload_sha256: str
    expected_total: int
    workload_index_schema: str
    workload_index_sha256: str
    tokenizer_sha256: str
    vocabulary_size: int
    eos_token_ids: tuple[int, ...]
    oracle_sha256: str | None
    checkpoint_source_sha256: str
    checkpoint_files: tuple[tuple[str, int, str], ...]


# These are acceptance identities, not values learned from the input files at
# run time.  A same-model graph or a more permissive capability is a different
# target and is refused even when it is internally self-consistent.  Caller
# expectations must equal these locks as well as the selected files.  A lane
# whose oracle identity is ``None`` remains deliberately unpublished.
TARGET_PROFILES: dict[tuple[str, str], TargetProfile] = {
    ("qwen3-8b", "hbm_sram"): TargetProfile(
        profile_id="qwen3_8b_hbm_single_chip_agent_v1",
        model_id="qwen3-8b",
        backend="hbm_sram",
        graph_id="84bb97dd1243553f170fde014c15c76c6adf0b80f0ef3bdad27a015577b6c24b",
        kernel_ir_sha256="62499454381d24641f8cedda00f049aff61b4aa96410fa3fe460e0044df567e6",
        numeric_profile="qwen3_bf16_gqa_target_v1",
        capability_sha256="fa70dd44a1b532a99d103968b31b743bbed324d002fbe0214c9541fb1687e23d",
        topology_class=0,
        node_count=1,
        deployment_backend="hbm-sram-abi3",
        target_id="hbm-sram-abi3-single_chip",
        workload_id="TA-QW-AGENT-2",
        workload_digest="e4c424a64f88dbe17f3f9eec08e02db8ac449ef5f25ef424d854ac788b3c2b0c",
        workload_sha256="388907a0b690af1b6bac00664731570f967eb4d00eff977646fdd68de5be87d0",
        expected_total=239,
        workload_index_schema="opentallas.abi3.workload_index.v1",
        workload_index_sha256="ffd0c0f52c6d96f172ad5318f157eddd352907e35bc46bee01e098d1b98ec065",
        tokenizer_sha256="aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
        vocabulary_size=151936,
        eos_token_ids=(151645, 151643),
        oracle_sha256="70de9a208e80cfcdf96d2d2f1267da2ea03d036ec43550f9392f727f1a38de82",
        checkpoint_source_sha256="5cd6273118054c4a9140682bcd7a32488d8697db26bedf5d7ece8de99e141607",
        checkpoint_files=QWEN_CHECKPOINT_FILES,
    ),
    ("qwen3-8b", "rom_qwen3"): TargetProfile(
        profile_id="qwen3_8b_rom_single_chip_agent_v1",
        model_id="qwen3-8b",
        backend="rom_qwen3",
        graph_id="84bb97dd1243553f170fde014c15c76c6adf0b80f0ef3bdad27a015577b6c24b",
        kernel_ir_sha256="62499454381d24641f8cedda00f049aff61b4aa96410fa3fe460e0044df567e6",
        numeric_profile="qwen3_bf16_gqa_target_v1",
        capability_sha256="5b5770fa766cd89d7a236a62722ef33d1db9f87be7403a8f8c55fc9ec8c8458e",
        topology_class=0,
        node_count=1,
        deployment_backend="rom.single_chip",
        target_id="qwen3-8b-rom-single-chip",
        workload_id="TA-QW-AGENT-2",
        workload_digest="e4c424a64f88dbe17f3f9eec08e02db8ac449ef5f25ef424d854ac788b3c2b0c",
        workload_sha256="388907a0b690af1b6bac00664731570f967eb4d00eff977646fdd68de5be87d0",
        expected_total=239,
        workload_index_schema="opentallas.abi3.workload_index.v1",
        workload_index_sha256="ffd0c0f52c6d96f172ad5318f157eddd352907e35bc46bee01e098d1b98ec065",
        tokenizer_sha256="aeb13307a71acd8fe81861d94ad54ab689df773318809eed3cbe794b4492dae4",
        vocabulary_size=151936,
        eos_token_ids=(151645, 151643),
        oracle_sha256="70de9a208e80cfcdf96d2d2f1267da2ea03d036ec43550f9392f727f1a38de82",
        checkpoint_source_sha256="5cd6273118054c4a9140682bcd7a32488d8697db26bedf5d7ece8de99e141607",
        checkpoint_files=QWEN_CHECKPOINT_FILES,
    ),
    ("deepseek-v4-flash-0731", "hbm_sram"): TargetProfile(
        profile_id="deepseek_v4_flash_hbm_cluster_32_agent_v1",
        model_id="deepseek-v4-flash-0731",
        backend="hbm_sram",
        graph_id="9ef6c3248d23c181c774fd43c09b0de2a19c8e23f344cb9a25c43040268337d9",
        kernel_ir_sha256="e101b3e7a63e73f7dd66b3d6c15c40d0b7b6eba7cdc387ddc5cd9623c0e0ccf1",
        numeric_profile="deepseek_v4_flash_target_precision_v1",
        capability_sha256="1eb2e92dac1d9fb8937b7724953d2f65993bd56e342e9058569442eb61d74bad",
        topology_class=1,
        node_count=32,
        deployment_backend="hbm-sram-abi3",
        target_id="hbm-sram-abi3-cluster_32",
        workload_id="TA-DS-AGENT-1",
        workload_digest="0044a2560aae31da30b6540eb1b32d76f8c321e2adddb7212c1e954a728080c9",
        workload_sha256="a38f1df67253d121eeec84bcc115c94f1cfaff6a054d2131609682f855aeb8f1",
        expected_total=239,
        workload_index_schema="opentallas.workload_index.v1",
        workload_index_sha256="45f478d457d0e617d1ef06e6f5a5b542bc567bd911be28072fa10ec6c625d310",
        tokenizer_sha256="8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf",
        vocabulary_size=129280,
        eos_token_ids=(1,),
        oracle_sha256=None,
        checkpoint_source_sha256="c9cf820d5183a4de2fdd51769535b48d6a47975a6d707f5d1b2f105af64141c5",
        checkpoint_files=DEEPSEEK_CHECKPOINT_FILES,
    ),
    ("deepseek-v4-flash-0731", "rom_deepseek_v4"): TargetProfile(
        profile_id="deepseek_v4_flash_rom_wafer_agent_v1",
        model_id="deepseek-v4-flash-0731",
        backend="rom_deepseek_v4",
        graph_id="9ef6c3248d23c181c774fd43c09b0de2a19c8e23f344cb9a25c43040268337d9",
        kernel_ir_sha256="e101b3e7a63e73f7dd66b3d6c15c40d0b7b6eba7cdc387ddc5cd9623c0e0ccf1",
        numeric_profile="deepseek_v4_flash_target_precision_v1",
        capability_sha256="5abf26b4ef235d6083c6f6dbe48d7021068c59ecb451238569a2f660303d26b6",
        topology_class=2,
        node_count=1,
        deployment_backend="rom.wafer_logical_device",
        target_id="deepseek-v4-flash-rom-wafer",
        workload_id="TA-DS-AGENT-1",
        workload_digest="0044a2560aae31da30b6540eb1b32d76f8c321e2adddb7212c1e954a728080c9",
        workload_sha256="a38f1df67253d121eeec84bcc115c94f1cfaff6a054d2131609682f855aeb8f1",
        expected_total=239,
        workload_index_schema="opentallas.workload_index.v1",
        workload_index_sha256="45f478d457d0e617d1ef06e6f5a5b542bc567bd911be28072fa10ec6c625d310",
        tokenizer_sha256="8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf",
        vocabulary_size=129280,
        eos_token_ids=(1,),
        oracle_sha256=None,
        checkpoint_source_sha256="c9cf820d5183a4de2fdd51769535b48d6a47975a6d707f5d1b2f105af64141c5",
        checkpoint_files=DEEPSEEK_CHECKPOINT_FILES,
    ),
}

FUNCTIONAL_SOURCE_PATHS = (
    "schemas/runtime/abi3_agent_episode_v3.schema.json",
    "compiler/__init__.py",
    "compiler/ir/__init__.py",
    "compiler/ir/model.py",
    "compiler/ir/v3/__init__.py",
    "compiler/backends/numeric_contracts.py",
    "compiler/ir/v3/kernel_ir.py",
    "compiler/ir/v3/lowering.py",
    "compiler/ir/v3/numeric.py",
    "runtime/abi3/builder.py",
    "runtime/abi3/__init__.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/layout.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "runtime/__init__.py",
    "runtime/agent.py",
    "runtime/driver.py",
    "runtime/evidence.py",
    "runtime/sim/backend.py",
    "runtime/sim/__init__.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/memory.py",
)

# Importing the engine registry executes every engine module.  Those modules
# enter the reference and tensor-accelerator packages through package
# ``__init__`` files which themselves import sibling implementations.  Lock
# the complete package boundaries rather than a hand-selected subset that can
# silently miss a newly imported numeric helper.
FUNCTIONAL_SOURCE_GLOBS = (
    "runtime/reference/*.py",
    "runtime/sim/engines/*.py",
    "runtime/tensor_accelerator/*.py",
)

BACKEND_SOURCE_PATHS = {
    "hbm_sram": (
        "compiler/backends/__init__.py",
        "compiler/backends/hbm_sram/__init__.py",
        "compiler/backends/hbm_sram/capability.py",
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
    "rom_qwen3": (
        "compiler/backends/__init__.py",
        "compiler/backends/rom/__init__.py",
        "compiler/backends/rom/common/__init__.py",
        "compiler/backends/rom/qwen3.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
        "compiler/qwen3/__init__.py",
        "compiler/qwen3/adapter.py",
        "compiler/qwen3/constants.py",
    ),
    "rom_deepseek_v4": (
        "compiler/backends/__init__.py",
        "compiler/backends/rom/__init__.py",
        "compiler/backends/rom/common/__init__.py",
        "compiler/backends/rom/deepseek_v4.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
}

MODEL_SOURCE_PATHS = {
    "qwen3-8b": (
        "compiler/workloads/__init__.py",
        "compiler/workloads/qwen3.py",
    ),
    "deepseek-v4-flash-0731": (
        "compiler/frontend/__init__.py",
        "compiler/workloads/__init__.py",
        "compiler/workloads/qwen3.py",
        "compiler/workloads/deepseek_v4.py",
    ),
}

MODEL_SOURCE_GLOBS = {
    "qwen3-8b": (),
    "deepseek-v4-flash-0731": ("compiler/frontend/*.py",),
}

BACKEND_SOURCE_GLOBS = {
    "hbm_sram": (),
    "rom_qwen3": ("compiler/frontend/*.py", "compiler/qwen3/*.py"),
    "rom_deepseek_v4": (),
}

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ANSWER_LINE = re.compile(r"ANSWER:[ \t]*(?P<answer>[^\r\n]*)\Z")
_QWEN_FENCE = re.compile(r"```bash[ \t]*\r?\n(?P<body>.*?)\r?\n?```", re.DOTALL)
_AWK_SUM = re.compile(
    r"\{[ \t]*(?P<name>sum|s|total)[ \t]*\+=[ \t]*\$2[ \t]*\}"
    r"[ \t]*END[ \t]*\{[ \t]*print[ \t]+(?P=name)[ \t]*\}"
)


class EpisodeRefusal(ValueError):
    """An input or generated turn does not satisfy the frozen contract."""


def validate_inventory_command(command: str) -> None:
    """Admit only network-inert reads or the pinned inventory sum operation.

    ``runtime.agent.Sandbox`` confines the working directory and environment,
    but does not create an operating-system network namespace.  This harness
    therefore never exposes its general ``bash -c`` surface: it accepts two
    exact argv shapes that name only the pinned relative input file.  The raw
    model string is still what the sandbox executes; this check neither writes
    nor repairs a command.
    """

    if not isinstance(command, str) or not command or command != command.strip():
        raise EpisodeRefusal("command is not one exact non-empty line")
    if any(not character.isprintable() for character in command):
        raise EpisodeRefusal("command contains a control character")
    try:
        arguments = shlex.split(command, posix=True)
    except ValueError as exc:
        raise EpisodeRefusal(f"command is not valid shell quoting: {exc}") from exc
    if arguments == ["cat", "inventory.txt"]:
        return
    if (
        len(arguments) == 4
        and arguments[0] == "awk"
        and arguments[1] == "-F,"
        and _AWK_SUM.fullmatch(arguments[2]) is not None
        and arguments[3] == "inventory.txt"
    ):
        return
    raise EpisodeRefusal(
        f"command is outside deterministic policy {COMMAND_POLICY_ID!r}"
    )


def command_policy_evidence() -> dict[str, Any]:
    """Describe the narrow command gate without claiming OS isolation."""

    return {
        "policy_id": COMMAND_POLICY_ID,
        "allowed_input": "inventory.txt",
        "os_network_namespace_isolation": False,
        "general_shell_access": False,
    }


def _integer(value: object, *, minimum: int = 0) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EpisodeRefusal(f"duplicate JSON member {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise EpisodeRefusal(f"non-finite JSON number {value!r}")


def load_json(path: Path) -> dict[str, Any]:
    """Load one strict UTF-8 JSON object, rejecting ambiguity."""

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EpisodeRefusal(f"cannot load strict JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise EpisodeRefusal(f"{path} must contain one JSON object")
    return value


def load_output_validator() -> Draft202012Validator:
    """Load and meta-validate the evidence schema before execution starts."""

    schema = load_json(OUTPUT_SCHEMA_PATH)
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise EpisodeRefusal("output schema does not declare JSON Schema Draft 2020-12")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise EpisodeRefusal(f"output JSON Schema is invalid: {exc.message}") from exc
    return Draft202012Validator(schema)


def _json_path(parts: Sequence[object]) -> str:
    path = "$"
    for part in parts:
        path += f"[{part}]" if isinstance(part, int) else f".{part}"
    return path


def validate_output_artifact(
    body: Mapping[str, Any],
    *,
    validator: Draft202012Validator | None = None,
    expected_source_sha256: Mapping[str, str] | None = None,
) -> None:
    """Validate the complete evidence shape and its cross-field bindings."""

    active_validator = validator if validator is not None else load_output_validator()
    schema_errors = sorted(
        active_validator.iter_errors(body),
        key=lambda error: tuple(str(part) for part in error.absolute_path),
    )
    if schema_errors:
        first = schema_errors[0]
        raise EpisodeRefusal(
            f"output schema violation at {_json_path(first.absolute_path)}: "
            f"{first.message}"
        )

    # The schema settles types, required members and closed object shapes.  The
    # remaining relations require values from two fields, exact source keys,
    # or a digest computation and therefore cannot be expressed in JSON Schema.
    problems: list[str] = []

    def equal(label: str, actual: object, expected: object) -> None:
        if actual != expected:
            problems.append(f"{label} is not bound to its source value")

    model = body["model"]
    backend = str(body["backend"])
    profile = select_target_profile(str(model["model_id"]), backend)
    target_profile = body["target_profile"]
    target = body["target"]
    workload = body["workload"]
    inputs = body["inputs"]
    reference = body["reference"]

    equal("target profile id", target_profile["profile_id"], profile.profile_id)
    equal(
        "target profile kernel identity",
        target_profile["expected_kernel_ir_sha256"],
        profile.kernel_ir_sha256,
    )
    equal(
        "target profile capability identity",
        target_profile["expected_capability_sha256"],
        profile.capability_sha256,
    )
    equal(
        "target profile oracle identity",
        target_profile["expected_reference_sha256"],
        profile.oracle_sha256,
    )
    equal("model graph id", model["graph_id"], profile.graph_id)
    equal("model numeric profile", model["numeric_profile"], profile.numeric_profile)
    equal("target id", target["target_id"], profile.target_id)
    equal("target backend", target["backend"], profile.deployment_backend)
    equal("target topology", target["topology_class"], profile.topology_class)
    equal("target node count", target["node_count"], profile.node_count)
    equal(
        "target capability digest",
        target["capability_digest"],
        profile.capability_sha256,
    )
    equal("target capability path", target["capability"], inputs["capability"]["path"])
    equal("workload id", workload["workload_id"], profile.workload_id)
    equal("workload digest", workload["workload_digest"], profile.workload_digest)
    equal("workload tokenizer", workload["tokenizer_sha256"], profile.tokenizer_sha256)
    equal("workload expected total", body["expected_total"], profile.expected_total)

    equal(
        "kernel input identity", inputs["kernel_ir"]["sha256"], profile.kernel_ir_sha256
    )
    equal(
        "capability input identity",
        inputs["capability"]["sha256"],
        profile.capability_sha256,
    )
    equal(
        "workload input identity", inputs["workload"]["sha256"], profile.workload_sha256
    )
    equal(
        "workload index input identity",
        inputs["workload_index"]["sha256"],
        profile.workload_index_sha256,
    )
    equal(
        "workload declared digest",
        inputs["workload"]["declared_workload_digest"],
        workload["workload_digest"],
    )
    equal(
        "workload token digest",
        inputs["workload"]["prompt_token_ids_sha256"],
        digest_of(workload["prompt_token_ids"]),
    )
    equal(
        "workload prompt count",
        workload["prompt_token_count"],
        len(workload["prompt_token_ids"]),
    )
    equal(
        "reference input identity",
        inputs["reference"]["sha256"],
        profile.oracle_sha256,
    )
    equal(
        "reference artifact identity",
        reference["artifact_sha256"],
        profile.oracle_sha256,
    )
    equal(
        "reference workload digest",
        reference["workload_digest"],
        profile.workload_digest,
    )
    equal("reference path", reference["artifact"], inputs["reference"]["path"])
    equal(
        "deployment digest binding",
        inputs["checkpoint_root"]["deployment_digest_binding"],
        target["deployment_digest"],
    )

    checkpoint_identity = inputs["checkpoint_root"]["identity"]
    equal(
        "checkpoint source identity",
        checkpoint_identity["source"]["sha256"],
        profile.checkpoint_source_sha256,
    )
    expected_checkpoint = {
        name: (size, digest) for name, size, digest in profile.checkpoint_files
    }
    for name, (expected_size, expected_digest) in expected_checkpoint.items():
        identity = checkpoint_identity["files"][name]
        equal(f"checkpoint {name} byte count", identity["bytes"], expected_size)
        equal(f"checkpoint {name} identity", identity["sha256"], expected_digest)
    for name in ("tokenizer.json", "tokenizer_config.json", "generation_config.json"):
        equal(
            f"loaded {name} identity",
            inputs["tokenizer_files"][name],
            checkpoint_identity["files"][name],
        )

    source_identity = (
        dict(expected_source_sha256)
        if expected_source_sha256 is not None
        else source_sha256(backend, str(model["model_id"]))
    )
    equal("functional source map", body["source_sha256"], source_identity)

    policy = body["generation_policy"]
    expected_policy_digest = digest_of(policy) if policy else ""
    equal(
        "generation policy digest",
        body["generation_policy_digest"],
        expected_policy_digest,
    )
    equal("command policy", body["command_policy"], command_policy_evidence())
    equal("claim boundary", tuple(body["not_a_claim"]), NOT_A_CLAIMS)
    if policy:
        equal(
            "generation vocabulary",
            policy["vocabulary_size"],
            profile.vocabulary_size,
        )
        equal("generation EOS count", policy["eos_count"], len(profile.eos_token_ids))
        for index, token in enumerate(profile.eos_token_ids):
            equal(f"generation EOS token {index}", policy[f"eos_token_{index}"], token)

    turns = body["turns"]
    equal("turn count", body["turn_count"], len(turns))
    if len(turns) > workload["max_turns"]:
        problems.append("turn count exceeds the workload turn bound")
    if body["oracle_agreement"]:
        equal("reference turn count", reference["oracle_turn_count"], len(turns))
    equal(
        "executed command count",
        body["executed_command_count"],
        sum(turn.get("outcome") == "executed" for turn in turns),
    )
    equal(
        "task-solved flag",
        body["task_solved"],
        body["answer"] == str(profile.expected_total),
    )
    equal(
        "counter-scope node count",
        body["counter_scope"]["node_count"],
        profile.node_count,
    )
    equal("final node-counter count", len(body["node_counters"]), profile.node_count)
    if turns:
        equal(
            "initial workload tokens",
            turns[0]["prompt_token_ids"],
            workload["prompt_token_ids"],
        )
        equal(
            "initial workload rendering",
            turns[0]["rendered_prompt_sha256"],
            workload["rendered_text_sha256"],
        )

    for index, turn in enumerate(turns):
        equal(f"turn {index} index", turn["turn"], index)
        equal(
            f"turn {index} prompt count",
            turn["prompt_token_count"],
            len(turn["prompt_token_ids"]),
        )
        equal(
            f"turn {index} rendered prompt identity",
            turn["rendered_prompt_sha256"],
            hashlib.sha256(turn["rendered_prompt_text"].encode("utf-8")).hexdigest(),
        )
        expected_limit = min(
            workload["max_new_tokens_per_turn"],
            workload["session_context_capacity"] - len(turn["prompt_token_ids"]),
        )
        equal(f"turn {index} generation limit", turn["max_new_tokens"], expected_limit)
        if "generated_token_ids" not in turn:
            continue
        equal(
            f"turn {index} generated count",
            turn["generated_token_count"],
            len(turn["generated_token_ids"]),
        )
        for name in (
            "node_counters_before",
            "node_counters_after",
            "node_counter_delta",
        ):
            equal(f"turn {index} {name} count", len(turn[name]), profile.node_count)
        observation = turn.get("observation")
        parsed = turn.get("parsed")
        if observation is not None and parsed is not None:
            equal(
                f"turn {index} observation command",
                observation["command"],
                parsed["command"],
            )
        if observation is not None and index + 1 < len(turns):
            rendered_observation = CommandResult(**observation).rendered()
            if rendered_observation not in turns[index + 1]["rendered_prompt_text"]:
                problems.append(
                    f"turn {index + 1} rendered prompt does not contain the real "
                    f"turn {index} observation"
                )

    coverage = body["engine_coverage"]
    equal("missing-engine count", coverage["missing_count"], len(coverage["missing"]))
    implementation = body["implementation_identity"]
    implementation_backend = implementation["backend"]
    expected_library = "numpy" if implementation_backend == "numpy" else "torch"
    equal("implementation library", implementation["library"], expected_library)
    required_implementation_fields = {
        "numpy": {"blas"},
        "torch_cpu": set(),
        "torch_cuda": {
            "compute_capability",
            "cuda_version",
            "device_memory_bytes",
        },
    }[implementation_backend]
    optional_implementation_fields = {
        "blas",
        "compute_capability",
        "cuda_version",
        "device_memory_bytes",
    }
    actual_implementation_fields = optional_implementation_fields & set(implementation)
    equal(
        "implementation backend-specific fields",
        actual_implementation_fields,
        required_implementation_fields,
    )
    association = body["executed_association"]
    equal(
        "association entry count",
        association["distinct_association_count"],
        len(association["entries"]),
    )
    equal(
        "association call count",
        association["blocked_call_count"],
        sum(entry["call_count"] for entry in association["entries"]),
    )
    association_identity = dict(body["implementation_identity"])
    association_identity.pop("device_memory_bytes", None)
    equal(
        "association implementation identity",
        association["implementation_identity"],
        association_identity,
    )
    unsigned_association = {
        key: value for key, value in association.items() if key != "manifest_sha256"
    }
    association_digest = hashlib.sha256(
        json.dumps(
            unsigned_association,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()
    equal(
        "association manifest identity",
        association["manifest_sha256"],
        association_digest,
    )

    if body["status"] == "pass":
        equal("pass stop reason", body["stop_reason"], "answered")
        equal("pass oracle agreement", body["oracle_agreement"], True)
        equal("pass task solved", body["task_solved"], True)
        equal("pass problems", body["problems"], [])
        if body["executed_command_count"] < 1:
            problems.append("pass has no executed command")
        if association["blocked_call_count"] < 1:
            problems.append("pass has no executed blocked association")
        if not turns:
            problems.append("pass has no turns")
        session_ids: list[int] = []
        for index, turn in enumerate(turns):
            session_id = turn.get("session_id")
            if session_id in session_ids:
                problems.append(f"pass turn {index} reuses an accelerator session")
            session_ids.append(session_id)
            equal(f"pass turn {index} failure", turn.get("failure"), None)
            equal(
                f"pass turn {index} token legitimacy",
                turn.get("token_legitimacy_problems"),
                [],
            )
            comparison = turn.get("oracle_comparison", {})
            for name in (
                "prompt_exact",
                "rendered_prompt_exact",
                "token_limit_exact",
                "generated_exact",
                "stop_reason_exact",
            ):
                equal(f"pass turn {index} oracle {name}", comparison.get(name), True)
            generated = turn.get("generated_token_ids", [])
            for problem in validate_token_ids(generated, profile.vocabulary_size):
                problems.append(f"pass turn {index}: {problem}")
            for problem in _terminal_problems(
                tokens=generated,
                stop_reason=str(turn.get("stop_reason")),
                limit=turn["max_new_tokens"],
                eos_token_ids=profile.eos_token_ids,
            ):
                problems.append(f"pass turn {index}: {problem}")
            steps = turn.get("per_step", [])
            equal(f"pass turn {index} per-step count", len(steps), len(generated))
            equal(
                f"pass turn {index} transactions", turn.get("transactions"), len(steps)
            )
            equal(
                f"pass turn {index} prefill count",
                turn.get("prefill_tokens"),
                len(turn["prompt_token_ids"]),
            )
            equal(
                f"pass turn {index} decode count",
                turn.get("decode_steps"),
                max(0, len(generated) - 1),
            )
            for step_index, (step, token) in enumerate(zip(steps, generated)):
                equal(f"pass turn {index} step index", step["step"], step_index)
                equal(
                    f"pass turn {index} step phase",
                    step["phase"],
                    "prefill" if step_index == 0 else "decode",
                )
                equal(f"pass turn {index} step status", step["status"], "SUCCESS")
                equal(f"pass turn {index} step trap", step["trap"], "NONE")
                equal(
                    f"pass turn {index} step produced token",
                    step["produced_tokens"],
                    [token],
                )
                equal(
                    f"pass turn {index} step final token",
                    step["final_token_id"],
                    token,
                )
            equal(
                f"pass turn {index} aggregate counter delta",
                turn.get("counter_delta"),
                _counter_delta(turn["counters_before"], turn["counters_after"]),
            )
            if len(turn["node_counters_before"]) == len(turn["node_counters_after"]):
                equal(
                    f"pass turn {index} node counter delta",
                    turn.get("node_counter_delta"),
                    _node_counter_deltas(
                        turn["node_counters_before"], turn["node_counters_after"]
                    ),
                )
        if turns:
            expected_outcomes = ["executed"] * (len(turns) - 1) + ["answered"]
            equal(
                "pass turn outcome sequence",
                [turn["outcome"] for turn in turns],
                expected_outcomes,
            )
            equal(
                "pass final parsed answer",
                turns[-1].get("parsed", {}).get("answer"),
                body["answer"],
            )
            equal("pass final counters", body["counters"], turns[-1]["counters_after"])
            equal(
                "pass final node counters",
                body["node_counters"],
                turns[-1]["node_counters_after"],
            )

    if problems:
        raise EpisodeRefusal(
            "output semantic validation failed: " + "; ".join(problems)
        )


def write_validated_output(
    body: Mapping[str, Any],
    *,
    output: Path,
    validator: Draft202012Validator,
    expected_source_sha256: Mapping[str, str],
) -> None:
    """Validate the complete artifact before creating or replacing its path."""

    validate_output_artifact(
        body,
        validator=validator,
        expected_source_sha256=expected_source_sha256,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(body))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO).as_posix()
    except ValueError:
        return str(resolved)


def file_identity(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise EpisodeRefusal(f"required input is not a file: {resolved}")
    return {
        "path": _record_path(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": _sha256(resolved),
    }


def deployment_identities(root: Path) -> dict[str, Any]:
    return {
        "path": _record_path(root),
        "manifest": file_identity(root / "deployment.json"),
        "descriptors": file_identity(root / "descriptors.bin"),
        "program": file_identity(root / "program.bin"),
    }


def _globbed_sources(patterns: Sequence[str]) -> set[Path]:
    paths: set[Path] = set()
    for pattern in patterns:
        paths.update(REPO.glob(pattern))
    return paths


def source_sha256(backend: str, model_id: str) -> dict[str, str]:
    if backend not in BACKEND_SOURCE_PATHS or model_id not in MODEL_SOURCE_PATHS:
        raise EpisodeRefusal("no functional source boundary exists for this target")
    paths = {
        Path(__file__).resolve(),
        *(REPO / relative for relative in FUNCTIONAL_SOURCE_PATHS),
        *(REPO / relative for relative in BACKEND_SOURCE_PATHS[backend]),
        *(REPO / relative for relative in MODEL_SOURCE_PATHS[model_id]),
        *_globbed_sources(FUNCTIONAL_SOURCE_GLOBS),
        *_globbed_sources(MODEL_SOURCE_GLOBS[model_id]),
        *_globbed_sources(BACKEND_SOURCE_GLOBS[backend]),
    }
    missing = [path for path in sorted(paths) if not path.is_file()]
    if missing:
        raise EpisodeRefusal(f"functional source boundary is missing {missing}")
    return {path.relative_to(REPO).as_posix(): _sha256(path) for path in sorted(paths)}


def expected_file_identity(
    path: Path, expected_sha256: str, label: str
) -> dict[str, Any]:
    """Bind a supplied artifact to an expectation independent of its contents."""

    if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(
        expected_sha256
    ):
        raise EpisodeRefusal(f"expected {label} SHA-256 is malformed")
    identity = file_identity(path)
    if identity["sha256"] != expected_sha256:
        raise EpisodeRefusal(
            f"{label} SHA-256 differs from the externally expected identity"
        )
    return identity


def require_unchanged_file(path: Path, identity: Mapping[str, Any], label: str) -> None:
    if file_identity(path) != dict(identity):
        raise EpisodeRefusal(f"{label} changed during lowering or execution")


def validate_reference_identity(
    profile: TargetProfile, path: Path, expected_sha256: str
) -> dict[str, Any]:
    if profile.oracle_sha256 is None:
        raise EpisodeRefusal(
            f"{profile.profile_id} has no published closed-loop oracle identity"
        )
    if expected_sha256 != profile.oracle_sha256:
        raise EpisodeRefusal(
            "--expected-reference-sha256 differs from the target profile lock"
        )
    return expected_file_identity(path, profile.oracle_sha256, "reference oracle")


def validate_checkpoint_identity(
    profile: TargetProfile, checkpoint: Path
) -> dict[str, Any]:
    """Bind a local root to the immutable official checkpoint declaration."""

    source_path = (
        REPO / "compiler" / "models" / profile.model_id / "checkpoint_source.json"
    )
    source_identity = expected_file_identity(
        source_path, profile.checkpoint_source_sha256, "checkpoint source"
    )
    source = load_json(source_path)
    expected_repository = (
        "Qwen/Qwen3-8B"
        if profile.model_id == "qwen3-8b"
        else "deepseek-ai/DeepSeek-V4-Flash-0731"
    )
    expected_revision = (
        "b968826d9c46dd6066d109eabc6255188de91218"
        if profile.model_id == "qwen3-8b"
        else "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    )
    if (
        source.get("schema") != "opentallas.checkpoint_source.v1"
        or source.get("repository") != expected_repository
        or source.get("revision") != expected_revision
        or source.get("remote_code_policy") != "disabled"
    ):
        raise EpisodeRefusal("checkpoint source is not the pinned model release")
    raw_expected = source.get("expected_files")
    if not isinstance(raw_expected, list):
        raise EpisodeRefusal("checkpoint source has no expected-file table")
    expected_by_path: dict[str, dict[str, Any]] = {}
    for entry in raw_expected:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise EpisodeRefusal("checkpoint source expected-file entry is malformed")
        name = entry["path"]
        if name in expected_by_path:
            raise EpisodeRefusal(f"checkpoint source duplicates {name!r}")
        expected_by_path[name] = entry

    files: dict[str, dict[str, Any]] = {}
    for relative, size, digest in profile.checkpoint_files:
        expected = {"path": relative, "size_bytes": size, "sha256": digest}
        if expected_by_path.get(relative) != expected:
            raise EpisodeRefusal(
                f"checkpoint source identity for {relative!r} differs from the profile"
            )
        identity = file_identity(checkpoint / relative)
        if identity["bytes"] != size or identity["sha256"] != digest:
            raise EpisodeRefusal(
                f"checkpoint file {relative!r} differs from the pinned release"
            )
        files[relative] = identity
    return {"source": source_identity, "files": files}


def select_target_profile(model_id: str, backend: str) -> TargetProfile:
    try:
        return TARGET_PROFILES[(model_id, backend)]
    except KeyError as exc:
        if model_id not in MODEL_BACKENDS:
            raise EpisodeRefusal(
                f"unsupported neutral graph model {model_id!r}"
            ) from exc
        raise EpisodeRefusal(
            f"backend {backend!r} is not valid for model {model_id!r}"
        ) from exc


def validate_target_inputs(
    *,
    profile: TargetProfile,
    graph: KernelGraph,
    kernel_ir_identity: Mapping[str, Any],
    capability: Capability,
    capability_identity: Mapping[str, Any],
) -> None:
    """Refuse a same-family graph or capability outside the fixed lane."""

    if not _integer(capability.topology_class):
        raise EpisodeRefusal("capability topology class must be a nonnegative integer")
    max_nodes = capability.limits.get("max_nodes")
    if not _integer(max_nodes, minimum=1):
        raise EpisodeRefusal("capability max_nodes must be a positive integer")
    numeric_profile = graph.to_dict().get("numeric_profile")
    checks = {
        "model_id": (graph.model_id, profile.model_id),
        "graph_id": (graph.graph_id, profile.graph_id),
        "kernel IR SHA-256": (
            kernel_ir_identity.get("sha256"),
            profile.kernel_ir_sha256,
        ),
        "numeric profile": (numeric_profile, profile.numeric_profile),
        "capability SHA-256": (
            capability_identity.get("sha256"),
            profile.capability_sha256,
        ),
        "capability digest": (capability.digest, profile.capability_sha256),
        "topology class": (capability.topology_class, profile.topology_class),
        "maximum node count": (
            max_nodes,
            profile.node_count,
        ),
    }
    for label, (actual, expected) in checks.items():
        if actual != expected:
            raise EpisodeRefusal(
                f"{profile.profile_id}: {label} {actual!r} differs from {expected!r}"
            )


def _resolve(spec: str) -> Callable[..., Deployment]:
    module_name, separator, attribute = spec.partition(":")
    if not separator:
        raise EpisodeRefusal(f"invalid lowerer specification {spec!r}")
    return getattr(importlib.import_module(module_name), attribute)


def workload_digest(workload: Mapping[str, Any]) -> str:
    required = ("workload_id", "kind", "token_ids", "max_new_tokens")
    missing = [key for key in required if key not in workload]
    if missing:
        raise EpisodeRefusal(f"workload is missing digest fields {missing}")
    payload = json.dumps(
        {key: workload[key] for key in required},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _validate_oracle_action(
    model_id: str, turn_index: int, turn: Mapping[str, Any]
) -> None:
    parsed = turn.get("parsed")
    if not isinstance(parsed, dict):
        raise EpisodeRefusal(f"oracle turn {turn_index} lacks a normalized parse")
    outcome = turn["outcome"]
    expected_keys = {"kind", "command", "answer"}
    if model_id == "deepseek-v4-flash-0731":
        expected_keys.add("tool_name")
    if set(parsed) != expected_keys:
        raise EpisodeRefusal(
            f"oracle turn {turn_index} parsed fields are not the normalized schema"
        )
    if outcome == "executed":
        command = parsed.get("command")
        if (
            parsed.get("kind") != "command"
            or not isinstance(command, str)
            or not command
            or command != command.strip()
            or "\n" in command
            or "\r" in command
            or parsed.get("answer") is not None
        ):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} has an invalid command parse"
            )
        if (
            model_id == "deepseek-v4-flash-0731"
            and parsed.get("tool_name") != "run_shell"
        ):
            raise EpisodeRefusal(f"oracle turn {turn_index} has the wrong tool parse")
        try:
            validate_inventory_command(command)
        except EpisodeRefusal as exc:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} command violates the execution policy: {exc}"
            ) from exc
        observation = turn["observation"]
        expected_observation_keys = {
            "command",
            "exit_code",
            "stdout",
            "stderr",
            "timed_out",
            "truncated",
        }
        if set(observation) != expected_observation_keys:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} observation fields are not exact"
            )
        if (
            observation.get("command") != command
            or not isinstance(observation.get("exit_code"), int)
            or isinstance(observation.get("exit_code"), bool)
            or not isinstance(observation.get("stdout"), str)
            or not isinstance(observation.get("stderr"), str)
            or not isinstance(observation.get("timed_out"), bool)
            or not isinstance(observation.get("truncated"), bool)
        ):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} has a malformed command observation"
            )
        return

    if (
        parsed.get("kind") != "answer"
        or parsed.get("command") is not None
        or parsed.get("answer") is None
        or not isinstance(parsed.get("answer"), str)
    ):
        raise EpisodeRefusal(f"oracle turn {turn_index} has an invalid answer parse")
    if model_id == "deepseek-v4-flash-0731" and parsed.get("tool_name") is not None:
        raise EpisodeRefusal(f"oracle turn {turn_index} answer names a tool")
    if parsed["answer"] != turn.get("answer", parsed["answer"]):
        raise EpisodeRefusal(f"oracle turn {turn_index} has inconsistent answer fields")
    if "observation" in turn and turn.get("observation") is not None:
        raise EpisodeRefusal(f"oracle turn {turn_index} answer carries an observation")


@dataclass(frozen=True)
class ValidatedBundle:
    workload: dict[str, Any]
    index: dict[str, Any]
    oracle: dict[str, Any]
    oracle_result: dict[str, Any]
    oracle_episode: dict[str, Any]
    tokenizer_sha256: str
    expected_total: int
    max_turns: int
    context_capacity: int


def validate_bundle(
    *,
    profile: TargetProfile,
    checkpoint: Path,
    workload_path: Path,
    index_path: Path,
    reference_path: Path,
) -> ValidatedBundle:
    """Reopen and cross-check every model-independent episode identity."""

    expected_file_identity(workload_path, profile.workload_sha256, "workload")
    workload = load_json(workload_path)
    expected_file_identity(index_path, profile.workload_index_sha256, "workload index")
    index = load_json(index_path)
    oracle = load_json(reference_path)

    graph_model_id = profile.model_id
    if workload.get("workload_id") != profile.workload_id:
        raise EpisodeRefusal("the workload is not the target profile's agent task")
    if workload.get("kind") != "agent":
        raise EpisodeRefusal("the selected workload kind must be 'agent'")
    if workload.get("digest") != workload_digest(workload):
        raise EpisodeRefusal(
            "the workload digest does not match its exact token request"
        )
    if workload.get("digest") != profile.workload_digest:
        raise EpisodeRefusal("the workload digest differs from the target profile")
    tokens = workload.get("token_ids")
    if (
        not isinstance(tokens, list)
        or not tokens
        or not all(_integer(token) for token in tokens)
    ):
        raise EpisodeRefusal("workload.token_ids must be a non-empty integer list")
    if any(int(token) >= profile.vocabulary_size for token in tokens):
        raise EpisodeRefusal("workload.token_ids contains an out-of-vocabulary token")
    if workload.get("prompt_token_count") != len(tokens):
        raise EpisodeRefusal("workload prompt_token_count differs from token_ids")
    if not _integer(workload.get("max_new_tokens"), minimum=1):
        raise EpisodeRefusal("workload max_new_tokens must be positive")
    rendered = workload.get("rendered_text")
    if not isinstance(rendered, str) or not rendered:
        raise EpisodeRefusal("workload rendered_text must be non-empty")
    if (
        workload.get("rendered_text_sha256")
        != hashlib.sha256(rendered.encode()).hexdigest()
    ):
        raise EpisodeRefusal("workload rendered_text_sha256 is invalid")

    metadata = workload.get("metadata")
    if not isinstance(metadata, dict) or metadata.get("closed_loop") is not True:
        raise EpisodeRefusal("agent workload must explicitly declare closed_loop=true")
    sandbox_files = metadata.get("sandbox_files")
    if (
        not isinstance(sandbox_files, dict)
        or not sandbox_files
        or not all(
            isinstance(name, str) and isinstance(body, str)
            for name, body in sandbox_files.items()
        )
    ):
        raise EpisodeRefusal("metadata.sandbox_files must be a non-empty string map")
    for name in sandbox_files:
        relative = Path(name)
        if (
            not name
            or relative.is_absolute()
            or relative == Path(".")
            or ".." in relative.parts
        ):
            raise EpisodeRefusal(
                f"sandbox file path {name!r} is not relative and confined"
            )
    expected_total = metadata.get("expected_total")
    max_turns = metadata.get("max_turns")
    context_capacity = metadata.get("session_context_capacity")
    if not _integer(expected_total):
        raise EpisodeRefusal("metadata.expected_total must be a nonnegative integer")
    if expected_total != profile.expected_total:
        raise EpisodeRefusal("metadata.expected_total differs from the target profile")
    if not _integer(max_turns, minimum=2):
        raise EpisodeRefusal("metadata.max_turns must be at least two")
    if not _integer(context_capacity, minimum=1):
        raise EpisodeRefusal("metadata.session_context_capacity must be positive")
    if graph_model_id == "qwen3-8b" and not isinstance(
        metadata.get("enable_thinking"), bool
    ):
        raise EpisodeRefusal("Qwen agent metadata must bind enable_thinking")
    if graph_model_id == "deepseek-v4-flash-0731" and metadata.get(
        "thinking_mode"
    ) not in {"chat", "thinking"}:
        raise EpisodeRefusal("DeepSeek agent metadata must bind thinking_mode")

    if index.get("schema") != profile.workload_index_schema:
        raise EpisodeRefusal("workload index schema differs from the target profile")
    if index.get("model_id") != graph_model_id:
        raise EpisodeRefusal("workload index model_id differs from the neutral graph")
    tokenizer_sha = index.get("tokenizer_sha256")
    if not isinstance(tokenizer_sha, str) or not _SHA256_RE.fullmatch(tokenizer_sha):
        raise EpisodeRefusal("workload index has no valid tokenizer SHA-256")
    if tokenizer_sha != profile.tokenizer_sha256:
        raise EpisodeRefusal("workload index tokenizer differs from the target profile")
    entries = index.get("workloads")
    workload_id = workload.get("workload_id")
    if not isinstance(entries, dict) or workload_id not in entries:
        raise EpisodeRefusal(f"workload index has no entry for {workload_id!r}")
    entry = entries[workload_id]
    if not isinstance(entry, dict):
        raise EpisodeRefusal("workload index entry is not an object")
    indexed_path = (index_path.parent / str(entry.get("path", ""))).resolve()
    if indexed_path != workload_path.resolve():
        raise EpisodeRefusal(
            "workload index entry does not name the selected workload file"
        )
    expected_entry = {
        "kind": workload["kind"],
        "digest": workload["digest"],
        "prompt_token_count": len(tokens),
        "max_new_tokens": workload["max_new_tokens"],
    }
    for key, expected in expected_entry.items():
        if entry.get(key) != expected:
            raise EpisodeRefusal(f"workload index {key} differs from the workload")

    if graph_model_id == "qwen3-8b":
        snapshot = index.get("snapshot")
        if (
            not isinstance(snapshot, str)
            or Path(snapshot).resolve() != checkpoint.resolve()
        ):
            raise EpisodeRefusal(
                "Qwen workload index snapshot differs from --checkpoint"
            )
    else:
        source = index.get("source")
        if not isinstance(source, dict) or source != {
            "repository": "deepseek-ai/DeepSeek-V4-Flash-0731",
            "revision": "7872f01b1d1fe23eabc4c98b48bffcef5a386062",
        }:
            raise EpisodeRefusal(
                "DeepSeek workload index source is not the pinned release"
            )

    if oracle.get("schema") != ORACLE_SCHEMA:
        raise EpisodeRefusal(f"oracle schema must be {ORACLE_SCHEMA!r}")
    if oracle.get("evidence_class") != "external_reference_comparator":
        raise EpisodeRefusal(
            "oracle is not labelled as an external reference comparator"
        )
    if oracle.get("model_id") != graph_model_id:
        raise EpisodeRefusal("oracle model_id differs from the neutral graph")
    if oracle.get("tokenizer_sha256") != tokenizer_sha:
        raise EpisodeRefusal("oracle and workload index bind different tokenizers")
    results = oracle.get("results")
    if not isinstance(results, dict) or workload_id not in results:
        raise EpisodeRefusal(f"oracle has no result for {workload_id!r}")
    oracle_result = results[workload_id]
    if not isinstance(oracle_result, dict):
        raise EpisodeRefusal("oracle workload result is not an object")
    if oracle_result.get("workload_digest") != workload["digest"]:
        raise EpisodeRefusal("oracle was generated from a different workload digest")
    if (
        graph_model_id == "deepseek-v4-flash-0731"
        and oracle_result.get("expert_numeric_path") != "fp8"
    ):
        raise EpisodeRefusal("DeepSeek oracle did not use the shipped fp8 expert path")
    episode = oracle_result.get("episode")
    if not isinstance(episode, dict):
        raise EpisodeRefusal("oracle result is a static generation, not an episode")
    turns = episode.get("turns")
    if not isinstance(turns, list) or len(turns) < 2:
        raise EpisodeRefusal("oracle episode must contain at least two turns")
    if not _integer(episode.get("turn_count"), minimum=2) or episode.get(
        "turn_count"
    ) != len(turns):
        raise EpisodeRefusal("oracle episode turn_count is inconsistent")
    if len(turns) > max_turns:
        raise EpisodeRefusal("oracle episode exceeds the workload max_turns")
    if episode.get("stop_reason") != "answered":
        raise EpisodeRefusal("oracle episode did not terminate with an answer")
    if episode.get("answer") != str(expected_total):
        raise EpisodeRefusal(
            "oracle episode's final answer is not the exact expected total"
        )
    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, dict) or turn.get("turn") != turn_index:
            raise EpisodeRefusal(f"oracle turn {turn_index} is missing or out of order")
        prompt = turn.get("prompt_token_ids")
        generated = turn.get("generated_token_ids")
        if (
            not isinstance(prompt, list)
            or not prompt
            or not all(_integer(token) for token in prompt)
        ):
            raise EpisodeRefusal(f"oracle turn {turn_index} has invalid prompt tokens")
        if (
            not isinstance(generated, list)
            or not generated
            or not all(_integer(token) for token in generated)
        ):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} has invalid generated tokens"
            )
        if any(
            int(token) >= profile.vocabulary_size for token in (*prompt, *generated)
        ):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} contains an out-of-vocabulary token"
            )
        if turn.get("prompt_token_count") != len(prompt):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} prompt count is inconsistent"
            )
        if turn.get("generated_token_count") != len(generated):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} generated count is inconsistent"
            )
        if not _integer(turn.get("max_new_tokens"), minimum=1):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} has no positive token limit"
            )
        if turn.get("stop_reason") not in {"eos", "max_new_tokens"}:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} has an invalid terminal reason"
            )
        if turn.get("outcome") not in {"executed", "answered"}:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} is not part of a closed loop"
            )
        expected_outcome = "answered" if turn_index == len(turns) - 1 else "executed"
        if turn.get("outcome") != expected_outcome:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} must have outcome {expected_outcome!r}"
            )
        if turn.get("outcome") == "executed" and not isinstance(
            turn.get("observation"), dict
        ):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} lacks a sandbox observation"
            )
        rendered_sha = turn.get("rendered_prompt_sha256")
        if not isinstance(rendered_sha, str) or not _SHA256_RE.fullmatch(rendered_sha):
            raise EpisodeRefusal(
                f"oracle turn {turn_index} lacks a rendered prompt identity"
            )
        budget = context_capacity - len(prompt)
        expected_limit = min(int(workload["max_new_tokens"]), budget)
        if budget <= 0 or turn.get("max_new_tokens") != expected_limit:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} token limit violates the context contract"
            )
        terminal = _terminal_problems(
            tokens=generated,
            stop_reason=str(turn["stop_reason"]),
            limit=expected_limit,
            eos_token_ids=profile.eos_token_ids,
        )
        if terminal:
            raise EpisodeRefusal(
                f"oracle turn {turn_index} has invalid terminal evidence: {terminal}"
            )
        _validate_oracle_action(graph_model_id, turn_index, turn)

    first = turns[0]
    if first["prompt_token_ids"] != tokens:
        raise EpisodeRefusal("oracle turn 0 prompt differs from the workload tokens")
    if first["rendered_prompt_sha256"] != workload["rendered_text_sha256"]:
        raise EpisodeRefusal("oracle turn 0 rendered prompt differs from the workload")
    if turns[-1]["parsed"]["answer"] != episode["answer"]:
        raise EpisodeRefusal(
            "oracle final parsed answer differs from the episode answer"
        )

    return ValidatedBundle(
        workload=workload,
        index=index,
        oracle=oracle,
        oracle_result=oracle_result,
        oracle_episode=episode,
        tokenizer_sha256=tokenizer_sha,
        expected_total=int(expected_total),
        max_turns=int(max_turns),
        context_capacity=int(context_capacity),
    )


@dataclass(frozen=True)
class ParsedModelTurn:
    kind: str
    raw_decoded_text: str
    visible_text: str
    thinking_text: str | None
    parsed: dict[str, Any]
    assistant_message: dict[str, Any]
    command: str | None = None
    answer: str | None = None


def _exact_answer(text: str) -> str | None:
    match = _ANSWER_LINE.fullmatch(text.strip())
    if match is None:
        return None
    answer = match.group("answer").strip()
    if not answer:
        raise EpisodeRefusal("the model emitted an empty ANSWER line")
    return answer


def parse_qwen_completion(raw_text: str, visible_text: str) -> ParsedModelTurn:
    """Apply the official Qwen parser and reject answer/action ambiguity."""

    open_count = visible_text.count("<think>")
    close_count = visible_text.count("</think>")
    if (open_count, close_count) not in {(0, 0), (1, 1)}:
        raise EpisodeRefusal("Qwen turn has malformed thinking delimiters")
    if open_count:
        open_at = visible_text.find("<think>")
        close_at = visible_text.find("</think>")
        if open_at > close_at or visible_text[:open_at].strip():
            raise EpisodeRefusal("Qwen turn has malformed thinking delimiters")
    thinking, action_text = split_thinking(visible_text)
    try:
        parsed = parse_turn(action_text)
    except AgentProtocolError as exc:
        raise EpisodeRefusal(str(exc)) from exc
    answer_lines = [
        line for line in action_text.splitlines() if line.startswith("ANSWER:")
    ]
    fences = _QWEN_FENCE.findall(action_text)
    if answer_lines and fences:
        raise EpisodeRefusal(
            "Qwen turn ambiguously contains both an answer and a command"
        )
    if parsed.kind == "answer":
        answer = _exact_answer(action_text)
        if answer is None:
            raise EpisodeRefusal("Qwen final turn must be exactly one ANSWER line")
        return ParsedModelTurn(
            kind="answer",
            raw_decoded_text=raw_text,
            visible_text=action_text,
            thinking_text=thinking,
            parsed={"kind": "answer", "command": None, "answer": answer},
            assistant_message={"role": "assistant", "content": visible_text},
            answer=answer,
        )
    if parsed.kind != "command" or parsed.command is None:
        raise EpisodeRefusal("Qwen turn contains neither one command nor one answer")
    command = parsed.command.strip()
    if not command or "\n" in command or "\r" in command:
        raise EpisodeRefusal("Qwen run_shell command must be one non-empty line")
    return ParsedModelTurn(
        kind="command",
        raw_decoded_text=raw_text,
        visible_text=action_text,
        thinking_text=thinking,
        parsed={"kind": "command", "command": command, "answer": None},
        assistant_message={"role": "assistant", "content": visible_text},
        command=command,
    )


def _strict_arguments(text: str) -> dict[str, Any]:
    try:
        value = json.loads(
            text,
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise EpisodeRefusal(f"tool arguments are not strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EpisodeRefusal("tool arguments must be one JSON object")
    return value


def parse_deepseek_completion(raw_text: str, thinking_mode: str) -> ParsedModelTurn:
    """Parse the exact DeepSeek DSML wire grammar and narrow it to run_shell."""

    from compiler.frontend.deepseek_v4_encoding import (
        DeepSeekV4CompletionError,
        parse_message_from_completion_text,
    )

    try:
        message = parse_message_from_completion_text(raw_text, thinking_mode)
    except DeepSeekV4CompletionError as exc:
        raise EpisodeRefusal(str(exc)) from exc
    calls = message["tool_calls"]
    content = message["content"]
    reasoning = message["reasoning_content"] or None
    if calls:
        if len(calls) != 1:
            raise EpisodeRefusal("DeepSeek turn must contain exactly one tool call")
        if content.strip():
            raise EpisodeRefusal(
                "DeepSeek command turn also contains final-answer content"
            )
        function = calls[0].get("function")
        if not isinstance(function, dict) or function.get("name") != "run_shell":
            raise EpisodeRefusal("DeepSeek may call only run_shell")
        argument_text = function.get("arguments")
        if not isinstance(argument_text, str):
            raise EpisodeRefusal("run_shell arguments must remain encoded as text")
        arguments = _strict_arguments(argument_text)
        if set(arguments) != {"command"} or not isinstance(arguments["command"], str):
            raise EpisodeRefusal(
                "run_shell requires exactly one string command argument"
            )
        command = arguments["command"]
        if (
            not command
            or command != command.strip()
            or "\n" in command
            or "\r" in command
        ):
            raise EpisodeRefusal("run_shell command must be one non-empty line")
        return ParsedModelTurn(
            kind="command",
            raw_decoded_text=raw_text,
            visible_text=content,
            thinking_text=reasoning,
            parsed={
                "kind": "command",
                "tool_name": "run_shell",
                "command": command,
                "answer": None,
            },
            assistant_message=message,
            command=command,
        )
    answer = _exact_answer(content)
    if answer is None:
        raise EpisodeRefusal("DeepSeek final turn must be exactly one ANSWER line")
    return ParsedModelTurn(
        kind="answer",
        raw_decoded_text=raw_text,
        visible_text=content,
        thinking_text=reasoning,
        parsed={
            "kind": "answer",
            "tool_name": None,
            "command": None,
            "answer": answer,
        },
        assistant_message=message,
        answer=answer,
    )


class ModelAdapter(Protocol):
    model_id: str

    def initial_messages(self) -> list[dict[str, Any]]: ...

    def render(
        self, messages: Sequence[Mapping[str, Any]]
    ) -> tuple[str, list[int]]: ...

    def parse_generated(self, token_ids: Sequence[int]) -> ParsedModelTurn: ...

    def append_observation(
        self,
        messages: Sequence[Mapping[str, Any]],
        turn: ParsedModelTurn,
        observation: str,
    ) -> list[dict[str, Any]]: ...

    def tokenizer_identities(self) -> dict[str, Any]: ...


class QwenAdapter:
    model_id = "qwen3-8b"

    def __init__(self, checkpoint: Path, metadata: Mapping[str, Any]) -> None:
        from compiler.workloads.qwen3 import AGENT_SYSTEM, AGENT_TASK
        from transformers import AutoTokenizer

        enable_thinking = metadata.get("enable_thinking")
        if not isinstance(enable_thinking, bool):
            raise EpisodeRefusal("Qwen agent metadata must bind enable_thinking")
        self.enable_thinking = enable_thinking
        self._system = AGENT_SYSTEM
        self._task = AGENT_TASK
        self._checkpoint = checkpoint.resolve()
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(checkpoint), local_files_only=True, trust_remote_code=False
        )

    def initial_messages(self) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": self._system},
            {"role": "user", "content": self._task},
        ]

    def render(self, messages: Sequence[Mapping[str, Any]]) -> tuple[str, list[int]]:
        return render_agent_context(
            self._tokenizer, messages, enable_thinking=self.enable_thinking
        )

    def parse_generated(self, token_ids: Sequence[int]) -> ParsedModelTurn:
        raw = self._tokenizer.decode(list(token_ids), skip_special_tokens=False)
        visible = self._tokenizer.decode(list(token_ids), skip_special_tokens=True)
        return parse_qwen_completion(raw, visible)

    def append_observation(
        self,
        messages: Sequence[Mapping[str, Any]],
        turn: ParsedModelTurn,
        observation: str,
    ) -> list[dict[str, Any]]:
        result = [dict(message) for message in messages]
        result.append(dict(turn.assistant_message))
        result.append({"role": "user", "content": observation})
        return result

    def tokenizer_identities(self) -> dict[str, Any]:
        names = ("tokenizer.json", "tokenizer_config.json", "generation_config.json")
        return {name: file_identity(self._checkpoint / name) for name in names}


class DeepSeekAdapter:
    model_id = "deepseek-v4-flash-0731"

    def __init__(self, checkpoint: Path, metadata: Mapping[str, Any]) -> None:
        from compiler.frontend.deepseek_v4_tokenizer import (
            load_verified_deepseek_v4_tokenizer,
        )
        from compiler.workloads.deepseek_v4 import AGENT_SYSTEM, AGENT_TASK, AGENT_TOOLS

        mode = metadata.get("thinking_mode")
        if mode not in {"chat", "thinking"}:
            raise EpisodeRefusal("DeepSeek agent metadata must bind thinking_mode")
        tools = metadata.get("tools")
        expected_tools = [dict(tool) for tool in AGENT_TOOLS]
        if tools != expected_tools:
            raise EpisodeRefusal(
                "DeepSeek workload tool schema is not the pinned run_shell schema"
            )
        self.thinking_mode = str(mode)
        self._system = AGENT_SYSTEM
        self._task = AGENT_TASK
        self._tools = expected_tools
        self._checkpoint = checkpoint.resolve()
        self._tokenizer = load_verified_deepseek_v4_tokenizer(checkpoint)

    def initial_messages(self) -> list[dict[str, Any]]:
        return [
            {"role": "system", "content": self._system, "tools": self._tools},
            {"role": "user", "content": self._task},
        ]

    def render(self, messages: Sequence[Mapping[str, Any]]) -> tuple[str, list[int]]:
        return self._tokenizer.encode_prompt(
            [dict(message) for message in messages], self.thinking_mode
        )

    def parse_generated(self, token_ids: Sequence[int]) -> ParsedModelTurn:
        raw = self._tokenizer.decode(list(token_ids), skip_special_tokens=False)
        return parse_deepseek_completion(raw, self.thinking_mode)

    def append_observation(
        self,
        messages: Sequence[Mapping[str, Any]],
        turn: ParsedModelTurn,
        observation: str,
    ) -> list[dict[str, Any]]:
        result = [dict(message) for message in messages]
        result.append(dict(turn.assistant_message))
        result.append({"role": "tool", "content": observation})
        return result

    def tokenizer_identities(self) -> dict[str, Any]:
        names = ("tokenizer.json", "tokenizer_config.json", "generation_config.json")
        return {name: file_identity(self._checkpoint / name) for name in names}


def make_adapter(
    model_id: str, checkpoint: Path, metadata: Mapping[str, Any]
) -> ModelAdapter:
    if model_id == "qwen3-8b":
        return QwenAdapter(checkpoint, metadata)
    if model_id == "deepseek-v4-flash-0731":
        return DeepSeekAdapter(checkpoint, metadata)
    raise EpisodeRefusal(f"no agent protocol adapter exists for model {model_id!r}")


def _counter_delta(
    before: Mapping[str, int], after: Mapping[str, int]
) -> dict[str, int]:
    keys = set(before) | set(after)
    result: dict[str, int] = {}
    for key in sorted(keys):
        left, right = before.get(key, 0), after.get(key, 0)
        if not _integer(left) or not _integer(right) or right < left:
            raise EpisodeRefusal(f"counter {key!r} is malformed or decreased")
        if right != left:
            result[key] = right - left
    return result


def _node_counter_deltas(
    before: Sequence[Mapping[str, int]], after: Sequence[Mapping[str, int]]
) -> list[dict[str, int]]:
    if len(before) != len(after):
        raise EpisodeRefusal("per-node counter snapshot count changed during a turn")
    return [
        _counter_delta(left, right) for left, right in zip(before, after, strict=True)
    ]


@dataclass(frozen=True)
class TurnExecution:
    result: Any
    session_id: int
    generation_policy: dict[str, Any]
    counters_before: dict[str, int]
    counters_after: dict[str, int]
    node_counters_before: list[dict[str, int]]
    node_counters_after: list[dict[str, int]]


@dataclass(frozen=True)
class EpisodeOutcome:
    status: str
    stop_reason: str
    answer: str | None
    task_solved: bool
    turns: list[dict[str, Any]]
    executed_command_count: int
    oracle_agreement: bool
    generation_policy: dict[str, Any]
    generation_policy_digest: str
    problems: list[str]


def _terminal_problems(
    *, tokens: Sequence[int], stop_reason: str, limit: int, eos_token_ids: Sequence[int]
) -> list[str]:
    problems: list[str] = []
    eos = set(int(token) for token in eos_token_ids)
    if not tokens:
        return ["generated token sequence is empty"]
    if len(tokens) > limit:
        problems.append("generated token sequence exceeds its declared limit")
    if stop_reason == "eos":
        if tokens[-1] not in eos or any(token in eos for token in tokens[:-1]):
            problems.append("EOS stop is not exactly the first official EOS")
    elif stop_reason == "max_new_tokens":
        if len(tokens) != limit or any(token in eos for token in tokens):
            problems.append("token-cap stop is not an exact non-EOS cap")
    else:
        problems.append(f"unsupported stop reason {stop_reason!r}")
    return problems


def _step_problems(
    result: Any, generated: Sequence[int], *, prompt_token_count: int
) -> list[str]:
    steps = getattr(result, "per_step", None)
    if not isinstance(steps, list) or len(steps) != len(generated):
        return ["per_step evidence does not contain exactly one row per token"]
    problems: list[str] = []
    transaction_ids: list[int] = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            problems.append(f"per_step[{index}] is not an object")
            continue
        if step.get("step") != index:
            problems.append(f"per_step[{index}] has the wrong step index")
        if step.get("phase") != ("prefill" if index == 0 else "decode"):
            problems.append(f"per_step[{index}] has the wrong phase")
        if step.get("status") != "SUCCESS" or step.get("trap") != "NONE":
            problems.append(f"per_step[{index}] did not complete successfully")
        if step.get("produced_tokens") != [generated[index]]:
            problems.append(f"per_step[{index}] does not bind its produced token")
        if step.get("final_token_id") != generated[index]:
            problems.append(f"per_step[{index}] does not bind its final token")
        transaction = step.get("transaction_id")
        if not _integer(transaction, minimum=1):
            problems.append(f"per_step[{index}] has no positive transaction id")
        else:
            transaction_ids.append(int(transaction))
    if len(transaction_ids) == len(steps) and any(
        left >= right for left, right in zip(transaction_ids, transaction_ids[1:])
    ):
        problems.append("per-step transaction ids are not strictly increasing")
    if getattr(result, "transactions", None) != len(steps):
        problems.append("driver transaction count differs from per_step evidence")
    if getattr(result, "prefill_tokens", None) != prompt_token_count:
        problems.append("driver prefill token count differs from the rendered prompt")
    if getattr(result, "decode_steps", None) != max(0, len(generated) - 1):
        problems.append("driver decode-step count differs from generated tokens")
    return problems


def _observation_dict(observation: CommandResult) -> dict[str, Any]:
    return observation.to_dict()


def run_episode(
    *,
    adapter: ModelAdapter,
    workload: Mapping[str, Any],
    oracle_episode: Mapping[str, Any],
    expected_total: int,
    max_turns: int,
    context_capacity: int,
    vocabulary_size: int,
    eos_token_ids: Sequence[int],
    generate_turn: Callable[[Sequence[int], int], TurnExecution],
    sandbox: Any,
) -> EpisodeOutcome:
    """Drive a closed loop using injected generation and sandbox dependencies."""

    if not _integer(expected_total):
        raise EpisodeRefusal("expected_total must be a nonnegative integer")
    if not _integer(max_turns, minimum=2):
        raise EpisodeRefusal("max_turns must be at least two")
    if not _integer(context_capacity, minimum=1):
        raise EpisodeRefusal("context_capacity must be positive")
    if not _integer(vocabulary_size, minimum=1):
        raise EpisodeRefusal("vocabulary_size must be positive")
    if (
        not isinstance(eos_token_ids, Sequence)
        or not eos_token_ids
        or not all(
            _integer(token) and int(token) < vocabulary_size for token in eos_token_ids
        )
        or len(set(eos_token_ids)) != len(eos_token_ids)
    ):
        raise EpisodeRefusal("eos_token_ids must be distinct in-vocabulary integers")
    messages = adapter.initial_messages()
    gold_turns = oracle_episode.get("turns")
    if not isinstance(gold_turns, list) or len(gold_turns) < 2:
        raise EpisodeRefusal("oracle episode must supply at least two turns")
    turns: list[dict[str, Any]] = []
    problems: list[str] = []
    answer: str | None = None
    stop_reason = "max_turns"
    executed_commands = 0
    policies: list[dict[str, Any]] = []
    session_ids: list[int] = []

    for index in range(max_turns):
        if index >= len(gold_turns):
            problems.append(
                "accelerator episode requires a turn absent from the oracle"
            )
            stop_reason = "oracle_exhausted"
            break
        gold = gold_turns[index]
        rendered, prompt_value = adapter.render(messages)
        if not isinstance(rendered, str) or not rendered:
            raise EpisodeRefusal("adapter rendered an empty or non-text prompt")
        try:
            prompt = list(prompt_value)
        except TypeError as exc:
            raise EpisodeRefusal("adapter prompt tokens are not a sequence") from exc
        if not prompt or not all(_integer(token) for token in prompt):
            raise EpisodeRefusal("adapter prompt tokens are not nonnegative integers")
        prompt_problems = validate_token_ids(prompt, vocabulary_size)
        if prompt_problems:
            raise EpisodeRefusal(
                "adapter rendered invalid prompt tokens: " + "; ".join(prompt_problems)
            )
        rendered_sha = hashlib.sha256(rendered.encode()).hexdigest()
        if index == 0:
            if prompt != list(workload["token_ids"]):
                raise EpisodeRefusal(
                    "turn-0 renderer differs from the pinned workload tokens"
                )
            if rendered != workload["rendered_text"]:
                raise EpisodeRefusal(
                    "turn-0 renderer differs from the pinned workload text"
                )
        budget = context_capacity - len(prompt)
        if budget <= 0:
            problems.append("rendered prompt exhausts the pinned context capacity")
            stop_reason = "context_exhausted"
            break
        limit = min(int(workload["max_new_tokens"]), budget)
        prompt_match = prompt == gold["prompt_token_ids"]
        rendered_match = rendered_sha == gold["rendered_prompt_sha256"]
        limit_match = limit == gold["max_new_tokens"]
        if not (prompt_match and rendered_match and limit_match):
            turns.append(
                {
                    "turn": index,
                    "prompt_token_ids": prompt,
                    "prompt_token_count": len(prompt),
                    "rendered_prompt_text": rendered,
                    "rendered_prompt_sha256": rendered_sha,
                    "max_new_tokens": limit,
                    "outcome": "oracle_prompt_divergence",
                    "oracle_comparison": {
                        "prompt_exact": prompt_match,
                        "rendered_prompt_exact": rendered_match,
                        "token_limit_exact": limit_match,
                        "generated_exact": False,
                        "stop_reason_exact": False,
                    },
                }
            )
            problems.append(
                f"turn {index} prompt or token limit differs from the oracle"
            )
            stop_reason = "oracle_divergence"
            break

        execution = generate_turn(prompt, limit)
        result = execution.result
        repeated_session = execution.session_id in session_ids
        session_ids.append(execution.session_id)
        policies.append(dict(execution.generation_policy))
        try:
            generated = list(result.generated_token_ids)
            result_prompt = list(result.prompt_token_ids)
        except (AttributeError, TypeError) as exc:
            raise EpisodeRefusal(
                "driver result does not carry token sequences"
            ) from exc
        result_stop = str(result.stop_reason)
        evidence_problems: list[str] = []
        if not _integer(execution.session_id, minimum=1):
            evidence_problems.append("accelerator session id is not a positive integer")
        elif repeated_session:
            evidence_problems.append("accelerator session id was reused")
        if result_prompt != prompt or not all(
            _integer(token) for token in result_prompt
        ):
            evidence_problems.append(
                "driver result prompt differs from the rendered prompt"
            )
        token_type_problems = validate_token_ids(generated, vocabulary_size)
        evidence_problems.extend(token_type_problems)
        if all(
            isinstance(token, int) and not isinstance(token, bool)
            for token in generated
        ):
            evidence_problems.extend(
                check_token_legitimacy(
                    generated,
                    vocabulary_size=vocabulary_size,
                    eos_token_ids=eos_token_ids,
                    stop_reason=result_stop,
                )
            )
            evidence_problems.extend(
                _terminal_problems(
                    tokens=generated,
                    stop_reason=result_stop,
                    limit=limit,
                    eos_token_ids=eos_token_ids,
                )
            )
        evidence_problems.extend(
            _step_problems(result, generated, prompt_token_count=len(prompt))
        )
        if result_stop == "eos":
            if not generated or result.eos_token_id != generated[-1]:
                evidence_problems.append(
                    "driver EOS identity does not bind the final token"
                )
        elif result.eos_token_id is not None:
            evidence_problems.append(
                "non-EOS termination unexpectedly names an EOS token"
            )
        if result.failure:
            evidence_problems.append(str(result.failure))

        generated_match = generated == gold["generated_token_ids"]
        stop_match = result_stop == gold["stop_reason"]
        gold_terminal = _terminal_problems(
            tokens=gold["generated_token_ids"],
            stop_reason=str(gold["stop_reason"]),
            limit=limit,
            eos_token_ids=eos_token_ids,
        )
        if gold_terminal:
            raise EpisodeRefusal(
                f"oracle turn {index} has invalid terminal evidence: {gold_terminal}"
            )
        comparison = {
            "prompt_exact": True,
            "rendered_prompt_exact": True,
            "token_limit_exact": True,
            "generated_exact": generated_match,
            "stop_reason_exact": stop_match,
            "oracle_generated_token_count": len(gold["generated_token_ids"]),
        }
        record: dict[str, Any] = {
            "turn": index,
            "session_id": execution.session_id,
            "prompt_token_ids": prompt,
            "prompt_token_count": len(prompt),
            "rendered_prompt_text": rendered,
            "rendered_prompt_sha256": rendered_sha,
            "max_new_tokens": limit,
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "stop_reason": result_stop,
            "eos_token_id": result.eos_token_id,
            "failure": result.failure,
            "token_legitimacy_problems": evidence_problems,
            "per_step": result.per_step,
            "transactions": result.transactions,
            "prefill_tokens": result.prefill_tokens,
            "decode_steps": result.decode_steps,
            "driver_counters": result.counters,
            "counters_before": execution.counters_before,
            "counters_after": execution.counters_after,
            "counter_delta": _counter_delta(
                execution.counters_before, execution.counters_after
            ),
            "node_counters_before": execution.node_counters_before,
            "node_counters_after": execution.node_counters_after,
            "node_counter_delta": _node_counter_deltas(
                execution.node_counters_before, execution.node_counters_after
            ),
            "oracle_comparison": comparison,
        }
        turns.append(record)
        if evidence_problems:
            record["outcome"] = "invalid_execution_evidence"
            problems.extend(f"turn {index}: {problem}" for problem in evidence_problems)
            stop_reason = "failed"
            break
        if not generated_match or not stop_match:
            record["outcome"] = "oracle_token_divergence"
            problems.append(
                f"turn {index} tokens or terminal reason differ from oracle"
            )
            stop_reason = "oracle_divergence"
            break

        try:
            parsed = adapter.parse_generated(generated)
            if parsed.kind == "command" and parsed.command is not None:
                validate_inventory_command(parsed.command)
        except EpisodeRefusal as exc:
            record["outcome"] = "protocol_violation"
            record["protocol_violation"] = str(exc)
            problems.append(f"turn {index}: {exc}")
            stop_reason = "protocol_violation"
            break
        record.update(
            {
                "raw_decoded_text": parsed.raw_decoded_text,
                "visible_text": parsed.visible_text,
                "thinking_text": parsed.thinking_text,
                "parsed": parsed.parsed,
            }
        )
        if gold.get("parsed") != parsed.parsed:
            record["outcome"] = "oracle_parse_divergence"
            problems.append(f"turn {index} parsed action differs from oracle")
            stop_reason = "oracle_divergence"
            break

        if parsed.kind == "answer":
            answer = parsed.answer
            record["outcome"] = "answered"
            if gold.get("outcome") != "answered":
                problems.append(f"turn {index} answer outcome differs from oracle")
                stop_reason = "oracle_divergence"
            else:
                stop_reason = "answered"
            break

        if parsed.kind != "command" or parsed.command is None:
            record["outcome"] = "protocol_violation"
            violation = "model turn is neither a command nor an answer"
            record["protocol_violation"] = violation
            problems.append(f"turn {index}: {violation}")
            stop_reason = "protocol_violation"
            break
        observation = sandbox.run(parsed.command)
        executed_commands += 1
        observed = _observation_dict(observation)
        record["observation"] = observed
        record["outcome"] = "executed"
        if gold.get("outcome") != "executed" or gold.get("observation") != observed:
            problems.append(f"turn {index} sandbox observation differs from oracle")
            stop_reason = "oracle_divergence"
            break
        messages = adapter.append_observation(messages, parsed, observation.rendered())

    if policies and any(policy != policies[0] for policy in policies[1:]):
        problems.append("generation policy changed between turns")
    policy = policies[0] if policies else {}
    all_turns_exact = bool(turns) and all(
        all(
            turn.get("oracle_comparison", {}).get(key) is True
            for key in (
                "prompt_exact",
                "rendered_prompt_exact",
                "token_limit_exact",
                "generated_exact",
                "stop_reason_exact",
            )
        )
        for turn in turns
    )
    oracle_agreement = (
        all_turns_exact
        and len(turns) == len(gold_turns)
        and stop_reason == "answered"
        and answer == oracle_episode.get("answer")
    )
    task_solved = answer == str(expected_total)
    if stop_reason == "answered" and len(turns) != len(gold_turns):
        problems.append("accelerator answered at a different oracle turn count")
    if stop_reason == "answered" and executed_commands < 1:
        problems.append("episode answered without executing a model-generated command")
    if stop_reason == "answered" and not task_solved:
        problems.append("final answer is not exactly the pinned expected total")
    if stop_reason == "answered" and not oracle_agreement:
        problems.append("episode did not exactly equal the external oracle")

    if not problems and oracle_agreement and task_solved and executed_commands >= 1:
        status = "pass"
    elif stop_reason == "oracle_divergence":
        status = "diverged"
    elif stop_reason == "protocol_violation":
        status = "protocol_violation"
    else:
        status = "failed"
    return EpisodeOutcome(
        status=status,
        stop_reason=stop_reason,
        answer=answer,
        task_solved=task_solved,
        turns=turns,
        executed_command_count=executed_commands,
        oracle_agreement=oracle_agreement,
        generation_policy=policy,
        generation_policy_digest=digest_of(policy) if policy else "",
        problems=problems,
    )


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def validate_output_boundaries(
    *, checkpoint: Path, publish: Path, output: Path, force: bool
) -> None:
    if publish.is_symlink():
        raise EpisodeRefusal("--publish must not be a symbolic link")
    if output.is_symlink():
        raise EpisodeRefusal("--output must not be a symbolic link")
    checkpoint = checkpoint.resolve()
    publish = publish.resolve()
    output = output.resolve()
    if not checkpoint.is_dir():
        raise EpisodeRefusal(f"checkpoint root is not a directory: {checkpoint}")
    if _path_is_within(publish, checkpoint):
        raise EpisodeRefusal("--publish must not be the checkpoint or lie inside it")
    if _path_is_within(checkpoint, publish):
        raise EpisodeRefusal("--publish must not contain the checkpoint")
    if _path_is_within(output, checkpoint):
        raise EpisodeRefusal("--output must not be the checkpoint or lie inside it")
    if _path_is_within(output, publish):
        raise EpisodeRefusal("--output must not lie inside the deployment publication")
    if _path_is_within(publish, output):
        raise EpisodeRefusal("--publish must not lie inside the output path")
    if publish.exists() and not force:
        raise EpisodeRefusal(
            f"refusing to overwrite publication {publish}; pass --force"
        )
    if output.exists() and not force:
        raise EpisodeRefusal(f"refusing to overwrite output {output}; pass --force")
    if publish.exists():
        if not publish.is_dir():
            raise EpisodeRefusal("--publish exists but is not a directory")
        allowed = {"deployment.json", "descriptors.bin", "program.bin"}
        entries = {entry.name for entry in publish.iterdir()}
        unexpected = sorted(entries - allowed)
        if unexpected:
            raise EpisodeRefusal(
                "--force publication contains unrelated entries: "
                + ", ".join(unexpected)
            )
        for entry in publish.iterdir():
            if entry.is_symlink() or not entry.is_file():
                raise EpisodeRefusal(
                    f"--force publication member {entry.name!r} is not a file "
                    "or is a symbolic link"
                )
    if output.exists() and not output.is_file():
        raise EpisodeRefusal("--output exists but is not a regular file")


def _node_snapshots(device: Device) -> list[dict[str, int]]:
    return [
        dict(sorted(counters.snapshot().items())) for counters in device.node_counters
    ]


def _counter_scope(device: Device) -> dict[str, Any]:
    return {
        "aggregate": "cluster_total",
        "per_node": "engine_work_by_node_id",
        "node_count": device.node_count,
        "node_counters_index": "NODE_ID",
        "reconciliation": (
            "cluster total equals per-node engine work plus cluster-only LINK, "
            "STATE, control, and host bookkeeping"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-ir", type=Path, required=True)
    parser.add_argument("--backend", choices=sorted(BACKENDS), required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--workload-index", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument(
        "--expected-kernel-ir-sha256",
        required=True,
        help="external expected identity for --kernel-ir",
    )
    parser.add_argument(
        "--expected-capability-sha256",
        required=True,
        help="external expected identity for --capability",
    )
    parser.add_argument(
        "--expected-reference-sha256",
        required=True,
        help="external expected identity for --reference",
    )
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument(
        "--publish",
        type=Path,
        required=True,
        help="deployment publication, always separate from the read-only checkpoint",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        validate_output_boundaries(
            checkpoint=args.checkpoint,
            publish=args.publish,
            output=args.output,
            force=args.force,
        )
        kernel_ir_identity = expected_file_identity(
            args.kernel_ir, args.expected_kernel_ir_sha256, "kernel IR"
        )
        graph = KernelGraph.read(args.kernel_ir)
        profile = select_target_profile(graph.model_id, args.backend)
        if args.expected_kernel_ir_sha256 != profile.kernel_ir_sha256:
            raise EpisodeRefusal(
                "--expected-kernel-ir-sha256 differs from the target profile lock"
            )
        if args.expected_capability_sha256 != profile.capability_sha256:
            raise EpisodeRefusal(
                "--expected-capability-sha256 differs from the target profile lock"
            )
        capability_identity = expected_file_identity(
            args.capability, profile.capability_sha256, "capability"
        )
        reference_identity = validate_reference_identity(
            profile, args.reference, args.expected_reference_sha256
        )
        capability = Capability.from_dict(load_json(args.capability))
        validate_target_inputs(
            profile=profile,
            graph=graph,
            kernel_ir_identity=kernel_ir_identity,
            capability=capability,
            capability_identity=capability_identity,
        )
        bundle = validate_bundle(
            profile=profile,
            checkpoint=args.checkpoint,
            workload_path=args.workload,
            index_path=args.workload_index,
            reference_path=args.reference,
        )
        checkpoint_identity = validate_checkpoint_identity(profile, args.checkpoint)
        if bundle.context_capacity > int(capability.limits["max_context_positions"]):
            raise EpisodeRefusal(
                "workload session_context_capacity exceeds the selected capability"
            )
        adapter = make_adapter(
            graph.model_id, args.checkpoint, bundle.workload["metadata"]
        )
        tokenizer_inputs = adapter.tokenizer_identities()
        if tokenizer_inputs["tokenizer.json"]["sha256"] != bundle.tokenizer_sha256:
            raise EpisodeRefusal(
                "loaded tokenizer.json differs from the workload index"
            )
        output_validator = load_output_validator()
        functional_sources = source_sha256(args.backend, graph.model_id)
        workload_identity = file_identity(args.workload)
        workload_index_identity = expected_file_identity(
            args.workload_index, profile.workload_index_sha256, "workload index"
        )
    except (EpisodeRefusal, KeyError, TypeError, ValueError, OSError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    try:
        coverage = load_engines()
        lower = _resolve(BACKENDS[args.backend])
        lowering_started = time.perf_counter()
        deployment = lower(graph, capability)
        lowering_seconds = time.perf_counter() - lowering_started
        if not _integer(deployment.topology_class):
            raise EpisodeRefusal(
                "lowerer returned a non-integer deployment topology class"
            )
        deployment_checks = {
            "model_id": (deployment.model_id, profile.model_id),
            "backend": (deployment.backend, profile.deployment_backend),
            "target_id": (deployment.target_id, profile.target_id),
            "topology_class": (
                deployment.topology_class,
                profile.topology_class,
            ),
            "capability_digest": (
                deployment.capability_digest,
                capability.digest,
            ),
        }
        for label, (actual, expected) in deployment_checks.items():
            if actual != expected:
                raise EpisodeRefusal(
                    f"lowerer returned deployment {label} {actual!r}, "
                    f"expected {expected!r}"
                )
        deployment.write(args.publish)
        deployment = Deployment.read(args.publish)
        published_deployment_identity = deployment_identities(args.publish)
        verification = verify_deployment(deployment, capability)
        if not verification.admitted:
            print(
                f"refused: deployment did not admit: {verification.errors}",
                file=sys.stderr,
            )
            return 2

        numeric_backend = get_backend()
        numeric_backend.reset_executed_associations()
        device = Device(deployment, capability, root=args.checkpoint, verify=False)
        if not _integer(device.node_count, minimum=1):
            raise EpisodeRefusal("device node count is not a positive integer")
        if device.node_count != profile.node_count:
            raise EpisodeRefusal(
                f"deployment has {device.node_count} nodes; profile requires "
                f"{profile.node_count}"
            )
        driver_template = GenerationDriver(device)
        if not _integer(driver_template.vocabulary_size, minimum=1):
            raise EpisodeRefusal("generation vocabulary is not a positive integer")
        if driver_template.vocabulary_size != profile.vocabulary_size:
            raise EpisodeRefusal(
                "generation vocabulary differs from the target profile"
            )
        if tuple(driver_template.eos_token_ids) != profile.eos_token_ids:
            raise EpisodeRefusal("generation EOS set differs from the target profile")
    except (
        EpisodeRefusal,
        AttributeError,
        ImportError,
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"refused during lowering/publication: {exc}", file=sys.stderr)
        return 2

    def generate_turn(prompt: Sequence[int], limit: int) -> TurnExecution:
        before = dict(sorted(device.counters.snapshot().items()))
        nodes_before = _node_snapshots(device)
        session = device.create_session()
        driver = GenerationDriver(device)
        result = driver.generate(prompt, max_new_tokens=limit, session=session)
        after = dict(sorted(device.counters.snapshot().items()))
        nodes_after = _node_snapshots(device)
        return TurnExecution(
            result=result,
            session_id=session.session_id,
            generation_policy=dict(driver.policy),
            counters_before=before,
            counters_after=after,
            node_counters_before=nodes_before,
            node_counters_after=nodes_after,
        )

    started = time.perf_counter()
    try:
        with Sandbox(bundle.workload["metadata"]["sandbox_files"]) as sandbox:
            outcome = run_episode(
                adapter=adapter,
                workload=bundle.workload,
                oracle_episode=bundle.oracle_episode,
                expected_total=bundle.expected_total,
                max_turns=bundle.max_turns,
                context_capacity=bundle.context_capacity,
                vocabulary_size=driver_template.vocabulary_size,
                eos_token_ids=driver_template.eos_token_ids,
                generate_turn=generate_turn,
                sandbox=sandbox,
            )
    except (
        EpisodeRefusal,
        AgentProtocolError,
        DriverError,
        AttributeError,
        OSError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"refused during episode: {exc}", file=sys.stderr)
        return 3
    wall_seconds = time.perf_counter() - started

    try:
        require_unchanged_file(args.kernel_ir, kernel_ir_identity, "kernel IR")
        require_unchanged_file(args.capability, capability_identity, "capability")
        require_unchanged_file(args.workload, workload_identity, "workload")
        require_unchanged_file(
            args.workload_index, workload_index_identity, "workload index"
        )
        require_unchanged_file(args.reference, reference_identity, "reference oracle")
        if adapter.tokenizer_identities() != tokenizer_inputs:
            raise EpisodeRefusal(
                "tokenizer inputs changed during lowering or execution"
            )
        if (
            validate_checkpoint_identity(profile, args.checkpoint)
            != checkpoint_identity
        ):
            raise EpisodeRefusal("checkpoint identity changed during execution")
        if deployment_identities(args.publish) != published_deployment_identity:
            raise EpisodeRefusal("published deployment changed during execution")
        if source_sha256(args.backend, graph.model_id) != functional_sources:
            raise EpisodeRefusal("functional source boundary changed during execution")
    except (EpisodeRefusal, OSError, TypeError, ValueError) as exc:
        print(f"refused after execution: {exc}", file=sys.stderr)
        return 3

    inputs = {
        "kernel_ir": dict(kernel_ir_identity),
        "capability": dict(capability_identity),
        "workload": {
            **workload_identity,
            "declared_workload_digest": bundle.workload["digest"],
            "prompt_token_ids_sha256": digest_of(bundle.workload["token_ids"]),
        },
        "workload_index": dict(workload_index_identity),
        "reference": dict(reference_identity),
        "tokenizer_files": tokenizer_inputs,
        "checkpoint_root": {
            "path": _record_path(args.checkpoint),
            "kind": "read_only_directory",
            "content_binding": "authenticated deployment object segment SHA-256 values",
            "deployment_digest_binding": deployment.deployment_digest.hex(),
            "identity": checkpoint_identity,
        },
        "published_deployment": published_deployment_identity,
    }
    body = {
        "schema": SCHEMA,
        "status": outcome.status,
        "evidence_class": EVIDENCE_CLASS,
        "not_a_claim": list(NOT_A_CLAIMS),
        "tool": "tools/run_abi3_agent_episode.py",
        "target_profile": {
            "profile_id": profile.profile_id,
            "expected_kernel_ir_sha256": profile.kernel_ir_sha256,
            "expected_capability_sha256": profile.capability_sha256,
            "expected_reference_sha256": args.expected_reference_sha256,
        },
        "backend": args.backend,
        "model": {
            "model_id": graph.model_id,
            "graph_id": graph.graph_id,
            "numeric_profile": graph.to_dict().get("numeric_profile", ""),
        },
        "target": {
            "target_id": deployment.target_id,
            "backend": deployment.backend,
            "topology_class": deployment.topology_class,
            "node_count": device.node_count,
            "capability": _record_path(args.capability),
            "capability_digest": capability.digest,
            "deployment_digest": deployment.deployment_digest.hex(),
            "technology_view": capability.technology_view,
        },
        "workload": {
            "workload_id": bundle.workload["workload_id"],
            "workload_digest": bundle.workload["digest"],
            "kind": bundle.workload["kind"],
            "prompt_token_ids": bundle.workload["token_ids"],
            "prompt_token_count": bundle.workload["prompt_token_count"],
            "rendered_text_sha256": bundle.workload["rendered_text_sha256"],
            "max_new_tokens_per_turn": bundle.workload["max_new_tokens"],
            "max_turns": bundle.max_turns,
            "session_context_capacity": bundle.context_capacity,
            "tokenizer_sha256": bundle.tokenizer_sha256,
        },
        "command_policy": command_policy_evidence(),
        "generation_policy": outcome.generation_policy,
        "generation_policy_digest": outcome.generation_policy_digest,
        "verification": verification.to_dict(),
        "engine_coverage": {
            "implemented_count": coverage["implemented_count"],
            "missing_count": coverage["missing_count"],
            "missing": list(coverage["missing"]),
        },
        "implementation_identity": dict(numeric_backend.implementation_identity()),
        "executed_association": numeric_backend.executed_association_manifest(),
        "inputs": inputs,
        "source_sha256": functional_sources,
        "reference": {
            "artifact": _record_path(args.reference),
            "artifact_sha256": reference_identity["sha256"],
            "schema": bundle.oracle["schema"],
            "evidence_class": "external_reference_comparator",
            "workload_digest": bundle.oracle_result["workload_digest"],
            "oracle_turn_count": bundle.oracle_episode["turn_count"],
            "note": (
                "The external oracle supplied no activation, weight, command, "
                "observation, or token to the accelerator path. It is used only "
                "for exact post-generation comparison."
            ),
        },
        "oracle_agreement": outcome.oracle_agreement,
        "expected_total": bundle.expected_total,
        "answer": outcome.answer,
        "task_solved": outcome.task_solved,
        "stop_reason": outcome.stop_reason,
        "turns": outcome.turns,
        "turn_count": len(outcome.turns),
        "executed_command_count": outcome.executed_command_count,
        "problems": outcome.problems,
        "counters": dict(sorted(device.counters.snapshot().items())),
        "counter_scope": _counter_scope(device),
        "node_counters": _node_snapshots(device),
        "lowering_seconds": round(lowering_seconds, 3),
        "wall_seconds": round(wall_seconds, 3),
        "note": (
            "Every executed command was decoded by the accelerator, parsed "
            "without repair, run in the frozen sandbox, and fed back through "
            "the model-specific official renderer. Pass additionally requires "
            "exact oracle prompts, tokens, terminal reasons, parses, observations, "
            "turn count, and exact final answer."
        ),
    }
    try:
        write_validated_output(
            body,
            output=args.output,
            validator=output_validator,
            expected_source_sha256=functional_sources,
        )
    except (EpisodeRefusal, OSError, TypeError, ValueError) as exc:
        print(f"refused while writing output: {exc}", file=sys.stderr)
        return 5
    print(
        f"wrote {args.output}: status={outcome.status}, turns={len(outcome.turns)}, "
        f"executed={outcome.executed_command_count}, seconds={wall_seconds:.1f}",
        flush=True,
    )
    return 0 if outcome.status == "pass" else 4


if __name__ == "__main__":
    raise SystemExit(main())
