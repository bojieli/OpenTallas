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
import json
import sys
from pathlib import Path

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


def load_record(path: Path) -> ExecutionRecord:
    """Rebuild an ExecutionRecord from a campaign, cycle, or token report.

    Campaign records carry the canonical identity objects directly.  Governed
    token captures retain a richer execution schema: model identity is in the
    top-level ``model`` object and workload/target objects include diagnostic
    fields that are not constructor arguments.  Read the common identity
    explicitly so adding evidence fields never makes an otherwise comparable
    capture unreadable.
    """
    body = json.loads(path.read_text())
    record = body.get("record", body)
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True, help="ROM target report")
    parser.add_argument("--hbm", type=Path, required=True, help="HBM target report")
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

    rom = load_record(args.rom)
    hbm = load_record(args.hbm)

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
        )
    except ComparisonError as exc:
        print(f"comparison refused: {exc}", file=sys.stderr)
        return 3

    body["sources"] = {"rom": str(args.rom), "hbm": str(args.hbm)}
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
            print(f"    {name:38s} rom={delta['left']:<14} hbm={delta['right']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
