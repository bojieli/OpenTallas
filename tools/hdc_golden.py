#!/usr/bin/env python3
"""Golden model of the hardwired decode core (HDC) for the reduced Qwen3 vehicle.

This is the arithmetic SPECIFICATION the RTL implements.  Every operation is a
single IEEE binary32 operation with round-to-nearest-even (NumPy float32 rounds
each op), applied in exactly the order the hardware applies it:

* matvec      inputs rounded to BF16; per output, products (exact) accumulated
              sequentially over K from +0.0
* reduction   sums of P=8 interleaved partials (element i into partial i mod 8,
              each sequential), then a pairwise tree ((p0+p1)+(p2+p3))+...
* rsqrt       bit seed 0x5f3759df - (bits >> 1), three Newton-Raphson steps
* reciprocal  bit seed 0x7ef311c7 - bits, three Newton-Raphson steps
* exp         n = rint(x*log2e) by the 1.5*2^23 trick, two-constant Cody-Waite
              reduction, degree-6 Horner polynomial, scale by 2^n in the exponent
* softmax     max, exp(s - max), reduction sum, reciprocal, multiply
* silu        g * reciprocal(1 + exp(-g))

See docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md.  `decode_token` returns the
logits and every intermediate the RTL is checked against.
"""
import json
import struct
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / "build/models/qwen3-reduced-v1/model-00001-of-00001.safetensors"
CONFIG = ROOT / "compiler/models/qwen3-reduced-v1/config.json"
ORACLE = ROOT / "results/abi3/qwen3_reduced_reference_oracle.json"

F = np.float32
P = 8                         # interleaved partials in every reduction
LOG2E = F(1.4426950408889634)
LN2_HI = F(0.693145751953125)   # 0x3f317200: low bits zero, so n*LN2_HI is exact
LN2_LO = F(1.428606765330187e-06)
MAGIC = F(12582912.0)         # 1.5 * 2^23: adding and subtracting rounds to an integer
EXP_POLY = [F(1.0 / 720), F(1.0 / 120), F(1.0 / 24), F(1.0 / 6), F(0.5), F(1.0), F(1.0)]
EXP_MAX = F(88.0)
EXP_MIN = F(-87.0)


# -- representation helpers ---------------------------------------------------
def bits(x):
    return np.asarray(x, dtype=F).view(np.uint32)


def from_bits(b):
    return np.asarray(b, dtype=np.uint32).view(F)


def to_bf16(x):
    """FP32 -> BF16 round-to-nearest-even, returned as FP32 (low 16 bits zero)."""
    b = bits(x).astype(np.uint64)
    rounded = (b + 0x7FFF + ((b >> 16) & 1)) >> 16
    return from_bits((rounded << 16).astype(np.uint32))


def load_weights():
    raw = CHECKPOINT.read_bytes()
    n = struct.unpack("<Q", raw[:8])[0]
    header = json.loads(raw[8:8 + n])
    base = 8 + n
    out = {}
    for name, meta in header.items():
        if name == "__metadata__":
            continue
        start, end = meta["data_offsets"]
        u16 = np.frombuffer(raw[base + start:base + end], dtype=np.uint16)
        out[name] = from_bits(u16.astype(np.uint32) << 16).reshape(meta["shape"])
    return out


# -- arithmetic primitives -------------------------------------------------------
# The RTL builds on the qualified pipes ot_fp32_add_rne_pipe / ot_fp32_mul_rne_pipe.
# They are IEEE binary32 RNE with gradual underflow, except that every ZERO result
# is canonical +0.  `add` and `mul` are those two operations; everything else is
# composed of them, and a subtraction is an addition of the sign-flipped operand.
def z(x):
    x = np.asarray(x, dtype=F)
    return np.where(x == 0, F(0), x).astype(F)


def add(a, b):
    return z(np.asarray(a, dtype=F) + np.asarray(b, dtype=F))


def mul(a, b):
    return z(np.asarray(a, dtype=F) * np.asarray(b, dtype=F))


def neg(a):
    return from_bits(bits(a) ^ np.uint32(0x80000000))


def matvec(w, x):
    """y[n] = sum_k w[n,k] * bf16(x)[k], sequential over k per output, from +0."""
    return matvec_fp32(w, to_bf16(x))


def matvec_fp32(w, x):
    acc = np.zeros(w.shape[0], dtype=F)
    for k in range(w.shape[1]):
        acc = add(acc, mul(w[:, k], x[k]))
    return acc


def reduce_sum(v):
    """P interleaved sequential partials (each from +0), then a pairwise tree."""
    part = np.zeros(P, dtype=F)
    for i, x in enumerate(np.asarray(v, dtype=F)):
        part[i % P] = add(part[i % P], x)
    while len(part) > 1:
        part = np.array([add(part[j], part[j + 1]) for j in range(0, len(part), 2)], dtype=F)
    return part[0]


def rsqrt(v):
    v = np.asarray(v, dtype=F)
    y = from_bits(np.uint32(0x5F3759DF) - (bits(v) >> np.uint32(1)))
    half = mul(v, F(0.5))
    for _ in range(3):
        y = mul(y, add(F(1.5), neg(mul(half, mul(y, y)))))
    return y


def reciprocal(d):
    d = np.asarray(d, dtype=F)
    y = from_bits(np.uint32(0x7EF311C7) - bits(d))
    for _ in range(3):
        y = mul(y, add(F(2.0), neg(mul(d, y))))
    return y


