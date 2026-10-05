#!/usr/bin/env python3
"""Greedy continuations of DeepSeek-V4.1-Flash under the vendor reference (mode a of
tools/deepseek_v41_deployment_quality.py), decoded token by token the way the release's generate.py does
(one prefill call, then one decode call per token with the release's own KV caches), for the
greedy-agreement part of the norm-after-matvec stability check (tools/deepseek_v41_nam_quality.py).

The full model does not fit one GPU, so every decoder block is built once and kept resident WITHOUT its
384 routed experts; a routed expert's FP4 weights are read from the checkpoint the first time a token routes
to it and kept in an LRU cache.  The arithmetic is the reference's (the same patched release modules,
_vendor_final and an FP32 head as mode a); only where the weights live differs.

Output: JSON [{name, ids, prompt_len}] -- prompt plus greedy continuation -- which the NAM tool scores
teacher-forced under every arithmetic (--gen-file).  For a greedy decoder the teacher-forced pass over the
reference's own continuation is the free-running decode up to the first disagreement, so the position of a
mode's first top-1 disagreement is where its own greedy decode would leave the reference's.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import deepseek_v41_deployment_quality as Q  # noqa: E402


class LazyExperts:
    """blk.ffn.experts stand-in: expert i built and loaded from the checkpoint on first use (LRU)."""

    def __init__(self, VM, args, ck, L, cache):
        self.VM, self.args, self.ck, self.L, self.cache = VM, args, ck, L, cache
        self.loads = 0

    def __getitem__(self, i):
        key = (self.L, i)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        prev = torch.get_default_dtype()
        torch.set_default_dtype(torch.bfloat16)
        try:
            with torch.device("cuda"):
                ex = self.VM.Expert(self.args.dim, self.args.moe_inter_dim,
                                    dtype=torch.float4_e2m1fn_x2 if self.args.expert_dtype == "fp4" else None,
                                    swiglu_limit=self.args.swiglu_limit)
        finally:
            torch.set_default_dtype(prev)
        with torch.no_grad():
            for name, prm in ex.named_parameters():
                t = self.ck.get(f"layers.{self.L}.ffn.experts.{i}.{name}")
                if prm.element_size() == 1:
                    prm.data.view(torch.uint8).copy_(t.view(torch.uint8))
                else:
                    prm.data.copy_(t.to(prm.dtype))
        self.cache[key] = ex
        self.loads += 1
        while len(self.cache) > self.cache.capacity:
            self.cache.popitem(last=False)
        return ex


class LRU(collections.OrderedDict):
    def __init__(self, capacity):
        super().__init__()
        self.capacity = capacity


def build_block(vend, L, ck, cache):
    """Q.Vendor.block without the routed experts' weights (they load lazily)."""
    VM = vend.VM
    small = None
    if vend.layout is not None:
        import dataclasses
        small = dataclasses.replace(vend.layout, num_embeddings=tuple(1 for _ in vend.layout.num_embeddings))
    prev = torch.get_default_dtype()
    torch.set_default_dtype(torch.bfloat16)
    try:
        with torch.device("cuda"):
            blk = VM.Block(L, vend.args, small)
    finally:
        torch.set_default_dtype(prev)
    del blk.ffn._modules["experts"]
    torch.cuda.empty_cache()
    blk.ffn.experts = LazyExperts(VM, vend.args, ck, L, cache)
    P = f"layers.{L}."
    with torch.no_grad():
        for name, prm in blk.named_parameters():
            if name.startswith("engram.embed."):
                continue
            t = ck.get(P + name)
            if name.endswith("attn.wo_a.weight"):
                sc = ck.get(P + "attn.wo_a.scale").float()
                ob, ib = t.shape[0] // sc.shape[0], t.shape[1] // sc.shape[1]
                t = (t.float().unflatten(0, (-1, ob)).unflatten(-1, (-1, ib)) * sc[:, None, :, None]) \
                    .flatten(2, 3).flatten(0, 1).bfloat16()
            if prm.element_size() == 1:
                prm.data.view(torch.uint8).copy_(t.view(torch.uint8))
            elif prm.dtype == t.dtype:
                prm.data.copy_(t)
            else:
                prm.data.copy_(t.to(prm.dtype))
    if blk.engram is not None:
        blk.engram.embed = Q._RowsEmbed()
    return blk


