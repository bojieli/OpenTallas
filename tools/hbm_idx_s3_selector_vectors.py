#!/usr/bin/env python3
"""L2H-IDXSEL s3 selector vectors: frame 0 = a CRAFTED frame that makes the two schedule margins observable, frames 1..3 =
the three frames of tools/hbm_idx_static_selector_vectors.py (same seed, same bytes: full10928 / all-tie / partial4100).

Crafted frame (orderkey K = orderkey(bf16 bits), positive values only, no zero, no NaN): the k = 512 threshold
T = (20 << 11) | (31 << 6) | 0, i.e. pass-0 bin 20, pass-1 bin 31 and pass-2 bin 0 (the LAST op5 of the pass-2 run).
511 keys lie above T inside the same pass-0 / pass-1 bins (pass-2 bins 1..63), so pass 2 finds the bin on its final
op5 with rank_left 1 and the tie budget (ties) is decided by that final choose step.  Three keys equal T; the one with
the lowest index sits in line 0 of quadrant 0, so the FIRST compaction line consumes the fresh tie budget:
  * a choose spacing one edge short (sel_choose_rt 7) reads the stale (post-reset 0) budget -> 511 chosen: FAIL;
  * a scan drain one edge short (op5 inside the last drain slot) misses line 170's pass-2 bin-63 keys (put there on
    purpose) -> rank_left off at bin 0 -> no tie budget: FAIL.
The crafted frame runs FIRST after reset so the stale budget is the reset value 0 (deterministic).
"""
import sys
from pathlib import Path
import numpy as np


def write(out, frame, n, bits):
    vals = (bits.astype(np.uint32) << 16).view(np.float32)
    chosen = set(sorted(range(n), key=lambda i: (-float(vals[i]), i))[:512])
    lines = []
    for a in range(171):
        packed = 0
        for q in range(4):
            for l in range(16):
                i = q * 2736 + a * 16 + l
                entry = ((i << 17) | (int(bits[i]) << 1) | 1) if i < n else 0
                packed |= entry << (q * 592 + l * 37)
        lines.append(packed)
    (out / f'lines{frame}.hex').write_text(''.join(f'{v:0592x}\n' for v in lines))
    (out / f'gold{frame}.hex').write_text(''.join(f'{int(i in chosen):x}\n' for i in range(10944)))
    (out / f'scores{frame}.hex').write_text(''.join(f'{int(bits[i]) if i < n else 0:04x}\n' for i in range(10944)))
    return chosen


def crafted():
    n = 10928
    rng = np.random.default_rng(20261020)
    T = (20 << 11) | (31 << 6)
    K = np.zeros(n, dtype=np.uint32)
    special = {}
    # line 170 (a = 170) of quadrants 0..2: pass-2 bin-63 keys (above T), lanes 0..3
    for q in range(3):
        for l in range(4):
            special[q * 2736 + 170 * 16 + l] = T | 63
    # ties (== T): quadrant 0 line 0 lane 3 (lowest index -> the chosen one), quadrant 2 line 0 lane 7, quadrant 1 line 9
    for i in (3, 2 * 2736 + 7, 2736 + 9 * 16 + 4):
        special[i] = T
    free = [i for i in range(n) if i not in special]
    rng.shuffle(free)
    above = 511 - sum(1 for v in special.values() if v > T)
    for j, i in enumerate(free[:above]):
        special[i] = T | int(1 + rng.integers(0, 63))          # pass-2 bins 1..63
    for i in free[above:]:
        special[i] = int(rng.integers(0x8100, T))              # below T, positive, no zero
    for i, v in special.items():
        K[i] = v
    assert int((K > T).sum()) == 511 and int((K == T).sum()) == 3
    bits = (K ^ 0x8000).astype(np.uint16)                      # K[15] = 1 -> positive bf16 = K ^ 0x8000
    return n, bits


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    n, bits = crafted()
    ch = write(out, 0, n, bits)
    assert 3 in ch and (2 * 2736 + 7) not in ch and len(ch) == 512
    rng = np.random.default_rng(20261015)                       # == tools/hbm_idx_static_selector_vectors.py
    for frame in range(3):
        n = 4100 if frame == 2 else 10928
        values = (rng.normal(size=n) * 4).astype(np.float32)
        if frame == 1:
            values[:] = 1
        bits = (values.view(np.uint32) >> 16).astype(np.uint16)
        write(out, frame + 1, n, bits)


if __name__ == '__main__':
    main()
