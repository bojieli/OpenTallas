#!/usr/bin/env python3
"""Vectors + golden for the q3h C_B16 fabric bench: vec.hex (op * 16 + K-slice -> 16 FP32 lanes, lane 0 = bit 31:0) and
gold.hex (the reference morton pair-tree sum per op, numpy float32 = IEEE RNE per add, leg a = the lower half).
Lanes 0..3 carry cancellation patterns so a wrong pairing (bench MUT 2: slices 0 and 4 exchanged) changes the sum."""
import sys
import numpy as np

NOPS = 4


def tree(v):                      # v: [16, 16] float32, rows = K-slice in morton order
    while len(v) > 1:
        v = np.array([(v[2 * i] + v[2 * i + 1]).astype(np.float32) for i in range(len(v) // 2)], dtype=np.float32)
    return v[0]


def hex512(lanes):
    u = lanes.astype(np.float32).view(np.uint32)
    return "".join("%08x" % int(u[15 - i]) for i in range(16))


def main(out):
    rng = np.random.default_rng(20261016)
    vec, gold = [], []
    for o in range(NOPS):
        v = (rng.standard_normal((16, 16)) * np.float32(2.0) ** rng.integers(-8, 9, (16, 16))).astype(np.float32)
        big = np.float32(1e20 * (o + 1))
        v[:, 0] = np.float32(1.0)
        v[0, 0], v[1, 0], v[4, 0], v[5, 0] = big, -big, np.float32(1.0), np.float32(1.0)
        v[:, 1] = np.float32(2.0 ** -20)
        v[0, 1], v[1, 1] = np.float32(3.0), np.float32(-3.0)
        v[4, 2], v[0, 2] = np.float32(1e30), np.float32(-1e30)
        for k in range(16):
            vec.append(hex512(v[k]))
        gold.append(hex512(tree(v)))
    open(f"{out}/vec.hex", "w").write("\n".join(vec) + "\n")
    open(f"{out}/gold.hex", "w").write("\n".join(gold) + "\n")


if __name__ == "__main__":
    main(sys.argv[1])
