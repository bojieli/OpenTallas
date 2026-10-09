"""The HGI-1 arithmetic library (spec section 4): the order functions every unit op computes, shared by the
simulator's units and by the qwen_r25 golden (and nothing else is shared between them).

All operations are IEEE binary32 RNE with every zero result +0 (tools/hdc_golden.py add / mul; exp, rsqrt as the
golden defines them; div IEEE).  Each order function names the unit and the RTL bench it is pinned to.

  csum          R-ARITH chunk8: contiguous chunks of 8 from +0, chunk sums a +0-padded pairwise tree
                (SU reducer ot_hdc_v41x_vec_red; norm engine; softmax unit's streaming binary counter)
  sm_int8 / sm_bf16 / sm_blockdot
                SM.MATVEC fmt 3 / 0 / 1-2 on the die's rows (fmt 3 == fmt 0 on the BF16-widened image)
  pairwise      COLL.ALL_REDUCE_SUM: die partials in rank order ((p0 + p1) + (p2 + p3)) ...
  row_norm      FUSED.ROW_NORM: per segment r = rsqrt(csum(x*x) * fp32(1/seg) + fp32(eps)); (x * r) * g
  att_qk / att_pv
                ATT tiles: chunk8 + pairwise per 64-slice, slices in slice order (== csum8 over the head dim);
                p.v: csum8 over the positions, zero-padded to a power-of-two chunk count
  glu           SFU.GLU in Qwen mode (out FP32 here; BF16 / clamp / route weight per glu_* modes)
  argmax        ARGMAX.LOCAL / COLL.ARGMAX_MERGE: numpy argmax, lowest index on ties
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_golden as G  # noqa: E402

F = np.float32
CHUNK = 8
add, mul, neg, exp, rsqrt, to_bf16, to_fp8, z = G.add, G.mul, G.neg, G.exp, G.rsqrt, G.to_bf16, G.to_fp8, G.z


def div(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return z(np.asarray(a, dtype=F) / np.asarray(b, dtype=F))


def csum(t, axis=-1, c=CHUNK):
    t = np.moveaxis(np.asarray(t, dtype=F), axis, -1)
    n = t.shape[-1]
    nc = max(1, -(-n // c))
    pad = nc * c - n
    if pad:
        t = np.concatenate([t, np.zeros(t.shape[:-1] + (pad,), dtype=F)], axis=-1)
    t = t.reshape(t.shape[:-1] + (nc, c))
    acc = np.zeros(t.shape[:-1], dtype=F)
    for i in range(c):
        acc = add(acc, t[..., i])
    while acc.shape[-1] & (acc.shape[-1] - 1):
        acc = np.concatenate([acc, np.zeros(acc.shape[:-1] + (1,), dtype=F)], axis=-1)
    while acc.shape[-1] > 1:
        acc = add(acc[..., 0::2], acc[..., 1::2])
    return acc[..., 0]


def pairwise(parts):
    parts = list(parts)
    while len(parts) & (len(parts) - 1):
        parts.append(np.zeros_like(parts[0]))
    while len(parts) > 1:
        parts = [add(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
    return parts[0]


def sm_int8(codes, x, rows_per=2048):
    """SM.MATVEC fmt 3: t[n] = csum8_k(bf16(x)[k] * code[n, k]) (INT8 x BF16 products are exact in FP32)."""
    xb = to_bf16(np.asarray(x, dtype=F))
    n = codes.shape[0]
    out = np.empty(n, dtype=F)
    for r0 in range(0, n, rows_per):
        out[r0:r0 + rows_per] = csum(mul(np.asarray(codes[r0:r0 + rows_per], dtype=F), xb[None, :]))
    return out


def sm_bf16(w, x, rows_per=2048):
    """SM.MATVEC fmt 0: BF16 weights (the BF16-widened INT8 image gives the same products as fmt 3)."""
    return sm_int8(w, x, rows_per)


def row_norm(x, g, eps, seg=0):
    """FUSED.ROW_NORM: x [m * seg] (seg 0 = one segment of the whole row)."""
    x = np.asarray(x, dtype=F)
    d = x.size if seg == 0 else seg
    xs = x.reshape(-1, d)
    s = csum(mul(xs, xs))
    r = rsqrt(add(mul(s, F(1.0 / d)), F(eps)))
    return mul(mul(xs, r[:, None]), np.asarray(g, dtype=F).reshape(1, -1)).reshape(-1)


def rope_tables(pos, hd, theta):
    """cos / sin of rotate-half RoPE at one position: fp32(cos(f64(fp32(pos) * fp32(inv_freq))))."""
    inv = (1.0 / (theta ** (np.arange(0, hd, 2, dtype=np.float64) / hd))).astype(np.float32)
    ang = (np.asarray(pos, dtype=np.float32).reshape(-1)[:, None] * inv[None, :]).astype(np.float32)
    return np.cos(ang.astype(np.float64)).astype(F), np.sin(ang.astype(np.float64)).astype(F)


def rope_half(v, cos, sin):
    h = v.shape[-1] // 2
    a, b = v[..., :h], v[..., h:]
    return np.concatenate([add(mul(a, cos), mul(b, neg(sin))), add(mul(b, cos), mul(a, sin))], axis=-1).astype(F)


def att_qk(q, K):
    """q [hd] (BF16 values), K [P, hd] -> raw dots [P] (chunk8 per 64-slice, slices in order == csum8 over hd)."""
    hd = K.shape[1]
    if hd % 64 == 0 and hd > 64:
        parts = [csum(mul(q[None, s:s + 64], K[:, s:s + 64])) for s in range(0, hd, 64)]
        acc = parts[0]
        for p in parts[1:]:
            acc = add(acc, p)
        return acc
    return csum(mul(q[None, :], K))


def att_pv(p, Vr):
    """p [P] (BF16 values), V [P, hd] -> [hd]: csum8 over positions (zero padding to a power-of-two chunk count)."""
    return csum(mul(np.asarray(p, dtype=F)[:, None], Vr), axis=0)


def softmax_e_z(s, scale, sink=None):
    """Scaled scores s * scale, max, e = exp(x - m), Z = csum(e) (+ exp(sink - m) after the row sum)."""
    x = mul(s, scale)
    m = F(np.max(x))
    e = exp(add(x, neg(m)))
    Z = csum(e)
    if sink is not None:
        Z = add(Z, exp(add(F(sink), neg(m))))
    return e, Z, m


def glu(g, u, limit=None, route_w=None, out_bf16=False):
    """SFU.GLU: act = g / (1 + exp(-g)) (IEEE divide); (clamp, route weight, BF16 publication per mode)."""
    if limit is not None:
        u = np.clip(u, -limit, limit).astype(F)
        g = np.minimum(g, limit).astype(F)
    a = mul(div(g, add(exp(mul(g, F(-1.0))), F(1.0))), u)
    if route_w is not None:
        a = mul(F(route_w), a)
    return to_bf16(a) if out_bf16 else a


def argmax(v):
    v = np.asarray(v, dtype=F)
    return int(np.argmax(v))       # lowest index on ties