def exp(x):
    x = np.clip(np.asarray(x, dtype=F), EXP_MIN, EXP_MAX).astype(F)
    t = mul(x, LOG2E)
    u = add(t, MAGIC)                     # integer n = rint(t) sits in u's low bits
    n = add(u, neg(MAGIC))
    r = add(add(x, neg(mul(n, LN2_HI))), neg(mul(n, LN2_LO)))
    p = np.full_like(r, EXP_POLY[0])
    for c in EXP_POLY[1:]:
        p = add(mul(p, r), c)
    # Scale by 2^n: add n to the biased exponent (n in [-126, 127] after the clamp).
    e = bits(p).astype(np.int64) + (n.astype(np.int64) << 23)
    return from_bits(e.astype(np.uint32))


def rmsnorm(x, w, eps):
    r = rsqrt(add(mul(reduce_sum(mul(x, x)), F(1.0 / len(x))), F(eps)))
    return mul(mul(x, r), w)


def rope_tables(position, head_dim, theta):
    """cos/sin of position * inv_freq.  A table ROM in the hardware (model-specific
    constants); computed here in float64 and rounded once."""
    half = head_dim // 2
    inv = (1.0 / (theta ** (np.arange(0, head_dim, 2, dtype=np.float64) / head_dim))).astype(F)
    angle = (F(position) * inv).astype(F)
    return np.cos(angle.astype(np.float64)).astype(F), np.sin(angle.astype(np.float64)).astype(F), half


def rope(v, cos, sin, half):
    a, b = v[:half], v[half:]
    return np.concatenate([add(mul(a, cos), mul(b, neg(sin))), add(mul(b, cos), mul(a, sin))])


def softmax(s):
    e = exp(add(s, neg(np.max(s))))
    return mul(e, reciprocal(reduce_sum(e)))


def silu(g):
    return mul(g, reciprocal(add(exp(mul(g, F(-1.0))), F(1.0))))


# -- the decode step ------------------------------------------------------------
class Model:
    def __init__(self):
        self.cfg = json.loads(CONFIG.read_text())
        self.w = load_weights()
        c = self.cfg
        self.layers, self.hidden = c["num_hidden_layers"], c["hidden_size"]
        self.heads, self.kv_heads, self.hd = c["num_attention_heads"], c["num_key_value_heads"], c["head_dim"]
        self.eps, self.theta = c["rms_norm_eps"], c["rope_theta"]

    def lw(self, layer, name):
        return self.w[f"model.layers.{layer}.{name}"]

    def decode_token(self, token, position, cache, trace=None):
        """One decode step.  `cache[layer]` is a list of (k, v) per earlier position
        (each [kv_heads, hd] float32); the step appends its own row."""
        x = self.w["model.embed_tokens.weight"][token].astype(F)
        cos, sin, half = rope_tables(position, self.hd, self.theta)
        group = self.heads // self.kv_heads
        for L in range(self.layers):
            h = rmsnorm(x, self.lw(L, "input_layernorm.weight"), self.eps)
            q = matvec(self.lw(L, "self_attn.q_proj.weight"), h).reshape(self.heads, self.hd)
            k = matvec(self.lw(L, "self_attn.k_proj.weight"), h).reshape(self.kv_heads, self.hd)
            v = matvec(self.lw(L, "self_attn.v_proj.weight"), h).reshape(self.kv_heads, self.hd)
            qn, kn = self.lw(L, "self_attn.q_norm.weight"), self.lw(L, "self_attn.k_norm.weight")
            q = np.stack([rope(rmsnorm(q[i], qn, self.eps), cos, sin, half) for i in range(self.heads)])
            k = np.stack([rope(rmsnorm(k[i], kn, self.eps), cos, sin, half) for i in range(self.kv_heads)])
            cache[L].append((k, v))
            attn = np.zeros((self.heads, self.hd), dtype=F)
            scale = F(1.0 / np.sqrt(self.hd))  # 0.25: exact
            for hh in range(self.heads):
                g = hh // group
                keys = np.stack([kv[0][g] for kv in cache[L]])       # [T, hd]
                vals = np.stack([kv[1][g] for kv in cache[L]])
                s = mul(matvec_fp32(keys, q[hh]), scale)             # sequential over head dim
                attn[hh] = matvec_fp32(vals.T, softmax(s))            # sequential over positions
            x = add(x, matvec(self.lw(L, "self_attn.o_proj.weight"), attn.reshape(-1)))
            h = rmsnorm(x, self.lw(L, "post_attention_layernorm.weight"), self.eps)
            gate = matvec(self.lw(L, "mlp.gate_proj.weight"), h)
            up = matvec(self.lw(L, "mlp.up_proj.weight"), h)
            a = mul(silu(gate), up)
            x = add(x, matvec(self.lw(L, "mlp.down_proj.weight"), a))
            if trace is not None:
                trace[f"layer{L}"] = x.copy()
        xf = rmsnorm(x, self.w["model.norm.weight"], self.eps)
        logits = matvec(self.w["lm_head.weight"], xf)
        if trace is not None:
            trace["final_norm"] = xf
            trace["logits"] = logits
        return logits


def prompt_and_expected():
    body = json.loads(ORACLE.read_text())
    run = body["results"]["TA-QW-REDUCED-EOS-1"]
    return run["prompt_token_ids"], run["generated_token_ids"]


def main():
    model = Model()
    prompt, expected = prompt_and_expected()
    cache = [[] for _ in range(model.layers)]
    for pos, tok in enumerate(prompt[:-1]):
        model.decode_token(tok, pos, cache)
    logits = model.decode_token(prompt[-1], len(prompt) - 1, cache)
    token = int(np.argmax(logits))           # lowest index on ties
    top = np.argsort(-logits.astype(np.float64))[:3]
    print("decoded", token, "oracle", expected[0], "match", token == expected[0],
          "top3", [(int(i), float(logits[i])) for i in top])


if __name__ == "__main__":
    main()
