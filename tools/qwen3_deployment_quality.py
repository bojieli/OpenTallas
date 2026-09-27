#!/usr/bin/env python3
"""Full-model quality of Qwen3-8B under the ROM reticle's deployment arithmetic.

Answers finding 4 of docs/ARCHITECTURE_ATLAS_FEASIBILITY_REVIEW_2026_09_27.md:
bit-exactness proves the RTL matches the adopted arithmetic contract, not that
the contract (plus the weight and KV formats) leaves model quality unchanged.
This tool runs the FULL Qwen3-8B (36 layers, 151,936 vocabulary) on a GPU with
each deployment deviation applied alone and all together, and measures quality.

Arithmetic modes (``--mode``; see MODES):

* ``gpu``       the vendor BF16 inference arithmetic (HF transformers Qwen3:
                BF16 GEMMs with FP32 accumulation and BF16 outputs, FP32
                RMSNorm, BF16 residual stream, SDPA attention in BF16).
* ``contract``  the decode core's golden arithmetic, emulated exactly on the
                GPU (tools/hdc_golden.py at 45762e32, the vector-core
                configuration HDC_SU_WIDTH>1 at the spec's 8,192 lane groups):
                FP32 residual stream and FP32 matrix outputs; every matrix
                input rounded to BF16; every weight dot product cut into the
                split_for() K-split -- S contiguous chunks, each summed
                sequentially from +0, chunk sums added by a pairwise tree; the
                attention products K-split INTERLEAVED (attn_splits: scores 128
                ways over head_dim, P.V 1,024 ways over positions); RMSNorm
                weights folded into the following projections (W' =
                bf16(W diag(w)), 1/rms applied after); every stream-unit sum
                (norms, softmax Z) R-ARITH chunk-8 + pairwise tree; rsqrt and
                reciprocal by bit seed + 3 Newton steps; exp by Cody-Waite +
                degree-6 Horner; one-pass softmax normalised after P.V with the
                unnormalised probabilities rounded to BF16; canonical +0.

Weight formats (``--weights``): ``bf16``; ``q35`` (3.5 bits/parameter: the
Taalas HC1 "3-bit base type mixed with 6-bit" point of
configs/hardware/technology.json#reference_parts.taalas_hc1, realised as
symmetric INT3 / INT6 groups of 128 along K with one BF16 scale each, the 1/8
of groups of each matrix with the largest INT3->INT6 error reduction at INT6:
3 + 3/8 + 16/128 = 3.5 bits); ``w4`` (INT4 g128, 4.125 bits) and ``w3``
(INT3 g128, 3.125 bits) bracket it.  The repository defines no exact 3.5-bit
quantiser (atlas: "Pending - Qwen3-8B weight and KV formats"), so ``q35`` is a
concrete, data-free (round-to-nearest with per-group MSE-optimal clipping)
realisation of the stated point, not the Taalas format.

KV formats (``--kv``): ``bf16``; ``fp8`` = golden to_fp8: per-element FP8 E4M3
(bias 7, max 448 saturating, subnormals, RNE), NO scale, applied to K after
q/k-norm and RoPE and to V.

Every contract-mode product is exact in FP32 (BF16 x BF16, E4M3 x BF16, or an
INT<=6 x BF16-scale x BF16 product of <= 21 significant bits), so the Triton
kernel's fused multiply-adds equal the golden's separate mul + add; the test
checks the contract forward bit-exactly against the numpy golden on the
reduced vehicle.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as Fn

ROOT = Path(__file__).resolve().parents[1]
F32 = torch.float32
BF16 = torch.bfloat16

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

# -- golden constants (tools/hdc_golden.py @ 8a91421a:36-45) ----------------------
LOG2E = 1.4426950408889634
LN2_HI = 0.693145751953125
LN2_LO = 1.428606765330187e-06
MAGIC = 12582912.0
EXP_POLY = [1.0 / 720, 1.0 / 120, 1.0 / 24, 1.0 / 6, 0.5, 1.0, 1.0]
EXP_MAX, EXP_MIN = 88.0, -87.0
CHUNK = 8
W_LANES, INTERLEAVE = 16, 8
SPEC_GROUPS = 8192           # tools/arch_budget_qwen3.py GROUPS_ROM


def f32c(v):
    """A Python float rounded to FP32 (np.float32(v)), as a Python float."""
    return float(np.float32(v))


# -- the K-split rules (tools/hdc_golden.py @ 8a91421a:121-150) ---------------------
def split_for(n, k, groups, lanes=W_LANES, interleave=INTERLEAVE):
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


def attn_splits(hd, groups, lanes=W_LANES):
    return min(hd, p2floor(groups)), p2floor(max(1, groups // max(1, hd // lanes)))


# -- the chunk + pairwise-tree dot product kernel ----------------------------------
try:
    import triton
    import triton.language as tl

    @triton.jit(do_not_specialize=["S"])
    def _chunk_tree_kernel(XT, WT, SC, OUT, STK, T, N, S, NTT, NNP,
                           sxb, sxk, swb, swk, ssk, sob, sot, son, sop,
                           M: tl.constexpr, LV: tl.constexpr, BT: tl.constexpr, BN: tl.constexpr,
                           QUANT: tl.constexpr, G: tl.constexpr):
        """OUT[b, t, n] = sum over k of XT[b, k, t] * WT[b, k, n] in the golden order:
        S contiguous chunks of M products, each summed sequentially from +0; each
        finished chunk sum enters a binary-counter stack (per program, in global
        scratch STK) that adds equal-size neighbours left + right, which is exactly
        the pairwise tree ((c0+c1)+(c2+c3))+... over the S chunk sums.  Grid axis 2
        cuts the S chunks into contiguous power-of-two parts, each program the
        subtree of its part (OUT[..., part]); the caller adds the parts by the same
        pairwise tree, so the order is unchanged."""
        pid0 = tl.program_id(0)
        pid_b = pid0 // NTT
        pid_t = pid0 % NTT
        pid_n = tl.program_id(1)
        part = tl.program_id(2)
        XT += pid_b * sxb
        WT += pid_b * swb
        OUT += pid_b * sob + part * sop
        offs_t = pid_t * BT + tl.arange(0, BT)
        offs_n = pid_n * BN + tl.arange(0, BN)
        mt = offs_t < T
        mn = offs_n < N
        prog = ((part * tl.num_programs(0) + pid0) * NNP + pid_n).to(tl.int64)
        stk = STK + prog * (LV * BT * BN) + tl.arange(0, BT)[:, None] * BN + tl.arange(0, BN)[None, :]
        for c in range(S):
            acc = tl.zeros([BT, BN], dtype=tl.float32)
            for j in range(M):
                k = (part * S + c) * M + j
                xk = tl.load(XT + k * sxk + offs_t, mask=mt, other=0.0).to(tl.float32)
                wk = tl.load(WT + k * swk + offs_n, mask=mn, other=0).to(tl.float32)
                if QUANT:
                    wk = wk * tl.load(SC + (k // G) * ssk + offs_n, mask=mn, other=0.0).to(tl.float32)
                acc += xk[:, None] * wk[None, :]          # exact product: the FMA rounds once, as mul+add
            cc = c
            lvl = 0
            while (cc & 1) == 1:
                acc = tl.load(stk + lvl * (BT * BN)) + acc
                cc = cc >> 1
                lvl += 1
            tl.store(stk + lvl * (BT * BN), acc)
        res = tl.load(stk + (LV - 1) * (BT * BN))
        tl.store(OUT + offs_t[:, None] * sot + offs_n[None, :] * son, res, mask=mt[:, None] & mn[None, :])

    HAVE_TRITON = True
except Exception:  # pragma: no cover
    HAVE_TRITON = False


def _tree_last(v):
    """Pairwise tree ((v0+v1)+(v2+v3))+... over the last axis (a power of two)."""
    while v.shape[-1] > 1:
        v = v[..., 0::2] + v[..., 1::2]
    return v[..., 0]


def chunk_tree_dot_t(xT, wT, S, scaleT=None, group=128, budget=1 << 26, BT=32, BN=64):
    """y[b, t, n] = sum_k xT[b, k, t] wT[b, k, n] in the golden matvec order: K cut
    into S contiguous chunks of K/S, each sequential from +0, chunk sums a pairwise
    tree.  K-major operands: xT [B, K, T] FP32 (values the golden has already
    rounded), wT [B, K, N] BF16/FP32, or INT8 codes with scaleT [K/group, N]
    (w = code * scale, exact in FP32)."""
    Bt, K, T = xT.shape
    N = wT.shape[2]
    assert K % S == 0 and S & (S - 1) == 0
    M = K // S
    if T < BT:
        BT = 16
        BN = 32
    nnp = triton.cdiv(N, BN)
    parts = 1
    while parts < S and Bt * triton.cdiv(T, BT) * nnp * parts < 2048:
        parts *= 2
    SP = S // parts
    LV = int(math.log2(SP)) + 1
    rows = max(BT, (budget // max(1, Bt * N * (LV + parts))) // BT * BT)
    out = torch.empty((Bt, T, N), device=xT.device, dtype=F32)
    for t0 in range(0, T, rows):
        xt = xT[:, :, t0:t0 + rows]
        tt = xt.shape[2]
        ntt = triton.cdiv(tt, BT)
        stk = torch.empty(parts * Bt * ntt * nnp * LV * BT * BN, device=xT.device, dtype=F32)
        o = torch.empty((Bt, tt, N, parts), device=xT.device, dtype=F32)
        _chunk_tree_kernel[(Bt * ntt, nnp, parts)](
            xt, wT, scaleT if scaleT is not None else wT, o, stk, tt, N, SP, ntt, nnp,
            xt.stride(0), xt.stride(1), wT.stride(0), wT.stride(1),
            scaleT.stride(0) if scaleT is not None else 0, o.stride(0), o.stride(1), o.stride(2), o.stride(3),
            M=M, LV=LV, BT=BT, BN=BN, QUANT=scaleT is not None, G=group, num_warps=4)
        out[:, t0:t0 + tt] = _tree_last(o)
    return out


def chunk_tree_dot(x, w, S, scale=None, group=128):
    """Row-major convenience form: x [T, K] or [B, T, K]; w [N, K] or [B, N, K];
    scale [N, K/group].  Same order as chunk_tree_dot_t."""
    batched = x.dim() == 3
    if not batched:
        x, w = x[None], w[None]
    if not HAVE_TRITON or not x.is_cuda:
        y = torch.stack([_chunk_tree_dot_ref(x[b], w[b], S, scale, group) for b in range(x.shape[0])])
    else:
        y = chunk_tree_dot_t(x.transpose(1, 2).contiguous(), w.transpose(1, 2).contiguous(), S,
                             scale.t().contiguous() if scale is not None else None, group)
    return y if batched else y[0]


def _chunk_tree_dot_ref(x, w, S, scale=None, group=128):
    """Slow reference of chunk_tree_dot (plain torch elementwise; no fusion)."""
    wf = w.to(F32)
    if scale is not None:
        wf = wf * scale.to(F32).repeat_interleave(group, dim=1)
    T, K = x.shape
    M = K // S
    acc = torch.zeros((T, w.shape[0], S), device=x.device, dtype=F32)
    for j in range(M):
        acc = acc + x[:, None, j::M] * wf[None, :, j::M]
    return _tree_last(acc)


def interleave_perm(K, S, device):
    """Index order that turns an interleaved S-way K-split (chunk c = c, c+S, ...)
    into contiguous chunks of ceil(K/S), padding with -1 (zero) slots."""
    M = -(-K // S)
    idx = torch.arange(M * S, device=device).view(M, S).t().reshape(-1)   # c*M+j -> c + j*S
    return idx, M


def gather_pad(t, idx, K, dim):
    """t indexed along `dim` by idx, entries >= K zero."""
    pad = int(idx.max().item()) + 1 - K if idx.numel() else 0
    if pad > 0:
        shape = list(t.shape)
        shape[dim] = pad
        t = torch.cat([t, torch.zeros(shape, device=t.device, dtype=t.dtype)], dim)
    return t.index_select(dim, idx)


# -- golden elementwise primitives (eager torch: separate IEEE FP32 mul and add) ----
def z(x):
    """Canonical +0: under RNE, x + (+0) is x for every x except -0, which becomes +0."""
    return x + 0.0


def add(a, b):
    return (a + b) + 0.0


def mul(a, b):
    return (a * b) + 0.0


def to_bf16(x):
    return x.to(BF16).to(F32)


def to_fp8(x):
    """Golden to_fp8 (8a91421a:257-267): E4M3, RNE, saturating at 448, canonical +0."""
    return z(x.clamp(-448.0, 448.0).to(torch.float8_e4m3fn).to(F32))


def _bits(x):
    return x.contiguous().view(torch.int32)


def _from_bits(b):
    return b.contiguous().view(F32)


def rsqrt_g(v):
    y = _from_bits(0x5F3759DF - (_bits(v) >> 1))
    half = mul(v, 0.5)
    for _ in range(3):
        y = mul(y, add(1.5, -mul(half, mul(y, y))))
    return y


# RECIP_SAT, the implemented contract's reciprocal saturation (tools/hdc_golden.py
# @ 45762e32 reciprocal(); rtl/hdc/ot_hdc_sfu.sv, ot_hdc_sfu_q.sv): for finite
# positive d with bits(d) > 0x7EF311C7 (d > 1.6158e38) the bit seed would wrap, so
# the seed is +0 and the Newton steps return +0.  This is an explicit saturation
# contract (+0), not IEEE rounding; the true reciprocal is subnormal.
# silu(g) reaches it for every gate g <= -87.98 (exp(-g) clamps at exp(88)); full
# Qwen3-8B produces such gates on ordinary text.  Before 45762e32 the golden and
# RTL returned NaN there.  RECIP_SAT_HITS counts the saturated elements.
RECIP_SAT = True
RECIP_SAT_HITS = [0]


def reciprocal_g(d):
    db = _bits(d)
    over = (db > 0x7EF311C7) & (db < 0x7F800000)          # finite positive, above the seed's range
    if RECIP_SAT:
        RECIP_SAT_HITS[0] = RECIP_SAT_HITS[0] + over.sum()
        seed = torch.where(over, torch.zeros_like(db), 0x7EF311C7 - db)
    else:
        seed = 0x7EF311C7 - db
    y = _from_bits(seed)
    for _ in range(3):
        y = mul(y, add(2.0, -mul(d, y)))
    return y


def exp_g(x):
    x = x.clamp(EXP_MIN, EXP_MAX)
    t = mul(x, f32c(LOG2E))
    u = add(t, MAGIC)
    n = add(u, -MAGIC)
    r = add(add(x, -mul(n, f32c(LN2_HI))),
            -mul(n, f32c(LN2_LO)))
    p = torch.full_like(r, f32c(EXP_POLY[0]))
    for c in EXP_POLY[1:]:
        p = add(mul(p, r), f32c(c))
    e = _bits(p) + (n.to(torch.int32) << 23)
    return _from_bits(e)


def reduce_chunked(v, c=CHUNK):
    """R-ARITH (8a91421a:194-213) over the last axis: contiguous chunks of c,
    each sequential from +0, chunk sums a pairwise tree padded with +0."""
    L = v.shape[-1]
    nch = max(1, -(-L // c))
    if nch * c != L:
        v = torch.cat([v, torch.zeros(*v.shape[:-1], nch * c - L, device=v.device, dtype=v.dtype)], -1)
    v = v.reshape(*v.shape[:-1], nch, c)
    acc = torch.zeros(v.shape[:-1], device=v.device, dtype=F32)
    for j in range(c):
        acc = add(acc, v[..., j])
    n = 1
    while n < nch:
        n *= 2
    if n != nch:
        acc = torch.cat([acc, torch.zeros(*acc.shape[:-1], n - nch, device=v.device, dtype=F32)], -1)
    while acc.shape[-1] > 1:
        acc = add(acc[..., 0::2], acc[..., 1::2])
    return acc[..., 0]


def rstd_g(x, eps):
    d = x.shape[-1]
    s = reduce_chunked(mul(x, x))
    return rsqrt_g(add(mul(s, f32c(1.0 / d)), f32c(eps)))


def rmsnorm_g(x, w, eps):
    return mul(mul(x, rstd_g(x, eps)[..., None]), w)


def rope_tables_g(positions, hd, theta, device):
    """cos/sin per position (8a91421a:304-310): angle = fp32(pos) * fp32(inv) in FP32,
    cos/sin in float64, rounded once."""
    inv = (1.0 / (theta ** (np.arange(0, hd, 2, dtype=np.float64) / hd))).astype(np.float32)
    ang = (np.asarray(positions, dtype=np.float32)[:, None] * inv[None, :]).astype(np.float32)
    c = np.cos(ang.astype(np.float64)).astype(np.float32)
    s = np.sin(ang.astype(np.float64)).astype(np.float32)
    return torch.from_numpy(c).to(device), torch.from_numpy(s).to(device)


def rope_g(v, cos, sin):
    """v [..., T, hd]; cos/sin [T, hd/2]."""
    h = v.shape[-1] // 2
    a, b = v[..., :h], v[..., h:]
    return torch.cat([add(mul(a, cos), mul(b, -sin)), add(mul(b, cos), mul(a, sin))], -1)


def silu_g(g):
    return mul(g, reciprocal_g(add(exp_g(mul(g, -1.0)),
                                   1.0)))


# -- weight quantisation ---------------------------------------------------------
QFORMATS = {
    # name: (low bits, high bits, fraction of groups at high bits, group)
    "q35": (3, 6, 0.125, 128),
    "w4": (4, 4, 0.0, 128),
    "w3": (3, 3, 0.0, 128),
}


def _rtn_mse(wg, bits, grid=np.linspace(0.5, 1.0, 21)):
    """Symmetric INT`bits` (codes -2^(b-1) .. 2^(b-1)-1) per group, scale BF16,
    clip ratio chosen per group to minimise the group's squared error."""
    qmax = 2 ** (bits - 1) - 1
    qmin = -(2 ** (bits - 1))
    amax = wg.abs().amax(-1, keepdim=True).clamp_min(1e-30)
    best_err = None
    best_s = None
    for r in grid:
        s = to_bf16(amax * float(r) / qmax).clamp_min(1e-30)
        q = torch.clamp(torch.round(wg / s), qmin, qmax)
        err = ((q * s - wg) ** 2).sum(-1, keepdim=True)
        if best_err is None:
            best_err, best_s = err, s
        else:
            better = err < best_err
            best_err = torch.where(better, err, best_err)
            best_s = torch.where(better, s, best_s)
    q = torch.clamp(torch.round(wg / best_s), qmin, qmax)
    return q, best_s, best_err[..., 0]


