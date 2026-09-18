#!/usr/bin/env python3
"""Localise the reduced V4.1 device's disagreement with the oracle, by depth.

``tools/compare_deepseek_v41_oracle_logits.py`` settled what the disagreement
is NOT: the two stores correlate with each other at r = 0.84 while both
correlate with the oracle at r = 0.03 and 0.01.  Rows that uncorrelated are not
a rounding difference and not an ill-conditioned argmax; something in the V4.1
path computes a different function, and the question is where.

The instrument is a depth sweep rather than a per-kernel digest.  The oracle's
own forward pass has natural checkpoints -- the embedding, the residual after
every one of the 40 blocks, the final norm -- and they are taken with forward
hooks on the vendor modules, so no reimplementation is involved.  On the device
side every engine call's output view is recorded in issue order.  Then, for each
oracle checkpoint, the device trace is searched for the record that best matches
it by absolute cosine similarity among records of the same element count.

Reading it: the checkpoints that match near 1.0 are computed correctly, and the
first that does not is where the device's function departs from the oracle's.
A tool that only compared the logits could say that they differ; this says at
what depth they start to.

Both sides are compared at the LAST prompt position only.  The oracle prefills
the whole prompt in one batched call and the device walks positions, so the
batched rows are not a shape either side shares; the last position is the one
the token comes from and the one both sides agree on the shape of.

Not an RTL measurement: the device is ``runtime.sim``.  Cosine similarity is a
localisation instrument, not a correctness proof -- a high score means the two
tensors are proportional, which is what a correct intermediate should be.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.frontend.checkpoint import (  # noqa: E402
    load_checkpoint_lock,
    verify_checkpoint_lock,
)
from runtime.sim import formats  # noqa: E402
from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engine import _REGISTRY  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402
from tools.build_deepseek_v41_reduced_model import (  # noqa: E402
    DEFAULT_LOCK,
    DEFAULT_SNAPSHOT,
    WORKLOAD_ID,
    build_model,
    import_vendor,
    released_snapshot,
)
from tools.run_deepseek_v41_reduced_reference_oracle import _load_weights  # noqa: E402

SCHEMA = "opentallas.abi3.v41_oracle_depth_bisection.v1"
TOOL = "tools/bisect_deepseek_v41_oracle_divergence.py"
ORACLE_RECORD = ROOT / "results/abi3/deepseek_v41_reduced_reference_oracle.json"
CHECKPOINT = ROOT / "build/models/deepseek-v4.1-flash-reduced-v1"

STORES = {
    "rom": (
        "build/abi3/deepseek-v41-reduced-rom",
        "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json",
    ),
    "hbm": (
        "build/abi3/deepseek-v41-reduced-hbm",
        "results/abi3/deepseek_v41_hbm_comparator_capability.json",
    ),
}


def _git(*args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()


def oracle_checkpoints(
    prompt: list[int],
    deep_layers: Sequence[int] = (),
    expert_numeric_path: str = "fp4",
    snapshot: Path | None = None,
    lock_path: Path | None = None,
) -> list[dict[str, Any]]:
    """The vendor forward pass's own tensors, at the last prompt position."""
    snapshot = Path(snapshot) if snapshot is not None else DEFAULT_SNAPSHOT
    lock = load_checkpoint_lock(Path(lock_path) if lock_path else DEFAULT_LOCK)
    verify_checkpoint_lock(snapshot, lock)
    body = json.loads(
        (snapshot / "inference_config.json").read_text(encoding="utf-8")
    )
    import importlib

    import torch
    from transformers import AutoTokenizer

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    # The reference has to run on the SAME routed-expert numeric path as the
    # oracle being compared against, or its taps come from a model whose experts
    # are dead and every feed-forward comparison is meaningless.  See
    # results/abi3/deepseek_v41_reduced_oracle_dead_experts.json.
    convert_mod = None
    if expert_numeric_path == "fp8":
        convert_mod = importlib.import_module("convert")
        body = dict(body)
        body["expert_dtype"] = None
    elif expert_numeric_path == "fp4_dequantised":
        # The device computes its routed experts as MXFP4 and its SHARED expert as
        # fp8.  Against an fp8-recast oracle the shared expert matches at cosine 1.0
        # and the routed ones do not -- which is not a fault, it is two different
        # legitimate arithmetics being compared.  This path keeps the declared
        # numerics (same FP4 codes, same E8M0 block scales, same activation
        # quantisation) and replaces only the vendor kernel that is broken on this
        # GPU, so the comparison is like for like.
        from tools.run_deepseek_v41_reduced_reference_oracle import (
            install_fp4_dequantised_linear,
        )

        install_fp4_dequantised_linear(vendor, importlib.import_module("convert"))
    tokenizer = AutoTokenizer.from_pretrained(str(snapshot))
    model = build_model(vendor, body, tokenizer)
    _load_weights(model, snapshot, convert_mod=convert_mod)
    model.eval()

    taps: list[dict[str, Any]] = []

    def rows_of(name: str, value: Any) -> list[tuple[str, np.ndarray]]:
        """The tensors of one tap, at the last prompt position.

        A block's residual is ``[batch, sequence, hc_mult, dim]``: four
        hyper-connection streams, and the device holds each stream as its own
        object rather than one 640-element buffer, so the streams are tapped
        SEPARATELY.  Matching them jointly found no candidate of that size at
        all and said nothing about any layer.  The head's output is
        ``[batch, vocabulary]`` and has no sequence axis to index.
        """
        if isinstance(value, tuple):
            value = value[0]
        if not hasattr(value, "shape"):
            return []
        array = np.asarray(value.float().cpu(), dtype=np.float64)
        if name == "head":
            return [(name, array[0].reshape(-1))] if array.ndim >= 2 else []
        if array.ndim < 2:
            return [(f"{name}.all", array.reshape(-1))] if array.size else []
        rows: list[tuple[str, np.ndarray]] = []
        at_position = array[0, -1]
        if at_position.ndim == 2:  # [hc_mult, dim] or [heads, head_dim]
            rows.extend(
                (f"{name}.s{stream}", at_position[stream].reshape(-1))
                for stream in range(at_position.shape[0])
            )
        else:
            rows.append((name, at_position.reshape(-1)))
        # A submodule's output is not always [batch, sequence, ...]; recording
        # the whole tensor too costs one extra candidate lookup and means an
        # axis order this tool does not know still gets compared.
        if array.size != at_position.size:
            rows.append((f"{name}.all", array.reshape(-1)))
        return rows

    def record(name: str):
        def hook(_module, _inputs, output):
            for label, row in rows_of(name, output):
                taps.append({"name": label, "values": row})

        return hook

    handles = [model.embed.register_forward_hook(record("embed"))]
    for index, layer in enumerate(model.layers):
        handles.append(layer.register_forward_hook(record(f"block.{index:02d}")))
        if getattr(layer, "engram", None) is not None:
            handles.append(
                layer.engram.register_forward_hook(record(f"engram.{index:02d}"))
            )
    # Deep taps: every named submodule of the named blocks.  The block-level
    # sweep says which layer departs; only the submodules can say which
    # operator, and a block's own module tree is the list of candidates without
    # this tool having to know the architecture.
    for index in deep_layers:
        if not 0 <= int(index) < len(model.layers):
            continue
        block = model.layers[int(index)]
        for name, module in block.named_modules():
            if not name:
                continue
            handles.append(
                module.register_forward_hook(record(f"L{int(index):02d}.{name}"))
            )
    handles.append(model.norm.register_forward_hook(record("final_norm")))
    handles.append(model.head.register_forward_hook(record("head")))
    # ``hc_pre`` collapses the four streams into the tensor the final norm reads.
    # It is a plain method on the block, not a submodule, so it takes a wrapper
    # rather than a hook; the wrapper is removed with the hooks below.
    block = model.layers[-1]
    original_hc_pre = getattr(type(block), "hc_pre", None)
    if callable(original_hc_pre):
        def wrapped_hc_pre(self, *args, **kwargs):
            result = original_hc_pre(self, *args, **kwargs)
            for label, row in rows_of("hc_pre", result):
                taps.append({"name": label, "values": row})
            return result

        type(block).hc_pre = wrapped_hc_pre

    # Function taps.  ``sparse_attn`` is a compiled tilelang kernel and
    # ``apply_rotary_emb`` rotates in place, so neither is a module and neither
    # can carry a forward hook -- yet between them they hold everything the
    # attention does after the Q and KV projections, which is exactly the span
    # the module taps leave unresolved.  Both are module-level names in the
    # vendor module's own globals, so wrapping them there is enough.
    wrapped: list[tuple[str, Any]] = []
    for function_name in ("sparse_attn", "apply_rotary_emb"):
        original_function = getattr(vendor, function_name, None)
        if not callable(original_function):
            continue
        wrapped.append((function_name, original_function))

        def make(function_name: str, original_function: Any):
            counter = {"calls": 0}

            def wrapper(*args: Any, **kwargs: Any):
                result = original_function(*args, **kwargs)
                counter["calls"] += 1
                # Only the first layer's calls: the point is to split ONE
                # layer's attention, and recording all forty would add ten
                # thousand candidates to every later search.
                if counter["calls"] <= 4:
                    for label, row in rows_of(
                        f"fn.{function_name}.{counter['calls']:02d}", result
                    ):
                        taps.append({"name": label, "values": row})
                return result

            return wrapper

        setattr(vendor, function_name, make(function_name, original_function))

    device = next(model.parameters()).device
    ids = torch.tensor([prompt], dtype=torch.long, device=device)
    with torch.inference_mode():
        model(ids)
    for handle in handles:
        handle.remove()
    if callable(original_hc_pre):
        type(block).hc_pre = original_hc_pre
    for function_name, original_function in wrapped:
        setattr(vendor, function_name, original_function)
    return taps


