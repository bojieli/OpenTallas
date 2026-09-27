#!/usr/bin/env python3
"""Golden model of the hardwired decode core (HDC) for the reduced Qwen3 vehicle.

This is the arithmetic SPECIFICATION the RTL implements.  Every operation is a
single IEEE binary32 operation with round-to-nearest-even (NumPy float32 rounds
each op), applied in exactly the order the hardware applies it:

* matvec      inputs rounded to BF16; per output, products (exact) accumulated
              sequentially over K from +0.0
* reduction   (stream unit: norms, the softmax denominator) R-ARITH: chunks of
              8 contiguous elements, each sequential from +0, the chunk sums a
              pairwise tree padded with +0 (reduce_chunked); reduce_sum (P=8
              interleaved partials + a pairwise tree) remains for the V4.1
              golden
* rsqrt       bit seed 0x5f3759df - (bits >> 1), three Newton-Raphson steps
* reciprocal  bit seed 0x7ef311c7 - bits, three Newton-Raphson steps
* exp         n = rint(x*log2e) by the 1.5*2^23 trick, two-constant Cody-Waite
              reduction, degree-6 Horner polynomial, scale by 2^n in the exponent
* softmax     max, exp(s - max), reduction sum, reciprocal, multiply (softmax());
              attention normalises AFTER the weighted sum (attend): P.V of
              the unnormalised exp, then x 1/Z
* attention   KV cache in BF16; q and the probabilities rounded to BF16 before
              their products (exact BF16 x BF16 products, FP32 accumulation);
              both products K-split INTERLEAVED over the core's lane groups
              (attn_splits, matvec_il): scores over head_dim, the weighted sum
              over positions, chunk sums added by a pairwise tree
* silu        g * reciprocal(1 + exp(-g))

See docs/TOKEN_PIPELINE_OPTIMIZATION_PLAN.md.  `decode_token` returns the
logits and every intermediate the RTL is checked against.
"""
import json
import os
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