def quantize(w, fmt):
    """w [N, K] -> (codes int8 [N, K], scales BF16 [N, K/g], bits/param).  Mixed
    formats take two passes: the per-group INT_lo -> INT_hi error reductions of the
    whole matrix fix the threshold, then each group is coded at its width."""
    lo, hi, frac, g = QFORMATS[fmt]
    N, K = w.shape
    assert K % g == 0
    codes = torch.empty((N, K), dtype=torch.int8, device=w.device)
    scales = torch.empty((N, K // g), dtype=BF16, device=w.device)
    rows = max(1, (1 << 24) // K)
    thr = None
    if frac > 0:
        gains = []
        for r0 in range(0, N, rows):
            wg = w[r0:r0 + rows].to(F32).reshape(-1, K // g, g)
            gains.append(_rtn_mse(wg, lo)[2] - _rtn_mse(wg, hi)[2])
        gain = torch.cat(gains, 0)
        nhi = int(round(frac * gain.numel()))
        thr = torch.topk(gain.reshape(-1), nhi).values[-1] if nhi else None
        del gains, gain
    n_hi = 0
    for r0 in range(0, N, rows):
        wg = w[r0:r0 + rows].to(F32).reshape(-1, K // g, g)
        q, s, e = _rtn_mse(wg, lo)
        if thr is not None:
            q_hi, s_hi, e_hi = _rtn_mse(wg, hi)
            u = ((e - e_hi) >= thr)[..., None]
            n_hi += int(u.sum().item())
            q = torch.where(u, q_hi, q)
            s = torch.where(u, s_hi, s)
        codes[r0:r0 + rows] = q.reshape(-1, K).to(torch.int8)
        scales[r0:r0 + rows] = s[..., 0].to(BF16)
    f_hi = n_hi / (N * K // g)
    bits = lo + (hi - lo) * f_hi + 16.0 / g
    return codes, scales, bits


def dequant(codes, scales, g=128):
    return codes.to(F32) * scales.to(F32).repeat_interleave(g, dim=1)


# -- the model --------------------------------------------------------------------
MODES = {
    # name: (arith, weights, kv)
    "a_bf16": ("gpu", "bf16", "bf16"),
    "b_wq35": ("gpu", "q35", "bf16"),
    "b_w4": ("gpu", "w4", "bf16"),
    "b_w3": ("gpu", "w3", "bf16"),
    "c_kvfp8": ("gpu", "bf16", "fp8"),
    "d_contract": ("contract", "bf16", "bf16"),
    "e_full": ("contract", "q35", "fp8"),
    "f_contract_kvfp8": ("contract", "bf16", "fp8"),      # everything but the weight format
    "e_full_w4": ("contract", "w4", "fp8"),
}


def find_snapshot(name="Qwen--Qwen3-8B"):
    base = Path.home() / ".cache/huggingface/hub" / f"models--{name}" / "snapshots"
    snaps = sorted(base.glob("*/config.json"))
    if not snaps:
        raise FileNotFoundError(base)
    return snaps[0].parent


def load_state(path, device):
    from safetensors import safe_open
    path = Path(path)
    files = sorted(path.glob("*.safetensors"))
    sd = {}
    for f in files:
        with safe_open(str(f), framework="pt", device=str(device)) as h:
            for k in h.keys():
                sd[k] = h.get_tensor(k).to(BF16)
    return sd


class Qwen3:
    def __init__(self, path, arith, weights, kv, groups=SPEC_GROUPS, device="cuda", wfile=None):
        self.cfg = json.loads((Path(path) / "config.json").read_text())
        c = self.cfg
        self.L, self.H = c["num_hidden_layers"], c["hidden_size"]
        self.NH, self.KV, self.HD = c["num_attention_heads"], c["num_key_value_heads"], c["head_dim"]
        self.FF, self.V = c["intermediate_size"], c["vocab_size"]
        self.eps, self.theta = c["rms_norm_eps"], c["rope_theta"]
        self.arith, self.wfmt, self.kvfmt = arith, weights, kv
        self.groups = groups
        self.prefill_chunk = 512
        self.device = torch.device(device)
        self.bits = {}
        self.wfile = None
        if wfile is not None:
            self.wfile = wfile if isinstance(wfile, dict) else torch.load(wfile, map_location="cpu")
            assert self.wfile["fold"] == (arith == "contract"), "GPTQ file was built for the other norm placement"
            self.wfmt = self.wfile["fmt"]
        sd = load_state(path, self.device)
        self.embed = sd.pop("model.embed_tokens.weight").cpu()      # gathered on the host: 1.2 GB less GPU
        self.norm = sd.pop("model.norm.weight")
        lm = sd.pop("lm_head.weight")
        self.layers = []
        for i in range(self.L):
            p = f"model.layers.{i}."
            g = lambda n: sd.pop(p + n)
            ln1, ln2 = g("input_layernorm.weight"), g("post_attention_layernorm.weight")
            qw, kw, vw = g("self_attn.q_proj.weight"), g("self_attn.k_proj.weight"), g("self_attn.v_proj.weight")
            ow = g("self_attn.o_proj.weight")
            gw, uw, dw = g("mlp.gate_proj.weight"), g("mlp.up_proj.weight"), g("mlp.down_proj.weight")
            lay = dict(qn=g("self_attn.q_norm.weight").to(F32), kn=g("self_attn.k_norm.weight").to(F32))
            if arith == "contract":
                # NORM FOLD (8a91421a:282-296): W' = bf16(W diag(w)) for q,k,v and gate,up
                fold = lambda m, w: (m.to(F32) * w.to(F32)[None, :]).to(BF16)
                qkv = torch.cat([fold(qw, ln1), fold(kw, ln1), fold(vw, ln1)], 0)
                gu = torch.cat([fold(gw, ln2), fold(uw, ln2)], 0)
            else:
                lay["ln1"], lay["ln2"] = ln1, ln2
                qkv = torch.cat([qw, kw, vw], 0)
                gu = torch.cat([gw, uw], 0)
            del qw, kw, vw, gw, uw
            lay["qkv"] = self._w(qkv, "qkv", f"{i}.qkv")
            lay["o"] = self._w(ow, "o", f"{i}.o")
            lay["gu"] = self._w(gu, "gate_up", f"{i}.gu")
            lay["down"] = self._w(dw, "down", f"{i}.down")
            self.layers.append(lay)
        self.lm = self._w(lm, "lm_head", "lm_head")
        self.wfile = None
        del sd
        torch.cuda.empty_cache()
        inv = 1.0 / (self.theta ** (torch.arange(0, self.HD, 2, dtype=torch.int64).to(F32) / self.HD))
        self.inv_freq = inv.to(self.device)

    def _w(self, m, name, key):
        """Weights as the mode consumes them: row-major [N, K] for the GPU linear;
        K-major [K, N] (codes and [K/g, N] scales) for the contract kernel."""
        N = m.shape[0]
        if self.wfile is not None:
            codes, scales, bits = self.wfile["w"][key]
            self.bits.setdefault(name, []).append(bits)
            W = {"q": codes.to(self.device), "s": scales.to(self.device), "N": N}
        elif self.wfmt == "bf16":
            W = {"w": m.contiguous(), "N": N}
        else:
            codes, scales, bits = quantize(m, self.wfmt)
            self.bits.setdefault(name, []).append(bits)
            W = {"q": codes, "s": scales, "N": N}
        if self.arith == "contract":
            W = {k: (v.t().contiguous() if torch.is_tensor(v) else v) for k, v in W.items()}
        return W

    # -- matrix products --------------------------------------------------------
    def mv(self, x, W):
        """Contract matvec: x [T, K] FP32 -> [T, N] FP32 (golden mv: BF16 input, split_for order)."""
        wT = W.get("w", W.get("q"))
        K, N = wT.shape
        S = split_for(N, K, self.groups)
        return chunk_tree_dot_t(to_bf16(x).t().contiguous()[None], wT[None], S, W.get("s"))[0]

    def lin(self, x, W):
        """GPU linear: BF16 x [T, K] -> BF16 [T, N] (FP32 accumulation)."""
        if "w" in W:
            return Fn.linear(x, W["w"])
        out = []
        rows = max(1, (1 << 26) // W["q"].shape[1])
        for r0 in range(0, W["q"].shape[0], rows):
            wd = dequant(W["q"][r0:r0 + rows], W["s"][r0:r0 + rows])
            out.append(Fn.linear(x.to(F32), wd).to(BF16))
        return torch.cat(out, -1)

    def kv_round(self, t):
        if self.kvfmt == "fp8":
            return to_fp8(t.to(F32)).to(t.dtype)
        return t.to(BF16).to(t.dtype) if self.arith == "contract" else t

    # -- forward -------------------------------------------------------------------
    def new_cache(self, B=1, cap=8192):
        """Per-sequence KV cache: layer -> (K, V) [B, KV, cap, HD], valid up to lens[b]."""
        dt = BF16      # every cached K/V value is BF16- (or E4M3-) exact: storage is lossless
        return {"lens": [0] * B, "kv": [(torch.zeros((B, self.KV, cap, self.HD), device=self.device, dtype=dt),
                                        torch.zeros((B, self.KV, cap, self.HD), device=self.device, dtype=dt))
                                       for _ in range(self.L)]}

    @torch.no_grad()
    def forward(self, tokens, cache):
        """tokens [T] (one sequence) or [B, T]: each sequence's next T tokens at its
        positions lens[b].., appended to the cache.  Returns the final hidden states
        after the final norm, [T, H] or [B, T, H] (FP32 contract / BF16 gpu)."""
        single = tokens.dim() == 1
        if single:
            tokens = tokens[None]
        if self.arith == "contract":
            # Prefill in blocks on the growing cache: exact, because every contract
            # position is the golden's own decode step.
            hs = [self._forward_contract(tokens[:, i:i + self.prefill_chunk], cache)
                  for i in range(0, tokens.shape[1], self.prefill_chunk)]
            h = torch.cat(hs, 1)
        else:
            h = self._forward_gpu(tokens, cache)
        return h[0] if single else h

    def logits(self, h):
        if self.arith == "contract":
            return self.mv(h, self.lm)
        return self.lin(h, self.lm).to(F32)

    def _append(self, cache, i, k, v, T):
        """k, v [B, KV, T, HD] into layer i at lens[b].. ; returns the valid prefix views."""
        K, V = cache["kv"][i]
        lens = cache["lens"]
        B = len(lens)
        if all(l == lens[0] for l in lens):
            K[:, :, lens[0]:lens[0] + T] = k
            V[:, :, lens[0]:lens[0] + T] = v
        else:
            bi = torch.arange(B, device=self.device)[:, None].expand(B, T)
            pi = (torch.tensor(lens, device=self.device)[:, None] + torch.arange(T, device=self.device)[None, :])
            K[bi, :, pi] = k.transpose(1, 2).to(K.dtype)
            V[bi, :, pi] = v.transpose(1, 2).to(V.dtype)
        P = max(lens) + T
        return K[:, :, :P], V[:, :, :P], P

    def _qpos(self, cache, T):
        return (torch.tensor(cache["lens"], device=self.device)[:, None]
                + torch.arange(T, device=self.device)[None, :])            # [B, T]

    # GPU BF16 (HF transformers Qwen3 arithmetic)
    def _rms_hf(self, x, w):
        xf = x.to(F32)
        var = xf.pow(2).mean(-1, keepdim=True)
        xf = xf * torch.rsqrt(var + self.eps)
        return w * xf.to(BF16)

    def _forward_gpu(self, tokens, cache):
        B, T = tokens.shape
        x = self.embed[tokens.cpu()].to(self.device)                        # [B, T, H]
        qpos = self._qpos(cache, T)
        fr = qpos.to(F32)[..., None] * self.inv_freq
        emb = torch.cat([fr, fr], -1)[:, None]                              # [B, 1, T, HD]
        cos, sin = emb.cos().to(BF16), emb.sin().to(BF16)
        rot = lambda t: torch.cat([-t[..., self.HD // 2:], t[..., :self.HD // 2]], -1)
        fresh = B == 1 and cache["lens"][0] == 0
        for i, lay in enumerate(self.layers):
            h = self._rms_hf(x, lay["ln1"])
            qkv = self.lin(h, lay["qkv"])
            q, k, v = qkv.split([self.NH * self.HD, self.KV * self.HD, self.KV * self.HD], -1)
            q = self._rms_hf(q.view(B, T, self.NH, self.HD), lay["qn"].to(BF16)).transpose(1, 2)
            k = self._rms_hf(k.view(B, T, self.KV, self.HD), lay["kn"].to(BF16)).transpose(1, 2)
            v = v.view(B, T, self.KV, self.HD).transpose(1, 2)
            q = q * cos + rot(q) * sin
            k = k * cos + rot(k) * sin
            k, v = self.kv_round(k), self.kv_round(v)
            Kc, Vc, P = self._append(cache, i, k, v, T)
            if fresh:
                a = Fn.scaled_dot_product_attention(q, Kc, Vc, is_causal=True, enable_gqa=True)
            else:
                mask = (torch.arange(P, device=self.device)[None, None, :] <= qpos[:, :, None])[:, None]
                a = Fn.scaled_dot_product_attention(q, Kc, Vc, attn_mask=mask, enable_gqa=True)
            a = a.transpose(1, 2).reshape(B, T, self.NH * self.HD)
            x = x + self.lin(a, lay["o"])
            h = self._rms_hf(x, lay["ln2"])
            gu = self.lin(h, lay["gu"])
            gt, up = gu.split([self.FF, self.FF], -1)
            x = x + self.lin(Fn.silu(gt) * up, lay["down"])
        cache["lens"] = [l + T for l in cache["lens"]]
        return self._rms_hf(x, self.norm)

    # Contract arithmetic (tools/hdc_golden.py @ 45762e32, Model.decode_token, NORM_FOLD)
    def _forward_contract(self, tokens, cache):
        B, T = tokens.shape
        dev = self.device
        x = self.embed[tokens.cpu()].to(self.device).to(F32).reshape(B * T, self.H)
        qpos = self._qpos(cache, T)
        cos, sin = rope_tables_g(qpos.cpu().numpy().reshape(-1), self.HD, self.theta, dev)
        cos, sin = cos.view(B, 1, T, -1), sin.view(B, 1, T, -1)
        s_sc, s_pv = attn_splits(self.HD, self.groups)
        scale = torch.tensor(f32c(1.0 / np.sqrt(self.HD)), device=dev)
        grp = self.NH // self.KV
        for i, lay in enumerate(self.layers):
            r = rstd_g(x, self.eps)[:, None]
            qkv = mul(self.mv(x, lay["qkv"]), r)
            q, k, v = qkv.split([self.NH * self.HD, self.KV * self.HD, self.KV * self.HD], -1)
            q = rmsnorm_g(q.reshape(B, T, self.NH, self.HD), lay["qn"], self.eps).transpose(1, 2)   # [B, NH, T, HD]
            k = rmsnorm_g(k.reshape(B, T, self.KV, self.HD), lay["kn"], self.eps).transpose(1, 2)
            q = rope_g(q, cos, sin)
            k = self.kv_round(rope_g(k, cos, sin))
            v = self.kv_round(v.reshape(B, T, self.KV, self.HD).transpose(1, 2))
            Kc, Vc, P = self._append(cache, i, k, v, T)
            qb = to_bf16(q).reshape(B * self.KV, grp, T, self.HD)
            attn = self._attend(qb, Kc.reshape(B * self.KV, -1, self.HD), Vc.reshape(B * self.KV, -1, self.HD),
                                P, T, qpos.repeat_interleave(self.KV, 0), s_sc, s_pv, scale)   # [B*KV, grp, T, HD]
            attn = attn.reshape(B, self.NH, T, self.HD).transpose(1, 2).reshape(B * T, -1)
            x = add(x, self.mv(attn, lay["o"]))
            r = rstd_g(x, self.eps)[:, None]
            gu = mul(self.mv(x, lay["gu"]), r)
            gt, up = gu.split([self.FF, self.FF], -1)
            x = add(x, self.mv(mul(silu_g(gt), up), lay["down"]))
        cache["lens"] = [l + T for l in cache["lens"]]
        return rmsnorm_g(x, self.norm.to(F32), self.eps).view(B, T, self.H)

    def _attend(self, q, K, V, P, T, qpos, s_sc, s_pv, scale, budget=1 << 25):
        """q [Bt, grp, T, HD] (BF16-rounded) query heads by (sequence, KV head); K, V
        [Bt, P, HD] (zero past each sequence's end); qpos [Bt, T] the query positions.
        Scores: head_dim interleaved s_sc ways; P.V: positions interleaved s_pv ways
        (8a91421a:140-172, 323-331); one-pass softmax normalised after P.V.  Zero
        probabilities past a sequence's end only append +0 terms, so padding is exact.
        Query rows are processed in blocks (rows are independent, so blocking is exact)."""
        dev = q.device
        Bt, G = q.shape[0], q.shape[1]
        idx_d, Md = interleave_perm(self.HD, s_sc, dev)
        KpT = gather_pad(K, idx_d, self.HD, 2).transpose(1, 2).contiguous()   # [Bt, Md*s_sc, P]
        idx_p, Mp = interleave_perm(P, s_pv, dev)
        Vp = gather_pad(V, idx_p, P, 1).contiguous()                        # [Bt, Mp*s_pv, HD]
        out = torch.empty((Bt, G, T, self.HD), device=dev, dtype=F32)
        rows = max(1, budget // max(P, 1) // (G * Bt))
        ar = torch.arange(P, device=dev)
        for t0 in range(0, T, rows):
            t1 = min(T, t0 + rows)
            tt = t1 - t0
            qq = gather_pad(q[:, :, t0:t1].reshape(Bt, G * tt, self.HD), idx_d, self.HD, 2)
            sc = mul(chunk_tree_dot_t(qq.transpose(1, 2).contiguous(), KpT, s_sc), scale).view(Bt, G, tt, P)
            valid = (ar[None, None, :] <= qpos[:, t0:t1, None])[:, None]      # [Bt, 1, tt, P]
            mx = torch.where(valid, sc, -float("inf")).amax(-1, keepdim=True)
            e = exp_g(add(sc, -mx))
            del sc
            e = torch.where(valid, e, 0.0)
            Z = reduce_chunked(e)                                  # [Bt, G, tt]
            epT = gather_pad(to_bf16(e).reshape(Bt, G * tt, P).transpose(1, 2), idx_p, P, 1).contiguous()
            del e
            pv = chunk_tree_dot_t(epT, Vp, s_pv).view(Bt, G, tt, self.HD)
            out[:, :, t0:t1] = mul(pv, reciprocal_g(Z)[..., None])
            del epT, pv, valid
        return out


# -- evaluations --------------------------------------------------------------------
def head_stats(model, h, targets, chunk=512):
    """Per-position NLL of targets, argmax, and top-1/top-2 margin of the logits."""
    nll, arg, margin = [], [], []
    for r0 in range(0, h.shape[0], chunk):
        lg = model.logits(h[r0:r0 + chunk]).to(F32)
        lp = torch.log_softmax(lg.double(), -1)
        if targets is not None:
            tg = targets[r0:r0 + chunk]
            nll.append(-lp[torch.arange(len(tg), device=lg.device), tg].float())
        top = lg.topk(2, -1)
        arg.append(top.indices[:, 0])
        margin.append((top.values[:, 0] - top.values[:, 1]))
    out = {"arg": torch.cat(arg).cpu(), "margin": torch.cat(margin).cpu()}
    if targets is not None:
        out["nll"] = torch.cat(nll).cpu()
    return out


def wikitext_ids(tok):
    from datasets import load_dataset
    d = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split="test")
    return tok("\n\n".join(d["text"]), return_tensors="pt").input_ids[0]


def run_ppl(model, ids, ctx, max_windows, out):
    n = min(max_windows, ids.numel() // ctx)
    recs = []
    for w in range(n):
        seg = ids[w * ctx:(w + 1) * ctx].to(model.device)
        t0 = time.time()
        cache = model.new_cache(1, ctx)
        h = model.forward(seg, cache)
        del cache
        st = head_stats(model, h, seg[1:], chunk=256)
        # the last position has no target: drop its row
        recs.append({"nll": st["nll"].numpy().tolist(), "arg": st["arg"][:-1].numpy().tolist(),
                     "margin": st["margin"][:-1].numpy().tolist()})
        print(f"  ppl ctx={ctx} window {w + 1}/{n}: mean nll {np.mean(recs[-1]['nll']):.4f} "
              f"({time.time() - t0:.1f}s)", flush=True)
        torch.cuda.empty_cache()
    out[f"ppl_{ctx}"] = recs


def mtbench_prompts(tok, n):
    from datasets import load_dataset
    d = load_dataset("HuggingFaceH4/mt_bench_prompts", split="train")
    res = []
    for row in list(d)[:n]:
        msg = [{"role": "user", "content": row["prompt"][0]}]
        s = tok.apply_chat_template(msg, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        res.append(tok(s, return_tensors="pt").input_ids[0])
    return res


@torch.no_grad()
def greedy_batch(model, prompts, n_new, batched=True):
    """Greedy continuation of every prompt: each prompt prefilled alone, then all
    decoded together one token per step (batched=False decodes each alone)."""
    if not batched:
        res = []
        for p in prompts:
            res += greedy_batch(model, [p], n_new, True)
        return res
    B = len(prompts)
    cap = max(p.numel() for p in prompts) + n_new + 1
    cache = model.new_cache(B, cap)
    cur = []
    for b, p in enumerate(prompts):
        c1 = model.new_cache(1, p.numel())
        h = model.forward(p.to(model.device), c1)
        for i in range(model.L):
            cache["kv"][i][0][b, :, :p.numel()] = c1["kv"][i][0][0]
            cache["kv"][i][1][b, :, :p.numel()] = c1["kv"][i][1][0]
        cache["lens"][b] = p.numel()
        cur.append(h[-1:])
        del c1
    st = head_stats(model, torch.cat(cur, 0), None)
    toks = [[] for _ in range(B)]
    margins = [[] for _ in range(B)]
    for step in range(n_new):
        nxt = st["arg"]
        for b in range(B):
            toks[b].append(int(nxt[b]))
            margins[b].append(float(st["margin"][b]))
        if step == n_new - 1:
            break
        h = model.forward(nxt.to(model.device)[:, None], cache)[:, 0]
        st = head_stats(model, h, None)
    return [{"tokens": t, "margins": m} for t, m in zip(toks, margins)]


@torch.no_grad()
def teacher_forced(model, seq, start):
    """Argmax, margin and NLL at the positions predicting seq[start:]."""
    cache = model.new_cache(1, seq.numel())
    h = model.forward(seq.to(model.device), cache)
    return head_stats(model, h[start - 1:-1], seq[start:].to(model.device))


def mmlu_items(n, seed=0):
    from datasets import load_dataset
    d = load_dataset("cais/mmlu", "all", split="test")
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(d), size=n, replace=False)
    return [d[int(i)] for i in sorted(idx)]


def run_mmlu(model, tok, items):
    letters = ["A", "B", "C", "D"]
    cand = [tok(" " + L).input_ids[-1] for L in letters]
    res = []
    for it in items:
        q = f"The following is a multiple choice question about {it['subject'].replace('_', ' ')}.\n\n{it['question']}\n"
        for L, c in zip(letters, it["choices"]):
            q += f"{L}. {c}\n"
        q += "Answer:"
        ids = tok(q, return_tensors="pt").input_ids[0].to(model.device)
        cache = model.new_cache(1, ids.numel())
        h = model.forward(ids, cache)
        lg = model.logits(h[-1:])[0]
        pick = int(torch.argmax(lg[cand]).item())
        res.append({"pick": pick, "answer": int(it["answer"]), "correct": pick == int(it["answer"])})
    return res


# -- GPTQ (calibrated) variant of the weight formats ---------------------------------
def _gptq_matrix(W, H, fmt, blocksize=128, percdamp=0.01, row_chunk=16384):
    """GPTQ (Frantar et al. 2022) of W [N, K] with input Hessian H [K, K], groups of
    128 along K (the block), per-group symmetric INT scale chosen by MSE search on
    the error-updated weights at the group's start, and the same INT_lo/INT_hi
    group allocation as quantize() (chosen on the unupdated W)."""
    lo, hi, frac, g = QFORMATS[fmt]
    assert g == blocksize
    W = W.to(F32).clone() if W.shape[0] <= row_chunk else W.clone()
    N, K = W.shape
    H = H.clone()
    dead = torch.diag(H) == 0
    H[dead, dead] = 1
    W[:, dead] = 0
    use_hi = torch.zeros((N, K // g), dtype=torch.bool, device=W.device)
    if frac > 0:
        rows = max(1, (1 << 24) // K)
        gains = []
        for r0 in range(0, N, rows):
            wg = W[r0:r0 + rows].to(F32).reshape(-1, K // g, g)
            gains.append(_rtn_mse(wg, lo)[2] - _rtn_mse(wg, hi)[2])
        gain = torch.cat(gains)
        nhi = int(round(frac * gain.numel()))
        thr = torch.topk(gain.reshape(-1), nhi).values[-1]
        use_hi = gain >= thr
    H += percdamp * torch.mean(torch.diag(H)) * torch.eye(K, device=W.device)
    Hinv = torch.linalg.cholesky(torch.cholesky_inverse(torch.linalg.cholesky(H)), upper=True)
    codes = torch.empty((N, K), dtype=torch.int8)
    scales = torch.empty((N, K // g), dtype=BF16)
    for r0 in range(0, N, row_chunk):                       # rows are independent given H
        Wr = W[r0:r0 + row_chunk].to(F32)
        ur = use_hi[r0:r0 + row_chunk]
        cr = torch.empty(Wr.shape, dtype=torch.int8, device=W.device)
        sr = torch.empty((Wr.shape[0], K // g), dtype=BF16, device=W.device)
        for i1 in range(0, K, blocksize):
            i2 = i1 + blocksize
            gi = i1 // g
            W1 = Wr[:, i1:i2].clone()
            Err1 = torch.zeros_like(W1)
            Hinv1 = Hinv[i1:i2, i1:i2]
            _, s_lo, _ = _rtn_mse(W1[:, None, :], lo)
            _, s_hi, _ = _rtn_mse(W1[:, None, :], hi)
            u = ur[:, gi]
            sc = torch.where(u, s_hi[:, 0, 0], s_lo[:, 0, 0])
            qmax = torch.where(u, 2 ** (hi - 1) - 1, 2 ** (lo - 1) - 1).to(F32)
            qmin = -qmax - 1
            sr[:, gi] = sc.to(BF16)
            for i in range(blocksize):
                w = W1[:, i]
                d = Hinv1[i, i]
                q = torch.minimum(torch.maximum(torch.round(w / sc), qmin), qmax)
                cr[:, i1 + i] = q.to(torch.int8)
                err = (w - q * sc) / d
                W1[:, i:] -= err[:, None] * Hinv1[i, i:][None, :]
                Err1[:, i] = err
            Wr[:, i2:] -= Err1 @ Hinv[i1:i2, i2:]
        codes[r0:r0 + row_chunk] = cr.cpu()
        scales[r0:r0 + row_chunk] = sr.cpu()
    bits = lo + (hi - lo) * use_hi.float().mean().item() + 16.0 / g
    return codes, scales, bits


def c4_calibration(tok, nseq, seqlen, seed=0):
    from datasets import load_dataset
    d = load_dataset("allenai/c4", data_files={"train": "en/c4-train.00000-of-01024.json.gz"}, split="train")
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < nseq:
        t = d[int(rng.integers(len(d)))]["text"]
        ids = tok(t, return_tensors="pt").input_ids[0]
        if ids.numel() <= seqlen:
            continue
        s0 = int(rng.integers(ids.numel() - seqlen))
        out.append(ids[s0:s0 + seqlen])
    return torch.stack(out)


@torch.no_grad()
def gptq_build(snap, fmt, fold, out_path, nseq=128, seqlen=2048, chunk=8):
    """Sequential layer-by-layer GPTQ of every linear layer (fused qkv, o, fused
    gate/up, down, lm_head) on C4 calibration text, in the vendor BF16 forward.
    fold=True quantises the norm-folded W' = bf16(W diag(w)) of q,k,v and gate,up
    against the inputs they see in the contract (x / rms, i.e. normalised without
    the weight), as the decode core consumes them."""
    from transformers import AutoTokenizer
    dev = torch.device("cuda")
    tok = AutoTokenizer.from_pretrained(str(snap))
    cfg = json.loads((Path(snap) / "config.json").read_text())
    L, Hd, NH, KV, HD, FF = (cfg[k] for k in ("num_hidden_layers", "hidden_size", "num_attention_heads",
                                               "num_key_value_heads", "head_dim", "intermediate_size"))
    eps, theta = cfg["rms_norm_eps"], cfg["rope_theta"]
    sd = load_state(snap, "cpu")
    calib = c4_calibration(tok, nseq, seqlen)
    xs = sd["model.embed_tokens.weight"][calib]                     # [nseq, T, H] bf16 on CPU
    inv = 1.0 / (theta ** (torch.arange(0, HD, 2, dtype=torch.int64).to(F32) / HD))
    fr = torch.arange(seqlen, dtype=F32)[:, None] * inv[None, :]
    emb = torch.cat([fr, fr], -1).to(dev)
    cos, sin = emb.cos().to(BF16), emb.sin().to(BF16)
    rot = lambda t: torch.cat([-t[..., HD // 2:], t[..., :HD // 2]], -1)

    def rms(x, w=None):
        xf = x.to(F32)
        xf = xf * torch.rsqrt(xf.pow(2).mean(-1, keepdim=True) + eps)
        return xf.to(BF16) if w is None else w * xf.to(BF16)

    def hess(fn, K):
        Hm = torch.zeros((K, K), device=dev, dtype=F32)
        for c0 in range(0, nseq, chunk):
            a = fn(c0).reshape(-1, K).to(F32)
            Hm += a.t() @ a
        return Hm * (2.0 / (nseq * seqlen))

    def deq(codes, scales):
        return dequant(codes.to(dev), scales.to(dev)).to(BF16)

    res = {"fmt": fmt, "fold": fold, "calib": f"C4 en train shard 00000, {nseq} x {seqlen} tokens, seed 0", "w": {}}
    for i in range(L):
        t0 = time.time()
        p = f"model.layers.{i}."
        g = lambda n: sd[p + n].to(dev)
        ln1, ln2 = g("input_layernorm.weight"), g("post_attention_layernorm.weight")
        qn, kn = g("self_attn.q_norm.weight"), g("self_attn.k_norm.weight")
        qkv = torch.cat([g("self_attn.q_proj.weight"), g("self_attn.k_proj.weight"), g("self_attn.v_proj.weight")])
        gu = torch.cat([g("mlp.gate_proj.weight"), g("mlp.up_proj.weight")])
        ow, dw = g("self_attn.o_proj.weight"), g("mlp.down_proj.weight")
        if fold:
            qkv = (qkv.to(F32) * ln1.to(F32)[None]).to(BF16)
            gu = (gu.to(F32) * ln2.to(F32)[None]).to(BF16)
        in1 = (lambda x: rms(x)) if fold else (lambda x: rms(x, ln1))
        in2 = (lambda x: rms(x)) if fold else (lambda x: rms(x, ln2))
        X = lambda c0: xs[c0:c0 + chunk].to(dev)
        c, s_, b = _gptq_matrix(qkv, hess(lambda c0: in1(X(c0)), Hd), fmt)
        res["w"][f"{i}.qkv"] = (c, s_, b)
        qkv_q = deq(c, s_)

        def attn_in(c0):
            x = X(c0)
            B = x.shape[0]
            q, k, v = Fn.linear(in1(x), qkv_q).split([NH * HD, KV * HD, KV * HD], -1)
            q = rms(q.view(B, seqlen, NH, HD), qn).transpose(1, 2)
            k = rms(k.view(B, seqlen, KV, HD), kn).transpose(1, 2)
            v = v.view(B, seqlen, KV, HD).transpose(1, 2)
            q, k = q * cos + rot(q) * sin, k * cos + rot(k) * sin
            a = Fn.scaled_dot_product_attention(q, k, v, is_causal=True, enable_gqa=True)
            return a.transpose(1, 2).reshape(B, seqlen, NH * HD)
        c, s_, b = _gptq_matrix(ow, hess(attn_in, NH * HD), fmt)
        res["w"][f"{i}.o"] = (c, s_, b)
        o_q = deq(c, s_)
        for c0 in range(0, nseq, chunk):                       # residual after attention
            xs[c0:c0 + chunk] = (X(c0) + Fn.linear(attn_in(c0), o_q)).cpu()
        c, s_, b = _gptq_matrix(gu, hess(lambda c0: in2(X(c0)), Hd), fmt)
        res["w"][f"{i}.gu"] = (c, s_, b)
        gu_q = deq(c, s_)

        def down_in(c0):
            gt, up = Fn.linear(in2(X(c0)), gu_q).split([FF, FF], -1)
            return Fn.silu(gt) * up
        c, s_, b = _gptq_matrix(dw, hess(down_in, FF), fmt)
        res["w"][f"{i}.down"] = (c, s_, b)
        d_q = deq(c, s_)
        for c0 in range(0, nseq, chunk):
            xs[c0:c0 + chunk] = (X(c0) + Fn.linear(down_in(c0), d_q)).cpu()
        del qkv_q, o_q, gu_q, d_q
        torch.cuda.empty_cache()
        print(f"  gptq layer {i} ({time.time() - t0:.0f}s)", flush=True)
    nw = sd["model.norm.weight"].to(dev)
    c, s_, b = _gptq_matrix(sd["lm_head.weight"].to(dev), hess(lambda c0: rms(xs[c0:c0 + chunk].to(dev), nw), Hd), fmt)
    res["w"]["lm_head"] = (c, s_, b)
    if out_path:
        torch.save(res, out_path)
    return res


# -- summary -----------------------------------------------------------------------
THRESHOLD = {
    "rule": "acceptable iff, against a_bf16, WikiText-2 perplexity rises by at most 2.0% (relative) at "
            "every measured context AND MMLU accuracy falls by at most 1.0 point (point estimates; the "
            "95% CIs are reported beside them). Fixed before any full-model result was seen.",
    "ppl_rel_max": 0.02, "mmlu_drop_max_pt": 1.0,
}


def _boot(fn, n, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    vals = [fn(rng.integers(0, n, n)) for _ in range(B)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def summarize(raw_dir, out_path, meta):
    raw = {p.stem: json.loads(p.read_text()) for p in Path(raw_dir).glob("*.json")}
    ref = raw["a_bf16"]
    res = {"schema": "opentallas.qwen3-8b-deployment-quality.v1", **meta, "threshold": THRESHOLD, "modes": {}}
    for name, r in sorted(raw.items()):
        m = {"arith": r["arith"], "weights": r["weights"], "kv": r["kv"], "weight_bits": r.get("weight_bits"),
             "wall_s": r.get("wall_s"), "recip_sat_hits": r.get("recip_sat_hits")}
        for ctx in (2048, 8192):
            key = f"ppl_{ctx}"
            if key not in r or key not in ref:
                continue
            n = min(len(r[key]), len(ref[key]))
            s_m = np.array([np.sum(w["nll"]) for w in r[key][:n]])
            s_r = np.array([np.sum(w["nll"]) for w in ref[key][:n]])
            cnt = np.array([len(w["nll"]) for w in r[key][:n]])
            ppl = lambda s, i: float(np.exp(s[i].sum() / cnt[i].sum()))
            allw = np.arange(n)
            agree = [np.array(a["arg"]) == np.array(b["arg"]) for a, b in zip(r[key][:n], ref[key][:n])]
            ag_n = np.array([a.sum() for a in agree])
            ag_c = np.array([len(a) for a in agree])
            d = {"windows": int(n), "tokens": int(cnt.sum()), "ppl": ppl(s_m, allw), "ppl_ref": ppl(s_r, allw),
                 "delta_ppl": ppl(s_m, allw) - ppl(s_r, allw),
                 "delta_ppl_ci95": _boot(lambda i: ppl(s_m, i) - ppl(s_r, i), n),
                 "rel_delta_ppl": ppl(s_m, allw) / ppl(s_r, allw) - 1,
                 "rel_delta_ppl_ci95": _boot(lambda i: ppl(s_m, i) / ppl(s_r, i) - 1, n),
                 "top1_agree_vs_ref": float(ag_n.sum() / ag_c.sum()),
                 "top1_agree_ci95": _boot(lambda i: ag_n[i].sum() / ag_c[i].sum(), n)}
            ref_margin = np.concatenate([np.array(w["margin"]) for w in ref[key][:n]])
            dis = ~np.concatenate(agree)
            if dis.any():
                d["ref_margin_at_disagreements"] = {
                    "median_logits": float(np.median(ref_margin[dis])),
                    "fraction_below_0.5": float(np.mean(ref_margin[dis] < 0.5)),
                    "fraction_below_1.0": float(np.mean(ref_margin[dis] < 1.0))}
            if ctx == 8192:
                buckets = {}
                for lo in range(0, ctx, 2048):
                    a = np.concatenate([x[lo:lo + 2048] for x in agree])
                    buckets[f"{lo}-{lo + 2048}"] = float(a.mean())
                d["top1_agree_by_position"] = buckets
                late = np.array([x[6144:].mean() for x in agree])
                d["top1_disagree_rate_positions_6144_8191"] = float(1 - late.mean())
                d["top1_disagree_rate_positions_6144_8191_ci95"] = sorted(
                    1 - np.array(_boot(lambda i: late[i].mean(), n)))
            m[f"wikitext2_{ctx}"] = d
        if "greedy" in r and "greedy" in ref:
            div, full = [], 0
            for a, b in zip(r["greedy"], ref["greedy"]):
                ta, tb = a["tokens"], b["tokens"]
                k = next((i for i, (x, y) in enumerate(zip(ta, tb)) if x != y), None)
                if k is None:
                    k = min(len(ta), len(tb))
                    if len(ta) == len(tb):
                        full += 1
                div.append(k)
            div = np.array(div)
            m["greedy_free_run"] = {"prompts": int(len(div)), "identical_continuations": int(full),
                                    "identical_fraction": full / len(div),
                                    "first_divergence_median": float(np.median(div)),
                                    "first_divergence_mean": float(div.mean()),
                                    "first_divergence_all": div.tolist()}
        if "teacher_forced" in r:
            rg = ref["greedy"]
            ag = [np.array(t["arg"]) == np.array(g["tokens"]) for t, g in zip(r["teacher_forced"], rg)]
            ag_n = np.array([a.sum() for a in ag])
            ag_c = np.array([len(a) for a in ag])
            m["greedy_teacher_forced"] = {
                "prompts": len(ag), "tokens": int(ag_c.sum()),
                "top1_agree_with_bf16_greedy": float(ag_n.sum() / ag_c.sum()),
                "ci95_cluster_bootstrap": _boot(lambda i: ag_n[i].sum() / ag_c[i].sum(), len(ag)),
                "mean_nll_of_bf16_greedy_tokens": float(np.mean(np.concatenate([t["nll"] for t in r["teacher_forced"]])))}
        if "mmlu" in r and "mmlu" in ref:
            c = np.array([x["correct"] for x in r["mmlu"]], float)
            cr = np.array([x["correct"] for x in ref["mmlu"]], float)
            same = np.mean([x["pick"] == y["pick"] for x, y in zip(r["mmlu"], ref["mmlu"])])
            m["mmlu"] = {"questions": int(len(c)), "accuracy": float(c.mean()),
                         "accuracy_ci95": _boot(lambda i: c[i].mean(), len(c)),
                         "delta_pt": float(100 * (c.mean() - cr.mean())),
                         "delta_pt_ci95": [100 * v for v in _boot(lambda i: c[i].mean() - cr[i].mean(), len(c))],
                         "same_answer_as_ref": float(same)}
        res["modes"][name] = m
    verdict = {}
    for name, m in res["modes"].items():
        if name == "a_bf16" or "unbatched" in name:
            continue
        ok = []
        for ctx in (2048, 8192):
            if f"wikitext2_{ctx}" in m:
                ok.append(m[f"wikitext2_{ctx}"]["rel_delta_ppl"] <= THRESHOLD["ppl_rel_max"])
        if "mmlu" in m:
            ok.append(m["mmlu"]["delta_pt"] >= -THRESHOLD["mmlu_drop_max_pt"])
        verdict[name] = "acceptable" if ok and all(ok) else ("not acceptable" if ok else "not measured")
    res["verdict"] = verdict
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mode", choices=sorted(MODES))
    ap.add_argument("--summarize", default=None, help="directory of per-mode raw JSONs (<mode>.json)")
    ap.add_argument("--meta", default=None, help="JSON file merged into the summary")
    ap.add_argument("--tasks", default="ppl2k,ppl8k,greedy,mmlu")
    ap.add_argument("--ppl-windows-2k", type=int, default=1000)
    ap.add_argument("--ppl-windows-8k", type=int, default=1000)
    ap.add_argument("--greedy-prompts", type=int, default=50)
    ap.add_argument("--greedy-tokens", type=int, default=256)
    ap.add_argument("--greedy-unbatched", action="store_true", help="decode each prompt alone (noise-floor run)")
    ap.add_argument("--greedy-ref", default=None, help="a_bf16 raw JSON whose greedy tokens are teacher-forced")
    ap.add_argument("--mmlu", type=int, default=1000)
    ap.add_argument("--groups", type=int, default=SPEC_GROUPS)
    ap.add_argument("--wfile", default=None, help="pre-quantised (GPTQ) weights from --build-gptq")
    ap.add_argument("--build-gptq", default=None, metavar="FMT", help="build GPTQ weights of FMT into --out")
    ap.add_argument("--fold", action="store_true", help="--build-gptq for the contract's norm-folded matrices")
    ap.add_argument("--gptq-nseq", type=int, default=128)
    ap.add_argument("--gptq-inline", default=None, metavar="FMT",
                    help="GPTQ-quantise FMT in this process (no dump on disk) and evaluate with it")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.build_gptq:
        gptq_build(find_snapshot(), args.build_gptq, args.fold, args.out, nseq=args.gptq_nseq)
        return
    if args.summarize:
        meta = json.loads(Path(args.meta).read_text()) if args.meta else {}
        summarize(args.summarize, args.out, meta)
        return
    from transformers import AutoTokenizer
    snap = find_snapshot()
    tok = AutoTokenizer.from_pretrained(str(snap))
    arith, wf, kv = MODES[args.mode]
    t0 = time.time()
    wsrc = args.wfile
    if args.gptq_inline:
        tg = time.time()
        wsrc = gptq_build(snap, args.gptq_inline, arith == "contract", None, nseq=args.gptq_nseq)
        wsrc["build_s"] = time.time() - tg
        torch.cuda.empty_cache()
    gptq_meta = {k: v for k, v in wsrc.items() if k != "w"} if isinstance(wsrc, dict) else None
    model = Qwen3(snap, arith, wf, kv, groups=args.groups, wfile=wsrc)
    del wsrc
    if args.wfile or args.gptq_inline:
        wf = model.wfmt + "_gptq"
    out = {"mode": args.mode, "arith": arith, "weights": wf, "kv": kv, "groups": args.groups, "wfile": args.wfile, "gptq": gptq_meta,
           "snapshot": str(snap), "load_s": time.time() - t0,
           "weight_bits": {k: float(np.mean(v)) for k, v in model.bits.items()}}
    print(f"[{args.mode}] loaded in {out['load_s']:.0f}s bits={out['weight_bits']} "
          f"mem={torch.cuda.memory_allocated() / 2**30:.1f} GiB", flush=True)
    tasks = args.tasks.split(",")
    outp = Path(args.out)

    def save():
        out["recip_sat_hits"] = int(RECIP_SAT_HITS[0])
        outp.write_text(json.dumps(out))
    if "ppl2k" in tasks or "ppl8k" in tasks:
        ids = wikitext_ids(tok)
        out["wikitext_tokens"] = int(ids.numel())
        if "ppl2k" in tasks:
            run_ppl(model, ids, 2048, args.ppl_windows_2k, out)
            save()
        if "ppl8k" in tasks:
            run_ppl(model, ids, 8192, args.ppl_windows_8k, out)
            save()
    if "greedy" in tasks:
        prompts = mtbench_prompts(tok, args.greedy_prompts)
        t1 = time.time()
        g = greedy_batch(model, prompts, args.greedy_tokens, batched=not args.greedy_unbatched)
        for p, r in zip(prompts, g):
            r["prompt"] = p.tolist()
        print(f"  greedy {len(prompts)} x {args.greedy_tokens} ({time.time() - t1:.0f}s)", flush=True)
        out["greedy"] = g
        out["greedy_batched"] = not args.greedy_unbatched
        save()
    if "tf" in tasks:
        ref = json.loads(Path(args.greedy_ref).read_text())["greedy"]
        tf = []
        for r in ref:
            seq = torch.tensor(r["prompt"] + r["tokens"])
            st = teacher_forced(model, seq, len(r["prompt"]))
            tf.append({"arg": st["arg"].tolist(), "margin": st["margin"].tolist(), "nll": st["nll"].tolist()})
        out["teacher_forced"] = tf
        save()
    if "mmlu" in tasks:
        t1 = time.time()
        out["mmlu"] = run_mmlu(model, tok, mmlu_items(args.mmlu))
        print(f"  mmlu acc {np.mean([r['correct'] for r in out['mmlu']]):.4f} ({time.time() - t1:.0f}s)", flush=True)
        save()
    out["wall_s"] = time.time() - t0
    save()


if __name__ == "__main__":
    main()
