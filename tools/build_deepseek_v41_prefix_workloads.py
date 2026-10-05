#!/usr/bin/env python3
"""Materialise *sub-gate* prefixes of the pinned DeepSeek-V4.1 chat workload.

Why this exists, given that ``TA-DS41-CHAT-1-P32`` is already an acceptance
workload
-----------------------------------------------------------------------------
Plan section 10.1 makes the 32-token prefix V4.1's first executable claim, so it
lives in ``compiler/workloads/deepseek_v41.py`` and is built by
``tools/build_deepseek_v41_workloads.py`` with the rest of the acceptance set.
That leaves the job this tool's V4 predecessor actually does: giving a
*bisection* somewhere to go when the gate disagrees.  A mismatch at 32 tokens
says the first token is wrong; it does not say where.  ``TA-DS41-CHAT-1-P8``
runs the same lane shorter, so the question can be asked again with less of the
prompt in it.

These are debugging comparators and they are not acceptance workloads.  They are
written to their own directory, ``acceptance_set`` false in the index, so
nothing that iterates the acceptance set picks them up - the same separation the
V4 prefixes keep.

Nothing is re-invented
----------------------
The identity, the truncation and the honesty check all come from
:func:`compiler.workloads.deepseek_v41.build_chat_prefix_workload`, so a change
to the digest rule or to what counts as an honest prefix moves these workloads
with the pinned ones instead of silently leaving them behind.  The parent is
read from the materialised acceptance build rather than re-rendered, and its
digest is required to equal the one the acceptance index recorded: a prefix of
something else is gold for a question nobody asked.
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

from compiler.frontend.deepseek_v41_tokenizer import (  # noqa: E402
    load_verified_deepseek_v41_tokenizer,
)
from compiler.workloads.deepseek_v41 import (  # noqa: E402
    MODEL_ID,
    PREFIX_MAX_NEW_TOKENS,
    PREFIX_PROMPT_TOKENS,
    PREFIX_RULE,
    WORKLOAD_ID_PREFIX,
    Workload,
    build_chat_prefix_workload,
    resolve_identity,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

#: The acceptance workload these are prefixes of.
PARENT_ID = f"{WORKLOAD_ID_PREFIX}-CHAT-1"

#: Sub-gate prompt lengths.  Every one of them is below plan section 10.1's
#: :data:`compiler.workloads.deepseek_v41.PREFIX_PROMPT_TOKENS`, because a rung
#: at or above the gate would be a second gate rather than a bisection step.
SUB_GATE_LENGTHS: tuple[int, ...] = (8,)

DEFAULT_ACCEPTANCE_DIR = REPO / "build" / "workloads" / MODEL_ID
DEFAULT_OUTPUT = REPO / "build" / "workloads" / f"{MODEL_ID}-prefix"


def _load_parent(acceptance_dir: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """The parent workload document and the index entry that vouches for it."""

    index_path = acceptance_dir / "index.json"
    parent_path = acceptance_dir / f"{PARENT_ID}.json"
    for path in (index_path, parent_path):
        if not path.exists():
            raise SystemExit(
                f"{path} is missing; run tools/build_deepseek_v41_workloads.py "
                "first, because these prefixes are prefixes of what it wrote"
            )
    index = json.loads(index_path.read_text())
    parent = json.loads(parent_path.read_text())
    recorded = index["workloads"][PARENT_ID]["digest"]
    if parent["digest"] != recorded:
        raise SystemExit(
            f"{parent_path.name} carries digest {parent['digest']} but the "
            f"index records {recorded}; the acceptance build is inconsistent "
            "and a prefix of it would inherit that"
        )
    return parent, index


def _as_workload(document: dict[str, Any]) -> Workload:
    """Rebuild the parent as a :class:`Workload` so the digest rule is reapplied.

    The document's own ``digest`` field is not trusted for this: reconstructing
    the object and recomputing the digest is what proves the rule that produced
    the prefix's identity is the rule that produced the parent's.
    """

    workload = Workload(
        workload_id=document["workload_id"],
        kind=document["kind"],
        description=document["description"],
        rendered_text=document["rendered_text"],
        token_ids=tuple(document["token_ids"]),
        max_new_tokens=document["max_new_tokens"],
        metadata=document.get("metadata", {}),
    )
    if workload.digest != document["digest"]:
        raise SystemExit(
            f"re-applying the digest rule to {document['workload_id']} gives "
            f"{workload.digest}, the document records {document['digest']}; the "
            "digest rule moved and these prefixes would be identified under the "
            "new one while the acceptance set is identified under the old"
        )
    return workload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    identity = resolve_identity()
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=(
            Path.home()
            / ".cache/huggingface/hub"
            / f"models--{identity.repository.replace('/', '--')}"
            / "snapshots"
            / identity.revision
        ),
        help="snapshot to read the verified tokenizer from (default: %(default)s)",
    )
    parser.add_argument(
        "--acceptance-dir",
        type=Path,
        default=DEFAULT_ACCEPTANCE_DIR,
        help="where the acceptance build was written (default: %(default)s)",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT, help="(default: %(default)s)"
    )
    parser.add_argument(
        "--tokens",
        type=int,
        nargs="*",
        default=list(SUB_GATE_LENGTHS),
        help=(
            "prompt lengths to materialise; each must be below the "
            f"{PREFIX_PROMPT_TOKENS}-token gate (default: %(default)s)"
        ),
    )
    parser.add_argument("--max-new-tokens", type=int, default=PREFIX_MAX_NEW_TOKENS)
    args = parser.parse_args()

    lengths = tuple(sorted(set(args.tokens)))
    above = [count for count in lengths if count >= PREFIX_PROMPT_TOKENS]
    if above:
        parser.error(
            f"{above} are at or above plan section 10.1's {PREFIX_PROMPT_TOKENS}"
            "-token gate; a sub-gate prefix is for bisecting below it, and a "
            "rung at the gate belongs in the acceptance module instead"
        )

    document, index = _load_parent(args.acceptance_dir)
    parent = _as_workload(document)
    tokenizer = load_verified_deepseek_v41_tokenizer(args.snapshot)

    workloads = {}
    for count in lengths:
        workload = build_chat_prefix_workload(
            parent,
            lambda ids: tokenizer.decode(ids),
            prefix_tokens=count,
            max_new_tokens=args.max_new_tokens,
        )
        workloads[workload.workload_id] = workload

    args.output.mkdir(parents=True, exist_ok=True)
    for workload_id, workload in sorted(workloads.items()):
        (args.output / f"{workload_id}.json").write_bytes(
            canonical_json(workload.to_dict())
        )
        print(
            f"  {workload_id:24s} {workload.kind:12s} "
            f"{len(workload.token_ids):>7d} tokens  digest={workload.digest[:16]}"
        )
    (args.output / "index.json").write_bytes(
        canonical_json(
            {
                "schema": "opentallas.workload_index.v1",
                "model_id": MODEL_ID,
                "source": index["source"],
                "acceptance_set": False,
                "derived_from": {
                    "workload_id": parent.workload_id,
                    "digest": parent.digest,
                    "prompt_token_count": len(parent.token_ids),
                    "rule": PREFIX_RULE,
                },
                "gate_prefix_tokens": PREFIX_PROMPT_TOKENS,
                "note": (
                    "sub-gate prefixes of a pinned workload, for fast "
                    "correctness bisection below plan section 10.1's "
                    f"{PREFIX_PROMPT_TOKENS}-token gate. They do not extend, "
                    "replace or weaken the acceptance set in "
                    "compiler/workloads/deepseek_v41.py."
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
        )
    )
    print(f"\nwrote {len(workloads)} sub-gate prefixes + index to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
