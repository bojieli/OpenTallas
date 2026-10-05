#!/usr/bin/env python3
"""Materialise the pinned DeepSeek-V4.1-Flash workloads.

Writes one JSON document per workload plus an ``index.json`` under
``build/workloads/deepseek-v4.1-flash``, so the oracle, the three deployments
and the cycle model read the same prompt token IDs by digest instead of
re-encoding a string literal and hoping they agree.  It is the V4.1 sibling of
``tools/build_deepseek_v4_workloads.py`` and keeps that tool's shape.

Two things it does that the V4 tool does not have to
---------------------------------------------------
*It supplies the renderer.*  V4.1's prompt grammar is not V4's, and this
repository has no reimplementation of ``encoding/encoding.py`` yet, so the
prompts are rendered by the released module loaded from the authenticated
snapshot.  ``compiler/workloads/deepseek_v41.py`` takes its renderer as a
callable precisely so this is the tool's decision and not the module's, and the
index records the renderer's own SHA-256 next to every prompt it produced.  The
V4 tool cross-checks two renderers against each other and refuses a
disagreement; there is only one here, so ``renderer.independent_crosscheck`` is
recorded false and stays false until a reimplementation lands.

*It proves the prompts against V4's.*  V4.1 renders a plain chat turn
byte-identically to V4 and keeps V4's base vocabulary and merges, so the ladder
rungs and the chat prompt come out as the same token integers as their
``TA-DS-`` counterparts.  That is checked here, against the committed V4
documents when they are present, rather than left as a remark: it is the one
independent statement available about these token IDs while V4.1 has no oracle.
It is a statement about *prompts*, not answers - V4's gold is not V4.1's gold.

Pins
----
``--pins`` writes ``results/abi3/deepseek_v41_workload_pins.json``: the identity
table, the provenance, the tokenizer's verification chain and an explicit
statement of what has *not* been claimed.  Nothing in it is an execution
result; no V4.1 model has been run anywhere in this repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.deepseek_v41_tokenizer import (  # noqa: E402
    TOKENIZER_SHA256,
    VerifiedDeepSeekV41Tokenizer,
    load_verified_deepseek_v41_tokenizer,
)
from compiler.workloads.deepseek_v41 import (  # noqa: E402
    CONTEXT_LADDER,
    LONG_PROMPT_TOKENS,
    MODEL_ID,
    PREFIX_PROMPT_TOKENS,
    WORKLOAD_ID_PREFIX,
    Workload,
    build_workloads,
    index_document,
    resolve_identity,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

#: The released renderer, relative to the snapshot root.  V4 shipped
#: ``encoding/encoding_dsv4.py``; V4.1 renamed it and rewrote the grammar.
VENDOR_ENCODING_RELATIVE = Path("encoding") / "encoding.py"

#: Where the V4 documents this tool proves the prompts against are materialised
#: by ``tools/build_deepseek_v4_workloads.py``.
V4_WORKLOAD_DIR = REPO / "build" / "workloads" / "deepseek-v4-flash-0731"

#: ``TA-DS41-`` id -> the ``TA-DS-`` id whose token IDs it must equal.  Only the
#: prompts V4.1 renders identically are listed: the agent transcript uses V4.1's
#: own DSML tag names and the G1 question has no V4 counterpart.
V4_TOKEN_ID_EQUIVALENCE: dict[str, str] = {
    f"{WORKLOAD_ID_PREFIX}-CHAT-1": "TA-DS-CHAT-1",
    **{
        f"{WORKLOAD_ID_PREFIX}-CTX-{rung // 1000}K-1": f"TA-DS-CTX-{rung // 1000}K-1"
        for rung in CONTEXT_LADDER
    },
}

DEFAULT_PINS = REPO / "results" / "abi3" / "deepseek_v41_workload_pins.json"


def _load_vendor_renderer(snapshot: Path) -> tuple[Callable[..., str], dict[str, Any]]:
    """Import the released V4.1 encoder from the authenticated snapshot."""

    module_path = snapshot / VENDOR_ENCODING_RELATIVE
    if not module_path.exists():
        raise SystemExit(
            f"released renderer missing at {module_path}; the V4.1 prompts "
            "cannot be rendered without it and this tool will not guess at the "
            "grammar"
        )
    payload = module_path.read_bytes()
    directory = str(module_path.parent)
    if directory not in sys.path:
        sys.path.insert(0, directory)
    import encoding as vendor  # noqa: PLC0415

    if Path(vendor.__file__).resolve() != module_path.resolve():
        raise SystemExit(
            f"imported {vendor.__file__}, expected {module_path}; another "
            "module named 'encoding' shadowed the released one"
        )
    identity = {
        "module": str(VENDOR_ENCODING_RELATIVE),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "independent_crosscheck": False,
        "independent_crosscheck_note": (
            "this repository has no reimplementation of V4.1's encoding.py, so "
            "the released module is the only renderer and nothing confronts it. "
            "The V4 program cross-checks compiler/frontend/deepseek_v4_"
            "encoding.py against encoding/encoding_dsv4.py on every build; the "
            "equivalent for V4.1 is unwritten and these prompt identities rest "
            "on vendor code until it exists."
        ),
    }
    return vendor.encode_messages, identity


def _encode_prompt(
    tokenizer: VerifiedDeepSeekV41Tokenizer, render: Callable[..., str]
) -> Callable[[list[dict[str, Any]], str], tuple[str, list[int]]]:
    def encode_prompt(
        messages: list[dict[str, Any]], thinking_mode: str
    ) -> tuple[str, list[int]]:
        text = render(messages, thinking_mode=thinking_mode)
        if not isinstance(text, str):
            raise SystemExit(
                f"the released renderer returned {type(text).__name__}, not a "
                "string; a multimodal return value is not a text prompt"
            )
        return text, tokenizer.encode(text, enforce_max_length=False)

    return encode_prompt


def _v4_prompt_equivalence(workloads: dict[str, Workload]) -> dict[str, Any]:
    """Require the prompts V4.1 renders identically to carry V4's token IDs."""

    checked: dict[str, Any] = {}
    for v41_id, v4_id in sorted(V4_TOKEN_ID_EQUIVALENCE.items()):
        if v41_id not in workloads:
            # A --ladder that omits a rung omits its check; the rung is still
            # defined, it just was not materialised on this run.
            continue
        path = V4_WORKLOAD_DIR / f"{v4_id}.json"
        if not path.exists():
            checked[v41_id] = {
                "counterpart": v4_id,
                "checked": False,
                "reason": (
                    f"{path.relative_to(REPO)} is not materialised; run "
                    "tools/build_deepseek_v4_workloads.py to enable the check"
                ),
            }
            continue
        document = json.loads(path.read_text())
        workload = workloads[v41_id]
        same_ids = list(workload.token_ids) == list(document["token_ids"])
        same_text = workload.rendered_text == document["rendered_text"]
        if not same_ids:
            raise SystemExit(
                f"{v41_id} token IDs differ from {v4_id}'s. V4.1 keeps V4's "
                "base vocabulary and merges and renders a plain chat turn "
                "identically, so a difference here means one of those two "
                "statements stopped being true and the equivalence table is "
                "wrong, not the workload."
            )
        checked[v41_id] = {
            "counterpart": v4_id,
            "checked": True,
            "identical_token_ids": same_ids,
            "identical_rendered_text": same_text,
            "counterpart_digest": document["digest"],
            "digests_differ": document["digest"] != workload.digest,
        }
    return checked


