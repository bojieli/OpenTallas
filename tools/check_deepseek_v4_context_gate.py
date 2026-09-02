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
or ``get_compress_topk_idxs`` for the second -- and it reproduced an independent
raw 32-token ROM prefill exactly: 25,224 gathered positions and 25,829,376 KV
bytes.  The governed multi-token records add decode.  A model that reproduces a
measurement it was not fitted to is worth more as a checker than as a
prediction.

What is checked
---------------
1. the record's workload digest is the pinned rung's, so the run answered the
   question the gold answers;
2. the generated tokens are a prefix of the pinned gold; and
3. ``attention.context_positions``, ``attention.sparse_indices``,
   ``attention.kv_bytes_read`` and ``attention.heads`` equal the model on every
   measured node; and
4. on a multi-node target, the independently retained cluster totals equal the
   per-node model times the admitted ``node_count``.  Aggregate division is
   never accepted in place of the per-node measurements because cluster-only
   work does not in general divide that way.

A record that fails any of these is reported and the tool exits non-zero.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

SCHEMA = "opentallas.deepseek_v4_context_gate.v2"
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

# A context record is evidence from these engines, not merely from this
# checker.  The token runner embeds their digests in every new functional
# artifact; this gate requires them so a record cannot be relabelled
# "post-amendment" after the simulator source changed underneath it.
REQUIRED_FUNCTIONAL_SOURCES = (
    "tools/run_accelerator_tokens.py",
    "compiler/backends/hbm_sram/lower.py",
    "compiler/backends/hbm_sram/plan.py",
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
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/memory.py",
    "runtime/sim/counters.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/engines/__init__.py",
    "runtime/sim/engines/deepseek_vector.py",
    "runtime/sim/engines/dma.py",
    "runtime/sim/engines/link.py",
    "runtime/sim/engines/reduction.py",
    "runtime/sim/engines/route.py",
    "runtime/sim/engines/attention.py",
    "runtime/sim/engines/selection.py",
    "runtime/sim/engines/tensor.py",
    "runtime/sim/engines/vector.py",
    "runtime/tensor_accelerator/attention.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/elementwise.py",
    "runtime/tensor_accelerator/rmsnorm.py",
    "runtime/tensor_accelerator/rope.py",
    "runtime/tensor_accelerator/sparse_attention.py",
)


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_lock_problems(source_sha256: object) -> list[str]:
    """Validate the complete recorded map and the non-removable minimum.

    Checking only a hand-picked subset lets a producer record a changed source
    and have the consumer silently ignore it.  Every entry is therefore a
    promise the gate verifies, while ``REQUIRED_FUNCTIONAL_SOURCES`` prevents a
    producer from evading the check by deleting a critical entry.
    """

    problems: list[str] = []
    if not isinstance(source_sha256, dict):
        problems.append(
            "record has no functional source_sha256 map; its simulator "
            "implementation cannot be source-locked"
        )
        source_sha256 = {}

    repo = REPO.resolve()
    for relative, expected in sorted(
        source_sha256.items(), key=lambda item: str(item[0])
    ):
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
        elif _sha256(source) != expected:
            problems.append(
                f"record source {relative} does not match the current "
                "implementation"
            )

    for relative in REQUIRED_FUNCTIONAL_SOURCES:
        if relative not in source_sha256:
            problems.append(f"record does not bind required source {relative}")
    return problems


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

    The accelerator now executes DeepSeek decode at the short 32-token prefix,
    below every window/pruning threshold.  It has not executed decode at the
    threshold rungs.  The reference oracle's ``--measure-kv`` records those
    rungs per layer from the released implementation: how many (layer,
    position) pairs its attention actually visited at a decode step.  That is
    the same quantity
    :func:`gathered_rows_for_query` states, so the two are compared directly and
    per layer -- not as a ratio and not in aggregate, where a compensating pair
    of errors could hide.

    This is the threshold-regime evidence for the decode arm.  It is evidence
    about the released implementation and the model, and none at all about an
    accelerator backend at those lengths.
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


