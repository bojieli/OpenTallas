"""Opt-in TP4 arithmetic lowering of the pinned DSpark W8 golden.

This module does not load a checkpoint or launch inference. The GPU golden
owner supplies already quantised W8 objects and the pinned golden_step callable.
Explicit norms stay before matvecs. QKV and gate/up use their fused local row
geometry. O/down fold RAW rank partials before the one full-row BF16 scale.
"""
from __future__ import annotations

import numpy as np
import hdc_golden as G


class MatrixTP4:
    def __init__(self, weight, mode, *, fused_rows=None, groups=6144):
        self.codes, self.scale = weight.codes, weight.scale
        self.n, self.k = self.codes.shape
        self.groups, self.mode = groups, mode
        if mode not in ('rows', 'columns'):
            raise ValueError('partition must be rows or columns')
        if (self.n if mode == 'rows' else self.k) % 4:
            raise ValueError('TP4 partition must divide evenly')
        n = (fused_rows or self.n) // 4 if mode == 'rows' else self.n
        k = self.k if mode == 'rows' else self.k // 4
        self.split = G.split_for(n, k, groups)
        if groups % self.split:
            raise ValueError('K-split does not divide the actual lane groups')

    def __call__(self, x):
        x = np.asarray(x, dtype=np.float32)
        if x.shape != (self.k,):
            raise ValueError('matrix input extent mismatch')
        parts = []
        for rank in range(4):
            if self.mode == 'rows':
                lo, hi = rank * self.n // 4, (rank + 1) * self.n // 4
                raw = G.matvec(self.codes[lo:hi], x, self.split)
                parts.append(G.mul(raw, self.scale[lo:hi]))
            else:
                lo, hi = rank * self.k // 4, (rank + 1) * self.k // 4
                parts.append(G.matvec(self.codes[:, lo:hi], x[lo:hi], self.split))
        if self.mode == 'rows':
            return np.concatenate(parts)
        return G.mul(G.fold(parts), self.scale)


def lower_weights(weights, *, enabled=False):
    if not enabled:
        raise ValueError('DSpark TP4 lowering is default-off')
    out = dict(weights)
    for name in ('fc', 'lm_head', 'w2'):
        out[name] = MatrixTP4(weights[name], 'rows')
    out['layers'] = []
    for layer in weights['layers']:
        p = dict(layer)
        qkv_rows = sum(layer[name].n for name in ('q', 'k', 'v'))
        gu_rows = layer['gate'].n + layer['up'].n
        for name in ('q', 'k', 'v', 'gate', 'up'):
            p[name] = MatrixTP4(layer[name], 'rows',
                                fused_rows=qkv_rows if name in ('q', 'k', 'v') else gu_rows)
        for name in ('o', 'down'):
            p[name] = MatrixTP4(layer[name], 'columns')
        out['layers'].append(p)
    return out


def golden_step_tp4(golden_step, weights, *args, enabled=False, **kwargs):
    """Same pinned golden operation order, with the TP4 matrix substitutions."""
    return golden_step(lower_weights(weights, enabled=enabled), *args, **kwargs)
