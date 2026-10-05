#!/usr/bin/env python3
"""Score an execution record against a reference oracle, without touching it.

An execution record says what the accelerator produced.  Whether that was
*correct* is a separate judgement, and this tool makes it separately so that
the verdict can never be confused with the run that produced the tokens.

Why it exists as its own step.  ``tools/run_abi3_campaign.py`` used to write
``status: pass`` whenever a run neither crashed nor emitted an illegitimate
token, with no comparison against anything.  That reports "the script finished"
in a field a reader will take to mean "the tokens are right".  The distinction
is not hypothetical here: a released vendor kernel in this same program decoded
fluent, well-formed, semantically empty text, and every liveness check it had
passed.  The campaign runner now refuses to say ``pass`` without a reference;
this tool scores records written before that change, and re-scores any record
whose oracle arrived later than the run.

The verdict is written beside the execution record, never into it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import canonical_json, digest_of  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    body = json.loads(args.execution.read_text())
    record = body["record"]
    workload_id = record["workload"]["workload_id"]
    got = [int(t) for t in record["generated_token_ids"]]

    reference_body = json.loads(args.reference.read_text())
    results = reference_body.get("results", {})
    if workload_id not in results:
        raise SystemExit(
            f"reference {args.reference} holds no result for {workload_id!r}; "
            f"it has {sorted(results)}"
        )
    gold = [int(t) for t in results[workload_id]["generated_token_ids"]]

    divergence = next(
        (i for i, (a, b) in enumerate(zip(got, gold)) if a != b), None
    )
    # Both sides must be non-empty.  Two empty lists compare equal and
    # reporting that as agreement is a vacuous pass, which this repository has
    # produced once already.
    if not got:
        verdict, reason = "no_tokens", "the run produced no tokens"
    elif not gold:
        verdict, reason = "no_reference_tokens", "the oracle produced no tokens"
    elif len(got) > len(gold):
        verdict, reason = (
            "reference_too_short",
            f"the run produced {len(got)} tokens and the oracle only {len(gold)}",
        )
    elif got == gold[: len(got)]:
        verdict, reason = (
            "agree",
            f"all {len(got)} tokens match the oracle"
            + ("" if len(got) == len(gold) else f" (a prefix of {len(gold)})"),
        )
    else:
        verdict, reason = (
            "diverge",
            f"first difference at index {divergence}: "
            f"produced {got[divergence]}, oracle {gold[divergence]}",
        )

    out = {
        "schema": "opentallas.abi3.reference_comparison.v1",
        "verdict": verdict,
        "reason": reason,
        "workload_id": workload_id,
        "execution": {
            "path": str(args.execution),
            "recorded_status": body.get("status"),
            "stop_reason": record.get("stop_reason"),
            "token_count": len(got),
            "implementation_identity": record.get("implementation_identity"),
        },
        "reference": {
            "path": str(args.reference),
            "token_count": len(gold),
            "digest": digest_of(results[workload_id]),
        },
        "first_divergence_index": divergence,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(out))
    print(f"{workload_id}: {verdict} - {reason}")
    print(f"wrote {args.output}")
    return 0 if verdict == "agree" else 1


if __name__ == "__main__":
    raise SystemExit(main())
