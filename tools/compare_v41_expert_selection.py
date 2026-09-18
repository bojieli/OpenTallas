#!/usr/bin/env python3
"""Do the device and the oracle route the same tokens to the same experts?

The depth taps established two facts that only make sense together.  At layer 0 the
whole attention block matches the oracle at cosine 1.0 -- including ``ffn_norm``, the
gate's own input -- and yet several of the oracle's per-expert tensors have no device
tensor of the same size at all.  A per-expert tensor's length is set by how many
tokens routed to that expert, so either the two sides route differently, or the
device simply does not materialise per-expert tensors and the taps are matching
noise.  Cosine cannot tell those apart.  Expert IDs can: they are integers.

This reads both sides' selections directly.

* Oracle: ``Gate.forward`` returns ``(weights, indices)``; the indices are captured
  with a forward hook, no reimplementation.
* Device: every ``ROUTE.BIASED_TOPK`` call writes its selected expert IDs to output
  view 0.  Those are captured by wrapping the engine.

Then the two are compared as SETS per (layer, position), because the ABI's order
contract is "score descending then index ascending" while torch's ``topk`` is only
stable, so slot order is not required to agree -- membership is.

The measurement also records the dtype the device's score view is stored in.  The IR
declares ``fp32`` for the gate scores, and the router's cut gaps are as small as
1.7e-03 on scores of order 0.8 -- a relative 2e-03, which is BELOW one BF16 epsilon
(3.9e-03).  If the deployment ever narrowed that view to BF16 the selection would be
decided by the narrowing, so the stored width is part of the evidence rather than an
assumption.
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

SCHEMA = "opentallas.abi3.v41_expert_selection_comparison.v1"
TOOL = "tools/compare_v41_expert_selection.py"


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
    parser.add_argument("--output", type=Path, default=ROOT / "results/abi3/deepseek_v41_v2_expert_selection.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    import torch

    from compiler.frontend.checkpoint import load_checkpoint_lock, verify_checkpoint_lock
    from runtime.abi3.constants import Major, Route
    from runtime.abi3.capability import Capability
    from runtime.abi3.deployment import Deployment
    from runtime.driver import GenerationDriver
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

    # ---- oracle side -----------------------------------------------------
    lock = load_checkpoint_lock(args.checkpoint_lock)
    verify_checkpoint_lock(args.snapshot, lock)
    body = json.loads((args.snapshot / "inference_config.json").read_text(encoding="utf-8"))
    import importlib

    from transformers import AutoTokenizer

    released = released_snapshot()
    vendor, _engram = import_vendor(released)
    # ``convert`` lives in the vendor snapshot, so it only resolves after
    # import_vendor has put that directory on sys.path.
    convert_mod = importlib.import_module("convert")
    body = dict(body)
    body["expert_dtype"] = None
    tokenizer = AutoTokenizer.from_pretrained(str(args.snapshot))
    model = build_model(vendor, body, tokenizer)
    _load_weights(model, args.snapshot, convert_mod=convert_mod)
    model.eval()

    oracle: list[dict[str, Any]] = []

    def make_hook(layer_index: int):
        def hook(module, inputs, output):
            if isinstance(output, tuple) and len(output) >= 2:
                oracle.append(
                    {
                        "layer": layer_index,
                        "indices": output[1].detach().cpu().numpy().reshape(
                            -1, output[1].shape[-1]
                        ),
                    }
                )
        return hook

    handles = []
    for index, layer in enumerate(model.layers):
        ffn = getattr(layer, "ffn", None)
        gate = getattr(ffn, "gate", None) if ffn is not None else None
        if gate is not None:
            handles.append(gate.register_forward_hook(make_hook(index)))
    with torch.inference_mode():
        model.forward(torch.tensor([token_ids], dtype=torch.long), 0)
    for handle in handles:
        handle.remove()

    # ---- device side -----------------------------------------------------
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

    device_rows: list[dict[str, Any]] = []
    original = dict(_REGISTRY)
    key = (Major.ROUTE, Route.BIASED_TOPK)
    real = original.get(key)

    def spy(ctx, sub, descriptor):
        result = real(ctx, sub, descriptor)
        try:
            score_view = ctx.input_view(descriptor, 0)
            id_view = ctx.output_view(descriptor, 0)
            ids = np.asarray(ctx.read(id_view)).reshape(-1, id_view.dims[-1])
            device_rows.append(
                {
                    "call": len(device_rows),
                    "score_view_dtype": str(score_view.dtype),
                    "score_view_dims": list(score_view.dims),
                    "indices": ids.astype(int),
                }
            )
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

    # The engine wrapper is entered twice per descriptor, so every selection
    # arrives as an identical consecutive pair.  Left in place the pairing would be
    # off by one from layer 1 onward and every layer would look wrong -- which is
    # exactly how this instrument first read.  Dropping consecutive duplicates is
    # the same correction the router-margin tool needed for Tensor.topk.
    deduplicated: list[dict[str, Any]] = []
    for row in device_rows:
        if deduplicated and np.array_equal(row["indices"], deduplicated[-1]["indices"]):
            continue
        deduplicated.append(row)
    device_duplicates_dropped = len(device_rows) - len(deduplicated)
    device_rows = deduplicated

    # ---- compare ---------------------------------------------------------
    comparisons: list[dict[str, Any]] = []
    matched_positions = 0
    total_positions = 0
    pairs = min(len(oracle), len(device_rows))
    for index in range(pairs):
        o = oracle[index]["indices"]
        d = device_rows[index]["indices"]
        rows = min(o.shape[0], d.shape[0])
        per_position = []
        agree = 0
        for row in range(rows):
            oset = set(int(v) for v in o[row])
            dset = set(int(v) for v in d[row])
            same = oset == dset
            agree += int(same)
            per_position.append(
                {
                    "position": row,
                    "oracle": sorted(oset),
                    "device": sorted(dset),
                    "same_set": same,
                    "overlap": len(oset & dset),
                }
            )
        matched_positions += agree
        total_positions += rows
        comparisons.append(
            {
                "pair_index": index,
                "oracle_layer": oracle[index]["layer"],
                "device_call": device_rows[index]["call"],
                "score_view_dtype": device_rows[index]["score_view_dtype"],
                "score_view_dims": device_rows[index]["score_view_dims"],
                "positions": rows,
                "positions_with_the_same_selected_set": agree,
                "per_position": per_position,
            }
        )

    first_divergent = next(
        (c["pair_index"] for c in comparisons if c["positions_with_the_same_selected_set"] < c["positions"]),
        None,
    )
    dtypes = sorted({c["score_view_dtype"] for c in comparisons})

    record = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": (
            "do the device and the oracle select the same experts for the same "
            "tokens, and at what depth do they first stop?"
        ),
        "store": args.store,
        "workload": {"workload_id": prompt.get("workload_id"), "token_ids": token_ids},
        "oracle_gates_captured": len(oracle),
        "device_biased_topk_calls": len(device_rows),
        "device_duplicate_captures_dropped": device_duplicates_dropped,
        "capture_note": (
            "the engine wrapper is entered twice per descriptor, so each selection "
            "arrives twice; consecutive duplicates are dropped.  Without that the "
            "pairing is off by one from layer 1 onward and every layer reads as "
            "divergent"
        ),
        "device_score_view_dtypes": dtypes,
        "device_emitted_token_ids": [int(t) for t in result.get("generated_token_ids", [])],
        "summary": {
            "pairs_compared": pairs,
            "positions_compared": total_positions,
            "positions_with_the_same_selected_set": matched_positions,
            "agreement_fraction": (matched_positions / total_positions) if total_positions else None,
            "first_divergent_pair_index": first_divergent,
        },
        "comparisons": comparisons,
        "not_a_claim": [
            "not an RTL measurement: the device is runtime.sim",
            "selections are compared as SETS, because the ABI orders by score "
            "descending then index ascending while torch's topk is only stable; "
            "slot order is not required to agree",
            "pairing is by issue order -- the nth oracle gate against the nth device "
            "BIASED_TOPK call.  If the device issues a gate the oracle does not, or "
            "in another order, the pairing is wrong and the disagreement is an "
            "artifact of pairing rather than of routing; the captured counts are "
            "reported so that can be checked",
        ],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    s = record["summary"]
    print(f"wrote {args.output}")
    print(f"  oracle gates {len(oracle)}   device BIASED_TOPK calls {len(device_rows)}")
    print(f"  device score view dtype(s): {dtypes}")
    print(f"  positions compared {s['positions_compared']}   same set {s['positions_with_the_same_selected_set']}"
          f"   agreement {s['agreement_fraction']!s}")
    print(f"  first divergent pair index: {s['first_divergent_pair_index']!s}")
    for c in comparisons[:4]:
        print(f"   pair {c['pair_index']} (oracle layer {c['oracle_layer']}, dtype {c['score_view_dtype']}): "
              f"{c['positions_with_the_same_selected_set']}/{c['positions']} same")
        for p in c["per_position"][:2]:
            print(f"      pos {p['position']}: oracle {p['oracle']} device {p['device']} overlap {p['overlap']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
