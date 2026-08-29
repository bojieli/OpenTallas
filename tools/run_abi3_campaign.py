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
    parser.add_argument("--topology", default=None)
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
    device = Device(deployment, capability, verify=False, trace=args.trace)
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

    record = ExecutionRecord(
        evidence_class=EvidenceClass.FUNCTIONAL,
        workload=WorkloadIdentity(
            model_id=graph_body.get("model_id", ""),
            workload_id=workload["workload_id"],
            workload_digest=workload["digest"],
            prompt_token_count=len(prompt),
            max_new_tokens=limit,
            generation_policy_digest=digest_of(driver.policy),
            numeric_profile=graph_body.get("numeric_profile", ""),
            graph_id=graph_id,
            tokenizer_sha256=workload.get("metadata", {}).get("tokenizer_sha256", ""),
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
        notes={
            "lowering_seconds": round(lowering_seconds, 3),
            "verification": report.to_dict(),
            "engine_coverage": {
                "implemented_count": coverage["implemented_count"],
                "missing_count": coverage["missing_count"],
            },
            "token_legitimacy_problems": legitimacy,
            "per_step": result.per_step,
        },
        failure=result.failure,
    )
    _write(
        args.output,
        {
            "schema": "opentallas.abi3.campaign.v1",
            "status": "failed" if (result.failure or legitimacy) else "pass",
            "record": record.to_dict(),
        },
    )
    print(f"wrote {args.output}")
    if legitimacy:
        for problem in legitimacy:
            print(f"  TOKEN LEGITIMACY {problem}")
        return 3
    return 0 if not result.failure else 4


def _write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


if __name__ == "__main__":
    raise SystemExit(main())
