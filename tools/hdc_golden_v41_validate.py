#!/usr/bin/env python3
"""Validate tools/hdc_golden_v41.py against the release's own reduced V4.1 oracle.

Three measurements, written to results/rtl/hdc_golden_v41_validation.json:

1. ORACLE SELF-CONSISTENCY.  The release's inference/model.py (FP8 expert path,
   the v2 fixture, exactly as tools/run_deepseek_v41_reduced_reference_oracle.py
   builds it) is run twice: the prompt prefilled in one call (how the committed
   oracle ran) and the prompt fed one position per call.  Both are the same
   model; they differ only in the kernels' evaluation order.
2. TEACHER-FORCED LAYER AGREEMENT.  Forward hooks record every layer's input,
   sublayer outputs and hyper-connection mix on the committed oracle's path (the
   prompt, then its generated tokens).  The golden runs every layer from the
   oracle's own input at every position and every BF16 tensor it produces is
   compared element for element.  Decode positions use the release decode
   kernel's KV block order (Model(vendor_decode_from=len(prompt))).
3. FREE-RUNNING TOKENS.  The golden prefills one position at a time and decodes
   greedily, in its specified two-pass attention order and in the release's
   decode block order; tokens and top-1 margins against the oracle's.

Needs the reduced checkpoint (build/models/deepseek-v4.1-flash-reduced-v2), the
pinned release snapshot and a CUDA GPU for step 1-2's oracle run; the oracle
taps are cached with --taps.
"""
from __future__ import annotations

import argparse
import json
import pickle
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdc_golden_v41 as G  # noqa: E402

ROOT = G.ROOT
OUT = ROOT / "results/rtl/hdc_golden_v41_validation.json"


def run_oracle(cap, chunked):
    """The release's Transformer on the v2 fixture; returns generated ids, logits
    per step and per-layer taps keyed (name, position)."""
    import importlib
    import torch
    from transformers import AutoTokenizer
    sys.path.insert(0, str(ROOT))
    from tools.build_deepseek_v41_reduced_model import build_model, import_vendor, released_snapshot
    from tools.run_deepseek_v41_reduced_reference_oracle import _load_weights

    body = dict(json.loads((G.SNAPSHOT / "inference_config.json").read_text()))
    vendor, _ = import_vendor(released_snapshot())
    convert = importlib.import_module("convert")
    body["expert_dtype"] = None                      # the committed oracle's --expert-numeric-path fp8
    model = build_model(vendor, body, AutoTokenizer.from_pretrained(str(G.SNAPSHOT)))
    _load_weights(model, G.SNAPSHOT, convert_mod=convert)
    model.eval()
    taps, cur = {}, {"pos": 0}

    def hook(name):
        def f(_mod, _inp, out):
            if isinstance(out, tuple):
                taps.setdefault(f"pre{name[5:]}", []).append((cur["pos"], out[1].float().cpu().numpy()))
                out = out[0]
            taps.setdefault(name, []).append((cur["pos"], out.float().cpu().numpy()))
        return f

    for i, layer in enumerate(model.layers):
        layer.register_forward_hook(hook(f"block{i}"))
        for sub in ("attn_norm", "attn", "ffn_norm", "ffn"):
            getattr(layer, sub).register_forward_hook(hook(f"L{i}.{sub}"))
        if layer.engram is not None:
            layer.engram.register_forward_hook(hook(f"L{i}.engram"))
    prompt, _ = G.prompt_and_expected()
    dev = next(model.parameters()).device
    rows, gen = [], []
    with torch.inference_mode():
        if chunked:
            cur["pos"] = 0
            _, logits, _ = model(torch.tensor([prompt], device=dev))
        else:
            for p, t in enumerate(prompt):
                cur["pos"] = p
                _, logits, _ = model(torch.tensor([[t]], device=dev), p)
        for i in range(cap):
            row = logits[0].float().cpu().numpy()
            rows.append(row)
            gen.append(int(row.argmax()))
            cur["pos"] = len(prompt) + i
            _, logits, _ = model(torch.tensor([[gen[-1]]], device=dev), len(prompt) + i)
    flat = {}
    for name, items in taps.items():
        for p, arr in items:
            if arr.shape[1] > 1:                      # a chunked prefill call: one row per position
                for j in range(arr.shape[1]):
                    flat[(name, p + j)] = arr[0, j]
            else:
                flat[(name, p)] = arr[0, 0]
    return {"generated": gen, "logits": rows, "taps": flat}


