#!/usr/bin/env python3
"""Full-model quality of DeepSeek-V4.1-Flash under the ROM array's deployment arithmetic.

Answers finding 4 of the 2026-09-27 atlas feasibility review for V4.1: bit-exactness
shows the RTL matches the adopted arithmetic contract, not that the contract leaves
model quality unchanged.  This tool runs the FULL released checkpoint (40 layers,
384 routed experts, hidden 5,120, vocabulary 129,280, the official FP8/FP4
precision everywhere) layer by layer on one GPU and compares three arithmetics on
the same inputs:

* ``a``   the REFERENCE: the vendor's own inference code
          (inference/model.py + kernel.py of revision dba1be0a, its tilelang FP8/FP4
          GEMMs, sparse-attention and Sinkhorn kernels), evaluated as the vendor
          evaluates a prompt (one prefill call per sequence).
* ``b``   the DEPLOYMENT CONTRACT: tools/hdc_golden_v41.py under
          HDC_V41_ARITH=chunk8 and HDC_V41_FUSE=osm (R-ARITH plus the adopted
          R-ARITH v2 online softmax; norm folding is rejected, docs/ARCH_SPEC_V41.md
          section 12), emulated EXACTLY on the GPU: every accumulation cut into
          contiguous chunks of 8 summed sequentially from +0, chunk sums a pairwise
          tree padded with +0; FP8/FP4 linears as exact 32-element block dots
          rounded once, block sums by the same chunk-8 tree; attention the online
          softmax in the release kernel's 64-entry blocks in the decode kernel's
          row order; exp by Cody-Waite + degree-6 Horner, rsqrt by bit seed + 3
          Newton steps, softplus by the log1p series, IEEE division and sqrt;
          top-k ties to the lower index; every zero canonical +0.  The GPU
          emulation is checked bit-exact against the numpy golden on the reduced
          vehicle (tests/test_deepseek_v41_deployment_quality.py).
* ``a2``  an independent GPU implementation of the release's semantics (this
          file's code with cuBLAS FP32 GEMMs, torch special functions, a plain
          two-pass softmax and torch.topk): a second legitimate GPU arithmetic, so
          a vs a2 is the noise floor that any reordering of FP32 sums produces.

``c`` (deployment + compressed/FP8 KV) is ``b`` itself: the deployed KV formats are
the checkpoint's own -- window KV FP8 E4M3 with one UE8M0 scale per 32, compressed
KV FP4 E2M1 with one E4M3 scale per 16, index keys FP4 with one UE8M0 scale per
32 -- and every dequantised value is exactly representable in BF16, so storing the
codes in HBM and dequantising on read is value-identical to the golden's BF16
quantise-dequantise (asserted at run time).

Teacher-forced modes ``b_tf`` / ``a2_tf`` run layer L on the reference's own input
at layer L (and their own compressed/index state chain), so the router and index
flip rates they report are those of ONE layer's arithmetic, not of drift
accumulated through earlier layers.

Layer streaming: one decoder layer (7.4 GB) is resident at a time; every sequence
of the evaluation set goes through layer L in every mode before layer L+1 is
loaded, so the checkpoint is read once.  Engram rows are gathered from the 98 GB
tables through a random-access mmap.  Nothing large is written to disk.
"""
from __future__ import annotations

import argparse
import dataclasses
import gc
import json
import math
import mmap
import os
import struct
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as Fn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import hdc_golden as G  # noqa: E402  (constants and the numpy primitives' definitions)
import hdc_golden_v41 as GV  # noqa: E402  (rope tables, series constants)

F32, BF16 = torch.float32, torch.bfloat16
SNAPSHOT = Path(os.environ.get(
    "DEEPSEEK_V41_SNAPSHOT",
    Path.home() / ".cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/"
    "dba1be0a40aa45a94ad051997016db3960a90277"))
OUT = ROOT / "results/quality/deepseek_v41_flash_deployment_arithmetic.json"
CHUNK = 8

# Pre-registered acceptance rule (fixed before any full-model result existed; same rule as
# results/quality/qwen3_8b_deployment_arithmetic.json).
THRESHOLD = {
    "rule": "the deployment contract (b) is acceptable iff, against the vendor reference (a), WikiText-2 "
            "perplexity rises by at most 2.0% (relative) AND MMLU accuracy falls by at most 1.0 point "
            "(point estimates; paired 95% bootstrap CIs reported beside them). Top-1 agreement, KL, and the "
            "per-layer router/index selection flip rates are reported against the a-vs-a2 noise floor of two "
            "legitimate GPU arithmetics; they are descriptive, not gating. Fixed before any full-model result "
            "was seen.",
    "ppl_rel_max": 0.02,
    "mmlu_drop_max_pt": 1.0,
}


# ======================================================================================
# Triton kernels
# ======================================================================================
try:
    import triton
    import triton.language as tl

    @triton.jit(do_not_specialize=["T", "N", "NB", "S"])
    def _qdot_kernel(XT, XE, WT, WE, OUT, T, N, NB, S,
                     sxk, sxeb, swk, sweb, sos, sot,
                     BT: tl.constexpr, BN: tl.constexpr, WFMT: tl.constexpr):
        """OUT[c, t, n] = chunk c (blocks 8c .. 8c+7) of the R-ARITH block sum of an FP8/FP4 linear:
        per 32-wide block b the dot of the codes XT[k, t] (E4M3 values) and WT[k, n] (E4M3/E2M1
        values) formed EXACTLY and rounded once to FP32, times 2^(XE[b,t] + WE[b,n]); the blocks of
        a chunk added sequentially from +0.  Exactness: every product is exact and a multiple of
        2^-18; p is split into ph = (p + 1.5*2^25) - 1.5*2^25 (a multiple of 4) and p - ph
        (|.| <= 2); the 32 high parts sum exactly below 2^25 and the low parts exactly below 2^6
        at 2^-18 resolution, so hi + lo is the exact block dot and one rounding.  Launched with
        enable_fp_fusion=False, so nothing is contracted."""
        pid_t = tl.program_id(0)
        pid_n = tl.program_id(1)
        offs_t = pid_t * BT + tl.arange(0, BT)
        offs_n = pid_n * BN + tl.arange(0, BN)
        mt = offs_t < T
        mn = offs_n < N
        MAGIC_SPLIT = 50331648.0
        c = tl.program_id(2)
        if True:
            acc = tl.zeros([BT, BN], dtype=tl.float32)
            b_end = tl.minimum(c * 8 + 8, NB)
            for b in range(c * 8, b_end):
                hi = tl.zeros([BT, BN], dtype=tl.float32)
                lo = tl.zeros([BT, BN], dtype=tl.float32)
                for j in range(32):
                    k = b * 32 + j
                    xk = tl.load(XT + k * sxk + offs_t, mask=mt, other=0.0)
                    if WFMT == 0:      # code values (BF16/FP32)
                        wk = tl.load(WT + k * swk + offs_n, mask=mn, other=0.0).to(tl.float32)
                    elif WFMT == 1:    # E4M3 bytes
                        wb = tl.load(WT + k * swk + offs_n, mask=mn, other=0)
                        wk = wb.to(tl.float8e4nv, bitcast=True).to(tl.float32)
                    else:              # packed E2M1, low nibble = even k
                        wb = tl.load(WT + (k // 2) * swk + offs_n, mask=mn, other=0).to(tl.int32)
                        nib = (wb >> ((k % 2) * 4)) & 15
                        cc = nib & 7
                        cf = cc.to(tl.float32)
                        mag = tl.where(cc < 4, cf * 0.5, tl.where(cc == 7, 6.0, cf - 2.0))
                        wk = tl.where(nib >= 8, -mag, mag)
                    p = xk[:, None] * wk[None, :]
                    ph = (p + MAGIC_SPLIT) - MAGIC_SPLIT
                    hi = hi + ph
                    lo = lo + (p - ph)
                v = hi + lo
                ex = tl.load(XE + b * sxeb + offs_t, mask=mt, other=0)
                ew = tl.load(WE + b * sweb + offs_n, mask=mn, other=0)
                e = ex[:, None] + ew[None, :]
                e1 = e >> 1
                e2 = e - e1
                direct = e >= -126
                s_a = (tl.where(direct, e, e1) + 127) << 23
                s_b = (tl.where(direct, 0, e2) + 127) << 23
                v = v * s_a.to(tl.float32, bitcast=True)
                v = v * s_b.to(tl.float32, bitcast=True)
                acc = acc + v
            tl.store(OUT + c * sos + offs_t[:, None] * sot + offs_n[None, :], acc,
                     mask=mt[:, None] & mn[None, :])

    @triton.jit
    def _mul_rn(a, b):
        return tl.inline_asm_elementwise("mul.rn.f32 $0, $1, $2;", "=r,r,r", [a, b],
                                         dtype=tl.float32, is_pure=True, pack=1)

    @triton.jit
    def _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0, K, sxk, swk,
                BT: tl.constexpr, BN: tl.constexpr, ROUND: tl.constexpr):
        acc = tl.zeros([BT, BN], dtype=tl.float32)
        for j in tl.static_range(8):
            k = k0 + j
            kin = k < K
            xk = tl.load(Xb + k * sxk + offs_t, mask=mt & kin, other=0.0).to(tl.float32)
            wk = tl.load(Wb + k * swk + offs_n, mask=mn & kin, other=0.0).to(tl.float32)
            if ROUND:
                acc = acc + _mul_rn(tl.broadcast_to(xk[:, None], (BT, BN)), tl.broadcast_to(wk[None, :], (BT, BN)))
            else:
                acc = acc + xk[:, None] * wk[None, :]
        return acc

    @triton.jit(do_not_specialize=["T", "N", "K", "NG", "NTT", "NNP", "sxb", "sxk", "swb", "swk",
                                   "sob", "sot", "son"])
    def _csum_kernel(X, W, OUT, STK, T, N, K, NG, NTT, NNP,
                     sxb, sxk, swb, swk, sob, sot, son,
                     BT: tl.constexpr, BN: tl.constexpr, LV: tl.constexpr, ROUND: tl.constexpr):
        """OUT[b, t, n] = R-ARITH sum over k of X[b, k, t] * W[b, k, n]: chunks of 8 sequential
        from +0; the chunk sums a pairwise tree padded with +0.  Each group of 8 chunks (64 k) is
        a static register tree; the group sums enter a binary-counter stack in global scratch
        (STK, per program) and the partial stack of a non-power-of-two group count is folded
        from its lowest level up (= padding the leaves with +0).  With exact products (BF16 x
        BF16) the FMA equals mul + add; the rounded-product form is the same kernel launched with
        enable_fp_fusion=False."""
        pid0 = tl.program_id(0)
        pid_b = pid0 // NTT
        pid_t = pid0 % NTT
        pid_n = tl.program_id(1)
        Xb = X + pid_b.to(tl.int64) * sxb
        Wb = W + pid_b.to(tl.int64) * swb
        offs_t = pid_t * BT + tl.arange(0, BT)
        offs_n = pid_n * BN + tl.arange(0, BN)
        mt = offs_t < T
        mn = offs_n < N
        prog = pid0.to(tl.int64) * NNP + pid_n
        stk = STK + prog * (LV * BT * BN) + tl.arange(0, BT)[:, None] * BN + tl.arange(0, BN)[None, :]
        for g in range(NG):
            k0 = g * 64
            c0 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0, K, sxk, swk, BT, BN, ROUND)
            c1 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 8, K, sxk, swk, BT, BN, ROUND)
            q0 = c0 + c1
            c0 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 16, K, sxk, swk, BT, BN, ROUND)
            c1 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 24, K, sxk, swk, BT, BN, ROUND)
            q0 = q0 + (c0 + c1)
            c0 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 32, K, sxk, swk, BT, BN, ROUND)
            c1 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 40, K, sxk, swk, BT, BN, ROUND)
            q1 = c0 + c1
            c0 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 48, K, sxk, swk, BT, BN, ROUND)
            c1 = _chunk8(Xb, Wb, offs_t, offs_n, mt, mn, k0 + 56, K, sxk, swk, BT, BN, ROUND)
            acc = q0 + (q1 + (c0 + c1))
            cc = g
            lvl = 0
            while (cc & 1) == 1:
                acc = tl.load(stk + lvl * (BT * BN)) + acc
                cc = cc >> 1
                lvl += 1
            tl.store(stk + lvl * (BT * BN), acc)
        res = tl.zeros([BT, BN], dtype=tl.float32)
        for lv in range(LV):
            if ((NG >> lv) & 1) == 1:
                res = tl.load(stk + lv * (BT * BN)) + res
        tl.store(OUT + pid_b.to(tl.int64) * sob + offs_t[:, None] * sot + offs_n[None, :] * son, res,
                 mask=mt[:, None] & mn[None, :])

    HAVE_TRITON = True
except Exception:  # pragma: no cover
    HAVE_TRITON = False


