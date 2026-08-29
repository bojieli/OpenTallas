#!/usr/bin/env python3
"""Materialise the pinned DeepSeek-V4-Flash-0731 workloads.

Writes one JSON document per workload plus an ``index.json`` under
``build/workloads/deepseek-v4-flash-0731``, so the oracle, the deployments and
the cycle model all read the same prompt token IDs by digest instead of
re-encoding a string literal and hoping they agree.

The prompts are rendered by the verified local tokenizer, which runs the
OpenTallas reimplementation of ``encoding/encoding_dsv4.py``.  Unless
``--skip-vendor-crosscheck`` is passed, every rendered prompt is *also* produced
by the vendor module from the snapshot and the two are required to be
byte-identical, so a drift in either renderer fails the build rather than
quietly changing a workload identity.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.deepseek_v4_tokenizer import (  # noqa: E402
    load_verified_deepseek_v4_tokenizer,
)
from compiler.workloads.deepseek_v4 import (  # noqa: E402
    CONTEXT_LADDER,
    LONG_PROMPT_TOKENS,
    build_workloads,
    index_document,
)
from runtime.abi3.capability import canonical_json  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/"
    "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots/"
    "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)


def _vendor_crosscheck(snapshot: Path, workloads) -> dict[str, object]:
    """Re-render the chat and agent prompts with the vendor's own module."""
    encoding_dir = str(snapshot / "encoding")
    if encoding_dir not in sys.path:
        sys.path.insert(0, encoding_dir)
    from encoding_dsv4 import encode_messages as vendor_encode_messages

    from compiler.workloads.deepseek_v4 import (
        AGENT_SYSTEM,
        AGENT_TASK,
        AGENT_TOOLS,
        CHAT_QUESTION,
    )

    cases = {
        "TA-DS-CHAT-1": [{"role": "user", "content": CHAT_QUESTION}],
        "TA-DS-AGENT-1": [
            {
                "role": "system",
                "content": AGENT_SYSTEM,
                "tools": [dict(tool) for tool in AGENT_TOOLS],
            },
            {"role": "user", "content": AGENT_TASK},
        ],
    }
    checked = {}
    for workload_id, messages in cases.items():
        vendor_text = vendor_encode_messages(messages, thinking_mode="chat")
        ours = workloads[workload_id].rendered_text
        if vendor_text != ours:
            raise SystemExit(
                f"{workload_id}: vendor encoding differs from the OpenTallas "
                f"renderer.\nvendor: {vendor_text!r}\nours:   {ours!r}"
            )
        checked[workload_id] = hashlib.sha256(vendor_text.encode()).hexdigest()
    return {
        "vendor_module": "encoding/encoding_dsv4.py",
        "identical": True,
        "rendered_text_sha256": checked,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "build" / "workloads" / "deepseek-v4-flash-0731",
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
            "no machine can execute it"
        ),
    )
    parser.add_argument("--skip-vendor-crosscheck", action="store_true")
    args = parser.parse_args()

    started = time.perf_counter()
    tokenizer = load_verified_deepseek_v4_tokenizer(args.snapshot)
    print(
        f"tokenizer verified: vocab={tokenizer.vocab_size} "
        f"bos={tokenizer.bos_token_id} eos={tokenizer.eos_token_id}",
        flush=True,
    )

    ladder = tuple(sorted(set(args.ladder)))
    workloads = build_workloads(
        tokenizer, max_new_tokens=args.max_new_tokens, ladder=ladder
    )
    print(f"built {len(workloads)} workloads in {time.perf_counter() - started:.1f}s")

    extra: dict[str, object] = {
        "tokenizer_sha256": tokenizer.validation_report["source"]["tokenizer_sha256"],
        "materialised_ladder": list(ladder),
    }
    if not args.skip_vendor_crosscheck:
        extra["vendor_encoding_crosscheck"] = _vendor_crosscheck(
            args.snapshot, workloads
        )
        print("vendor encoding cross-check: identical", flush=True)

    args.output.mkdir(parents=True, exist_ok=True)
    for workload_id, workload in sorted(workloads.items()):
        path = args.output / f"{workload_id}.json"
        path.write_bytes(canonical_json(workload.to_dict()))
        print(
            f"  {workload_id:20s} {workload.kind:16s} "
            f"{len(workload.token_ids):>7d} tokens  digest={workload.digest[:16]}"
        )
    index_path = args.output / "index.json"
    index_path.write_bytes(canonical_json(index_document(workloads, **extra)))
    print(f"\nwrote {len(workloads)} workloads + index to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
