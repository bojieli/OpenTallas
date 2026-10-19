#!/usr/bin/env python3
"""TOK-S81-GAPS/GU (10-18): fixture values of the G-unit's boundary words (moved out of gu_kit.py so the layer compiler
and the bench kit encode the SAME words): HP beat roots (the slice model = the golden's own chunk-8 tree, independent
of the RTL), the HC coefficient rows, the router SC scores, ids and weights rows."""
import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as g     # noqa: E402

g.set_arith('chunk8')
F = np.float32
SIZES = [[32, 8], [8, 16, 16], [16, 16, 8], [8, 32]]
KF = 4 * 5120


def u32(x):
    return int(np.asarray(x, dtype=F).view(np.uint32))


def chunk_sums(t):
    t = t.reshape(t.shape[:-1] + (KF // 8, 8))
    acc = np.zeros(t.shape[:-1], dtype=F)
    for i in range(8):
        acc = g.add(acc, t[..., i])
    return acc


def block(cs, c0, n):
    v = cs[..., c0:c0 + n]
    while v.shape[-1] > 1:
        v = g.add(v[..., 0::2], v[..., 1::2])
    return v[..., 0]


class Fx:
    def __init__(self, d):
        self.d = Path(d)
        self.read = {}

    def __call__(self, rel, dt='<f4'):
        p = self.d / rel
        self.read[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        return np.fromfile(p, dtype=dt)


def hc_roots(fx, which):
    # attn HC input: the layer input h, or on an Engram layer (L14) the Engram mix output eng.add (h + Engram)
    if which == 'attn':
        x = fx('ops/eng.add.bin') if (fx.d / 'ops/eng.add.bin').exists() else fx('io/h_in.bin')
    else:
        x = fx('ops/attn.hc_post.bin')
    flat = x.astype(F)
    assert np.array_equal(g.to_bf16(flat), flat)
    fn = fx(f'weights/hc_{which}_fn.bin').reshape(24, KF)
    terms = np.concatenate([g.mul(fn, flat[None, :]), g.mul(flat, flat)[None, :]])
    cs = chunk_sums(terms)
    # self-check: the slice model's roots finish to the fixture fn / sum of squares (golden csum)
    l5 = np.stack([block(cs, 32 * i, 32) for i in range(80)], axis=-1)
    root = g.csum(l5, c=1)
    assert np.array_equal(root[:24].view(np.uint32), fx(f'ops/{which}.hc.fn.bin').view(np.uint32)), 'fn roots'
    assert u32(root[24]) == u32(fx(f'ops/{which}.hc.sumsq.bin')[0]), 'sumsq root'

    def roots(acc, gs, h):
        wd = [0] * 6
        for kk in range(2):
            k = 2 * h + kk
            c0 = 640 * k + 40 * gs
            for j, n in enumerate(SIZES[gs % 4]):
                wd[3 * kk + j] = u32(block(cs[acc], c0, n))
                c0 += n
        return wd
    return roots


def hc_coef(fx, which):
    """24 coefficient words: pre 0..3, post 0..3, comb row-major (row i = words 4 i .. 4 i + 3)"""
    return [u32(v) for v in fx(f'ops/{which}.hc.pre_post.bin')] + [u32(v) for v in fx(f'ops/{which}.hc.sinkhorn.bin')]


def router_vals(fx):
    """(sc scores padded, {tag: (row offset, m, d128)}) for the router job"""
    sc = [u32(v) for v in fx('ops/ffn.softplus_sqrt.bin')] + [0] * 8
    ids = [int(v) for v in fx('ops/ffn.top6_order.bin', '<i8')]
    assert sorted(int(v) for v in fx('ops/ffn.top6.bin', '<i8')) == ids
    wts = [u32(v) for v in fx('ops/ffn.weights.bin')]
    p0 = ids[0] | ids[1] << 9 | ids[2] << 18
    p1 = ids[3] | ids[4] << 9 | ids[5] << 18
    return sc, {'ids': (0, 0x3, p0 | p1 << 32), 'w0': (1, 0xF, sum(wts[j] << (32 * j) for j in range(4))),
                'w1': (2, 0x3, wts[4] | wts[5] << 32)}
