#!/usr/bin/env python3
"""Independent fixed-order FP32 pair-tree / BF16 oracle for the actual IDX tail."""
import json
import sys
from pathlib import Path
import numpy as np
import hdc_golden_v41 as G

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(202610160851)
rows, expected = [], []
for i in range(256):
    # Every lane is distinct and nonzero; cancellation witnesses distinguish
    # (c0+c1)+(c2+c3) from a different reduction tree.
    signs = rng.integers(0, 2, (4, 4), dtype=np.uint32)
    exponents = rng.integers(100, 140, (4, 4), dtype=np.uint32)
    mantissas = rng.integers(0, 1 << 23, (4, 4), dtype=np.uint32)
    bits = (signs << 31) | (exponents << 23) | mantissas
    partials = bits.view(np.float32)
    if i % 8 == 0:
        for k in range(4):
            partials[k] = [np.float32(2.0 ** (40+k)), np.float32(-(2.0 ** (40+k))), np.float32(k+1), np.float32(k+1)]
        bits = partials.view(np.uint32)
    left = np.add(partials[:, 0], partials[:, 1], dtype=np.float32)
    right = np.add(partials[:, 2], partials[:, 3], dtype=np.float32)
    summed = np.add(left, right, dtype=np.float32)
    bf16 = (G.bits(G.to_bf16(summed)) >> 16).astype(np.uint16)
    faults = int(rng.integers(0, 1 << 16)) if i % 5 == 0 else 0
    keep = int(rng.integers(0, 16)); kv = int(rng.integers(0, 16))
    scores, fault_bits = 0, 0
    for k in range(4):
        bad = bool((faults >> (4*k)) & 15)
        fault_bits |= int(bad) << k
        value = 0 if bad else int(bf16[k]) if (keep >> k) & 1 else 0xff80
        scores |= value << (16*k)
    packed_sum = sum(int(bits[k, c]) << (32*(4*k+c)) for k in range(4) for c in range(4))
    rows.append(packed_sum | (faults << 512) | (keep << 528) | (kv << 532))
    expected.append(scores | (fault_bits << 64) | (kv << 68))
(out/'input.hex').write_text(''.join(f'{x:0134x}\n' for x in rows))
(out/'expected.hex').write_text(''.join(f'{x:018x}\n' for x in expected))
(out/'vectors.json').write_text(json.dumps(dict(count=len(rows),lanes=4,chunks=4,order='(c0+c1)+(c2+c3), each add rounded FP32 RNE, final BF16 RNE',seed=202610160851),indent=2)+'\n')
