#!/usr/bin/env python3
"""Build a DeepSeek Tensor Kernel IR v3 document.

The front ends live in ``compiler/frontends/v3/deepseek_v4.py`` (the two V4
releases) and ``compiler/frontends/v3/deepseek_v41.py`` (V4.1-Flash); this tool
only selects a model profile, writes the canonical JSON and prints the census a
release report quotes.  Two runs with the same arguments produce byte-identical
output and the same ``graph_id``.

    python3 tools/build_deepseek_v4_kernel_ir_v3.py \\
        --output build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json

``--model deepseek-v4.1-flash`` selects the V4.1 front end.  That front end's
plan -- the profile, the CSA2 mode sequence, the lowering and the per-layer
census -- is complete and checkable without a single payload byte, and
``--plan-only`` prints and writes exactly that.  A full ``--model
deepseek-v4.1-flash`` build additionally needs the V4.1 checkpoint lock and
registry-witnessed source contract, and stops naming each artifact it does not
have.  Given them it emits the document and prints the census gate DS41-I2
quotes, whose ``unknown``, ``unpriced``, ``unreferenced`` and ``unbound`` counts
are the exit criterion and must all be zero.  ``--include-speculative`` is
planned but not emitted for this model: the seven DSpark source kinds have no
node-by-node lowering yet and the build says so rather than emitting a partial
draft stack.

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
from compiler.frontends.v3 import deepseek_v41  # noqa: E402

#: Every model either front end carries.  The V4.1 entry is a second front end,
#: not a third V4 profile, so the tool dispatches on membership here rather than
#: passing a V4.1 model id into a V4 resolver that would refuse it.
V41_MODEL_PROFILES = deepseek_v41.MODEL_PROFILES
ALL_MODELS = tuple(sorted({*MODEL_PROFILES, *V41_MODEL_PROFILES}))


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
        choices=ALL_MODELS,
        default=MODEL_ID,
        help=(
            "which pinned release to build (default %(default)s); "
            "deepseek-v4-pro-0813 needs the Pro checkpoint lock, source "
            "contract and complete snapshot, not the Flash ones, and "
            "deepseek-v4.1-flash needs its own"
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
    parser.add_argument(
        "--plan-only",
        action="store_true",
        help=(
            "deepseek-v4.1-flash only: confront the released configuration, "
            "derive the CSA2 mode sequence and print the planned per-layer "
            "census without binding a byte.  This is the part of gate DS41-I2 "
            "that does not need the checkpoint lock"
        ),
    )
    return parser


def build_v41(args: argparse.Namespace) -> int:
    """Build, or plan, the DeepSeek-V4.1-Flash document."""

    profile = deepseek_v41.resolve_model_profile(args.model)
    output = (
        REPOSITORY_ROOT / "build" / "ir-v3" / profile.model_id / "kernel_ir.v3.json"
        if args.output is None
        else args.output
    )
    if args.plan_only:
        try:
            config = deepseek_v41.released_architecture_config(profile, args.config)
            deepseek_v41.validate_architecture_pins(profile, config)
            deepseek_v41.confront_layer_modes(profile)
            digests = deepseek_v41.confront_source_digests(
                profile, args.snapshot or profile.release.snapshot
            )
            defects = deepseek_v41.plan_defects(profile)
        except deepseek_v41.DeepSeekV41KernelIRError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        if defects:
            for defect in defects:
                print(f"error: {defect}", file=sys.stderr)
            return 1
        census = deepseek_v41.planned_census(
            profile, include_speculative=args.include_speculative
        )
        census["confronted_inference_sources"] = digests
        census["confronted_architecture_pins"] = len(profile.architecture_pins)
        census["planned_output"] = str(output)
        if args.census_output is not None:
            args.census_output.parent.mkdir(parents=True, exist_ok=True)
            args.census_output.write_text(
                json.dumps(census, indent=2, sort_keys=True) + "\n"
            )
        print(json.dumps(census, indent=2, sort_keys=True))
        return 0
    try:
        graph = deepseek_v41.export_deepseek_v41_kernel_graph(
            model=profile,
            snapshot=args.snapshot,
            checkpoint_lock_path=args.checkpoint_lock,
            config_path=args.config,
            context_tokens=args.context_tokens,
            maximum_new_tokens=args.maximum_new_tokens,
            include_speculative=args.include_speculative,
        )
    except deepseek_v41.DeepSeekV41KernelIRError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    verified = []
    if args.verify_bindings:
        verified = verify_checkpoint_bindings(
            args.snapshot or profile.release.snapshot,
            graph,
            sample=args.verify_bindings,
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    graph_id = graph.write(output)
    census = deepseek_v41.graph_census_v41(graph, profile)
    census["confronted_architecture_pins"] = len(profile.architecture_pins)
    census["confronted_inference_sources"] = deepseek_v41.confront_source_digests(
        profile, args.snapshot or profile.release.snapshot
    )
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


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.model in V41_MODEL_PROFILES:
        return build_v41(args)
    if args.plan_only:
        print(
            f"error: --plan-only is a deepseek-v4.1-flash option; {args.model} "
            "emits a complete document",
            file=sys.stderr,
        )
        return 1
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
