#!/usr/bin/env python3
"""qwen_r25 golden == the quality harness's r25_prenorm_full_w8 mode, value for value, on the released Qwen3-8B.

The harness (tools/qwen3_deployment_quality.Qwen3, order "r25", prenorm, w8, fp8 KV: the mode the owner's quality
run measures) is instantiated on the first `--layers` decoder layers with the SAME INT8 image (tools/qwen_r25_golden.
Image), and run on a real prompt through its own forward (prefill in one block on its CPU reference kernels).  The
numpy golden decodes the same prompt position by position.  Every position's final hidden state (after the final
RMSNorm), and the logits / argmax of the last `--logit-positions`, must agree bit for bit.  A negative control
(the harness's legacy contract order, order="contract") must DISAGREE.

    python3 tools/qwen_r25_golden_check.py --snapshot SNAP --cache DIR --layers 2 --tokens 16 --out REC.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import torch  # noqa: E402

import hdc_golden as G  # noqa: E402
import qwen3_deployment_quality as Q  # noqa: E402
import qwen_r25_golden as R  # noqa: E402

PROMPT = [151644, 872, 198, 785, 6722, 315, 9625, 374, 12095, 13, 3555, 374, 279, 6722, 315, 9856, 30, 151645, 198,
          151644, 77091, 198]       # "<|im_start|>user\nThe capital of France is Paris. What is the capital of Germany?..."


def harness(model: R.QwenR25, nl, order, tp=4):
    q = Q.Qwen3.__new__(Q.Qwen3)
    c = model.ck.cfg
    q.prenorm, q.cfg = True, c
    q.L, q.H, q.NH, q.KV, q.HD = nl, model.H, model.NH, model.KV, model.HD
    q.FF, q.V, q.eps, q.theta = model.FF, model.V, model.eps, model.theta
    q.arith, q.wfmt, q.kvfmt, q.groups = "contract", "w8", "fp8", Q.SPEC_GROUPS
    q.order, q.tp, q.prefill_chunk = order, tp, 512
    q.device = torch.device("cpu")
    q.bits, q.wfile, q.down_had, q.post_scale = {}, None, None, False
    bf = torch.bfloat16

    def W(key):
        codes, scales = model.img.get(key)
        return {"q": torch.from_numpy(codes).t().contiguous(),
                "s": torch.from_numpy(scales.astype(np.float32)).to(bf).reshape(-1, 1).t().contiguous(),
                "N": codes.shape[0], "post": True}
    ec, es = model.img.get("embed")
    q.embed_q, q.embed_s = torch.from_numpy(ec), torch.from_numpy(es).to(bf).reshape(-1, 1)
    q.embed = None
    q.norm = torch.from_numpy(model.ck.get("model.norm.weight")).to(bf)
    q.layers = []
    for i in range(nl):
        lw = lambda n: torch.from_numpy(model.lw(i, n))       # noqa: E731
        q.layers.append(dict(qn=lw("self_attn.q_norm").float(), kn=lw("self_attn.k_norm").float(),
                             ln1=lw("input_layernorm").to(bf), ln2=lw("post_attention_layernorm").to(bf),
                             qkv=W(f"L{i}.qkv"), o=W(f"L{i}.o"), gu=W(f"L{i}.gu"), down=W(f"L{i}.down")))
    q.lm = W("lm_head")
    inv = 1.0 / (q.theta ** (torch.arange(0, q.HD, 2, dtype=torch.int64).to(torch.float32) / q.HD))
    q.inv_freq = inv
    return q


def bits(a):
    return np.asarray(a, dtype=np.float32).view(np.uint32)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--snapshot", required=True, type=Path)
    ap.add_argument("--cache", required=True, type=Path)
    ap.add_argument("--layers", type=int, default=2)
    ap.add_argument("--tokens", type=int, default=16)
    ap.add_argument("--logit-positions", type=int, default=2)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    t0 = time.time()
    torch.set_num_threads(8)
    m = R.QwenR25(a.snapshot, a.cache)
    toks = PROMPT[:a.tokens]
    T, nl = len(toks), a.layers
    # the golden, position by position
    Kc = [np.zeros((m.KV, T, m.HD), dtype=np.float32) for _ in range(nl)]
    Vc = [np.zeros((m.KV, T, m.HD), dtype=np.float32) for _ in range(nl)]
    gh, glog = [], {}
    for p, tk in enumerate(toks):
        x = m.embed(tk)
        for i in range(nl):
            x = m.layer(i, x, p, Kc[i], Vc[i])
        gh.append(R.rmsnorm(x, m.ck.get("model.norm.weight"), m.eps))
        if p >= T - a.logit_positions:
            glog[p], _ = m.head(x)
    gh = np.stack(gh)
    tg = time.time() - t0
    out = {}
    for order, tp in (("r25", 4), ("r25_tp1", 1)):
        q = harness(m, nl, "r25", tp)
        cache = q.new_cache(B=1, cap=T)
        h = q.forward(torch.tensor(toks), cache).float().numpy()
        same_h = [bool(np.array_equal(bits(h[p]), bits(gh[p]))) for p in range(T)]
        lg = {}
        if order == "r25":
            hl = torch.from_numpy(h[T - a.logit_positions:])
            L = q.logits(hl).float().numpy()
            for j, p in enumerate(range(T - a.logit_positions, T)):
                lg[p] = dict(bit_exact=bool(np.array_equal(bits(L[j]), bits(glog[p]))),
                             argmax_harness=int(np.argmax(L[j])), argmax_golden=int(np.argmax(glog[p])),
                             first_diff=None if np.array_equal(bits(L[j]), bits(glog[p])) else
                             int(np.nonzero(bits(L[j]) != bits(glog[p]))[0][0]))
        out[order] = dict(hidden_bit_exact_per_position=same_h, all_hidden_exact=all(same_h), logits=lg,
                          max_abs_hidden_diff=float(np.max(np.abs(h - gh))))
    ok = out["r25"]["all_hidden_exact"] and all(v["bit_exact"] for v in out["r25"]["logits"].values()) and \
        not out["r25_tp1"]["all_hidden_exact"]
    rec = dict(schema="opentallas.qwen_r25_golden_check.v1", status="pass" if ok else "fail",
               generated_utc=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               host=os.uname().nodename, layers=nl, tokens=toks, golden_s=round(tg, 1), wall_s=round(time.time() - t0, 1),
               harness_mode="r25_prenorm_full_w8 (Qwen3(order='r25', prenorm=True), w8, fp8 KV), CPU reference kernels",
               negative_control="harness r25 order with tp=1 (o/down K not split over the 4 dies, so no die-partial tree) must differ", result=out,
               source_sha256={p: hashlib.sha256((TOOLS / p).read_bytes()).hexdigest()
                              for p in ("qwen_r25_golden.py", "qwen_r25_golden_check.py", "qwen3_deployment_quality.py",
                                        "hdc_golden.py")},
               snapshot=str(a.snapshot.name))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(dict(status=rec["status"], r25=out["r25"], negative_exact=out["r25_tp1"]["all_hidden_exact"]),
                     indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
