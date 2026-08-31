#!/usr/bin/env python3
"""Materialise short *honest prefixes* of the pinned DeepSeek chat workload.

Why this exists
---------------
The only DeepSeek reference-oracle gold in the repository is ``TA-DS-CHAT-1``:
104 prompt tokens, 333 generated tokens
(``results/abi3/deepseek_v4_reference_oracle_short.json``).  A ROM-backend run
at that prompt length takes about seven hours, so every correctness attempt has
a seven-hour turnaround and bisecting a token mismatch is impractical.  A
32-token prompt runs the same lane in about seventy minutes -- but a shorter
prompt is only a *gate* if something independent says what the right answer is
at that length, and nothing did.

So this tool defines the short workloads and nothing else.  It invents no
prompt text.  Each workload is exactly ``TA-DS-CHAT-1``'s pinned token IDs
truncated to the first *n*, which is precisely what the accelerator side does
when it shortens a run (``prompt = workload["token_ids"][: args.tokens]``).
Both sides therefore answer the same question, token for token, and the
comparison means something.

Why it is a separate tool and a separate directory
--------------------------------------------------
``compiler/workloads/deepseek_v4.py`` pins the acceptance workloads and is the
authority on workload identity; these prefixes are a debugging instrument, not
acceptance workloads, and adding them there would put them in the acceptance
set, the program status and every gate that iterates it.  They are written to
their own directory instead, in the same ``index.json`` shape, so
``tools/run_deepseek_v4_reference_oracle.py --workloads`` and any backend
runner can read them without the acceptance set changing shape.

Identity is *not* re-invented here: the digest comes from
:class:`compiler.workloads.deepseek_v4.Workload`, so a change to the digest
rule moves these workloads with the pinned ones instead of silently leaving
them behind.

What is checked before anything is written
------------------------------------------
1. the parent workload's digest still equals :data:`PARENT_DIGEST`;
2. the digest rule, re-applied to the parent's own fields, reproduces that
   digest -- so a prefix digest computed here is computed the same way;
3. every prefix's decoded text is a genuine prefix of the parent's rendered
   text, decoded by the same verified tokenizer that rendered it; and
4. each derived digest equals its entry in :data:`EXPECTED_DIGESTS`, so a
   silent change to the truncation or the parent breaks the build rather than
   producing gold for a question nobody asked.
"""

from __future__ import annotations

import argparse
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
    MODEL_ID,
    OFFICIAL_REPOSITORY,
    OFFICIAL_REVISION,
    Workload,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)

#: The workload these are prefixes of, and its pinned identity.  If this digest
#: moves, the prefixes are prefixes of something else and the gold produced from
#: them is gold for a different question.
PARENT_ID = "TA-DS-CHAT-1"
PARENT_DIGEST = "ee161c0614073a207c3dd08136357cf2317a25f9b6fd68a03c021359fc34f6b5"
PARENT_PROMPT_TOKENS = 104

#: Prompt lengths.  32 is the length a ROM-backend run was measured completing
#: in 4,353 s; 8 is below it so a bisection has somewhere to go.
PREFIX_LENGTHS: tuple[int, ...] = (8, 32)

#: Generation horizon.  The first generated token is what a bisection needs;
#: sixteen gives a short run something to disagree about after it.
PREFIX_MAX_NEW_TOKENS = 16

#: A prefix is not a chat turn -- it stops mid-sentence and there is no
#: assistant marker -- so it does not claim to be one.
PREFIX_KIND = "chat_prefix"

#: Recomputed on every build and required to match.  Filled from the first
#: build; a mismatch means the parent, the truncation or the digest rule moved.
EXPECTED_DIGESTS = {
    "TA-DS-CHAT-1-P8": (
        "7677bf2b45b6e2152d04d9ddbd09e6c5ed8322c7bd90ef0eff979184de5be71e"
    ),
    "TA-DS-CHAT-1-P32": (
        "29463bd6579825c8826b9d6b6168ecd8e99336c11ed0d99652d2d8053b9e42a9"
    ),
}


