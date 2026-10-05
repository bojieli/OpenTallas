#!/usr/bin/env python3
"""Does the device dispatch the right token row to the right expert?

Everything upstream of the routed experts is now eliminated at layer 0: the FFN input
matches at cosine 1.0, the selected expert sets are identical at 8/8 positions, the
routing weights agree to 4.3e-08 once ``route_scale`` is accounted for, and the shared
expert is exact.  The FFN output is still 0.984103 across all eight positions while
the LAST position alone is 0.999983 -- thirty times better.  An error concentrated in
the non-final positions is not a wrong weight or a wrong expert; it is per-position
handling.

``ROUTE.EXPERT_DISPATCH`` is where per-position handling lives.  It takes the
normalised FFN input and the selected expert ids and emits one row per (token,
selected expert) pair, in a declared order -- ``ascending_token_then_ascending_selection``
-- together with the expert id each row belongs to.  So the check is exact and needs
no tolerance: **row r must equal the oracle's ffn_norm row for the token that the
declared order assigns to r**, and its expert id must be the one the oracle selected
in that slot.

That is a permutation check against a known permutation, not a cosine search, so it
cannot be fooled the way the nearest-neighbour taps can.
"""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SCHEMA = "opentallas.abi3.v41_expert_dispatch_rows.v1"
TOOL = "tools/compare_v41_expert_dispatch_rows.py"


