#!/usr/bin/env python3
"""Materialise the pinned DeepSeek-V4 workloads.

Writes one JSON document per workload plus an ``index.json`` under
``build/workloads/<model id>``, so the oracle, the deployments and the cycle
model all read the same prompt token IDs by digest instead of re-encoding a
string literal and hoping they agree.

``--model`` selects the release.  It defaults to ``deepseek-v4-flash-0731``,
which builds exactly what it always built: the Flash documents are byte-for-byte
what they were before this tool learned a second release, and
``tests/compiler/test_deepseek_v4_workload_ladder.py`` pins their digests.
``deepseek-v4-pro-0813`` builds the same ladder under Pro's own identity, with
``TA-DSP-*`` workload ids, Pro's snapshot and checkpoint source, and Pro's
output directory.  The two releases ship the same ``tokenizer.json``, so a
rung's prompt token IDs are the same integers on both sides; the workload
digests are not, because a digest covers the workload id.

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
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.frontend.deepseek_v4_releases import (  # noqa: E402
    RELEASES,
    DeepSeekV4Release,
    DeepSeekV4ReleaseError,
    resolve_release,
)
from compiler.frontend.deepseek_v4_tokenizer import (  # noqa: E402
    load_verified_deepseek_v4_tokenizer,
)
from compiler.workloads.deepseek_v4 import (  # noqa: E402
    CONTEXT_LADDER,
    DEFAULT_MODEL_ID,
    LONG_PROMPT_TOKENS,
    build_workloads,
    index_document,
    workload_id_prefix,
)
from runtime.abi3.capability import canonical_json  # noqa: E402


def _release(value: str) -> DeepSeekV4Release:
    """An ``argparse`` type that refuses a release this front end does not carry."""
    try:
        return resolve_release(value)
    except DeepSeekV4ReleaseError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _vendor_crosscheck(
    snapshot: Path, workloads, prefix: str
) -> dict[str, object]:
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
        f"{prefix}-CHAT-1": [{"role": "user", "content": CHAT_QUESTION}],
        f"{prefix}-AGENT-1": [
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
    parser.add_argument(
        "--model",
        type=_release,
        default=DEFAULT_MODEL_ID,
        help=(
            "which pinned release to build for; the tokenizer source, the "
            "output directory and the workload-id prefix all follow it. "
            f"one of {', '.join(sorted(RELEASES))} (default: %(default)s)"
        ),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="local snapshot to read the tokenizer from (default: the release's)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="directory to write into (default: build/workloads/<model id>)",
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

    release = resolve_release(args.model)
    prefix = workload_id_prefix(release)
    snapshot = args.snapshot if args.snapshot is not None else release.snapshot
    # An overridden snapshot is bound to the named release by content, not by
    # the path's spelling.  The two DeepSeek-V4 releases ship byte-identical
    # tokenizer.json, tokenizer_config.json and encoding/ modules, so every
    # digest this builder verifies would pass against the wrong snapshot and
    # the index would carry one release's provenance over the other's bytes.
    # The released config is what actually differs, so it is what is checked.
    if args.snapshot is not None:
        observed = hashlib.sha256((snapshot / "config.json").read_bytes()).hexdigest()
        if observed != release.config_sha256:
            parser.error(
                f"--snapshot {snapshot} holds config.json {observed}, which is "
                f"not {release.model_id}'s {release.config_sha256}; the two "
                "DeepSeek-V4 releases share their tokenizer and encoding bytes, "
                "so only the released config distinguishes their snapshots"
            )
    output = (
        args.output
        if args.output is not None
        else REPO / "build" / "workloads" / release.model_id
    )

    started = time.perf_counter()
    tokenizer = load_verified_deepseek_v4_tokenizer(snapshot, release=release)
    print(
        f"{release.model_id}: workload ids {prefix}-*, snapshot {snapshot}",
        flush=True,
    )
    print(
        f"tokenizer verified: vocab={tokenizer.vocab_size} "
        f"bos={tokenizer.bos_token_id} eos={tokenizer.eos_token_id}",
        flush=True,
    )

    ladder = tuple(sorted(set(args.ladder)))
    workloads = build_workloads(
        tokenizer,
        release=release,
        max_new_tokens=args.max_new_tokens,
        ladder=ladder,
    )
    print(f"built {len(workloads)} workloads in {time.perf_counter() - started:.1f}s")

    extra: dict[str, object] = {
        "tokenizer_sha256": tokenizer.validation_report["source"]["tokenizer_sha256"],
        "materialised_ladder": list(ladder),
    }
    if not args.skip_vendor_crosscheck:
        extra["vendor_encoding_crosscheck"] = _vendor_crosscheck(
            snapshot, workloads, prefix
        )
        print("vendor encoding cross-check: identical", flush=True)

    output.mkdir(parents=True, exist_ok=True)
    for workload_id, workload in sorted(workloads.items()):
        path = output / f"{workload_id}.json"
        path.write_bytes(canonical_json(workload.to_dict()))
        print(
            f"  {workload_id:20s} {workload.kind:16s} "
            f"{len(workload.token_ids):>7d} tokens  digest={workload.digest[:16]}"
        )
    index_path = output / "index.json"
    index_path.write_bytes(
        canonical_json(index_document(workloads, release=release, **extra))
    )
    print(f"\nwrote {len(workloads)} workloads + index to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
