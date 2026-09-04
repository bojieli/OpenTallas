#!/usr/bin/env python3
"""Build a governed same-model ROM-versus-HBM comparison.

Only same-model pairs are compared: Qwen ROM against Qwen HBM, and the DeepSeek
ROM wafer against the DeepSeek 32-node HBM cluster. The gate in
``runtime/evidence.py`` refuses a pair that does not share a prompt, a numeric
profile, a generation policy or a technology view, refuses to mix evidence
boundaries, and refuses outright when the two targets produced different tokens
-- a performance comparison may not precede correct execution.

Topology cost is reported on both sides and never normalised away. A 32-node
cluster and a wafer are different physical objects; making that visible is the
comparison's job.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.evidence import (  # noqa: E402
    ComparisonError,
    EvidenceClass,
    ExecutionRecord,
    Provenance,
    Quantity,
    TargetIdentity,
    WorkloadIdentity,
    build_comparison,
    check_comparable,
)


COMPARISON_SOURCE_PATHS = (
    "runtime/abi3/capability.py",
    "runtime/abi3/crc.py",
    "runtime/evidence.py",
    "tools/build_comparison_report.py",
)

REQUIRED_EXECUTION_SOURCE_PATHS = (
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
    "runtime/sim/backend.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/memory.py",
    "runtime/sim/engines/__init__.py",
    "runtime/sim/engines/attention.py",
    "runtime/sim/engines/deepseek_vector.py",
    "runtime/sim/engines/dma.py",
    "runtime/sim/engines/link.py",
    "runtime/sim/engines/reduction.py",
    "runtime/sim/engines/route.py",
    "runtime/sim/engines/selection.py",
    "runtime/sim/engines/tensor.py",
    "runtime/sim/engines/vector.py",
)

BACKEND_EXECUTION_SOURCE_PATHS = {
    "hbm_sram": (
        "compiler/backends/hbm_sram/lower.py",
        "compiler/backends/hbm_sram/plan.py",
    ),
    "rom_qwen3": (
        "compiler/backends/rom/qwen3.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
    "rom_deepseek_v4": (
        "compiler/backends/rom/deepseek_v4.py",
        "compiler/backends/rom/common/image.py",
        "compiler/backends/rom/common/program.py",
    ),
}


class InputRefusal(ValueError):
    """A purported execution artifact is not promotable into a comparison."""


@dataclass(frozen=True, slots=True)
class GovernedInput:
    path: Path
    artifact_sha256: str
    source_sha256: Mapping[str, str]
    record: ExecutionRecord

    def identity(self) -> dict[str, str]:
        return {"path": str(self.path), "sha256": self.artifact_sha256}


def _execution_record(body: Mapping[str, Any]) -> ExecutionRecord:
    """Normalize the execution portion of a supported evidence document."""

    record = body.get("record", body)
    if not isinstance(record, Mapping):
        raise ValueError("execution record is not an object")
    workload = record["workload"]
    model = record.get("model", {})
    target = record["target"]
    return ExecutionRecord(
        evidence_class=EvidenceClass(record["evidence_class"]),
        workload=WorkloadIdentity(
            model_id=str(workload.get("model_id", model.get("model_id", ""))),
            workload_id=str(workload["workload_id"]),
            workload_digest=str(workload["workload_digest"]),
            prompt_token_count=int(workload["prompt_token_count"]),
            max_new_tokens=int(workload["max_new_tokens"]),
            generation_policy_digest=str(
                workload.get(
                    "generation_policy_digest",
                    record.get("generation_policy_digest", ""),
                )
            ),
            numeric_profile=str(
                workload.get("numeric_profile", model.get("numeric_profile", ""))
            ),
            graph_id=str(workload.get("graph_id", model.get("graph_id", ""))),
            tokenizer_sha256=str(workload.get("tokenizer_sha256", "")),
            generation_policy=workload.get(
                "generation_policy", record.get("generation_policy", {})
            ),
        ),
        target=TargetIdentity(
            target_id=str(target["target_id"]),
            backend=str(target["backend"]),
            topology_class=int(target["topology_class"]),
            node_count=int(target["node_count"]),
            capability_digest=str(target["capability_digest"]),
            deployment_digest=str(target["deployment_digest"]),
            technology_view=str(target.get("technology_view", "uncharacterized")),
        ),
        generated_token_ids=tuple(record["generated_token_ids"]),
        stop_reason=record["stop_reason"],
        counters=record.get("counters", {}),
        quantities=tuple(
            Quantity(
                name=q["name"],
                value=q["value"],
                unit=q["unit"],
                provenance=Provenance(q["provenance"]),
                source=q.get("source", ""),
            )
            for q in record.get("quantities", [])
        ),
        notes=record.get("notes", {}),
        failure=record.get("failure"),
        implementation_identity=record.get("implementation_identity", {}),
    )


def load_record(path: Path) -> ExecutionRecord:
    """Rebuild an ExecutionRecord from a campaign, cycle, or token report.

    Campaign records carry the canonical identity objects directly.  Governed
    token captures retain a richer execution schema: model identity is in the
    top-level ``model`` object and workload/target objects include diagnostic
    fields that are not constructor arguments.  Read the common identity
    explicitly so adding evidence fields never makes an otherwise comparable
    capture unreadable.
    """
    return _execution_record(json.loads(path.read_text()))


def _source_lock_problems(source_sha256: object) -> list[str]:
    if not isinstance(source_sha256, Mapping) or not source_sha256:
        return ["record has no non-empty source_sha256 map"]

    problems: list[str] = []
    repo = REPO.resolve()
    for relative, expected in sorted(source_sha256.items(), key=lambda item: str(item[0])):
        if not isinstance(relative, str) or not relative:
            problems.append("record source path is not a non-empty string")
            continue
        candidate = Path(relative)
        source = (REPO / candidate).resolve()
        try:
            source.relative_to(repo)
        except ValueError:
            problems.append(f"record source path escapes the repository: {relative}")
            continue
        if candidate.is_absolute() or relative != candidate.as_posix():
            problems.append(
                f"record source path is not normalized repository-relative: "
                f"{relative}"
            )
            continue
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or any(character not in "0123456789abcdef" for character in expected)
        ):
            problems.append(f"record source {relative} has no valid SHA-256")
        elif not source.is_file():
            problems.append(f"record source {relative} does not exist")
        elif hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            problems.append(
                f"record source {relative} does not match the current source"
            )
    for relative in REQUIRED_EXECUTION_SOURCE_PATHS:
        if relative not in source_sha256:
            problems.append(f"record does not bind required source {relative}")
    return problems


def _governance_problems(body: Mapping[str, Any]) -> list[str]:
    record = body.get("record", body)
    if not isinstance(record, Mapping):
        return ["execution record is not an object"]

    problems: list[str] = []
    status = body.get("status", record.get("status"))
    if status != "pass":
        problems.append(f"status is {status!r}, expected 'pass'")

    verification = record.get("verification", body.get("verification"))
    if not isinstance(verification, Mapping) or verification.get("admitted") is not True:
        problems.append("verification.admitted is not true")

    oracle = record.get("oracle", body.get("oracle"))
    if not isinstance(oracle, Mapping) or oracle.get("agreement") is not True:
        problems.append("oracle.agreement is not true")

    legitimacy = record.get(
        "token_legitimacy_problems", body.get("token_legitimacy_problems")
    )
    if not isinstance(legitimacy, list):
        problems.append("token_legitimacy_problems is not a recorded list")
    elif legitimacy:
        problems.append(
            "token legitimacy problems are present: "
            + "; ".join(str(problem) for problem in legitimacy)
        )

    if record.get("failure") is not None:
        problems.append("execution failure is not null")

    workload = record.get("workload")
    tokenizer_sha256 = (
        workload.get("tokenizer_sha256") if isinstance(workload, Mapping) else None
    )
    if (
        not isinstance(tokenizer_sha256, str)
        or len(tokenizer_sha256) != 64
        or any(
            character not in "0123456789abcdef"
            for character in tokenizer_sha256
        )
    ):
        problems.append("workload.tokenizer_sha256 is not a valid SHA-256")

    source_sha256 = record.get("source_sha256", body.get("source_sha256"))
    problems.extend(_source_lock_problems(source_sha256))
    backend = record.get("backend", body.get("backend"))
    backend_sources = BACKEND_EXECUTION_SOURCE_PATHS.get(str(backend))
    if backend_sources is None:
        problems.append(f"record backend {backend!r} has no governed source boundary")
    elif isinstance(source_sha256, Mapping):
        for relative in backend_sources:
            if relative not in source_sha256:
                problems.append(
                    f"record does not bind backend source {relative}"
                )
    return problems


def load_governed_input(path: Path) -> GovernedInput:
    """Load an execution only after every promotion precondition is proved."""

    payload = path.read_bytes()
    body = json.loads(payload)
    if not isinstance(body, Mapping):
        raise InputRefusal(f"{path}: document is not an object")
    problems = _governance_problems(body)
    if problems:
        raise InputRefusal(f"{path}:\n  " + "\n  ".join(problems))
    record_body = body.get("record", body)
    source_sha256 = record_body.get(
        "source_sha256", body.get("source_sha256", {})
    )
    return GovernedInput(
        path=path,
        artifact_sha256=hashlib.sha256(payload).hexdigest(),
        source_sha256=dict(source_sha256),
        record=_execution_record(body),
    )


def _comparison_source_sha256() -> dict[str, str]:
    return {
        relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
        for relative in COMPARISON_SOURCE_PATHS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True, help="ROM target report")
    side = parser.add_mutually_exclusive_group(required=True)
    side.add_argument("--hbm", type=Path, help="HBM target report")
    side.add_argument(
        "--rom-array",
        type=Path,
        help=(
            "second immutable-ROM target report, for the packaging comparison "
            "(the wafer against the 32-node array) rather than the "
            "storage-class one"
        ),
    )
    parser.add_argument("--comparison-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--allow-token-divergence",
        action="store_true",
        help=(
            "Emit a divergence analysis instead of refusing. Produces a report "
            "explicitly marked as NOT a performance comparison."
        ),
    )
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    right_role = "hbm" if args.hbm is not None else "rom_array"
    right_path = args.hbm if args.hbm is not None else args.rom_array
    try:
        rom_input = load_governed_input(args.rom)
        hbm_input = load_governed_input(right_path)
    except (InputRefusal, KeyError, OSError, TypeError, ValueError) as exc:
        print(f"comparison refused: {exc}", file=sys.stderr)
        return 2

    rom = rom_input.record
    hbm = hbm_input.record

    problems = check_comparable(rom, hbm)
    if problems:
        print("comparison refused:", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        return 2

    try:
        body = build_comparison(
            rom,
            hbm,
            comparison_id=args.comparison_id,
            require_identical_tokens=not args.allow_token_divergence,
            roles=("rom", right_role),
        )
    except ComparisonError as exc:
        print(f"comparison refused: {exc}", file=sys.stderr)
        return 3

    body["sources"] = {
        "rom": rom_input.identity(),
        right_role: hbm_input.identity(),
    }
    body["source_sha256"] = _comparison_source_sha256()
    if args.allow_token_divergence and not body["token_agreement"]["identical"]:
        body["claim_boundary"]["performance_comparison"] = False
        body["claim_boundary"]["note"] = (
            "The two targets produced different token sequences, so this is a "
            "divergence analysis and not a performance comparison. No latency, "
            "throughput or energy figure in it may be quoted as a result."
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))
    print(f"wrote {args.output}")
    print(f"  tokens identical: {body['token_agreement']['identical']}")
    print(f"  evidence class:   {body['evidence_class']}")
    print(f"  depends on assumption: {body['depends_on_assumption']}")
    deltas = body["counter_deltas"]
    if deltas:
        print(f"  counters differing: {len(deltas)}")
        for name, delta in list(sorted(deltas.items()))[:12]:
            print(
                f"    {name:38s} rom={delta['left']:<14} "
                f"{right_role}={delta['right']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
