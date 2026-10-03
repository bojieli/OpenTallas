#!/usr/bin/env python3
"""Golden (hdc_golden arithmetic) for one DSpark draft step of the Qwen3-8B drafter, checked against
the publisher's PyTorch modeling code.

Drafter deepseek-ai/dspark_qwen3_8b_block7 @ 03326e50, reference implementation
github.com/deepseek-ai/DeepSpec @ 005e03b8 deepspec/modeling/dspark/qwen3/modeling.py + markov_head.py
(VanillaMarkov).  One draft step at anchor position `start`:

  ctx      = hidden_norm(fc(concat(target hidden after layers 1, 9, 17, 25, 33)))   positions [0, start)
  block    = embed([anchor, mask x (S-1)])                                         positions start .. start+S-1
  5 x layer: x += o(attn(q = rope(q_norm(q(rms(x)))), K/V over ctx + block, non-causal)); x += down(silu(gate) * up)
  h        = norm(x);  base logits = lm_head(h) (the target's head)
  slots k = 0 .. S-1 in order: logits_k = base_k + w2 . w1[prev], prev = anchor, then the argmax of slot k-1

Arithmetic contract (the target's, tools/hdc_golden.py + tools/qwen3_deployment_quality.py):
  * every matrix (fc, q/k/v/o, gate/up/down, lm_head, w2) is the W8 contract: quantize_w8 codes and one
    BF16 row scale; y = fl32(matvec(codes, bf16(x), split_for(n, k, 6,144)) x s);
  * w1 rows dequantised once (code x scale, one RNE multiply), as the embedding;
  * RMSNorm hdc_golden.rmsnorm (R-ARITH sum, bit-seed rsqrt), RoPE hdc_golden.rope at theta 1e6,
    SiLU hdc_golden.silu, residuals hdc_golden.add;
  * attention: q and probabilities BF16, K/V in --kv {fp8, fp32} (fp8: hdc_golden.kv_round, the target's
    KV contract), scores x 1/sqrt(128), attend() normalise-after-sum, K-splits hdc_golden.attn_splits(128, 6144);
  * argmax: lower index on ties.
This is the single-core order (tp = 1).  The TP4 lowering keeps each column-split matrix's own K sums and
folds row-split partials in rank order (hdc_golden.Model.decode_token_tp); that variant is not emitted here.

The PyTorch check runs DeepSpec's Qwen3DSparkModel in FP32 with the SAME dequantised weights (codes x
scale) and FP32 K/V, and compares draft tokens and logits; the golden's BF16 activation rounding makes
logits differ at the 1e-2 level, so the check is: identical draft tokens, and the max |logit diff| reported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

os.environ.setdefault("HDC_SU_WIDTH", "1024")
os.environ.setdefault("HDC_KV_FMT", "fp8")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdc_golden as G  # noqa: E402

F = np.float32
GROUPS, HD, NH, KVH, THETA, EPS = 6144, 128, 32, 8, 1000000.0, 1e-6


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class W8:
    def __init__(self, w_t):
        import torch
        from qwen3_deployment_quality import quantize_w8
        codes, scales, _ = quantize_w8(w_t.float())
        self.codes = codes.numpy().astype(F)
        self.scale = scales.float().numpy().reshape(-1).astype(F)
        self.n, self.k = self.codes.shape
        self.split = G.split_for(self.n, self.k, GROUPS)

    def deq(self):
        return G.mul(self.codes, self.scale[:, None])

    def __call__(self, x):
        return G.mul(G.matvec(self.codes, x, self.split), self.scale)


def golden_step(Wt, feats, anchor, start, S, mask_id, kv_fmt):
    """feats: [start, 20480] FP32 target features; returns (draft tokens, step logits [S, V])."""
    kvr = G.kv_round if kv_fmt == "fp8" else (lambda v: np.asarray(v, dtype=F))
    ctx = np.stack([G.rmsnorm(Wt["fc"](f), Wt["hidden_norm"], F(EPS)) for f in feats])
    x = np.stack([Wt["embed"][t] for t in [anchor] + [mask_id] * (S - 1)]).astype(F)
    s_sc, s_pv = G.attn_splits(HD, GROUPS)
    scale = F(1.0 / np.sqrt(HD))
    tabs = [G.rope_tables(p, HD, THETA) for p in range(start + S)]
    for L in range(5):
        P = Wt["layers"][L]
        h = np.stack([G.rmsnorm(v, P["in"], F(EPS)) for v in x])

        def kv(v, pos):
            k = P["k"](v).reshape(KVH, HD)
            vv = P["v"](v).reshape(KVH, HD)
            cos, sin, half = tabs[pos]
            k = np.stack([G.rope(G.rmsnorm(k[i], P["kn"], F(EPS)), cos, sin, half) for i in range(KVH)])
            return kvr(k), kvr(vv)
        kvs = [kv(ctx[t], t) for t in range(start)] + [kv(h[j], start + j) for j in range(S)]
        keys = np.stack([a for a, _ in kvs])     # [T, KVH, HD]
        vals = np.stack([b for _, b in kvs])
        out = []
        for j in range(S):
            q = P["q"](h[j]).reshape(NH, HD)
            cos, sin, half = tabs[start + j]
            attn = np.zeros((NH, HD), dtype=F)
            for hh in range(NH):
                g = hh // (NH // KVH)
                qq = G.rope(G.rmsnorm(q[hh], P["qn"], F(EPS)), cos, sin, half)
                sc = G.mul(G.matvec_il(keys[:, g], G.to_bf16(qq), s_sc), scale)
                attn[hh] = G.attend(sc, vals[:, g], s_pv)
            out.append(G.add(x[j], P["o"](attn.reshape(-1))))
        x = np.stack(out)
        nx = []
        for j in range(S):
            h2 = G.rmsnorm(x[j], P["post"], F(EPS))
            gt, up = P["gate"](h2), P["up"](h2)
            nx.append(G.add(x[j], P["down"](G.mul(G.silu(gt), up))))
        x = np.stack(nx)
    hf = np.stack([G.rmsnorm(v, Wt["norm"], F(EPS)) for v in x])
    base = np.stack([Wt["lm_head"](v) for v in hf])
    toks, logits, prev = [], [], anchor
    for j in range(S):
        lg = G.add(base[j], Wt["w2"](Wt["w1"][prev]))
        t = int(np.argmax(lg))
        toks.append(t)
        logits.append(lg)
        prev = t
    return toks, np.stack(logits)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--deepspec", type=Path, required=True)
    ap.add_argument("--draft", type=Path, required=True)
    ap.add_argument("--target", type=Path, required=True)
    ap.add_argument("--prompt", default="Explain the difference between weather and climate to a ten-year-old.")
    ap.add_argument("--gen", type=int, default=24, help="target greedy tokens before the draft step")
    ap.add_argument("--S", default="3,7")
    ap.add_argument("--threads", type=int, default=32)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    import torch
    torch.set_num_threads(a.threads)
    sys.path.insert(0, str(a.deepspec))
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from deepspec.modeling.dspark.qwen3 import Qwen3DSparkModel
    from deepspec.modeling.dspark.common import extract_context_feature
    t0 = time.time()
    tok = AutoTokenizer.from_pretrained(a.target)
    dev = torch.device(a.device)
    torch.backends.cuda.matmul.allow_tf32 = False
    target = AutoModelForCausalLM.from_pretrained(a.target, dtype=torch.bfloat16).to(dev).eval()
    text = tok.apply_chat_template([{"role": "user", "content": a.prompt}], tokenize=False,
                                   add_generation_prompt=True, enable_thinking=False)
    inp = tok(text, return_tensors="pt").input_ids.to(dev)
    with torch.no_grad():
        seq = target.generate(inp, max_new_tokens=a.gen, do_sample=False, temperature=None, top_p=None, top_k=None)
        out = target(seq, output_hidden_states=True)
    ref = Qwen3DSparkModel.from_pretrained(a.draft, dtype=torch.float32, attn_implementation="eager").eval()
    feats_t = extract_context_feature(out.hidden_states, ref.target_layer_ids).float().cpu()
    del target, out
    torch.cuda.empty_cache()
    seq = seq.cpu()
    start = seq.shape[1] - 1                    # anchor: the last committed token
    anchor = int(seq[0, start])
    sd = {k: v for k, v in ref.state_dict().items()}
    Wt = {"fc": W8(sd["fc.weight"]), "hidden_norm": sd["hidden_norm.weight"].numpy().astype(F),
          "norm": sd["norm.weight"].numpy().astype(F), "lm_head": W8(sd["lm_head.weight"]),
          "w2": W8(sd["markov_head.markov_w2.weight"]), "layers": []}
    w1 = W8(sd["markov_head.markov_w1.weight"])
    Wt["w1"] = w1.deq()
    emb = W8(sd["embed_tokens.weight"])          # the target's INT8 embedding contract
    Wt["embed"] = emb.deq()
    for L in range(5):
        p = f"layers.{L}."
        Wt["layers"].append({"in": sd[p + "input_layernorm.weight"].numpy().astype(F),
                             "post": sd[p + "post_attention_layernorm.weight"].numpy().astype(F),
                             "qn": sd[p + "self_attn.q_norm.weight"].numpy().astype(F),
                             "kn": sd[p + "self_attn.k_norm.weight"].numpy().astype(F),
                             **{n: W8(sd[p + f"self_attn.{n}_proj.weight"]) for n in "qkvo"},
                             **{n: W8(sd[p + f"mlp.{n}_proj.weight"]) for n in ("gate", "up", "down")}})
    # the reference runs on the same dequantised weights
    with torch.no_grad():
        for name, mod in ref.named_modules():
            if isinstance(mod, torch.nn.Linear):
                key = name + ".weight"
                q = {"fc.weight": Wt["fc"], "lm_head.weight": Wt["lm_head"],
                     "markov_head.markov_w2.weight": Wt["w2"]}.get(key)
                if q is None and name.startswith("layers."):
                    L, rest = int(name.split(".")[1]), name.split(".", 2)[2]
                    q = Wt["layers"][L][rest.split(".")[1].replace("_proj", "")]
                if q is not None:
                    mod.weight.copy_(torch.from_numpy(q.deq()))
        ref.markov_head.markov_w1.weight.copy_(torch.from_numpy(Wt["w1"]))
        ref.embed_tokens.weight.copy_(torch.from_numpy(Wt["embed"]))
    feats = feats_t[0, :start].numpy().astype(F)
    ref = ref.to(dev)
    feats_t = feats_t.to(dev)
    rec = {"schema": "opentallas.qwen-rom-dspark-drafter-golden.v1", "prompt": a.prompt, "start": start,
           "anchor": anchor, "mask_token_id": int(ref.mask_token_id), "context_tokens": seq[0, :start].tolist(),
           "tool_sha256": sha(__file__), "golden_sha256": sha(Path(G.__file__)),
           "draft": "deepseek-ai/dspark_qwen3_8b_block7@03326e5043815da1f81b109078b2889737c26017",
           "deepspec": "deepseek-ai/DeepSpec@005e03b81cec38b7da6399833d609ee89a2587f2", "steps": []}
    for S in map(int, a.S.split(",")):
        with torch.no_grad():
            ids = torch.full((1, S), int(ref.mask_token_id), dtype=torch.long, device=dev)
            ids[0, 0] = anchor
            hid = ref._forward_backbone(target_hidden_states=feats_t[:, :start], noise_embedding=ref.embed_tokens(ids),
                                        position_ids=torch.arange(start + S, device=dev).unsqueeze(0), attention_mask=None,
                                        past_key_values=None, use_cache=False, is_causal=False)
            rt, rl = ref.sample_draft_tokens(ref.compute_logits(hid[:, :S]), first_prev_token_ids=ids[:, 0],
                                             temperature=0.0, hidden_states=hid[:, :S])
        rt, rl = rt[0].tolist(), rl[0].float().cpu().numpy()
        for kv in ("fp32", "fp8"):
            t1 = time.time()
            gt, gl = golden_step(Wt, feats, anchor, start, S, int(ref.mask_token_id), kv)
            d = {"S": S, "kv": kv, "golden_tokens": gt, "torch_tokens": rt, "tokens_equal": gt == rt,
                 "max_abs_logit_diff": float(np.max(np.abs(gl - rl))), "max_abs_logit": float(np.max(np.abs(rl))),
                 "golden_logit_bits_argmax": [f"{int(G.bits(F(gl[j][gt[j]]))):08x}" for j in range(S)],
                 "golden_seconds": round(time.time() - t1, 1)}
            rec["steps"].append(d)
            print(json.dumps(d), flush=True)
            a.out.write_text(json.dumps(rec, indent=1) + "\n")
    rec["wall_seconds"] = round(time.time() - t0, 1)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")


if __name__ == "__main__":
    main()
