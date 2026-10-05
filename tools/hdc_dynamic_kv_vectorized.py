#!/usr/bin/env python3
"""Opt-in host-only dynamic-KV ME; original ISA/golden sources stay unchanged.

Independent split/output coordinates are batched. Each coordinate keeps its
increasing-k separate G.mul then G.add, BF16 input round and canonical zero;
only the original adjacent-pair split tree combines coordinates. Invalid tail
splits perform neither gathers nor zero arithmetic. No hardware/rate claim.
"""
import numpy as np
import hdc_golden as G
import hdc_program as P


def me_dynamic_kv(machine, f, dyn):
    if not f['me_wsrc']:
        raise ValueError('vectorized dynamic-KV path requires me_wsrc=1')
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
    r, q, j, lane = (a.reshape(-1) for a in np.meshgrid(
        np.arange(tiles), np.arange(per_round), np.arange(P.IL),
        np.arange(P.W), indexing='ij'))
    t = r * per_round + q
    nidx = (t * P.IL + j) * P.W + lane
    keep = (nidx < n) if f['me_mmode'] == 0 else (t * P.W + lane < n)
    t, j, lane, nidx = t[keep], j[keep], lane[keep], nidx[keep]
    acc = np.zeros((S, len(t)), dtype=P.F)
    # Only independent coordinates are vectorized: never a sum/reduction over k.
    for k in range(-(-K // S)):
        active = min(S, K - k * S)
        if active <= 0:
            continue
        # Keep gather scratch bounded even at a full context. This is a
        # host working-set tile, not a changed split, tree or causal bound.
        batch = max(1, 262144 // max(1, len(t)))
        for first in range(0, active, batch):
            last = min(active, first + batch)
            c = np.arange(first, last)[:, None]
            # Mask BEFORE either gather: invalid past-K coordinates never
            # touch memory and never execute an added multiply/add of zero.
            word = (wb + t[None, :] * f['me_ts'] + c * f['me_wcs'] +
                    k * f['me_ks'] + (j[None, :] >> f['me_jsh']) * f['me_js'])
            w = machine.kv[word * P.W + lane[None, :]]
            x = machine.vm[xb + c * f['me_xcs'] + k * f['me_xks'] +
                           j[None, :] * f['me_xjs']]
            if f['me_round']:
                x = G.to_bf16(x)
            acc[first:last] = G.add(acc[first:last], G.mul(w, x))
    while acc.shape[0] > 1:
        acc = G.add(acc[0::2], acc[1::2])
    result = acc[0]
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
