#!/usr/bin/env python3
"""Host-only R-ARITH successor; original golden source remains untouched.

Batch independent contiguous chunk accumulators, never offsets within a
chunk. Missing tail elements perform no add; padding is introduced only at
exactly the original chunk-tree boundary. No hardware latency/rate claim.
"""
import operator
import numpy as np
import hdc_golden as G


def reduce_chunked_vectorized(v, c=G.CHUNK):
    c = operator.index(c)
    if c <= 0:
        raise ValueError('chunk size must be positive')
    v = np.asarray(v, dtype=G.F).reshape(-1)
    chunks = max(1, (len(v) + c - 1) // c)
    padded = 1 << (chunks - 1).bit_length()
    parts = np.zeros(padded, dtype=G.F)
    for offset in range(min(c, len(v))):
        values = v[offset::c]
        # Only real elements update their own chunk, in offset order. Neither
        # missing tail elements nor padded chunks receive an extra zero add.
        parts[:len(values)] = G.add(parts[:len(values)], values)
    while len(parts) > 1:
        parts = G.add(parts[0::2], parts[1::2])
    return G.F(parts[0])