#: What a short prompt does and does not put pressure on, stated once so the
#: gate is not read as stronger than it is.  The three numbers are the released
#: ``inference/config.json``'s own; the ``context/4`` scan width is this
#: repository's measurement of the indexer (see commit de5c34c).
COMPARATOR_SCOPE = {
    "note": (
        "A prefix gate is a full-depth numeric gate, not a sparsity gate. It "
        "runs all 43 layers, every routed expert the router picks, the "
        "hyper-connections, the compressor, RoPE, the FP8 dense path and the "
        "float32 head -- a wrong constant or a wrong reduction order anywhere "
        "in that moves the first token. What it does NOT put under pressure "
        "is sparse *selection*, because the model's three thresholds all "
        "exceed the context."
    ),
    "window_size": 128,
    "index_topk": 512,
    "compressed_positions_rule": "about context/4 in the compress_ratio=4 layers",
    "at_32_tokens": {
        "window_covers_whole_context": True,
        "index_topk_exceeds_compressed_positions": True,
        "compressed_positions_in_ratio_4_layers": 8,
        "compressed_positions_in_ratio_128_layers": 0,
    },
    "at_104_tokens": {
        "window_covers_whole_context": True,
        "index_topk_exceeds_compressed_positions": True,
        "compressed_positions_in_ratio_4_layers": 26,
        "compressed_positions_in_ratio_128_layers": 0,
    },
    "consequence": (
        "The pinned 104-token workload is already below all three thresholds, "
        "so the 32-token prefix loses no sparsity coverage relative to it: the "
        "only structural difference is how many compressed positions exist in "
        "the compress_ratio=4 layers (8 against 26), and how many positions "
        "the window layers see. Sparse selection under pressure is tested by "
        "the TA-DS-CTX-* ladder, at 1,000 tokens and above, and neither this "
        "nor TA-DS-CHAT-1 substitutes for it."
    ),
}


def workload_id_for(prefix_tokens: int) -> str:
    return f"{PARENT_ID}-P{prefix_tokens}"


def build_prefix_workload(
    parent: dict,
    prefix_tokens: int,
    decode,  # noqa: ANN001
    *,
    max_new_tokens: int = PREFIX_MAX_NEW_TOKENS,
) -> Workload:
    """One prefix workload, with the honesty check that makes it one."""
    ids = tuple(parent["token_ids"][:prefix_tokens])
    if len(ids) != prefix_tokens:
        raise SystemExit(
            f"{PARENT_ID} has only {len(parent['token_ids'])} tokens; cannot "
            f"take a {prefix_tokens}-token prefix"
        )
    text = decode(list(ids))
    if not parent["rendered_text"].startswith(text):
        raise SystemExit(
            f"the decoded {prefix_tokens}-token prefix is not a prefix of "
            f"{PARENT_ID}'s rendered text; this is not an honest prefix.\n"
            f"decoded: {text!r}\nparent:  {parent['rendered_text'][:120]!r}"
        )
    return Workload(
        workload_id=workload_id_for(prefix_tokens),
        kind=PREFIX_KIND,
        description=(
            f"The first {prefix_tokens} pinned token IDs of {PARENT_ID}, "
            "unchanged. A debugging comparator, not an acceptance workload: it "
            "exists so a correctness gate on this model can run in minutes "
            "instead of hours while still asking the same question the "
            "104-token workload asks."
        ),
        rendered_text=text,
        token_ids=ids,
        max_new_tokens=max_new_tokens,
        metadata={
            "derived_from": PARENT_ID,
            "derived_from_digest": PARENT_DIGEST,
            "derived_from_prompt_token_count": len(parent["token_ids"]),
            "prefix_tokens": prefix_tokens,
            "derivation": "token_ids[:prefix_tokens]",
            "acceptance_workload": False,
            "purpose": (
                "reference-oracle gold at a prompt length a backend run can "
                "reach in minutes, so a token mismatch can be bisected"
            ),
        },
    )