def check_counter_evidence(
    record: dict, expected_per_node: dict[str, int], *, compared: bool
) -> dict:
    """Check logical counters without mistaking a cluster total for one node.

    A multi-node ``Device`` runs each compute instruction at every ``NODE_ID``.
    Its aggregate counters are therefore cluster totals, while LINK, STATE,
    control, and host bookkeeping are cluster-only and cannot in general be
    divided by ``node_count``.  For the four attention-engine counters checked
    here, require the measured per-node split and compare every node directly.
    The aggregate must independently equal ``expected_per_node * node_count``.
    """

    problems: list[str] = []
    target = record.get("target") or {}
    if not isinstance(target, dict):
        problems.append("target is not an object")
        target = {}
    raw_node_count = target.get("node_count")
    node_count = (
        int(raw_node_count)
        if isinstance(raw_node_count, int)
        and not isinstance(raw_node_count, bool)
        and raw_node_count > 0
        else 0
    )
    if node_count == 0:
        problems.append(
            "target.node_count is missing or invalid; counter scope cannot be "
            "inferred from target_id, topology_class, or capability limits"
        )

    aggregate_source = record.get("counters") or {}
    observed_aggregate: dict[str, int] = {}
    for name in expected_per_node:
        value = aggregate_source.get(name) if isinstance(aggregate_source, dict) else None
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            problems.append(
                f"cluster-total {name} is missing or is not a non-negative integer"
            )
            value = -1
        observed_aggregate[name] = value
    expected_aggregate: dict[str, int | None] = {
        name: value * node_count if node_count else None
        for name, value in expected_per_node.items()
    }

    scope = record.get("counter_scope") or {}
    if not isinstance(scope, dict):
        problems.append("counter_scope is not an object")
        scope = {}
    raw_nodes = record.get("node_counters")
    node_rows: list[dict] = []
    comparison_scope = "invalid_or_missing"
    if node_count == 1:
        if (
            isinstance(raw_nodes, list)
            and len(raw_nodes) == 1
            and isinstance(raw_nodes[0], dict)
        ):
            node_rows = raw_nodes
            comparison_scope = "measured_single_node_and_aggregate"
        else:
            # On an explicitly one-node topology, the aggregate is the node's
            # complete work.  This keeps older single-node records checkable;
            # there is no ambiguous cluster total to divide.
            node_rows = [aggregate_source]
            comparison_scope = "explicit_single_node_aggregate"
    elif node_count > 1:
        if scope.get("aggregate") != "cluster_total":
            problems.append(
                "multi-node record does not declare counters as cluster_total"
            )
        if scope.get("per_node") != "engine_work_by_node_id":
            problems.append(
                "multi-node record does not declare node_counters as "
                "engine_work_by_node_id"
            )
        if scope.get("node_count") != node_count:
            problems.append(
                f"counter_scope.node_count is {scope.get('node_count')!r}, "
                f"target.node_count is {node_count}"
            )
        if scope.get("node_counters_index") != "NODE_ID":
            problems.append(
                "multi-node record does not declare node_counters_index as NODE_ID"
            )
        if not isinstance(raw_nodes, list) or len(raw_nodes) != node_count:
            problems.append(
                f"multi-node record has "
                f"{len(raw_nodes) if isinstance(raw_nodes, list) else 0} "
                f"node counter sets, expected {node_count}; aggregate division "
                "is not accepted as a substitute"
            )
        elif not all(isinstance(row, dict) for row in raw_nodes):
            problems.append("node_counters contains a non-object entry")
        else:
            node_rows = raw_nodes
            comparison_scope = "measured_per_node_and_cluster_total"

    summaries: dict[str, dict] = {}
    for name, want in expected_per_node.items():
        values: list[int | None] = []
        invalid: list[int] = []
        for index, row in enumerate(node_rows):
            value = row.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                values.append(None)
                invalid.append(index)
            else:
                values.append(value)
        valid_values = [value for value in values if value is not None]
        mismatched = [
            index for index, value in enumerate(values) if value != want
        ]
        if invalid:
            problems.append(
                f"{name} is missing or invalid on {len(invalid)} node(s): "
                f"{invalid[:8]}"
            )
        summaries[name] = {
            "expected_each_node": want,
            "minimum_observed": min(valid_values) if valid_values else None,
            "maximum_observed": max(valid_values) if valid_values else None,
            "nodes_observed": len(values),
            "nodes_with_valid_counter": len(valid_values),
            "mismatched_node_count": len(mismatched),
            "first_mismatched_nodes": mismatched[:8],
        }

    if compared and node_count > 0:
        for name, want in expected_aggregate.items():
            assert want is not None
            got = observed_aggregate[name]
            if got != want:
                problems.append(
                    f"cluster-total {name} is {got:,}, expected {want:,} "
                    f"for {node_count} nodes"
                )
        for name, summary in summaries.items():
            if summary["mismatched_node_count"]:
                problems.append(
                    f"{name} disagrees with the logical model on "
                    f"{summary['mismatched_node_count']} of {node_count} nodes"
                )

    return {
        "counter_comparison_scope": comparison_scope,
        "node_count": node_count or None,
        "expected_counters_per_node": expected_per_node,
        "expected_aggregate_counters": expected_aggregate,
        "observed_aggregate_counters": observed_aggregate,
        "aggregate_excess_over_model": {
            name: (
                observed_aggregate[name] - expected_aggregate[name]
                if expected_aggregate[name] is not None
                else None
            )
            for name in expected_per_node
        },
        "per_node_counter_summary": summaries,
        "problems": problems,
    }