def matvec(w, x, split=1):
    """y[n] = sum_k w[n,k] * bf16(x)[k].  K is cut into `split` contiguous chunks;
    each chunk is summed sequentially from +0 and the chunk sums are added by a
    pairwise tree ((c0+c1)+(c2+c3)).  split=1 is the plain sequential sum."""
    xb = to_bf16(x)
    kc = w.shape[1] // split
    assert kc * split == w.shape[1]
    parts = [matvec_fp32(w[:, c * kc:(c + 1) * kc], xb[c * kc:(c + 1) * kc]) for c in range(split)]
    while len(parts) > 1:
        parts = [add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


def split_for(n, k, groups, lanes=16, interleave=8):
    """The K-split the decode core uses for an n x k matrix: fewest engine cycles
    (rounds * k/S * interleave), the smaller split on a tie."""
    tiles = -(-n // (lanes * interleave))
    best = None
    s = 1
    while s <= groups:
        if k % s == 0:
            cycles = -(-tiles * s // groups) * (k // s) * interleave
            if best is None or cycles < best[0]:
                best = (cycles, s)
        s *= 2
    return best[1]


def p2floor(n):
    return 1 << (max(1, int(n)).bit_length() - 1)


def attn_splits(hd, groups, lanes=16):
    """K-splits of the two attention products on a core of `groups` lane groups
    (tools/hdc_program.py emits them; rtl/hdc/ot_hdc_matvec.sv runs them):
    scores split head_dim over min(hd, G) groups per position tile; the
    weighted sum splits positions over the G / (hd / lanes) groups per head_dim
    tile.  HDC_ATTN_SPLIT=0 in the environment keeps both unsplit (1, 1): the
    KV-in-HBM configuration, whose streamer (rtl/hdc/kv/ot_hdc_kv_stream.sv)
    fetches the unsplit op's word order."""
    if os.environ.get("HDC_ATTN_SPLIT", "1") == "0":
        return 1, 1
    return min(hd, p2floor(groups)), p2floor(max(1, groups // max(1, hd // lanes)))


def matvec_il(w, x, split=1):
    """y[n] = sum_k w[n,k] * x[k] with K cut INTERLEAVED into `split` chunks:
    chunk c holds k = c, c+S, c+2S, ... (k < K; a chunk may be short or empty),
    each summed sequentially from +0, the chunk sums added by the pairwise tree
    ((c0+c1)+(c2+c3)).  The attention products' order (KV-sourced ops, whose K
    is head_dim or the context length).  split=1 is matvec_fp32.  x is used
    as given (the caller rounds it)."""
    w = np.asarray(w, dtype=F)
    x = np.asarray(x, dtype=F)
    K = w.shape[1]
    parts = []
    for c in range(split):
        acc = np.zeros(w.shape[0], dtype=F)
        for k in range(c, K, split):
            acc = add(acc, mul(w[:, k], x[k]))
        parts.append(acc)
    while len(parts) > 1:
        parts = [add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


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


CHUNK = 8                     # R-ARITH chunk length (shared with the DeepSeek-V4.1 core)


def reduce_chunked(v, c=CHUNK):
    """The arithmetic contract R-ARITH of every Qwen3 stream-unit sum (norms,
    the softmax denominator): contiguous chunks of c elements, each summed
    sequentially from +0, and the chunk sums added by a pairwise tree
    ((s0 + s1) + (s2 + s3)) + ... padded with +0.  Independent of the stream
    unit's width (rtl/hdc/ot_hdc_vreduce.sv); shared with the V4.1 core."""
    v = np.asarray(v, dtype=F).reshape(-1)
    parts = []
    for i in range(0, max(len(v), 1), c):
        acc = F(0)
        for x in v[i:i + c]:
            acc = add(acc, x)
        parts.append(F(acc))
    n = 1
    while n < len(parts):
        n *= 2
    parts += [F(0)] * (n - len(parts))
    while len(parts) > 1:
        parts = [add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return F(parts[0])


# The stream unit the Qwen3 golden describes: HDC_SU_WIDTH >= 8 is the vector
# unit and its R-ARITH order; 1 is the scalar unit (rtl/hdc/ot_hdc_stream.sv)
# and its P=8 interleaved reducer -- the configurations not yet moved.
SU_WIDTH = int(os.environ.get("HDC_SU_WIDTH", 8))


def lane_sum(v):
    return reduce_sum(v) if SU_WIDTH == 1 else reduce_chunked(v)


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


def to_fp8(x):
    """FP32 -> FP8 E4M3 (bias 7, max 448, subnormal quantum 2^-9), round to
    nearest even, saturating; returned as FP32.  Every E4M3 value is a BF16
    value, so an FP8 KV cache still gives exact BF16 x BF16 products."""
    x = np.asarray(x, dtype=F)
    a = np.abs(x).astype(np.float64)
    _, ex = np.frexp(a)
    e = np.maximum(ex - 1, -6)                       # the binade (subnormals share 2^-6's quantum)
    q = np.ldexp(1.0, e - 3)
    r = np.minimum(np.round(a / q) * q, 448.0)       # np.round: half to even
    return z(np.where(x < 0, -r, r).astype(F))


# The KV cache's format: FP8 E4M3 on the vector core (the spec's design point:
# half the KV bytes of BF16), BF16 on the scalar core.  HDC_KV_FMT overrides.
KV_FMT = os.environ.get("HDC_KV_FMT", "fp8" if SU_WIDTH > 1 else "bf16")


def kv_round(x):
    return to_fp8(x) if KV_FMT == "fp8" else to_bf16(x)


def rstd(x, eps):
    return rsqrt(add(mul(lane_sum(mul(x, x)), F(1.0 / len(x))), F(eps)))


# NORM FOLD (the vector core; SU_WIDTH > 1, one die).  The two per-layer
# RMSNorms fold their weight into the following projections' columns, stored
# in BF16 (W' = bf16(W x diag(w))), and apply 1/rms AFTER them:
#   attention: q, k, v = (W'_qkv bf16(x)) x r        r = rstd(x)
#   MLP:       g, u    = (W'_gu  bf16(x)) x r
# so the sum of squares and the rsqrt run beside the projection instead of in
# front of it.  Mathematically RMSNorm; the rounding (and the BF16 of W x w)
# differ from the unfolded order, which the scalar core and the tensor-group
# path keep.
NORM_FOLD = SU_WIDTH > 1


def fold_cols(wmat, w):
    return to_bf16(mul(np.asarray(wmat, dtype=F), np.asarray(w, dtype=F)[None, :]))


def rmsnorm(x, w, eps):
    r = rsqrt(add(mul(lane_sum(mul(x, x)), F(1.0 / len(x))), F(eps)))
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
    return mul(e, reciprocal(lane_sum(e)))


def attend(scores, vals, s_pv):
    """One head's attention after its scores: the row max, e = exp(s - max)
    and its sum Z, the weighted sum of V by the UNNORMALISED e (BF16-rounded,
    K-split over positions), then one scale by 1/Z of the head's HD outputs
    (normalise-after-sum, as flash attention does): the stream unit makes one
    pass over the scores instead of two, and 1/Z is formed beside the
    weighted sum instead of before it."""
    e = exp(add(scores, neg(np.max(scores))))
    return mul(matvec_il(vals.T, to_bf16(e), s_pv), reciprocal(lane_sum(e)))


def silu(g):
    return mul(g, reciprocal(add(exp(mul(g, F(-1.0))), F(1.0))))


# -- the decode step ------------------------------------------------------------
def fold(parts):
    """The one-shot all-reduce of a tensor group (rtl/rom/ot_rom_oneshot_allreduce.sv):
    every die sums the partials in RANK order, ((p0 + p1) + p2) + p3, so all
    replicas hold the same bits."""
    acc = parts[0]
    for p in parts[1:]:
        acc = add(acc, p)
    return acc


class Model:
    def __init__(self, groups=1, tp=1):
        """`groups`: matrix-engine lane groups of the decode core; it fixes each
        matrix's K-split (split_for) and therefore the accumulation order.
        `tp`: dies of the tensor group (1: one core holds every matrix).  With
        tp > 1 every die is a decode core of `groups` groups holding a slice of
        every matrix, Megatron style (see decode_token_tp)."""
        self.groups = groups
        self.tp = tp
        self.cfg = json.loads(CONFIG.read_text())
        self.w = load_weights()
        c = self.cfg
        self.layers, self.hidden = c["num_hidden_layers"], c["hidden_size"]
        self.heads, self.kv_heads, self.hd = c["num_attention_heads"], c["num_key_value_heads"], c["head_dim"]
        self.eps, self.theta = c["rms_norm_eps"], c["rope_theta"]

    def lw(self, layer, name):
        return self.w[f"model.layers.{layer}.{name}"]

    def folded(self, layer, part):
        """The projections of `part` ('attn': q, k, v; 'mlp': gate, up) with the
        preceding RMSNorm weight folded into their columns (NORM_FOLD)."""
        cache = self.__dict__.setdefault("_folded", {})
        if (layer, part) not in cache:
            if part == "attn":
                w = self.lw(layer, "input_layernorm.weight")
                names = ("self_attn.q_proj.weight", "self_attn.k_proj.weight", "self_attn.v_proj.weight")
            else:
                w = self.lw(layer, "post_attention_layernorm.weight")
                names = ("mlp.gate_proj.weight", "mlp.up_proj.weight")
            cache[(layer, part)] = [fold_cols(self.lw(layer, n), w) for n in names]
        return cache[(layer, part)]

    def split(self, *mats):
        """K-split of the fused matrix formed by stacking `mats` row-wise."""
        n = sum(m.shape[0] for m in mats)
        return split_for(n, mats[0].shape[1], self.groups)

    def mv(self, x, *mats):
        """Rows of the fused matrix, returned per member."""
        s = self.split(*mats)
        return [matvec(m, x, s) for m in mats]

    # -- tensor-parallel group ------------------------------------------------------
    def die_heads(self, d):
        """Query heads of die d, and the KV heads they read (replicated on every
        die whose query heads use them when tp exceeds the KV head count)."""
        nh = self.heads // self.tp
        hs = list(range(d * nh, (d + 1) * nh))
        group = self.heads // self.kv_heads
        return hs, sorted({h // group for h in hs})

    def die_slices(self, d):
        """Rows (column-split) / columns (row-split) of every matrix held by die d:
        QKV, gate and up are split by output rows (heads / FFN rows); o and down
        by input columns, their partial outputs summed by the one-shot all-reduce;
        lm_head by vocabulary rows, the argmax combined by an all-gather."""
        hs, kvs = self.die_heads(d)
        ff = self.cfg["intermediate_size"] // self.tp
        vocab = self.w["lm_head.weight"].shape[0] // self.tp
        return dict(heads=hs, kv=kvs,
                    q_rows=np.concatenate([np.arange(h * self.hd, (h + 1) * self.hd) for h in hs]),
                    kv_rows=np.concatenate([np.arange(g * self.hd, (g + 1) * self.hd) for g in kvs]),
                    ff=np.arange(d * ff, (d + 1) * ff), vocab=np.arange(d * vocab, (d + 1) * vocab))

    def decode_token_tp(self, token, position, cache, trace=None):
        """One decode step of a tensor group of `tp` dies (docs/ARCHITECTURE_ATLAS.html
        6.6: one package, one tensor group).  Each die runs the same program on
        its slice; the arithmetic that changes relative to one core:

        * a column-split matrix (QKV, gate/up) keeps every output's own K sum,
          but the die's matrix is smaller, so split_for may choose another
          K-split for it and the output rounds differently;
        * a row-split matrix (o, down) gives each die a K-slice partial
          (its own split_for), and the all-reduce adds the partials in die order
          (`fold`);
        * lm_head rows are split by vocabulary: every logit is exactly the one
          core's (same K, same split), and the argmax over parts in die order,
          ties to the lower die, is the full argmax.

        Everything else (norms, residuals, the embedding) is replicated; KV heads
        are replicated where two dies' query heads share one, and both dies
        compute them bit-identically (asserted)."""
        tp, hd = self.tp, self.hd
        assert self.heads % tp == 0
        x = self.w["model.embed_tokens.weight"][token].astype(F)
        cos, sin, half = rope_tables(position, hd, self.theta)
        group = self.heads // self.kv_heads
        sl = [self.die_slices(d) for d in range(tp)]
        for L in range(self.layers):
            h = rmsnorm(x, self.lw(L, "input_layernorm.weight"), self.eps)
            qw, kw_, vw = (self.lw(L, f"self_attn.{n}_proj.weight") for n in "qkv")
            qn, kn = self.lw(L, "self_attn.q_norm.weight"), self.lw(L, "self_attn.k_norm.weight")
            ow = self.lw(L, "self_attn.o_proj.weight")
            kv_new = {}
            parts = []
            for d, s in enumerate(sl):
                q, k, v = self.mv(h, qw[s["q_rows"]], kw_[s["kv_rows"]], vw[s["kv_rows"]])
                q, k, v = q.reshape(-1, hd), k.reshape(-1, hd), v.reshape(-1, hd)
                q = np.stack([rope(rmsnorm(q[i], qn, self.eps), cos, sin, half) for i in range(len(q))])
                k = np.stack([rope(rmsnorm(k[i], kn, self.eps), cos, sin, half) for i in range(len(k))])
                for i, g in enumerate(s["kv"]):
                    kb, vb = to_bf16(k[i]), to_bf16(v[i])
                    if g in kv_new:
                        assert np.array_equal(bits(kv_new[g][0]), bits(kb)) and \
                            np.array_equal(bits(kv_new[g][1]), bits(vb)), "replicated KV head differs"
                    kv_new[g] = (kb, vb)
                parts.append((d, q))
            cache[L].append((np.stack([kv_new[g][0] for g in range(self.kv_heads)]),
                             np.stack([kv_new[g][1] for g in range(self.kv_heads)])))
            scale = F(1.0 / np.sqrt(hd))
            s_sc, s_pv = attn_splits(hd, self.groups)
            partial = []
            for d, q in parts:
                s = sl[d]
                attn = np.zeros((len(s["heads"]), hd), dtype=F)
                for i, hh in enumerate(s["heads"]):
                    g = hh // group
                    keys = np.stack([kv[0][g] for kv in cache[L]])
                    vals = np.stack([kv[1][g] for kv in cache[L]])
                    sc = mul(matvec_il(keys, to_bf16(q[i]), s_sc), scale)
                    attn[i] = attend(sc, vals, s_pv)
                partial.append(self.mv(attn.reshape(-1), ow[:, s["q_rows"]])[0])
            x = add(x, fold(partial))
            h = rmsnorm(x, self.lw(L, "post_attention_layernorm.weight"), self.eps)
            gw, uw = self.lw(L, "mlp.gate_proj.weight"), self.lw(L, "mlp.up_proj.weight")
            dw = self.lw(L, "mlp.down_proj.weight")
            partial = []
            for s in sl:
                gate, up = self.mv(h, gw[s["ff"]], uw[s["ff"]])
                partial.append(self.mv(mul(silu(gate), up), dw[:, s["ff"]])[0])
            x = add(x, fold(partial))
            if trace is not None:
                trace[f"layer{L}"] = x.copy()
        xf = rmsnorm(x, self.w["model.norm.weight"], self.eps)
        lm = self.w["lm_head.weight"]
        logits = np.concatenate([self.mv(xf, lm[s["vocab"]])[0] for s in sl])
        if trace is not None:
            trace["final_norm"] = xf
            trace["logits"] = logits
        return logits

    def decode_token(self, token, position, cache, trace=None):
        """One decode step.  `cache[layer]` is a list of (k, v) per earlier position
        (each [kv_heads, hd] float32); the step appends its own row."""
        if self.tp > 1:
            return self.decode_token_tp(token, position, cache, trace)
        x = self.w["model.embed_tokens.weight"][token].astype(F)
        cos, sin, half = rope_tables(position, self.hd, self.theta)
        group = self.heads // self.kv_heads
        for L in range(self.layers):
            if NORM_FOLD:
                r = rstd(x, self.eps)
                q, k, v = (mul(t, r) for t in self.mv(x, *self.folded(L, "attn")))
            else:
                h = rmsnorm(x, self.lw(L, "input_layernorm.weight"), self.eps)
                q, k, v = self.mv(h, self.lw(L, "self_attn.q_proj.weight"), self.lw(L, "self_attn.k_proj.weight"),
                                  self.lw(L, "self_attn.v_proj.weight"))
            q, k, v = q.reshape(self.heads, self.hd), k.reshape(self.kv_heads, self.hd), v.reshape(self.kv_heads, self.hd)
            qn, kn = self.lw(L, "self_attn.q_norm.weight"), self.lw(L, "self_attn.k_norm.weight")
            q = np.stack([rope(rmsnorm(q[i], qn, self.eps), cos, sin, half) for i in range(self.heads)])
            k = np.stack([rope(rmsnorm(k[i], kn, self.eps), cos, sin, half) for i in range(self.kv_heads)])
            # KV cache in BF16; q and the probabilities are BF16-rounded before
            # their products, so every attention product is an exact BF16 x BF16
            # product any lane can form
            cache[L].append((kv_round(k), kv_round(v)))
            attn = np.zeros((self.heads, self.hd), dtype=F)
            scale = F(1.0 / np.sqrt(self.hd))  # 0.25: exact
            s_sc, s_pv = attn_splits(self.hd, self.groups)
            for hh in range(self.heads):
                g = hh // group
                keys = np.stack([kv[0][g] for kv in cache[L]])       # [T, hd]
                vals = np.stack([kv[1][g] for kv in cache[L]])
                s = mul(matvec_il(keys, to_bf16(q[hh]), s_sc), scale)       # head dim, interleaved K-split
                attn[hh] = attend(s, vals, s_pv)     # one-pass softmax, normalised after P.V
            x = add(x, self.mv(attn.reshape(-1), self.lw(L, "self_attn.o_proj.weight"))[0])
            if NORM_FOLD:
                r = rstd(x, self.eps)
                gate, up = (mul(t, r) for t in self.mv(x, *self.folded(L, "mlp")))
            else:
                h = rmsnorm(x, self.lw(L, "post_attention_layernorm.weight"), self.eps)
                gate, up = self.mv(h, self.lw(L, "mlp.gate_proj.weight"), self.lw(L, "mlp.up_proj.weight"))
            a = mul(silu(gate), up)
            x = add(x, self.mv(a, self.lw(L, "mlp.down_proj.weight"))[0])
            if trace is not None:
                trace[f"layer{L}"] = x.copy()
        xf = rmsnorm(x, self.w["model.norm.weight"], self.eps)
        logits = self.mv(xf, self.w["lm_head.weight"])[0]
        if trace is not None:
            trace["final_norm"] = xf
            trace["logits"] = logits
        return logits


def prompt_and_expected():
    body = json.loads(ORACLE.read_text())
    run = body["results"]["TA-QW-REDUCED-EOS-1"]
    return run["prompt_token_ids"], run["generated_token_ids"]


def main():
    import hdc_isa
    model = Model(hdc_isa.GROUPS)
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
