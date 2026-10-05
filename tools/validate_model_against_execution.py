#!/usr/bin/env python3
"""Check an analytical prediction against what the accelerator actually did.

This is the join between the two halves of the project, and without it the
performance work is arithmetic on a whiteboard. An analytical or roofline model
predicts the traffic and the work a decode step costs. A deployment that
executed real tokens *counted* them. If the two disagree, the model has not
accounted for the system; if they agree, the model's traffic terms rest on a
real implementation and only its hardware terms -- bandwidth, density, latency
-- remain assumptions, and those are anchored to published parts.

That distinction is the whole argument. A reviewer is entitled to ask whether a
projected speedup considered every part of the system, and the only answer that
settles it is a machine that ran the model end to end and produced the same
byte counts the projection assumed.

What this tool does NOT do: it does not validate time. The functional device has
no clock. It validates the *quantities* a roofline consumes -- weight bytes, KV
bytes, arithmetic -- so that the time a roofline computes from them is a
statement about hardware rather than about unexamined traffic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
for extra in (REPO, REPO / "src"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

from opentallas.schema import ModelProfile  # noqa: E402
from opentallas.workload import kv_traffic, weight_traffic  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402

#: A measured quantity may exceed its analytical counterpart, because the model
#: counts model weights while a real deployment also moves scales, index tables,
#: rotary coefficients and activations.  It may not fall short: reading fewer
#: weight bytes than the model has weights means the machine did not do the work.
TOLERANCE_OVER = 0.15
TOLERANCE_UNDER = 0.01
#: The KV term admits no such allowance in either direction.
TOLERANCE_KV = 0.001


def _steps(record: dict[str, Any]) -> int:
    """Decode steps plus the one prefill transaction."""
    notes = record.get("notes", {})
    decode = notes.get("decode_steps")
    if decode is None:
        decode = max(0, int(record.get("generated_token_count", 1)) - 1)
    return int(decode) + 1


def _positions(record: dict[str, Any], prompt_tokens: int) -> int:
    """Token positions the machine actually computed: the prompt plus decodes."""
    return prompt_tokens + max(0, int(record.get("generated_token_count", 1)) - 1)


def _causal_position_reads(prompt_tokens: int, decode_steps: int) -> int:
    """Every (query, key) position pair a causal attention must visit, per layer.

    Prefill is the triangle: query *i* attends to the *i* positions at or before
    it.  Each decode step then attends to the whole context that exists when it
    runs.  This is not an approximation of the machine -- it is what causal
    attention *is*, and a deployment that reports a different number is either
    recomputing, caching across queries, or skipping work.
    """

    prefill = prompt_tokens * (prompt_tokens + 1) // 2
    decode = sum(prompt_tokens + step for step in range(1, decode_steps + 1))
    return prefill + decode


def _kv_bytes_per_layer_position(model: ModelProfile, context_tokens: int) -> float:
    """Mean KV bytes one layer reads for one context position.

    Derived from the profile's own traffic model rather than restated here, so
    that a change to the profile cannot silently pass this check.
    """

    reads = kv_traffic(model, context_tokens).read_bytes
    return reads / (model.num_layers * context_tokens)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execution", type=Path, required=True, action="append",
                        help="an execution record; repeat to validate several lanes")
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force")
        return 1

    model = ModelProfile.load(args.model)
    predicted_weight = weight_traffic(model, 1).total_bytes
    predicted_kv = kv_traffic(model, args.context)

    lanes: list[dict[str, Any]] = []
    problems: list[str] = []
    for path in args.execution:
        body = json.loads(path.read_text())
        record = body["record"]
        counters = record["counters"]
        prompt = int(record["workload"]["prompt_token_count"])
        steps = _steps(record)
        positions = _positions(record, prompt)

        measured_weight = int(counters.get("rom.bytes_read", 0)) + int(
            counters.get("hbm.bytes_read", 0)
        )
        per_step = measured_weight / steps if steps else 0.0
        ratio = per_step / predicted_weight if predicted_weight else 0.0

        lane = {
            "record": str(path),
            "status": body.get("status"),
            "target": record["target"]["target_id"],
            "backend": record["target"]["backend"],
            "tokens": record.get("generated_token_count"),
            "prompt_tokens": prompt,
            "transactions": steps,
            "token_positions": positions,
            "weight_bytes": {
                "measured_total": measured_weight,
                "measured_per_step": per_step,
                "predicted_per_step": predicted_weight,
                "ratio": ratio,
            },
            "by_storage_class": {
                k: int(counters.get(k, 0))
                for k in (
                    "rom.bytes_read",
                    "hbm.bytes_read",
                    "hbm.bytes_written",
                    "sram.bytes_read",
                    "sram.bytes_written",
                )
                if k in counters
            },
            "arithmetic": {
                "tensor_multiplications": int(counters.get("tensor.multiplications", 0)),
                "per_token_position": (
                    int(counters.get("tensor.multiplications", 0)) / positions
                    if positions
                    else 0.0
                ),
            },
            "attention_context_positions": int(
                counters.get("attention.context_positions", 0)
            ),
        }

        # The KV term is where the ROM argument is won or lost, and at long
        # context it dominates.  Unlike weight traffic it admits no allowance:
        # there are no scales or index tables riding along with a KV row, so
        # prediction and measurement should agree to the byte.
        decode_steps = max(0, int(record.get("generated_token_count", 1)) - 1)
        predicted_positions = model.num_layers * _causal_position_reads(
            prompt, decode_steps
        )
        measured_positions = int(counters.get("attention.context_positions", 0))
        entry_bytes = _kv_bytes_per_layer_position(model, args.context)
        predicted_kv_bytes = entry_bytes * measured_positions
        measured_kv_bytes = int(counters.get("attention.kv_bytes_read", 0))
        # A roofline models a DECODE step, so the quantity it consumes is the
        # decode share of this traffic, not the total.  Prefill's causal triangle
        # dominates the logical count at long context -- 1,152,144,000 of the
        # 1,208,107,008 pairs in the 8,000-token record -- and a real prefill
        # blocks its KV reads, so logical and physical diverge there.  For a
        # decode step they coincide: one query reads the whole cache once.
        prefill_pairs = model.num_layers * (prompt * (prompt + 1) // 2)
        decode_pairs = predicted_positions - prefill_pairs
        lane["kv"] = {
            "decode_only": {
                "pairs": decode_pairs,
                "bytes": entry_bytes * decode_pairs,
                "share_of_total_pairs": (
                    decode_pairs / measured_positions if measured_positions else 0.0
                ),
                "note": (
                    "the quantity a roofline divides by KV bandwidth; for a decode"
                    " step the logical and physical reads coincide, which is not"
                    " true of prefill"
                ),
            },
            "measured_context_positions": measured_positions,
            "predicted_context_positions": predicted_positions,
            "position_ratio": (
                measured_positions / predicted_positions if predicted_positions else 0.0
            ),
            "measured_bytes_read": measured_kv_bytes,
            "predicted_bytes_read": predicted_kv_bytes,
            "byte_ratio": (
                measured_kv_bytes / predicted_kv_bytes if predicted_kv_bytes else 0.0
            ),
            "measured_bytes_per_layer_position": (
                measured_kv_bytes / measured_positions if measured_positions else 0.0
            ),
            "profile_bytes_per_layer_position": entry_bytes,
        }
        if measured_positions:
            if abs(lane["kv"]["position_ratio"] - 1.0) > TOLERANCE_KV:
                problems.append(
                    f"{path.name}: attention visited {measured_positions:,} "
                    f"(layer, position) pairs where causal attention over a "
                    f"{prompt:,}-token prompt and {decode_steps} decode steps "
                    f"requires {predicted_positions:,}"
                )
            if abs(lane["kv"]["byte_ratio"] - 1.0) > TOLERANCE_KV:
                problems.append(
                    f"{path.name}: KV read traffic is "
                    f"{lane['kv']['byte_ratio']:.4f} of the profile's, and the KV"
                    " term carries no scales or index tables that could explain a"
                    " difference"
                )
        if ratio < 1.0 - TOLERANCE_UNDER:
            problems.append(
                f"{path.name}: measured weight traffic is {ratio:.3f} of predicted; "
                "reading fewer weight bytes than the model has weights means the "
                "machine did not do the work"
            )
        elif ratio > 1.0 + TOLERANCE_OVER:
            problems.append(
                f"{path.name}: measured weight traffic is {ratio:.3f} of predicted, "
                f"beyond the {TOLERANCE_OVER:.0%} allowance for scales, index "
                "tables and activations the model does not count"
            )
        lanes.append(lane)

    # Two lanes of the same model must perform identical arithmetic; only the
    # storage class of the bytes may differ.  That is the storage-class thesis,
    # and here it is a measurement rather than a claim.
    arithmetic_agreement = None
    if len(lanes) > 1:
        values = {lane["arithmetic"]["tensor_multiplications"] for lane in lanes}
        arithmetic_agreement = len(values) == 1
        if not arithmetic_agreement:
            problems.append(
                f"lanes disagree on arithmetic: {sorted(values)}; two deployments "
                "of one model must compute the same products"
            )

    out = {
        "schema": "opentallas.roofline.execution_validation.v1",
        "status": "pass" if not problems else "fail",
        "model": model.name,
        "context_tokens": args.context,
        "predicted": {
            "weight_bytes_per_step": predicted_weight,
            "kv_read_bytes_per_token": predicted_kv.read_bytes,
            "kv_storage_bytes_per_user": predicted_kv.storage_bytes_per_user,
            "weight_to_kv_read_ratio": predicted_weight / predicted_kv.read_bytes,
        },
        "lanes": lanes,
        "arithmetic_agreement_across_lanes": arithmetic_agreement,
        "problems": problems,
        "scope": [
            "Validates the QUANTITIES a roofline consumes: weight bytes, KV bytes,"
            " arithmetic. Does not validate time; the functional device has no clock.",
            "attention.kv_bytes_read is LOGICAL traffic: it counts every (query,"
            " key) pair. For a decode step that equals the physical read, because one"
            " query reads the whole cache once. For prefill it does not, because a"
            " real implementation blocks its KV reads over a query tile. The"
            " decode_only figures are therefore the ones a roofline consumes.",
            "The KV check has two halves. The (layer, position) pair count is"
            " compared against the causal triangle the prompt and decode steps"
            " require, which catches a machine that recomputes or skips. The byte"
            " count is then compared against the profile's own entry size, which"
            " catches a machine reading a KV row at the wrong precision or width.",
            "A measured excess over prediction is expected and bounded: a real"
            " deployment also moves scales, index tables, rotary coefficients and"
            " activations, which the analytical weight model does not count.",
            "A measured shortfall is a failure, not a tolerance.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(out))

    print(f"model {model.name} @ {args.context:,} tokens")
    print(f"  predicted weight bytes/step : {predicted_weight:>18,}")
    for lane in lanes:
        w = lane["weight_bytes"]
        print(f"  {lane['backend']:<18} measured/step {w['measured_per_step']:>18,.0f}"
              f"  ratio {w['ratio']:.3f}")
        kv = lane.get("kv")
        if kv and kv["measured_context_positions"]:
            print(f"  {'':<18} KV bytes      {kv['measured_bytes_read']:>18,}"
                  f"  ratio {kv['byte_ratio']:.4f}"
                  f"  ({kv['measured_bytes_per_layer_position']:,.0f} B per layer"
                  f"-position vs profile {kv['profile_bytes_per_layer_position']:,.0f})")
            dec = kv["decode_only"]
            print(f"  {'':<18} decode KV     {dec['bytes']:>18,}"
                  f"  ({dec['share_of_total_pairs']:.1%} of pairs; the roofline's quantity)")
            print(f"  {'':<18} causal pairs  "
                  f"{kv['measured_context_positions']:>18,}"
                  f"  ratio {kv['position_ratio']:.4f}")
    if arithmetic_agreement is not None:
        print(f"  arithmetic identical across lanes: {arithmetic_agreement}")
    print(f"  status {out['status']} -> {args.output}")
    for p in problems:
        print(f"  PROBLEM {p}")
    return 0 if not problems else 2


if __name__ == "__main__":
    raise SystemExit(main())
