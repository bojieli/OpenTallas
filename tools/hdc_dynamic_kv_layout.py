#!/usr/bin/env python3
"""Opt-in CPU host layout specialization; no hardware traffic/rate claim.

No state survives a call. Strided views refer to CURRENT decoded KV storage;
X/BF16 values broadcast only across independent output coordinates. Original
increasing-k separate operations, split tree and masks are retained.
"""
import numpy as np
import hdc_golden as G
import hdc_program as P
from hdc_dynamic_kv_vectorized import me_dynamic_kv as qualified


def _weight_view(kv, base, shape, steps):
    """Read-only affine view with every accessed element bounds checked."""
    top = base + sum((size - 1) * step for size, step in zip(shape, steps))
    if base < 0 or top >= kv.size:
        raise IndexError('dynamic KV view outside current storage')
    view = np.ndarray(shape, dtype=kv.dtype, buffer=kv, offset=base * kv.itemsize,
                      strides=tuple(step * kv.itemsize for step in steps))
    view.flags.writeable = False
    return view


def me_dynamic_kv_layout(machine, f, dyn):
    # Generic layouts/proxy storage retain the exact qualified implementation.
    group = 1 << f['me_jsh']
    if (not f['me_wsrc'] or f['me_mmode'] != 1 or group > P.IL or P.IL % group
        or any(f[key] < 0 for key in ('me_ts', 'me_wcs', 'me_js', 'me_ks', 'me_xcs', 'me_xks', 'me_xjs'))
        or any(not isinstance(a, np.ndarray) or a.ndim != 1
               or a.dtype != np.dtype(P.F) or not a.flags.c_contiguous
               for a in (machine.vm, machine.kv))):
        return qualified(machine, f, dyn)
    n = f['me_nout'] + dyn[f['me_d_nout']]
    tiles = f['me_tiles'] + dyn[f['me_d_tiles']]
    K = f['me_k'] + dyn[f['me_d_k']]
    wb = f['me_wbase'] + dyn[f['me_d_wbase']]
    xb = f['me_xbase'] + dyn[f['me_d_xbase']]
    ob = f['me_obase'] + dyn[f['me_d_obase']]
    S = 1 << f['me_split']
    per_round = P.GR // S
    if f['me_d_tiles'] == P.I.DYN_TTILES:
        tiles = f['me_tiles'] + machine.pos // (P.W * (P.GR >> f['me_split'])) + 1
    if min(n, tiles, K, wb) < 0 or per_round <= 0:
        return qualified(machine, f, dyn)
    valid = min(n, tiles * per_round * P.W)
    if not valid:
        return qualified(machine, f, dyn)
    full, tail = divmod(valid, P.W)
    heads = P.IL // group
    # Flat storage preserves t,j,lane publication order, including partial word.
    count = valid * P.IL
    acc = np.zeros((S, count), dtype=P.F)
    parts = []
    if full:
        parts.append((0, full, P.W, acc[:, :full * P.IL * P.W].reshape(
            S, full, heads, group, P.W)))
    if tail:
        parts.append((full, 1, tail, acc[:, full * P.IL * P.W:].reshape(
            S, 1, heads, group, tail)))
    batch = max(1, 262144 // count)
    jx = np.arange(P.IL)[None, :]
    for k in range(-(-K // S)):
        active = min(S, K - k * S)
        for first in range(0, active, batch):
            last = min(active, first + batch)
            c = np.arange(first, last)[:, None]
            x = machine.vm[xb + c * f['me_xcs'] + k * f['me_xks'] + jx * f['me_xjs']]
            if f['me_round']:
                x = G.to_bf16(x)
            x = x.reshape(last - first, 1, heads, group, 1)
            for start, length, lanes, dest in parts:
                base = (wb + k * f['me_ks'] + first * f['me_wcs'] + start * f['me_ts']) * P.W
                w = _weight_view(machine.kv, base, (last - first, length, heads, 1, lanes),
                                 (f['me_wcs'] * P.W, f['me_ts'] * P.W, f['me_js'] * P.W, 0, 1))
                dest[first:last] = G.add(dest[first:last], G.mul(w, x))
    while acc.shape[0] > 1:
        acc = G.add(acc[0::2], acc[1::2])
    result = acc[0]
    # Only valid coordinates exist, so tails cannot read past n or K.
    t, j, lane = (a.reshape(-1) for a in np.meshgrid(
        np.arange(full), np.arange(P.IL), np.arange(P.W), indexing='ij'))
    if tail:
        t = np.concatenate((t, np.full(P.IL * tail, full)))
        j = np.concatenate((j, np.repeat(np.arange(P.IL), tail)))
        lane = np.concatenate((lane, np.tile(np.arange(tail), P.IL)))
    nidx = (t * P.IL + j) * P.W + lane
    if f['me_oen']:
        machine.vm[(ob + t * f['me_ots'] + j * f['me_ojs']) * P.W + lane] = result
    if f['me_rmax']:
        for jj in range(P.IL):
            sel = result[j == jj]
            if len(sel):
                machine.vm[f['me_mbase'] + jj] = P.F(np.max(sel))
    if f['me_amax']:
        order = np.argsort(nidx)
        machine.logits = (np.concatenate([machine.logits, result[order]])
                          if f['me_amc'] else result[order])
        machine.argmax = int(np.argmax(machine.logits))
