"""Can a gate at this prompt length see a wrong index score at all?

The DeepSeek sparse gate has two arms.  One compares the accelerator's token
against oracle gold; the other requires the executed KV-traffic counters to
equal a closed-form model.  Neither arm is sensitive to the *index scores* at
every length a backend can reach, and that is not obvious from either one.

Two independent reasons, both checked here rather than argued:

**The counter arm is blind at every context, without exception.**  The rows a
query gathers are ``min(p + 1, W) + min(top_k, (p + 1) // r)``.  Every term is
position arithmetic.  No score appears, so a deployment that computed index
scores by any rule at all -- including a constant -- gathers exactly the same
number of rows and records exactly the same counters.  The margin is zero at
129 tokens, at 2,052, and at 1,000,000.  The counter arm gates *how many* rows
are read, which is what the byte-traffic model needs; it cannot gate *which*.

**The token arm is blind below the pruning threshold.**  A ranking layer
discards a candidate only when it has more than ``top_k`` of them, i.e. from
``r * (top_k + 1)`` prompt tokens.  Below that the ranking keeps everything it
ranks, so the selected set is the whole candidate set whatever the scores say,
and ``ROUTE.INDEX_TOPK`` emits it sorted ascending -- so neither the set nor
its order carries any score information, and the token cannot move.

The second reason is the one that matters for this ladder: every rung a
backend has ever completed is below the threshold.  So this tool does not
assert it.  It runs ``ROUTE.INDEX_TOPK`` on the functional device twice per
case with two different score blocks and compares the emitted KV-row arrays
byte for byte:

* below the threshold the two must be **identical** -- if they are not, the
  operator is doing something with scores that position arithmetic does not
  explain, and this file is the finding;
* at and above it they must **differ** -- if they do not, the operator is
  ignoring its score input, and this file is that finding instead.

The second case is a real check with teeth, and it is the only one in this
repository that would fail if ``INDEX_TOPK`` dropped its scores on the floor.

This supplies no activation to any accelerator run and produces no token.  It
is an operator experiment on the shipped engine, run through a real ABI 3.0
deployment, exactly as `tools/audit_deepseek_v4_index_selection.py` is.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import platform
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location(
    "audit_index_selection", REPO / "tools" / "audit_deepseek_v4_index_selection.py"
)
audit = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(audit)

from runtime.abi3.constants import DType, Major, Route  # noqa: E402
from runtime.abi3.descriptors import Symbol  # noqa: E402
from runtime.abi3.records import CompletionStatus  # noqa: E402
import runtime.sim.engines.route  # noqa: E402,F401  (registers the handlers)


def _relative(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return str(path)


def raw_selection(
    score_codes: np.ndarray | None,
    window_rows: np.ndarray,
    *,
    ratio: int,
    top_k: int,
    span: int,
    start_pos: int,
    context: int,
) -> tuple[np.ndarray, dict[str, int]]:
    """``ROUTE.INDEX_TOPK`` on the device, returned **unsorted and whole**.

    `audit_deepseek_v4_index_selection.accelerator_selection` sorts each row
    into a set because that is the question it asks.  This one keeps the array
    the engine actually wrote, because the question here is whether *anything*
    about the emitted bytes -- membership or order -- moved when the scores
    did.
    """

    window = int(window_rows.shape[1])
    slots = window + top_k
    footprint = (
        (0 if score_codes is None else score_codes.nbytes)
        + window_rows.nbytes
        + span * slots * 4
        + (1 << 20)
    )
    build = audit._Build(max(1 << 22, int(footprint * 2)))
    inputs: list[int] = []
    if score_codes is None:
        inputs.append(audit.NO_ID)
    else:
        inputs.append(build.input_view(score_codes, DType.BF16))
    inputs.append(build.input_view(window_rows.astype(np.uint32), DType.U32))
    inputs.append(build.input_view(np.array([ratio], dtype=np.uint32), DType.U32))
    out = build.output_view((span, slots), DType.U32, 4)
    build.emit(
        Major.ROUTE,
        Route.INDEX_TOPK,
        inputs,
        [out],
        aux=[top_k, 0, int(Symbol.CONTEXT_LENGTH), int(Symbol.POSITION_START)],
    )
    device = build.finish()
    symbols = {
        int(Symbol.CONTEXT_LENGTH): context,
        int(Symbol.POSITION_START): start_pos,
    }
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols
    )
    if result.status != CompletionStatus.SUCCESS:
        raise SystemExit(
            f"ROUTE.INDEX_TOPK did not complete: {result.status.name} "
            f"{getattr(result, 'message', '')}"
        )
    view = device.views.resolve(out, {}, symbols)
    got = np.array(device.views.read_array(view), dtype=np.uint32).reshape(
        span, slots
    )
    return got, dict(result.counters)


def gathered_rows(context: int, window: int, ratio: int, top_k: int) -> int:
    """Rows the final query of a ``context``-token prefill gathers, one layer."""
    position = context - 1
    rows = min(position + 1, window)
    groups = (position + 1) // ratio
    rows += min(top_k, groups) if top_k else groups
    return rows


def first_pruning_length(ratio: int, top_k: int) -> int | None:
    """Shortest prompt whose final query has more candidates than ``top_k``.

    ``(N - 1 + 1) // r > k`` is ``N >= r * (k + 1)``.  A group that ranks
    nothing (``top_k == 0``) never prunes and has no such length.
    """
    if not top_k:
        return None
    return ratio * (top_k + 1)


def run_pair(
    *,
    label: str,
    ratio: int,
    top_k: int,
    window: int,
    span: int,
    start_pos: int,
    context: int,
    seed: int,
) -> dict[str, Any]:
    """One case: the same selection under two different score blocks."""

    candidates = context // ratio
    ranked = top_k > 0
    selected = min(top_k, candidates) if ranked else candidates
    prunes = bool(ranked and candidates > top_k)

    window_rows = audit._window_block(window, span, start_pos)
    effective_k = top_k if ranked else candidates

    codes_a = audit._scores("distinct", span, candidates, seed) if ranked else None
    codes_b = (
        audit._scores("distinct", span, candidates, seed + 977) if ranked else None
    )
    scores_differ = bool(
        ranked and codes_a is not None and not np.array_equal(codes_a, codes_b)
    )

    got_a, counters_a = raw_selection(
        codes_a,
        window_rows,
        ratio=ratio,
        top_k=effective_k,
        span=span,
        start_pos=start_pos,
        context=context,
    )
    got_b, counters_b = raw_selection(
        codes_b,
        window_rows,
        ratio=ratio,
        top_k=effective_k,
        span=span,
        start_pos=start_pos,
        context=context,
    )

    identical = bool(np.array_equal(got_a, got_b))
    differing_rows = int(np.sum(np.any(got_a != got_b, axis=1)))
    counter_key = "route.topk_candidates"
    same_counters = counters_a == counters_b

    # What the token arm and the counter arm can each see for this case.
    expected_identical = not prunes
    agrees = identical == expected_identical

    return {
        "label": label,
        "context": context,
        "span": span,
        "start_pos": start_pos,
        "phase": "prefill" if start_pos == 0 else "decode",
        "compression_ratio": ratio,
        "top_k": top_k,
        "window": window,
        "ranks_candidates": ranked,
        "candidate_groups_at_final_query": candidates,
        "selected_per_query": selected,
        "selection_prunes": prunes,
        "score_blocks_differ": scores_differ,
        "emitted_rows_identical_under_different_scores": identical,
        "rows_that_moved": differing_rows,
        "index_score_reaches_the_emitted_rows": not identical,
        "counters_identical_under_different_scores": bool(same_counters),
        "counters_a": counters_a,
        "counters_b": counters_b,
        "expected_emitted_rows_identical": expected_identical,
        "agrees_with_the_position_arithmetic": agrees,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-profile",
        type=Path,
        default=REPO / "configs" / "models" / "deepseek-v4-flash-0731.json",
    )
    parser.add_argument(
        "--pins",
        type=Path,
        nargs="+",
        default=[
            REPO
            / "results"
            / "abi3"
            / "deepseek_v4_context_threshold_workload_pins.json"
        ],
        help="workload pins naming the prompt lengths a backend rung has",
    )
    parser.add_argument(
        "--extra-context",
        type=int,
        nargs="*",
        default=[],
        help="further contexts to exercise the operator at, in decode",
    )
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config, groups = audit._profile(args.model_profile)
    window = int(config["window_tokens"])
    profile_body = json.loads(args.model_profile.read_text())
    ranking = {
        int(g["compression_ratio"]): int(g["top_k"]) for g in groups
    }
    census: dict[int, int] = {}
    for ratio in config["compress_ratios"]:
        # ``compress_ratios`` writes the uncompressed layers 0 and
        # ``attention_groups`` writes them 1; this is the mapping
        # check_deepseek_v4_context_gate.layer_table already uses.
        ratio = int(ratio) or 1
        census[ratio] = census.get(ratio, 0) + 1

    # Prompt lengths this ladder actually has rungs for, read from the pins,
    # and the contexts the published ratios are quoted at.
    lengths: dict[int, str] = {}
    headline: set[int] = set()
    for pin_path in args.pins:
        if not Path(pin_path).exists():
            continue
        body = json.loads(pin_path.read_text())
        for value in body.get("context_ladder", []) or []:
            headline.add(int(value))
        if body.get("mandatory_context_tokens"):
            headline.add(int(body["mandatory_context_tokens"]))
        block = body.get("prompts") or body.get("workloads") or {}
        for workload_id, entry in block.items():
            if not isinstance(entry, dict):
                continue
            count = entry.get("prompt_token_count") or entry.get("token_count")
            if count is None and "token_ids" in entry:
                count = len(entry["token_ids"])
            if count:
                lengths[int(count)] = workload_id
    headline.update(int(c) for c in args.extra_context)
    # A profile that states its own maximum context states a headline too.
    for key in ("max_context_tokens", "mandatory_context_tokens"):
        value = (
            config.get(key)
            or profile_body.get(key)
            or profile_body.get("metadata", {}).get(key)
        )
        if value:
            headline.add(int(value))

    # Thresholds, derived per group and never typed in.
    thresholds = {
        str(ratio): {
            "top_k": top_k,
            "ranks_candidates": bool(top_k),
            "layers": census.get(ratio, 0),
            "first_prompt_length_that_prunes": first_pruning_length(ratio, top_k),
            "why_none": (
                None
                if top_k
                else "top_k is 0: the released Attention.__init__ builds no "
                "Indexer for this ratio, so it ranks nothing and no prompt "
                "length makes it discard"
            ),
        }
        for ratio, top_k in sorted(ranking.items())
    }

    # Per pinned prompt length: can the *token* arm see a score defect?
    by_length: dict[str, Any] = {}
    for count in sorted(lengths):
        per_group = {}
        for ratio, top_k in sorted(ranking.items()):
            candidates = count // ratio
            threshold = first_pruning_length(ratio, top_k)
            # How much of the prompt actually exercises the ranking's order:
            # a prefill query at 0-based q sees (q + 1) // ratio candidates, so
            # it prunes only once that exceeds top_k, i.e. from q + 1 >= the
            # threshold.  A rung that only just crosses the threshold prunes in
            # one query and discards one candidate, which is a threshold
            # crossing but a very weak test of the scores.
            pruning_queries = (
                0 if threshold is None else max(0, count - threshold + 1)
            )
            per_group[str(ratio)] = {
                "candidate_groups_at_final_query": candidates,
                "selected_per_query": (
                    min(top_k, candidates) if top_k else candidates
                ),
                "selection_prunes": bool(top_k and candidates > top_k),
                "prefill_queries_that_prune": pruning_queries,
                "prefill_queries_that_prune_fraction": (
                    pruning_queries / count if count else 0.0
                ),
                "candidates_discarded_at_final_query": (
                    max(0, candidates - top_k) if top_k else 0
                ),
                "layers": census.get(ratio, 0),
            }
        visible = any(g["selection_prunes"] for g in per_group.values())
        by_length[lengths[count]] = {
            "prompt_tokens": count,
            "by_compress_ratio": per_group,
            "index_score_can_move_the_token": visible,
            "index_score_can_move_the_kv_counter": False,
            "prefill_queries_that_prune": max(
                (g["prefill_queries_that_prune"] for g in per_group.values()),
                default=0,
            ),
            "candidates_discarded_at_final_query": max(
                (
                    g["candidates_discarded_at_final_query"]
                    for g in per_group.values()
                ),
                default=0,
            ),
        }

    # Executed cases on the device.
    cases: list[dict[str, Any]] = []
    ranking_ratios = [r for r, k in sorted(ranking.items()) if k]
    for ratio in ranking_ratios:
        top_k = ranking[ratio]
        threshold = first_pruning_length(ratio, top_k)
        # Every pinned rung, in prefill: the shape a backend run actually has.
        for count in sorted(lengths):
            cases.append(
                dict(
                    label=f"prefill_ratio{ratio}_{count}",
                    ratio=ratio,
                    top_k=top_k,
                    window=window,
                    span=count,
                    start_pos=0,
                    context=count,
                    seed=args.seed,
                )
            )
        # The headline contexts, in decode, where the span is one and the
        # experiment is cheap.  No backend run reaches these; the operator
        # does.
        for context in (threshold, *sorted(headline)):
            if context is None or context < ratio:
                continue
            cases.append(
                dict(
                    label=f"decode_ratio{ratio}_{context}",
                    ratio=ratio,
                    top_k=top_k,
                    window=window,
                    span=1,
                    start_pos=context - 1,
                    context=context,
                    seed=args.seed,
                )
            )

    executed = [run_pair(**case) for case in cases]
    disagreeing = [c for c in executed if not c["agrees_with_the_position_arithmetic"]]
    counter_blind = all(c["counters_identical_under_different_scores"] for c in executed)

    body = {
        "schema": "opentallas.deepseek_v4_ctx_score_visibility.v1",
        "model_id": profile_body.get("model_id") or args.model_profile.stem,
        "evidence_class": "operator_experiment",
        "seed": args.seed,
        "window_tokens": window,
        "headline_contexts": sorted(headline),
        "layer_census_by_compression_ratio": {
            str(k): v for k, v in sorted(census.items())
        },
        "thresholds": thresholds,
        "by_prompt_length": by_length,
        "executed_cases": executed,
        "case_count": len(executed),
        "all_cases_agree_with_the_position_arithmetic": not disagreeing,
        "disagreeing_cases": disagreeing,
        "kv_counter_is_blind_to_index_scores_at_every_case": bool(counter_blind),
        "conclusion": {
            "counter_arm": (
                "The KV-traffic counter is a function of position arithmetic "
                "alone. It has zero discrimination against a wrong index score "
                "at every context, including the 200,000 and 1,000,000 the "
                "headline ratios are quoted at."
            ),
            "token_arm": (
                "End-to-end token agreement can only see a wrong index score "
                "from the first prompt length at which a ranking layer "
                "discards a candidate. Below it the selected set is the whole "
                "candidate set and ROUTE.INDEX_TOPK emits it sorted ascending, "
                "so neither membership nor order carries score information."
            ),
        },
        "not_a_claim": [
            "index_score_arithmetic_is_correct",
            "accelerator_execution_of_the_whole_model",
            "end_to_end_token_agreement",
            "timing_or_performance",
        ],
        "inputs": {
            "model_profile": _relative(args.model_profile),
            "pins": [_relative(p) for p in args.pins],
            "operator_under_test": "ROUTE.INDEX_TOPK",
            "executed_by": "runtime/sim/engines/route.py on runtime/sim/device.py",
            "reuses": _relative(
                REPO / "tools" / "audit_deepseek_v4_index_selection.py"
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n")
    print(f"wrote {_relative(args.output)}: {len(executed)} cases")
    for case in executed:
        print(
            f"  {case['label']:<28} prunes={str(case['selection_prunes']):<5} "
            f"identical={str(case['emitted_rows_identical_under_different_scores']):<5} "
            f"expected={str(case['expected_emitted_rows_identical']):<5} "
            f"{'OK' if case['agrees_with_the_position_arithmetic'] else 'DISAGREES'}"
        )
    if disagreeing:
        print(f"DISAGREEING CASES: {len(disagreeing)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
