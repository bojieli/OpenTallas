#!/usr/bin/env python3
"""Where inside layer 0 do tokens 2, 3 and 4 stop being bit-identical?

The interval is bounded on both sides.  The embedding is exact for all eight tokens;
the FFN input is exact for tokens 0, 1, 5, 6, 7 and differs for 2, 3, 4; expert
selection, dispatch rows and ids, routing weights and the shared expert are all exact.
Between those two points sit the hyper-connection pre-mix, the attention norm, the
attention itself, and the post-mix.

Cosine cannot resolve this -- a 0.18% max-element difference on three rows of eight
leaves ``.all`` at 1.0 to six digits, which is how it was missed.  So the localiser
here does not use cosine at all.  For every oracle checkpoint it searches the device
trace for tensors of the same element count and scores each candidate by **how many
rows match EXACTLY**, bit for bit.  A partial exact-row count is a fingerprint: a
tensor that agrees on five of eight rows and disagrees on three is the tensor, and an
unrelated tensor of the same size scores zero.  That makes the match self-evidencing
in a way a cosine ranking never is.

Reading it: the first checkpoint whose exact-row count drops below 8 is where the
three tokens diverge, and the checkpoints before it should all read 8/8.
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

SCHEMA = "opentallas.abi3.v41_layer0_exact_row_localisation.v1"
TOOL = "tools/localise_v41_layer0_exact_rows.py"


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
    parser.add_argument("--layer", type=int, default=0)
    parser.add_argument("--output", type=Path, default=ROOT / "results/abi3/deepseek_v41_v2_layer0_exact_rows.json")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output} without --force", file=sys.stderr)
        return 1

    import torch
    from transformers import AutoTokenizer

    from compiler.frontend.checkpoint import load_checkpoint_lock, verify_checkpoint_lock
    from runtime.abi3.capability import Capability
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

    # ---- oracle checkpoints inside the chosen layer ----------------------
    checkpoints: list[dict[str, Any]] = []

    def record(name: str, tensor: Any) -> None:
        if isinstance(tensor, tuple):
            tensor = tensor[0]
        if not hasattr(tensor, "detach"):
            return
        values = tensor.detach().float().cpu().numpy()
        # Flatten everything except the last axis; the hyper-connection residual
        # carries an extra hc_mult axis and each stream is its own device object.
        if values.ndim >= 3 and values.shape[-2] not in (0, 1) and values.ndim == 4:
            for stream in range(values.shape[-2]):
                checkpoints.append(
                    {"name": f"{name}.s{stream}", "values": values[..., stream, :].reshape(-1, values.shape[-1])}
                )
            return
        checkpoints.append({"name": name, "values": values.reshape(-1, values.shape[-1])})

    handles = []
    layer = model.layers[args.layer]

    def hook_for(name: str, pre: bool = False):
        if pre:
            def pre_hook(module, inputs):
                record(name, inputs[0])
            return pre_hook

        def hook(module, inputs, output):
            record(name, output)
        return hook

    handles.append(model.embed.register_forward_hook(hook_for("embed")))
    handles.append(layer.register_forward_pre_hook(hook_for(f"L{args.layer:02d}.block_input", pre=True)))
    for attribute in ("attn_norm", "ffn_norm"):
        module = getattr(layer, attribute, None)
        if module is not None:
            handles.append(module.register_forward_hook(hook_for(f"L{args.layer:02d}.{attribute}")))
    attention = getattr(layer, "attn", None)
    if attention is not None:
        handles.append(attention.register_forward_pre_hook(hook_for(f"L{args.layer:02d}.attn_input", pre=True)))
        handles.append(attention.register_forward_hook(hook_for(f"L{args.layer:02d}.attn_output")))
        for attribute in ("wq_a", "q_norm", "wq_b", "wkv", "kv_norm", "wo_b"):
            module = getattr(attention, attribute, None)
            if module is not None:
                handles.append(module.register_forward_hook(hook_for(f"L{args.layer:02d}.attn.{attribute}")))
    feed_forward = getattr(layer, "ffn", None)
    if feed_forward is not None:
        handles.append(feed_forward.register_forward_pre_hook(hook_for(f"L{args.layer:02d}.ffn_input", pre=True)))
    handles.append(layer.register_forward_hook(hook_for(f"L{args.layer:02d}.block_output")))

    # ``hc_mixes``, ``hc_pre`` and ``hc_post`` are METHODS, not submodules, so no hook
    # reaches them -- and the whole remaining interval lives inside them.  Wrap them on
    # this one layer and record what they consume and produce, which also captures the
    # post-attention residual that has no module boundary of its own.
    real_mixes = type(layer).hc_mixes
    real_pre = type(layer).hc_pre
    real_post = type(layer).hc_post
    mix_calls = {"n": 0}
    pre_calls = {"n": 0}
    post_calls = {"n": 0}

    def wrapped_mixes(self, x, hc_fn, hc_scale, hc_base):
        out = real_mixes(self, x, hc_fn, hc_scale, hc_base)
        if self is layer:
            index = mix_calls["n"]
            mix_calls["n"] += 1
            tag = "attn" if index == 0 else "ffn"
            flat = x.flatten(2).float()
            record(f"L{args.layer:02d}.hc_{tag}.mixes_input", flat)
            record(f"L{args.layer:02d}.hc_{tag}.pre", out[0])
            record(f"L{args.layer:02d}.hc_{tag}.post", out[1])
            record(f"L{args.layer:02d}.hc_{tag}.comb", out[2].flatten(2))
        return out

    def wrapped_pre(self, x, pre_mix):
        out = real_pre(self, x, pre_mix)
        if self is layer:
            index = pre_calls["n"]
            pre_calls["n"] += 1
            record(f"L{args.layer:02d}.hc_pre_call{index}.output", out)
        return out

    def wrapped_post(self, x, residual, post, comb):
        out = real_post(self, x, residual, post, comb)
        if self is layer:
            index = post_calls["n"]
            post_calls["n"] += 1
            record(f"L{args.layer:02d}.hc_post_call{index}.output", out)
        return out

    type(layer).hc_mixes = wrapped_mixes
    type(layer).hc_pre = wrapped_pre
    type(layer).hc_post = wrapped_post
    try:
        with torch.inference_mode():
            model.forward(torch.tensor([token_ids], dtype=torch.long), 0)
    finally:
        type(layer).hc_mixes = real_mixes
        type(layer).hc_pre = real_pre
        type(layer).hc_post = real_post
    for handle in handles:
        handle.remove()

    # ---- device trace ----------------------------------------------------
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

    trace: list[np.ndarray] = []
    original = dict(_REGISTRY)

    def wrap(function):
        def spy(ctx, sub, descriptor):
            result = function(ctx, sub, descriptor)
            try:
                view = ctx.output_view(descriptor, 0)
                values = np.asarray(
                    formats.widen(view.dtype, ctx.read(view)), dtype=np.float64
                )
                if values.size:
                    trace.append(values.reshape(-1))
            except Exception:
                return result
            return result
        return spy

    for key, function in original.items():
        _REGISTRY[key] = wrap(function)
    try:
        result = GenerationDriver(device).generate(token_ids, max_new_tokens=1).to_dict()
    finally:
        _REGISTRY.clear()
        _REGISTRY.update(original)

    # ---- match by EXACT ROW COUNT ---------------------------------------
    rows_out: list[dict[str, Any]] = []
    for entry in checkpoints:
        target = entry["values"]
        tokens, width = target.shape
        size = target.size
        best = None
        candidates = 0
        for values in trace:
            if values.size != size:
                continue
            candidates += 1
            candidate = values.reshape(tokens, width)
            exact = int(np.sum(np.all(candidate == target, axis=1)))
            per_row = []
            for row in range(tokens):
                a = target[row]
                b = candidate[row]
                scale = max(float(np.max(np.abs(a))), 1e-30)
                per_row.append(float(np.max(np.abs(a - b)) / scale))
            score = (exact, -max(per_row))
            if best is None or score > best["score"]:
                best = {"score": score, "exact_rows": exact, "per_row": per_row}
        rows_out.append(
            {
                "checkpoint": entry["name"],
                "tokens": tokens,
                "width": width,
                "candidates_of_that_size": candidates,
                "best_exact_rows": None if best is None else best["exact_rows"],
                "per_row_max_relative_difference": None if best is None else best["per_row"],
                "exact_tokens": (
                    None
                    if best is None
                    else [i for i, v in enumerate(best["per_row"]) if v == 0.0]
                ),
                "differing_tokens": (
                    None
                    if best is None
                    else [i for i, v in enumerate(best["per_row"]) if v != 0.0]
                ),
            }
        )

    first_partial = next(
        (
            r["checkpoint"]
            for r in rows_out
            if r["best_exact_rows"] is not None and r["best_exact_rows"] < r["tokens"]
        ),
        None,
    )

    record_out = {
        "schema": SCHEMA,
        "producer": {"tool": TOOL, "git": {"commit": _git_commit()}},
        "question": (
            f"inside layer {args.layer}, at which checkpoint do tokens 2, 3 and 4 stop "
            "being bit-identical to the oracle?"
        ),
        "method": (
            "for each oracle checkpoint, every device engine output of the same "
            "element count is scored by HOW MANY ROWS MATCH EXACTLY, and the best is "
            "reported.  A partial exact-row count is a fingerprint -- an unrelated "
            "tensor of the same size scores zero -- so the match is self-evidencing "
            "in a way a cosine ranking is not."
        ),
        "workload": {"workload_id": prompt.get("workload_id"), "token_ids": token_ids},
        "device_emitted_token_ids": [int(t) for t in result.get("generated_token_ids", [])],
        "device_trace_tensors": len(trace),
        "first_checkpoint_not_fully_exact": first_partial,
        "checkpoints": rows_out,
        "not_a_claim": [
            "not an RTL measurement: the device is runtime.sim",
            "a checkpoint with 0 exact rows is NOT evidence of a fault there: the "
            "device may not materialise that tensor at all, and then the best "
            "same-size candidate is unrelated.  Only a PARTIAL count (between 1 and "
            "tokens-1) identifies the tensor and localises the difference",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record_out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    print(f"  device trace tensors {len(trace)}")
    for r in rows_out:
        mark = ""
        if r["best_exact_rows"] is not None and 0 < r["best_exact_rows"] < r["tokens"]:
            mark = f"   <== PARTIAL, differing tokens {r['differing_tokens']}"
        print(
            f"  {r['checkpoint']:34s} {r['tokens']}x{r['width']:<4} cand={r['candidates_of_that_size']:>4} "
            f"exact={r['best_exact_rows']}/{r['tokens']}{mark}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