def check_record(
    record_path: Path, prompts: dict, golds: dict, profile: Path
) -> dict:
    body = json.loads(record_path.read_text())
    record = body.get("record", body)
    workload = record["workload"]
    workload_id = workload["workload_id"]
    problems: list[str] = []

    problems.extend(_source_lock_problems(record.get("source_sha256")))

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

    expected = predict(
        int(workload["prompt_token_count"]), max(0, len(generated) - 1), profile
    )
    failure = record.get("failure")
    status = body.get("status")
    if status != "pass":
        problems.append(f"record status is {status!r}, expected 'pass'")
    # A run that trapped part-way did work the model does not describe -- the
    # aborted step's completed layers are in the counters and its remaining
    # ones are not.  Such a record already fails, on the trap; comparing its
    # counters as well would report the same defect twice and hide what the
    # residual actually tells you, which is *where* it stopped.  The numbers
    # are still recorded, and a completed run is still compared exactly.
    compared = failure is None
    counter_evidence = check_counter_evidence(record, expected, compared=compared)
    problems.extend(counter_evidence.pop("problems"))

    return {
        "record": _relative(record_path),
        "record_sha256": _sha256(record_path),
        "workload_id": workload_id,
        "prompt_token_count": int(workload["prompt_token_count"]),
        "generated_token_ids": generated,
        "gold_token_ids": gold_ids[: max(1, len(generated))],
        "decode_steps": max(0, len(generated) - 1),
        **counter_evidence,
        "discrimination": discrimination(
            int(workload["prompt_token_count"]),
            max(0, len(generated) - 1),
            profile,
        ),
        "counters_compared": compared,
        "failure": failure,
        "status": status,
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
    missing_pins = [_relative(path) for path in pins if not path.is_file()]
    prompts, golds = load_pins([path for path in pins if path.is_file()])
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
        print(
            f"     counter scope {row['counter_comparison_scope']}, "
            f"nodes={row['node_count']}"
        )
        for name, want in row["expected_aggregate_counters"].items():
            got = row["observed_aggregate_counters"][name]
            if want is None:
                expected = "scope unresolved"
                flag = "   (node scope unavailable)"
            elif not row["counters_compared"]:
                expected = f"{want:,}"
                flag = "   (partial run, not compared)"
            else:
                expected = f"{want:,}"
                flag = "" if got == want else "   <-- DISAGREES"
            print(
                f"     cluster {name:26s} {got:>15,} "
                f"expected {expected:>15s}{flag}"
            )
            summary = row["per_node_counter_summary"][name]
            if row["node_count"] and row["node_count"] > 1:
                print(
                    f"       per node min/max "
                    f"{summary['minimum_observed']!s:>15}/"
                    f"{summary['maximum_observed']!s:<15} "
                    f"expected {summary['expected_each_node']:,}; "
                    f"mismatched nodes {summary['mismatched_node_count']}"
                )
        if row["failure"]:
            print(f"     FAILURE {row['failure']}")
        for problem in row["problems"]:
            print(f"     PROBLEM {problem}")
    for path in missing:
        print(f"MISSING {path}")
    for path in missing_pins:
        print(f"MISSING PIN {path}")

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

    maximum_record_context = max(
        (
            row["prompt_token_count"] + row["decode_steps"]
            for row in results
        ),
        default=0,
    )
    window, _heads, layers = layer_table(args.model_profile)
    pruning_thresholds = [
        ratio * (top_k + 1) for ratio, top_k in layers if ratio and top_k
    ]
    first_pruning_context = min(pruning_thresholds) if pruning_thresholds else None
    checked_records_pass = bool(results) and all(r["passes"] for r in results)
    cross_check_pass = bool(cross.get("available")) and bool(cross.get("all_agree"))
    all_pass = (
        checked_records_pass
        and not missing
        and not missing_pins
        and cross_check_pass
    )
    document = {
        "schema": SCHEMA,
        "decode_arm_cross_check": cross,
        "discrimination_ladder": {
            "note": (
                "What the gathered-position counter would be if the sparse "
                "path were not doing its job, at every pinned prompt length. "
                "An equality check is a gate only where the quantity moves. "
                "At 32 prompt tokens -- the length of the shortest retained "
                "DeepSeek accelerator gate -- a sliding window that never "
                "clipped produces "
                "a bit-identical counter, so no run at that length could have "
                "detected one."
            ),
            "by_workload": ladder,
        },
        "model": "deepseek-v4-flash-0731",
        "pins": [_relative(path) for path in pins],
        "pins_missing": missing_pins,
        "source_sha256": {
            _relative(path): _sha256(path)
            for path in [
                Path(__file__),
                *(REPO / relative for relative in REQUIRED_FUNCTIONAL_SOURCES),
                args.model_profile,
                args.oracle,
                *[path for path in pins if path.is_file()],
            ]
            if path.exists()
        },
        "counter_model": (
            "min(position + 1, window) + min(top_k or all, (position + 1) // "
            "ratio), summed over every layer and every query position; "
            "kv_bytes = gathered * 1024"
        ),
        "records_checked": len(results),
        "records_missing": missing,
        "results": results,
        "all_pass": all_pass,
        "claim_boundary": {
            "all_checked_records_pass": checked_records_pass,
            "all_required_records_present": not missing,
            "all_required_pins_present": not missing_pins,
            "decode_arm_cross_check_pass": cross_check_pass,
            "maximum_accelerator_context_tokens_checked": maximum_record_context,
            "first_window_clipping_context_tokens": window + 1,
            "first_index_pruning_context_tokens": first_pruning_context,
            "accelerator_window_clipping_executed": (
                maximum_record_context >= window + 1
            ),
            "accelerator_index_pruning_executed": (
                first_pruning_context is not None
                and maximum_record_context >= first_pruning_context
            ),
            "all_declared_sparsity_thresholds_executed": (
                maximum_record_context >= window + 1
                and first_pruning_context is not None
                and maximum_record_context >= first_pruning_context
            ),
            "functional_simulator_only": True,
            "rtl": False,
            "cycles_or_performance": False,
        },
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
    if not cross.get("available"):
        print(
            "the decode-arm oracle cross-check is unavailable; the governed "
            "context gate fails closed"
        )
        return 1
    return 0 if document["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
