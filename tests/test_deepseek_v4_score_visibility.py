"""The arithmetic behind "this gate cannot see a wrong index score".

`tools/check_deepseek_v4_ctx_score_visibility.py` executes ROUTE.INDEX_TOPK to
show it, which is the evidence.  These are the two derivations that decide
*which* answer the execution is supposed to give, held separately so that a
change to the rule has to change a stated number rather than quietly re-score
the experiment against itself.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "score_visibility",
    REPO / "tools" / "check_deepseek_v4_ctx_score_visibility.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)

PROFILE = REPO / "configs" / "models" / "deepseek-v4-flash-0731.json"


def _flash_csa() -> tuple[int, int]:
    body = json.loads(PROFILE.read_text())
    group = next(
        g for g in body["attention_groups"] if int(g["compression_ratio"]) == 4
    )
    return 4, int(group["top_k"])


def test_a_group_that_ranks_nothing_has_no_pruning_length():
    """`top_k == 0` is the released model building no Indexer at all.

    The first version of the rung rule invented a threshold for exactly this
    case by reading the model-wide `index_topk`; there is no such length.
    """
    assert tool.first_pruning_length(128, 0) is None
    assert tool.first_pruning_length(1, 0) is None


def test_the_pruning_length_is_the_first_prompt_with_more_candidates_than_top_k():
    ratio, top_k = _flash_csa()
    threshold = tool.first_pruning_length(ratio, top_k)
    # One token short, the final query has exactly top_k candidates and keeps
    # them all; at the threshold it has one more than it can keep.
    assert (threshold - 1) // ratio == top_k
    assert threshold // ratio == top_k + 1


def test_gathered_rows_never_reads_a_score():
    """The counter arm's blindness, as arithmetic rather than as a claim.

    `gathered_rows` is the closed form the KV-traffic gate requires the
    executed counters to equal.  Its arguments are a context, a window, a ratio
    and a top_k -- there is no score parameter to pass, which is exactly why no
    score defect can move the counter it gates.
    """
    ratio, top_k = _flash_csa()
    threshold = tool.first_pruning_length(ratio, top_k)
    for context in (129, 160, 256, threshold, 200_000):
        rows = tool.gathered_rows(context, 128, ratio, top_k)
        assert rows == min(context, 128) + min(top_k, context // ratio)


def test_below_the_threshold_every_candidate_is_kept():
    ratio, top_k = _flash_csa()
    threshold = tool.first_pruning_length(ratio, top_k)
    for context in (129, 160, 256, threshold - 1):
        candidates = context // ratio
        assert candidates <= top_k, context
    assert threshold // ratio > top_k


def test_the_committed_artifact_agrees_with_the_operator():
    """The executed artifact must still say what it said when committed."""
    path = REPO / "results" / "abi3" / "deepseek_v4_ctx_score_visibility.json"
    body = json.loads(path.read_text())
    assert body["all_cases_agree_with_the_position_arithmetic"] is True
    assert body["kv_counter_is_blind_to_index_scores_at_every_case"] is True
    reached = {
        c["context"]
        for c in body["executed_cases"]
        if c["phase"] == "prefill"
        and not c["index_score_reaches_the_emitted_rows"]
    }
    # Every rung a backend has run is one where the scores cannot be seen.
    assert {129, 160, 256} <= reached
