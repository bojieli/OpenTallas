#!/usr/bin/env python3
"""Golden model of a hardwired decode core (HDC) for the reduced DeepSeek-V4.1-Flash.

The arithmetic SPECIFICATION of a future HDC-based V4.1 ROM package, written the
way tools/hdc_golden.py specifies the reduced Qwen3 core: every operation is one
IEEE binary32 operation (the qualified add/mul pipes: RNE, gradual underflow,
every zero result canonical +0), applied in exactly the order the hardware
applies it.  The primitives (add, mul, neg, exp, rsqrt, reduce_sum, to_bf16,
matvec_fp32) are imported from hdc_golden; this file composes the V4.1
operators from them.  It is an independent model of the MATH: it reads the
checkpoint bytes and the release's published semantics (inference/model.py,
inference/engram.py, inference/kernel.py), never the ABI3 compiler.

Numerics the model DECLARES (the release's own storage and quantisation points,
kept because they are the model, not an implementation accident):

* residual stream, sublayer inputs and outputs are BF16 tensors: every value
  that the reference stores in a BF16 tensor is rounded to BF16 (RNE) here;
* FP8 linears (wq_a, wq_b, wkv, wo_b, the indexer's wq_b, the Engram wkv, the
  shared expert) quantise their activation per 32-element block to E4M3 with a
  power-of-two (UE8M0) scale; FP4 routed experts (E2M1 weights, UE8M0 scale per
  row and 32-column block) take the same FP8 activation;
* the window KV row is FP8 quantise-dequantised (block 32), index keys and index
  queries FP4 quantise-dequantised (block 32, UE8M0 scale), compressed KV rows
  FP4 quantise-dequantised (block 16, E4M3 scale);
* attention probabilities are rounded to BF16 before the probability x value
  product, as the release's sparse-attention kernel does.

Orders the model CHOOSES (the reference leaves them to a GPU library):

* BF16/FP32 matvec: per output, products accumulated sequentially over K from
  +0 (hdc_golden.matvec_fp32; BF16 x BF16 products are exact);
* FP8/FP4 linear: per 32-wide K block the dot product of the two quantised
  operands is formed EXACTLY and rounded once to FP32 (every product has at most
  8 significant bits and the block sum spans < 42 bits, so a small fixed-point
  accumulator is exact); the block sum is scaled by 2^(e_w + e_x) (exact) and
  the blocks are accumulated sequentially from +0 -- the release kernel's own
  outer order;
* every long sum (sums of squares, softmax denominators, the index-head sum,
  hyper-connection norms) is hdc_golden.reduce_sum: P=8 interleaved partials
  then a pairwise tree; sums of 2-6 terms (hyper-connection mixes, Sinkhorn
  rows/columns, routing-weight sums, the compressor's 2-slot pooling) are
  sequential from the first term, in index order;
* where the reference divides (attention normalisation, Sinkhorn, the
  compressor's pooling softmax, routing-weight normalisation, sigmoid, SiLU, a
  mean) the model divides: IEEE binary32 division, the qualified divider pipe
  rtl/abi3/ot_a3_fp32_div_rne_pipe.sv; a Newton reciprocal-and-multiply there
  measurably disagrees with the reference more often (see the inventory);
  sqrt is IEEE; rsqrt is hdc_golden's Newton pipeline (the reference's rsqrt is
  itself approximate);
* softmax over attention scores is two-pass (max, then exp) over the whole
  selected set; the attention sink joins only the denominator, after the sum,
  exactly as the release's kernel adds it;
* top-k selections rank by value descending with ties to the LOWER index;
  argmax of the logits takes the lowest id on ties.

New special functions (see docs/HDC_DEEPSEEK_V41_OPERATOR_INVENTORY.md):

* softplus(x) = max(x, 0) + log1p(t), t = exp(-|x|) in (0, 1]; log1p(t) =
  2 atanh(u), u = t / (2 + t) in (0, 1/3], by a degree-17 odd Horner series in
  u (error < 5e-10); no logarithm unit and no branch but a sign;
* sigmoid(x) = 1 / (1 + exp(-x)) and silu(x) = x / (1 + exp(-x)), the
  reference's forms;
* FP8/FP4 quantisers: power-of-two scale from the block's absolute maximum
  (exponent arithmetic on the bits), E4M3/E2M1 round-to-nearest-even with
  saturation; the E4M3-scaled FP4 quantiser rounds by comparing |x| against
  the seven code midpoints times the scale, exactly (no divider);
* the Engram hash: 64-bit integer multiply by a constant, XOR, and a modulo by
  a constant prime (a Barrett reduction in hardware).

`Model.decode_token` runs one token through the 40 backbone layers and returns
the FP32 logits; `generate` feeds a prompt one position at a time, as the HDC
does, then decodes greedily.  `python3 tools/hdc_golden_v41.py` decodes the oracle's workload.
"""
from __future__ import annotations

import json
import math
import os
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hdc_golden import (  # noqa: E402
    F, add, bits, exp, from_bits, matvec_fp32, mul, neg, reduce_sum, rsqrt, to_bf16, z,
)

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path(os.environ.get("OPENTALLAS_BUILD", ROOT / "build"))
SNAPSHOT = BUILD / "models/deepseek-v4.1-flash-reduced-v2"
CHECKPOINT = SNAPSHOT / "model-00001-of-00001.safetensors"
MODEL_DIR = ROOT / "compiler/models/deepseek-v4.1-flash-reduced-v2"
CONFIG = MODEL_DIR / "inference_config.json"
TOKENIZER = MODEL_DIR / "tokenizer.json"
ORACLE = ROOT / "results/abi3/deepseek_v41_reduced_v2_reference_oracle_fp8.json"
WORKLOAD = "TA-DS41-REDUCED-EOS-1"

