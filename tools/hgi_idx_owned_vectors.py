#!/usr/bin/env python3
"""hgi-takeover 2026-10-09: vectors for IDX.OWNED (ot_hgi_idx_owned, proposed G21).
Golden: the spec 6.7 owner rule.  Row i: owner (i div B) mod G, local row (i div (B G)) B + i mod B.  For list order:
R[i] = owner * M + (count of earlier entries with the same owner); O = this rank's local rows in list order padded with 0
to M; M = max per-owner count.
  hgi_idx_owned_vectors.py OUTDIR -> cases.txt (B G die K fault M) + case_<c>.{a,o,r}.mem"""
import sys
from pathlib import Path
import numpy as np


def golden(ids, B, G, die):
    rank = die % 96 if G == 96 else die % G
    own = (ids // B) % G
    loc = (ids // (B * G)) * B + ids % B
    cnt = np.bincount(own, minlength=G)
    M = int(cnt.max())
    seen = np.zeros(G, dtype=np.int64)
    R = np.zeros(len(ids), dtype=np.uint32)
    O = []
    for i, (o, l) in enumerate(zip(own, loc)):
        R[i] = o * M + seen[o]; seen[o] += 1
        if o == rank:
            O.append(l)
    O += [0] * (M - len(O))
    return np.array(O, dtype=np.uint32), R, M


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(7)
    specs = [(8, 96, 0, 512), (8, 96, 77, 512), (8, 96, 150, 2048), (8, 8, 13, 512), (16, 4, 2, 300), (8, 1, 5, 7),
             (1, 2, 1, 64), (128, 96, 95, 512), (8, 96, 3, 512)]
    lines = []
    for c, (B, G, die, K) in enumerate(specs):
        ctx = 1 << 20
        ids = rng.choice(ctx, size=K, replace=False).astype(np.uint32)
        if c == 1:
            ids = np.sort(ids)                    # DS selections are ascending
        fault = 0
        if c == len(specs) - 1:
            ids[100] = 1 << 20; fault = 1          # id out of range
            O, R, M = np.zeros(1, np.uint32), np.zeros(1, np.uint32), 0
        else:
            O, R, M = golden(ids.astype(np.int64), B, G, die)
        np.savetxt(out / f"case_{c}.a.mem", ids, fmt="%08x")
        np.savetxt(out / f"case_{c}.o.mem", O, fmt="%08x")
        np.savetxt(out / f"case_{c}.r.mem", R, fmt="%08x")
        lines.append(f"{B} {G} {die} {K} {fault} {M} {len(O)}")
    (out / "cases.txt").write_text(f"{len(lines)}\n" + "\n".join(lines) + "\n")
    print(lines)


if __name__ == "__main__":
    main()
