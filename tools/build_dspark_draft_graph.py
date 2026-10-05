#!/usr/bin/env python3
"""Slice the DSpark draft stack out of a speculative graph as its own model.

DFlash's cost model (arXiv:2602.06036 equation 1) is
``L = (T_draft + T_verify) / tau``.  Both terms are measurable on the cycle
model, but only if each can be *lowered*, and the speculative graph as a whole
cannot: it is prologue, the target's 43-layer span, the target's head as an
unlayered interlude, the draft's 3-stage span, epilogue, and the ROM loop
compressor admits exactly one layered span.

The draft stack on its own has no such problem.  Its stages are layers 0, 1 and
2 of a single contiguous span, so it compresses under the rule that exists.
What stops it being a graph is only that it reads five values the target
produces.  This tool promotes exactly those to inputs and emits the remainder
unchanged:

* ``main.layer{N}.target_hidden.output`` for each layer in
  ``dspark_target_layer_ids`` -- the hidden states ``main_proj`` fuses, which is
  the conditioning DFlash calls the target context feature and DSpark reads
  through its own projection;
* ``main.sample.tokens`` -- the anchor token the block is built around; and
* any rope coefficient table, which is a generated constant either way.

Nothing else crosses the boundary, and the tool refuses if anything does, so
the slice cannot silently become a different model.  What it yields is the
draft pass exactly as the released implementation runs it, and timing it gives
``T_draft`` as a measurement rather than a byte-count estimate.

    PYTHONPATH=. python3 tools/build_dspark_draft_graph.py \\
      --speculative-ir build/ir-v3/deepseek-v4-flash-0731-speculative/kernel_ir.v3.json \\
      --output build/ir-v3/deepseek-v4-flash-0731-dspark-draft/kernel_ir.v3.json

The emitted graph carries its own ``model_id`` and therefore its own
``graph_id``; it is a derived artifact of the speculative graph and names it in
``source.derived_from``.  It is not a released model and must never be compared
with one as if it were.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.ir.v3.kernel_ir import (  # noqa: E402
    IRError,
    KernelGraph,
    check_neutral,
)

DRAFT_SCOPE = "dspark"
#: Roles a promoted boundary tensor may have had.  A weight needs no promotion
#: (the draft owns its own), and a state is not a value the target hands over.
PROMOTABLE_ROLES = frozenset({"activation", "input"})


class DraftSliceError(RuntimeError):
    """Raised when the draft stack does not separate cleanly."""


#: How each derived symbol's maximum follows the request horizon ``n``.  Read
#: off the shipped graph, where n = 262,144 gives 65,536 / 2,048 / 262,144 /
#: 327,680 / 264,192 exactly.
DERIVED_MAXIMA = {
    "span_tokens": lambda n: n,
    "context_length": lambda n: n,
    "span_groups_ratio4": lambda n: n // 4,
    "span_groups_ratio128": lambda n: n // 128,
    "context_groups_ratio4": lambda n: n // 4,
    "context_groups_ratio128": lambda n: n // 128,
    "attention_rows_window": lambda n: n,
    "attention_rows_ratio4": lambda n: n + n // 4,
    "attention_rows_ratio128": lambda n: n + n // 128,
}


def _rescale_symbols(graph: KernelGraph, horizon: int) -> tuple[Any, ...]:
    """Restate the request horizon this derived graph is built for.

    The draft stack reads one target position and its own 128-row window; it
    has no use for the target's 262,144-position horizon, and inheriting it
    sizes the promoted conditioning inputs for a context the draft never sees.
    A derived graph may declare its own horizon so long as it declares it, and
    every derived symbol is rescaled by the same rule the shipped graph obeys.
    """

    rescaled = []
    for symbol in graph.symbols:
        rule = DERIVED_MAXIMA.get(symbol.name)
        if rule is None:
            rescaled.append(symbol)
            continue
        rescaled.append(dataclasses.replace(symbol, maximum=rule(horizon)))
    return tuple(rescaled)


def _rescale_shape(shape: tuple[Any, ...], horizon: int) -> tuple[Any, ...]:
    out = []
    for extent in shape:
        rule = DERIVED_MAXIMA.get(getattr(extent, "symbol", None))
        if rule is None:
            out.append(extent)
            continue
        out.append(dataclasses.replace(extent, maximum=rule(horizon)))
    return tuple(out)


def slice_draft(
    graph: KernelGraph, *, model_id: str, horizon: int | None = None
) -> KernelGraph:
    """Return the draft stack as a standalone neutral graph."""

    kernels = [k for k in graph.kernels if k.kernel_id.startswith(f"{DRAFT_SCOPE}.")]
    if not kernels:
        raise DraftSliceError(
            f"the graph has no {DRAFT_SCOPE}.* kernels; it is not a speculative "
            "graph (build it with --include-speculative)"
        )
    layers = sorted({k.layer for k in kernels if k.layer is not None})
    if layers != list(range(len(layers))):
        raise DraftSliceError(
            f"the draft stack's layers are {layers}, which is not one "
            "contiguous span starting at zero; the loop compressor needs one"
        )

    produced = {name for k in kernels for name in k.outputs}
    consumed = {name for k in kernels for name in k.inputs}
    predicates = {k.predicate for k in kernels if k.predicate}
    boundary = sorted((consumed | predicates) - produced)

    tensors = {t.tensor_id: t for t in graph.tensors}
    missing = [name for name in boundary if name not in tensors]
    if missing:
        raise DraftSliceError(
            f"the draft stack reads {len(missing)} tensor(s) the graph does not "
            f"declare: {missing[:6]}"
        )

    promoted: list[str] = []
    kept: list[Any] = []
    for name in boundary:
        tensor = tensors[name]
        if tensor.role in PROMOTABLE_ROLES:
            if tensor.role == "activation":
                promoted.append(name)
                tensor = dataclasses.replace(tensor, role="input")
            kept.append(tensor)
            continue
        # A weight, a generated constant or anything else the draft owns
        # outright crosses no boundary: it is carried unchanged.
        kept.append(tensor)

    for name in produced:
        tensor = tensors.get(name)
        if tensor is None:
            raise DraftSliceError(
                f"the draft stack writes {name!r}, which the graph does not declare"
            )
        kept.append(tensor)

    if horizon is not None:
        kept = [
            dataclasses.replace(t, shape=_rescale_shape(t.shape, horizon))
            for t in kept
        ]
    by_id = {t.tensor_id: t for t in kept}
    states = [
        s
        for s in graph.states
        if any(
            s.state_id in set(k.state_reads) | set(k.state_writes) for k in kernels
        )
    ]
    renumbered = [
        dataclasses.replace(kernel, index=position)
        for position, kernel in enumerate(kernels)
    ]
    source = dict(graph.source)
    if horizon is not None:
        source["deployment_context_tokens"] = horizon
    source["derived_from"] = {
        "graph_id": graph.graph_id,
        "model_id": graph.model_id,
        "slice": f"{DRAFT_SCOPE}.* kernels only",
        "request_horizon_tokens": horizon,
        "promoted_to_input": sorted(promoted),
    }
    return KernelGraph(
        model_id=model_id,
        source=source,
        symbols=(
            _rescale_symbols(graph, horizon) if horizon is not None else graph.symbols
        ),
        tensors=tuple(sorted(by_id.values(), key=lambda t: t.tensor_id)),
        states=tuple(states),
        kernels=tuple(renumbered),
        entrypoints=graph.entrypoints,
        numeric_profile=graph.numeric_profile,
        generation_policy=graph.generation_policy,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--speculative-ir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--model-id",
        default=None,
        help="model id for the derived graph (default: <source>-dspark-draft)",
    )
    parser.add_argument(
        "--context-tokens",
        type=int,
        default=None,
        help=(
            "request horizon for the derived graph; the draft reads one target "
            "position and its own 128-row window, so the target's horizon is "
            "not required and inheriting it oversizes the promoted inputs"
        ),
    )
    parser.add_argument("--census-output", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(f"{args.output} exists; pass --force", file=sys.stderr)
        return 4
    try:
        graph = KernelGraph.read(args.speculative_ir)
    except (OSError, IRError, ValueError) as exc:
        print(f"cannot read the speculative graph: {exc}", file=sys.stderr)
        return 2
    model_id = args.model_id or f"{graph.model_id}-dspark-draft"
    try:
        draft = slice_draft(
            graph, model_id=model_id, horizon=args.context_tokens
        )
    except DraftSliceError as exc:
        print(f"draft slice refused: {exc}", file=sys.stderr)
        return 3
    problems = check_neutral(draft)
    if problems:
        print("derived draft graph is not neutral:", file=sys.stderr)
        for problem in problems[:8]:
            print(f"  {problem}", file=sys.stderr)
        return 5

    args.output.parent.mkdir(parents=True, exist_ok=True)
    draft.write(args.output)
    print(f"wrote {args.output}")
    print(f"  model_id   {draft.model_id}")
    print(f"  graph_id   {draft.graph_id}")
    print(f"  kernels    {len(draft.kernels)}")
    print(f"  tensors    {len(draft.tensors)}")
    print(
        "  promoted   "
        + ", ".join(draft.source["derived_from"]["promoted_to_input"])
    )
    if args.census_output:
        census = {
            "graph_id": draft.graph_id,
            "kernel_count": len(draft.kernels),
            "tensor_count": len(draft.tensors),
            "kernels_by_kind": {
                kind: sum(1 for k in draft.kernels if k.kind == kind)
                for kind in sorted({k.kind for k in draft.kernels})
            },
            "model_id": draft.model_id,
            "derived_from": draft.source["derived_from"],
        }
        args.census_output.parent.mkdir(parents=True, exist_ok=True)
        args.census_output.write_text(
            json.dumps(census, indent=2, sort_keys=True) + "\n"
        )
        print(f"  census     {args.census_output}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