def index_document(workloads: dict[str, Workload], **extra) -> dict:  # noqa: ANN003
    """The same ``index.json`` shape the oracle reads for the pinned set."""
    document = {
        "schema": "opentallas.workload_index.v1",
        "model_id": MODEL_ID,
        "source": {
            "repository": OFFICIAL_REPOSITORY,
            "revision": OFFICIAL_REVISION,
        },
        "derived_from": {
            "workload_id": PARENT_ID,
            "digest": PARENT_DIGEST,
            "prompt_token_count": PARENT_PROMPT_TOKENS,
            "rule": "token_ids[:prefix_tokens]",
        },
        "acceptance_set": False,
        "note": (
            "prefixes of a pinned workload, for fast correctness bisection. "
            "They do not extend, replace or weaken the acceptance set in "
            "compiler/workloads/deepseek_v4.py."
        ),
        "workloads": {
            workload_id: {
                "path": f"{workload_id}.json",
                "kind": workload.kind,
                "digest": workload.digest,
                "prompt_token_count": len(workload.token_ids),
                "max_new_tokens": workload.max_new_tokens,
            }
            for workload_id, workload in sorted(workloads.items())
        },
    }
    document.update(extra)
    return document


def _relative(path: Path) -> str:
    if path.is_absolute() and path.is_relative_to(REPO):
        return str(path.relative_to(REPO))
    return str(path)


def reproduction_record(path: Path, gold: dict) -> dict:
    """Whether a second run of the same command produced the same token IDs.

    A gate is only worth building on if the thing it compares against is the
    same every time it is asked.  This is that question answered by running it
    twice rather than by asserting the selection rule is deterministic.
    """
    if not path.exists():
        return {
            "note": f"no reproduction report at {_relative(path)}",
            "identical": None,
        }
    repeat = json.loads(path.read_text())["results"]
    rows = {}
    for workload_id, row in gold.items():
        other = repeat.get(workload_id)
        if other is None:
            rows[workload_id] = {"present_in_reproduction": False}
            continue
        rows[workload_id] = {
            "present_in_reproduction": True,
            "identical_token_ids": (
                other["generated_token_ids"] == row["generated_token_ids"]
            ),
            "same_workload_digest": (
                other["workload_digest"] == row["workload_digest"]
            ),
            "wall_seconds": other["wall_seconds"],
        }
    return {
        "artifact": _relative(path),
        "note": (
            "the same command, the same pinned snapshot, a second process; "
            "only the wall times differ"
        ),
        "identical": all(
            row.get("identical_token_ids") and row.get("same_workload_digest")
            for row in rows.values()
        ),
        "workloads": rows,
    }


