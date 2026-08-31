#!/usr/bin/env python3
"""End-to-end ABI 3.0 campaign: neutral IR -> deployment -> real tokens.

This is the integration point where the four targets meet. It performs the same
sequence for every one of them, which is what makes their results comparable:

    neutral Kernel IR v3
        -> backend lowering to an ABI 3.0 deployment
        -> independent verification
        -> functional device
        -> host driver: prefill, decode, first EOS
        -> evidence record with an explicit evidence class

The backend is selected by name and nothing else changes. A target is a set of
descriptors, not a code path.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402
from runtime.abi3.constants import TopologyClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.driver import GenerationDriver, validate_token_ids  # noqa: E402
from runtime.evidence import (  # noqa: E402
    EvidenceClass,
    ExecutionRecord,
    TargetIdentity,
    WorkloadIdentity,
    check_token_legitimacy,
)
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

#: Backend name -> "module:function" producing a Deployment.
BACKENDS = {
    "hbm_sram": "compiler.backends.hbm_sram.lower:lower_to_abi3",
    "rom_qwen3": "compiler.backends.rom.qwen3:lower_to_abi3",
    "rom_deepseek_v4": "compiler.backends.rom.deepseek_v4:lower_to_abi3",
}


def resolve(spec: str):
    module_name, _, attribute = spec.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, attribute)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-ir", type=Path, required=True)
    parser.add_argument("--backend", choices=sorted(BACKENDS), required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--deployment-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument(
        "--reference",
        type=Path,
        default=None,
        help=(
            "reference-oracle result file holding this workload's gold token "
            "ids.  Without it a run cannot be reported as a pass: executing "
            "without crashing is not evidence of a correct token."
        ),
    )
    parser.add_argument(
        "--topology",
        type=int,
        default=None,
        choices=[t.value for t in TopologyClass],
        help=(
            "topology class as its ABI value ("
            + ", ".join(f"{t.value}={t.name}" for t in TopologyClass)
            + ").  Omit to use the capability's own topology_class, which is "
            "normally what you want -- the capability already names it."
        ),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help=(
            "checkpoint root that relative object-source paths resolve "
            "against.  A backend may name its weight segments by shard file "
            "name rather than absolute path -- the DeepSeek ROM backend does "
            "-- and such a deployment cannot be activated without this.  "
            "Omit it when every object path is absolute."
        ),
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--trace", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    coverage = load_engines()
    print(
        f"engines: {coverage['implemented_count']} implemented, "
        f"{coverage['missing_count']} missing"
    )
    if coverage["unavailable"]:
        print(f"  unavailable modules: {coverage['unavailable']}")

    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    workload = json.loads(args.workload.read_text())

    # -- lower --------------------------------------------------------
    from compiler.ir.v3.kernel_ir import KernelGraph

    print(f"loading neutral IR from {args.kernel_ir} ...", flush=True)
    # KernelGraph.read re-derives graph_id, so a document edited after
    # publication is rejected here rather than silently compiled.
    graph = KernelGraph.read(args.kernel_ir)
    graph_body = graph.to_dict()
    graph_id = graph.graph_id
    lower = resolve(BACKENDS[args.backend])
    started = time.perf_counter()
    kwargs: dict[str, Any] = {}
    if args.topology:
        kwargs["topology"] = args.topology
    deployment = lower(graph, capability, **kwargs)
    lowering_seconds = time.perf_counter() - started
    print(
        f"lowered in {lowering_seconds:.1f}s: "
        f"{len(deployment.table)} descriptors, "
        f"{len(deployment.program)} program bytes"
    )

    root = args.deployment_root
    if root is not None:
        deployment.write(root)
        deployment = Deployment.read(root)
        print(f"published deployment to {root}")

    # -- verify -------------------------------------------------------
    report = verify_deployment(deployment, capability)
    print(
        f"verification: admitted={report.admitted} "
        f"instructions={report.instruction_count} "
        f"work={report.proved_retired_work}/{report.declared_retired_work} "
        f"loop_depth={report.loop_depth}"
    )
    for error in report.errors:
        print(f"  ERROR {error}")
    if not report.admitted:
        _write(
            args.output,
            {
                "schema": "opentallas.abi3.campaign.v1",
                "status": "rejected_at_admission",
                "verification": report.to_dict(),
                "engine_coverage": coverage,
            },
        )
        return 2

    # -- execute ------------------------------------------------------
    device = Device(
        deployment,
        capability,
        root=args.snapshot,
        verify=False,
        trace=args.trace,
    )
    driver = GenerationDriver(device)
    prompt = workload["token_ids"]
    limit = args.max_new_tokens or workload["max_new_tokens"]
    print(
        f"executing {workload['workload_id']}: {len(prompt)} prompt tokens, "
        f"max_new={limit} ...",
        flush=True,
    )
    result = driver.generate(prompt, max_new_tokens=limit)
    print(
        f"produced {len(result.generated_token_ids)} tokens in "
        f"{result.wall_seconds:.1f}s, stop={result.stop_reason}"
    )
    if result.failure:
        print(f"  FAILURE {result.failure}")

    legitimacy = check_token_legitimacy(
        result.generated_token_ids,
        vocabulary_size=driver.vocabulary_size,
        eos_token_ids=driver.eos_token_ids,
        stop_reason=result.stop_reason,
    )
    legitimacy += validate_token_ids(
        result.generated_token_ids, driver.vocabulary_size
    )

    reference = _load_reference(args.reference, workload["workload_id"])
    got = list(result.generated_token_ids)
    agreement, divergence = _compare(got, reference)
    if reference is None:
        print(
            "  NO REFERENCE: this run is recorded as executed_unverified.  "
            "Pass --reference to compare against the oracle."
        )
    else:
        print(
            f"reference: {len(reference)} gold tokens, agreement={agreement}, "
            f"first divergence={divergence}"
        )

    record = ExecutionRecord(
        evidence_class=EvidenceClass.FUNCTIONAL,
        workload=WorkloadIdentity(
            model_id=graph_body.get("model_id", ""),
            workload_id=workload["workload_id"],
            workload_digest=workload["digest"],
            prompt_token_count=len(prompt),
            max_new_tokens=limit,
            generation_policy_digest=digest_of(driver.policy),
            generation_policy=dict(driver.policy),
            numeric_profile=graph_body.get("numeric_profile", ""),
            graph_id=graph_id,
            tokenizer_sha256=_tokenizer_digest(workload, args.reference),
        ),
        target=TargetIdentity(
            target_id=deployment.target_id,
            backend=deployment.backend,
            topology_class=deployment.topology_class,
            node_count=1,
            capability_digest=capability.digest,
            deployment_digest=deployment.deployment_digest.hex(),
            technology_view=capability.technology_view,
        ),
        generated_token_ids=result.generated_token_ids,
        stop_reason=result.stop_reason,
        counters=result.counters,
        implementation_identity=_implementation_identity(),
        notes={
            "lowering_seconds": round(lowering_seconds, 3),
            "verification": report.to_dict(),
            "engine_coverage": {
                "implemented_count": coverage["implemented_count"],
                "missing_count": coverage["missing_count"],
            },
            "token_legitimacy_problems": legitimacy,
            "per_step": result.per_step,
            "reference_token_ids": reference,
            "reference_agreement": agreement,
            "first_divergence_index": divergence,
        },
        failure=result.failure,
    )
    status = _status(result.failure, legitimacy, reference, agreement)
    _write(
        args.output,
        {
            "schema": "opentallas.abi3.campaign.v1",
            "status": status,
            "record": record.to_dict(),
        },
    )
    print(f"wrote {args.output} (status {status})")
    if legitimacy:
        for problem in legitimacy:
            print(f"  TOKEN LEGITIMACY {problem}")
        return 3
    if result.failure:
        return 4
    return 0 if status == "pass" else 5


def _tokenizer_digest(workload: dict[str, Any], reference: Path | None) -> str:
    """The tokenizer these token ids came from.

    Two evidence writers sourced this differently -- one from the workload's
    metadata, which the workload files do not carry, and one from the reference
    oracle, which does -- so one side of a comparison recorded the digest and
    the other recorded an empty string, and the comparison gate refused the pair
    for a reason that was really a bookkeeping difference.  The workload is the
    right source and the oracle is the fallback until the workload files carry
    it.
    """
    stated = workload.get("metadata", {}).get("tokenizer_sha256", "")
    if stated or reference is None:
        return str(stated)
    try:
        return str(json.loads(reference.read_text()).get("tokenizer_sha256", ""))
    except Exception:  # a missing oracle must not fail the run
        return ""


def _status(
    failure: Any,
    legitimacy: list[Any],
    reference: list[int] | None,
    agreement: bool | None,
) -> str:
    """The engineering result, which is not the same as "the script finished".

    ``pass`` is reserved for a run whose tokens were compared against a
    reference oracle and matched.  A run with no reference is
    ``executed_unverified`` however healthy it looks: the device produced
    tokens and nothing checked them, and a fluent-but-wrong decode is exactly
    the failure this program has already hit once, in a vendor kernel that
    produced well-formed and semantically empty text.
    """
    if failure or legitimacy:
        return "failed"
    if reference is None:
        return "executed_unverified"
    if not reference:
        return "reference_empty"
    return "pass" if agreement else "diverged"


def _load_reference(path: Path | None, workload_id: str) -> list[int] | None:
    """Gold token ids for this workload, or None if no reference was named."""
    if path is None:
        return None
    body = json.loads(path.read_text())
    results = body.get("results", {})
    if workload_id not in results:
        raise SystemExit(
            f"reference {path} holds no result for workload {workload_id!r}; "
            f"it has {sorted(results)}"
        )
    return [int(t) for t in results[workload_id]["generated_token_ids"]]


def _compare(
    got: list[int], reference: list[int] | None
) -> tuple[bool | None, int | None]:
    """Prefix agreement and the first differing index.

    A run stopped by a token cap is a prefix of the oracle's sequence, so the
    comparison is against ``reference[:len(got)]``.  Both sides must be
    non-empty: two empty lists compare equal, and reporting that as agreement
    is a vacuous pass this repository has already produced once.
    """
    if reference is None:
        return None, None
    divergence = next(
        (i for i, (a, b) in enumerate(zip(got, reference)) if a != b), None
    )
    if not got or not reference:
        return False, divergence
    return got == reference[: len(got)], divergence


def _implementation_identity() -> dict[str, Any]:
    """What executed the blocked contract, so the result is reproducible."""
    try:
        from runtime.sim.backend import get_backend

        return dict(get_backend().implementation_identity())
    except Exception as exc:  # a missing backend must be visible, not silent
        return {"unavailable": f"{type(exc).__name__}: {exc}"}


def _write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


if __name__ == "__main__":
    raise SystemExit(main())