def qdot_chunks(xq, xe, qw, BT=32, BN=64):
    """Chunk sums [S, M, N] of an FP8/FP4 linear (see _qdot_kernel).  xq [M, K] E4M3 code values
    (FP32), xe [M, K/32] int32; qw a QW (K-major codes or raw bytes, [K/32, N] exponents)."""
    M, K = xq.shape
    N = qw.N
    NB = K // 32
    S = -(-NB // 8)
    xT = xq.t().contiguous()
    xeT = xe.t().contiguous().to(torch.int32)
    out = torch.empty((S, M, N), device=xq.device, dtype=F32)
    grid = (triton.cdiv(M, BT), triton.cdiv(N, BN), S)
    _qdot_kernel[grid](xT, xeT, qw.wT, qw.we, out, M, N, NB, S,
                       xT.stride(0), xeT.stride(0), qw.wT.stride(0), qw.we.stride(0), out.stride(0), out.stride(1),
                       BT=BT, BN=BN, WFMT=qw.fmt, num_warps=4)
    return out


def csum_mm(x, w, x_kmajor=False, w_kmajor=False, exact=True, BT=None, BN=None, budget=1 << 28):
    """R-ARITH dot products out[b, t, n] = csum_k x[b, t, k] * w[b, n, k].
    x: [B, T, K] (or [B, K, T] if x_kmajor); w: [B, N, K] (or [B, K, N] if w_kmajor) or unbatched
    [N, K]/[K, N] shared by every b.  exact=True: products are exact (BF16 x BF16) so the kernel's
    FMAs equal the golden's mul + add; exact=False: every product rounded (mul.rn, then add)."""
    if x.dim() == 2:
        x = x[None]
    xk = (x if x_kmajor else x.transpose(1, 2)).contiguous()           # [B, K, T]
    B, K, T = xk.shape
    shared = w.dim() == 2
    wb = w[None] if shared else w
    wk = (wb if w_kmajor else wb.transpose(1, 2)).contiguous()         # [B|1, K, N]
    N = wk.shape[2]
    swb = 0 if shared else wk.stride(0)
    BT = BT or (32 if T >= 32 else 16)
    BN = BN or (32 if T >= 32 or N < 64 else 64)
    NG = -(-K // 64)
    LV = max(1, int(NG).bit_length())
    NTT = triton.cdiv(T, BT)
    NNP = triton.cdiv(N, BN)
    out = torch.empty((B, T, N), device=x.device, dtype=F32)
    per_b = NTT * NNP * LV * BT * BN
    bstep = max(1, budget // max(1, per_b))
    for b0 in range(0, B, bstep):
        nb = min(bstep, B - b0)
        stk = torch.empty(nb * per_b, device=x.device, dtype=F32)
        xs = xk[b0:b0 + nb]
        ws = wk if shared else wk[b0:b0 + nb]
        os_ = out[b0:b0 + nb]
        _csum_kernel[(nb * NTT, NNP)](xs, ws, os_, stk, T, N, K, NG, NTT, NNP,
                                      xs.stride(0), xs.stride(1), swb, ws.stride(1),
                                      os_.stride(0), os_.stride(1), os_.stride(2),
                                      BT=BT, BN=BN, LV=LV, ROUND=not exact, num_warps=4)
        del stk
    return out


# ======================================================================================
# golden elementwise primitives (eager torch: separate IEEE binary32 operations)
# ======================================================================================
def f32c(v):
    return float(np.float32(v))


def z(x):
    """canonical +0: x + (+0) is x except -0 -> +0."""
    return x + 0.0


def add(a, b):
    return (a + b) + 0.0


def mul(a, b):
    return (a * b) + 0.0


def div(a, b):
    return (a / b) + 0.0


def neg(a):
    return -a


def to_bf16(x):
    return x.to(BF16).to(F32)


def _bits(x):
    return x.contiguous().view(torch.int32)


def _from_bits(b):
    return b.contiguous().view(F32)


def pow2(e):
    """2^e as FP32 for integer tensor e in [-126, 127]."""
    return _from_bits(((e.to(torch.int32) + 127) << 23))


def pow2_64(e):
    """2^e as float64, exactly, for integer tensor e in [-1022, 1023] (torch.ldexp on CUDA is not exact)."""
    return ((e.to(torch.int64) + 1023) << 52).view(torch.float64)


def rsqrt_g(v):
    y = _from_bits(0x5F3759DF - (_bits(v) >> 1))
    half = mul(v, 0.5)
    for _ in range(3):
        y = mul(y, add(1.5, neg(mul(half, mul(y, y)))))
    return y


def exp_g(x):
    x = x.clamp(f32c(G.EXP_MIN), f32c(G.EXP_MAX))
    t = mul(x, f32c(G.LOG2E))
    u = add(t, f32c(G.MAGIC))
    n = add(u, -f32c(G.MAGIC))
    r = add(add(x, neg(mul(n, f32c(G.LN2_HI)))), neg(mul(n, f32c(G.LN2_LO))))
    p = torch.full_like(r, f32c(G.EXP_POLY[0]))
    for c in G.EXP_POLY[1:]:
        p = add(mul(p, r), f32c(c))
    return _from_bits(_bits(p) + (n.to(torch.int32) << 23))


def sqrt_g(x):
    return torch.sqrt(x) + 0.0


def sigmoid_g(x):
    return div(torch.ones_like(x), add(exp_g(neg(x)), 1.0))


def silu_g(x):
    return div(x, add(exp_g(neg(x)), 1.0))


def log1p_unit_g(t):
    u = div(t, add(t, 2.0))
    u2 = mul(u, u)
    p = torch.full_like(u, f32c(GV.LOG1P_ODD[0]))
    for c in GV.LOG1P_ODD[1:]:
        p = add(mul(p, u2), f32c(c))
    return mul(mul(u, p), 2.0)


def softplus_g(x):
    t = exp_g(neg(x.abs()))
    return add(torch.clamp_min(x, 0.0), log1p_unit_g(t))


def csum_t(v, dim=-1, c=CHUNK):
    """R-ARITH sum along `dim` (torch, elementwise IEEE adds)."""
    v = v.movedim(dim, -1)
    n = v.shape[-1]
    nc = max(1, -(-n // c))
    if nc * c != n:
        v = torch.cat([v, v.new_zeros(*v.shape[:-1], nc * c - n)], -1)
    v = v.reshape(*v.shape[:-1], nc, c)
    acc = v.new_zeros(v.shape[:-1])
    for j in range(c):
        acc = add(acc, v[..., j])
    p = 1
    while p < nc:
        p *= 2
    if p != nc:
        acc = torch.cat([acc, acc.new_zeros(*acc.shape[:-1], p - nc)], -1)
    while acc.shape[-1] > 1:
        acc = add(acc[..., 0::2], acc[..., 1::2])
    return acc[..., 0]


def tree_t(v):
    """pairwise tree over dim 0 (chunk sums), padded with +0 to a power of two."""
    n = v.shape[0]
    p = 1
    while p < n:
        p *= 2
    if p != n:
        v = torch.cat([v, v.new_zeros((p - n,) + tuple(v.shape[1:]))], 0)
    while v.shape[0] > 1:
        v = add(v[0::2], v[1::2])
    return v[0]


def ceil_log2_bits(v):
    b = _bits(v)
    return ((b >> 23) & 0xFF) - 127 + ((b & 0x7FFFFF) != 0).to(torch.int32)


def quant_fp8(x, block=32):
    """act_quant with a UE8M0 scale: (E4M3 code values FP32 [.., K], exponent int32 [.., K/32])."""
    shp = x.shape
    xb = x.reshape(*shp[:-1], shp[-1] // block, block)
    amax = torch.clamp_min(xb.abs().amax(-1), f32c(GV.FP8_AMAX_FLOOR))
    e = ceil_log2_bits(mul(amax, f32c(GV.FP8_MAX_INV)))
    v = (xb * pow2(-e)[..., None]).clamp(-448.0, 448.0)
    q = v.to(torch.float8_e4m3fn).to(F32)
    return q.reshape(shp), e


def qdq_fp8(x, block=32):
    q, e = quant_fp8(x, block)
    shp = x.shape
    return to_bf16((q.reshape(*shp[:-1], -1, block) * pow2(e)[..., None]).reshape(shp))


def _round_grid64(a, min_exp, mant_bits):
    """|a| (float64, exact) rounded to a grid with `mant_bits` mantissa bits and minimum
    exponent min_exp, half to even."""
    m, ex = torch.frexp(a)                       # a = m * 2^ex, m in [0.5, 1)
    e = torch.clamp_min(ex - 1, min_exp)
    step = pow2_64(e - mant_bits)
    return torch.round(a / step) * step


def qdq_fp4_e8m0(x, block=32):
    shp = x.shape
    xb = x.reshape(*shp[:-1], shp[-1] // block, block)
    amax = torch.clamp_min(xb.abs().amax(-1), f32c(GV.FP4_AMAX_FLOOR_E8M0))
    e = ceil_log2_bits(mul(amax, f32c(GV.FP4_MAX_INV)))
    v = (xb.double() * pow2_64(-e)[..., None]).clamp(-6.0, 6.0)
    q = torch.sign(v) * _round_grid64(v.abs(), 0, 1)
    return to_bf16((q * pow2_64(e)[..., None]).float()
                   .reshape(shp))


_MIDS = [float(m) for m in GV.E2M1_MIDPOINTS]
_E2M1 = [float(v) for v in GV.E2M1_VALUES]


def qdq_fp4_e4m3(x, block=16):
    shp = x.shape
    xb = x.reshape(*shp[:-1], shp[-1] // block, block)
    amax = torch.clamp_min(xb.abs().amax(-1), f32c(GV.FP4_AMAX_FLOOR_E4M3))
    s = _round_grid64(amax.double() / 6.0, -6, 3)
    a = xb.double().abs()
    code = torch.zeros(a.shape, dtype=torch.int64, device=x.device)
    for i, m in enumerate(_MIDS):
        t = (m * s)[..., None]
        code = torch.where((a > t) | ((a == t) & ((i + 1) % 2 == 0)), i + 1, code)
    vals = torch.tensor(_E2M1, dtype=torch.float64, device=x.device)
    q = torch.sign(xb.double()) * vals[code]
    return to_bf16((q * s[..., None]).float().reshape(shp))


# ======================================================================================
# checkpoint access
# ======================================================================================
class Checkpoint:
    def __init__(self, snap):
        from safetensors import safe_open
        self.snap = Path(snap)
        idx = self.snap / "model.safetensors.index.json"
        if idx.exists():
            self.map = json.loads(idx.read_text())["weight_map"]
        else:
            f = next(self.snap.glob("*.safetensors")).name
            with safe_open(str(self.snap / f), framework="pt") as h:
                self.map = {k: f for k in h.keys()}
        self._open = {}
        self._safe_open = safe_open
        self._mm = {}

    def has(self, name):
        return name in self.map

    def get(self, name):
        f = self.map[name]
        if f not in self._open:
            self._open[f] = self._safe_open(str(self.snap / f), framework="pt", device="cpu")
        return self._open[f].get_tensor(name)

    def _raw(self, name):
        """(mmap, dtype, shape, byte offset) of a tensor, for random row access."""
        f = self.snap / self.map[name]
        if f not in self._mm:
            fh = open(os.path.realpath(f), "rb")
            n = struct.unpack("<Q", fh.read(8))[0]
            header = json.loads(fh.read(n))
            mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                mm.madvise(mmap.MADV_RANDOM)
            except Exception:
                pass
            self._mm[f] = (fh, mm, header, 8 + n)
        fh, mm, header, base = self._mm[f]
        meta = header[name]
        return mm, meta["dtype"], meta["shape"], base + meta["data_offsets"][0]

    def rows_u8(self, name, ids):
        """rows `ids` (np int64, any order) of a 1-byte-per-element 2-D tensor, as uint8 [len, cols]."""
        mm, dt, shape, off = self._raw(name)
        arr = np.frombuffer(mm, dtype=np.uint8, count=shape[0] * shape[1], offset=off).reshape(shape)
        uniq, inv = np.unique(ids, return_inverse=True)
        return arr[uniq][inv]


def e8m0_exp(t):
    """UE8M0 scale tensor -> int32 exponent."""
    return t.view(torch.uint8).to(torch.int32) - 127


_FP4_TABLE = torch.tensor([0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0])


def fp4_values(packed):
    """packed E2M1 (int8 / float4_e2m1fn_x2 [N, K/2], low nibble first) -> values [N, K] FP32."""
    b = packed.view(torch.uint8).to(torch.int32)
    return torch.stack([e2m1_decode(b & 15), e2m1_decode(b >> 4)], -1).reshape(b.shape[0], b.shape[1] * 2)


def e2m1_decode(nib):
    """E2M1 nibble codes (int tensor) -> FP32 values."""
    c = (nib & 7).to(F32)
    mag = torch.where(c < 4, c * 0.5, torch.where(c == 7, torch.full_like(c, 6.0), c - 2.0))
    return torch.where(nib >= 8, -mag, mag)


class QW:
    """A quantised weight, K-major: fmt 0 code values [K, N], 1 E4M3 bytes [K, N], 2 packed E2M1
    bytes [K/2, N] (low nibble = even k); we [K/32, N] int32 exponents of the (row, 32-block) scales."""
    __slots__ = ("wT", "we", "N", "K", "fmt")

    def __init__(self, wT, we, N, K, fmt):
        self.wT, self.we, self.N, self.K, self.fmt = wT, we, N, K, fmt

    @staticmethod
    def from_values(codes, exps):
        N, K = codes.shape
        return QW(codes.to(BF16).t().contiguous(), exps.t().contiguous().to(torch.int32), N, K, 0)

    @staticmethod
    def from_fp8(w, scale):
        N, K = w.shape
        e = e8m0_exp(scale).repeat_interleave(32, 0)[:N]
        return QW(w.view(torch.uint8).t().contiguous(), e.t().contiguous(), N, K, 1)

    @staticmethod
    def from_fp4(w, scale):
        N, K = w.shape[0], w.shape[1] * 2
        return QW(w.view(torch.uint8).t().contiguous(), e8m0_exp(scale).t().contiguous(), N, K, 2)

    def values_T(self):
        if self.fmt == 0:
            return self.wT.to(F32)
        if self.fmt == 1:
            return self.wT.view(torch.float8_e4m3fn).to(F32)
        b = self.wT.to(torch.int32)
        return torch.stack([e2m1_decode(b & 15), e2m1_decode(b >> 4)], 1).reshape(self.K, self.N)

    def dense_T(self):
        """dequantised FP32 [K, N] (the a2 engine)."""
        return self.values_T() * pow2(self.we).repeat_interleave(32, 0)


# ======================================================================================
# model configuration and the shared (golden) tables
# ======================================================================================
class Cfg:
    def __init__(self, snap):
        c = json.loads((Path(snap) / "inference_config.json").read_text())
        self.c = c
        self.L = c["n_layers"]
        self.dim, self.hc = c["dim"], c["hc_mult"]
        self.heads, self.hd, self.rd = c["n_heads"], c["head_dim"], c["rope_head_dim"]
        self.eps, self.hc_eps = f32c(c["norm_eps"]), f32c(c["hc_eps"])
        self.ratio = list(c["compress_ratios"][:self.L])
        self.kv_src = list(c["kv_source_layers"])
        self.idx_src = list(c["index_source_layers"])
        self.cand_src = c["candidate_source_layer"]
        self.topk, self.cand_k, self.cand_b = c["index_topk"], c["candidate_topk_blocks"], c["candidate_block_size"]
        self.ih, self.ihd = c["index_n_heads"], c["index_head_dim"]
        self.groups, self.o_rank = c["o_groups"], c["o_lora_rank"]
        self.n_exp, self.k_exp = c["n_routed_experts"], c["n_activated_experts"]
        self.route_scale, self.limit = f32c(c["route_scale"]), f32c(c["swiglu_limit"])
        self.window = c["window_size"]
        self.attn_scale = f32c(self.hd ** -0.5)
        self.index_w_scale = f32c(self.ihd ** -0.5 * self.ih ** -0.5)
        self.engram_scale = f32c(self.dim ** -0.5)
        self.iters = c["hc_sinkhorn_iters"]
        self.engram_layers = list(c.get("engram_layer_ids", ()))
        self.vocab = c["vocab_size"]
        self.freqs_plain = GV.rope_freqs(self.rd, 0, c["rope_theta"], c["rope_factor"], c["beta_fast"], c["beta_slow"])
        self.freqs_yarn = GV.rope_freqs(self.rd, c["original_seq_len"], c["compress_rope_theta"], c["rope_factor"],
                                        c["beta_fast"], c["beta_slow"])
        self.kv_of = {L: max(s for s in self.kv_src if s <= L) for L in range(self.L) if self.ratio[L]}
        self.idx_of = {L: max(s for s in self.idx_src if s <= L) for L in range(self.L) if self.ratio[L]}
        self._cs = {}

    def rope_table(self, yarn, T, device):
        """cos, sin [T, rd/2] FP32 exactly as hdc_golden_v41.rope_cs."""
        key = (yarn, T, str(device))
        if key not in self._cs:
            freqs = self.freqs_yarn if yarn else self.freqs_plain
            ang = (np.arange(T, dtype=np.float32)[:, None] * freqs[None, :]).astype(np.float32)
            c = np.cos(ang.astype(np.float64)).astype(np.float32)
            s = np.sin(ang.astype(np.float64)).astype(np.float32)
            self._cs[key] = (torch.from_numpy(c).to(device), torch.from_numpy(s).to(device))
        return self._cs[key]


def rope_tail(v, c, s, inverse=False, exact=True):
    """rotate the last 2*len(c) elements of v's rows as adjacent pairs, stored BF16.  v [..., d];
    c, s broadcastable to v[..., ::2]'s rope part."""
    rd = 2 * c.shape[-1]
    v = v.clone()
    a, b = v[..., -rd::2], v[..., -rd + 1::2]
    if exact:
        if inverse:
            re, im = add(mul(a, c), mul(b, s)), add(mul(b, c), neg(mul(a, s)))
        else:
            re, im = add(mul(a, c), neg(mul(b, s))), add(mul(a, s), mul(b, c))
    else:
        if inverse:
            re, im = a * c + b * s, b * c - a * s
        else:
            re, im = a * c - b * s, a * s + b * c
    v[..., -rd::2] = to_bf16(re)
    v[..., -rd + 1::2] = to_bf16(im)
    return v


# ======================================================================================
# the contract (exact=True) and the independent torch (exact=False) engines
# ======================================================================================
class Engine:
    """One decoder layer for a chunk of sequences [B, T] at a time.  exact=True: the golden
    arithmetic (hdc_golden_v41, chunk8 + osm) emulated exactly; exact=False: the same release
    semantics (quantisation points, BF16 storage points) on cuBLAS/torch arithmetic."""

    def __init__(self, cfg: Cfg, exact: bool):
        self.cfg, self.exact = cfg, exact

    # ---- arithmetic selection -----------------------------------------------------
    def mv(self, w, x, w_kmajor=False):
        """x [M, K] (BF16 values) times BF16/FP32 weight -> FP32 [M, N]."""
        if self.exact:
            return csum_mm(x, w, w_kmajor=w_kmajor)[0]
        wf = w.to(F32)
        return x @ (wf if w_kmajor else wf.t())

    def linq(self, qw: QW, x):
        """FP8/FP4 linear of x [M, K] (BF16-valued FP32) -> BF16-valued FP32 [M, N]."""
        xq, xe = quant_fp8(x)
        if self.exact:
            outs = []
            step = max(1, (1 << 27) // max(1, qw.N * (-(-(qw.K // 32) // 8))))
            for m0 in range(0, x.shape[0], step):
                outs.append(tree_t(qdot_chunks(xq[m0:m0 + step], xe[m0:m0 + step], qw)))
            return to_bf16(torch.cat(outs, 0))
        xd = (xq.reshape(xq.shape[0], -1, 32) * pow2(xe)[..., None]).reshape(xq.shape)
        return to_bf16(xd @ qw.dense_T())

    def lin_bf16(self, w, x, w_kmajor=False):
        return to_bf16(self.mv(w, to_bf16(x), w_kmajor))

    def rowsum(self, v):
        return csum_t(v) if self.exact else v.sum(-1)

    def exp(self, x):
        return exp_g(x) if self.exact else torch.exp(x)

    def rsqrt(self, x):
        return rsqrt_g(x) if self.exact else torch.rsqrt(x)

    def sigmoid(self, x):
        return sigmoid_g(x) if self.exact else torch.sigmoid(x)

    def silu(self, x):
        return silu_g(x) if self.exact else Fn.silu(x)

    def softplus(self, x):
        return softplus_g(x) if self.exact else Fn.softplus(x)

    def rmsnorm(self, x, w):
        d = x.shape[-1]
        r = self.rsqrt(add(div(self.rowsum(mul(x, x)), float(d)), self.cfg.eps))
        return to_bf16(mul(w, mul(x, r[..., None])))

    def topk_sel(self, v, k):
        """indices of the k largest along the last axis: ties to the lower index (exact) or torch.topk."""
        if self.exact:
            return torch.sort(v, dim=-1, descending=True, stable=True).indices[..., :k]
        return v.topk(k, dim=-1).indices

    # ---- hyper-connections ------------------------------------------------------------
    def hc_mixes(self, h, W, which):
        """h [M, hc, dim] BF16-valued FP32 -> pre [M, hc], post [M, hc], comb [M, hc, hc]."""
        cfg = self.cfg
        fn, scale, base = W[f"hc_{which}_fn"], W[f"hc_{which}_scale"], W[f"hc_{which}_base"]
        flat = h.reshape(h.shape[0], -1)
        r = self.rsqrt(add(div(self.rowsum(mul(flat, flat)), float(flat.shape[1])), cfg.eps))
        if self.exact:
            mixes = mul(csum_mm(flat, fn, exact=False)[0], r[:, None])
        else:
            mixes = mul(flat @ fn.t(), r[:, None])
        hc = cfg.hc
        pre = add(self.sigmoid(add(mul(mixes[:, :hc], scale[0]), base[:hc])), cfg.hc_eps)
        post = mul(self.sigmoid(add(mul(mixes[:, hc:2 * hc], scale[1]), base[hc:2 * hc])), 2.0)
        comb = add(mul(mixes[:, 2 * hc:], scale[2]), base[2 * hc:]).reshape(-1, hc, hc)
        m = comb.amax(-1, keepdim=True)
        e = self.exp(add(comb, neg(m)))

        def seq(v, dim):
            parts = v.unbind(dim)
            acc = parts[0]
            for p in parts[1:]:
                acc = add(acc, p)
            return acc

        rs = seq(e, 2)
        comb = add(div(e, rs[:, :, None]), cfg.hc_eps)

        def cols(cm):
            return div(cm, add(seq(cm, 1), cfg.hc_eps)[:, None, :])

        def rows(cm):
            return div(cm, add(seq(cm, 2), cfg.hc_eps)[:, :, None])

        comb = cols(comb)
        for _ in range(cfg.iters - 1):
            comb = cols(rows(comb))
        return pre, post, comb

    def hc_pre(self, h, pre):
        acc = mul(pre[:, 0, None], h[:, 0])
        for j in range(1, self.cfg.hc):
            acc = add(acc, mul(pre[:, j, None], h[:, j]))
        return to_bf16(acc)

    def hc_post(self, y, res, post, comb):
        outs = []
        for k in range(self.cfg.hc):
            mix = mul(comb[:, 0, k, None], res[:, 0])
            for j in range(1, self.cfg.hc):
                mix = add(mix, mul(comb[:, j, k, None], res[:, j]))
            outs.append(add(mul(post[:, k, None], y), mix))
        return to_bf16(torch.stack(outs, 1))

    # ---- Engram -----------------------------------------------------------------------
    def engram(self, h, W, rows):
        """h [M, hc, dim]; rows [M, n_cols * head_dim] BF16 values."""
        cfg = self.cfg
        kv = self.linq(W["engram.wkv"], rows)
        key = kv[:, :cfg.hc * cfg.dim].reshape(-1, cfg.hc, cfg.dim)
        value = kv[:, cfg.hc * cfg.dim:]
        wgt = mul(W["engram.q_weight"], W["engram.k_weight"])
        n = float(cfg.dim)
        rstd = mul(self.rsqrt(add(div(self.rowsum(mul(h, h)), n), cfg.eps)),
                   self.rsqrt(add(div(self.rowsum(mul(key, key)), n), cfg.eps)))
        dot = mul(mul(self.rowsum(mul(mul(h, wgt[None]), key)), rstd), cfg.engram_scale)
        if self.exact:
            mag = sqrt_g(torch.clamp_min(dot.abs(), f32c(1e-6)))
        else:
            mag = torch.sqrt(torch.clamp_min(dot.abs(), 1e-6))
        gate = self.sigmoid(torch.where(dot < 0, neg(mag), mag))
        return to_bf16(add(h, mul(gate[..., None], value[:, None, :])))

    # ---- attention ----------------------------------------------------------------------
    def attention(self, L, W, x, qr, st, T, B, trace):
        """x [B*T, dim] BF16 values (attn-normed); qr [B*T, q_lora].  st: this chunk's shared
        state (per sequence lists).  Returns the attention output [B*T, dim]."""
        cfg, dev = self.cfg, x.device
        yarn = cfg.ratio[L] > 0
        c, s = cfg.rope_table(yarn, T, dev)
        pos = torch.arange(T, device=dev)
        q = self.linq(W["attn.wq_b"], qr).reshape(B, T, cfg.heads, cfg.hd)
        q = rope_tail(q, c[None, :, None, :], s[None, :, None, :], exact=self.exact)
        kv = self.rmsnorm(self.linq(W["attn.wkv"], x), W["attn.kv_norm"]).reshape(B, T, cfg.hd)
        kv = qdq_fp8(rope_tail(kv, c[None], s[None], exact=self.exact))
        if yarn:
            src = cfg.kv_of[L]
            r = cfg.ratio[L]
            if L == src:
                self.compress(L, W, x.reshape(B, T, -1), st, T, B)
            if L == cfg.idx_of[L]:
                st["sel"] = self.indexer(L, W, x.reshape(B, T, -1), qr.reshape(B, T, -1), st, T, B, trace)
            ckv = st["ckv"][src]
        selv = torch.stack(st["sel"]).reshape(B * T, -1) if yarn else None
        o = self.attend_all(L, W, q.reshape(B * T, cfg.heads, cfg.hd), kv, ckv if yarn else None, selv, c, s, T, B)
        og = o.reshape(B * T, cfg.groups, -1)
        wa = W["attn.wo_a"]                                            # [groups, rank, K] BF16
        if self.exact:
            zz = csum_mm(og.transpose(0, 1), W["attn.wo_aT"], w_kmajor=True)   # [groups, M, rank]
            zz = zz.transpose(0, 1)
        else:
            zz = torch.einsum("mgk,grk->mgr", og, wa.to(F32))
        zz = to_bf16(zz.reshape(B * T, -1))
        return self.linq(W["attn.wo_b"], zz)

    def compress(self, L, W, x, st, T, B):
        """compressed KV rows and index keys of source layer L for every complete group."""
        cfg = self.cfg
        r = cfg.ratio[L]
        ng = T // r
        xf = x.reshape(B * T, -1)
        if r == 1:
            lat = self.rmsnorm(self.lin_bf16(W["attn.compressor.wkv"], xf), W["attn.compressor.norm"])
            lat = lat.reshape(B, T, -1)
        else:
            both = self.mv(W["attn.compressor.wkvgate"], to_bf16(xf))       # FP32 [B*T, 2*hd]
            kvp, scp = both[:, :cfg.hd].reshape(B, T, -1), both[:, cfg.hd:].reshape(B, T, -1)
            kvp = kvp[:, :ng * r].reshape(B, ng, r, -1)
            scp = scp[:, :ng * r].reshape(B, ng, r, -1)
            m = scp.amax(2, keepdim=True)
            e = self.exp(add(scp, neg(m)))
            den = e[:, :, 0]
            for i in range(1, r):
                den = add(den, e[:, :, i])
            p = div(e, den[:, :, None])
            pooled = mul(kvp[:, :, 0], p[:, :, 0])
            for i in range(1, r):
                pooled = add(pooled, mul(kvp[:, :, i], p[:, :, i]))
            lat = self.rmsnorm(to_bf16(pooled), W["attn.compressor.norm"])
        lat = lat[:, :ng]                                                  # [B, ng, hd]
        cy, sy = cfg.rope_table(True, T, x.device)
        gpos = torch.arange(ng, device=x.device) * r
        gc, gs = cy[gpos][None], sy[gpos][None]
        k = self.rmsnorm(self.lin_bf16(W["attn.indexer.wk"], lat.reshape(B * ng, -1)), W["attn.indexer.k_norm"])
        ik = qdq_fp4_e8m0(rope_tail(k.reshape(B, ng, -1), gc, gs, exact=self.exact))
        ckv = qdq_fp4_e4m3(rope_tail(lat, gc, gs, exact=self.exact), 16)
        assert torch.equal(to_bf16(ckv), ckv) and torch.equal(to_bf16(ik), ik)
        st["ckv"][L] = ckv
        st["ik"][L] = ik

    def indexer(self, L, W, x, qr, st, T, B, trace):
        """per sequence, per query: the selected compressed positions, ascending, -1 padded [T, topk]."""
        cfg, dev = self.cfg, x.device
        r, src = cfg.ratio[L], cfg.kv_of[L]
        cy, sy = cfg.rope_table(True, T, dev)
        q = self.linq(W["attn.indexer.wq_b"], qr.reshape(B * T, -1)).reshape(B, T, cfg.ih, cfg.ihd)
        q = qdq_fp4_e8m0(rope_tail(q, cy[None, :, None], sy[None, :, None], exact=self.exact))
        wts = to_bf16(mul(self.lin_bf16(W["attn.indexer.weights_proj"], x.reshape(B * T, -1)), cfg.index_w_scale))
        wts = wts.reshape(B, T, cfg.ih)
        nvis = (torch.arange(T, device=dev) + 1) // r                        # visible groups per query
        k = min(cfg.topk, T // r)
        sels = []
        for bi in range(B):
            keys = st["ik"][src][bi]                                        # [ng, ihd]
            ng = keys.shape[0]
            sel_rows = []
            QC = max(1, (1 << 26) // max(1, cfg.ih * ng))
            for t0 in range(0, T, QC):
                qq = q[bi, t0:t0 + QC]                                      # [Q, ih, ihd]
                if self.exact:
                    # dots_q4: each 32-block dot of FP4 x FP4 dequantised values is exact in FP32 (every
                    # product is a small integer times the two blocks' common power of two), so the
                    # cuBLAS FP32 GEMM of one block is the exact block dot; blocks by csum (<= 8 terms:
                    # sequential from +0)
                    acc = torch.zeros(qq.shape[0], cfg.ih, ng, device=dev)
                    for b0 in range(0, cfg.ihd, 32):
                        blk = torch.einsum("qhd,nd->qhn", qq[..., b0:b0 + 32], keys[:, b0:b0 + 32])
                        acc = add(acc, blk)
                    score = to_bf16(acc)
                else:
                    score = to_bf16(torch.einsum("qhd,nd->qhn", qq, keys))
                terms = to_bf16(mul(torch.clamp_min(score, 0.0), wts[bi, t0:t0 + QC, :, None]))
                sc = to_bf16(self.rowsum(terms.transpose(1, 2)))            # [Q, ng]
                vis = torch.arange(ng, device=dev)[None, :] < nvis[t0:t0 + QC, None]
                sc = torch.where(vis, sc, torch.full_like(sc, -math.inf))
                if L == cfg.cand_src:
                    st["cand"][bi][t0:t0 + QC] = self.candidate_blocks(sc, nvis[t0:t0 + QC])
                elif 0 <= cfg.cand_src < L:
                    sc = torch.where(st["cand"][bi][t0:t0 + QC, :ng], sc, torch.full_like(sc, -math.inf))
                if k > 0:
                    idx = self.topk_sel(sc, k)
                    kq = torch.clamp(nvis[t0:t0 + QC], max=cfg.topk)[:, None]
                    idx = torch.where(torch.arange(k, device=dev)[None, :] < kq, idx, torch.full_like(idx, 1 << 30))
                    idx = torch.sort(idx, -1).values
                    idx = torch.where(idx == (1 << 30), torch.full_like(idx, -1), idx)
                else:
                    idx = torch.empty(qq.shape[0], 0, dtype=torch.int64, device=dev)
                sel_rows.append(idx)
            sels.append(torch.cat(sel_rows, 0))
        if trace is not None:
            trace["index"] = sels
        return sels

    def candidate_blocks(self, sc, nvis):
        """level one: block max, pin the block of the newest position, keep the top blocks."""
        cfg = self.cfg
        b = cfg.cand_b
        n = sc.shape[1]
        nb = -(-n // b)
        pad = torch.full((sc.shape[0], nb * b - n), -math.inf, device=sc.device)
        bs = torch.cat([sc, pad], 1).reshape(sc.shape[0], nb, b).amax(-1)
        last = (nvis - 1) // b
        bs = torch.where(torch.arange(nb, device=sc.device)[None, :] == last[:, None], math.inf, bs)
        kk = min(cfg.cand_k, nb)
        top = self.topk_sel(bs, kk)
        keep = torch.zeros_like(bs, dtype=torch.bool)
        keep.scatter_(1, top, bs.gather(1, top) > -math.inf)
        return keep.repeat_interleave(b, 1)[:, :n]

    def attend_all(self, L, W, q, kv, ckv, sel, c, s, T, B):
        """every query of a chunk: q [B*T, heads, hd] over its own sequence's window rows (kv
        [B, T, hd]) and its selected compressed rows (ckv [B, ng, hd], sel [B*T, nsel] -1 padded);
        returns o [B*T, heads, hd] (BF16 values, inverse RoPE applied)."""
        cfg, dev = self.cfg, q.device
        win_n = cfg.window
        nsel = sel.shape[1] if sel is not None else 0
        ng = ckv.shape[1] if ckv is not None else 0
        stride = T + ng
        tab = kv.reshape(B * T, -1) if ckv is None else torch.cat([kv, ckv], 1).reshape(B * stride, -1)
        zero_row = tab.shape[0]
        tab = torch.cat([tab, tab.new_zeros(1, tab.shape[1])], 0)
        sink = W["attn.attn_sink"]
        QC = 512
        outs = []
        n = B * T
        for t0 in range(0, n, QC):
            t1 = min(n, t0 + QC)
            ii = torch.arange(t0, t1, device=dev)
            p = ii % T
            boff = (ii // T) * stride
            Q = t1 - t0
            win = torch.clamp(p + 1, max=win_n)                              # [Q]
            w_idx = torch.arange(win_n, device=dev)[None, :]                 # window row w (0 = oldest)
            w_valid = w_idx < win[:, None]
            w_pos = p[:, None] - win[:, None] + 1 + w_idx + boff[:, None]
            if self.exact:
                slot = win_n - win[:, None] + w_idx
                wblk = slot // 64
                first = torch.clamp_min(win_n - win[:, None], 0)
                wpos_in = slot - torch.maximum(wblk * 64, first)
            nblk = (win_n // 64 if self.exact else 1) + (-(-nsel // 64) if self.exact else (1 if nsel else 0))
            nblk = max(nblk, 1)
            width = 64 if self.exact else win_n + nsel
            IDX = torch.full((Q, nblk, width), zero_row, dtype=torch.int64, device=dev)
            VAL = torch.zeros((Q, nblk, width), dtype=torch.bool, device=dev)
            if self.exact:
                bi_ = wblk.expand(Q, win_n)[w_valid]
                pi_ = wpos_in.expand(Q, win_n)[w_valid]
                qi_ = torch.arange(Q, device=dev)[:, None].expand(Q, win_n)[w_valid]
                IDX[qi_, bi_, pi_] = w_pos[w_valid]
                VAL[qi_, bi_, pi_] = True
            else:
                IDX[:, 0, :win_n] = torch.where(w_valid, w_pos, zero_row)
                VAL[:, 0, :win_n] = w_valid
            if nsel:
                sq = sel[t0:t1]                                               # [Q, nsel] (-1 pads)
                sv = sq >= 0
                srow = torch.where(sv, sq + T + boff[:, None], torch.full_like(sq, zero_row))
                if self.exact:
                    j = torch.arange(nsel, device=dev)
                    b0 = win_n // 64
                    sb = (b0 + j // 64)[None, :].expand(Q, nsel)
                    sp = (j % 64)[None, :].expand(Q, nsel)
                    qi = torch.arange(Q, device=dev)[:, None].expand(Q, nsel)
                    IDX[qi[sv], sb[sv], sp[sv]] = srow[sv]
                    VAL[qi[sv], sb[sv], sp[sv]] = True
                else:
                    IDX[:, 0, win_n:] = srow
                    VAL[:, 0, win_n:] = sv
            rows = tab[IDX.reshape(Q, -1)].to(BF16)                           # [Q, R, hd] BF16 values
            qq = q[t0:t1]                                                     # [Q, heads, hd]
            if self.exact:
                sc = csum_mm(qq.to(BF16).transpose(1, 2).contiguous(), rows.transpose(1, 2).contiguous(),
                             x_kmajor=True, w_kmajor=True)                   # [Q, heads, R]
                sc = mul(sc, cfg.attn_scale).reshape(Q, cfg.heads, nblk, 64)
                m = den = acc = None
                have = torch.zeros(Q, dtype=torch.bool, device=dev)
                rowsb = rows.reshape(Q, nblk, 64, -1)
                for bk in range(nblk):
                    v = VAL[:, bk]                                            # [Q, 64]
                    ne = v.any(-1)
                    if not bool(ne.any()):
                        continue
                    sb_ = sc[:, :, bk]
                    mblk = torch.where(v[:, None, :], sb_, torch.full_like(sb_, -math.inf)).amax(-1)
                    mb = mblk if m is None else torch.where(have[:, None], torch.maximum(m, mblk), mblk)
                    e = exp_g(add(sb_, neg(mb[..., None])))
                    e = torch.where(v[:, None, :], e, torch.zeros_like(e))
                    pv = csum_mm(to_bf16(e).to(BF16).transpose(1, 2).contiguous(), rowsb[:, bk].contiguous(),
                                 x_kmajor=True, w_kmajor=True)                 # [Q, heads, hd]
                    es = csum_t(e)
                    if m is None:
                        den_n, acc_n = es, pv
                    else:
                        rr = exp_g(add(m, neg(mb)))
                        den_n = torch.where(have[:, None], add(mul(den, rr), es), es)
                        acc_n = torch.where(have[:, None, None], add(mul(acc, rr[..., None]), pv), pv)
                    if m is None:
                        den, acc, m = den_n, acc_n, mb
                    else:   # a block empty for a query leaves its running state untouched
                        den = torch.where(ne[:, None], den_n, den)
                        acc = torch.where(ne[:, None, None], acc_n, acc)
                        m = torch.where(ne[:, None], mb, m)
                    have = have | ne
                den = add(den, exp_g(add(sink[None, :], neg(m))))
                o = to_bf16(div(acc, den[..., None]))
            else:
                v = VAL.reshape(Q, -1)
                rowsf = rows.float()
                sc = torch.einsum("qhd,qrd->qhr", qq, rowsf) * cfg.attn_scale
                sc = torch.where(v[:, None, :], sc, torch.full_like(sc, -math.inf))
                m = sc.amax(-1)
                e = torch.exp(sc - m[..., None])
                den = e.sum(-1) + torch.exp(sink[None, :] - m)
                pv = torch.einsum("qhr,qrd->qhd", to_bf16(e), rowsf)
                o = to_bf16(pv / den[..., None])
            o = rope_tail(o, c[p][:, None, :], s[p][:, None, :], inverse=True, exact=self.exact)
            outs.append(o)
        return torch.cat(outs, 0)

    # ---- MoE ---------------------------------------------------------------------------
    def moe(self, W, experts, x, trace):
        """x [M, dim]; experts(i) -> (w1, w2, w3) QW of routed expert i."""
        cfg = self.cfg
        raw = self.mv(W["ffn.gateT"], x, w_kmajor=True)
        scores = sqrt_g(self.softplus(raw)) if self.exact else torch.sqrt(self.softplus(raw))
        biased = add(scores, W["ffn.gate.bias"][None])
        chosen = self.topk_sel(biased, cfg.k_exp)
        ids = torch.sort(chosen, -1).values                                  # experts run and sum in id order
        sel_scores = scores.gather(1, ids)
        total = sel_scores[:, 0]
        for j in range(1, cfg.k_exp):
            total = add(total, sel_scores[:, j])
        den = add(total, f32c(1e-20))
        wgt = mul(div(sel_scores, den[:, None]), cfg.route_scale)            # [M, k]
        y = torch.zeros_like(x)
        flat = ids.flatten()
        order = torch.argsort(flat, stable=True)
        counts = torch.bincount(flat, minlength=cfg.n_exp).tolist()
        o0 = 0
        for i in range(cfg.n_exp):                                           # ascending expert id
            if counts[i] == 0:
                continue
            seg = order[o0:o0 + counts[i]]
            o0 += counts[i]
            tok, slot = seg // cfg.k_exp, seg % cfg.k_exp
            out = self.expert(experts(i), x[tok], wgt[tok, slot][:, None])
            y[tok] = add(y[tok], out)
        y = add(y, self.expert(W["shared"], x, None))
        if trace is not None:
            trace["router"] = ids
        return to_bf16(y)

    def expert(self, ws, x, weight):
        w1, w2, w3 = ws
        g = self.linq(w1, x)
        u = self.linq(w3, x)
        u = torch.clamp(u, -self.cfg.limit, self.cfg.limit)
        g = torch.clamp_max(g, self.cfg.limit)
        a = mul(self.silu(g), u)
        if weight is not None:
            a = mul(weight, a)
        return self.linq(w2, to_bf16(a))

    # ---- one layer -----------------------------------------------------------------------
    def attn_half(self, L, W, h, pre, st, B, T, engram_rows=None, trace=None):
        """Engram, the attention sublayer and its hyper-connection post.  Returns (h_mid, a_pre)."""
        if engram_rows is not None:
            h = self.engram(h, W, engram_rows)
        res = h
        a_pre, a_post, a_comb = self.hc_mixes(h, W, "attn")
        x = self.rmsnorm(self.hc_pre(h, pre), W["attn_norm"])
        qr = self.rmsnorm(self.linq(W["attn.wq_a"], x), W["attn.q_norm"])
        y = self.attention(L, W, x, qr, st, T, B, trace)
        if trace is not None and trace.get("debug"):
            trace["attn_in"], trace["attn_out"] = x, y
        return self.hc_post(y, res, a_post, a_comb), a_pre

    def ffn_prep(self, W, h, a_pre):
        """per token: the FFN's hyper-connection mixes and its normed input."""
        f_pre, f_post, f_comb = self.hc_mixes(h, W, "ffn")
        x = self.rmsnorm(self.hc_pre(h, a_pre), W["ffn_norm"])
        return x, f_pre, f_post, f_comb

    def layer(self, L, W, experts, h, pre, st, B, T, engram_rows=None, trace=None):
        """h [B*T, hc, dim] BF16-valued FP32; pre [B*T, hc].  Returns (h, pre)."""
        h, a_pre = self.attn_half(L, W, h, pre, st, B, T, engram_rows, trace)
        x, f_pre, f_post, f_comb = self.ffn_prep(W, h, a_pre)
        y = self.moe(W, experts, x, trace)
        if trace is not None and trace.get("debug"):
            trace["ffn_in"], trace["ffn_out"] = x, y
        return self.hc_post(y, h, f_post, f_comb), f_pre

    def final(self, h, pre, W):
        """logits [M, vocab] FP32."""
        xf = self.rmsnorm(self.hc_pre(h, pre), W["norm"])
        if not self.exact:
            return xf @ W["head_f32"].t()
        return self.mv(W["headT"], xf, w_kmajor=True)


def new_state(cfg, B, T, device):
    return {"ckv": {}, "ik": {}, "sel": None,
            "cand": [torch.ones(T, max(1, T), dtype=torch.bool, device=device) for _ in range(B)]}


# ======================================================================================
# layer weights (shared by the vendor module and the engines)
# ======================================================================================
def contract_weights(cfg, blk, ck, L, device):
    """the engines' view of layer L's tensors (decoded codes, K-major copies)."""
    P = f"layers.{L}."
    W = {}
    at = blk.attn

    def qw(lin):
        if lin.weight.dtype == torch.float4_e2m1fn_x2:
            return QW.from_fp4(lin.weight.data, lin.scale.data)
        return QW.from_fp8(lin.weight.data, lin.scale.data)

    for k in ("wq_a", "wq_b", "wkv", "wo_b"):
        W[f"attn.{k}"] = qw(getattr(at, k))
    W["attn.q_norm"] = at.q_norm.weight.data.float()
    W["attn.kv_norm"] = at.kv_norm.weight.data.float()
    W["attn.attn_sink"] = at.attn_sink.data.float()
    wa = at.wo_a.weight.data.float().reshape(cfg.groups, cfg.o_rank, -1)
    W["attn.wo_a"] = wa
    W["attn.wo_aT"] = wa.to(BF16).transpose(1, 2).contiguous()
    if at.compressor is not None:
        cp = at.compressor
        W["attn.compressor.norm"] = cp.norm.weight.data.float()
        if cfg.ratio[L] == 1:
            W["attn.compressor.wkv"] = cp.wkv.weight.data.to(BF16)
        else:
            W["attn.compressor.wkvgate"] = torch.cat([cp.wkv.weight.data, cp.wgate.weight.data]).to(BF16)
    if at.indexer is not None:
        ix = at.indexer
        W["attn.indexer.wq_b"] = qw(ix.wq_b)
        W["attn.indexer.weights_proj"] = ix.weights_proj.weight.data.to(BF16)
        if ix.owns_k:
            W["attn.indexer.wk"] = ix.wk.weight.data.to(BF16)
            W["attn.indexer.k_norm"] = ix.k_norm.weight.data.float()
    W["attn_norm"] = blk.attn_norm.weight.data.float()
    W["ffn_norm"] = blk.ffn_norm.weight.data.float()
    for which in ("attn", "ffn"):
        W[f"hc_{which}_fn"] = getattr(blk, f"hc_{which}_fn").data.float()
        W[f"hc_{which}_scale"] = getattr(blk, f"hc_{which}_scale").data.float()
        W[f"hc_{which}_base"] = getattr(blk, f"hc_{which}_base").data.float()
    W["ffn.gateT"] = blk.ffn.gate.weight.data.to(BF16).t().contiguous()
    W["ffn.gate.bias"] = blk.ffn.gate.bias.data.float()
    se = blk.ffn.shared_experts
    W["shared"] = (qw(se.w1), qw(se.w2), qw(se.w3))
    if blk.engram is not None:
        W["engram.wkv"] = qw(blk.engram.wkv)
        W["engram.q_weight"] = blk.engram.q_weight.data.float()
        W["engram.k_weight"] = blk.engram.k_weight.data.float()

    cache = {}

    def experts(i):
        if i not in cache:
            ex = blk.ffn.experts[i]
            cache.clear()
            cache[i] = (qw(ex.w1), qw(ex.w2), qw(ex.w3))
        return cache[i]

    return W, experts


# ======================================================================================
# the vendor reference (mode a)
# ======================================================================================
class Vendor:
    def __init__(self, snap, max_batch, max_seq, device="cuda"):
        # the release's code (the reduced vehicle ships weights and configs only)
        inf = str(SNAPSHOT / "inference")
        if inf not in sys.path:
            sys.path.insert(0, inf)
        import model as VM  # the release's inference/model.py
        self.VM = VM
        VM.world_size, VM.rank = 1, 0
        VM.default_dtype = torch.float8_e4m3fn
        if not getattr(VM, "_opentallas_patched", False):   # once per process
            VM._opentallas_patched = True
            # The released fp4_gemm TileLang kernel is broken on this sm_120 GPU (NaN at the released
            # expert shape, rel. error 1.0 at the reduced one; also recorded by
            # tools/run_deepseek_v41_reduced_reference_oracle.py).  Replaced, as that oracle does, by
            # the same FP4 codes and E8M0 scales and the vendor's own FP8 activation quantisation,
            # dequantised exactly and multiplied by one cuBLAS FP32 GEMM, BF16 out.
            VM.fp4_gemm = _fp4_gemm_dequant
            # The released sparse_attn kernel keeps all heads' q and o in shared memory: at 64 heads x 512
            # it asks for 141,312 B, over sm_120's limit.  Heads are independent in it (one row max, sum
            # and accumulator per head), so it is called on groups of 16 heads -- its own minimum width
            # -- which is the same arithmetic per head.
            orig_sa = VM.sparse_attn

            def sparse_attn_grouped(q, kv, attn_sink, topk_idxs, softmax_scale, _orig=orig_sa):
                h = q.size(2)
                if h <= 16 or h * q.size(3) <= 16 * 1024:     # fits (the reduced vehicle): one call
                    return _orig(q, kv, attn_sink, topk_idxs, softmax_scale)
                return torch.cat([_orig(q[:, :, i:i + 16].contiguous(), kv, attn_sink[i:i + 16].contiguous(),
                                        topk_idxs, softmax_scale) for i in range(0, h, 16)], dim=2)

            VM.sparse_attn = sparse_attn_grouped
            # The released quantisation and FP8 GEMM kernels tile rows by 32 with no row bound: at a row
            # count that is not a multiple of 32 (a routed expert's tokens) they touch memory past the
            # tensor and the result becomes run-dependent (measured: the first MoE call differs from later
            # identical calls).  Every call is padded to a multiple of 32 rows and sliced back; rows are
            # independent in all three kernels, so the arithmetic of the real rows is unchanged.
            # The released act_quant / fp4_act_quant emit NaN FP8 codes on this GPU (1,426 of 2.6M codes
            # of layer 0's attention input on WikiText; tilelang 0.1.8 on sm_120): replaced by PyTorch
            # restatements of the kernels' own formulas (UE8M0 scale 2^ceil(log2(amax/max)); E4M3 scale
            # e4m3(amax/6) for compressed KV; clamp, round to nearest even, dequantise, BF16 out).
            VM.act_quant = _act_quant_ref
            VM.fp4_act_quant = _fp4_act_quant_ref
            # The released fp8_gemm returns NaN on this GPU at some released shapes (wo_b, K = 8,192, on
            # random input; wq_a inside a real prefill): replaced like fp4_gemm -- the same E4M3 codes and
            # 32x32 UE8M0 block scales and the vendor's activation quantisation, dequantised exactly, one
            # FP32 GEMM, BF16 out.
            VM.fp8_gemm = _fp8_gemm_dequant
        c = json.loads((Path(snap) / "inference_config.json").read_text())
        fields = {f.name for f in dataclasses.fields(VM.ModelArgs)}
        kw = {k: (tuple(v) if isinstance(v, list) else v) for k, v in c.items() if k in fields}
        kw.update(max_batch_size=max_batch, max_seq_len=max_seq, vision_n_layers=0, temperature=0)
        self.args = VM.ModelArgs(**kw)
        self.layout = VM.EngramLayout.from_args(self.args)
        self.device = device

    def hashes(self, tokenizer, ids_list):
        """engram hash ids per sequence: list of int64 [T, n_engram_layers, n_cols] (CPU)."""
        VM = self.VM
        from engram import NgramHashState
        if not hasattr(self, "_hs"):
            with torch.device("cpu"):
                args = dataclasses.replace(self.args, max_batch_size=1,
                                           max_seq_len=max(len(i) for i in ids_list))
                self._hs = NgramHashState(args, self.layout, tokenizer)
        out = []
        for ids in ids_list:
            if len(ids) > self._hs.cache.shape[1]:
                self._hs.cache = torch.empty(1, len(ids), dtype=torch.int64)
            out.append(self._hs(torch.tensor([ids], dtype=torch.int64), 0)[0].clone())
        return out

    def block(self, L, ck):
        VM = self.VM
        small = dataclasses.replace(self.layout, num_embeddings=tuple(1 for _ in self.layout.num_embeddings)) \
            if self.layout is not None else None
        prev = torch.get_default_dtype()
        torch.set_default_dtype(torch.bfloat16)
        try:
            with torch.device(self.device):
                blk = VM.Block(L, self.args, small)
        finally:
            torch.set_default_dtype(prev)
        P = f"layers.{L}."
        with torch.no_grad():
            for name, prm in blk.named_parameters():
                if name.startswith("engram.embed."):
                    continue
                key = P + name
                if not ck.has(key):
                    raise KeyError(key)
                t = ck.get(key)
                if name.endswith("attn.wo_a.weight"):
                    sc = ck.get(P + "attn.wo_a.scale").float()
                    ob, ib = t.shape[0] // sc.shape[0], t.shape[1] // sc.shape[1]
                    t = (t.float().unflatten(0, (-1, ob)).unflatten(-1, (-1, ib)) * sc[:, None, :, None]) \
                        .flatten(2, 3).flatten(0, 1).bfloat16()
                if prm.element_size() == 1:          # FP8 / E8M0 / packed FP4: copy the bytes
                    assert t.element_size() == 1 and t.shape == prm.shape, (key, t.shape, prm.shape)
                    prm.data.view(torch.uint8).copy_(t.view(torch.uint8))
                elif prm.dtype == t.dtype:
                    prm.data.copy_(t)
                else:
                    prm.data.copy_(t.to(prm.dtype))
        if blk.engram is not None:
            blk.engram.embed = _RowsEmbed()
        return blk

    def _ctx(self):
        vend = self

        class C:
            def __enter__(self):
                self.prev = torch.get_default_dtype()
                torch.set_default_dtype(torch.bfloat16)
                self.dev = torch.device(vend.device)
                self.dev.__enter__()
                self.inf = torch.inference_mode()
                self.inf.__enter__()

            def __exit__(self, *a):
                self.inf.__exit__(*a)
                self.dev.__exit__(*a)
                torch.set_default_dtype(self.prev)
        return C()

    def attn_half(self, blk, h, pre, shared, engram_rows=None, trace=None):
        """Block.forward's first half (engram, hc_mixes, hc_pre, attn_norm, attn, hc_post), exactly as
        the release writes it.  h [B, T, hc, dim] BF16; pre [B, T, hc].  Returns (h_mid, attn_pre)."""
        sa = self.VM.shared_attn
        for k in ("compress_kv", "index_k", "topk_idxs", "candidates"):
            setattr(sa, k, shared.get(k))
        with self._ctx():
            if blk.engram is not None:
                blk.engram.embed.rows = engram_rows
                h = blk.engram(h, torch.zeros(h.shape[0], h.shape[1], 1, dtype=torch.int64, device=h.device), None)
            residual = h
            attn_pre, attn_post, attn_comb = blk.hc_mixes(h, blk.hc_attn_fn, blk.hc_attn_scale, blk.hc_attn_base)
            x = blk.hc_pre(h, pre)
            x = blk.attn_norm(x)
            x = blk.attn(x, 0)
            h = blk.hc_post(x, residual, attn_post, attn_comb)
        if trace is not None and blk.attn.is_index_source:
            T = h.shape[1]
            idx = sa.topk_idxs
            if idx is not None and idx.numel():
                trace["index"] = [torch.where(i >= 0, i.long() - T, torch.full_like(i.long(), -1)) for i in idx]
        if blk.attn.is_kv_source:
            shared["compress_kv"] = sa.compress_kv.clone()
            shared["index_k"] = sa.index_k.clone() if sa.index_k is not None else None
        if blk.attn.is_index_source:
            shared["topk_idxs"] = sa.topk_idxs
        if blk.attn.indexer is not None and blk.attn.indexer.is_candidate_source:
            shared["candidates"] = sa.candidates
        return h, attn_pre

    def ffn_prep(self, blk, h, attn_pre):
        """h [1, M, hc, dim] BF16, attn_pre [1, M, hc]: (x, ffn_pre, ffn_post, ffn_comb)."""
        with self._ctx():
            ffn_pre, ffn_post, ffn_comb = blk.hc_mixes(h, blk.hc_ffn_fn, blk.hc_ffn_scale, blk.hc_ffn_base)
            x = blk.ffn_norm(blk.hc_pre(h, attn_pre))
        return x, ffn_pre, ffn_post, ffn_comb

    def moe(self, blk, x, trace=None):
        hooks = []
        if trace is not None:
            hooks.append(blk.ffn.gate.register_forward_hook(lambda m, i, o: trace.__setitem__("router", o[1])))
        try:
            with self._ctx():
                y = blk.ffn(x)
        finally:
            for hk in hooks:
                hk.remove()
        return y

    def ffn_post(self, blk, y, h, ffn_post, ffn_comb):
        with self._ctx():
            return blk.hc_post(y, h, ffn_post, ffn_comb)

    def run(self, blk, h, pre, shared, engram_rows=None, trace=None):
        """the whole block (Block.forward's two halves)."""
        h, a_pre = self.attn_half(blk, h, pre, shared, engram_rows, trace)
        x, f_pre, f_post, f_comb = self.ffn_prep(blk, h, a_pre)
        y = self.moe(blk, x, trace)
        return self.ffn_post(blk, y, h, f_post, f_comb), f_pre


def _pad_rows(x2, mult=32):
    pad = (-x2.shape[0]) % mult
    if pad:
        x2 = torch.cat([x2, x2.new_zeros((pad,) + tuple(x2.shape[1:]))], 0)
    return x2.contiguous()


def _row_padded_quant(orig):
    import inspect
    sig = inspect.signature(orig)

    def f(x, *args, **kw):
        bound = sig.bind(x, *args, **kw)
        bound.apply_defaults()
        inplace = bound.arguments["inplace"]
        N = x.size(-1)
        lead = x.shape[:-1]
        M = x.numel() // N
        xp = _pad_rows(x.reshape(M, N))
        bound.arguments["x"] = xp
        r = orig(*bound.args, **bound.kwargs)
        if inplace:
            x.copy_(xp[:M].view(x.shape))
            return x
        y, sc = r
        return y[:M].reshape(*lead, y.shape[-1]), sc[:M].reshape(*lead, sc.shape[-1])
    return f


def _row_padded_gemm(orig):
    def f(a, a_s, b, b_s, *args, **kw):
        K = a.size(-1)
        M = a.numel() // K
        c = orig(_pad_rows(a.reshape(M, K)), _pad_rows(a_s.reshape(M, -1)), b, b_s, *args, **kw)
        return c[:M].reshape(*a.shape[:-1], c.shape[-1])
    return f


def _act_quant_ref(x, block_size=128, scale_fmt=None, scale_dtype=torch.float32, inplace=False):
    assert scale_fmt is not None
    q, e = quant_fp8(x.float(), block_size)
    if inplace:
        shp = x.shape
        x.copy_((q.reshape(*shp[:-1], -1, block_size) * pow2(e)[..., None]).reshape(shp).to(x.dtype))
        return x
    return q.to(torch.float8_e4m3fn), pow2(e)


def _fp4_act_quant_ref(x, block_size=32, inplace=False, scale_dtype=torch.float8_e8m0fnu):
    assert inplace
    xf = x.float()
    shp = xf.shape
    xb = xf.reshape(*shp[:-1], shp[-1] // block_size, block_size)
    if scale_dtype == torch.float8_e4m3fn:
        amax = torch.clamp_min(xb.abs().amax(-1), f32c(6 * 2.0 ** -9))
        sc = (amax / 6.0).to(torch.float8_e4m3fn).float()
    else:
        amax = torch.clamp_min(xb.abs().amax(-1), f32c(6 * 2.0 ** -126))
        sc = pow2(ceil_log2_bits(amax * f32c(1.0 / 6.0)))
    v = (xb / sc[..., None]).clamp(-6.0, 6.0).double()
    qv = torch.sign(v) * _round_grid64(v.abs(), 0, 1)
    x.copy_((qv.float() * sc[..., None]).reshape(shp).to(x.dtype))
    return x


def _fp8_gemm_dequant(a, a_s, b, b_s, scale_dtype=None, block_size=32):
    K = a.size(-1)
    M = a.numel() // K
    N = b.shape[0]
    ad = (a.view(M, K // block_size, block_size).float() * a_s.view(M, -1).float()[..., None]).view(M, K)
    bs = b_s.float().repeat_interleave(block_size, 0)[:N].repeat_interleave(block_size, 1)[:, :K]
    bd = b.float() * bs
    return (ad @ bd.t()).to(torch.get_default_dtype()).view(*a.shape[:-1], N)


def _fp4_gemm_dequant(a, a_s, b, b_s, scale_dtype=None, act_block_size=32):
    """C = A_fp8 @ B_fp4^T with A's per-32 and B's per-32 E8M0 scales, via exact dequantisation."""
    K = a.size(-1)
    M = a.numel() // K
    ad = (a.view(M, K // act_block_size, act_block_size).float()
          * a_s.view(M, -1).float()[..., None]).view(M, K)
    bd = (fp4_values(b).view(b.shape[0], K // 32, 32) * b_s.float()[..., None]).view(b.shape[0], K)
    return (ad @ bd.t()).to(torch.get_default_dtype()).view(*a.shape[:-1], b.shape[0])


class _RowsEmbed(torch.nn.Module):
    """stands in for ParallelEngramEmbedding: returns the pre-gathered rows [B, T, n_cols, head_dim] BF16."""

    def __init__(self):
        super().__init__()
        self.rows = None

    def forward(self, indices):
        return self.rows


def engram_rows(ck, cfg, L, hash_ids, device):
    """dequantised Engram rows (BF16) [N, n_cols, head_dim] for hash ids [N, n_cols] (CPU int64)."""
    P = f"layers.{L}.engram.embed."
    ids = hash_ids.reshape(-1).numpy()
    codes = torch.from_numpy(ck.rows_u8(P + "weight", ids))
    sc = torch.from_numpy(ck.rows_u8(P + "scale", ids))
    hd = codes.shape[1]
    vals = codes.view(torch.float8_e4m3fn).to(device).float().reshape(len(ids), -1, 32)
    e = sc.to(device).to(torch.int32) - 127
    vals = (vals * pow2(e)[..., None]).reshape(len(ids), hd).to(BF16)
    return vals.reshape(*hash_ids.shape, hd)


# ======================================================================================
# evaluation data
# ======================================================================================
def tokenizer_for(snap):
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(str(snap))


def wikitext_windows(tok, T, n):
    """n non-overlapping windows of T tokens (BOS + T-1 text tokens), evenly spaced over the
    WikiText-2 raw test split joined with blank lines."""
    from datasets import load_dataset
    d = load_dataset("Salesforce/wikitext", "wikitext-2-raw-v1", split="test")
    ids = tok("\n\n".join(d["text"]), add_special_tokens=False).input_ids
    span = T - 1
    total = len(ids) // span
    starts = np.linspace(0, total - 1, n).round().astype(int) if n < total else np.arange(total)
    bos = tok.bos_token_id
    return [[bos] + ids[s * span:(s + 1) * span] for s in sorted(set(starts.tolist()))], len(ids)


def mmlu_items(tok, n, seed=0):
    from datasets import load_dataset
    d = load_dataset("cais/mmlu", "all", split="test")
    rng = np.random.default_rng(seed)
    idx = sorted(rng.choice(len(d), size=n, replace=False).tolist())
    letters = ["A", "B", "C", "D"]
    items = []
    for i in idx:
        it = d[int(i)]
        q = f"The following is a multiple choice question about {it['subject'].replace('_', ' ')}.\n\n{it['question']}\n"
        for L, c in zip(letters, it["choices"]):
            q += f"{L}. {c}\n"
        q += "Answer:"
        items.append({"ids": [tok.bos_token_id] + tok(q, add_special_tokens=False).input_ids,
                      "answer": int(it["answer"]), "index": int(i)})
    cand = [tok(" " + L, add_special_tokens=False).input_ids[-1] for L in letters]
    return items, cand


# ======================================================================================
# the layer-streamed driver
# ======================================================================================
MODE_SPEC = {
    "a": ("vendor", None),
    "a2": ("torch", None),
    "b": ("contract", None),
    "b_tf": ("contract", "a"),
    "a2_tf": ("torch", "a"),
}


def run(args):
    dev = torch.device("cuda")
    snap = Path(args.snapshot)
    cfg = Cfg(snap)
    if args.max_layers:
        cfg.L = min(cfg.L, args.max_layers)          # smoke/timing only: the head then reads layer L-1's output
    ck = Checkpoint(snap)
    tok = tokenizer_for(snap)
    seqs = []                                   # dicts: ids, kind, meta
    if args.windows:
        wins, ntok = wikitext_windows(tok, args.ctx, args.windows)
        for w, ids in enumerate(wins):
            seqs.append({"ids": ids, "kind": "wt", "w": w})
    cand = None
    if args.mmlu:
        items, cand = mmlu_items(tok, args.mmlu)
        for q, it in enumerate(items):
            seqs.append({"ids": it["ids"], "kind": "mmlu", "q": q, "answer": it["answer"], "index": it["index"]})
    # chunks: equal-length (right-padded) groups
    chunks = []
    wt = [s for s in seqs if s["kind"] == "wt"]
    for i in range(0, len(wt), args.batch):
        chunks.append(wt[i:i + args.batch])
    mm = sorted([s for s in seqs if s["kind"] == "mmlu"], key=lambda s: len(s["ids"]))
    tok_budget = args.batch * args.ctx
    i = 0
    while i < len(mm):
        j = i
        while j < len(mm) and (j - i + 1) * len(mm[j]["ids"]) <= tok_budget:
            j += 1
        j = max(j, i + 1)
        chunks.append(mm[i:j])
        i = j
    chunk_meta = []
    for c in chunks:
        Tm = max(len(s["ids"]) for s in c)
        for s in c:
            s["len"] = len(s["ids"])
        c_ids = torch.tensor([s["ids"] + [2] * (Tm - len(s["ids"])) for s in c], dtype=torch.int64)
        chunk_meta.append({"T": Tm, "B": len(c), "ids": c_ids, "seqs": c})
    max_T = max(cm["T"] for cm in chunk_meta)
    max_B = max(cm["B"] for cm in chunk_meta)
    vend = Vendor(snap, max_B, max_T)
    modes = args.modes.split(",")
    assert modes[0] == "a"
    eng = {"contract": Engine(cfg, True), "torch": Engine(cfg, False)}
    print(f"sequences {len(seqs)} in {len(chunk_meta)} chunks, max T {max_T}, modes {modes}", flush=True)

    # engram hashes (shared by every mode)
    hashes = None
    if cfg.engram_layers:
        for cm in chunk_meta:
            cm["hash"] = torch.stack(vend.hashes(tok, [row.tolist() for row in cm["ids"]]))   # [B, T, nl, cols]

    # ---- state.  Hidden states live in file-backed tensors on scratch disk (never in host RAM:
    # 57K tokens x 40 KB x modes does not fit the host budget), double-buffered by layer parity so a
    # killed run resumes at its last completed layer.  Small per-chunk attention state (vendor
    # shared_attn fields, the engines' compressed KV / index keys / selections) is kept compact in RAM
    # and checkpointed with the per-mode hyper-connection mix after every layer.
    offs, ntok = [], 0
    for cm in chunk_meta:
        offs.append(ntok)
        ntok += cm["B"] * cm["T"]
    work = Path(args.work)
    work.mkdir(parents=True, exist_ok=True)
    full_modes = [m for m in modes if MODE_SPEC[m][1] is None]
    nbytes = ntok * cfg.hc * cfg.dim * 2
    H = {}
    for m in full_modes:
        for par in (0, 1):
            f = work / f"h_{m}_{par}.bin"
            if not f.exists() or f.stat().st_size != nbytes:
                with open(f, "wb") as fh:
                    fh.truncate(nbytes)
            H[(m, par)] = torch.from_file(str(f), shared=True, size=ntok * cfg.hc * cfg.dim,
                                          dtype=BF16).view(ntok, cfg.hc, cfg.dim)
    ckpt = work / "checkpoint.pt"
    sig = {"ids": [cm["ids"].tolist() for cm in chunk_meta], "modes": modes, "tf_chunks": args.tf_chunks}
    start = 0
    if args.resume and ckpt.exists():
        saved = torch.load(ckpt, weights_only=False)
        assert saved["sig"] == sig, "checkpoint belongs to another evaluation set"
        start, pre_state, small, stats = saved["layer_done"] + 1, saved["pre"], saved["small"], saved["stats"]
        print(f"resuming after layer {start - 1}", flush=True)
    else:
        embed = ck.get("embed.weight").to(dev)
        pre_state = {}
        for m in full_modes:
            for ci, cm in enumerate(chunk_meta):
                n = cm["B"] * cm["T"]
                h0 = embed[cm["ids"].to(dev)].reshape(n, 1, cfg.dim).repeat(1, cfg.hc, 1)
                H[(m, 0)][offs[ci]:offs[ci] + n] = h0.cpu()
            pre_state[m] = torch.zeros(ntok, cfg.hc)
            pre_state[m][:, 0] = 1.0
        small = {(m, ci): {"sh": {}, "st": _st_to(new_state(cfg, cm["B"], cm["T"], "cpu"), "cpu")}
                 for m in modes for ci, cm in enumerate(chunk_meta)}
        stats = {"layers": []}
        del embed
    torch.cuda.empty_cache()

    def active(m, ci):
        return MODE_SPEC[m][1] is None or ci < args.tf_chunks

    t_start = time.time()
    valid = []                                         # per chunk: real (unpadded) positions [B*T]
    for cm in chunk_meta:
        v = torch.zeros(cm["B"], cm["T"], dtype=torch.bool)
        for bi, s_ in enumerate(cm["seqs"]):
            v[bi, :s_["len"]] = True
        valid.append(v.reshape(-1))
    for L in range(start, cfg.L):
        pin, pout = L % 2, 1 - L % 2
        tl0 = time.time()
        blk = vend.block(L, ck)
        W, experts = contract_weights(cfg, blk, ck, L, dev)
        erows = {}
        if L in cfg.engram_layers:
            li = cfg.engram_layers.index(L)
            for ci, cm in enumerate(chunk_meta):
                erows[ci] = engram_rows(ck, cfg, L, cm["hash"][:, :, li, :], dev).cpu()   # [B, T, cols, hd]
        tload = time.time() - tl0
        lst = {"layer": L, "load_s": tload, "mode_s": {m: 0.0 for m in modes}, "attn_s": {m: 0.0 for m in modes},
               "router": {}, "index": {}, "hidden_rel_rms": {}}
        a_index, router_a = {}, None
        new_pre = {}
        for m in modes:
            kind, src = MODE_SPEC[m]
            srcm = "a" if src == "a" else m
            cis = [ci for ci in range(len(chunk_meta)) if active(m, ci)]
            A = {"router_tok": 0, "router_any": 0, "router_changed": 0, "idx_q": 0, "idx_any": 0,
                 "idx_diff": 0, "idx_tot": 0, "dh2": 0.0, "h2": 0.0}
            t0 = time.time()
            # ---- phase A: Engram + attention half, per chunk (sequences) ----
            mids, aps = [], []
            for ci in cis:
                cm = chunk_meta[ci]
                B, T = cm["B"], cm["T"]
                n = B * T
                h = H[(srcm, pin)][offs[ci]:offs[ci] + n].to(dev)
                pre = pre_state[srcm][offs[ci]:offs[ci] + n].to(dev)
                er = erows[ci].to(dev) if ci in erows else None
                S = small[(m, ci)]
                tr = {}
                if kind == "vendor":
                    sh = {k: (v.to(dev) if torch.is_tensor(v) else v) for k, v in S["sh"].items()}
                    hm, ap = vend.attn_half(blk, h.view(B, T, cfg.hc, cfg.dim), pre.view(B, T, cfg.hc), sh, er, tr)
                    S["sh"] = {k: (v.cpu() if torch.is_tensor(v) else v) for k, v in sh.items()}
                    hm, ap = hm.reshape(n, cfg.hc, cfg.dim), ap.reshape(n, cfg.hc)
                else:
                    st = _st_to(S["st"], dev)
                    rows = er.reshape(n, -1).float() if er is not None else None
                    hm, ap = eng[kind].attn_half(L, W, h.float(), pre.float(), st, B, T, rows, tr)
                    S["st"] = _st_to(st, "cpu")
                mids.append(hm.to(BF16))
                aps.append(ap.float())
                if "index" in tr:
                    sel = [x.to(torch.int32).cpu() for x in tr["index"]]
                    if m == "a":
                        a_index[ci] = sel
                    else:
                        for bi, s_ in enumerate(cm["seqs"]):
                            d, tot, anyd = _sel_diff(a_index[ci][bi][: s_["len"]], sel[bi][: s_["len"]])
                            A["idx_q"] += s_["len"]
                            A["idx_any"] += anyd
                            A["idx_diff"] += d
                            A["idx_tot"] += tot
                del h, pre, er, tr
            torch.cuda.synchronize()
            lst["attn_s"][m] = time.time() - t0
            # ---- phase B: the FFN half over every token at once (one expert sweep) ----
            xs, fps, fpo, fco = [], [], [], []
            for j, ci in enumerate(cis):
                if kind == "vendor":
                    x, fp, fpost, fcomb = vend.ffn_prep(blk, mids[j][None], aps[j][None])
                    xs.append(x[0])
                    fps.append(fp[0])
                    fpo.append(fpost[0])
                    fco.append(fcomb[0])
                else:
                    x, fp, fpost, fcomb = eng[kind].ffn_prep(W, mids[j].float(), aps[j])
                    xs.append(x.to(BF16))
                    fps.append(fp)
                    fpo.append(fpost)
                    fco.append(fcomb)
            X = torch.cat(xs)
            del xs
            tr = {}
            Y = vend.moe(blk, X[None], tr)[0] if kind == "vendor" else eng[kind].moe(W, experts, X.float(), tr)
            del X
            ids = tr["router"].reshape(-1, cfg.k_exp)
            o0 = 0
            vflat = torch.cat([valid[ci] for ci in cis]).to(dev)
            if src is None:
                new_pre[m] = pre_state[m].clone()
            for j, ci in enumerate(cis):
                n = chunk_meta[ci]["B"] * chunk_meta[ci]["T"]
                if kind == "vendor":
                    ho = vend.ffn_post(blk, Y[o0:o0 + n][None], mids[j][None], fpo[j][None], fco[j][None])[0]
                else:
                    ho = eng[kind].hc_post(Y[o0:o0 + n].float(), mids[j].float(), fpo[j], fco[j])
                ho = ho.to(BF16)
                if src is None:
                    H[(m, pout)][offs[ci]:offs[ci] + n] = ho.cpu()
                    new_pre[m][offs[ci]:offs[ci] + n] = fps[j].float().cpu()
                if m != "a":
                    v = valid[ci].to(dev)
                    ha = H[("a", pout)][offs[ci]:offs[ci] + n].to(dev).float()
                    A["dh2"] += float(((ho.float() - ha) ** 2)[v].sum())
                    A["h2"] += float((ha ** 2)[v].sum())
                o0 += n
            del Y, mids, aps, fps, fpo, fco
            if m == "a":
                router_a = ids
            else:
                sa_ = torch.sort(router_a[:ids.shape[0]], -1).values      # active chunks are a prefix
                sm_ = torch.sort(ids.to(sa_.dtype), -1).values
                diff = _set_diff(sa_, sm_)
                A["router_tok"] += int(vflat.sum())
                A["router_any"] += int(((diff > 0) & vflat).sum())
                A["router_changed"] += int(diff[vflat].sum())
                lst["router"][m] = {"tokens": A["router_tok"], "tokens_with_flip": A["router_any"],
                                    "flip_rate": A["router_any"] / max(1, A["router_tok"]),
                                    "experts_changed_per_token": A["router_changed"] / max(1, A["router_tok"])}
                if A["idx_q"]:
                    lst["index"][m] = {"queries": A["idx_q"], "queries_with_diff": A["idx_any"],
                                       "query_flip_rate": A["idx_any"] / A["idx_q"],
                                       "selected_positions_changed_frac": A["idx_diff"] / max(1, A["idx_tot"])}
                lst["hidden_rel_rms"][m] = math.sqrt(A["dh2"] / max(A["h2"], 1e-30))
            torch.cuda.synchronize()
            lst["mode_s"][m] = time.time() - t0
            torch.cuda.empty_cache()
        pre_state.update(new_pre)
        lst["rss_anon_gb"], lst["rss_file_gb"], lst["peak_rss_gb"] = _rss_gb()
        lst["gpu_peak_gb"] = torch.cuda.max_memory_allocated() / 1e9
        stats["layers"].append(lst)
        print(f"layer {L}: load {tload:.1f}s " + " ".join(f"{m} {lst['mode_s'][m]:.1f}s ({lst['attn_s'][m]:.1f})"
                                                        for m in modes) +
              " | router flips " + " ".join(f"{m} {lst['router'][m]['flip_rate']:.4f}" for m in lst["router"]) +
              " | index " + " ".join(f"{m} {lst['index'][m]['query_flip_rate']:.4f}" for m in lst["index"]) +
              " | rel rms " + " ".join(f"{m} {v:.2e}" for m, v in lst["hidden_rel_rms"].items()) +
              f" | rss anon {lst['rss_anon_gb']:.1f} file {lst['rss_file_gb']:.1f} GB (peak total {lst['peak_rss_gb']:.1f}), gpu peak {lst['gpu_peak_gb']:.1f} GB"
              f" | {time.time() - t_start:.0f}s", flush=True)
        del blk, W, experts, erows
        gc.collect()
        torch.cuda.empty_cache()
        tmp = work / "checkpoint.tmp"
        torch.save({"sig": sig, "layer_done": L, "pre": pre_state, "small": small, "stats": stats}, tmp)
        os.replace(tmp, ckpt)
        if args.partial:
            Path(args.partial).write_text(json.dumps(stats) + "\n")
    parity = cfg.L % 2

    # the head
    head = ck.get("head.weight").to(dev)
    Wh = {"norm": ck.get("norm.weight").to(dev).float(), "headT": head.t().contiguous()}
    headf = head.float()
    Wh["head_f32"] = headf
    del head
    final_modes = [m for m in modes if MODE_SPEC[m][1] is None]
    per_seq = {m: [] for m in final_modes}
    def logits_rows(m, ci, rows):
        """final-layer logits [len(rows), vocab] FP32 of mode m at flattened rows of chunk ci."""
        h = H[(m, parity)][offs[ci] + rows].to(dev)
        pre = pre_state[m][offs[ci] + rows].to(dev)
        if MODE_SPEC[m][0] == "vendor":
            x = _vendor_final(vend, h[None], pre[None], Wh["norm"])[0]
            return Fn.linear(x.float(), headf)
        e = eng[MODE_SPEC[m][0]]
        step = 64 if e.exact else 1024
        return torch.cat([e.final(h[r0:r0 + step].float(), pre[r0:r0 + step].float(), Wh)
                          for r0 in range(0, h.shape[0], step)])

    for ci, cm in enumerate(chunk_meta):
        T = cm["T"]
        for bi, s_ in enumerate(cm["seqs"]):
            n = s_["len"]
            ids = cm["ids"][bi, :n].to(dev)
            if s_["kind"] == "wt":
                rows = torch.arange(bi * T, bi * T + n - 1)
            else:
                rows = torch.tensor([bi * T + n - 1])
            la = None
            for m in final_modes:
                l = logits_rows(m, ci, rows)
                rec = {"kind": s_["kind"]}
                if s_["kind"] == "wt":
                    lp = torch.log_softmax(l.double(), -1)
                    rec["nll"] = (-lp.gather(1, ids[1:, None])[:, 0]).cpu().numpy()
                    top = l.topk(2, -1)
                    rec["arg"] = top.indices[:, 0].cpu().numpy()
                    rec["margin"] = (top.values[:, 0] - top.values[:, 1]).cpu().numpy()
                    if m == "a":
                        la = lp
                    else:
                        rec["kl_a"] = (la.exp() * (la - lp)).sum(-1).cpu().numpy()
                    del lp
                else:
                    rec["pick"] = int(torch.argmax(l[0, cand]).item())
                    rec["answer"] = s_["answer"]
                    rec["mmlu_index"] = s_["index"]
                per_seq[m].append(rec)
                del l
            del la
        torch.cuda.empty_cache()
    return cfg, seqs, per_seq, stats, time.time() - t_start


def model_logits(snap, ids, kind, device="cuda"):
    """Whole-model logits [B, T, vocab] of the token batch ids [B, T] (equal lengths) under one
    arithmetic (kind: vendor | contract | torch), layer by layer, plus the router choice per layer.
    For tests and spot checks; the evaluation driver is run()."""
    dev = torch.device(device)
    snap = Path(snap)
    cfg = Cfg(snap)
    ck = Checkpoint(snap)
    tok = tokenizer_for(snap)
    ids = torch.as_tensor(ids, dtype=torch.int64)
    B, T = ids.shape
    vend = Vendor(snap, B, T, device)
    hashes = torch.stack(vend.hashes(tok, [r.tolist() for r in ids])) if cfg.engram_layers else None
    embed = ck.get("embed.weight").to(dev)
    h = embed[ids.to(dev)][:, :, None, :].repeat(1, 1, cfg.hc, 1).contiguous()
    pre = torch.zeros(B, T, cfg.hc, device=dev)
    pre[..., 0] = 1.0
    eng = None if kind == "vendor" else Engine(cfg, kind == "contract")
    st = new_state(cfg, B, T, dev)
    sh = {}
    routers = []
    for L in range(cfg.L):
        blk = vend.block(L, ck)
        er = None
        if L in cfg.engram_layers:
            er = engram_rows(ck, cfg, L, hashes[:, :, cfg.engram_layers.index(L), :], dev)
        tr = {}
        if kind == "vendor":
            h, pre = vend.run(blk, h, pre, sh, er, tr)
        else:
            W, experts = contract_weights(cfg, blk, ck, L, dev)
            hf, pf = eng.layer(L, W, experts, h.reshape(B * T, cfg.hc, cfg.dim).float(), pre.reshape(B * T, cfg.hc),
                               st, B, T, er.reshape(B * T, -1).float() if er is not None else None, tr)
            h, pre = hf.reshape(B, T, cfg.hc, cfg.dim).to(BF16), pf.reshape(B, T, cfg.hc)
        routers.append(tr["router"].reshape(B, T, -1).cpu())
        del blk
    normw = ck.get("norm.weight").to(dev).float()
    head = ck.get("head.weight").to(dev)
    if kind == "vendor":
        x = _vendor_final(vend, h, pre, normw)
        logits = Fn.linear(x.float(), head.float())
    else:
        Wh = {"norm": normw, "headT": head.t().contiguous(), "head_f32": head.float()}
        logits = eng.final(h.reshape(B * T, cfg.hc, cfg.dim).float(), pre.reshape(B * T, cfg.hc), Wh)
        logits = logits.reshape(B, T, -1)
    return logits, routers


def _vendor_final(vend, h, pre, normw):
    """vendor: hc_pre with the last pre_mix, the final RMSNorm (release RMSNorm), BF16 out."""
    y = torch.sum(pre.unsqueeze(-1) * h.float(), dim=2).to(h.dtype)
    x = y.float()
    var = x.square().mean(-1, keepdim=True)
    x = x * torch.rsqrt(var + vend.args.norm_eps)
    return (normw.to(BF16) * x).to(BF16)


def _st_to(st, dev):
    """move an engine's per-chunk attention state; on the CPU it is kept compact (the rows are
    BF16-exact, the selections fit int32), on the GPU expanded to the engines' FP32/int64."""
    cpu = str(dev) == "cpu"
    fl = (lambda v: v.to(BF16).cpu()) if cpu else (lambda v: v.to(dev).float())
    ix = (lambda v: v.to(torch.int32).cpu()) if cpu else (lambda v: v.to(dev).long())
    return {"ckv": {k: fl(v) for k, v in st["ckv"].items()},
            "ik": {k: fl(v) for k, v in st["ik"].items()},
            "sel": [ix(x) for x in st["sel"]] if st["sel"] is not None else None,
            "cand": [c.to(dev) for c in st["cand"]]}


def _rss_gb():
    """(anonymous RSS, file-backed RSS, peak total RSS) in GB.  File-backed pages (the checkpoint and
    Engram mmaps, the hidden-state files) are reclaimable page cache; the anonymous part is the
    process's own memory."""
    import resource
    v = {}
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith(("RssAnon:", "RssFile:", "RssShmem:")):
            k, n = line.split()[:2]
            v[k[:-1]] = int(n) / 1e6
    return (v.get("RssAnon", 0.0), v.get("RssFile", 0.0) + v.get("RssShmem", 0.0),
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6)


def _set_diff(a, b):
    """number of elements of sorted rows a not in sorted rows b (same k)."""
    eq = (a[..., :, None] == b[..., None, :]).any(-1)
    return (~eq).sum(-1)


def _sel_diff(ia, im):
    """(changed positions, total selected, queries with any change) between two -1-padded selections."""
    if ia.shape[1] == 0 and im.shape[1] == 0:
        return 0, 0, 0
    k = max(ia.shape[1], im.shape[1])
    if ia.shape[1] < k:
        ia = torch.cat([ia, ia.new_full((ia.shape[0], k - ia.shape[1]), -1)], 1)
    if im.shape[1] < k:
        im = torch.cat([im, im.new_full((im.shape[0], k - im.shape[1]), -1)], 1)
    ia = ia.to(im.device).long()
    im = im.long()
    va, vm = ia >= 0, im >= 0
    ina = (ia[:, :, None] == im[:, None, :]).any(-1) & va
    inm = (im[:, :, None] == ia[:, None, :]).any(-1) & vm
    changed = (va & ~ina).sum(-1) + (vm & ~inm).sum(-1)
    return int(changed.sum()), int(va.sum() + vm.sum()), int((changed > 0).sum())


# ======================================================================================
# summary
# ======================================================================================
def _boot(fn, n, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    vals = [fn(rng.integers(0, n, n)) for _ in range(B)]
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def summarize(cfg, per_seq, stats, wall, args, meta):
    out = {"modes": {}}
    ref = per_seq["a"]
    wt_idx = [i for i, r in enumerate(ref) if r["kind"] == "wt"]
    mm_idx = [i for i, r in enumerate(ref) if r["kind"] == "mmlu"]
    for m, recs in per_seq.items():
        d = {}
        if wt_idx:
            nll_m = [recs[i]["nll"] for i in wt_idx]
            nll_a = [ref[i]["nll"] for i in wt_idx]
            sm = np.array([x.sum() for x in nll_m])
            sa = np.array([x.sum() for x in nll_a])
            cnt = np.array([len(x) for x in nll_a])
            ppl_m = float(np.exp(sm.sum() / cnt.sum()))
            ppl_a = float(np.exp(sa.sum() / cnt.sum()))
            agree = np.array([(recs[i]["arg"] == ref[i]["arg"]).sum() for i in wt_idx])
            nW = len(wt_idx)
            d["wikitext2"] = {
                "windows": nW, "tokens": int(cnt.sum()), "ctx": args.ctx,
                "ppl": ppl_m, "ppl_ref": ppl_a, "rel_delta_ppl": ppl_m / ppl_a - 1,
                "rel_delta_ppl_ci95": _boot(lambda ix: float(np.exp((sm[ix].sum() - sa[ix].sum()) / cnt[ix].sum()) - 1),
                                            nW),
                "top1_agree_vs_ref": float(agree.sum() / cnt.sum()),
                "top1_agree_ci95": _boot(lambda ix: float(agree[ix].sum() / cnt[ix].sum()), nW),
            }
            if m != "a":
                kl = np.concatenate([recs[i]["kl_a"] for i in wt_idx])
                d["wikitext2"]["kl_ref_to_mode_mean_nats"] = float(kl.mean())
                d["wikitext2"]["kl_ref_to_mode_p99_nats"] = float(np.percentile(kl, 99))
                dis = np.concatenate([recs[i]["arg"] != ref[i]["arg"] for i in wt_idx])
                marg = np.concatenate([ref[i]["margin"] for i in wt_idx])
                if dis.any():
                    d["wikitext2"]["ref_margin_at_disagreements"] = {
                        "count": int(dis.sum()), "median_logits": float(np.median(marg[dis])),
                        "fraction_below_0.25": float((marg[dis] < 0.25).mean()),
                        "fraction_below_1.0": float((marg[dis] < 1.0).mean())}
                dn = np.concatenate([recs[i]["nll"] - ref[i]["nll"] for i in wt_idx])
                d["wikitext2"]["per_token_nll_delta_mean"] = float(dn.mean())
                d["wikitext2"]["per_token_nll_delta_abs_mean"] = float(np.abs(dn).mean())
                d["wikitext2"]["positions_with_changed_nll_frac"] = float((dn != 0).mean())
        if mm_idx:
            cor_m = np.array([recs[i]["pick"] == recs[i]["answer"] for i in mm_idx], dtype=float)
            cor_a = np.array([ref[i]["pick"] == ref[i]["answer"] for i in mm_idx], dtype=float)
            same = np.array([recs[i]["pick"] == ref[i]["pick"] for i in mm_idx], dtype=float)
            nQ = len(mm_idx)
            d["mmlu"] = {"questions": nQ, "accuracy": float(cor_m.mean()),
                         "accuracy_ci95": _boot(lambda ix: float(cor_m[ix].mean()), nQ),
                         "delta_pt": float(100 * (cor_m.mean() - cor_a.mean())),
                         "delta_pt_ci95": _boot(lambda ix: float(100 * (cor_m[ix].mean() - cor_a[ix].mean())), nQ),
                         "same_answer_as_ref": float(same.mean())}
        out["modes"][m] = d
    return out


def _layer_tables(layers):
    """per-layer flip/divergence series and their summaries."""
    out = {"router_flip_rate": {}, "index_query_flip_rate": {}, "index_positions_changed_frac": {},
           "hidden_rel_rms": {}}
    modes = sorted({m for l in layers for m in l["router"]})
    for m in modes:
        out["router_flip_rate"][m] = [l["router"][m]["flip_rate"] for l in layers]
        out["hidden_rel_rms"][m] = [l["hidden_rel_rms"][m] for l in layers]
        idx = {l["layer"]: l["index"][m] for l in layers if m in l["index"]}
        out["index_query_flip_rate"][m] = {str(k): v["query_flip_rate"] for k, v in idx.items()}
        out["index_positions_changed_frac"][m] = {str(k): v["selected_positions_changed_frac"] for k, v in idx.items()}
    summ = {}
    for m in modes:
        r = np.array(out["router_flip_rate"][m])
        i = np.array(list(out["index_positions_changed_frac"][m].values()) or [np.nan])
        summ[m] = {"router_flip_rate_mean": float(r.mean()), "router_flip_rate_max": float(r.max()),
                   "router_flip_rate_layer_of_max": int(r.argmax()),
                   "index_positions_changed_frac_mean": float(np.nanmean(i)),
                   "hidden_rel_rms_final_layer": out["hidden_rel_rms"][m][-1]}
    out["summary"] = summ
    return out


def finalize(run_json, raw_json, out, meta):
    """Recompute the summary from the raw per-sequence records, add the per-layer tables, the
    verdict under the pre-registered rule and the provenance, and write the committed record."""
    run_rec = json.loads(Path(run_json).read_text())
    raw = json.loads(Path(raw_json).read_text())
    per_seq = {m: [{k: (np.array(v) if isinstance(v, list) else v) for k, v in r.items()} for r in recs]
               for m, recs in raw.items()}

    class A:
        ctx = run_rec["args"]["ctx"]
    summ = summarize(None, per_seq, None, None, A, {})
    b = summ["modes"]["b"]
    ppl_rel = b["wikitext2"]["rel_delta_ppl"]
    mmlu_drop = -b["mmlu"]["delta_pt"] if "mmlu" in b else None
    ok_ppl = ppl_rel <= THRESHOLD["ppl_rel_max"]
    ok_mmlu = mmlu_drop is None or mmlu_drop <= THRESHOLD["mmlu_drop_max_pt"]
    rec = {"schema": run_rec["schema"], "tool": run_rec["tool"], "test": "tests/test_deepseek_v41_deployment_quality.py"}
    rec.update(meta)
    rec["threshold"] = THRESHOLD
    rec["verdict"] = {"acceptable": bool(ok_ppl and ok_mmlu), "ppl_rel_delta": ppl_rel,
                      "ppl_rel_delta_ci95": b["wikitext2"]["rel_delta_ppl_ci95"], "ppl_ok": bool(ok_ppl),
                      "mmlu_drop_pt": mmlu_drop, "mmlu_delta_pt_ci95": b.get("mmlu", {}).get("delta_pt_ci95"),
                      "mmlu_ok": bool(ok_mmlu)}
    rec["run"] = {"args": run_rec["args"], "wall_s": run_rec["wall_s"]}
    rec["summary"] = summ
    rec["layer_tables"] = _layer_tables(run_rec["layers"])
    rec["layers"] = run_rec["layers"]
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--finalize", nargs=3, metavar=("RUN_JSON", "RAW_JSON", "META_JSON"),
                    help="write the committed record (--out) from a run's record, raw records and provenance")
    ap.add_argument("--snapshot", default=str(SNAPSHOT))
    ap.add_argument("--windows", type=int, default=32)
    ap.add_argument("--ctx", type=int, default=2048)
    ap.add_argument("--mmlu", type=int, default=0)
    ap.add_argument("--batch", type=int, default=4, help="sequences per chunk (WikiText); MMLU packs to batch*ctx")
    ap.add_argument("--modes", default="a,a2,b,b_tf,a2_tf")
    ap.add_argument("--raw-out", default=None, help="write per-sequence raw records (npz-free JSON) here")
    ap.add_argument("--partial", default=None, help="write per-layer stats here as they complete")
    ap.add_argument("--tf-chunks", type=int, default=10 ** 9,
                    help="teacher-forced modes run on the first N chunks only (WikiText chunks come first)")
    ap.add_argument("--work", default=None, help="scratch directory for the file-backed hidden states")
    ap.add_argument("--resume", action="store_true", help="continue after the last completed layer in --work")
    ap.add_argument("--max-layers", type=int, default=0, help="smoke/timing: stop after this many layers")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()
    if args.finalize:
        rec = finalize(args.finalize[0], args.finalize[1], args.out, json.loads(Path(args.finalize[2]).read_text()))
        print(json.dumps(rec["verdict"], indent=1))
        return
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    cfg, seqs, per_seq, stats, wall = run(args)
    summ = summarize(cfg, per_seq, stats, wall, args, {})
    rec = {"schema": "opentallas.deepseek-v41-flash-deployment-quality.v1",
           "tool": "tools/deepseek_v41_deployment_quality.py",
           "threshold": THRESHOLD, "args": vars(args), "wall_s": wall,
           "summary": summ, "layers": stats["layers"]}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(rec, indent=1) + "\n")
    if args.raw_out:
        raw = {m: [{k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items()} for r in recs]
               for m, recs in per_seq.items()}
        Path(args.raw_out).write_text(json.dumps(raw))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
