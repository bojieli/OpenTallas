#!/usr/bin/env python3
"""Refuse a DeepSeek accelerator run that read the wrong KV rows.

Why this exists
---------------
A DeepSeek backend run has always been judged on one thing: did the token match
the oracle.  That is necessary and it is not sufficient for a *sparsity* gate,
because the counter that says how much KV the run actually touched was recorded
and never read by anything.  A run can agree on a token and still have attended
over a set of positions the model does not specify -- and at 200,000 tokens the
size of that set is the entire ROM-versus-HBM argument.

So this checker states the sparse traffic the pinned profile implies, exactly,
and requires the executed counters to equal it.  Not a tolerance: an equality.
The quantities are integers and the model is closed-form, so a disagreement is
a defect and not a rounding.

The model
---------
For a prefill of ``N`` tokens, a layer with window ``W``, compression ratio
``r`` and per-group ``top_k`` gathers, for the query at 0-based position ``q``:

    min(q + 1, W)                              window positions
  + min(top_k or all, (q + 1) // r)            compressed groups

and for a decode step at absolute position ``P`` the same expression with
``q = P``.  The two blocks are disjoint address ranges, so the gathered row
count is their sum.  ``r = 0`` layers contribute the window term alone.

This is not a new derivation.  It is the released ``Attention.forward``'s own
arithmetic -- ``get_window_topk_idxs`` for the first term, ``Indexer.forward``
or ``get_compress_topk_idxs`` for the second -- and it reproduces the one
completed DeepSeek backend run exactly: 25,224 gathered positions at a 32-token
prefill, against the 25,224 that run recorded, and 25,829,376 KV bytes against
its 25,829,376.  A model that reproduces a measurement it was not fitted to is
worth more as a checker than as a prediction.

What is checked
---------------
1. the record's workload digest is the pinned rung's, so the run answered the
   question the gold answers;
2. the generated tokens are a prefix of the pinned gold; and
3. ``attention.context_positions``, ``attention.sparse_indices``,
   ``attention.kv_bytes_read`` and ``attention.heads`` equal the model.

A record that fails any of these is reported and the tool exits non-zero.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "opentallas.deepseek_v4_context_gate.v1"
MODEL_PROFILE = REPO / "configs" / "models" / "deepseek-v4-flash-0731.json"
DEFAULT_PIN = (
    REPO / "results" / "abi3" / "deepseek_v4_context_threshold_workload_pins.json"
)
DEFAULT_PREFIX_PIN = (
    REPO / "results" / "abi3" / "deepseek_v4_prefix_workload_pins.json"
)
#: The released latent width and its BF16 byte count, from the pinned profile's
#: own attention_groups entry_bytes.
KV_ROW_BYTES = 1024


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def layer_table(profile: Path) -> tuple[int, int, list[tuple[int, int]]]:
    """``(window, query_heads, [(ratio, top_k)] per layer)`` from the profile."""
    body = json.loads(profile.read_text())
    config = body["metadata"]["operator_config"]
    window = int(config["window_tokens"])
    heads = int(config["num_attention_heads"])
    ranking = {
        int(g["compression_ratio"]): int(g["top_k"])
        for g in body["attention_groups"]
    }
    layers = []
    for ratio in config["compress_ratios"]:
        ratio = int(ratio)
        layers.append((ratio, ranking.get(ratio or 1, 0)))
    return window, heads, layers


def gathered_rows_for_query(
    position: int, window: int, ratio: int, top_k: int
) -> int:
    """Rows one query gathers in one layer, at 0-based absolute ``position``."""
    rows = min(position + 1, window)
    if ratio:
        groups = (position + 1) // ratio
        rows += min(top_k, groups) if top_k else groups
    return rows


def predict(
    prompt_tokens: int, decode_steps: int, profile: Path
) -> dict[str, int]:
    """The counters a conforming run must record, exactly."""
    window, heads, layers = layer_table(profile)
    positions = list(range(prompt_tokens)) + [
        prompt_tokens + step for step in range(decode_steps)
    ]
    gathered = 0
    for ratio, top_k in layers:
        for position in positions:
            gathered += gathered_rows_for_query(position, window, ratio, top_k)
    spans = prompt_tokens + decode_steps
    return {
        "attention.context_positions": gathered,
        "attention.sparse_indices": gathered,
        "attention.kv_bytes_read": gathered * KV_ROW_BYTES,
        "attention.heads": spans * heads * len(layers),
    }


def load_pins(paths: list[Path]) -> tuple[dict, dict]:
    """Merge several workload pins into ``{id: prompt}`` and ``{id: gold}``.

    Two pins exist and they name their prompt block differently -- the prefix
    pin puts the derived prompts under ``workloads``, this ladder's puts them
    under ``prompts`` -- so both spellings are read.  A workload named by two
    pins with different digests is refused rather than resolved by order.
    """

    prompts: dict[str, dict] = {}
    gold: dict[str, dict] = {}
    for path in paths:
        body = json.loads(path.read_text())
        block = body.get("prompts") or body.get("workloads") or {}
        for workload_id, entry in block.items():
            if not isinstance(entry, dict) or "digest" not in entry:
                continue
            existing = prompts.get(workload_id)
            if existing and existing["digest"] != entry["digest"]:
                raise SystemExit(
                    f"{workload_id} is pinned twice with different digests "
                    f"({existing['digest']} and {entry['digest']}); the pins "
                    "disagree about which prompt this is"
                )
            prompts[workload_id] = entry
        for workload_id, entry in (
            body.get("gold", {}).get("workloads", {}) or {}
        ).items():
            gold[workload_id] = entry
    return prompts, gold


def discrimination(
    prompt_tokens: int, decode_steps: int, profile: Path
) -> dict:
    """What the counter would be if sparsity were not doing its job.

    An equality check is only a gate if the quantity moves when the thing under
    test breaks.  These are the two ways the sparse path can fail while still
    producing a plausible run: the sliding window not clipping, so every query
    sees its whole history, and the compressed segments never being attended,
    so the model degenerates to pure sliding-window attention.  The margin is
    stated here rather than asserted in prose, and it is the reason a short
    rung is worth running: at 129 prompt tokens an unclipped window is only 43
    positions away from correct, and at 160 it is 22,704.
    """

    window, _heads, layers = layer_table(profile)
    positions = list(range(prompt_tokens)) + [
        prompt_tokens + step for step in range(decode_steps)
    ]
    correct = unclipped = windowed_only = 0
    for ratio, top_k in layers:
        for position in positions:
            correct += gathered_rows_for_query(position, window, ratio, top_k)
            unclipped += gathered_rows_for_query(
                position, position + 1, ratio, top_k
            )
            windowed_only += gathered_rows_for_query(position, window, 0, 0)
    return {
        "correct": correct,
        "if_the_window_did_not_clip": unclipped,
        "if_the_window_did_not_clip_margin": unclipped - correct,
        "if_no_compressed_segment_were_attended": windowed_only,
        "if_no_compressed_segment_were_attended_margin": windowed_only - correct,
    }


def oracle_decode_cross_check(oracle_path: Path, profile: Path) -> dict:
    """Check the model's *decode* arm against the released implementation.

    The accelerator has never executed a DeepSeek decode step, so the model's
    decode arm has no accelerator run to be checked against.  The reference
    oracle's ``--measure-kv`` does record one, per layer, from the released
    implementation: how many (layer, position) pairs its attention actually
    visited at a decode step.  That is the same quantity
    :func:`gathered_rows_for_query` states, so the two are compared directly and
    per layer -- not as a ratio and not in aggregate, where a compensating pair
    of errors could hide.

    This is the *only* evidence the decode arm has.  It is evidence about the
    released implementation and the model, and none at all about a backend.
    """

    if not oracle_path.exists():
        return {"available": False, "reason": f"no oracle report at {oracle_path}"}
    window, _heads, layers = layer_table(profile)
    body = json.loads(oracle_path.read_text())
    rungs = []
    for workload_id, entry in sorted(body.get("results", {}).items()):
        measurement = entry.get("kv_measurement") or {}
        for step in measurement.get("decode_steps", []):
            per_layer = step.get("per_layer") or {}
            if not per_layer:
                continue
            context = int(step["context_tokens"])
            position = context - 1
            mismatches = []
            for index, (ratio, top_k) in enumerate(layers):
                observed = per_layer.get(str(index))
                if observed is None:
                    continue
                want = gathered_rows_for_query(position, window, ratio, top_k)
                got = int(observed["main_pairs"])
                if got != want:
                    mismatches.append(
                        {"layer": index, "measured": got, "model": want}
                    )
            total_model = sum(
                gathered_rows_for_query(position, window, ratio, top_k)
                for ratio, top_k in layers
            )
            rungs.append(
                {
                    "workload_id": workload_id,
                    "context_tokens": context,
                    "layers_compared": len(
                        [i for i in range(len(layers)) if str(i) in per_layer]
                    ),
                    "measured_main_context_positions": int(
                        step["measured"]["main_context_positions"]
                    ),
                    "model_main_context_positions": total_model,
                    "per_layer_mismatches": mismatches[:8],
                    "per_layer_mismatch_count": len(mismatches),
                    "agrees": not mismatches
                    and int(step["measured"]["main_context_positions"]) == total_model,
                }
            )
    contexts = sorted({r["context_tokens"] for r in rungs})
    return {
        "available": bool(rungs),
        "oracle": _relative(oracle_path),
        "comparator": "released implementation, instrumented by --measure-kv",
        "decode_steps_compared": len(rungs),
        "total_layer_comparisons": sum(r["layers_compared"] for r in rungs),
        "total_layer_mismatches": sum(r["per_layer_mismatch_count"] for r in rungs),
        "context_range": [contexts[0], contexts[-1]] if contexts else [],
        "rungs": rungs,
        "all_agree": bool(rungs) and all(r["agrees"] for r in rungs),
    }


def check_record(
    record_path: Path, prompts: dict, golds: dict, profile: Path
) -> dict:
    body = json.loads(record_path.read_text())
    record = body.get("record", body)
    workload = record["workload"]
    workload_id = workload["workload_id"]
    problems: list[str] = []

    pinned = prompts.get(workload_id)
    gold = golds.get(workload_id)
    if pinned is None:
        problems.append(
            f"{workload_id} is not a pinned rung of this ladder; the record "
            "cannot be checked against gold that does not describe it"
        )
    elif workload["workload_digest"] != pinned["digest"]:
        problems.append(
            f"workload digest {workload['workload_digest']} is not the pinned "
            f"{pinned['digest']}: the run answered a different question"
        )

    generated = list(record.get("generated_token_ids") or [])
    gold_ids = list((gold or {}).get("generated_token_ids") or [])
    if not generated:
        problems.append("the run produced no token")
    elif not gold_ids:
        problems.append(f"no pinned gold for {workload_id}")
    elif generated != gold_ids[: len(generated)]:
        first = next(
            (
                i
                for i, (a, b) in enumerate(zip(generated, gold_ids))
                if a != b
            ),
            len(generated),
        )
        problems.append(
            f"token {first} is {generated[first] if first < len(generated) else None}"
            f", gold {gold_ids[first] if first < len(gold_ids) else None}"
        )

    counters = record.get("counters", {})
    expected = predict(
        int(workload["prompt_token_count"]), max(0, len(generated) - 1), profile
    )
    observed = {name: int(counters.get(name, -1)) for name in expected}
    excess = {name: observed[name] - expected[name] for name in expected}
    failure = record.get("failure")
    # A run that trapped part-way did work the model does not describe -- the
    # aborted step's completed layers are in the counters and its remaining
    # ones are not.  Such a record already fails, on the trap; comparing its
    # counters as well would report the same defect twice and hide what the
    # residual actually tells you, which is *where* it stopped.  The numbers
    # are still recorded, and a completed run is still compared exactly.
    compared = failure is None
    if compared:
        for name, want in expected.items():
            if observed[name] != want:
                problems.append(
                    f"{name} is {observed[name]:,}, the profile says {want:,}"
                )

    return {
        "record": _relative(record_path),
        "workload_id": workload_id,
        "prompt_token_count": int(workload["prompt_token_count"]),
        "generated_token_ids": generated,
        "gold_token_ids": gold_ids[: max(1, len(generated))],
        "decode_steps": max(0, len(generated) - 1),
        "expected_counters": expected,
        "observed_counters": observed,
        "discrimination": discrimination(
            int(workload["prompt_token_count"]),
            max(0, len(generated) - 1),
            profile,
        ),
        "counter_excess_over_model": excess,
        "counters_compared": compared,
        "failure": failure,
        "status": body.get("status"),
        "problems": problems,
        "passes": not problems and failure is None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, nargs="+")
    parser.add_argument(
        "--pin", type=Path, action="append", default=None,
        help="workload pin holding the derived prompts and their gold; repeatable",
    )
    parser.add_argument("--model-profile", type=Path, default=MODEL_PROFILE)
    parser.add_argument(
        "--oracle",
        type=Path,
        default=REPO
        / "results"
        / "abi3"
        / "deepseek_v4_reference_oracle_threshold.json",
        help=(
            "reference-oracle report carrying --measure-kv per-layer decode "
            "positions, to check the model's decode arm against the released "
            "implementation"
        ),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    pins = args.pin or [DEFAULT_PIN, DEFAULT_PREFIX_PIN]
    prompts, golds = load_pins([p for p in pins if p.exists()])
    results = [
        check_record(path, prompts, golds, args.model_profile)
        for path in args.records
        if path.exists()
    ]
    missing = [str(p) for p in args.records if not p.exists()]
    for row in results:
        mark = "PASS" if row["passes"] else "FAIL"
        print(
            f"{mark} {row['workload_id']} ({row['prompt_token_count']} tokens, "
            f"{row['decode_steps']} decode steps)"
        )
        print(
            f"     tokens {row['generated_token_ids']} against gold "
            f"{row['gold_token_ids']}"
        )
        for name, want in row["expected_counters"].items():
            got = row["observed_counters"][name]
            if not row["counters_compared"]:
                flag = "   (partial run, not compared)"
            else:
                flag = "" if got == want else "   <-- DISAGREES"
            print(f"     {name:34s} {got:>15,} expected {want:>15,}{flag}")
        if row["failure"]:
            print(f"     FAILURE {row['failure']}")
        for problem in row["problems"]:
            print(f"     PROBLEM {problem}")
    for path in missing:
        print(f"MISSING {path}")

    ladder = {}
    for workload_id, entry in sorted(prompts.items()):
        tokens = int(entry["prompt_token_count"])
        ladder[workload_id] = {
            "prompt_token_count": tokens,
            **discrimination(tokens, 0, args.model_profile),
        }

    cross = oracle_decode_cross_check(args.oracle, args.model_profile)
    if cross.get("available"):
        print(
            f"decode cross-check against the released implementation: "
            f"all_agree={cross['all_agree']}"
        )
        for rung in cross["rungs"]:
            print(
                f"     {rung['workload_id']} context {rung['context_tokens']}: "
                f"measured {rung['measured_main_context_positions']:,} "
                f"model {rung['model_main_context_positions']:,} "
                f"({rung['layers_compared']} layers, "
                f"{rung['per_layer_mismatch_count']} mismatched)"
            )

    document = {
        "schema": SCHEMA,
        "decode_arm_cross_check": cross,
        "discrimination_ladder": {
            "note": (
                "What the gathered-position counter would be if the sparse "
                "path were not doing its job, at every pinned prompt length. "
                "An equality check is a gate only where the quantity moves. "
                "At 32 prompt tokens -- the length of the only DeepSeek gate "
                "that existed -- a sliding window that never clipped produces "
                "a bit-identical counter, so no run at that length could have "
                "detected one."
            ),
            "by_workload": ladder,
        },
        "model": "deepseek-v4-flash-0731",
        "pins": [_relative(p) for p in pins if Path(p).exists()],
        "counter_model": (
            "min(position + 1, window) + min(top_k or all, (position + 1) // "
            "ratio), summed over every layer and every query position; "
            "kv_bytes = gathered * 1024"
        ),
        "records_checked": len(results),
        "records_missing": missing,
        "results": results,
        "all_pass": bool(results) and all(r["passes"] for r in results),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
        print(f"wrote {args.output}")
    if cross.get("available") and not cross["all_agree"]:
        print(
            "the decode arm of the traffic model disagrees with the released "
            "implementation; the model, not the run, is what failed here"
        )
        return 1
    return 0 if document["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