def teacher_forced(oracle, steps):
    prompt, _ = G.prompt_and_expected()
    seq = prompt + oracle["generated"][:steps]
    model = G.Model(vendor_decode_from=len(prompt))
    taps = oracle["taps"]
    state, per_tensor, logits_rows = model.new_state(), {}, []
    total = differing = 0
    for p, tok in enumerate(seq):
        def force(L, p=p):
            if L == 0:
                return None
            return taps[(f"block{L - 1}", p)].astype(np.float32), taps[(f"pre{L - 1}", p)].astype(np.float32)
        trace = {}
        logits_rows.append(model.decode_token(tok, p, state, trace=trace, force=force))
        for (name, q), ref in taps.items():
            if q != p or name.startswith("pre"):
                continue
            a, b = np.asarray(trace[name], np.float32).ravel(), ref.astype(np.float32).ravel()
            n = int(np.sum(a != b))
            total += a.size
            differing += n
            if n:
                per_tensor[f"{name}@{p}"] = n
    steps_out = []
    for i in range(steps + 1):
        a, b = logits_rows[len(prompt) - 1 + i], oracle["logits"][i]
        steps_out.append({"step": i, "golden_argmax": int(np.argmax(a)), "oracle_argmax": int(np.argmax(b)),
                          "max_abs_logit_difference": float(np.max(np.abs(a - b)))})
    return {"bf16_elements_compared": total, "bf16_elements_differing": differing,
            "differing_tensors": dict(sorted(per_tensor.items(), key=lambda kv: -kv[1])),
            "logits": steps_out}


def free_running(n, vendor_order, oracle):
    prompt, _ = G.prompt_and_expected()
    model = G.Model(vendor_decode_from=len(prompt) if vendor_order else None)
    tokens, rows = model.generate(prompt, n)
    agree = 0
    for t, e in zip(tokens, oracle["generated"]):
        if t != e:
            break
        agree += 1
    return {"tokens": tokens, "oracle_tokens": oracle["generated"][:n], "leading_tokens_agreeing": agree,
            "margins": [round(G.margin(r), 5) for r in rows]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--taps", type=Path, help="cache of the oracle runs (pickle)")
    ap.add_argument("--tokens", type=int, default=16)
    ap.add_argument("--teacher-steps", type=int, default=15)
    ap.add_argument("--output", type=Path, default=OUT)
    a = ap.parse_args()
    if a.taps and a.taps.exists():
        runs = pickle.loads(a.taps.read_bytes())
    else:
        runs = {"chunked": run_oracle(a.tokens, True), "stepwise": run_oracle(a.tokens, False)}
        if a.taps:
            a.taps.write_bytes(pickle.dumps(runs))
    chunked, stepwise = runs["chunked"], runs["stepwise"]
    prompt, committed = G.prompt_and_expected()
    report = {
        "schema": "opentallas.rtl.hdc_golden_v41_validation.v1",
        "golden": "tools/hdc_golden_v41.py",
        "producer": "tools/hdc_golden_v41_validate.py",
        "fixture": "build/models/deepseek-v4.1-flash-reduced-v2 (the committed oracle's lock "
                   "results/abi3/deepseek_v41_reduced_v2_checkpoint.lock.json)",
        "oracle": "the release's inference/model.py on the FP8 expert path, as "
                  "results/abi3/deepseek_v41_reduced_v2_reference_oracle_fp8.json",
        "prompt": prompt,
        "oracle_self_consistency": {
            "chunked_prefill_tokens": chunked["generated"],
            "chunked_reproduces_committed_oracle": chunked["generated"] == committed[:len(chunked["generated"])],
            "one_position_per_call_tokens": stepwise["generated"],
            "first_token_agrees": chunked["generated"][0] == stepwise["generated"][0],
            "chunked_first_margin": round(G.margin(chunked["logits"][0]), 5),
        },
        "teacher_forced_on_oracle_path": teacher_forced(chunked, a.teacher_steps),
        "free_running": {
            "specified_two_pass_attention": free_running(a.tokens, False, chunked),
            "release_decode_block_order": free_running(a.tokens, True, chunked),
        },
        "not_a_claim": [
            "not an RTL measurement: the golden is a NumPy specification",
            "the fixture's weights are random; its token is decided by rounding order, which is what "
            "oracle_self_consistency measures",
        ],
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=1) + "\n")
    tf = report["teacher_forced_on_oracle_path"]
    print(json.dumps(report["oracle_self_consistency"]))
    print("teacher-forced differing BF16 elements", tf["bf16_elements_differing"], "of", tf["bf16_elements_compared"])
    for k, v in report["free_running"].items():
        print(k, v["leading_tokens_agreeing"], v["tokens"], v["margins"][:4])


if __name__ == "__main__":
    main()