def _pins_document(
    workloads: dict[str, Workload],
    index: dict[str, Any],
    *,
    equivalence: dict[str, Any],
    tokenizer_report: dict[str, Any],
    renderer: dict[str, Any],
    output: Path,
) -> dict[str, Any]:
    return {
        "schema": "opentallas.workload_pins.v1",
        "model_id": MODEL_ID,
        "work_package": (
            "WP-I, docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md section 13"
        ),
        "gate": "DS41-X4",
        "acceptance_set": True,
        "source": index["source"],
        "mandatory_context_tokens": LONG_PROMPT_TOKENS,
        "context_ladder": list(CONTEXT_LADDER),
        "prefix_prompt_tokens": PREFIX_PROMPT_TOKENS,
        "materialised_to": str(output.relative_to(REPO)),
        "workloads": {
            workload_id: {
                "kind": workload.kind,
                "digest": workload.digest,
                "prompt_token_count": len(workload.token_ids),
                "max_new_tokens": workload.max_new_tokens,
                "rendered_text_sha256": hashlib.sha256(
                    workload.rendered_text.encode()
                ).hexdigest(),
                "plan_section": workload.metadata.get("plan_section"),
            }
            for workload_id, workload in sorted(workloads.items())
        },
        "tokenizer": tokenizer_report,
        "renderer": renderer,
        "v4_prompt_equivalence": {
            "claim": (
                "the prompts V4.1 renders identically to V4 carry V4's prompt "
                "token integers, under a different workload identity"
            ),
            "not_a_claim": (
                "that V4's gold is V4.1's gold; the same prompt on different "
                "weights has a different answer"
            ),
            "workloads": equivalence,
        },
        "not_a_claim": [
            "accelerator_execution",
            "artifact_only_execution",
            "reference_oracle_gold",
            "timing_or_performance",
        ],
        "note": (
            "Workloads are inputs, not evidence. Every digest here identifies a "
            "prompt; none of them records a run. No DeepSeek-V4.1 model has "
            "been executed in this repository, the reference oracle is WP-H's, "
            "and the three targets are WP-E, WP-F and WP-G's."
        ),
    }


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
        help=(
            "local snapshot to read the tokenizer and the released renderer "
            "from; it is authenticated by the committed inventory's "
            "config_sha256 (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "build" / "workloads" / MODEL_ID,
        help="directory to write into (default: %(default)s)",
    )
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument(
        "--ladder",
        type=int,
        nargs="*",
        default=list(CONTEXT_LADDER),
        help=(
            "context-ladder rungs to materialise; the mandatory "
            f"{LONG_PROMPT_TOKENS}-token workload is always defined even when "
            "no machine can execute it (default: every rung)"
        ),
    )
    parser.add_argument(
        "--pins",
        type=Path,
        nargs="?",
        const=DEFAULT_PINS,
        default=None,
        help=f"also write the pin record (default path: {DEFAULT_PINS})",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    tokenizer = load_verified_deepseek_v41_tokenizer(args.snapshot)
    report = tokenizer.validation_report
    render, renderer = _load_vendor_renderer(args.snapshot)
    print(
        f"{identity.model_id}: workload ids {WORKLOAD_ID_PREFIX}-*, snapshot "
        f"{args.snapshot}",
        flush=True,
    )
    print(
        f"identity from {', '.join(identity.authority)}; release record "
        f"{identity.release_record or 'absent (WP-B)'}",
        flush=True,
    )
    print(
        f"tokenizer verified: vocab={tokenizer.vocab_size} "
        f"bos={tokenizer.bos_token_id} eos={tokenizer.eos_token_id} "
        f"pad={tokenizer.pad_token_id} sha256={TOKENIZER_SHA256[:16]}",
        flush=True,
    )
    print(
        f"renderer {renderer['module']} sha256={renderer['sha256'][:16]} "
        f"(independent cross-check: {renderer['independent_crosscheck']})",
        flush=True,
    )

    ladder = tuple(sorted(set(args.ladder)))
    workloads = build_workloads(
        tokenizer,
        _encode_prompt(tokenizer, render),
        identity=identity,
        max_new_tokens=args.max_new_tokens,
        ladder=ladder,
    )
    print(f"built {len(workloads)} workloads in {time.perf_counter() - started:.1f}s")

    equivalence = _v4_prompt_equivalence(workloads)
    for workload_id, entry in sorted(equivalence.items()):
        if entry["checked"]:
            print(
                f"  {workload_id:24s} token IDs equal {entry['counterpart']}, "
                f"digests differ: {entry['digests_differ']}"
            )
        else:
            print(f"  {workload_id:24s} not checked: {entry['reason']}")

    index = index_document(
        workloads,
        identity=identity,
        tokenizer=report,
        renderer=renderer,
        materialised_ladder=list(ladder),
        v4_prompt_equivalence=equivalence,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    for workload_id, workload in sorted(workloads.items()):
        path = args.output / f"{workload_id}.json"
        path.write_bytes(canonical_json(workload.to_dict()))
        print(
            f"  {workload_id:24s} {workload.kind:12s} "
            f"{len(workload.token_ids):>7d} tokens  digest={workload.digest[:16]}"
        )
    (args.output / "index.json").write_bytes(canonical_json(index))
    print(f"\nwrote {len(workloads)} workloads + index to {args.output}")

    if args.pins is not None:
        args.pins.parent.mkdir(parents=True, exist_ok=True)
        args.pins.write_bytes(
            canonical_json(
                _pins_document(
                    workloads,
                    index,
                    equivalence=equivalence,
                    tokenizer_report=report,
                    renderer=renderer,
                    output=args.output,
                )
            )
        )
        print(f"wrote pins to {args.pins}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
