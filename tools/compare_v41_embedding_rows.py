#!/usr/bin/env python3
"""Is the device's embedding row bit-identical to the oracle's, per token?

The dispatch-row check found that at layer 0 five of eight tokens reach the experts
bit-identically and three -- tokens 2, 3 and 4, a contiguous run -- do not.  That is
structure rather than rounding, and it sits upstream of the experts.  The cheapest
upstream point to test is the first one: the embedding.

This repository has had exactly this failure before, recorded as "legacy unkeyed bases
ignore the placement table": ``EMBED_LOOKUP`` addressed by a launch counter rather
than by the token id, so the id was validated and then never used.  The symptom is a
run that completes correctly and quietly ignores part of its input -- which is what a
contiguous run of wrong positions looks like.

The comparison is exact and per token, because the instrument that missed this the
first time was a cosine: ``embed.all`` reads 1.0 while three rows of eight differ,
since a max-element difference of 0.18% confined to three rows leaves the whole
tensor's cosine at six printed digits.
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

SCHEMA = "opentallas.abi3.v41_embedding_rows.v1"
TOOL = "tools/compare_v41_embedding_rows.py"


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
    parser.add_argument("--output", type=Path, default=ROOT / "results/abi3/deepseek_v41_v2_embedding_rows.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoTokenizer

    from compiler.frontend.checkpoint import load_checkpoint_lock, verify_checkpoint_lock
    from runtime.abi3.capability import Capability
    from runtime.abi3.constants import Major, Tensor as TensorOp
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

    captured: list[np.ndarray] = []

    def embed_hook(module, inputs, output):
        captured.append(output.detach().float().cpu().numpy())

    handle = model.embed.register_forward_hook(embed_hook)
    with torch.inference_mode():
        model.forward(torch.tensor([token_ids], dtype=torch.long), 0)
    handle.remove()
    if not captured:
        print("no embedding captured", file=sys.stderr)
        return 1
    oracle_embed = captured[0].reshape(-1, captured[0].shape[-1])

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

    lookups: list[np.ndarray] = []
    original = dict(_REGISTRY)
    key = (Major.TENSOR, TensorOp.EMBED_LOOKUP)
    real = original.get(key)

    def spy(ctx, sub, descriptor):
        result = real(ctx, sub, descriptor)
        try:
            view = ctx.output_view(descriptor, 0)
            values = np.asarray(
                formats.widen(view.dtype, ctx.read(view)), dtype=np.float64
            ).reshape(-1, view.dims[-1])
            lookups.append(values)
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

    deduped: list[np.ndarray] = []
    for values in lookups:
        if deduped and values.shape == deduped[-1].shape and np.array_equal(values, deduped[-1]):
            continue
        deduped.append(values)
    duplicates_dropped = len(lookups) - len(deduped)

    comparisons: list[dict[str, Any]] = []
    for index, values in enumerate(deduped):
        rows = min(values.shape[0], oracle_embed.shape[0])
        per_token = []
        for token in range(rows):
            a = oracle_embed[token]
            b = values[token]
            if a.shape != b.shape:
                continue
            scale = max(float(np.max(np.abs(a))), 1e-30)
            relative = float(np.max(np.abs(a - b)) / scale)
            # Which oracle row does the device row actually look like?  If the
            # lookup used the wrong index, the device row will match a DIFFERENT
            # token's embedding exactly, and that is far more informative than a
            # difference magnitude.
            distances = np.max(np.abs(oracle_embed[:rows] - b[None, :]), axis=1)
            best = int(np.argmin(distances))
            per_token.append(
                {
                    "token_position": token,
                    "token_id": int(token_ids[token]) if token < len(token_ids) else None,
                    "max_relative_difference": relative,
                    "exact": relative == 0.0,
                    "closest_oracle_row": best,
                    "closest_is_itself": best == token,
                }
            )
        comparisons.append(
            {
                "lookup_call": index,
                "rows": rows,
                "tokens_exact": sum(1 for t in per_token if t["exact"]),
                "per_token": per_token,
            }
        )

    record = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": "is the device's embedding row bit-identical to the oracle's, per token?",
        "workload": {"workload_id": prompt.get("workload_id"), "token_ids": token_ids},
        "oracle_embedding_shape": list(oracle_embed.shape),
        "device_embed_lookup_calls": len(deduped),
        "duplicate_captures_dropped": duplicates_dropped,
        "device_emitted_token_ids": [int(t) for t in result.get("generated_token_ids", [])],
        "comparisons": comparisons,
        "not_a_claim": [
            "not an RTL measurement: the device is runtime.sim",
            "``closest_oracle_row`` is a nearest-row search over this prompt's eight "
            "embeddings only; it identifies a swapped index, it does not prove one",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"  device EMBED_LOOKUP calls {len(deduped)} (dropped {duplicates_dropped} duplicates)")
    for c in comparisons[:3]:
        print(f"  call {c['lookup_call']}: tokens exact {c['tokens_exact']}/{c['rows']}")
        for t in c["per_token"]:
            mark = "EXACT" if t["exact"] else f"rel {t['max_relative_difference']:.6g}"
            note = "" if t["closest_is_itself"] else f"  <== closest oracle row is {t['closest_oracle_row']}"
            print(f"     pos {t['token_position']} id {t['token_id']}: {mark}{note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
