#!/usr/bin/env python3
"""Build the DeepSeek-V4-Flash-0731 Tensor Kernel IR v3 document.

The front end lives in ``compiler/frontends/v3/deepseek_v4.py``; this tool only
selects a profile, writes the canonical JSON and prints the census a release
report quotes.  Two runs with the same arguments produce byte-identical output
and the same ``graph_id``.

    python3 tools/build_deepseek_v4_kernel_ir_v3.py \\
        --output build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from compiler.frontend.deepseek_v4 import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_SOURCE,
    MODEL_ID,
)
from compiler.frontends.v3.deepseek_v4 import (  # noqa: E402
    DEFAULT_CHECKPOINT_LOCK,
    DEFAULT_CONTEXT_TOKENS,
    DEFAULT_SNAPSHOT,
    DeepSeekV4KernelIRError,
    export_deepseek_v4_kernel_graph,
    graph_census,
    verify_checkpoint_bindings,
)

DEFAULT_OUTPUT = REPOSITORY_ROOT / "build" / "ir-v3" / MODEL_ID / "kernel_ir.v3.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--checkpoint-lock", type=Path, default=DEFAULT_CHECKPOINT_LOCK
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--context-tokens",
        type=int,
        default=DEFAULT_CONTEXT_TOKENS,
        help="deployment context maximum (architectural endpoint is 1048576)",
    )
    parser.add_argument(
        "--maximum-new-tokens",
        type=int,
        default=None,
        help="generation-policy bound; defaults to the deployment context",
    )
    parser.add_argument(
        "--include-speculative",
        action="store_true",
        help=(
            "add the three DSpark draft blocks, the Markov draft head and the "
            "confidence head; the first release profile leaves them out"
        ),
    )
    parser.add_argument(
        "--verify-bindings",
        type=int,
        default=8,
        metavar="N",
        help="re-read N bound byte ranges and confirm their SHA-256 (0 skips)",
    )
    parser.add_argument(
        "--census-output",
        type=Path,
        default=None,
        help="also write the census JSON to this path",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        graph = export_deepseek_v4_kernel_graph(
            snapshot=args.snapshot,
            checkpoint_lock_path=args.checkpoint_lock,
            config_path=args.config,
            source_path=args.source,
            context_tokens=args.context_tokens,
            maximum_new_tokens=args.maximum_new_tokens,
            include_speculative=args.include_speculative,
        )
    except DeepSeekV4KernelIRError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    verified = []
    if args.verify_bindings:
        verified = verify_checkpoint_bindings(
            args.snapshot, graph, sample=args.verify_bindings
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    graph_id = graph.write(args.output)
    census = graph_census(graph)
    census["file_bytes"] = args.output.stat().st_size
    census["output"] = str(args.output)
    census["verified_bindings"] = verified
    if args.census_output is not None:
        args.census_output.parent.mkdir(parents=True, exist_ok=True)
        args.census_output.write_text(
            json.dumps(census, indent=2, sort_keys=True) + "\n"
        )
    print(json.dumps(census, indent=2, sort_keys=True))
    assert graph_id == census["graph_id"]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
