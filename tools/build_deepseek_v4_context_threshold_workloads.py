#!/usr/bin/env python3
"""Materialise the ``TA-DS-CTX-*`` rungs that *cross a sparsity threshold*.

Why this exists
---------------
DeepSeek-V4-Flash's attention is sparse, and its sparsity has three thresholds:
a ``window_tokens`` sliding window, an ``index_topk`` selection width, and the
per-layer ``compress_ratios``.  Below all three the model is dense in
everything but name.  Every DeepSeek correctness gate this repository had ever
run -- ``TA-DS-CHAT-1`` at 104 tokens and its 32-token prefix -- sits below all
three, so **no gate had ever executed a sparse selection**, while the headline
ROM-versus-HBM ratios are quoted at 200,000 and 1,000,000 tokens where sparse
selection decides essentially every byte moved.

The existing ``TA-DS-CTX-*`` ladder starts at 1,000 tokens.  Its lowest rung is
already a ~31x longer prompt than the only prompt a backend has ever completed,
and backend cost grows at least linearly with it: the 32-token ROM run took
4,353 s.  So the ladder as it stood could state the problem and not gate it.

This tool adds the rungs *between* -- the shortest prompt that crosses each
threshold, so that a gate exists at a length a backend run can actually reach,
and so that the length at which the remaining threshold starts to bite is a
number in a file rather than an estimate in prose.

The rungs are derived, not chosen
---------------------------------
Every rung length is computed from the pinned operator configuration in
``configs/models/deepseek-v4-flash-0731.json`` -- ``window_tokens``,
``index_topk`` and ``compress_ratios`` -- by :func:`threshold_rungs`.  Nothing
here is a hand-typed prompt length.  If the released configuration changes, the
ladder moves with it and the pinned digests below stop matching, which fails
the build instead of quietly gating a different regime.

Identity is not re-invented: each rung is built by
``compiler.workloads.deepseek_v4.build_context_workload`` from the same pinned
public-domain corpus and the same digest rule as the 1,000-to-200,000 ladder,
so these are lower rungs *of that ladder* and not a different question.

What is checked before anything is written
------------------------------------------
1. the pinned operator configuration still holds the three constants the rung
   rule reads, and the rule reproduces :data:`EXPECTED_RUNGS` from them;
2. each rung's rendered text is a genuine prefix of every longer rung's, and of
   the committed ``TA-DS-CTX-1K-1`` text where that rung is the longer of the
   two, so the ladder is nested prose and not different prose; and
3. each derived digest equals its entry in :data:`EXPECTED_DIGESTS`.

Token streams are *not* required to nest, and the index records how far each
pair actually agrees.  Nesting the text does not nest the tokens: the tokenizer
re-merges across a truncation boundary, so the 129-token rung agrees with the
committed 1,000-token rung for 127 tokens and then differs, while the 160-token
rung agrees for all 160.  Requiring token nesting would be requiring something
the committed ladder never had -- ``TA-DS-CTX-1K-1`` and ``TA-DS-CTX-8K-1`` do
not nest either -- so it is measured and reported instead of asserted.  Each
rung's gold is produced for that rung's own token IDs, which is what makes the
comparison sound; nesting would only have helped a bisection.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.deepseek_v4_tokenizer import (  # noqa: E402
    load_verified_deepseek_v4_tokenizer,
)
from compiler.workloads.deepseek_v4 import (  # noqa: E402
    CONTEXT_LADDER,
    Workload,
    build_context_workload,
    index_document,
)
from compiler.workloads.qwen3 import load_corpus, natural_body  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)
MODEL_PROFILE = REPO / "configs" / "models" / "deepseek-v4-flash-0731.json"

#: The committed 1,000-token rung.  Every rung built here must be a prefix of
#: it, which is what makes them lower rungs of the same ladder.
PARENT_RUNG = REPO / "build/workloads/deepseek-v4-flash-0731/TA-DS-CTX-1K-1.json"

#: Generation horizon.  The first generated token is the gate; eight matches
#: the horizon the committed ladder's gold was produced at, so a rung built
#: here and a rung already on the ladder are compared the same way.
THRESHOLD_MAX_NEW_TOKENS = 8


def _profile(profile: Path) -> tuple[dict, list[dict]]:
    """The pinned operator config and the pinned per-attention-group profile.

    Both are needed and neither is sufficient.  ``operator_config`` carries
    ``index_topk`` as a single model-wide number; ``attention_groups`` carries
    the ``top_k`` that each group of layers actually applies -- and they are
    not the same statement.  See :func:`threshold_rungs`.
    """

    body = json.loads(profile.read_text())
    groups = body["attention_groups"]
    config = body["metadata"]["operator_config"]
    ratios = [int(r) for r in config["compress_ratios"]]
    counted = {int(g["compression_ratio"]): int(g["count"]) for g in groups}
    from_ratios: dict[int, int] = {}
    for ratio in ratios:
        # compress_ratio 0 in operator_config is compression_ratio 1 in
        # attention_groups: both name a layer that compresses nothing.
        from_ratios[ratio or 1] = from_ratios.get(ratio or 1, 0) + 1
    if counted != from_ratios:
        raise SystemExit(
            "attention_groups and operator_config.compress_ratios disagree "
            f"about the layer census: {counted} against {from_ratios}. One of "
            "the two pinned statements about this model is stale, and a rung "
            "derived from either would gate the wrong layers."
        )
    return config, groups


def threshold_rungs(config: dict, groups: list[dict]) -> dict[str, dict]:
    """The shortest prompt that crosses each sparsity threshold.

    Each entry states the length *and the reason*, both derived from the pinned
    profile.  ``linear_backend_estimate_seconds`` is this program's compute
    budget talking and is never used to decide what is correct.

    **``index_topk`` is not model-wide.**  ``operator_config`` states one
    ``index_topk`` and it is tempting to apply it to every compressing layer.
    The released model does not: ``Attention.__init__`` builds an ``Indexer``
    only when ``compress_ratio == 4``, and ``Attention.forward`` falls back to
    ``get_compress_topk_idxs`` otherwise -- which enumerates *every* completed
    compressed group with no ranking and no ``top_k``.  The pinned profile
    already says so, in ``attention_groups``: the ``compression_ratio=4`` group
    carries ``top_k: 512`` and ``kind: compressed_sparse``, the
    ``compression_ratio=128`` group carries ``top_k: 0`` and
    ``kind: compressed_dense``.  So the rungs are derived from the per-group
    ``top_k``, and a group that ranks nothing contributes no pruning rung at
    any context.
    """

    window = int(config["window_tokens"])
    ratios = sorted({int(r) for r in config["compress_ratios"] if int(r)})
    if not ratios:
        raise SystemExit("operator_config declares no non-zero compression ratio")
    fine, coarse = min(ratios), max(ratios)
    ranking = {
        int(g["compression_ratio"]): int(g["top_k"])
        for g in groups
        if int(g["top_k"]) > 0
    }
    rungs: dict[str, dict] = {}

    rungs["window_and_coarse_first_group"] = {
        "tokens": max(window, coarse) + 1,
        "crosses": [
            f"sliding window: a query at position {window} can no longer see "
            f"position 0, so the {window}-token window excludes a position "
            "for the first time",
            f"compress_ratio={coarse} layers hold their first completed "
            f"compressed group ({(max(window, coarse) + 1) // coarse}); below "
            "this length those layers are pure sliding-window attention",
        ],
    }
    rungs["window_clipping_with_split_write"] = {
        "tokens": window + window // fine,
        "crosses": [
            f"the sliding window excludes a position for {window // fine} "
            "queries rather than one",
            "the prefill circular-window commit splits at a non-zero cutoff "
            f"({(window + window // fine) % window})",
        ],
    }
    rungs["window_wrap_zero_cutoff"] = {
        "tokens": 2 * window,
        "crosses": [
            "the prefill circular-window commit lands on a zero cutoff, the "
            "boundary case of the split",
            f"compress_ratio={coarse} layers hold {2 * window // coarse} "
            "compressed groups",
        ],
    }
    for ratio, topk in sorted(ranking.items()):
        rungs[f"index_topk_prunes_ratio_{ratio}"] = {
            "tokens": ratio * (topk + 1),
            "crosses": [
                f"top_k={topk} becomes a *restriction* in the "
                f"compress_ratio={ratio} layers: {topk + 1} candidates, "
                f"{topk} selected, so selection discards a candidate for the "
                "first time. Below this length the ranking runs but keeps "
                "everything it ranks, so nothing depends on its order",
            ],
        }
    # Backend affordability, from the one measured backend run.
    measured_tokens, measured_seconds = 32, 4353.4
    for entry in rungs.values():
        entry["linear_backend_estimate_seconds"] = round(
            entry["tokens"] * measured_seconds / measured_tokens, 1
        )
        entry["estimate_basis"] = (
            "linear in prompt tokens from the one completed backend run: "
            f"{measured_tokens} tokens in {measured_seconds} s "
            "(results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32_raw.json). "
            "Attention cost is superlinear, so this is a floor, not a forecast."
        )
    return rungs


def groups_without_ranking(groups: list[dict]) -> list[int]:
    """Compression ratios whose layers rank nothing, so never prune.

    ``top_k: 0`` in the pinned profile is the released ``indexer is None``
    branch: every completed compressed group is taken, at every context, so
    there is no length at which selection starts discarding in these layers.
    They are not a weaker version of the ranked layers -- they are a different
    operator, and the ladder must not imply a pruning rung for them.
    """

    return sorted(
        int(g["compression_ratio"])
        for g in groups
        if int(g["compression_ratio"]) > 1 and int(g["top_k"]) == 0
    )


#: Recomputed from the pinned profile on every build and required to match.
EXPECTED_RUNGS = {
    "window_and_coarse_first_group": 129,
    "window_clipping_with_split_write": 160,
    "window_wrap_zero_cutoff": 256,
    "index_topk_prunes_ratio_4": 2052,
}

#: Rungs materialised by default: the three a backend run can plausibly reach,
#: plus the first ``index_topk`` pruning rung, which the oracle can reach even
#: though a backend run at that length is roughly 77 hours at the measured
#: cost.  Gold that exists is worth more than gold that does not, and the rung
#: it gates is exactly the regime the 200,000-token claims live in.
DEFAULT_RUNGS = (
    "window_and_coarse_first_group",
    "window_clipping_with_split_write",
    "window_wrap_zero_cutoff",
    "index_topk_prunes_ratio_4",
)

#: Filled from the first build; a mismatch means the corpus, the rung rule or
#: the digest rule moved and the gold produced from these is gold for a
#: different question.
EXPECTED_DIGESTS: dict[str, str] = {
    "TA-DS-CTX-129-1": (
        "8936f3f5e28f74e677fe316f9946499010f36c4f39aa7bf85228288248af6854"
    ),
    "TA-DS-CTX-160-1": (
        "c13d424dedf40354567ee2bf0df6f37c8b93c6754168243000d23430045bdaf7"
    ),
    "TA-DS-CTX-256-1": (
        "eb8d0741b0a106fa6cf1123fa62d81f3a345780fb36b197911b63e0dc154d013"
    ),
    "TA-DS-CTX-2052-1": (
        "8af40565a2b867e7e233bfc00be5a71eb2725f949fb27f43386c2200086278af"
    ),
}


def sparsity_profile(tokens: int, config: dict, groups: list[dict]) -> dict:
    """What sparsity actually does at this context, from the pinned profile.

    Every number here is arithmetic on the committed profile; none is measured
    and none is asserted about the accelerator.  ``selected`` follows the
    released ``Attention.forward``: a group with a ranking selects
    ``min(top_k, end_pos // ratio)``, and a group without one selects every
    completed group.
    """

    window = int(config["window_tokens"])
    ratios = [int(r) for r in config["compress_ratios"]]
    per_ratio = {}
    for group in sorted(groups, key=lambda g: int(g["compression_ratio"])):
        ratio = int(group["compression_ratio"])
        if ratio <= 1:
            continue
        topk = int(group["top_k"])
        candidates = tokens // ratio
        per_ratio[str(ratio)] = {
            "layers": int(group["count"]),
            "kind": group["kind"],
            "ranks_candidates": topk > 0,
            "top_k": topk,
            "candidate_compressed_groups_at_final_query": candidates,
            "selected": min(topk, candidates) if topk else candidates,
            "selection_prunes": bool(topk) and candidates > topk,
        }
    return {
        "prompt_tokens": tokens,
        "window_tokens": window,
        "window_excludes_a_position": tokens > window,
        "queries_whose_window_excludes_a_position": max(0, tokens - window),
        "prefill_circular_commit_cutoff": (tokens % window) if tokens > window else None,
        "dense_layers_without_compression": sum(1 for r in ratios if not r),
        "by_compress_ratio": per_ratio,
    }


def gold_record(gold_path: Path, workloads: dict[str, Workload]) -> dict:
    """Summarise the oracle report into a graded entry, by reading it.

    Every number is read out of the artifact the entry cites, so the pin cannot
    say something the artifact does not.  The per-workload digests in the
    report must equal the digests built here; if they do not, that gold is gold
    for a different prompt and summarising it would be a false attribution.
    """

    if not gold_path.exists():
        return {
            "grade": "assumed",
            "source": "not produced yet",
            "note": (
                f"no oracle report at {gold_path}; run "
                "tools/run_deepseek_v4_reference_oracle.py --workloads "
                "build/workloads/deepseek-v4-flash-0731-threshold "
                "--engine-per-workload"
            ),
        }
    report = json.loads(gold_path.read_text())
    results = report.get("results", {})
    rows = {}
    for workload_id, workload in sorted(workloads.items()):
        entry = results.get(workload_id)
        if entry is None:
            continue
        if entry["workload_digest"] != workload.digest:
            raise SystemExit(
                f"{gold_path}: {workload_id} was produced from digest "
                f"{entry['workload_digest']}, but this build produces "
                f"{workload.digest}. That gold is gold for a different prompt."
            )
        rows[workload_id] = {
            "workload_digest": entry["workload_digest"],
            "prompt_token_count": entry["prompt_token_count"],
            "generated_token_ids": entry["generated_token_ids"],
            "first_generated_token_id": entry["generated_token_ids"][0],
            "generated_token_count": entry["generated_token_count"],
            "stop_reason": entry["stop_reason"],
            "visible_decoded_text": entry["visible_decoded_text"],
            "expert_numeric_path": entry["expert_numeric_path"],
            "wall_seconds": entry["wall_seconds"],
        }
    return {
        "grade": "executed",
        "artifact": str(gold_path.relative_to(REPO)),
        "source": (
            "tools/run_deepseek_v4_reference_oracle.py --workloads "
            "build/workloads/deepseek-v4-flash-0731-threshold "
            "--engine-per-workload --measure-kv, on the pinned snapshot "
            f"{report.get('snapshot', '')}"
        ),
        "evidence_class": report.get("evidence_class"),
        "selection": report.get("selection"),
        "not_a_claim": report.get("not_a_claim"),
        "external_reference_note": (
            "These token IDs are what an external comparator computed. Per "
            "ADR-003 section 18 the oracle supplies no activation to the "
            "accelerator path, produces no accelerator token, and is labelled "
            "an external reference wherever it is quoted."
        ),
        "workloads": rows,
    }


def _require_text_nested(shorter: Workload, longer: Workload) -> None:
    """The identity rule: every rung is a text window of the same corpus."""
    if not longer.rendered_text.startswith(shorter.rendered_text):
        raise SystemExit(
            f"{shorter.workload_id}'s text is not a prefix of "
            f"{longer.workload_id}'s; the ladder is not nested prose"
        )


def token_prefix_agreement(shorter: Workload, longer: Workload) -> int:
    """How many leading token IDs the two rungs share.

    Reported, never required.  A shortfall is the tokenizer re-merging across
    the truncation boundary, not a defect.
    """
    agreed = 0
    for left, right in zip(shorter.token_ids, longer.token_ids):
        if left != right:
            break
        agreed += 1
    return agreed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--model-profile", type=Path, default=MODEL_PROFILE)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "build" / "workloads" / "deepseek-v4-flash-0731-threshold",
    )
    parser.add_argument(
        "--rungs",
        nargs="*",
        default=list(DEFAULT_RUNGS),
        help="rung names from threshold_rungs() to materialise",
    )
    parser.add_argument(
        "--pin",
        type=Path,
        default=REPO
        / "results"
        / "abi3"
        / "deepseek_v4_context_threshold_workload_pins.json",
        help=(
            "committed record of the derived token IDs, digests and sparsity "
            "arithmetic; build/ is not in the repository, so without this the "
            "gold produced from these workloads would name a prompt nobody "
            "could read back"
        ),
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=REPO
        / "results"
        / "abi3"
        / "deepseek_v4_reference_oracle_threshold.json",
        help=(
            "reference-oracle report to summarise into the pin. Read, never "
            "restated by hand: a graded record has to be a reading of the "
            "artifact it cites, or it is a second copy that can drift from it"
        ),
    )
    parser.add_argument(
        "--print-digests",
        action="store_true",
        help="print the computed digests and exit without writing or checking",
    )
    args = parser.parse_args()

    config, groups = _profile(args.model_profile)
    rungs = threshold_rungs(config, groups)
    derived = {name: entry["tokens"] for name, entry in rungs.items()}
    if derived != EXPECTED_RUNGS:
        raise SystemExit(
            "the rung rule no longer reproduces the pinned rungs: "
            f"{derived} against {EXPECTED_RUNGS}. The released operator "
            "configuration moved, so these workloads gate a different regime."
        )
    unknown = sorted(set(args.rungs) - set(rungs))
    if unknown:
        raise SystemExit(f"unknown rung name(s): {unknown}; have {sorted(rungs)}")

    tokenizer = load_verified_deepseek_v4_tokenizer(args.snapshot)

    def encode(text: str) -> list[int]:
        return tokenizer.encode(text, enforce_max_length=False)

    body = natural_body(load_corpus())
    lengths = sorted({rungs[name]["tokens"] for name in args.rungs})
    built = [
        build_context_workload(
            encode, tokens, body, max_new_tokens=THRESHOLD_MAX_NEW_TOKENS
        )
        for tokens in lengths
    ]
    for shorter, longer in zip(built, built[1:]):
        _require_text_nested(shorter, longer)

    parent = json.loads(PARENT_RUNG.read_text())
    parent_workload = Workload(
        workload_id=parent["workload_id"],
        kind=parent["kind"],
        description=parent["description"],
        rendered_text=parent["rendered_text"],
        token_ids=tuple(parent["token_ids"]),
        max_new_tokens=parent["max_new_tokens"],
    )
    agreement = {}
    for rung in built:
        if len(rung.token_ids) < len(parent_workload.token_ids):
            _require_text_nested(rung, parent_workload)
            agreement[rung.workload_id] = token_prefix_agreement(
                rung, parent_workload
            )
        else:
            _require_text_nested(parent_workload, rung)
            agreement[rung.workload_id] = token_prefix_agreement(
                parent_workload, rung
            )

    digests = {rung.workload_id: rung.digest for rung in built}
    if args.print_digests:
        print(json.dumps(digests, indent=1, sort_keys=True))
        return 0
    for workload_id, digest in digests.items():
        expected = EXPECTED_DIGESTS.get(workload_id)
        if expected is None:
            raise SystemExit(
                f"{workload_id} has no pinned digest; add {digest!r} to "
                "EXPECTED_DIGESTS after checking the build is the one you want"
            )
        if expected != digest:
            raise SystemExit(
                f"{workload_id} digest {digest} does not match the pinned "
                f"{expected}: the corpus, the rung rule or the digest rule "
                "moved"
            )

    args.output.mkdir(parents=True, exist_ok=True)
    for rung in built:
        (args.output / f"{rung.workload_id}.json").write_text(
            canonical_json(rung.to_dict()).decode()
        )
    index = index_document(
        {rung.workload_id: rung for rung in built},
        acceptance_set=False,
        purpose=(
            "The shortest TA-DS-CTX rungs that cross a sparse-attention "
            "threshold. The committed ladder starts at 1,000 tokens, which no "
            "backend run can reach; these exist so that sparse selection has "
            "a gate at all."
        ),
        derived_from={
            "rule": "tools/build_deepseek_v4_context_threshold_workloads.py::threshold_rungs",
            "operator_config_source": str(args.model_profile.relative_to(REPO)),
            "parent_rung": str(PARENT_RUNG.relative_to(REPO)),
            "committed_ladder": list(CONTEXT_LADDER),
        },
        rungs={name: rungs[name] for name in sorted(args.rungs)},
        sparsity_profile={
            rung.workload_id: sparsity_profile(
                len(rung.token_ids), config, groups
            )
            for rung in built
        },
        no_pruning_rung_for_compression_ratios={
            "ratios": groups_without_ranking(groups),
            "why": (
                "these layers carry top_k=0 in the pinned attention_groups, "
                "which is the released Attention.__init__ building no Indexer "
                "for them. They enumerate every completed compressed group at "
                "every context, so no prompt length makes selection start "
                "discarding in them. Applying the model-wide operator_config "
                "index_topk to them would invent a threshold the model does "
                "not have."
            ),
        },
        token_prefix_agreement_with_parent_rung={
            "note": (
                "leading token IDs shared with " + parent_workload.workload_id
                + ", measured. Nesting the prose does not nest the tokens; a "
                "shortfall is the tokenizer re-merging at the boundary and is "
                "not a defect. Each rung's gold is produced for its own token "
                "IDs."
            ),
            "parent_prompt_tokens": len(parent_workload.token_ids),
            "agreed": agreement,
        },
        tokenizer_sha256=tokenizer.validation_report["source"]["tokenizer_sha256"],
    )
    (args.output / "index.json").write_text(canonical_json(index).decode())
    for rung in built:
        print(
            f"{rung.workload_id}: {len(rung.token_ids)} tokens, "
            f"digest {rung.digest}"
        )
    print(f"wrote {len(built)} workloads to {args.output}")

    if args.pin:
        pin = dict(index)
        pin["schema"] = "opentallas.workload_context_threshold_pin.v1"
        pin["produced_by"] = (
            "tools/build_deepseek_v4_context_threshold_workloads.py"
        )
        pin["gold"] = gold_record(args.gold, {r.workload_id: r for r in built})
        pin["prompts"] = {
            rung.workload_id: {
                "digest": rung.digest,
                "prompt_token_count": len(rung.token_ids),
                "max_new_tokens": rung.max_new_tokens,
                "rendered_text_sha256": hashlib.sha256(
                    rung.rendered_text.encode()
                ).hexdigest(),
                "token_ids": list(rung.token_ids),
            }
            for rung in built
        }
        pin["note"] = (
            "The derived prompts themselves, committed. The workload "
            "documents live under build/, which is not in the repository, so "
            "this file is what lets a reader check that the gold in "
            "results/abi3/deepseek_v4_reference_oracle_threshold.json and any "
            "accelerator record citing these workload IDs answer the same "
            "question."
        )
        args.pin.parent.mkdir(parents=True, exist_ok=True)
        args.pin.write_text(canonical_json(pin).decode())
        print(f"pinned {args.pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