def prompts(tok, n, P, seed=11):
    """n WikiText-2 test prompts of exactly P tokens (BOS + P-1), at offsets away from the evaluation windows."""
    from datasets import load_dataset
    d = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split="test")
    ids = tok("\n\n".join(d["text"]), add_special_tokens=False).input_ids
    rng = np.random.default_rng(seed)
    starts = sorted(rng.choice(len(ids) - P, n, replace=False).tolist())
    return [[tok.bos_token_id] + ids[s:s + P - 1] for s in starts]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", default=str(Q.SNAPSHOT))
    ap.add_argument("--prompts", type=int, default=8)
    ap.add_argument("--prompt-len", type=int, default=128)
    ap.add_argument("--gen", type=int, default=128)
    ap.add_argument("--expert-cache", type=int, default=600)
    ap.add_argument("--max-layers", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    torch.backends.cuda.matmul.allow_tf32 = False
    dev = torch.device("cuda")
    snap = Path(args.snapshot)
    cfg, ck, tok = Q.Cfg(snap), Q.Checkpoint(snap), Q.tokenizer_for(snap)
    nl = args.max_layers or cfg.L
    B, P, G = args.prompts, args.prompt_len, args.gen
    vend = Q.Vendor(snap, B, P + G)
    t0 = time.time()
    cache = LRU(args.expert_cache)
    blocks = [build_block(vend, L, ck, cache) for L in range(nl)]
    print(f"built {nl} blocks in {time.time() - t0:.0f}s, gpu {torch.cuda.memory_allocated() / 1e9:.1f} GB", flush=True)
    embed = ck.get("embed.weight").to(dev)
    normw = ck.get("norm.weight").to(dev).float()
    headf = ck.get("head.weight").to(dev).float()
    from engram import NgramHashState
    import dataclasses
    with torch.device("cpu"):
        hs = NgramHashState(dataclasses.replace(vend.args, max_batch_size=B, max_seq_len=P + G), vend.layout, tok)
    ids = torch.tensor(prompts(tok, B, P), dtype=torch.int64)
    out = ids.clone()
    VM = vend.VM

    def step(tokens, start_pos):
        hashes = hs(tokens, start_pos) if cfg.engram_layers else None          # [B, s, nl, cols]
        with vend._ctx():
            h = embed[tokens.to(dev)].unsqueeze(2).repeat(1, 1, cfg.hc, 1)
            pre = VM.make_identity_pre_mix(h, cfg.hc)
            for L, blk in enumerate(blocks):
                if blk.engram is not None:
                    li = cfg.engram_layers.index(L)
                    blk.engram.embed.rows = Q.engram_rows(ck, cfg, L, hashes[:, :, li, :], dev)
                    h = blk.engram(h, torch.zeros(h.shape[0], h.shape[1], 1, dtype=torch.int64, device=dev), None)
                h, pre = blk(h, start_pos, pre, None)
            x = Q._vendor_final(vend, h[:, -1:], pre[:, -1:], normw)
        return torch.nn.functional.linear(x.float(), headf)[:, -1].argmax(-1).cpu()

    nxt = step(ids, 0)
    out = torch.cat([out, nxt[:, None]], 1)
    print(f"prefill done {time.time() - t0:.0f}s", flush=True)
    for g in range(1, G):
        nxt = step(out[:, -1:], P + g - 1)
        out = torch.cat([out, nxt[:, None]], 1)
        if g % 8 == 0:
            loads = sum(b.ffn.experts.loads for b in blocks)
            print(f"token {g}/{G} {time.time() - t0:.0f}s expert loads {loads}", flush=True)
            Path(args.out).write_text(json.dumps([{"name": f"gen{i}", "ids": out[i].tolist(), "prompt_len": P,
                                                   "partial": True} for i in range(B)]))
    rec = [{"name": f"gen{i}", "ids": out[i].tolist(), "prompt_len": P,
            "text": tok.decode(out[i, P:].tolist())} for i in range(B)]
    Path(args.out).write_text(json.dumps(rec, indent=1))
    print(f"done {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
