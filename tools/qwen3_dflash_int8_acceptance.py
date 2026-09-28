#!/usr/bin/env python3
"""Measure DFlash block acceptance with the deployed Qwen O4 INT8 target.

This uses the pinned DFlash drafter and its greedy block protocol, while the
target and the shared output head run ``e_full_w8`` from
``qwen3_deployment_quality``.  It is a bounded arithmetic measurement, not a
TP-2 RTL throughput measurement.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import qwen3_deployment_quality as Q
from tools.measure_speculative_acceptance import _render


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for part in iter(lambda: f.read(1 << 20), b""):
            h.update(part)
    return h.hexdigest()


def rows_from(path, workloads, per_workload):
    opener = gzip.open if str(path).endswith(".gz") else open
    counts = {}
    with opener(path, "rt") as f:
        for line in f:
            row = json.loads(line)
            w = row["workload"]
            if w not in workloads or counts.get(w, 0) >= per_workload:
                continue
            counts[w] = counts.get(w, 0) + 1
            yield row


def prefix_tau(lengths, output_tokens):
    """Acceptance over the first output_tokens, excluding the prefill token."""
    remaining = output_tokens - 1
    cycles = 0
    for n in lengths:
        if remaining <= 0:
            break
        remaining -= min(n, remaining)
        cycles += 1
    return (output_tokens - 1) / cycles if remaining == 0 and cycles else None


def reference_rows(path):
    with gzip.open(path, "rt") as f:
        return {(r["workload"], r["prompt_id"], r.get("turn", 0)): r
                for r in map(json.loads, f)}


class W8DraftLinear(nn.Module):
    """Drafter matrix with O4's signed INT8, one BF16 scale per output row.

    DFlash's non-matrix operations remain the released BF16 GPU implementation.
    The matrix output rounds to BF16 at the original nn.Linear boundary.  This is
    a weight-format sensitivity, because the drafter RTL arithmetic order is not
    yet frozen; the target verifier below is the exact deployment contract.
    """

    def __init__(self, source, groups):
        super().__init__()
        q, s, _ = Q.quantize_w8(source.weight.detach())
        self.register_buffer("qT", q.t().contiguous())
        self.register_buffer("sT", s.t().contiguous())
        self.splits = Q.split_for(source.out_features, source.in_features, groups)
        self.out_features = source.out_features
        self.in_features = source.in_features
        if source.bias is not None:
            self.register_buffer("bias", source.bias.detach().clone())
        else:
            self.bias = None

    def forward(self, x):
        shape = x.shape[:-1]
        y = Q.int8_mv_t(x.reshape(-1, self.in_features).to(Q.F32),
                         self.qT, self.sT, self.splits).to(Q.BF16)
        if self.bias is not None:
            y = (y + self.bias).to(Q.BF16)
        return y.reshape(*shape, self.out_features)


def quantize_drafter(draft, groups):
    names = [name for name, module in draft.named_modules() if isinstance(module, nn.Linear)]
    for name in names:
        parent_name, attr = name.rsplit(".", 1) if "." in name else ("", name)
        parent = draft.get_submodule(parent_name) if parent_name else draft
        setattr(parent, attr, W8DraftLinear(getattr(parent, attr), groups))
    return names


@torch.inference_mode()
def run_one(target, draft, tok, row, max_new, block):
    from transformers import DynamicCache
    from dflash.model import _crop_to

    ids = _render(tok, row["messages"], row.get("tools"), row["enable_thinking"])
    dev = target.device
    cache = target.new_cache(1, len(ids) + max_new + block)
    selected = draft.target_layer_ids
    h, target_hidden = target.forward_with_features(torch.tensor(ids, device=dev), cache, selected)
    first = int(torch.argmax(target.logits(h[-1:]), -1)[0])
    output = [first]
    lengths = []
    draft_cache = DynamicCache(config=draft.config)
    draft_cache.activate_past_recording()
    start = len(ids)
    stop = {tok.eos_token_id}
    scale = float(getattr(draft.config, "dflash_config", {}).get("input_embedding_scale", 1.0))
    mask = draft.mask_token_id
    while len(output) < max_new and output[-1] not in stop:
        verify = min(block, max_new - len(output) + 1)
        b_ids = [output[-1]] + [mask] * (verify - 1)
        if verify > 1:
            noise = target.embed_rows(torch.tensor(b_ids, device=dev)).to(Q.BF16)[None] * scale
            dpos = torch.arange(start - target_hidden.shape[1], start + verify, device=dev)[None]
            dh = draft(target_hidden=target_hidden, noise_embedding=noise,
                       position_ids=dpos, past_key_values=draft_cache, use_cache=True)[:, 1 - verify:]
            _crop_to(draft_cache, start)
            dlogits = target.logits(dh[0].to(Q.F32))
            drafts = torch.argmax(dlogits, -1).tolist()
            b_ids[1:] = drafts
        v_h, v_features = target.forward_with_features(torch.tensor(b_ids, device=dev), cache, selected)
        posterior = torch.argmax(target.logits(v_h), -1).tolist()
        accepted = 0
        while accepted < verify - 1 and b_ids[accepted + 1] == posterior[accepted]:
            accepted += 1
        bonus = posterior[accepted]
        proposal = b_ids[1:accepted + 1] + [bonus]
        produced = min(len(proposal), max_new - len(output))
        for token in proposal[:produced]:
            output.append(token)
            if token in stop:
                break
        actually = len(output) - (start - len(ids) + 1)
        lengths.append(actually)
        start += actually
        cache["lens"] = [start]
        target_hidden = v_features[:, :actually]
    # Teacher-force the emitted sequence through the same deployed target.  A
    # speculative verifier is useful only if every output is its greedy argmax.
    tf_cache = target.new_cache(1, len(ids) + len(output))
    tf_h = target.forward(torch.tensor(ids + output[:-1], device=dev), tf_cache)
    tf_arg = torch.argmax(target.logits(tf_h[len(ids) - 1:]), -1).tolist()
    mismatches = [i for i, (a, b) in enumerate(zip(output, tf_arg)) if a != b]
    return {"workload": row["workload"], "prompt_id": row["prompt_id"],
            "prompt_sha256": row["prompt_sha256"], "prompt_tokens": len(ids),
            "output_ids": output, "acceptance_lengths": lengths,
            "tokens": len(output), "cycles": len(lengths),
            "tau": sum(lengths) / len(lengths) if lengths else None,
            "greedy_mismatches": mismatches}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--prompts", default=str(ROOT / "results/speculative/raw/prompts.jsonl.gz"))
    ap.add_argument("--bf16-reference", default=str(ROOT / "results/speculative/raw/dflash_b5_hf_spec.jsonl.gz"))
    ap.add_argument("--dflash-repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workloads", default="reasoning_math500,agentic_bfcl,chat_mt_bench")
    ap.add_argument("--per-workload", type=int, default=2)
    ap.add_argument("--max-new", type=int, default=128)
    ap.add_argument("--block", type=int, default=5)
    ap.add_argument("--groups", type=int, default=6144)
    ap.add_argument("--draft-weights", choices=("bf16", "w8"), default="bf16")
    ap.add_argument("--gpu-memory-fraction", type=float, default=0.55)
    args = ap.parse_args()
    if not 2 <= args.block <= 16 or args.max_new < 2:
        ap.error("block must be 2..16 and max-new >= 2")
    sys.path.insert(0, args.dflash_repo)
    from dflash.model import DFlashDraftModel
    from transformers import AutoTokenizer
    torch.cuda.set_per_process_memory_fraction(args.gpu_memory_fraction)
    snap = Q.find_snapshot()
    draft_snap = next((Path.home() / ".cache/huggingface/hub/models--z-lab--Qwen3-8B-DFlash-b16/snapshots").iterdir())
    tok = AutoTokenizer.from_pretrained(str(snap))
    target = Q.Qwen3(snap, "contract", "w8", "fp8", groups=args.groups)
    draft = DFlashDraftModel.from_pretrained(str(draft_snap), attn_implementation="sdpa",
                                              dtype=torch.bfloat16).to("cuda").eval()
    quantized_draft_matrices = quantize_drafter(draft, args.groups) if args.draft_weights == "w8" else []
    rec = {"schema": "opentallas.qwen3-dflash-int8-acceptance.v1",
           "scope": "bounded deployed-arithmetic acceptance; no TP-2 RTL cycle or final DFlash rate claim",
           "source_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
           "source_sha256": {p: sha(ROOT / p) for p in
                             ("tools/qwen3_dflash_int8_acceptance.py", "tools/qwen3_deployment_quality.py")},
           "dflash_commit": subprocess.check_output(["git", "-C", args.dflash_repo, "rev-parse", "HEAD"], text=True).strip(),
           "target_checkpoint": snap.name, "drafter_checkpoint": draft_snap.name,
           "prompts_sha256": sha(args.prompts), "bf16_reference_sha256": sha(args.bf16_reference),
           "mode": "e_full_w8", "groups": args.groups,
           "draft_weights": args.draft_weights,
           "drafter_quantized_matrices": quantized_draft_matrices,
           "block": args.block, "max_new": args.max_new,
           "environment": {"host": platform.node(), "torch": torch.__version__,
                           "gpu": torch.cuda.get_device_name(0)}, "rows": []}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bf16 = reference_rows(args.bf16_reference)
    for row in rows_from(args.prompts, set(args.workloads.split(",")), args.per_workload):
        t = time.time()
        one = run_one(target, draft, tok, row, args.max_new, args.block)
        ref = bf16.get((row["workload"], row["prompt_id"], 0))
        one["bf16_prefix_tau"] = prefix_tau(ref["acceptance_lengths"], one["tokens"]) if ref else None
        one["seconds"] = time.time() - t
        rec["rows"].append(one)
        out.write_text(json.dumps(rec, indent=1) + "\n")
        print(row["workload"], row["prompt_id"], one["tokens"], one["cycles"],
              one["tau"], one["seconds"], flush=True)
        if one["greedy_mismatches"]:
            raise AssertionError(f"deployed-target greedy mismatch: {one['greedy_mismatches']}")


if __name__ == "__main__":
    main()