def _git_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", default="rom")
    parser.add_argument("--snapshot", type=Path, default=ROOT / "build/models/deepseek-v4.1-flash-reduced-v2")
    parser.add_argument("--checkpoint-lock", type=Path, default=ROOT / "results/abi3/deepseek_v41_reduced_v2_checkpoint.lock.json")
    parser.add_argument("--deployment", type=Path, default=ROOT / "build/abi3/deepseek-v41-reduced-v2-rom")
    parser.add_argument("--checkpoint-root", type=Path, default=ROOT / "build/models/deepseek-v4.1-flash-reduced-v2")
    parser.add_argument("--workload", type=Path, default=ROOT / "build/workloads/deepseek-v4.1-flash-reduced-v2/TA-DS41-REDUCED-EOS-1.json")
    parser.add_argument("--layers", type=int, default=2, help="how many layers to report in detail")
    parser.add_argument("--output", type=Path, default=ROOT / "results/abi3/deepseek_v41_v2_expert_dispatch_rows.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoTokenizer

    from compiler.frontend.checkpoint import load_checkpoint_lock, verify_checkpoint_lock
    from runtime.abi3.capability import Capability
    from runtime.abi3.constants import Major, Route
    from runtime.abi3.deployment import Deployment
    from runtime.driver import GenerationDriver
    from runtime.sim import formats
    from runtime.sim.device import Device
    from runtime.sim.engine import _REGISTRY
    from runtime.sim.engines import load_engines
    from tools.bisect_deepseek_v41_oracle_divergence import (
        STORES,
        _load_weights,
        build_model,
        import_vendor,
        released_snapshot,
    )

    load_engines()

    prompt = json.loads(args.workload.read_text(encoding="utf-8"))
    token_ids = prompt.get("token_ids") or prompt["prompt_token_ids"]

    lock = load_checkpoint_lock(args.checkpoint_lock)
    verify_checkpoint_lock(args.snapshot, lock)
    body = json.loads((args.snapshot / "inference_config.json").read_text(encoding="utf-8"))

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    convert_mod = importlib.import_module("convert")
    body = dict(body)
    body["expert_dtype"] = None
    tokenizer = AutoTokenizer.from_pretrained(str(args.snapshot))
    model = build_model(vendor, body, tokenizer)
    _load_weights(model, args.snapshot, convert_mod=convert_mod)
    model.eval()

    # Oracle: the FFN input each MoE sees, and the expert ids it selects.
    oracle: list[dict[str, Any]] = []
    handles = []

    def make_moe_hook(layer_index: int):
        # A forward PRE-hook, because ``Gate`` is called from inside ``MoE.forward``
        # and so its own forward hook fires FIRST.  With a post-hook on the MoE the
        # gate's indices have nowhere to attach and every comparison comes out empty.
        def hook(module, inputs):
            x = inputs[0]
            oracle.append(
                {
                    "layer": layer_index,
                    "ffn_input": x.detach().float().cpu().numpy().reshape(-1, x.shape[-1]),
                }
            )
        return hook

    def make_gate_hook(layer_index: int):
        def hook(module, inputs, output):
            if isinstance(output, tuple) and len(output) >= 2:
                for entry in reversed(oracle):
                    if entry["layer"] == layer_index and "indices" not in entry:
                        entry["indices"] = output[1].detach().cpu().numpy().reshape(
                            -1, output[1].shape[-1]
                        )
                        break
        return hook

    for index, layer in enumerate(model.layers):
        ffn = getattr(layer, "ffn", None)
        gate = getattr(ffn, "gate", None) if ffn is not None else None
        if gate is not None:
            handles.append(ffn.register_forward_pre_hook(make_moe_hook(index)))
            handles.append(gate.register_forward_hook(make_gate_hook(index)))
    with torch.inference_mode():
        model.forward(torch.tensor([token_ids], dtype=torch.long), 0)
    for handle in handles:
        handle.remove()

    # Device: every EXPERT_DISPATCH call's rows and their expert ids.
    _, capability_path = STORES[args.store]
    capability_body = json.loads((ROOT / capability_path).read_text())
    capability = Capability.from_dict(capability_body.get("capability", capability_body))
    device = Device(
        Deployment.read(args.deployment),
        capability,
        verify=False,
        trace=False,
        root=args.checkpoint_root,
    )

    dispatches: list[dict[str, Any]] = []
    original = dict(_REGISTRY)
    key = (Major.ROUTE, Route.EXPERT_DISPATCH)
    real = original.get(key)

    def spy(ctx, sub, descriptor):
        result = real(ctx, sub, descriptor)
        try:
            rows_view = ctx.output_view(descriptor, 0)
            ids_view = ctx.output_view(descriptor, 1)
            rows = np.asarray(
                formats.widen(rows_view.dtype, ctx.read(rows_view)), dtype=np.float64
            ).reshape(-1, rows_view.dims[-1])
            ids = np.asarray(ctx.read(ids_view)).reshape(-1).astype(int)
            dispatches.append({"rows": rows, "expert_ids": ids})
        except Exception:
            pass
        return result

    if real is not None:
        _REGISTRY[key] = spy
    try:
        result = GenerationDriver(device).generate(token_ids, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY.clear()
        _REGISTRY.update(original)

    deduped: list[dict[str, Any]] = []
    for entry in dispatches:
        if deduped and entry["rows"].shape == deduped[-1]["rows"].shape and np.array_equal(
            entry["rows"], deduped[-1]["rows"]
        ):
            continue
        deduped.append(entry)
    duplicates_dropped = len(dispatches) - len(deduped)
    dispatches = deduped

    comparisons: list[dict[str, Any]] = []
    for index in range(min(len(oracle), len(dispatches), max(args.layers, 1))):
        entry = oracle[index]
        if "indices" not in entry:
            continue
        ffn_input = entry["ffn_input"]
        indices = entry["indices"]
        rows = dispatches[index]["rows"]
        ids = dispatches[index]["expert_ids"]
        tokens, top_k = indices.shape

        expected_rows = []
        expected_ids = []
        for token in range(tokens):
            # "ascending_selection" is the SLOT index, not the expert id: the device
            # emits the gate's own top-k order.  Sorting by expert id here made every
            # id column disagree while the row VALUES were unaffected, because all
            # top_k rows of a token are the same vector.
            for slot in range(top_k):
                expected_rows.append(ffn_input[token])
                expected_ids.append(int(indices[token][slot]))
        expected = np.asarray(expected_rows, dtype=np.float64)
        expected_id_array = np.asarray(expected_ids, dtype=int)

        n = min(expected.shape[0], rows.shape[0])
        id_match = bool(np.array_equal(expected_id_array[:n], ids[:n]))
        per_row = []
        worst = 0.0
        for row in range(n):
            a = expected[row]
            b = rows[row]
            if a.shape != b.shape:
                continue
            scale = max(float(np.max(np.abs(a))), 1e-30)
            relative = float(np.max(np.abs(a - b)) / scale)
            worst = max(worst, relative)
            per_row.append(
                {
                    "row": row,
                    "token": row // top_k,
                    "expert_id_device": int(ids[row]) if row < ids.size else None,
                    "expert_id_expected": int(expected_id_array[row]),
                    "max_relative_difference": relative,
                }
            )
        # Per token: is the row the device dispatched the oracle's ffn_norm row?
        # Cosine over the whole tensor cannot see this -- a 0.18% difference on one
        # token of eight still reads as cosine 1.0 -- so it is reported per token as
        # a max-element relative difference, and exact means exactly 0.
        per_token = []
        for token in range(tokens):
            rows_of_token = [r for r in per_row if r["token"] == token]
            if not rows_of_token:
                continue
            worst_token = max(r["max_relative_difference"] for r in rows_of_token)
            per_token.append(
                {
                    "token": token,
                    "max_relative_difference": worst_token,
                    "exact": worst_token == 0.0,
                }
            )

        comparisons.append(
            {
                "layer": entry["layer"],
                "per_token": per_token,
                "tokens_exact": sum(1 for t in per_token if t["exact"]),
                "tokens": tokens,
                "top_k": top_k,
                "device_rows": int(rows.shape[0]),
                "expected_rows": int(expected.shape[0]),
                "expert_ids_match_declared_order": id_match,
                "worst_row_relative_difference": worst,
                "rows_exact": sum(1 for r in per_row if r["max_relative_difference"] == 0.0),
                "rows_compared": len(per_row),
                "per_row": per_row,
            }
        )

    record = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": (
            "does the device's EXPERT_DISPATCH emit the oracle's ffn_norm row for the "
            "token the declared order assigns, with the oracle's expert id?"
        ),
        "declared_row_order": "ascending_token_then_ascending_selection",
        "oracle_moe_layers": len(oracle),
        "device_dispatch_calls": len(dispatches),
        "duplicate_captures_dropped": duplicates_dropped,
        "device_emitted_token_ids": [int(t) for t in result.get("generated_token_ids", [])],
        "comparisons": comparisons,
        "not_a_claim": [
            "not an RTL measurement: the device is runtime.sim",
            "this is an exact permutation check against the ABI's DECLARED row order; "
            "if the deployment uses a different order the mismatch is in the "
            "expectation, not necessarily in the device, and the expert-id column "
            "says which",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"  oracle MoE layers {len(oracle)}  device dispatch calls {len(dispatches)}  dups dropped {duplicates_dropped}")
    for c in comparisons:
        print(
            f"  layer {c['layer']}: rows device {c['device_rows']} expected {c['expected_rows']}, "
            f"ids match declared order: {c['expert_ids_match_declared_order']}, "
            f"exact rows {c['rows_exact']}/{c['rows_compared']}, worst rel {c['worst_row_relative_difference']:.6g}"
        )
        bad = [r for r in c["per_row"] if r["max_relative_difference"] > 0][:6]
        for r in bad:
            print(f"     row {r['row']} (token {r['token']}): device expert {r['expert_id_device']} "
                  f"expected {r['expert_id_expected']}  rel {r['max_relative_difference']:.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
