#!/usr/bin/env python3
"""Check a model profile's KV traffic against a reference engine that ran it.

The KV term decides the ROM argument at long context, and for a sparse model it
is the hardest part of a profile to get right: the read set is not the context,
it is whatever the model's own routing selected. Reading the released
implementation and writing down what it *appears* to do is not the same as
running it and counting, and this tool exists because those two disagreed.

It compares three things per rung, because they fail differently:

  positions   the (layer, position) pairs each attention kind visited, which
              catches a wrong sparsity structure -- a window modelled where a
              compressed full-context scan belongs, or the reverse
  entry size  bytes per visited pair, which catches a KV row read at the wrong
              precision or width
  total       the product, which is what a roofline actually divides by
              bandwidth

A structural error and an entry-size error look identical in the total and have
completely different fixes, so the total alone is not a diagnosis.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "src"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import kv_traffic  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402

#: The KV term carries no scales or index tables riding along, so unlike weight
#: traffic it is expected to agree closely.  A rung outside this is a defect in
#: the profile, not a tolerance to widen.
TOLERANCE = 0.01


def _measured_rungs(body: dict[str, Any]) -> list[dict[str, Any]]:
    rungs = []
    for name, rung in sorted(body.get("results", {}).items()):
        steps = (rung.get("kv_measurement") or {}).get("decode_steps") or []
        if not steps:
            continue
        step = steps[0]
        by_kind: dict[str, dict[str, float]] = defaultdict(
            lambda: {"layers": 0, "pairs": 0, "bytes": 0}
        )
        for layer in step.get("per_layer", {}).values():
            entry = by_kind[layer["kind"]]
            entry["layers"] += 1
            entry["pairs"] += layer.get("main_pairs", 0) + layer.get("index_pairs", 0)
            entry["bytes"] += layer.get("main_bytes", 0) + layer.get("index_bytes", 0)
        rungs.append(
            {
                "workload_id": name,
                "context_tokens": int(step["context_tokens"]),
                "measured_bytes": int(step["measured"]["total_kv_bytes_read"]),
                "by_kind": {k: dict(v) for k, v in sorted(by_kind.items())},
            }
        )
    return rungs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--oracle", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force")
        return 1

    model = ModelProfile.load(args.model)
    rungs = _measured_rungs(json.loads(args.oracle.read_text()))
    if not rungs:
        print("the oracle artifact carries no KV measurement; nothing to check")
        return 1

    results, problems = [], []
    for rung in rungs:
        predicted = kv_traffic(model, rung["context_tokens"]).read_bytes
        ratio = rung["measured_bytes"] / predicted if predicted else 0.0
        rung["predicted_bytes"] = predicted
        rung["ratio"] = ratio
        rung["bytes_per_pair_by_kind"] = {
            kind: (v["bytes"] / v["pairs"] if v["pairs"] else 0.0)
            for kind, v in rung["by_kind"].items()
        }
        if abs(ratio - 1.0) > TOLERANCE:
            problems.append(
                f"{rung['workload_id']} at {rung['context_tokens']:,} tokens: the profile "
                f"predicts {predicted:,.0f} KV bytes per step where the engine read "
                f"{rung['measured_bytes']:,} ({ratio:.3f}x)"
            )
        results.append(rung)

    out = {
        "schema": "opentallas.roofline.kv_model_validation.v1",
        "status": "pass" if not problems else "fail",
        "model": model.name,
        "oracle": str(args.oracle),
        "tolerance": TOLERANCE,
        "rungs": results,
        "problems": problems,
        "scope": [
            "Validates the KV read traffic a profile predicts against the traffic the"
            " released implementation performed. Does not validate weights, arithmetic"
            " or time.",
            "Per-kind bytes-per-pair are reported so a structural error and an entry-size"
            " error can be told apart; they look identical in the total.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(out))

    print(f"{model.name} KV model vs the engine that ran it")
    for rung in results:
        print(f"  {rung['context_tokens']:>9,} tokens  measured {rung['measured_bytes']:>15,}"
              f"  predicted {rung['predicted_bytes']:>15,.0f}  ratio {rung['ratio']:.4f}")
        for kind, per in sorted(rung["bytes_per_pair_by_kind"].items()):
            k = rung["by_kind"][kind]
            print(f"      {kind:<8} {k['layers']:>3.0f} layers  {k['pairs']:>10,.0f} pairs"
                  f"  {per:>7,.0f} B/pair")
    print(f"  status {out['status']} -> {args.output}")
    for problem in problems:
        print(f"  PROBLEM {problem}")
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