def gold_record(
    gold_path: Path,
    workloads: dict[str, Workload],
    reproduction_path: Path | None = None,
) -> dict:
    """Summarise an oracle report into a graded entry, by reading it.

    Every number here is read out of the artifact the entry cites, so the pin
    cannot say something the artifact does not.  The grade is ``executed`` --
    we ran it, and the file holding the numbers is in the repository -- and it
    is never stronger than that: this is an *external comparator*, so the entry
    also carries what it is not, in the same words the report does.

    The per-workload digests in the report must equal the digests built here.
    If they do not, the gold answers a different question than these prompts
    ask and summarising it would be a false attribution, so it is refused.
    """
    if not gold_path.exists():
        return {
            "grade": "assumed",
            "source": "not produced yet",
            "note": (
                f"no oracle report at {gold_path}; run "
                "tools/run_deepseek_v4_reference_oracle.py --workloads "
                "build/workloads/deepseek-v4-flash-0731-prefix"
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
            "vendor_sample_disagreements": entry["vendor_sample_disagreements"],
            "wall_seconds": entry["wall_seconds"],
        }
    return {
        "grade": "executed",
        "artifact": _relative(gold_path),
        "source": (
            "tools/run_deepseek_v4_reference_oracle.py --workloads "
            "build/workloads/deepseek-v4-flash-0731-prefix, on the pinned "
            f"snapshot {report.get('snapshot', '')}"
        ),
        "evidence_class": report.get("evidence_class"),
        "not_a_claim": report.get("not_a_claim"),
        "selection": report.get("selection"),
        "expert_numeric_path": report.get("expert_numeric_path"),
        "total_wall_seconds": report.get("total_wall_seconds"),
        "external_reference_note": (
            "These token IDs are what an external comparator computed. Per "
            "ADR-003 section 18 the oracle supplies no activation to the "
            "accelerator path, produces no accelerator token, and is labelled "
            "an external reference wherever it is quoted. A backend that "
            "reproduces them has agreed with something it did not compute; "
            "the oracle has not executed anything on the accelerator."
        ),
        "comparator_scope": COMPARATOR_SCOPE,
        "reproduction": (
            reproduction_record(reproduction_path, rows)
            if reproduction_path is not None
            else None
        ),
        "workloads": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--pinned-workloads",
        type=Path,
        default=REPO / "build" / "workloads" / "deepseek-v4-flash-0731",
        help="the acceptance workload directory these are prefixes of",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "build" / "workloads" / "deepseek-v4-flash-0731-prefix",
    )
    parser.add_argument(
        "--pin",
        type=Path,
        default=REPO / "results" / "abi3" / "deepseek_v4_prefix_workload_pins.json",
        help=(
            "committed record of the derived token IDs and digests; build/ is "
            "not in the repository, so without this the gold produced from "
            "these workloads would name a prompt nobody could read back"
        ),
    )
    parser.add_argument(
        "--lengths",
        type=int,
        nargs="*",
        default=list(PREFIX_LENGTHS),
    )
    parser.add_argument(
        "--max-new-tokens", type=int, default=PREFIX_MAX_NEW_TOKENS
    )
    parser.add_argument(
        "--gold",
        type=Path,
        default=REPO / "results" / "abi3" / "deepseek_v4_reference_oracle_prefix.json",
        help=(
            "reference-oracle report to summarise into the pin. Read, never "
            "restated by hand: the graded record has to be a reading of the "
            "artifact it cites, or it is a second copy that can drift from it. "
            "Omitted from the pin when the file does not exist yet"
        ),
    )
    parser.add_argument(
        "--gold-reproduction",
        type=Path,
        default=REPO / "results" / "abi3" / "deepseek_v4_prefix_gold_reproduction.json",
        help=(
            "a second, independently executed run of the same command, "
            "compared against --gold token for token. A comparator nobody has "
            "run twice is not yet known to be a comparator"
        ),
    )
    parser.add_argument(
        "--allow-digest-drift",
        action="store_true",
        help=(
            "write even when a derived digest differs from EXPECTED_DIGESTS; "
            "use only when deliberately changing the derivation, and update "
            "the constants in the same commit"
        ),
    )
    args = parser.parse_args()

    parent_index_path = args.pinned_workloads / "index.json"
    if not parent_index_path.exists():
        print(
            f"no workload index at {parent_index_path}; run "
            f"tools/build_deepseek_v4_workloads.py first",
            file=sys.stderr,
        )
        return 1
    parent_index = json.loads(parent_index_path.read_text())
    parent_entry = parent_index["workloads"].get(PARENT_ID)
    if parent_entry is None:
        print(f"{PARENT_ID} is not in {parent_index_path}", file=sys.stderr)
        return 1
    if parent_entry["digest"] != PARENT_DIGEST:
        print(
            f"{PARENT_ID} digest is {parent_entry['digest']}, pinned "
            f"{PARENT_DIGEST}. These prefixes would be prefixes of a different "
            "prompt; refusing.",
            file=sys.stderr,
        )
        return 1
    parent = json.loads((args.pinned_workloads / parent_entry["path"]).read_text())

    # Re-apply the digest rule to the parent's own fields.  If it does not
    # reproduce the pinned digest, then a prefix digest computed here would be
    # computed differently from the way the acceptance set computes one, and
    # the two identities could not be compared.
    rebuilt_parent = Workload(
        workload_id=parent["workload_id"],
        kind=parent["kind"],
        description=parent["description"],
        rendered_text=parent["rendered_text"],
        token_ids=tuple(parent["token_ids"]),
        max_new_tokens=parent["max_new_tokens"],
    )
    if rebuilt_parent.digest != PARENT_DIGEST:
        print(
            "the digest rule in compiler/workloads/deepseek_v4.py no longer "
            f"reproduces {PARENT_ID}'s recorded digest "
            f"({rebuilt_parent.digest} != {PARENT_DIGEST}); refusing",
            file=sys.stderr,
        )
        return 1

    tokenizer = load_verified_deepseek_v4_tokenizer(args.snapshot)
    tokenizer_sha256 = tokenizer.validation_report["source"]["tokenizer_sha256"]
    if tokenizer_sha256 != parent_index["tokenizer_sha256"]:
        print(
            f"tokenizer {tokenizer_sha256} differs from the one that rendered "
            f"the pinned set ({parent_index['tokenizer_sha256']}); refusing",
            file=sys.stderr,
        )
        return 1
    print(
        f"tokenizer verified: vocab={tokenizer.vocab_size} sha256="
        f"{tokenizer_sha256[:16]}",
        flush=True,
    )

    def decode(ids: list[int]) -> str:
        return tokenizer.decode(ids)

    workloads = {}
    for length in sorted(set(args.lengths)):
        workload = build_prefix_workload(
            parent, length, decode, max_new_tokens=args.max_new_tokens
        )
        workloads[workload.workload_id] = workload

    drifted = [
        f"{wid}: built {workload.digest}, expected {EXPECTED_DIGESTS[wid]}"
        for wid, workload in workloads.items()
        if wid in EXPECTED_DIGESTS and workload.digest != EXPECTED_DIGESTS[wid]
    ]
    if drifted and not args.allow_digest_drift:
        print("derived digests moved:", file=sys.stderr)
        for line in drifted:
            print(f"  {line}", file=sys.stderr)
        print(
            "Gold produced from these workloads would answer a different "
            "question than the gold already recorded. Pass "
            "--allow-digest-drift only when the change is deliberate.",
            file=sys.stderr,
        )
        return 1

    args.output.mkdir(parents=True, exist_ok=True)
    for workload_id, workload in sorted(workloads.items()):
        (args.output / f"{workload_id}.json").write_bytes(
            canonical_json(workload.to_dict())
        )
        print(
            f"  {workload_id:20s} {workload.kind:12s} "
            f"{len(workload.token_ids):>5d} tokens  "
            f"max_new={workload.max_new_tokens}  "
            f"digest={workload.digest}"
        )
    (args.output / "index.json").write_bytes(
        canonical_json(
            index_document(workloads, tokenizer_sha256=tokenizer_sha256)
        )
    )
    print(f"\nwrote {len(workloads)} workloads + index to {args.output}")

    if args.pin:
        gold = gold_record(args.gold, workloads, args.gold_reproduction)
        args.pin.parent.mkdir(parents=True, exist_ok=True)
        args.pin.write_bytes(
            canonical_json(
                {
                    "schema": "opentallas.workload_prefix_pin.v1",
                    "gold": gold,
                    "model_id": MODEL_ID,
                    "source": {
                        "repository": OFFICIAL_REPOSITORY,
                        "revision": OFFICIAL_REVISION,
                    },
                    "tokenizer_sha256": tokenizer_sha256,
                    "produced_by": "tools/build_deepseek_v4_prefix_workloads.py",
                    "acceptance_set": False,
                    "note": (
                        "The derived prompts themselves, committed. The "
                        "workload documents live under build/, which is not in "
                        "the repository, so this file is what lets a reader "
                        "check that the gold in "
                        "results/abi3/deepseek_v4_reference_oracle_prefix.json "
                        "was produced from the first n token IDs of "
                        f"{PARENT_ID} and nothing else."
                    ),
                    "derived_from": {
                        "workload_id": PARENT_ID,
                        "digest": PARENT_DIGEST,
                        "prompt_token_count": len(parent["token_ids"]),
                        "rendered_text_sha256": parent["rendered_text_sha256"],
                        "rule": "token_ids[:prefix_tokens]",
                    },
                    "workloads": {
                        workload_id: {
                            "digest": workload.digest,
                            "kind": workload.kind,
                            "prompt_token_count": len(workload.token_ids),
                            "max_new_tokens": workload.max_new_tokens,
                            "prompt_token_ids": list(workload.token_ids),
                            "rendered_text": workload.rendered_text,
                            "is_prefix_of_parent_token_ids": True,
                            "is_prefix_of_parent_rendered_text": True,
                        }
                        for workload_id, workload in sorted(workloads.items())
                    },
                }
            )
        )
        print(f"wrote the committed pin to {args.pin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
