#!/usr/bin/env python3
"""Is the reduced V4.1 fixture's expert selection decidable at all?

The depth taps say the device tracks the oracle to about 1e-3 per layer with no
single operator wrong, and that at layer 0 the ENTIRE attention block is
bit-perfect while the first departure is in the expert path -- where several of the
oracle's per-expert tensors have no device counterpart of the same size at all.
A per-expert tensor's size is set by how many tokens routed to that expert, so
"no tensor of that size" means the two sides did not route the same tokens to the
same experts.

This measures whether they COULD have.  The reduced fixture routes **top-6 of 12**
experts -- a 50% selection rate, the least stable tie-break a router can have --
and its weights are a fixed Philox stream, so every expert's score is drawn from
the same distribution and no expert is meaningfully preferred.  The quantity that
decides whether selection is reproducible is the gap between the 6th and 7th
scores: if that gap is smaller than the arithmetic noise between two legitimate
implementations, then which experts get picked is decided by rounding, and the
token that comes out the far end is not a correctness statement about either side.

The instrument is the vendor's own gate, hooked -- no reimplementation.  For every
layer and every prompt position it records the sorted scores, the selected set,
and the 6th-to-7th gap relative to the score scale.  Then it asks the only
question that matters: how large a relative perturbation of the scores would it
take to change the selected set?

This is a statement about the FIXTURE, not about the implementation.  A trained
router separates its experts; a random one does not have to.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = "opentallas.abi3.v41_router_selection_margin.v1"
TOOL = "tools/measure_v41_router_selection_margin.py"


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=ROOT / "build/models/deepseek-v4.1-flash-reduced-v2")
    parser.add_argument("--checkpoint-lock", type=Path, default=ROOT / "results/abi3/deepseek_v41_reduced_v2_checkpoint.lock.json")
    parser.add_argument("--workload", type=Path, default=ROOT / "build/workloads/deepseek-v4.1-flash-reduced-v2/TA-DS41-REDUCED-EOS-1.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/abi3/deepseek_v41_v2_router_selection_margin.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoTokenizer

    from compiler.frontend.checkpoint import load_checkpoint_lock, verify_checkpoint_lock
    from tools.bisect_deepseek_v41_oracle_divergence import (
        _load_weights,
        build_model,
        import_vendor,
        released_snapshot,
    )

    lock = load_checkpoint_lock(args.checkpoint_lock)
    verify_checkpoint_lock(args.snapshot, lock)
    body = json.loads((args.snapshot / "inference_config.json").read_text(encoding="utf-8"))

    prompt = json.loads(args.workload.read_text(encoding="utf-8"))
    token_ids = prompt.get("token_ids") or prompt.get("prompt_token_ids") or prompt["tokens"]

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    import importlib

    convert_mod = importlib.import_module("convert")
    body = dict(body)
    body["expert_dtype"] = None
    tokenizer = AutoTokenizer.from_pretrained(str(args.snapshot))
    model = build_model(vendor, body, tokenizer)
    _load_weights(model, args.snapshot, convert_mod=convert_mod)
    model.eval()

    activated = int(body["n_activated_experts"])
    routed = int(body["n_routed_experts"])

    captures: list[dict[str, Any]] = []

    def make_hook(layer_index: int):
        def hook(module, inputs, output):
            # The gate returns (weights, indices) in the vendor's Gate.forward.
            if not isinstance(output, tuple) or len(output) < 2:
                return
            weights, indices = output[0], output[1]
            captures.append(
                {
                    "layer": layer_index,
                    "weights": weights.detach().float().cpu().numpy(),
                    "indices": indices.detach().cpu().numpy(),
                }
            )
        return hook

    handles = []
    for index, layer in enumerate(model.layers):
        ffn = getattr(layer, "ffn", None)
        gate = getattr(ffn, "gate", None) if ffn is not None else None
        if gate is not None:
            handles.append(gate.register_forward_hook(make_hook(index)))

    # The gate returns only the SELECTED weights, so the k-th-to-(k+1)-th gap --
    # the quantity that actually decides reproducibility -- is not in its output.
    # It IS the input to the topk the gate uses to select.  Intercepting torch.topk
    # captures that tensor exactly, with no reimplementation of sqrtsoftplus, the
    # route scale, or any group masking: whatever the vendor selects from is what
    # gets recorded.
    # ``Gate.forward`` selects with ``(scores + bias).topk(...)`` -- the TENSOR
    # method, so patching ``torch.topk`` captures nothing.  The tensor it is called
    # on is the biased score vector the cut is actually made on, which is the right
    # tensor: the bias steers selection while the weights come from the raw scores.
    scores: list[np.ndarray] = []
    real_topk = torch.Tensor.topk

    def capturing_topk(self, k, *rest, **kwargs):
        try:
            if int(k) == activated and self.shape[-1] == routed:
                scores.append(self.detach().float().cpu().numpy())
        except Exception:
            pass
        return real_topk(self, k, *rest, **kwargs)

    torch.Tensor.topk = capturing_topk
    try:
        with torch.inference_mode():
            model.forward(torch.tensor([token_ids], dtype=torch.long), 0)
    finally:
        torch.Tensor.topk = real_topk

    # Patching the tensor method re-enters once per call, so every score tensor is
    # captured twice in a row.  Duplicates would double the sample count without
    # changing any percentile; dropping them keeps the count honest.
    deduplicated: list[np.ndarray] = []
    for score in scores:
        if deduplicated and score.shape == deduplicated[-1].shape and np.array_equal(
            score, deduplicated[-1]
        ):
            continue
        deduplicated.append(score)
    duplicates_dropped = len(scores) - len(deduplicated)
    scores = deduplicated
    for handle in handles:
        handle.remove()

    if not captures:
        print("no MoE gate captured; nothing to measure", file=sys.stderr)
        return 1

    # The gate returns the SELECTED weights only, so the 6th-to-7th gap is not
    # directly visible from its output.  What IS visible is the spread inside the
    # selected set: the smallest selected weight against the largest.  A selection
    # whose smallest member is a hair above the cut is one the cut can lose.
    per_layer: list[dict[str, Any]] = []
    all_min_gaps: list[float] = []
    for capture in captures:
        weights = capture["weights"]
        flat = weights.reshape(-1, weights.shape[-1])
        smallest = flat.min(axis=-1)
        largest = flat.max(axis=-1)
        total = flat.sum(axis=-1)
        # Relative distance of the weakest selected expert from zero weight, i.e.
        # how close the marginal pick is to contributing nothing.
        with np.errstate(divide="ignore", invalid="ignore"):
            relative = np.where(largest > 0, smallest / largest, np.nan)
        per_layer.append(
            {
                "layer": capture["layer"],
                "positions": int(flat.shape[0]),
                "selected_per_position": int(flat.shape[-1]),
                "weakest_selected_over_strongest": {
                    "min": float(np.nanmin(relative)),
                    "median": float(np.nanmedian(relative)),
                    "max": float(np.nanmax(relative)),
                },
                "selected_weight_sum": {
                    "min": float(total.min()),
                    "median": float(np.median(total)),
                    "max": float(total.max()),
                },
                "last_position_indices": capture["indices"].reshape(-1, capture["indices"].shape[-1])[-1].tolist(),
                "last_position_weights": flat[-1].tolist(),
            }
        )
        all_min_gaps.extend(relative[np.isfinite(relative)].tolist())

    gaps = np.asarray(all_min_gaps, dtype=np.float64)
    bf16_epsilon = 2.0 ** -8

    # The real margin: for every position, sort the 12 scores and take the gap
    # between the 6th (last selected) and the 7th (first rejected), relative to the
    # spread of the whole score vector.  That is the perturbation the selection can
    # absorb before it changes.
    cut_margins: list[float] = []
    cut_absolute: list[float] = []
    per_score_capture: list[dict[str, Any]] = []
    for index, score in enumerate(scores):
        flat = score.reshape(-1, score.shape[-1]).astype(np.float64)
        ordered = np.sort(flat, axis=-1)[:, ::-1]
        kth = ordered[:, activated - 1]
        next_ = ordered[:, activated]
        spread = ordered[:, 0] - ordered[:, -1]
        absolute = kth - next_
        with np.errstate(divide="ignore", invalid="ignore"):
            relative = np.where(spread > 0, absolute / spread, np.nan)
        finite = relative[np.isfinite(relative)]
        cut_margins.extend(finite.tolist())
        cut_absolute.extend(absolute.tolist())
        if index < 3 or index == len(scores) - 1:
            per_score_capture.append(
                {
                    "capture_index": index,
                    "positions": int(flat.shape[0]),
                    "last_position_scores_sorted_desc": ordered[-1].tolist(),
                    "last_position_cut_gap_absolute": float(absolute[-1]),
                    "last_position_cut_gap_relative_to_spread": float(relative[-1]),
                }
            )

    cut = np.asarray(cut_margins, dtype=np.float64)
    cut_abs = np.asarray(cut_absolute, dtype=np.float64)

    record = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": (
            "on the reduced V4.1 fixture, is the top-6-of-12 expert selection "
            "decidable under the arithmetic noise between two legitimate "
            "implementations, or is it decided by rounding?"
        ),
        "fixture": {
            "snapshot": str(args.snapshot.relative_to(ROOT)),
            "checkpoint_lock_id": lock["lock_id"],
            "n_routed_experts": routed,
            "n_activated_experts": activated,
            "selection_rate": activated / routed,
            "score_func": body.get("score_func"),
            "route_scale": body.get("route_scale"),
            "weights": "a fixed Philox stream keyed by sha256(seed:tensor_name); no expert is trained to be preferred",
        },
        "layers_captured": len(captures),
        "per_layer": per_layer,
        "the_cut": {
            "selected_on": "scores + bias, which is what Gate.forward cuts on; the weights come from the raw scores",
            "what": (
                f"the gap between the {activated}th score (last selected) and the "
                f"{activated + 1}th (first rejected), over the full spread of the "
                f"{routed} scores.  A relative gap of g means a perturbation of the "
                "scores by g of their own spread can change which experts run."
            ),
            "score_tensors_captured": len(scores),
            "duplicate_captures_dropped": duplicates_dropped,
            "capture_note": (
                "patching Tensor.topk re-enters once per call, so each score tensor "
                "arrived twice; the duplicates are dropped rather than left to double "
                "the sample count"
            ),
            "samples": int(cut.size),
            "relative_gap_min": float(cut.min()) if cut.size else None,
            "relative_gap_p05": float(np.percentile(cut, 5)) if cut.size else None,
            "relative_gap_median": float(np.median(cut)) if cut.size else None,
            "relative_gap_max": float(cut.max()) if cut.size else None,
            "absolute_gap_median": float(np.median(cut_abs)) if cut_abs.size else None,
            "fraction_below_one_bf16_epsilon": (
                float(np.mean(cut < bf16_epsilon)) if cut.size else None
            ),
            "fraction_below_ten_bf16_epsilons": (
                float(np.mean(cut < 10 * bf16_epsilon)) if cut.size else None
            ),
            "samples_of_the_score_vector": per_score_capture,
        },
        "across_all_layers_and_positions": {
            "samples": int(gaps.size),
            "weakest_selected_over_strongest_min": float(gaps.min()),
            "weakest_selected_over_strongest_median": float(np.median(gaps)),
            "weakest_selected_over_strongest_p05": float(np.percentile(gaps, 5)),
            "bf16_epsilon": bf16_epsilon,
            "fraction_within_one_bf16_epsilon_of_the_cut": float(
                np.mean(gaps < bf16_epsilon)
            ),
        },
        "not_a_claim": [
            "this measures the FIXTURE's router, not the device: no device trace is "
            "read here",
            "the vendor Gate returns the selected weights only, so this reports the "
            "spread WITHIN the selected set rather than the 6th-to-7th score gap "
            "directly; a marginal pick with near-zero weight is the observable proxy "
            "for a selection the cut can lose, and it is a weaker instrument than "
            "the gap itself",
            "a small margin does not prove the device and oracle actually selected "
            "differently -- it establishes that they need not agree, which is what "
            "makes the emitted token unusable as a correctness oracle on this vehicle",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    summary = record["across_all_layers_and_positions"]
    print(f"wrote {args.output}")
    print(f"  layers captured                {len(captures)}")
    print(f"  selection                      top-{activated} of {routed} ({activated/routed:.0%})")
    print(f"  weakest/strongest  min         {summary['weakest_selected_over_strongest_min']:.6g}")
    print(f"  weakest/strongest  p05         {summary['weakest_selected_over_strongest_p05']:.6g}")
    print(f"  weakest/strongest  median      {summary['weakest_selected_over_strongest_median']:.6g}")
    print(f"  fraction within 1 bf16 epsilon {summary['fraction_within_one_bf16_epsilon_of_the_cut']:.4f}")
    the_cut = record["the_cut"]
    print(f"  --- the actual cut ({the_cut['score_tensors_captured']} score tensors, {the_cut['samples']} positions) ---")
    print(f"  cut gap / spread   min         {the_cut['relative_gap_min']!s}")
    print(f"  cut gap / spread   p05         {the_cut['relative_gap_p05']!s}")
    print(f"  cut gap / spread   median      {the_cut['relative_gap_median']!s}")
    print(f"  below 1 bf16 epsilon           {the_cut['fraction_below_one_bf16_epsilon']!s}")
    print(f"  below 10 bf16 epsilons         {the_cut['fraction_below_ten_bf16_epsilons']!s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