FP8_MAX = F(448.0)
FP8_MAX_INV = F(1.0 / 448.0)
FP4_MAX = 6.0
FP4_MAX_INV = F(1.0 / 6.0)
FP8_AMAX_FLOOR = F(1e-4)                 # act_quant's clamp_min on the block maximum
FP4_AMAX_FLOOR_E8M0 = F(6.0 * 2.0 ** -126)
FP4_AMAX_FLOOR_E4M3 = F(6.0 * 2.0 ** -9)  # compressed KV: keeps an all-zero block's scale nonzero
E2M1_VALUES = np.array([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0])
E2M1_MIDPOINTS = (E2M1_VALUES[:-1] + E2M1_VALUES[1:]) / 2   # 0.25 .. 5.0
# log1p(t) = 2*atanh(u) = 2*(u + u^3/3 + u^5/5 + ...), u = t/(2+t) <= 1/3
LOG1P_ODD = [F(1.0 / (2 * i + 1)) for i in range(8, -1, -1)]  # 1/17 .. 1/1, Horner in u^2


# -- storage formats -------------------------------------------------------------
def _e4m3_table():
    out = np.zeros(256, dtype=np.float64)
    for c in range(256):
        s, e, m = c >> 7, (c >> 3) & 15, c & 7
        if e == 15 and m == 7:
            v = np.nan
        elif e == 0:
            v = m / 8 * 2.0 ** -6
        else:
            v = (1 + m / 8) * 2.0 ** (e - 7)
        out[c] = -v if s else v
    return out


E4M3 = _e4m3_table()
E2M1 = np.concatenate([E2M1_VALUES, -E2M1_VALUES])


class Q8:
    """A block-quantised weight: `q` holds the E4M3 or E2M1 values (float64, exact),
    `e` the power-of-two exponent of every (row, 32-column block)."""

    def __init__(self, q, e):
        self.q, self.e = q, e
        self.shape = q.shape

    def dense(self):
        return (self.q * np.exp2(np.repeat(self.e, 32, axis=1)[:, :self.q.shape[1]])).astype(F)


def load_checkpoint(path=CHECKPOINT):
    raw = Path(path).read_bytes()
    n = struct.unpack("<Q", raw[:8])[0]
    header = json.loads(raw[8:8 + n])
    base = 8 + n
    t = {}
    for name, meta in header.items():
        if name == "__metadata__" or name.startswith("mtp."):
            continue
        s, e = meta["data_offsets"]
        buf, shape, dt = raw[base + s:base + e], meta["shape"], meta["dtype"]
        if dt == "F32":
            v = np.frombuffer(buf, dtype=np.float32).reshape(shape).copy()
        elif dt == "BF16":
            v = from_bits(np.frombuffer(buf, dtype=np.uint16).astype(np.uint32) << 16).reshape(shape)
        elif dt == "F8_E4M3":
            v = np.frombuffer(buf, dtype=np.uint8).reshape(shape)       # codes; decoded below
        elif dt == "F8_E8M0":
            v = np.frombuffer(buf, dtype=np.uint8).astype(np.int32).reshape(shape) - 127
        elif dt == "I8":                                                   # packed E2M1, low nibble first
            b = np.frombuffer(buf, dtype=np.uint8).reshape(shape)
            v = np.stack([E2M1[b & 15], E2M1[b >> 4]], axis=-1).reshape(shape[0], shape[1] * 2)
        else:
            raise ValueError(f"{name}: unsupported dtype {dt}")
        t[name] = v
    return t