def device_trace(
    store: str,
    prompt: list[int],
    deployment_override: Path | None = None,
    checkpoint_override: Path | None = None,
) -> tuple[list[dict[str, Any]], list[int]]:
    """Every engine call's output view, in issue order."""
    deployment_dir, capability_path = STORES[store]
    if deployment_override is not None:
        deployment_dir = str(deployment_override)
    body = json.loads(Path(ROOT / capability_path).read_text())
    capability = Capability.from_dict(body.get("capability", body))
    device = Device(
        Deployment.read(ROOT / deployment_dir),
        capability,
        verify=False,
        trace=False,
        root=Path(checkpoint_override) if checkpoint_override else CHECKPOINT,
    )
    trace: list[dict[str, Any]] = []
    original = dict(_REGISTRY)

    def wrap(key, function):
        def spy(ctx, sub, descriptor):
            result = function(ctx, sub, descriptor)
            try:
                view = ctx.output_view(descriptor, 0)
                values = np.asarray(
                    formats.widen(view.dtype, ctx.read(view)), dtype=np.float64
                ).reshape(-1)
            except Exception:  # an engine with no output view, or an odd dtype
                return result
            trace.append(
                {
                    "index": len(trace),
                    "major": int(key[0]),
                    "sub": int(key[1]),
                    "values": values,
                }
            )
            return result

        return spy

    for key, function in original.items():
        _REGISTRY[key] = wrap(key, function)
    try:
        result = GenerationDriver(device).generate(prompt, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY.clear()
        _REGISTRY.update(original)
    return trace, [int(t) for t in result.get("generated_token_ids", [])]


def _best_match(target: np.ndarray, records: list[dict[str, Any]]) -> dict[str, Any]:
    """The record most nearly proportional to ``target``, by |cosine|."""
    size = target.size
    candidates = [r for r in records if r["values"].size == size]
    norm = float(np.linalg.norm(target))
    if not candidates or norm == 0.0:
        return {
            "matched": False,
            "candidates_of_that_size": len(candidates),
            "cosine": None,
        }
    stack = np.stack([r["values"] for r in candidates], axis=0)
    norms = np.linalg.norm(stack, axis=1)
    safe = np.where(norms == 0.0, 1.0, norms)
    cosine = np.abs(stack @ target) / (safe * norm)
    cosine = np.where(norms == 0.0, 0.0, cosine)
    best = int(np.argmax(cosine))
    record = candidates[best]
    return {
        "matched": True,
        "candidates_of_that_size": len(candidates),
        "cosine": round(float(cosine[best]), 6),
        "at_device_call": int(record["index"]),
        "device_major": record["major"],
        "device_sub": record["sub"],
        "second_best_cosine": (
            round(float(np.sort(cosine)[-2]), 6) if cosine.size > 1 else None
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", action="append", choices=sorted(STORES))
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/abi3/deepseek_v41_oracle_depth_bisection.json",
    )
    parser.add_argument(
        "--oracle",
        type=Path,
        default=ORACLE_RECORD,
        help="the oracle record whose workload and token this compares against",
    )
    parser.add_argument(
        "--expert-numeric-path",
        choices=("fp4", "fp8", "fp4_dequantised"),
        default="fp4",
        help=(
            "the routed-expert path the REFERENCE runs on; it must match the "
            "oracle record's, or the reference's own experts are dead"
        ),
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=None,
        help="the reduced snapshot the REFERENCE is built from (default v1)",
    )
    parser.add_argument(
        "--checkpoint-lock",
        type=Path,
        default=None,
        help="the lock that snapshot is verified against",
    )
    parser.add_argument(
        "--deployment",
        type=Path,
        default=None,
        help="override the device deployment directory for the named store",
    )
    parser.add_argument(
        "--checkpoint-root",
        type=Path,
        default=None,
        help="the device's checkpoint root, which must match the deployment",
    )
    parser.add_argument(
        "--deep-layer",
        action="append",
        type=int,
        default=None,
        help="tap every named submodule of this block; repeatable",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.999,
        help="a checkpoint below this |cosine| counts as departed",
    )
    arguments = parser.parse_args(argv)
    stores = arguments.store or ["rom"]

    record = json.loads(Path(arguments.oracle).read_text())
    case = record["results"][WORKLOAD_ID]
    prompt = [int(t) for t in case["prompt_token_ids"]]

    taps = oracle_checkpoints(
        prompt,
        arguments.deep_layer or (),
        arguments.expert_numeric_path,
        arguments.snapshot,
        arguments.checkpoint_lock,
    )
    print(f"oracle: {len(taps)} checkpoints", flush=True)

    load_engines()
    report_stores: dict[str, Any] = {}
    for store in stores:
        trace, emitted = device_trace(
            store, prompt, arguments.deployment, arguments.checkpoint_root
        )
        print(f"{store}: {len(trace)} engine outputs, token {emitted}", flush=True)
        rows = []
        first_departure = None
        for tap in taps:
            match = _best_match(tap["values"], trace)
            row = {
                "checkpoint": tap["name"],
                "elements": int(tap["values"].size),
                **match,
            }
            rows.append(row)
            if (
                first_departure is None
                and match.get("cosine") is not None
                and float(match["cosine"]) < arguments.threshold
            ):
                first_departure = tap["name"]
            if first_departure is None and not match.get("matched"):
                first_departure = tap["name"]
        report_stores[store] = {
            "emitted_token_ids": emitted,
            "engine_outputs_recorded": len(trace),
            "first_checkpoint_below_threshold": first_departure,
            "checkpoints": rows,
        }
        for row in rows:
            print(
                f"  {row['checkpoint']:14s} n={row['elements']:6d} "
                f"cos={row.get('cosine')} "
                f"(of {row['candidates_of_that_size']} same-size records)",
                flush=True,
            )

    report = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git("rev-parse", "HEAD")}},
        "question": (
            "the device's logit row is uncorrelated with the oracle's (r = 0.03); "
            "at what depth does the device's function depart from the oracle's?"
        ),
        "method": (
            "forward hooks on the vendor modules give the oracle's own checkpoints; "
            "every device engine call's output view is recorded in issue order; each "
            "checkpoint is matched to the most nearly proportional device record of "
            "the same element count, at the last prompt position"
        ),
        "threshold": arguments.threshold,
        "workload": {"workload_id": WORKLOAD_ID, "prompt_token_ids": prompt},
        "stores": report_stores,
        "not_a_claim": [
            "not an RTL measurement: the device is runtime.sim",
            "a high cosine says two tensors are proportional, which is necessary for "
            "a correct intermediate and not sufficient",
            "an unmatched checkpoint may mean the device holds that tensor in a "
            "different shape rather than computing it wrongly",
        ],
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"-> {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
