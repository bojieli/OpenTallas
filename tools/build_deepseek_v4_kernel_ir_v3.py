#!/usr/bin/env python3
"""Build a DeepSeek-V4 Tensor Kernel IR v3 document.

The front end lives in ``compiler/frontends/v3/deepseek_v4.py``; this tool only
selects a model profile, writes the canonical JSON and prints the census a
release report quotes.  Two runs with the same arguments produce byte-identical
output and the same ``graph_id``.

    python3 tools/build_deepseek_v4_kernel_ir_v3.py \\
        --output build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json

``--model deepseek-v4-pro-0813`` builds the other pinned release.  It needs
that release's own checkpoint artifacts, which are not the Flash ones: the
complete 66-shard snapshot including ``model.safetensors.index.json``, the
committed ``compiler/models/deepseek-v4-pro-0813/checkpoint_source.json`` that
``tools/build_checkpoint_source.py`` writes, and the Pro checkpoint lock at
``~/.cache/opentallas/deepseek-v4-pro-0813/checkpoint.lock.json`` that
``tools/build_checkpoint_lock.py`` writes by reading all 892,727,580,904
payload bytes once.  Without them the build stops before emitting anything and
names each artifact it does not have.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from compiler.frontend.deepseek_v4 import MODEL_ID  # noqa: E402
from compiler.frontends.v3.deepseek_v4 import (  # noqa: E402
    DEFAULT_CONTEXT_TOKENS,
    MODEL_PROFILES,
    DeepSeekV4KernelIRError,
    export_deepseek_v4_kernel_graph,
    graph_census,
    resolve_model_profile,
    verify_checkpoint_bindings,
)


def default_output(model_id: str) -> Path:
    return REPOSITORY_ROOT / "build" / "ir-v3" / model_id / "kernel_ir.v3.json"


DEFAULT_OUTPUT = default_output(MODEL_ID)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--model",
        choices=sorted(MODEL_PROFILES),
        default=MODEL_ID,
        help=(
            "which pinned release to build (default %(default)s); "
            "deepseek-v4-pro-0813 needs the Pro checkpoint lock, source "
            "contract and complete snapshot, not the Flash ones"
        ),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="checkpoint snapshot root (default: the selected model's)",
    )
    parser.add_argument(
        "--checkpoint-lock",
        type=Path,
        default=None,
        help="checkpoint lock path (default: the selected model's)",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="committed official config (default: the selected model's)",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="committed checkpoint source contract (default: the selected model's)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="document path (default: build/ir-v3/<model>/kernel_ir.v3.json)",
    )
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
    profile = resolve_model_profile(args.model)
    output = default_output(profile.model_id) if args.output is None else args.output
    snapshot = profile.release.snapshot if args.snapshot is None else args.snapshot
    try:
        graph = export_deepseek_v4_kernel_graph(
            model=profile,
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
            snapshot, graph, sample=args.verify_bindings
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    graph_id = graph.write(output)
    census = graph_census(graph)
    census["file_bytes"] = output.stat().st_size
    census["output"] = str(output)
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