def _blocked(codes, exps, name):
    """E4M3 codes with a 32x32-block (or per-row) UE8M0 exponent -> Q8."""
    q = E4M3[codes] if codes.dtype == np.uint8 else codes
    rows, cols = q.shape
    kb = -(-cols // 32)
    if exps.shape == (rows, kb):            # per row (FP4 experts, Engram rows)
        e = exps
    else:                                    # per 32x32 block
        assert exps.shape == (-(-rows // 32), kb), (name, exps.shape)
        e = np.repeat(exps, 32, axis=0)[:rows]
    return Q8(q.astype(np.float64), e.astype(np.int64))


# -- quantisers (the release's act_quant / fp4_act_quant, as hardware) ---------
def _ceil_log2(v):
    """ceil(log2(v)) of positive normal binary32 values from their bits, as the
    release's fast_log2_ceil: exponent - 127, plus one if any mantissa bit is set."""
    b = bits(v).astype(np.int64)
    return ((b >> 23) & 0xFF) - 127 + ((b & 0x7FFFFF) != 0)


def _round_grid(v, min_exp, mant_bits):
    """Round |v| to a float grid with `mant_bits` mantissa bits and minimum normal
    exponent `min_exp`, nearest-even.  v: float64, exact inputs."""
    a = np.abs(v)
    e = np.floor(np.log2(np.where(a > 0, a, 1.0)))
    e = np.maximum(e, min_exp)
    step = np.exp2(e - mant_bits)
    return np.sign(v) * np.round(a / step) * step      # np.round is half-to-even


def quant_fp8(x, block=32):
    """E4M3 codes (as float64 values) and the per-block exponent of act_quant with a
    UE8M0 scale: s = 2^ceil(log2(amax * (1/448))), q = e4m3(clamp(x / s))."""
    x = np.asarray(x, dtype=F).reshape(-1, block)
    amax = np.maximum(np.max(np.abs(x), axis=1), FP8_AMAX_FLOOR).astype(F)
    e = _ceil_log2(mul(amax, FP8_MAX_INV))
    v = np.clip(x.astype(np.float64) * np.exp2(-e)[:, None], -448.0, 448.0)
    q = _round_grid(v, -6, 3)
    return q.reshape(-1), e


def qdq_fp8(x, block=32):
    """act_quant(..., inplace=True): quantise then dequantise, stored as BF16."""
    q, e = quant_fp8(x, block)
    return to_bf16((q.reshape(-1, block) * np.exp2(e)[:, None]).astype(F).reshape(-1))


def qdq_fp4_e8m0(x, block=32):
    """fp4_act_quant with a UE8M0 scale (index keys and queries), dequantised to BF16."""
    x = np.asarray(x, dtype=F).reshape(-1, block)
    amax = np.maximum(np.max(np.abs(x), axis=1), FP4_AMAX_FLOOR_E8M0).astype(F)
    e = _ceil_log2(mul(amax, FP4_MAX_INV))
    v = np.clip(x.astype(np.float64) * np.exp2(-e)[:, None], -FP4_MAX, FP4_MAX)
    q = _round_grid(v, 0, 1)
    return to_bf16((q * np.exp2(e)[:, None]).astype(F).reshape(-1))


def _e4m3_round(v):
    return _round_grid(np.asarray(v, dtype=np.float64), -6, 3)


def qdq_fp4_e4m3(x, block=16):
    """fp4_act_quant with an E4M3 scale (compressed KV rows): s = e4m3(amax / 6),
    q = e2m1(clamp(x / s)).  The E2M1 code is chosen by comparing |x| with each
    code midpoint times s -- exact products, so the rounding is the exact rounding
    of the real quotient (ties to even code) and no divider is needed."""
    x = np.asarray(x, dtype=F).reshape(-1, block)
    amax = np.maximum(np.max(np.abs(x), axis=1), FP4_AMAX_FLOOR_E4M3).astype(F)
    s = _e4m3_round(amax.astype(np.float64) / FP4_MAX)   # exact quotient, rounded once to E4M3
    a = np.abs(x.astype(np.float64))
    code = np.zeros(a.shape, dtype=np.int64)
    for i, m in enumerate(E2M1_MIDPOINTS):
        t = m * s[:, None]
        # above the midpoint -> next code; on it -> the even code (odd codes 1,3,5 round up to i+1 only when i+1 is even)
        code = np.where((a > t) | ((a == t) & ((i + 1) % 2 == 0)), i + 1, code)
    q = np.sign(x) * E2M1_VALUES[code]
    return to_bf16((q * s[:, None]).astype(F).reshape(-1))


# -- linears -------------------------------------------------------------------
def linear_q(w: Q8, x):
    """FP8 activation x FP8/FP4 weight, output BF16.  Per 32-wide K block: exact dot
    product of the quantised operands, rounded once to FP32, scaled by 2^(e_w+e_x);
    blocks accumulated sequentially from +0."""
    xq, xe = quant_fp8(x)
    n, k = w.q.shape
    acc = np.zeros(n, dtype=F)
    for b in range(k // 32):
        d = (w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(F)   # exact, rounded once
        acc = add(acc, np.ldexp(d, w.e[:, b] + xe[b]).astype(F))
    return to_bf16(acc)


def linear_bf16(w, x):
    """BF16 weight, BF16 activation: exact products, sequential FP32 sum, BF16 out."""
    return to_bf16(matvec_fp32(w, to_bf16(x)))


def dots(a, b):
    """out[i, j] = sum_k a[i, k] * b[j, k], each sum sequential over k from +0: one
    matvec_fp32 per row of `a`, evaluated for all rows at once."""
    acc = np.zeros((a.shape[0], b.shape[0]), dtype=F)
    for k in range(a.shape[1]):
        acc = add(acc, mul(a[:, k][:, None], b[:, k][None, :]))
    return acc


def reduce_rows(v):
    """hdc_golden.reduce_sum of every row of a 2-D array at once (P=8 interleaved
    partials, then the pairwise tree)."""
    v = np.asarray(v, dtype=F)
    part = np.zeros((v.shape[0], 8), dtype=F)
    for i in range(v.shape[1]):
        part[:, i % 8] = add(part[:, i % 8], v[:, i])
    while part.shape[1] > 1:
        part = add(part[:, 0::2], part[:, 1::2])
    return part[:, 0]


def seqsum(terms):
    acc = terms[0]
    for t in terms[1:]:
        acc = add(acc, t)
    return acc


# -- special functions ------------------------------------------------------------
def div(a, b):
    """IEEE binary32 division, RNE, canonical +0: the qualified divider pipe
    (rtl/abi3/ot_a3_fp32_div_rne_pipe.sv).  Used exactly where the reference divides."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return z(np.asarray(a, dtype=F) / np.asarray(b, dtype=F))


def sqrt(a):
    """IEEE binary32 square root, RNE."""
    return z(np.sqrt(np.asarray(a, dtype=F)))


def sigmoid(x):
    """1 / (1 + exp(-x)), the reference's form."""
    return div(F(1.0), add(exp(neg(x)), F(1.0)))


def silu(x):
    """x / (1 + exp(-x)), the form of torch's SiLU kernel."""
    return div(x, add(exp(neg(x)), F(1.0)))


def log1p_unit(t):
    """log1p(t) for t in [0, 1]: 2*atanh(t / (2 + t)), odd series to u^17."""
    u = div(t, add(t, F(2.0)))
    u2 = mul(u, u)
    p = np.full_like(u, LOG1P_ODD[0])
    for c in LOG1P_ODD[1:]:
        p = add(mul(p, u2), c)
    return mul(mul(u, p), F(2.0))


def softplus(x):
    x = np.asarray(x, dtype=F)
    t = exp(neg(np.abs(x).astype(F)))
    return add(np.maximum(x, F(0)).astype(F), log1p_unit(t))


def rmsnorm_bf16(x, w, eps):
    """The release's RMSNorm: x * rsqrt(mean(x^2) + eps), times the gain, stored BF16."""
    r = rsqrt(add(div(reduce_rows(mul(x, x)[None, :])[0], F(len(x))), F(eps)))
    return to_bf16(mul(w, mul(x, r)))


def topk_lowest_index(v, k):
    """Indices of the k largest values, ties to the lower index, in rank order.  In
    hardware: rank_i = #{j : v_j > v_i or (v_j == v_i and j < i)}, selected when
    rank_i < k -- one comparator per pair, so no sorting network state."""
    v = np.asarray(v, dtype=np.float64)
    order = np.lexsort((np.arange(len(v)), -v))
    return order[:k]


# -- RoPE ---------------------------------------------------------------------------
def rope_freqs(dim, original_seq_len, base, factor, beta_fast, beta_slow):
    """precompute_freqs_cis' frequencies in binary32, op by op (a table ROM)."""
    freqs = (F(1.0) / (F(base) ** (np.arange(0, dim, 2, dtype=F) / F(dim)).astype(F))).astype(F)
    if original_seq_len > 0:
        def corrected(rot):
            return dim * math.log(original_seq_len / (rot * 2 * math.pi)) / (2 * math.log(base))
        low = max(math.floor(corrected(beta_fast)), 0)
        high = min(math.ceil(corrected(beta_slow)), dim - 1)
        ramp = np.clip((np.arange(dim // 2, dtype=F) - F(low)) / F(max(high - low, 1e-3)), 0, 1).astype(F)
        smooth = (F(1) - ramp).astype(F)
        freqs = ((freqs / F(factor)).astype(F) * (F(1) - smooth)).astype(F) + (freqs * smooth).astype(F)
    return freqs.astype(F)


def rope_cs(freqs, position):
    angle = (F(position) * freqs).astype(F)
    return np.cos(angle.astype(np.float64)).astype(F), np.sin(angle.astype(np.float64)).astype(F)


def rope_tail(v, cs, inverse=False):
    """Rotate the last 2*len(cos) elements of each row of v as ADJACENT pairs (the
    release's complex view), stored BF16.  inverse=True applies the conjugate."""
    c, s = cs
    v = np.array(v, dtype=F)
    rd = 2 * len(c)
    a, b = v[..., -rd::2], v[..., -rd + 1::2]
    if inverse:
        re, im = add(mul(a, c), mul(b, s)), add(mul(b, c), neg(mul(a, s)))
    else:
        re, im = add(mul(a, c), neg(mul(b, s))), add(mul(a, s), mul(b, c))
    v[..., -rd::2], v[..., -rd + 1::2] = to_bf16(re), to_bf16(im)
    return v


# -- Engram tables --------------------------------------------------------------------
def _is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def compressed_token_map(tokenizer_path, size):
    """engram.build_compressed_token_map, restated: tokens that normalise alike share
    an id.  A ROM table in hardware."""
    from tokenizers import Regex, Tokenizer, normalizers
    tok = Tokenizer.from_file(str(tokenizer_path))
    sentinel = ""
    norm = normalizers.Sequence([
        normalizers.NFKC(), normalizers.NFD(), normalizers.StripAccents(), normalizers.Lowercase(),
        normalizers.Replace(Regex(r"[ \t\r\n]+"), " "), normalizers.Replace(Regex(r"^ $"), sentinel),
        normalizers.Strip(), normalizers.Replace(sentinel, " "),
    ])
    key_to_new, lookup = {}, []
    for tid in range(size):
        text = tok.decode([tid], skip_special_tokens=False)
        if "�" in text:
            key = tok.id_to_token(tid)
        else:
            n = norm.normalize_str(text)
            key = n if n else text
        lookup.append(key_to_new.setdefault(key, len(key_to_new)))
    return np.array(lookup, dtype=np.int64), len(key_to_new)


class EngramTables:
    """Primes, offsets and multipliers of engram.EngramLayout / NgramHashState."""

    def __init__(self, c, vocab):
        self.layer_ids = list(c["engram_layer_ids"])
        self.n = c["engram_max_ngram_size"]
        heads = c["engram_n_heads"]
        seen, primes = set(), []
        for _ in self.layer_ids:
            per = []
            for _ in range(self.n - 1):
                cur, row = c["engram_vocab_size"] - 1, []
                for _ in range(heads):
                    cur += 1
                    while not _is_prime(cur) or cur in seen:
                        cur += 1
                    seen.add(cur)
                    row.append(cur)
                per.append(row)
            primes.append(per)
        self.primes = np.array(primes, dtype=np.int64)                    # [layer, ngram-1, head]
        flat = self.primes.reshape(len(self.layer_ids), -1)
        self.offsets = np.concatenate([np.zeros((len(flat), 1), np.int64), np.cumsum(flat, 1)[:, :-1]], 1)
        self.token_map, cv = compressed_token_map(TOKENIZER, vocab)
        assert cv == c["engram_compressed_vocab_size"], (cv, c["engram_compressed_vocab_size"])
        bound = max(1, (np.iinfo(np.int64).max // cv) // 2)
        self.multipliers = np.stack([
            np.random.default_rng(10007 * lid).integers(0, bound, size=(self.n,), dtype=np.int64) * 2 + 1
            for lid in self.layer_ids])                                    # [layer, n]
        self.pad = int(self.token_map[c["engram_pad_id"]])

    def hashes(self, history, li):
        """Hash ids of the n-grams ending at the newest token of `history` (raw ids,
        oldest first) for engram layer index li: [(n-1) * heads]."""
        toks = [int(self.token_map[history[-1 - s]]) if s < len(history) else self.pad for s in range(self.n)]
        out, rolling = [], None
        for s in range(self.n):
            p = toks[s] * int(self.multipliers[li, s])          # < 2^63 by the multiplier bound
            rolling = p if rolling is None else rolling ^ p
            if s:
                out.extend(int(rolling % int(q)) for q in self.primes[li, s - 1])
        return np.array(out, dtype=np.int64) + self.offsets[li]


# -- the model ------------------------------------------------------------------------
class Model:
    def __init__(self, config=CONFIG, checkpoint=CHECKPOINT, vendor_decode_from=None):
        """`vendor_decode_from`: VALIDATION ONLY.  From this position on, attention
        streams its KV in the release decode kernel's 64-entry blocks (vendor_blocks)
        instead of the specified two-pass softmax.  The release computes a prompt in
        one prefill call, whose kernel sees at most 64 entries per query here (one
        block), and every later token in a decode call, whose ring-buffer layout
        splits the context across blocks.  Setting it to the prompt length makes
        this model follow the reference's own evaluation order."""
        self.vendor_decode_from = vendor_decode_from
        c = self.c = json.loads(Path(config).read_text())
        t = load_checkpoint(checkpoint)
        self.L = c["n_layers"]
        self.dim, self.hc = c["dim"], c["hc_mult"]
        self.heads, self.hd, self.rd = c["n_heads"], c["head_dim"], c["rope_head_dim"]
        self.eps, self.hc_eps = F(c["norm_eps"]), F(c["hc_eps"])
        self.ratio = c["compress_ratios"][:self.L]
        self.kv_src = list(c["kv_source_layers"])
        self.idx_src = list(c["index_source_layers"])
        self.cand_src = c["candidate_source_layer"]
        self.topk, self.cand_k, self.cand_b = c["index_topk"], c["candidate_topk_blocks"], c["candidate_block_size"]
        self.ih, self.ihd = c["index_n_heads"], c["index_head_dim"]
        self.groups, self.o_rank = c["o_groups"], c["o_lora_rank"]
        self.n_exp, self.k_exp = c["n_routed_experts"], c["n_activated_experts"]
        self.route_scale, self.limit = F(c["route_scale"]), F(c["swiglu_limit"])
        self.window = c["window_size"]
        self.attn_scale = F(self.hd ** -0.5)
        self.index_w_scale = F(self.ihd ** -0.5 * self.ih ** -0.5)
        self.engram_scale = F(self.dim ** -0.5)
        self.sinkhorn_iters = c["hc_sinkhorn_iters"]
        self.freqs_plain = rope_freqs(self.rd, 0, c["rope_theta"], c["rope_factor"], c["beta_fast"], c["beta_slow"])
        self.freqs_yarn = rope_freqs(self.rd, c["original_seq_len"], c["compress_rope_theta"], c["rope_factor"],
                                     c["beta_fast"], c["beta_slow"])
        self.w = {}
        for name, v in t.items():
            if name.endswith(".scale"):
                continue
            sc = name[:-len(".weight")] + ".scale" if name.endswith(".weight") else None
            if sc in t and not name.endswith("engram.embed.weight"):
                self.w[name] = _blocked(v, t[sc], name)
            else:
                self.w[name] = v
        # wo_a ships FP8 with a 32x32 UE8M0 scale and the release dequantises it to BF16 (convert.py)
        for L in range(self.L):
            k = f"layers.{L}.attn.wo_a.weight"
            self.w[k] = to_bf16(self.w[k].dense())
        self.emb_codes = {L: (t[f"layers.{L}.engram.embed.weight"], t[f"layers.{L}.engram.embed.scale"][:, 0])
                          for L in c["engram_layer_ids"]}
        self.engram = EngramTables(c, c["vocab_size"])
        # the source layer each layer reads compressed KV / index selections from
        self.kv_of = {L: max(s for s in self.kv_src if s <= L) for L in range(self.L) if self.ratio[L]}
        self.idx_of = {L: max(s for s in self.idx_src if s <= L) for L in range(self.L) if self.ratio[L]}

    def lw(self, L, name):
        return self.w[f"layers.{L}.{name}"]

    def new_state(self):
        return {"tokens": [], "win": [[] for _ in range(self.L)], "ckv": {s: [] for s in self.kv_src},
                "ik": {s: [] for s in self.kv_src}, "slots": {s: [] for s in self.kv_src}}

    # -- hyper-connections ------------------------------------------------------------
    def hc_mixes(self, x, L, which):
        """x: [hc, dim] BF16-valued.  Returns pre [hc], post [hc], comb [hc, hc]."""
        fn, scale, base = (self.lw(L, f"hc_{which}_{s}") for s in ("fn", "scale", "base"))
        flat = x.reshape(-1)
        r = rsqrt(add(div(reduce_rows(mul(flat, flat)[None, :])[0], F(flat.size)), self.eps))
        mixes = mul(matvec_fp32(fn, flat), r)
        h = self.hc
        pre = add(sigmoid(add(mul(mixes[:h], scale[0]), base[:h])), self.hc_eps)
        post = mul(sigmoid(add(mul(mixes[h:2 * h], scale[1]), base[h:2 * h])), F(2.0))
        comb = add(mul(mixes[2 * h:], scale[2]), base[2 * h:]).reshape(h, h)
        # row softmax + eps, then column normalisation, then (iters-1) x (row, column)
        m = np.max(comb, axis=1, keepdims=True)
        e = exp(add(comb, neg(m)))
        rs = seqsum([e[:, k] for k in range(h)])
        comb = add(div(e, rs[:, None]), self.hc_eps)

        def cols(cm):
            cs = seqsum([cm[j, :] for j in range(h)])
            return div(cm, add(cs, self.hc_eps)[None, :])

        def rows(cm):
            rs = seqsum([cm[:, k] for k in range(h)])
            return div(cm, add(rs, self.hc_eps)[:, None])

        comb = cols(comb)
        for _ in range(self.sinkhorn_iters - 1):
            comb = cols(rows(comb))
        return pre, post, comb

    def hc_pre(self, x, pre):
        return to_bf16(seqsum([mul(pre[j], x[j]) for j in range(self.hc)]))

    def hc_post(self, y, res, post, comb):
        mix = [seqsum([mul(comb[j, k], res[j]) for j in range(self.hc)]) for k in range(self.hc)]
        return to_bf16(np.stack([add(mul(post[k], y), mix[k]) for k in range(self.hc)]))

    # -- Engram -------------------------------------------------------------------------
    def engram_layer(self, h, L, state):
        li = self.engram.layer_ids.index(L)
        ids = self.engram.hashes(state["tokens"], li)
        codes, sc = self.emb_codes[L]
        rows = to_bf16((E4M3[codes[ids]] * np.exp2(sc[ids])[:, None]).astype(F)).reshape(-1)
        kv = linear_q(self.lw(L, "engram.wkv.weight"), rows)
        key = kv[:self.hc * self.dim].reshape(self.hc, self.dim)
        value = kv[self.hc * self.dim:]
        wgt = mul(self.lw(L, "engram.q_weight"), self.lw(L, "engram.k_weight"))
        out = []
        for j in range(self.hc):
            hj, kj = h[j], key[j]
            n = F(self.dim)
            rstd = mul(rsqrt(add(div(reduce_sum(mul(hj, hj)), n), self.eps)),
                       rsqrt(add(div(reduce_sum(mul(kj, kj)), n), self.eps)))
            dot = mul(mul(reduce_sum(mul(mul(hj, wgt[j]), kj)), rstd), self.engram_scale)
            mag = sqrt(np.maximum(np.abs(dot), F(1e-6)).astype(F))
            gate = sigmoid(np.where(dot < 0, neg(mag), mag).astype(F))
            out.append(add(hj, mul(gate, value)))
        return to_bf16(np.stack(out))

    # -- attention ------------------------------------------------------------------------
    def indexer(self, L, x, qr, pos, state, trace):
        """Positions of the source's compressed KV this query attends to (ascending)."""
        r, src = self.ratio[L], self.kv_of[L]
        n = (pos + 1) // r
        if n == 0:
            return []
        q = linear_q(self.lw(L, "attn.indexer.wq_b.weight"), qr).reshape(self.ih, self.ihd)
        q = rope_tail(q, rope_cs(self.freqs_yarn, pos))
        q = np.stack([qdq_fp4_e8m0(q[h]) for h in range(self.ih)])
        wts = to_bf16(mul(linear_bf16(self.lw(L, "attn.indexer.weights_proj.weight"), x), self.index_w_scale))
        keys = np.stack(state["ik"][src][:n])                                     # [n, ihd]
        score = to_bf16(dots(q, keys))                                           # [ih, n] BF16 einsum
        terms = to_bf16(mul(np.maximum(score, F(0)), wts[:, None]))
        s = to_bf16(reduce_rows(terms.T))
        s = s.astype(np.float64)
        if L == self.cand_src:
            state["cand"] = self.candidate_blocks(s, n)
        elif 0 <= self.cand_src < L:
            s = np.where(state["cand"][:n], s, -np.inf)
        sel = sorted(int(i) for i in topk_lowest_index(s, min(self.topk, n)))
        if trace is not None:
            trace[f"L{L}.index_select"], trace[f"L{L}.index_scores"] = sel, s
        return sel

    def candidate_blocks(self, s, n):
        """Level one: score each block of candidate_block_size positions by its best
        position, pin the block holding the newest position, keep the top blocks."""
        b = self.cand_b
        nb = -(-n // b)
        padded = np.concatenate([s, np.full(nb * b - n, -np.inf)])
        bs = padded.reshape(nb, b).max(axis=1)
        bs[(n - 1) // b] = np.inf
        keep = np.zeros(nb, dtype=bool)
        for i in topk_lowest_index(bs, min(self.cand_k, nb)):
            keep[i] = bs[i] > -np.inf
        return np.repeat(keep, b)[:n]

    def vendor_blocks(self, pos, n_comp, width=64):
        """VALIDATION ONLY: the row groups in which the release's decode kernel streams
        one query's KV.  Its index list is the window ring oldest slot first (window
        entries, empty slots included) followed by the compressed selections; it walks
        the list in `width`-entry blocks with a running maximum, rescaling the partial
        sums by exp(m_old - m_new).  Returns, per block holding a valid entry, the
        indices into this model's row list (window rows oldest first, then selections)."""
        win = min(pos + 1, self.window)
        list_idx = np.concatenate([np.arange(win) + (self.window - win),     # window position -> ring list slot
                                   self.window + np.arange(n_comp)])
        out = []
        for b in range(0, self.window + n_comp, width):
            sel = np.nonzero((list_idx >= b) & (list_idx < b + width))[0]
            if len(sel):
                out.append(sel)
        return out

    def compressor(self, L, x, pos, state):
        """The KV source's compressed latent for the group ending at pos (pre-RoPE, BF16),
        or None while the group is filling."""
        r = self.ratio[L]
        if r == 1:
            return rmsnorm_bf16(linear_bf16(self.lw(L, "attn.compressor.wkv.weight"), x),
                                self.lw(L, "attn.compressor.norm.weight"), self.eps)
        kv = matvec_fp32(self.lw(L, "attn.compressor.wkv.weight"), x)       # FP32 weights, FP32 out
        sc = matvec_fp32(self.lw(L, "attn.compressor.wgate.weight"), x)
        slots = state["slots"][L]
        slots.append((kv, sc))
        if (pos + 1) % r:
            return None
        state["slots"][L] = []
        kvs, scs = np.stack([a for a, _ in slots]), np.stack([b for _, b in slots])   # [r, hd]
        m = np.max(scs, axis=0)
        e = exp(add(scs, neg(m)))
        p = div(e, seqsum(list(e))[None, :])
        pooled = seqsum([mul(kvs[i], p[i]) for i in range(r)])
        return rmsnorm_bf16(to_bf16(pooled), self.lw(L, "attn.compressor.norm.weight"), self.eps)

    def attention(self, L, x, pos, state, trace):
        yarn = self.ratio[L] > 0
        cs = rope_cs(self.freqs_yarn if yarn else self.freqs_plain, pos)
        qr = rmsnorm_bf16(linear_q(self.lw(L, "attn.wq_a.weight"), x), self.lw(L, "attn.q_norm.weight"), self.eps)
        q = rope_tail(linear_q(self.lw(L, "attn.wq_b.weight"), qr).reshape(self.heads, self.hd), cs)
        kv = rmsnorm_bf16(linear_q(self.lw(L, "attn.wkv.weight"), x), self.lw(L, "attn.kv_norm.weight"), self.eps)
        kv = qdq_fp8(rope_tail(kv, cs))
        state["win"][L].append(kv)
        rows = state["win"][L][-self.window:]                     # oldest first
        if yarn:
            src = self.kv_of[L]
            if L == src:
                latent = self.compressor(L, x, pos, state)
                if latent is not None:
                    r = self.ratio[L]
                    gcs = rope_cs(self.freqs_yarn, pos + 1 - r)    # a group sits at its first token
                    k = rmsnorm_bf16(linear_bf16(self.lw(L, "attn.indexer.wk.weight"), latent),
                                     self.lw(L, "attn.indexer.k_norm.weight"), self.eps)
                    state["ik"][L].append(qdq_fp4_e8m0(rope_tail(k, gcs)))
                    state["ckv"][L].append(qdq_fp4_e4m3(rope_tail(latent, gcs), 16))
            if L == self.idx_of[L]:
                state["sel"] = self.indexer(L, x, qr, pos, state, trace)
            rows = rows + [state["ckv"][src][i] for i in state["sel"]]
        kvm = np.stack(rows)                                      # [T, hd]: keys and values alike
        sink = self.lw(L, "attn.attn_sink")
        blocks = self.vendor_blocks(pos, len(rows) - len(state["win"][L][-self.window:])) \
            if self.vendor_decode_from is not None and pos >= self.vendor_decode_from else [np.arange(len(rows))]
        # every head at once; per head the order is: scores sequential over head_dim,
        # max, exp, P (as BF16) x V sequential over positions, reduce_sum of P
        s = mul(dots(q, kvm), self.attn_scale)                    # [heads, T]
        m = acc = den = None
        for blk in blocks:                                        # one block: the two-pass softmax
            sb = s[:, blk]
            mb = np.max(sb, axis=1) if m is None else np.maximum(m, np.max(sb, axis=1))
            e = exp(add(sb, neg(mb)[:, None]))
            pv = dots(to_bf16(e), kvm[blk].T)                     # probabilities enter the PV product as BF16
            es = reduce_rows(e)
            if m is None:
                den, acc = es, pv
            else:
                r = exp(add(m, neg(mb)))
                den, acc = add(mul(den, r), es), add(mul(acc, r[:, None]), pv)
            m = mb
        den = add(den, exp(add(sink, neg(m))))
        o = to_bf16(div(acc, den[:, None]))
        o = rope_tail(o, cs, inverse=True)
        og = o.reshape(self.groups, -1)
        wa = self.lw(L, "attn.wo_a.weight").reshape(self.groups, self.o_rank, -1)
        z = np.zeros((self.groups, self.o_rank), dtype=F)       # grouped wo_a: each group sequential over its K
        for d in range(og.shape[1]):
            z = add(z, mul(wa[:, :, d], og[:, d][:, None]))
        z = to_bf16(z.reshape(-1))
        return linear_q(self.lw(L, "attn.wo_b.weight"), z)

    # -- mixture of experts --------------------------------------------------------------
    def expert(self, prefix, x, weight=None):
        g = linear_q(self.w[prefix + "w1.weight"], x)
        u = linear_q(self.w[prefix + "w3.weight"], x)
        u = np.clip(u, -self.limit, self.limit).astype(F)
        g = np.minimum(g, self.limit).astype(F)
        a = mul(silu(g), u)
        if weight is not None:
            a = mul(weight, a)
        return linear_q(self.w[prefix + "w2.weight"], to_bf16(a))

    def moe(self, L, x, trace):
        scores = sqrt(softplus(matvec_fp32(self.lw(L, "ffn.gate.weight"), x)))
        chosen = topk_lowest_index(add(scores, self.lw(L, "ffn.gate.bias")), self.k_exp)
        ids = sorted(int(i) for i in chosen)                     # experts run and sum in id order
        total = seqsum([scores[i] for i in ids])
        den = add(total, F(1e-20))
        y = np.zeros(self.dim, dtype=F)
        for i in ids:
            wgt = mul(div(scores[i], den), self.route_scale)
            y = add(y, self.expert(f"layers.{L}.ffn.experts.{i}.", x, wgt))
        y = add(y, self.expert(f"layers.{L}.ffn.shared_experts.", x))
        if trace is not None:
            trace[f"L{L}.experts"], trace[f"L{L}.router"] = ids, add(scores, self.lw(L, "ffn.gate.bias"))
        return to_bf16(y)

    # -- one token --------------------------------------------------------------------------
    def decode_token(self, token, pos, state, trace=None, force=None):
        """One decode step at `pos`.  `force(L)`, if given, returns (h, pre_mix) to
        replace layer L's input (teacher forcing against a reference), or None."""
        state["tokens"].append(int(token))
        h = np.repeat(self.w["embed.weight"][token][None, :], self.hc, axis=0).astype(F)
        pre_mix = np.array([1, 0, 0, 0], dtype=F)[:self.hc]
        for L in range(self.L):
            if force is not None:
                forced = force(L)
                if forced is not None:
                    h, pre_mix = forced
            if L in self.engram.layer_ids:
                h = self.engram_layer(h, L, state)
                if trace is not None:
                    trace[f"L{L}.engram"] = h
            res = h
            a_pre, a_post, a_comb = self.hc_mixes(h, L, "attn")
            x = rmsnorm_bf16(self.hc_pre(h, pre_mix), self.lw(L, "attn_norm.weight"), self.eps)
            y = self.attention(L, x, pos, state, trace)
            h = self.hc_post(y, res, a_post, a_comb)
            if trace is not None:
                trace[f"L{L}.attn_norm"], trace[f"L{L}.attn"] = x, y
            res = h
            f_pre, f_post, f_comb = self.hc_mixes(h, L, "ffn")
            x = rmsnorm_bf16(self.hc_pre(h, a_pre), self.lw(L, "ffn_norm.weight"), self.eps)
            y = self.moe(L, x, trace)
            h = self.hc_post(y, res, f_post, f_comb)
            pre_mix = f_pre
            if trace is not None:
                trace[f"L{L}.ffn_norm"], trace[f"L{L}.ffn"], trace[f"block{L}"], trace[f"pre{L}"] = x, y, h, f_pre
        xf = rmsnorm_bf16(self.hc_pre(h, pre_mix), self.w["norm.weight"], self.eps)
        logits = matvec_fp32(self.w["head.weight"], xf)
        if trace is not None:
            trace["final_norm"], trace["logits"] = xf, logits
        return logits

    def generate(self, prompt, n):
        """Prefill one position at a time, then greedy decode.  Returns (tokens, logits)."""
        state = self.new_state()
        for p, t in enumerate(prompt[:-1]):
            self.decode_token(t, p, state)
        logits = self.decode_token(prompt[-1], len(prompt) - 1, state)
        out, rows = [], []
        for i in range(n):
            tok = int(np.argmax(logits))                   # lowest id on ties
            out.append(tok)
            rows.append(logits)
            if i + 1 < n:
                logits = self.decode_token(tok, len(prompt) + i, state)
        return out, rows


def margin(logits):
    top = np.argsort(-logits.astype(np.float64), kind="stable")[:2]
    return float(logits[top[0]] - logits[top[1]])


def prompt_and_expected():
    run = json.loads(ORACLE.read_text())["results"][WORKLOAD]
    return run["prompt_token_ids"], run["generated_token_ids"]


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tokens", type=int, default=4)
    ap.add_argument("--vendor-decode-order", action="store_true",
                    help="stream decode-step attention in the release kernel's blocks (validation only)")
    a = ap.parse_args()
    prompt, expected = prompt_and_expected()
    model = Model(vendor_decode_from=len(prompt) if a.vendor_decode_order else None)
    got, rows = model.generate(prompt, a.tokens)
    for i, (t, lg) in enumerate(zip(got, rows)):
        print(f"step {i}: golden {t} oracle {expected[i]} match {t == expected[i]} margin {margin(lg):.4f} "
              f"oracle-token logit gap {float(lg[t] - lg[expected[i]]):.4f}")


if __name__ == "__main__":
    main()
